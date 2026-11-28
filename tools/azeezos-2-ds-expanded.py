#!/usr/bin/env python3
"""DS expanded text backgrounds and exact centered RG DS scanout."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
def rep(rel,a,b):
    p=root/rel
    s=p.read_text()
    if b in s: return
    if s.count(a)!=1: raise SystemExit("DS viewport anchor: "+rel+" "+repr(a[:80]))
    p.write_text(s.replace(a,b,1))
# Keep the GPU's internal methods private; expose one narrowly scoped read-only accessor.
rep("melonds/src/GPU.h","private:\n    void ResetVRAMCache() noexcept;",
    """    u16 ReadExpandedBGPalette(bool engine_b, u32 addr) const noexcept
    {
        return engine_b ? ReadVRAM_BBGExtPal<u16>(addr) : ReadVRAM_ABGExtPal<u16>(addr);
    }

private:
    void ResetVRAMCache() noexcept;""")

# Capture exterior at the actual pre-draw boundary, before HBlank DMA can
# replace tilemaps, scroll, palettes and priority. Keep only the winning text
# pixel above and below BG0's 3D layer; composite the existing 3D raster at
# presentation, without reading guest VRAM after the frame.
rep("melonds/src/GPU2D.h","    u32 Num;\n    bool Enabled;",r"""    void CaptureExpandedLine(u32 line);
    u16 ExpandedUnder[240][320]{};
    u16 ExpandedOver[240][320]{};
    u8 Expanded3D[240]{};
    u8 ExpandedValid[240]{};
    u32 Num;
    bool Enabled;""")
rep("melonds/src/GPU.cpp","            Rend->DrawScanline(line);",r"""        {
            static const bool azCapture = getenv("AZEEZ_EXPANDED_VIEWPORT") != nullptr;
            if (azCapture) {
                GPU2D_A.CaptureExpandedLine(line);
                GPU2D_B.CaptureExpandedLine(line);
            }
            Rend->DrawScanline(line);
        }""")
rep("melonds/src/GPU2D.cpp","void GPU2D::Reset()\n{",r"""void GPU2D::CaptureExpandedLine(u32 line)
{
    if (line>=192) return;
    if (line==0) memset(ExpandedValid,0,sizeof ExpandedValid);
    const unsigned dc=DispCnt, mode=dc&7;
    const bool white=ForcedBlank || (Enabled && ((dc>>16)&3)==0) || (!Enabled && Num);
    const bool active=Enabled && !ForcedBlank && ((dc>>16)&3)==1 && mode<6;
    const bool has3d=active && !Num && (dc&8) && (LayerEnable&1);
    const u16 backdrop=white?0x7fff:(!Enabled?0:GPU.ReadPalette<u16>(Num*0x400)&0x7fff);
    struct Layer { unsigned i,bc,map,chr; bool above; };
    Layer layers[4]; unsigned count=0;
    bool above=false;
    if(active) for(int pr=3;pr>=0;--pr) for(int i=3;i>=0;--i) {
        unsigned bc=BGCnt[i];
        if (!(LayerEnable&(1u<<i)) || (bc&3)!=(unsigned)pr) continue;
        if(i==0 && has3d) { above=true; continue; }
        if(i==3 && mode!=0) continue;
        if(i==2 && mode!=0 && mode!=1 && mode!=3) continue;
        layers[count++]={(unsigned)i,bc,((bc&0x1f00)<<3)+(Num?0:((dc&0x38000000)>>11)),
            ((bc&0x003c)<<12)+(Num?0:((dc&0x07000000)>>8)),above};
    }
    auto rd8=[&](unsigned a)->u8 {return Num?GPU.ReadVRAM_BBG<u8>(a):GPU.ReadVRAM_ABG<u8>(a);};
    auto rd16=[&](unsigned a)->u16 {return Num?GPU.ReadVRAM_BBG<u16>(a):GPU.ReadVRAM_ABG<u16>(a);};
    const int first=line==0?0:(int)line+24, end=line==191?240:(int)line+25;
    for(int row=first;row<end;row++) {
        bool sideOnly=row>=24 && row<216;
        for(int span=0;span<(sideOnly?2:1);span++) {
            int left=sideOnly&&span?288:0,right=sideOnly&&!span?32:320;
            for(int col=left;col<right;col++) {
                u16 under=backdrop, over=0;
                for(unsigned k=0;k<count;k++) {
                    const auto& l=layers[k]; unsigned bc=l.bc,i=l.i;
                    unsigned x=(unsigned)(col-32+BGXPos[i])&((bc&0x4000)?511:255);
                    unsigned y=(unsigned)(row-24+BGYPos[i])&((bc&0x8000)?511:255);
                    unsigned block=(x>>8)+((y>>8)*((bc&0x4000)?2:1));
                    unsigned tile=rd16(l.map+block*2048+((y&255)>>3)*64+((x&255)>>3)*2);
                    unsigned tx=x&7,ty=y&7,n;u16 c;
                    if(tile&0x400)tx=7-tx;
                    if(tile&0x800)ty=7-ty;
                    if(bc&0x80) {
                        n=rd8(l.chr+(tile&1023)*64+ty*8+tx);
                        if(!n)continue;
                        if(dc&(1u<<30)) {
                            unsigned slot=(i<2&&(bc&0x2000))?i+2:i;
                            c=GPU.ReadExpandedBGPalette(Num!=0,slot*8192+(tile>>12)*512+n*2);
                        } else c=GPU.ReadPalette<u16>(Num*0x400+n*2);
                    } else {
                        n=(rd8(l.chr+(tile&1023)*32+ty*4+tx/2)>>((tx&1)*4))&15;
                        if(!n)continue;
                        c=GPU.ReadPalette<u16>(Num*0x400+((tile>>12)*16+n)*2);
                    }
                    if(l.above)over=(c&0x7fff)|0x8000;
                    else under=c&0x7fff;
                }
                ExpandedUnder[row][col]=under;
                ExpandedOver[row][col]=over;
            }
        }
        Expanded3D[row]=has3d;
        ExpandedValid[row]=1;
    }
}

void GPU2D::Reset()
{
    memset(ExpandedValid,0,sizeof ExpandedValid);""")

rep("bananads/src/emu.h","    const uint32_t* bottom() const;",
    """    const uint32_t* bottom() const;
    const uint32_t* expanded_screen(bool bottom, uint32_t* dest=nullptr, int pitch=640) const;""")
# Keep the upstream 1x-4x rasterizer selection intact. Presentation is independent.
rep("bananads/src/emu.cpp","void Emu::set_audio_rate(double hz) {",r"""
// Read-only exterior tilemap sampling. Native LCD composition is untouched.
const uint32_t* Emu::expanded_screen(bool bottom_screen, uint32_t* dest, int pitch) const {
    static thread_local uint32_t frame[2][640*480];
    auto& gpu=nds_->GPU;
    auto& bg=(bottom_screen != gpu.ScreenSwap) ? gpu.GPU2D_A : gpu.GPU2D_B;
    const uint32_t* src=bottom_screen ? bottom() : top();
    const int sc=scale();
    const unsigned dc=bg.DispCnt, mode=dc&7;
    int sc3=1;
    const uint32_t* scene=nullptr;
    if (!bg.Num)
        scene=gpu.GetRenderer().Expanded3DFrame(sc3);
    auto read8=[&](unsigned a)->uint8_t {
        return bg.Num ? gpu.ReadVRAM_BBG<uint8_t>(a) : gpu.ReadVRAM_ABG<uint8_t>(a);
    };
    auto read16=[&](unsigned a)->uint16_t {
        return bg.Num ? gpu.ReadVRAM_BBG<uint16_t>(a) : gpu.ReadVRAM_ABG<uint16_t>(a);
    };
    auto rgb=[](unsigned c)->uint32_t {
        unsigned r=c&31,g=(c>>5)&31,b=(c>>10)&31;
        return 0xff000000u|((r*255/31)<<16)|((g*255/31)<<8)|(b*255/31);
    };
    // Build the active text-layer order once per output frame, not per
    // exterior pixel. Keep the original back-to-front priority/tie order.
    struct ExpandedLayer { int i; unsigned bc, map, chr; };
    ExpandedLayer layers[4];
    unsigned layer_count=0;
    const bool blank=(dc&0x80) || ((dc>>16)&3)==0;
    const bool text_active=!blank && ((dc>>16)&3)==1 && bg.Enabled && mode<6;
    const unsigned backdrop=gpu.ReadPalette<uint16_t>(bg.Num*0x400);
    if (text_active) for(int pr=3;pr>=0;--pr) for(int i=3;i>=0;--i) {
        unsigned bc=bg.BGCnt[i];
        if (!(dc&(0x100u<<i)) || (bc&3)!=(unsigned)pr) continue;
        if (i==0 && !bg.Num && (dc&8)) {
            if(scene) layers[layer_count++]={i,bc,0,0};
            continue;
        }
        if ((i>=2 && mode!=0 &&
            !(mode==1 && i==2) && !(mode==3 && i==2))) continue;
        layers[layer_count++]={i,bc,((bc&0x1f00)<<3)+(bg.Num?0:((dc&0x38000000)>>11)),
            ((bc&0x003c)<<12)+(bg.Num?0:((dc&0x07000000)>>8))};
    }
    auto sample=[&](int x,int y,unsigned dx,unsigned dy)->uint32_t {
        const unsigned row=(unsigned)(y+24), col=(unsigned)(x+32);
        if(row<240 && col<320 && bg.ExpandedValid[row]) {
            unsigned c=bg.ExpandedUnder[row][col], over=bg.ExpandedOver[row][col];
            if(over&0x8000)return rgb(over&0x7fff);
            if(scene && bg.Expanded3D[row]) {
                unsigned idx=sc3==2 ? (row*2+dy)*640+dx*320+col : row*320+col;
                uint32_t p=scene[idx]; unsigned a=(p>>24)&31;
                if(a) {
                    unsigned r=(p&63)>>1,g=((p>>8)&63)>>1,b=((p>>16)&63)>>1;
                    if(a<31) {
                        r=(r*(a+1)+(c&31)*(31-a))>>5;
                        g=(g*(a+1)+((c>>5)&31)*(31-a))>>5;
                        b=(b*(a+1)+((c>>10)&31)*(31-a))>>5;
                    }
                    c=r|(g<<5)|(b<<10);
                }
            }
            return rgb(c);
        }
        unsigned c=backdrop;
        if (blank) return 0xffffffffu;
        for(unsigned k=0;k<layer_count;++k) {
            const auto& layer=layers[k];
            const int i=layer.i;
            const unsigned bc=layer.bc;
            if(i==0 && !bg.Num && (dc&8) && scene) {
                // Native and HD expanded rasters share the same camera.
                // HD is stored in quarter rows: each row's even pixels, then odd.
                const unsigned sx=(unsigned)(x+32), sy=(unsigned)(y+24);
                if(sx<320 && sy<240) {
                    const unsigned idx=sc3==2 ? (sy*2+dy)*640+dx*320+sx : sy*320+sx;
                    uint32_t p=scene[idx];
                    unsigned a=(p>>24)&31;
                    if(a) {
                        unsigned r=((p&63)>>1), g=(((p>>8)&63)>>1), b=(((p>>16)&63)>>1);
                        if(a<31) {
                            r=(r*(a+1)+(c&31)*(31-a))>>5;
                            g=(g*(a+1)+((c>>5)&31)*(31-a))>>5;
                            b=(b*(a+1)+((c>>10)&31)*(31-a))>>5;
                        }
                        c=r|(g<<5)|(b<<10);
                    }
                }
                continue;
            }
            unsigned xx=(unsigned)(x+bg.BGXPos[i]) & ((bc&0x4000)?511:255);
            unsigned yy=(unsigned)(y+bg.BGYPos[i]) & ((bc&0x8000)?511:255);
            unsigned map=layer.map, chr=layer.chr;
            unsigned block=(xx>>8)+((yy>>8)*((bc&0x4000)?2:1));
            unsigned tile=read16(map+block*2048+((yy&255)>>3)*64+((xx&255)>>3)*2);
            unsigned tx=xx&7,ty=yy&7;
            if(tile&0x400) tx=7-tx;
            if(tile&0x800) ty=7-ty;
            unsigned n;
            if(bc&0x80) {
                n=read8(chr+(tile&1023)*64+ty*8+tx);
                if(!n) continue;
                if(dc&(1u<<30)) {
                    unsigned slot=(i<2 && (bc&0x2000))?i+2:i;
                    unsigned off=slot*8192+(tile>>12)*512+n*2;
                    c=gpu.ReadExpandedBGPalette(bg.Num!=0,off);
                } else c=gpu.ReadPalette<uint16_t>(bg.Num*0x400+n*2);
            } else {
                n=(read8(chr+(tile&1023)*32+ty*4+tx/2)>>((tx&1)*4))&15;
                if(!n) continue;
                c=gpu.ReadPalette<uint16_t>(bg.Num*0x400+((tile>>12)*16+n)*2);
            }
        }
        return rgb(c);
    };
    auto* out=dest?dest:frame[bottom_screen?1:0];
    if(!dest) pitch=640;
    for(int y=0;y<240;y++) {
        uint32_t* a=out+y*2*pitch;
        uint32_t* b=a+pitch;
        bool center=y>=24 && y<216 && src;
        if(center) {
            if(sc==2) {
                memcpy(a+64,src+(y-24)*2*512,512*sizeof(uint32_t));
                memcpy(b+64,src+((y-24)*2+1)*512,512*sizeof(uint32_t));
            } else if(sc>=3) {
                // Select two subpixels WITHIN each native DS pixel. 2D
                // elements keep exactly two output pixels per native pixel;
                // higher-resolution 3D retains its independent samples.
                const int lo=sc/4, hi=(3*sc)/4;
                const uint32_t* ra=src+((y-24)*sc+lo)*256*sc;
                const uint32_t* rb=src+((y-24)*sc+hi)*256*sc;
                for(int i=0;i<256;i++) {
                    a[64+i*2]=ra[i*sc+lo]; a[65+i*2]=ra[i*sc+hi];
                    b[64+i*2]=rb[i*sc+lo]; b[65+i*2]=rb[i*sc+hi];
                }
            } else {
                const uint32_t* row=src+(y-24)*256;
                for(int i=0;i<256;i++) a[64+i*2]=a[65+i*2]=b[64+i*2]=b[65+i*2]=row[i];
            }
        }
        for(int span=0;span<(center?2:1);span++) {
            int first=center && span?288:0;
            int last=center && !span?32:320;
            if(!bg.ExpandedValid[y] && (blank || layer_count==0)) {
                const uint32_t color=blank?0xffffffffu:rgb(backdrop);
                for(int i=first*2;i<last*2;++i) a[i]=b[i]=color;
                continue;
            }
            for(int i=first;i<last;i++) {
                    if(scene && sc3==2) {
                    a[i*2]=sample(i-32,y-24,0,0);
                    a[i*2+1]=sample(i-32,y-24,1,0);
                    b[i*2]=sample(i-32,y-24,0,1);
                    b[i*2+1]=sample(i-32,y-24,1,1);
                } else {
                    const uint32_t p=sample(i-32,y-24,0,0);
                    a[i*2]=a[i*2+1]=b[i*2]=b[i*2+1]=p;
                }
            }
        }
    }
    return out;
}

void Emu::set_audio_rate(double hz) {""")
p="bananads/src/frontend_kms.cpp"
rep(p,"    int fw = 0, fh = 0;", "    bool az_expanded = false;\n    int fw = 0, fh = 0;")
rep(p,"        fw = 256 * scale;\n        fh = 192 * scale;",
    """        az_expanded = getenv("AZEEZ_EXPANDED_VIEWPORT") && W == 640 && H == 480;
        if (getenv("AZEEZ_EXPANDED_VIEWPORT") && !az_expanded)
            Log(LogLevel::Warn, "[azeez] exact DS canvas requested but panel is %dx%d, not 640x480\\n", W,H);
        fw = az_expanded ? 640 : 256 * scale;
        fh = az_expanded ? 480 : 192 * scale;
        Log(LogLevel::Info, "[azeez] DS presentation: %dx%d, internal 3D %dx, exact canvas=%s\\n",
            W,H,scale,az_expanded ? "on" : "off");""")
rep(p,"        if (!hw) return false;\n        for (auto& pb : buf)",
    """        if (!hw || az_expanded) return false;
        for (auto& pb : buf)""")
rep(p,"        const std::string sh = cfg.str(\"kms.shader\", \"none\");",
    """        const std::string sh = dp.az_expanded ? "none" : cfg.str("kms.shader", "none");""")
# Do not let a menu shader turn exact scanout into a second scaling pass.
rep(p,"        std::string want;\n        bool asked = false;",
    """        if (az_expanded) return;
        std::string want;
        bool asked = false;""")
rep(p,"if (!dp.direct) dp.write(s, emu.top(), emu.bottom());",
    """if (!dp.direct) dp.write_game(s, emu);""")
rep(p,"if (!shown_ahead) dp.write(s, emu.top(), emu.bottom());",
    """if (!shown_ahead) dp.write_game(s, emu);""")
rep(p,"                                int tx = std::clamp((int)((px - rx) * 256 / rw), 0, 255);",
    """                                if (dp.az_expanded) {
                                    rx=64; ry=48; rw=512; rh=384;
                                    if (px<rx || py<ry || px>=rx+rw || py>=ry+rh) {
                                        in_touch=-1; d.was=d.down; continue;
                                    }
                                }
                                int tx = std::clamp((int)((px - rx) * 256 / rw), 0, 255);""")
print("DS centered expanded viewport source integrated")

rep("bananads/src/frontend_kms.cpp","    void write(int s, const uint32_t* top, const uint32_t* bot) {",'''    void write_game(int s, Emu& emu) {
        if(!az_expanded) { write(s,emu.top(),emu.bottom()); return; }
        if(!hw) { write(s,emu.expanded_screen(false),emu.expanded_screen(true)); return; }
        for(int i=0;i<2;i++) {
            Buf& b=buf[i][s];
            if(touched) touched(b.map);
            emu.expanded_screen(i!=0,(uint32_t*)b.map,(int)b.pitch/4);
        }
    }
    void write(int s, const uint32_t* top, const uint32_t* bot) {''')
print("DS: row copies, exterior-only sampling, one KMS write instead of two")

# Expanded camera: dedicated native 320x240 raster (15 bins of 16 lines).
# Original 256x192 and conventional higher scales remain available with wide mode off.
rep("melonds/src/GPU.h","    virtual bool NeedsShaderCompile() { return false; }",'''    virtual const u32* Expanded3DFrame(int& scale) const { scale=1; return nullptr; }
    virtual bool NeedsShaderCompile() { return false; }''')
rep("melonds/src/GPU3D.cpp","    // clipping\n",'''    // Each native viewport retains its original pixel mapping inside the
    // centered canvas. Extend only the edges touching the native LCD.
    static const bool azWide=getenv("AZEEZ_DS_WIDE3D")!=nullptr;
    const int azL=azWide && Viewport[0]==0 ? 32:0;
    const int azR=azWide && Viewport[0]+Viewport[4]==256 ? 32:0;
    const int azT=azWide && Viewport[3]==0 ? 24:0;
    const int azB=azWide && Viewport[3]+Viewport[5]==192 ? 24:0;
    const int azW=Viewport[4]+azL+azR, azH=Viewport[5]+azT+azB;
    const int azX=Viewport[0]+32-azL, azY=Viewport[3]+24-azT;
    if(azWide && azW>0 && azH>0) for(int i=clipstart;i<nverts;i++) {
        auto& p=clippedvertices[i].Position;
        // Signed arithmetic; y is inverted in the viewport transform.
        p[0]=(s32)(((s64)p[0]*Viewport[4]+(s64)p[3]*(azL-azR))/azW);
        p[1]=(s32)(((s64)p[1]*Viewport[5]+(s64)p[3]*(azB-azT))/azH);
    }
    // clipping
''')
rep("bananads/src/gengis_renderer.h","    int Scale() const { return Scale_; }",'''    int Scale() const { return Scale_; }
    const uint32_t* ExpandedFrame(int& scale) const {
        scale=Scale_;
        return Wide3D && !GPU3D.AbortFrame && !GPU3D.RenderXPos ? Presented : nullptr;
    }''')
rep("bananads/src/gengis_renderer.h","    alignas(16) uint32_t Scrolled[16][GX_W];",'''    alignas(16) uint32_t Scrolled[16][GX_W];
    bool Wide3D=false;
    const uint32_t* Presented=nullptr;''')
rep("bananads/src/gengis_renderer.h","    void SetRenderSettings(melonDS::RendererSettings&) override {}",'''    const melonDS::u32* Expanded3DFrame(int& scale) const override {
        return static_cast<GengisRenderer3D*>(this->Rend3D.get())->ExpandedFrame(scale);
    }
    void SetRenderSettings(melonDS::RendererSettings&) override {}''')
rep("bananads/src/gengis_renderer.cpp","    gx_zva = Zva;",'''    Wide3D=getenv("AZEEZ_DS_WIDE3D")!=nullptr && Scale_<=2;
    gx_zva = Zva;''')
rep("bananads/src/gengis_renderer.cpp","    WaitAll();  // the last frame's bins read VRAM and the polygons: done before either changes",'''    WaitAll();  // the last frame's bins read VRAM and the polygons: done before either changes
    if(Wide3D) Presented=Out;''')
rep("bananads/src/gengis_renderer.cpp","    Textures.clear();\n    Stale.clear();",'''    Presented=nullptr;
    Textures.clear();
    Stale.clear();''')
# Dedicated raster variant: separate thread-local scratch, shared tables.
rep("bananads/gengis/gx.h","void gx_render_bin(const gx_frame *f, unsigned bin, uint32_t *out);",
    """void gx_render_bin(const gx_frame *f, unsigned bin, uint32_t *out);
void gxwide_render_bin(const gx_frame *f, unsigned bin, uint32_t *out);
void gxwide2_render_bin(const gx_frame *f, unsigned bin, uint32_t *out);""")
rep("bananads/gengis/gx.c","#define GX_W (256 * GX_SCALE)\n#define GX_H (192 * GX_SCALE)",
    """#ifdef GX_NATIVE_WIDE
#define GX_W (320 * GX_SCALE)
#define GX_H (240 * GX_SCALE)
#undef gx_render_bin
#if GX_SCALE == 2
#define gx_render_bin gxwide2_render_bin
#else
#define gx_render_bin gxwide_render_bin
#endif
#else
#define GX_W (256 * GX_SCALE)
#define GX_H (192 * GX_SCALE)
#endif""")
rep("bananads/gengis/gx.c",'_Static_assert(GX_H / GX_BL == (192 / 16) * GX_SUB, "the bins");',
    '''#ifdef GX_NATIVE_WIDE
_Static_assert(GX_H / GX_BL == 15 && GX_W == 320*GX_SCALE && GX_SUB == 1, "expanded bins");
#else
_Static_assert(GX_H / GX_BL == (192 / 16) * GX_SUB, "the bins");
#endif''')
for marker in ("uintptr_t ds_base;", "uint8_t *gx_sys, *gx_geom;", "int gx_lazy;", "/* fused.c's stage-by-stage path"):
    rep("bananads/gengis/gx.c","#if GX_SCALE == 1\n"+marker,
        "#if GX_SCALE == 1 && !defined(GX_NATIVE_WIDE)\n"+marker)
rep("bananads/gengis/gx.c","const unsigned row = ((unsigned)(yl / GX_SCALE + f->rear_y) & 0xff) << 8;",
    """#ifdef GX_NATIVE_WIDE
        const unsigned row = ((unsigned)(yl / GX_SCALE - 24 + f->rear_y) & 0xff) << 8;
#else
        const unsigned row = ((unsigned)(yl / GX_SCALE + f->rear_y) & 0xff) << 8;
#endif""")
rep("bananads/gengis/gx.c","const unsigned ix = row + ((f->rear_x + i / GX_SCALE) & 0xff);",
    """#ifdef GX_NATIVE_WIDE
            const unsigned ix = row + ((f->rear_x + i / GX_SCALE - 32) & 0xff);
#else
            const unsigned ix = row + ((f->rear_x + i / GX_SCALE) & 0xff);
#endif""")
wide=root/"bananads/gengis/gxwide.c"
wide.write_text('#define GX_NATIVE_WIDE 1\n#include "gx.c"\n')
(root/"bananads/gengis/gxwide2.c").write_text('#define GX_NATIVE_WIDE 1\n#define GX_SCALE 2\n#include "gx.c"\n')
rep("bananads/CMakeLists.txt","add_library(gengis STATIC ${GX}/gx.c",
    "add_library(gengis STATIC ${GX}/gxwide.c ${GX}/gxwide2.c ${GX}/gx.c")
# Keep the game's viewport registers untouched. Map clip-space to expanded raster.
rep("melonds/src/GPU3D.cpp","            vtx->HiresPosition[0] = posX & 0x1FFF;\n            vtx->HiresPosition[1] = posY & 0xFFF;",
    """            if (azWide) {
                // Apply the matching expanded viewport with the offset once.
                // The original LCD center (128,96) maps to (160,120).
                posX = (u32)((((s64)vtx->Position[0]+w)*azW*16)/((s64)w*2)+azX*16);
                posY = (u32)(((-(s64)vtx->Position[1]+w)*azH*16)/((s64)w*2)+azY*16);
                vtx->HiresPosition[0] = posX;
                vtx->HiresPosition[1] = posY;
                vtx->FinalPosition[0] = posX >> 4;
                vtx->FinalPosition[1] = posY >> 4;
            } else {
                vtx->HiresPosition[0] = posX & 0x1FFF;
                vtx->HiresPosition[1] = posY & 0xFFF;
            }""")
# BananaDS has both synchronous and worker-thread polygon finalizers.
# Adjust both, keeping the worker's scope independent of SubmitPolygonBody.
p=root/"melonds/src/GPU3D.cpp"
src=p.read_text()
for old,new in (
    ("    s32 ytop = 192, ybot = 0;\n    s32 xtop = 256, xbot = 0;",
     "    const bool azBoundsWide=getenv(\"AZEEZ_DS_WIDE3D\")!=nullptr;\n    s32 ytop = azBoundsWide ? 240 : 192, ybot = 0;\n    s32 xtop = azBoundsWide ? 320 : 256, xbot = 0;"),
    ("    if (ybot > 192) poly->Degenerate = true;",
     "    if (ybot > (azBoundsWide ? 240 : 192)) poly->Degenerate = true;")
):
    if src.count(old)!=2: raise SystemExit("DS sync/worker bounds anchor mismatch: "+old)
    src=src.replace(old,new)
p.write_text(src)
# Expanded mode uses 1x the new canvas, not conventional supersampling.
rep("bananads/src/emu.cpp","    const int scale = scale_cfg >= 2 && scale_cfg <= 4 ? (int)scale_cfg : 1;",
    """    const bool native_wide = getenv("AZEEZ_DS_WIDE3D") != nullptr;
    const bool override_scale = getenv("BANANADS_RENDER_SCALE") != nullptr;
    const int target = override_scale ? (scale_cfg >= 2 ? 2 : 1) : (cfg_.num("render.expanded_scale",1)==2 ? 2 : 1);
    const int scale = native_wide ? (banana2d ? target : 1) : (scale_cfg >= 2 && scale_cfg <= 4 ? (int)scale_cfg : 1);
    if (native_wide) Log(LogLevel::Info, "[azeez] expanded 3D raster: %dx%d\\n",320*scale,240*scale);""")
rep("bananads/src/emu.cpp",'    const bool banana2d = cfg_.str("render.2d", "banana") == "banana";',
    '    const bool banana2d = getenv("AZEEZ_DS_WIDE3D") != nullptr || cfg_.str("render.2d", "banana") == "banana";')
rep("bananads/src/emu.cpp",'    if (cfg_.str("render.renderer", "gengis") == "gengis") {',
    '    if (native_wide || cfg_.str("render.renderer", "gengis") == "gengis") {')
h="bananads/src/gengis_renderer.h"
p="bananads/src/gengis_renderer.cpp"
rep(h,"    std::vector<uint8_t> BinKey[GX_NBINS], NewKey[GX_NBINS];\n    bool BinReuse[GX_NBINS] = {};",
    """    std::vector<uint8_t> BinKey[15], NewKey[15];
    bool BinReuse[15] = {};""")
rep(h,"    size_t OutWords() const { return (size_t)GX_H * GX_W * Scale_ * Scale_; }",
    """    unsigned BinCount() const { return Wide3D ? 15 : GX_NBINS; }
    size_t UnitWords() const { return Wide3D ? (size_t)320*16*Scale_*Scale_ : (size_t)GX_BL*GX_W*Scale_*Scale_/Sub; }
    size_t OutWords() const { return Wide3D ? (size_t)320*240*Scale_*Scale_ : (size_t)GX_H*GX_W*Scale_*Scale_; }""")
rep(h,"        if (line >= GX_H) line = GX_H - 1;\n        if (Scale_ >= 3)",
    """        if (line >= GX_H) line = GX_H - 1;
        if (Wide3D) return Out + ((line+24)*Scale_+q/Scale_)*320*Scale_+(q%Scale_)*320+32;
        if (Scale_ >= 3)""")
rep(p,"    NU = GX_NBINS * Sub;","    NU = BinCount() * Sub;")
rep(p,"        if (Scale_ == 2)\n            for (unsigned k = 1; k < n; k++)",
    """        if (Wide3D) {
            for (unsigned k=1;k<n;k++) {
                const unsigned vi=(p->VTop+k)%n;
                if (p->Vertices[vi]->HiresPosition[1] < p->Vertices[top]->HiresPosition[1]) top=vi;
            }
        } else if (Scale_ == 2)
            for (unsigned k = 1; k < n; k++)""")
for axis,idx in (("x",0),("y",1)):
    anchor=f"const uint16_t {axis} = (uint16_t)(Scale_ == 2 ?"
    rep(p,anchor,f"const uint16_t {axis} = (uint16_t)(Wide3D ? (v->HiresPosition[{idx}]*Scale_) >> 4 : Scale_ == 2 ?")
rep(p,"for (unsigned b = 0; b < GX_NBINS; b++) { BinKey[b].clear(); BinReuse[b] = false; }",
    "for (unsigned b = 0; b < BinCount(); b++) { BinKey[b].clear(); BinReuse[b] = false; }")
rep(p,"for (unsigned b = 0; b < GX_NBINS; b++) any |= BinReuse[b];",
    "for (unsigned b = 0; b < BinCount(); b++) any |= BinReuse[b];")
rep(p,"const unsigned BL = GX_BL * Scale_, H = GX_H * Scale_;",
    "const unsigned BL = GX_BL * Scale_, H = Wide3D ? 240*Scale_ : GX_H * Scale_;")
rep(p,"for (unsigned b = 0; b < GX_NBINS; b++) {\n        const unsigned hy0",
    "for (unsigned b = 0; b < BinCount(); b++) {\n        const unsigned hy0")
rep(p,"void GengisRenderer3D::RenderBin(unsigned b, uint32_t* dst) {",
    """void GengisRenderer3D::RenderBin(unsigned b, uint32_t* dst) {
    if (Wide3D) { (Scale_==2 ? gxwide2_render_bin : gxwide_render_bin)(&Frame,b,dst); return; }""")
rep(p,"const size_t un = (size_t)GX_BL * GX_W * Scale_ * Scale_ / Sub;",
    "const size_t un = UnitWords();")
rep(p,"const unsigned bin = (unsigned)line / (GX_BL / Sub);\n    auto drawn",
    "const unsigned bin = (unsigned)(line+(Wide3D?24:0)) / (GX_BL / Sub);\n    auto drawn")
rep(p,"    if (line < GX_H) WaitBin((unsigned)line / (GX_BL / Sub));",
    "    if (line < GX_H) WaitBin((unsigned)(line+(Wide3D?24:0)) / (GX_BL / Sub));")
print("Expanded 320x240 and 640x480 raster variants integrated: 15 bins, exact centered crop")

# Regression test for the viewport transform (exact rational coordinates).
from fractions import Fraction as F
for start,extent,limit,pad in [(0,256,256,32),(0,192,192,24),(0,256,256,32),(0,160,192,24),(32,224,256,32),(16,128,256,32)]:
    a=pad if start==0 else 0
    b=pad if start+extent==limit else 0
    for q in (-1,0,1):
        transformed=F(q*extent+a-b,extent+a+b)
        mapped=(transformed+1)*F(extent+a+b,2)+start+pad-a
        assert mapped == F(q+1,2)*extent+start+pad
print("PASS: expanded viewport retains exact native center and independent edge padding")
