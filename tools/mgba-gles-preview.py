#!/usr/bin/env python3
"""Experimental Switch-style mGBA GLES3 libretro bridge, separate from stock."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
def rep(rel,a,b):
    p=root/rel
    s=p.read_text()
    if s.count(a)!=1: raise SystemExit("GPU anchor mismatch: "+rel+" "+repr(a))
    p.write_text(s.replace(a,b,1))

rep("CMakeLists.txt",
    'target_link_libraries(${BINARY_NAME}_libretro ${OS_LIB})'.replace('\\',''),
    '''target_link_libraries(${BINARY_NAME}_libretro ${OS_LIB})
    find_library(AZ_GLES_LIBRARY NAMES GLESv2 REQUIRED)
    target_compile_definitions(${BINARY_NAME}_libretro PRIVATE BUILD_GLES3)
    target_link_libraries(${BINARY_NAME}_libretro ${AZ_GLES_LIBRARY})'''.replace('\\',''))
p="src/platform/libretro/libretro.c"
rep(p,'#include "libretro.h"','#include "libretro.h"\n#include <GLES3/gl3.h>')
rep(p,"static struct mCore* core;\n","static struct mCore* core;\n"+r'''
/* A distinct opt-in hardware core. The existing software viewport core is
 * untouched. GPU texture is owned by this bridge, never read back per frame.
 * The expanded exterior is rendered from live VRAM on the GPU. */
extern GLuint azGbaExteriorFramebuffer(void);
static struct retro_hw_render_callback azHW;
static GLuint azTex, azReadFbo;
static bool azRequested, azActive, azStarted;
static void azContextDestroy(void) {
    if (azActive && core) {
        mCoreConfigSetIntValue(&core->config,"hwaccelVideo",0);
        if (azStarted) core->reloadConfigOption(core,"hwaccelVideo",NULL);
        core->setVideoGLTex(core,(unsigned)-1);
    }
    if (azReadFbo) glDeleteFramebuffers(1,&azReadFbo);
    if (azTex) glDeleteTextures(1,&azTex);
    azReadFbo=azTex=0;
    azActive=false;
}
static void azContextReset(void) {
    if (!core || !azRequested) return;
    glGenTextures(1,&azTex);
    glGenFramebuffers(1,&azReadFbo);
    if (!azTex || !azReadFbo) { azContextDestroy(); return; }
    core->setVideoGLTex(core,azTex);
    mCoreConfigSetIntValue(&core->config,"videoScale",2);
    mCoreConfigSetIntValue(&core->config,"hwaccelVideo",1);
    azActive=true;
    if (azStarted) core->reloadConfigOption(core,"hwaccelVideo",NULL);
}
static void azPresent(void) {
    GLuint target=(GLuint)azHW.get_current_framebuffer();
    glDisable(GL_SCISSOR_TEST);
    glDisable(GL_BLEND);
    glDisable(GL_DEPTH_TEST);
    glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER,target);
    glViewport(0,0,640,480);
    GLuint exterior=azGbaExteriorFramebuffer();
    if (exterior) {
        glBindFramebuffer(GL_READ_FRAMEBUFFER,exterior);
        glBlitFramebuffer(0,0,640,480,0,480,640,0,GL_COLOR_BUFFER_BIT,GL_NEAREST);
    } else {
        glClearColor(0,0,0,1);
        glClear(GL_COLOR_BUFFER_BIT);
    }
    glBindFramebuffer(GL_READ_FRAMEBUFFER,azReadFbo);
    glFramebufferTexture2D(GL_READ_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,azTex,0);
    if (glCheckFramebufferStatus(GL_READ_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE) {
        /* mGBA output has row zero at GL y=0. Flip for the libretro FBO. */
        glBlitFramebuffer(0,0,480,320,80,400,560,80,GL_COLOR_BUFFER_BIT,GL_NEAREST);
    }
    /* The GL2 frontend binds its frame texture before restoring render state.
     * mGBA's finalizer leaves unit 8 active; hand back unit 0 and clean state
     * to avoid the normal gameplay shader sampling an unrelated texture. */
    glBindFramebuffer(GL_FRAMEBUFFER,target);
    glActiveTexture(GL_TEXTURE0);
    glBindSampler(0,0);
    glBindTexture(GL_TEXTURE_2D,0);
    glBindVertexArray(0);
    glBindBuffer(GL_ARRAY_BUFFER,0);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,0);
    glDisable(GL_STENCIL_TEST);
    glDisable(GL_CULL_FACE);
    glDisable(GL_RASTERIZER_DISCARD);
    glUseProgram(0);
    videoCallback(RETRO_HW_FRAME_BUFFER_VALID,640,480,0);
}
''')
rep(p,'\tinfo->library_name = projectName;','\tinfo->library_name = "mGBA GLES3 RGDS (experimental)";')
rep(p,'\tinfo->geometry.max_height = height;','''\tinfo->geometry.max_height = height;
    if (azRequested) {
        info->geometry.base_width=info->geometry.max_width=640;
        info->geometry.base_height=info->geometry.max_height=480;
        info->geometry.aspect_ratio=4.0/3.0;
    }''')
rep(p,'    core->reset(core);\n\t_setupMaps(core);','    core->reset(core);\n    azStarted=true;\n\t_setupMaps(core);')
rep(p,'\tcore->runFrame(core);\n\tunsigned width, height;','\tcore->runFrame(core);\n\tunsigned width, height;')
rep(p,'\tif (!skipFrame) {\n#if defined(COLOR_16_BIT) && defined(COLOR_5_6_5)','''    if (azActive) {
        if (!skipFrame) azPresent();
        else videoCallback(NULL,640,480,0);
    } else if (!skipFrame) {
#if defined(COLOR_16_BIT) && defined(COLOR_5_6_5)''')
rep(p,'\tcore->loadROM(core, rom);\n\tdeferredSetup = true;','''\tcore->loadROM(core, rom);
    azRequested=azActive=azStarted=false;
    if (core->platform(core)==mPLATFORM_GBA && core->supportsFeature(core,mCORE_FEATURE_OPENGL)) {
        memset(&azHW,0,sizeof(azHW));
        azHW.context_type=RETRO_HW_CONTEXT_OPENGLES3;
        azHW.version_major=3;
        azHW.version_minor=0;
        azHW.context_reset=azContextReset;
        azHW.context_destroy=azContextDestroy;
        azHW.bottom_left_origin=true;
        azRequested=true;
        if (!environCallback(RETRO_ENVIRONMENT_SET_HW_RENDER,&azHW)) azRequested=false;
    }
\tdeferredSetup = true;''')
rep(p,'\tmCoreConfigDeinit(&core->config);\n\tcore->deinit(core);','''    azContextDestroy();
    azRequested=azStarted=false;
\tmCoreConfigDeinit(&core->config);
\tcore->deinit(core);
    core=NULL;''')


# A dedicated background-only extension pass runs at the same batch boundary as
# upstream's renderer, sharing its VRAM and scanline palette textures. Never
# enlarge the emulated LCD, VRAM stride, sprite budget or timing.
import json
vertex=r"""#version 300 es
void main() {
    const vec4 rects[4]=vec4[4](vec4(0,0,640,80),vec4(0,400,640,480),vec4(0,80,80,400),vec4(560,80,640,400));
    const vec2 corners[6]=vec2[6](vec2(0,0),vec2(1,0),vec2(0,1),vec2(0,1),vec2(1,0),vec2(1,1));
    vec4 r=rects[gl_VertexID/6];
    vec2 p=mix(r.xy,r.zw,corners[gl_VertexID%6]);
    gl_Position=vec4(p/vec2(320.0,240.0)-1.0,0,1);
}
"""
fragment=r"""#version 300 es
precision highp float;
precision highp int;
precision highp usampler2D;
precision highp isampler2D;
uniform usampler2D vr;
uniform sampler2D pal;
uniform isampler2D lines;
uniform ivec4 cfg[4]; // char base in bytes, map base in bytes, size, flags
uniform ivec4 extra[4]; // enabledAtY, dmx, dmy, mosaic
uniform ivec4 disp; // mode, frame select, forced blank, backdrop blend flags
uniform ivec4 blend; // effect, a, b, brightness
uniform ivec2 batch;
uniform ivec2 mosaicSize;
out vec4 color;
int rd16(int a) {
    if(a<0 || a>=98304) return 0;
    int h=a>>1;
    return int(texelFetch(vr,ivec2(h&255,h>>8),0).r);
}
int rd8(int a) { return (rd16(a) >> (8*(a&1))) & 255; }
vec3 palette(int p,int y) { return texelFetch(pal,ivec2(p,y),0).rgb; }
bool sampleBg(int i,vec2 pos,int y,out vec3 c) {
    ivec4 b=cfg[i], e=extra[i];
    int mode=disp.x;
    if ((b.w&1)==0 || y<e.x) return false;
    bool text=mode==0 || (mode==1 && i<2);
    if (!text && (i<2 || (i==3 && mode!=2))) return false;
    if(mode>5) return false;
    ivec4 l=texelFetch(lines,ivec2(i,y),0);
    if(e.w!=0) {
        pos=floor(pos/vec2(mosaicSize))*vec2(mosaicSize);
    }
    if(text) {
        ivec2 q=ivec2(floor(pos))+ivec2(l.x&511,(l.x>>12)&511);
        q &= ivec2((b.z&1)!=0?511:255,(b.z&2)!=0?511:255);
        int page=(q.x>>8)+(q.y>>8)*((b.z&1)!=0?2:1);
        int m=(b.y+page*2048+2*(((q.y&255)>>3)*32+((q.x&255)>>3)))&65535;
        int t=rd16(m);
        int x=q.x&7, yy=q.y&7;
        if((t&1024)!=0)x=7-x;
        if((t&2048)!=0)yy=7-yy;
        int a=b.x+(t&1023)*((b.w&2)!=0?64:32)+yy*((b.w&2)!=0?8:4)+((b.w&2)!=0?x:x/2);
        if(a>=65536)return false;
        int n=rd8(a);
        if((b.w&2)==0) { n=(n>>((x&1)*4))&15; if(n!=0)n+=((t>>12)&15)*16; }
        if(n==0)return false;
        c=palette(n,y);return true;
    }
    // Each line uses the original live 8.8 origin and horizontal coefficients.
    // The vertical component extrapolates only outside the original LCD.
    ivec2 q=ivec2(floor((vec2(l.zw)+pos.x*vec2(l.xy)+(pos.y-float(y))*vec2(e.yz))/256.0));
    if(mode<=2) {
        int sz=128<<b.z;
        if((b.w&4)!=0)q &= ivec2(sz-1);
        if(any(lessThan(q,ivec2(0))) || any(greaterThanEqual(q,ivec2(sz))))return false;
        int m=(b.y+(q.y>>3)*(sz>>3)+(q.x>>3))&65535;
        int a=b.x+rd8(m)*64+(q.y&7)*8+(q.x&7);
        if(a>=65536)return false;
        int n=rd8(a);if(n==0)return false;
        c=palette(n,y);return true;
    }
    ivec2 sz=mode==5?ivec2(160,128):ivec2(240,160);
    if(any(lessThan(q,ivec2(0)))||any(greaterThanEqual(q,sz)))return false;
    int a=(mode!=3 && disp.y!=0?40960:0)+ (q.y*sz.x+q.x)*(mode==4?1:2);
    if(mode==4) {c=palette(rd8(a),y);return true;}
    int n=rd16(a);
    c=vec3(float(n&31),float((n>>5)&31),float((n>>10)&31))/31.0;
    return true;
}
void main() {
    // Native coordinates: the 240x160 image starts at (40,40).
    // For 2x HD, use subpixel phases 0 and 0.5, not a stretched image.
    vec2 p=(gl_FragCoord.xy-vec2(0.5))*0.5-vec2(40.0);
    int y=clamp(int(floor(p.y)),0,159);
    if(y<batch.x || y>batch.y)discard;
    if(p.x>=0.0 && p.x<240.0 && p.y>=0.0 && p.y<160.0)discard;
    if(disp.z!=0){color=vec4(1.0);return;}
    vec3 top=palette(0,y), second=top;
    int pri=16, pri2=17, flags=disp.w, flags2=0;
    for(int i=0;i<4;++i) {
        vec3 c;
        if(!sampleBg(i,p,y,c))continue;
        int f=cfg[i].w;
        int z=((f>>3)&3)*4+i;
        int t=(f>>5)&3;
        if(z<pri){second=top;pri2=pri;flags2=flags;top=c;pri=z;flags=t;}
        else if(z<pri2){second=c;pri2=z;flags2=t;}
    }
    if((flags&1)!=0) {
        if(blend.x==1 && (flags2&2)!=0)top=min(vec3(1),top*float(min(blend.y,16))/16.0+second*float(min(blend.z,16))/16.0);
        if(blend.x==2)top=mix(top,vec3(1),float(min(blend.w,16))/16.0);
        if(blend.x==3)top=mix(top,vec3(0),float(min(blend.w,16))/16.0);
    }
    color=vec4(top,1.0);
}
"""
def cstr(src):
    return "\n".join(json.dumps(l) for l in src.splitlines(keepends=True))
ext=r'''
/* RG DS experimental exterior GPU pass. The native compositor is untouched. */
static GLuint azExtFbo,azExtTex,azExtProgram,azExtVao,azExtLines;
static GLint azCfg,azExtra,azDisp,azBlend,azBatch,azMosaic;
GLuint azGbaExteriorFramebuffer(void) { return azExtProgram ? azExtFbo : 0; }
static GLuint azCompile(GLenum type,const char* source) {
    GLuint id=glCreateShader(type);
    GLint ok=0;
    glShaderSource(id,1,&source,NULL);
    glCompileShader(id);
    glGetShaderiv(id,GL_COMPILE_STATUS,&ok);
    if(!ok) {
        char log[2048]={0};
        glGetShaderInfoLog(id,sizeof(log),NULL,log);
        fprintf(stderr,"Azeez GBA exterior shader: %s\n",log);
        glDeleteShader(id);return 0;
    }
    return id;
}
static void azExteriorDeinit(void) {
    if(azExtProgram)glDeleteProgram(azExtProgram);
    if(azExtVao)glDeleteVertexArrays(1,&azExtVao);
    if(azExtFbo)glDeleteFramebuffers(1,&azExtFbo);
    if(azExtTex)glDeleteTextures(1,&azExtTex);
    if(azExtLines)glDeleteTextures(1,&azExtLines);
    azExtProgram=azExtVao=azExtFbo=azExtTex=azExtLines=0;
}
static void azExteriorInit(void) {
    const char* vsSource=
@VERT@;
    const char* fsSource=
@FRAG@;
    GLuint vs=azCompile(GL_VERTEX_SHADER,vsSource);
    GLuint fs=azCompile(GL_FRAGMENT_SHADER,fsSource);
    if(!vs||!fs){if(vs)glDeleteShader(vs);if(fs)glDeleteShader(fs);return;}
    azExtProgram=glCreateProgram();
    glAttachShader(azExtProgram,vs);glAttachShader(azExtProgram,fs);
    glLinkProgram(azExtProgram);
    glDeleteShader(vs);glDeleteShader(fs);
    GLint ok=0;
    glGetProgramiv(azExtProgram,GL_LINK_STATUS,&ok);
    if(!ok){azExteriorDeinit();return;}
    glUseProgram(azExtProgram);
    glUniform1i(glGetUniformLocation(azExtProgram,"vr"),0);
    glUniform1i(glGetUniformLocation(azExtProgram,"pal"),1);
    glUniform1i(glGetUniformLocation(azExtProgram,"lines"),2);
    azCfg=glGetUniformLocation(azExtProgram,"cfg[0]");
    azExtra=glGetUniformLocation(azExtProgram,"extra[0]");
    azDisp=glGetUniformLocation(azExtProgram,"disp");
    azBlend=glGetUniformLocation(azExtProgram,"blend");
    azBatch=glGetUniformLocation(azExtProgram,"batch");
    azMosaic=glGetUniformLocation(azExtProgram,"mosaicSize");
    glGenVertexArrays(1,&azExtVao);
    glGenTextures(1,&azExtLines);
    glBindTexture(GL_TEXTURE_2D,azExtLines);
    glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA32I,4,160);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glGenTextures(1,&azExtTex);
    glBindTexture(GL_TEXTURE_2D,azExtTex);
    glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,640,480);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glGenFramebuffers(1,&azExtFbo);
    glBindFramebuffer(GL_FRAMEBUFFER,azExtFbo);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,azExtTex,0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)azExteriorDeinit();
    glBindFramebuffer(GL_FRAMEBUFFER,0);
    glUseProgram(0);
}
static void azExteriorBatch(struct GBAVideoGLRenderer* r,int last) {
    int first=r->firstY;
    if(!azExtProgram||first<0||last<first||last>=160)return;
    GLint cfg[4][4], extra[4][4], rows[160][4][4];
    int mode=GBARegisterDISPCNTGetMode(r->dispcnt);
    for(int i=0;i<4;i++) {
        struct GBAVideoGLBackground* b=&r->bg[i];
        cfg[i][0]=b->charBase*2;cfg[i][1]=b->screenBase*2;cfg[i][2]=b->size;
        cfg[i][3]=(b->enabledAtY<=last && !r->d.disableBG[i]?1:0)|
            (b->multipalette?2:0)|(b->overflow?4:0)|(b->priority<<3)|(b->target1<<5)|(b->target2<<6);
        extra[i][0]=b->enabledAtY;extra[i][1]=b->affine.dmx;
        extra[i][2]=b->affine.dmy;extra[i][3]=b->mosaic;
        for(int y=first;y<=last;y++) {
            GLint* l=rows[y][i];
            if(mode==0 || (mode==1 && i<2)) {l[0]=b->scanlineOffset[y];l[1]=l[2]=l[3]=0;}
            else if(i>=2)memcpy(l,&b->scanlineAffine[y*4],sizeof(rows[0][0]));
            else l[0]=l[1]=l[2]=l[3]=0;
        }
    }
    glBindFramebuffer(GL_FRAMEBUFFER,azExtFbo);
    glDrawBuffers(1,(GLenum[]){GL_COLOR_ATTACHMENT0});
    glViewport(0,0,640,480);
    glEnable(GL_SCISSOR_TEST);
    glDisable(GL_DEPTH_TEST);glDisable(GL_STENCIL_TEST);glDisable(GL_BLEND);
    glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
    int bottom=first==0?0:80+first*2;
    int end=last==159?480:80+(last+1)*2;
    glScissor(0,bottom,640,end-bottom);
    glUseProgram(azExtProgram);glBindVertexArray(azExtVao);
    glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,r->vramTex);
    glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,r->paletteTex);
    glActiveTexture(GL_TEXTURE2);glBindTexture(GL_TEXTURE_2D,azExtLines);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,first,4,last-first+1,GL_RGBA_INTEGER,GL_INT,rows[first]);
    glUniform4iv(azCfg,4,&cfg[0][0]);glUniform4iv(azExtra,4,&extra[0][0]);
    glUniform4i(azDisp,mode,GBARegisterDISPCNTIsFrameSelect(r->dispcnt),GBARegisterDISPCNTIsForcedBlank(r->dispcnt),r->target1Bd|(r->target2Bd<<1));
    glUniform4i(azBlend,r->blendEffect,r->blda,r->bldb,r->bldy);
    glUniform2i(azBatch,first,last);
    glUniform2i(azMosaic,GBAMosaicControlGetBgH(r->mosaic)+1,GBAMosaicControlGetBgV(r->mosaic)+1);
    glDrawArrays(GL_TRIANGLES,0,24);
    glBindVertexArray(0);glActiveTexture(GL_TEXTURE0);
}
'''.replace("@VERT@",cstr(vertex)).replace("@FRAG@",cstr(fragment))
p="src/gba/renderers/gl.c"
rep(p,"void GBAVideoGLRendererInit(struct GBAVideoRenderer* renderer) {",ext+"\nvoid GBAVideoGLRendererInit(struct GBAVideoRenderer* renderer) {")
rep(p,"\tglDeleteShader(vs);\n\n\tGBAVideoGLRendererReset(renderer);","\tglDeleteShader(vs);\n\tazExteriorInit();\n\n\tGBAVideoGLRendererReset(renderer);")
rep(p,"void GBAVideoGLRendererDeinit(struct GBAVideoRenderer* renderer) {\n","void GBAVideoGLRendererDeinit(struct GBAVideoRenderer* renderer) {\n\tazExteriorDeinit();\n")
# Run before the next batch can upload changed VRAM. Preserve native rendering.
rep(p,"\tglRenderer->firstY = -1;\n}\n\nvoid GBAVideoGLRendererFinishFrame","\tazExteriorBatch(glRenderer,y);\n\tglRenderer->firstY = -1;\n}\n\nvoid GBAVideoGLRendererFinishFrame")
print("GPU exterior source applied: 320x240 logical canvas, 640x480 HD, modes 0-5; original LCD and timing preserved")
