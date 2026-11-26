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
rep("bananads/src/emu.h","    const uint32_t* bottom() const;",
    """    const uint32_t* bottom() const;
    const uint32_t* expanded_screen(bool bottom) const;""")
rep("bananads/src/emu.cpp",'    const long scale_cfg = cfg_.num("render.scale", 1);',
    '''    const long configured_scale = cfg_.num("render.scale", 1);
    const long scale_cfg = getenv("AZEEZ_EXPANDED_VIEWPORT") && configured_scale > 2 ? 2 : configured_scale;''')
rep("bananads/src/emu.cpp","void Emu::set_audio_rate(double hz) {",r"""
// Read-only exterior tilemap sampling. Native LCD composition is untouched.
const uint32_t* Emu::expanded_screen(bool bottom_screen) const {
    static thread_local uint32_t frame[2][640*480];
    auto& gpu=nds_->GPU;
    auto& bg=(bottom_screen != gpu.ScreenSwap) ? gpu.GPU2D_A : gpu.GPU2D_B;
    const uint32_t* src=bottom_screen ? bottom() : top();
    const int sc=scale();
    const unsigned dc=bg.DispCnt, mode=dc&7;
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
        if ((i==0 && !bg.Num && (dc&8)) || (i>=2 && mode!=0 &&
            !(mode==1 && i==2) && !(mode==3 && i==2))) continue;
        layers[layer_count++]={i,bc,((bc&0x1f00)<<3)+(bg.Num?0:((dc&0x38000000)>>11)),
            ((bc&0x003c)<<12)+(bg.Num?0:((dc&0x07000000)>>8))};
    }
    auto sample=[&](int x,int y)->uint32_t {
        unsigned c=backdrop;
        if (blank) return 0xffffffffu;
        for(unsigned k=0;k<layer_count;++k) {
            const auto& layer=layers[k];
            const int i=layer.i;
            const unsigned bc=layer.bc;
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
    auto* out=frame[bottom_screen?1:0];
    for(int y=0;y<240;y++) for(int x=0;x<320;x++) {
        if(x>=32 && x<288 && y>=24 && y<216 && src) {
            for(int j=0;j<2;j++) for(int i=0;i<2;i++) {
                int sx=((x-32)*2+i)*sc/2, sy=((y-24)*2+j)*sc/2;
                out[(y*2+j)*640+x*2+i]=src[sy*256*sc+sx];
            }
        } else {
            uint32_t p=sample(x-32,y-24);
            out[y*1280+x*2]=out[y*1280+x*2+1]=
            out[y*1280+640+x*2]=out[y*1280+640+x*2+1]=p;
        }
    }
    return out;
}

void Emu::set_audio_rate(double hz) {""")
p="bananads/src/frontend_kms.cpp"
rep(p,"    int fw = 0, fh = 0;", "    bool az_expanded = false;\n    int fw = 0, fh = 0;")
rep(p,"        fw = 256 * scale;\n        fh = 192 * scale;",
    """        az_expanded = getenv("AZEEZ_EXPANDED_VIEWPORT") && W == 640 && H == 480;
        fw = az_expanded ? 640 : 256 * scale;
        fh = az_expanded ? 480 : 192 * scale;""")
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
    """if (!dp.direct) dp.write(s, dp.az_expanded ? emu.expanded_screen(false) : emu.top(),
                                                        dp.az_expanded ? emu.expanded_screen(true) : emu.bottom());""")
rep(p,"if (!shown_ahead) dp.write(s, emu.top(), emu.bottom());",
    """if (!shown_ahead) dp.write(s, dp.az_expanded ? emu.expanded_screen(false) : emu.top(),
                                                               dp.az_expanded ? emu.expanded_screen(true) : emu.bottom());""")
rep(p,"                                int tx = std::clamp((int)((px - rx) * 256 / rw), 0, 255);",
    """                                if (dp.az_expanded) {
                                    rx=64; ry=48; rw=512; rh=384;
                                    if (px<rx || py<ry || px>=rx+rw || py>=ry+rh) {
                                        in_touch=-1; d.was=d.down; continue;
                                    }
                                }
                                int tx = std::clamp((int)((px - rx) * 256 / rw), 0, 255);""")
print("DS centered expanded viewport source integrated")
