/* Experimental read-only Mobius command interception. No guest code is skipped.
 * UV, texture layout and compositing are provisional; overlay is opt-in.
 * Include only in libretro.c after the core and log callback declarations. */
#define MOB_MAX 1024
#define MOB_BANKS 8
static bool mobEnabled, mobOverlay, mobHeld;
static unsigned mobCount, mobHits, mobFrames, mobBanks;
static struct { float v[12]; unsigned op, material, bank; } mobCmd[MOB_MAX];
static struct { uint32_t addr; unsigned char pixels[256*256*4]; } mobTex[MOB_BANKS];
static unsigned char mobPalette[256][4];
static GLuint mobProgram, mobVAO, mobVBO, mobTexture;
static bool mobRange(uint32_t a,unsigned n) {
    return (a>=0x02000000 && a<=0x02040000 && n<=0x02040000-a)
        || (a>=0x03000000 && a<=0x03008000 && n<=0x03008000-a)
        || (a>=0x05000000 && a<=0x05000400 && n<=0x05000400-a)
        || (a>=0x06000000 && a<=0x06018000 && n<=0x06018000-a)
        || (a>=0x08000000 && a<=0x08800000 && n<=0x08800000-a);
}
static unsigned mob8(uint32_t a) { return core->rawRead8(core,a,-1)&255; }
static unsigned mob16(uint32_t a) { return mob8(a)|(mob8(a+1)<<8); }
static uint32_t mob32(uint32_t a) { return mob16(a)|((uint32_t)mob16(a+2)<<16); }
static void mobReset(void) {
    uint32_t crc=0;
    mobCount=mobHits=mobFrames=mobBanks=0; mobOverlay=mobHeld=false; mobEnabled=false;
    if (!core || core->platform(core)!=mPLATFORM_GBA) return;
    core->checksum(core,&crc,mCHECKSUM_CRC32);
    mobEnabled=(crc==0xad356fb9u || crc==0xd0ab6a37u);
    if (mobEnabled && logCallback) logCallback(RETRO_LOG_INFO,"Mobius ROM recognized. Select+L+R toggles experimental polygon overlay.\n");
}
static unsigned mobBank(uint32_t a) {
    for(unsigned i=0;i<mobBanks;i++) if(mobTex[i].addr==a) return i;
    if(mobBanks==MOB_BANKS || !mobRange(a,65536)) return MOB_BANKS;
    unsigned b=mobBanks++;mobTex[b].addr=a;
    for(unsigned i=0;i<65536;i++) {
        unsigned idx=mob8(a+i);
        memcpy(mobTex[b].pixels+i*4,mobPalette[idx],4);
    }
    return b;
}
void azMobiusHit(uint32_t ctx) {
    if(!mobEnabled || !core || !mobRange(ctx,0x60)) return;
    uint32_t a=mob32(ctx+0x38), base=mob32(ctx+0x40), fb=mob32(ctx+0x3c);
    if(!mobRange(a,4) || !mobRange(fb,2) || (mob32(ctx+0x44)&15)>3) return;
    unsigned count=0;
    uint32_t seen[MOB_MAX];
    if(mobOverlay) {
        mobBanks=0;
        for(unsigned i=0;i<256;i++) {
            unsigned c=mob16(0x05000000+i*2);
            mobPalette[i][0]=(c&31)*255/31;
            mobPalette[i][1]=((c>>5)&31)*255/31;
            mobPalette[i][2]=((c>>10)&31)*255/31;
            mobPalette[i][3]=255;
        }
    }
    while(count<MOB_MAX) {
        if(!mobRange(a,4)) return;
        unsigned op=mob8(a);
        if(!op) {
            mobCount=count; mobHits++;
            if(mobHits==1 && logCallback) logCallback(RETRO_LOG_INFO,"Mobius live list: %u commands, context=%08x framebuffer=%08x\n",count,ctx,fb);
            return;
        }
        if(op>7) return;
        unsigned n=(op==3||op==6)?36:(op==2||op==5)?28:(op==7)?12:24;
        if(!mobRange(a,n)) return;
        for(unsigned i=0;i<count;i++) if(seen[i]==a) return;
        seen[count]=a;
        mobCmd[count].op=op; mobCmd[count].material=mob8(a+11); mobCmd[count].bank=MOB_BANKS;
        if(op!=7) {
            unsigned stride=(op==3||op==6)?8:4;
            for(unsigned j=0;j<3;j++) {
                unsigned p=a+12+j*stride;
                mobCmd[count].v[j*4]=(int16_t)mob16(p)/8.0f;
                mobCmd[count].v[j*4+1]=(int16_t)mob16(p+2)/8.0f;
                mobCmd[count].v[j*4+2]=stride==8?mob16(p+4)/65536.0f:0;
                mobCmd[count].v[j*4+3]=stride==8?mob16(p+6)/65536.0f:0;
            }
            if(mobOverlay && stride==8 && base<=UINT32_MAX-(mobCmd[count].material<<16))
                mobCmd[count].bank=mobBank(base+(mobCmd[count].material<<16));
        }
        count++; a=(a&0xffff0000u)|mob16(a+2);
    }
}
static const char* mobVS="#version 300 es\nlayout(location=0) in vec4 vertex; out vec2 uv; void main(){uv=vertex.zw;gl_Position=vec4(vertex.x/120.0-1.0,1.0-vertex.y/80.0,0,1);}";
/* Three taps across the texel triangle; nearest source texels, no bilinear.
 * Continuous affine UV, not an exact fixed-point RDP emulation. */
static const char* mobFS="#version 300 es\nprecision highp float; precision highp int; in vec2 uv; uniform sampler2D image; uniform int textured; uniform vec4 flatColor; out vec4 pixel;\n"
"vec4 tap(ivec2 p){ivec2 s=textureSize(image,0);return texelFetch(image,((p%s)+s)%s,0);}\n"
"vec4 threePoint(vec2 st){vec2 p=st*vec2(textureSize(image,0))-0.5;ivec2 i=ivec2(floor(p));vec2 f=fract(p);"
"if(f.x+f.y<=1.0){vec4 a=tap(i);return a+f.x*(tap(i+ivec2(1,0))-a)+f.y*(tap(i+ivec2(0,1))-a);}"
"vec4 d=tap(i+ivec2(1,1));return d+(1.0-f.x)*(tap(i+ivec2(0,1))-d)+(1.0-f.y)*(tap(i+ivec2(1,0))-d);}\n"
"void main(){pixel=textured!=0?threePoint(uv):flatColor;}";
static GLuint mobShader(GLenum kind,const char* source) {
    GLuint s=glCreateShader(kind); glShaderSource(s,1,&source,NULL);glCompileShader(s);
    GLint ok=0;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);
    if(!ok){char err[512];glGetShaderInfoLog(s,sizeof err,NULL,err);if(logCallback)logCallback(RETRO_LOG_ERROR,"Mobius shader: %s\n",err);glDeleteShader(s);return 0;}return s;
}
static bool mobInitGL(void) {
    if(mobProgram) return true;
    GLuint vs=mobShader(GL_VERTEX_SHADER,mobVS),fs=mobShader(GL_FRAGMENT_SHADER,mobFS);
    if(!vs||!fs){if(vs)glDeleteShader(vs);if(fs)glDeleteShader(fs);return false;}
    mobProgram=glCreateProgram();glAttachShader(mobProgram,vs);glAttachShader(mobProgram,fs);glLinkProgram(mobProgram);glDeleteShader(vs);glDeleteShader(fs);
    GLint ok=0;glGetProgramiv(mobProgram,GL_LINK_STATUS,&ok);if(!ok){glDeleteProgram(mobProgram);mobProgram=0;return false;}
    glGenVertexArrays(1,&mobVAO);glGenBuffers(1,&mobVBO);glGenTextures(1,&mobTexture);return true;
}
static void mobDestroyGL(void) {
    if(mobProgram)glDeleteProgram(mobProgram);if(mobVAO)glDeleteVertexArrays(1,&mobVAO);if(mobVBO)glDeleteBuffers(1,&mobVBO);if(mobTexture)glDeleteTextures(1,&mobTexture);
    mobProgram=mobVAO=mobVBO=mobTexture=0;
}
static void mobDraw(unsigned w,unsigned h) {
    if(!mobEnabled||!mobOverlay||!mobCount||!mobInitGL()) return;
    GLint program,vao,vbo,active,tex,viewport[4],unpack;
    glGetIntegerv(GL_CURRENT_PROGRAM,&program);glGetIntegerv(GL_VERTEX_ARRAY_BINDING,&vao);glGetIntegerv(GL_ARRAY_BUFFER_BINDING,&vbo);
    glGetIntegerv(GL_ACTIVE_TEXTURE,&active);glActiveTexture(GL_TEXTURE0);glGetIntegerv(GL_TEXTURE_BINDING_2D,&tex);
    glGetIntegerv(GL_VIEWPORT,viewport);glGetIntegerv(GL_UNPACK_ALIGNMENT,&unpack);
    GLboolean depth=glIsEnabled(GL_DEPTH_TEST),blend=glIsEnabled(GL_BLEND),cull=glIsEnabled(GL_CULL_FACE),stencil=glIsEnabled(GL_STENCIL_TEST);
    GLboolean mask[4];glGetBooleanv(GL_COLOR_WRITEMASK,mask);
    glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glDisable(GL_STENCIL_TEST);glColorMask(1,1,1,1);
    glViewport(0,0,w,h);glUseProgram(mobProgram);glBindVertexArray(mobVAO);glBindBuffer(GL_ARRAY_BUFFER,mobVBO);
    glVertexAttribPointer(0,4,GL_FLOAT,GL_FALSE,0,0);glEnableVertexAttribArray(0);
    glBindTexture(GL_TEXTURE_2D,mobTexture);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glPixelStorei(GL_UNPACK_ALIGNMENT,1);
    glUniform1i(glGetUniformLocation(mobProgram,"image"),0);
    GLint mode=glGetUniformLocation(mobProgram,"textured"),color=glGetUniformLocation(mobProgram,"flatColor");
    unsigned previous=MOB_BANKS;
    for(unsigned i=0;i<mobCount;i++) {
        unsigned op=mobCmd[i].op,b=mobCmd[i].bank;
        if(op==1||op==4){
            unsigned char* p=mobPalette[mobCmd[i].material];
            glUniform1i(mode,0);glUniform4f(color,p[0]/255.0f,p[1]/255.0f,p[2]/255.0f,1);
        } else if((op==3||op==6)&&b<mobBanks) {
            if(previous!=b){glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,256,256,0,GL_RGBA,GL_UNSIGNED_BYTE,mobTex[b].pixels);previous=b;}
            glUniform1i(mode,1);
        } else continue;
        glBufferData(GL_ARRAY_BUFFER,sizeof mobCmd[i].v,mobCmd[i].v,GL_STREAM_DRAW);glDrawArrays(GL_TRIANGLES,0,3);
    }
    glPixelStorei(GL_UNPACK_ALIGNMENT,unpack);glBindTexture(GL_TEXTURE_2D,tex);glActiveTexture(active);
    glBindVertexArray(vao);glBindBuffer(GL_ARRAY_BUFFER,vbo);glUseProgram(program);glViewport(viewport[0],viewport[1],viewport[2],viewport[3]);glColorMask(mask[0],mask[1],mask[2],mask[3]);
    if(depth)glEnable(GL_DEPTH_TEST);if(blend)glEnable(GL_BLEND);if(cull)glEnable(GL_CULL_FACE);if(stencil)glEnable(GL_STENCIL_TEST);
}
