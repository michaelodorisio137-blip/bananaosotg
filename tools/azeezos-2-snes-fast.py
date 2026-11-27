#!/usr/bin/env python3
"""Fast native SNES viewport: preserve the real raster and extend tile backgrounds."""
from pathlib import Path
import sys, shutil
mode, root=sys.argv[1],Path(sys.argv[2])
def rep(path,old,new):
    p=root/path
    s=p.read_text()
    if new in s:return
    if s.count(old)!=1:raise SystemExit("Fast SNES anchor mismatch: "+path+" "+repr(old[:80]))
    p.write_text(s.replace(old,new,1))
if mode=="--build":
    pkg=root/"buildroot/package/libretro-bananasnes"
    shutil.copyfile(__file__,pkg/"azeezos-2-snes-fast.py")
    rep("buildroot/package/libretro-bananasnes/libretro-bananasnes.mk",
        "define LIBRETRO_BANANASNES_BUILD_CMDS",
        "define LIBRETRO_BANANASNES_BUILD_CMDS\n\tpython3 $(BR2_EXTERNAL_BANANA_PATH)/package/libretro-bananasnes/azeezos-2-snes-fast.py --source $(@D)")
    sys.exit(0)
if mode!="--source":raise SystemExit("invalid mode")
rep("gfx.cpp","void S9xUpdateScreen (void)\n{",'''/* Presentation-only background extension; no changes to PPU state,
 * sprite limits, CPU timing or the central hardware-rendered raster. */
#include <stdlib.h>
uint16 az_snes_canvas[320*240];
bool az_snes_integer(void) { return getenv("AZEEZ_EXPANDED_VIEWPORT") != NULL; }
static unsigned az_snes_vram(unsigned addr) { return Memory.VRAM[addr & 0xffff]; }
static uint16 az_snes_bg(int x,int y,int line)
{
    unsigned best=0, color=0;
    if (PPU.ForcedBlanking) return 0;
    const int mode=PPU.BGMode;
    // Modes with offset-per-tile or affine transforms need dedicated handling.
    if (mode!=0 && mode!=1 && mode!=3) return IPPU.ScreenColors[0];
    const unsigned active=Memory.FillRAM[0x212c] & ~Settings.BG_Forced;
    for(int bg=0;bg<(mode==0?4:mode==1?3:2);++bg) {
        if (!(active & (1u<<bg))) continue;
        unsigned bpp=mode==0?2:mode==1?(bg==2?2:4):(bg==0?8:4);
        // Use the same per-line scroll latch as the stock background renderer.
        unsigned wx=(unsigned)(x+LineData[line].BG[bg].HOffset);
        unsigned wy=(unsigned)(y+LineData[line].BG[bg].VOffset);
        unsigned shift=PPU.BG[bg].BGSize?4:3;
        unsigned tx=wx>>shift, ty=wy>>shift;
        unsigned size=PPU.BG[bg].SCSize;
        unsigned page=((size&1)?((tx>>5)&1):0)+((size&2)?(((ty>>5)&1)*((size&1)?2:1)):0);
        unsigned a=(PPU.BG[bg].SCBase<<1)+page*2048+2*((ty&31)*32+(tx&31));
        unsigned t=az_snes_vram(a)|(az_snes_vram(a+1)<<8);
        unsigned px=wx&((1u<<shift)-1), py=wy&((1u<<shift)-1);
        if(t&0x4000)px=((1u<<shift)-1)-px;
        if(t&0x8000)py=((1u<<shift)-1)-py;
        unsigned tile=((t&1023)+(px>>3)+16*(py>>3))&1023;
        unsigned addr=(PPU.BG[bg].NameBase<<1)+tile*(bpp*8)+2*(py&7);
        unsigned pen=0;
        for(unsigned k=0;k<bpp;k++){
            unsigned byte=az_snes_vram(addr+(k>>1)*16+(k&1));
            pen|=((byte>>(7-(px&7)))&1)<<k;
        }
        if(!pen)continue;
        static const unsigned low[3][4]={{11,10,3,2},{11,10,3,0},{7,3,0,0}};
        static const unsigned high[3][4]={{15,14,7,6},{15,14,7,0},{15,11,0,0}};
        unsigned m=mode==3?2:mode;
        unsigned pri=(t&0x2000)?high[m][bg]:low[m][bg];
        if(mode==1 && bg==2 && PPU.BG3Priority && (t&0x2000))pri=17;
        if(pri<=best)continue;
        best=pri;
        color=(mode==0?bg*32:0)+(bpp==8?0:((t>>10)&7)*(1u<<bpp))+pen;
    }
    return IPPU.ScreenColors[color&255];
}
static void az_snes_extend(void)
{
    if(!az_snes_integer() || GFX.StartY>GFX.EndY || GFX.EndY>=239 ||
        IPPU.DoubleWidthPixels || IPPU.DoubleHeightPixels) return;
    const int top=(240-PPU.ScreenHeight)/2;
    if(top<0)return;
    for(unsigned y=GFX.StartY;y<=GFX.EndY;y++){
        uint16* dst=az_snes_canvas+(y+top)*320;
        for(int x=0;x<32;x++){
            dst[x]=az_snes_bg(x-32,y,y);
            dst[288+x]=az_snes_bg(256+x,y,y);
        }
        if(y==0)
            for(int r=0;r<top;r++)for(int x=0;x<320;x++)
                az_snes_canvas[r*320+x]=az_snes_bg(x-32,r-top,y);
        if(y+1==PPU.ScreenHeight)
            for(int r=y+top+1;r<240;r++)for(int x=0;x<320;x++)
                az_snes_canvas[r*320+x]=az_snes_bg(x-32,r-top,y);
    }
}
void S9xUpdateScreen (void)
{''')
rep("gfx.cpp","\tIPPU.PreviousLine = IPPU.CurrentLine;\n}","\taz_snes_extend();\n\tIPPU.PreviousLine = IPPU.CurrentLine;\n}")
rep("libretro/libretro.cpp","bool8 S9xDeinitUpdate(int width, int height)\n{",'''extern uint16 az_snes_canvas[320*240];
extern bool az_snes_integer(void);
bool8 S9xDeinitUpdate(int width, int height)
{
    if (az_snes_integer() && width==256 && height>0 && height<=239) {
        const int top=(240-height)/2;
        for(int y=0;y<height;y++)
            memcpy(az_snes_canvas+(y+top)*320+32,GFX.Screen+y*(GFX.Pitch>>1),256*sizeof(uint16));
        video_cb(az_snes_canvas,320,240,320*sizeof(uint16));
        return TRUE;
    }
    if (az_snes_integer() && width==512 && height>0 && height<=480) {
        static uint16 frame[640*480];
        const int sy=height<=240?2:1, top=(480-height*sy)/2;
        memset(frame,0,sizeof(frame));
        for(int y=0;y<height;y++)for(int d=0;d<sy;d++)
            memcpy(frame+(top+y*sy+d)*640+64,GFX.Screen+y*(GFX.Pitch>>1),512*sizeof(uint16));
        video_cb(frame,640,480,640*sizeof(uint16));
        return TRUE;
    }''')
# Declare the native 4:3 viewport, preserving the original max size for hires.
rep("libretro/libretro.cpp","    info->geometry.aspect_ratio = get_aspect_ratio(width, height);",'''    info->geometry.aspect_ratio = get_aspect_ratio(width, height);
    if (getenv("AZEEZ_EXPANDED_VIEWPORT")) {
        info->geometry.base_width=320;
        info->geometry.base_height=240;
        if(info->geometry.max_height<480)info->geometry.max_height=480;
        info->geometry.aspect_ratio=4.0f/3.0f;
    }''')
print("Fast BananaSNES 320x240 background extension installed; hires fallback preserved")
