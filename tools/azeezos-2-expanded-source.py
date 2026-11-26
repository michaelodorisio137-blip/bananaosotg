#!/usr/bin/env python3
"""Experimental renderer-side viewport support; no emulated clock changes."""
from pathlib import Path
import sys
kind, root = sys.argv[1], Path(sys.argv[2])
def rep(path, old, new):
    p=root/path
    s=p.read_text()
    if new in s: return
    if s.count(old)!=1: raise SystemExit("viewport anchor mismatch: "+path+" "+repr(old[:80]))
    p.write_text(s.replace(old,new,1))

if kind=="nes":
    p="src/ppu.c"
    rep(p, "static int rendis = 0;", """static int rendis = 0;
uint8_t azeez_nes_sides[240][64];
uint8_t azeez_nes_emphasis[240];
/* Read the currently mapped nametable and CHR without invoking mapper hooks,
 * changing PPU registers, or clocking extra dots. The original 256 pixels
 * are kept separately. Special mapper fetches are not reconstructed. */
static void azeez_nes_sample_sides(void) {
    int i;
    unsigned v=RefreshAddr;
    unsigned cy=(v>>5)&31, fy=(v>>12)&7;
    unsigned emph=(PPU[1]>>5)&7;
    azeez_nes_emphasis[scanline]=emph;
    for(i=0;i<64;i++) {
        int sx=i<32 ? i-32 : i+224;
        unsigned wx=(unsigned)(sx+XOffset+8*(v&31)+256*((v>>10)&1))&511;
        unsigned page=((v>>10)&2)|(wx>>8);
        unsigned tx=(wx>>3)&31;
        unsigned pen=PALRAM[0]&63;
        if (ScreenON && !(rendis&2) && cy<30 && vnapage[page]) {
            unsigned tile=vnapage[page][cy*32+tx];
            unsigned attr=vnapage[page][0x3c0+(cy>>2)*8+(tx>>2)];
            unsigned shift=((cy&2)<<1)|(tx&2);
            unsigned at=((PPU[0]&16)<<8)+tile*16+fy;
            unsigned bit=7-(wx&7);
            if(VPage[at>>10]) {
                unsigned n=((VPage[at>>10][at]>>bit)&1)|
                    (((VPage[(at+8)>>10][at+8]>>bit)&1)<<1);
                if(n) pen=PALRAM[(((attr>>shift)&3)*4)+n]&63;
            }
        }
        if(PPU[1]&1) pen&=0x30;
        azeez_nes_sides[scanline][i]=pen;
    }
}""")
    rep(p, "\tif (MMC5Hack && (ScreenON || SpriteON)) MMC5_hb(scanline);",
        """\tif (scanline >= 0 && scanline < 240 && getenv("AZEEZ_EXPANDED_VIEWPORT"))
        azeez_nes_sample_sides();
\tif (MMC5Hack && (ScreenON || SpriteON)) MMC5_hb(scanline);""")
    p="src/drivers/libretro/libretro.c"
    rep(p,"void retro_get_system_av_info(struct retro_system_av_info *info)\n{",
        """extern uint8_t azeez_nes_sides[240][64];
extern uint8_t azeez_nes_emphasis[240];
static bool azeez_nes_mode(void) {
   return getenv("AZEEZ_EXPANDED_VIEWPORT") && GameInfo && GameInfo->type != GIT_NSF;
}
void retro_get_system_av_info(struct retro_system_av_info *info)
{""")
    rep(p,"   info->geometry.aspect_ratio = get_aspect_ratio(width, height);\n   info->timing.sample_rate",
        """   info->geometry.aspect_ratio = get_aspect_ratio(width, height);
   if (azeez_nes_mode()) {
      info->geometry.base_width = info->geometry.max_width = 320;
      info->geometry.base_height = info->geometry.max_height = 240;
      info->geometry.aspect_ratio = 4.0f/3.0f;
   }
   info->timing.sample_rate""")
    rep(p,"   unsigned pitch  = width * sizeof(bpp_t);\n\n#ifdef HAVE_HDPACK",
        """   unsigned pitch  = width * sizeof(bpp_t);
   if (azeez_nes_mode() && gfx) {
      static bpp_t frame[320*240];
      for(y=0;y<240;y++) {
         unsigned emph=azeez_nes_emphasis[y];
         unsigned base=emph ? 256u+(emph<<6) : 0;
         for(x=0;x<320;x++) {
            unsigned pen;
            if(x>=32 && x<288) {
               unsigned n=gfx[y*256+x-32];
               unsigned d=XDBuf[y*256+x-32]&7;
               frame[y*320+x]=retro_palette[d ? 256u+(d<<6)+(n&63) :
                  (n & (use_raw_palette ? 63 : 255))];
               continue;
            }
            pen=azeez_nes_sides[y][x<32?x:x-256];
            frame[y*320+x]=retro_palette[base ? base+pen : (use_raw_palette?pen:0x80|pen)];
         }
      }
      video_cb(frame,320,240,320*sizeof(bpp_t));
      return;
   }

#ifdef HAVE_HDPACK""")
elif kind=="n64":
    rep("libretro/libretro.c","       // If we use Angrylion, we force 640x480",
        """       if (getenv("AZEEZ_EXPANDED_VIEWPORT")) {
          retro_screen_width = 320;
          retro_screen_height = 240;
          retro_screen_aspect = 4.0 / 3.0;
          AspectRatio = 1;
          EnableNativeResFactor = 1;
       }
       // If we use Angrylion, we force 640x480""")
elif kind=="psx":
    rep("frontend/libretro.c",'   var.key = "pcsx_rearmed_scale_hires";',
        """   /* Keep native high resolution modes. Overscan reveals available
    * VRAM, not geometry that the original game never drew. */
   if (getenv("AZEEZ_EXPANDED_VIEWPORT")) {
      pl_rearmed_cbs.screen_centering_type = 2;
      pl_rearmed_cbs.show_overscan = 1;
   }
   var.key = "pcsx_rearmed_scale_hires";""")
else:
    raise SystemExit("unknown viewport core")
