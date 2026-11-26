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
    # The same MMC5 statement also occurs after the frame loop; match DoLine only.
    rep(p, "\n\tif (MMC5Hack && (ScreenON || SpriteON)) MMC5_hb(scanline);\n\n\tX6502_Run(256);",
        """
\tif (scanline >= 0 && scanline < 240 && getenv("AZEEZ_EXPANDED_VIEWPORT"))
        azeez_nes_sample_sides();
\tif (MMC5Hack && (ScreenON || SpriteON)) MMC5_hb(scanline);

\tX6502_Run(256);""")
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
    # Reveal only VRAM already inside the game's drawing rectangle. Do not
    # expose neighboring textures or overwrite VRAM by changing GPU commands.
    p="plugins/gpulib/vout_pl.c"
    rep(p,"#include <string.h>","#include <string.h>\n#include <stdlib.h>")
    rep(p,"int vout_update(struct psx_gpu *gpu, int src_x, int src_y)",
        """static int az_psx_rect(struct psx_gpu *g,int sx,int sy,int *left,int *top)
{
  int w=g->screen.w,h=g->screen.h;
  int x=sx-(320-w)/2,y=sy-(240-h)/2;
  unsigned a=g->ex_regs[3], b=g->ex_regs[4];
  if (!getenv("AZEEZ_EXPANDED_VIEWPORT") || (g->status & PSX_GPU_STATUS_RGB24)
      || g->state.enhancement_enable || g->state.downscale_enable
      || w<240 || w>320 || h<192 || h>240 || x<0 || y<0
      || x+320>1024 || y+240>512) return 0;
  if (x<(int)(a&1023) || y<(int)((a>>10)&511) ||
      x+319>(int)(b&1023) || y+239>(int)((b>>10)&511)) return 0;
  *left=x; *top=y; return 1;
}

int vout_update(struct psx_gpu *gpu, int src_x, int src_y)""")
    rep(p,"  if (w <= 0 || h <= 0)\n    return 0;\n\n  check_mode_change(gpu, 0);\n  if (gpu->state.enhancement_active) {",
        """  if (w <= 0 || h <= 0)
    return 0;

  {
    int left,top;
    if (az_psx_rect(gpu,src_x,src_y,&left,&top)) {
      if (gpu->state.w_out_old!=320 || gpu->state.h_out_old!=240 ||
          ((gpu->state.status_vo_old^gpu->status)&((7<<16)|(1<<21)))) {
        cbs->pl_vout_set_mode(320,240,320,240,16);
        gpu->state.w_out_old=320; gpu->state.h_out_old=240;
        gpu->state.status_vo_old=gpu->status;
      }
      cbs->pl_vout_flip(vram,(top*1024+left)*2,0,0,0,320,240,gpu->state.dims_changed);
      gpu->state.dims_changed=0;
      return 1;
    }
  }
  check_mode_change(gpu, 0);
  if (gpu->state.enhancement_active) {""")
elif kind=="genesis":
    # The Wide renderer already extends the playfield in eight-pixel units.
    # Request 8 extra columns only for H32, preserving the native H40 image.
    # Expose vertical overscan as the actual VDP backdrop, not invented lines.
    p=root/"core/system.c"
    v=p.read_text()
    old="    bitmap.viewport.w += config.h40_extra_columns * 8;"
    new="""    if (getenv("AZEEZ_EXPANDED_VIEWPORT")) {
      config.h40_extra_columns = (reg[12] & 1) ? 0 : 8;
      if (bitmap.viewport.h <= 240)
        bitmap.viewport.y = (240 - bitmap.viewport.h) / 2;
    }
    bitmap.viewport.w += config.h40_extra_columns * 8;"""
    if new not in v:
        if v.count(old)!=2: raise SystemExit("GX width anchor mismatch")
        v=v.replace(old,new)
        if "#include <stdlib.h>" not in v: v="#include <stdlib.h>\n"+v
        p.write_text(v)
    # Do not change the game register or sprite budget. Mid-frame switching
    # remains a special case to validate on real hardware.
elif kind=="snes":
    p="bsnes/target-libretro/libretro.cpp"
    rep(p,'\temulator->configure("Hacks/PPU/Mode7/Scale", scale);',
        '''\tif (getenv("AZEEZ_EXPANDED_VIEWPORT")) scale = 1;
\temulator->configure("Hacks/PPU/Mode7/Scale", scale);''')
    rep(p,'\tif (scale == 0) ws = 0;',
        '''\tif (getenv("AZEEZ_EXPANDED_VIEWPORT")) ws = 403;
\tif (scale == 0) ws = 0;''')
    rep(p,'\t// wsbg1: auto horz and vert',
        '''\tif (getenv("AZEEZ_EXPANDED_VIEWPORT")) {
\t\temulator->configure("Hacks/PPU/Mode7/WsMode", 2);
\t\tws = 403;
\t}

\t// wsbg1: auto horz and vert''')
else:
    raise SystemExit("unknown viewport core")
