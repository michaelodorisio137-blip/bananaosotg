#!/usr/bin/env python3
"""Neo Geo Pocket Color shelf and opt-in tilemap viewport extension."""
from pathlib import Path
import sys, shutil
mode, root = sys.argv[1], Path(sys.argv[2])
def rep(path, old, new):
    p=root/path
    s=p.read_text()
    if new in s: return
    if s.count(old)!=1: raise SystemExit("NGP anchor mismatch: "+str(p)+" "+repr(old[:100]))
    p.write_text(s.replace(old,new,1))

if mode=="--source":
    p="mednafen/ngp/gfx.c"
    rep(p, 'bool ngpgfx_draw(ngpgfx_t *gfx, void *data, bool skip)', '''/* Read the two 32x32 tilemaps outside the 160x152 LCD.
 * Original window, sprites, interrupts and timing remain unchanged. */
static uint16_t az_ngp_read16(const uint8_t *p)
{
   return p[0] | ((uint16_t)p[1]<<8);
}
static unsigned az_ngp_mono(unsigned pen)
{
   pen &= 7;
   return ~( (pen<<1) | (pen<<5) | (pen<<9) ) & 4095;
}
static uint32_t az_ngp_background(ngpgfx_t *g, int x, int y)
{
   unsigned c, i;
   if (!g->K2GE_MODE)
      c=az_ngp_read16(g->ColorPaletteRAM+0x1e0+2*(g->bgc&7));
   else
      c=(g->bgc&0xc0)==0x80 ? az_ngp_mono(g->bgc) : 4095;
   for(i=0;i<2;i++) {
      unsigned plane = (g->planeSwap ? i : 1-i);
      unsigned wx=(uint8_t)(x+(plane ? g->scroll2x : g->scroll1x));
      unsigned wy=(uint8_t)(y+(plane ? g->scroll2y : g->scroll1y));
      unsigned t, row, col, bits, pen;
      if (!(g->layer_enable & (1<<i))) continue;
      t=az_ngp_read16(g->ScrollVRAM+plane*0x800+2*((wy>>3)*32+(wx>>3)));
      row=wy&7; col=wx&7;
      if(t&0x4000) row=7-row;
      if(t&0x8000) col=7-col;
      bits=az_ngp_read16(g->CharacterRAM+(t&511)*16+row*2);
      pen=(bits>>(14-col*2))&3;
      if(!pen) continue;
      if(!g->K2GE_MODE)
         c=az_ngp_read16(g->ColorPaletteRAM+0x80+plane*0x80+8*((t>>9)&15)+2*pen);
      else
         c=az_ngp_mono((plane ? g->SCRP2PLT : g->SCRP1PLT)[(t&0x2000 ? 3:0)+pen-1]);
   }
   if(g->negative) c=~c;
   return g->ColorMap[c&4095];
}
static void az_ngp_row(ngpgfx_t *g, MDFN_Surface *s, int y, const uint16_t *center)
{
   int x, dy=y+44;
   for(x=0;x<320;x++) {
      uint32_t color;
      if(center && x>=80 && x<240)
         color=g->ColorMap[center[x-80]&4095];
      else
         color=az_ngp_background(g,x-80,y);
      if(s->depth==24)
         ((uint32_t*)s->pixels)[dy*s->pitch+x]=color;
      else
         s->pixels[dy*s->pitch+x]=(uint16_t)color;
   }
}
bool ngpgfx_draw(ngpgfx_t *gfx, void *data, bool skip)''')
    rep(p,'      switch (surface->depth)\n      {', '''      if (surface->width == 320 && surface->height == 240) {
         int y;
         if (gfx->raster_line == 0)
            for(y=-44;y<0;y++) az_ngp_row(gfx,surface,y,NULL);
         az_ngp_row(gfx,surface,gfx->raster_line,cfb_scanline);
         if (gfx->raster_line == SCREEN_HEIGHT-1)
            for(y=152;y<196;y++) az_ngp_row(gfx,surface,y,NULL);
      }
      else switch (surface->depth)
      {''')
    p="libretro.c"
    rep(p,'#define FB_WIDTH 160\n#define FB_HEIGHT 152', '''#define FB_WIDTH (getenv("AZEEZ_EXPANDED_VIEWPORT") ? 320 : 160)
#define FB_HEIGHT (getenv("AZEEZ_EXPANDED_VIEWPORT") ? 240 : 152)''')
    rep(p,'   spec.DisplayRect.w      = 160;\n   spec.DisplayRect.h      = 152;', '   spec.DisplayRect.w      = FB_WIDTH;\n   spec.DisplayRect.h      = FB_HEIGHT;')
    rep(p,'   info->geometry.aspect_ratio = MEDNAFEN_CORE_GEOMETRY_ASPECT_RATIO;', '''   info->geometry.aspect_ratio = MEDNAFEN_CORE_GEOMETRY_ASPECT_RATIO;
   if (getenv("AZEEZ_EXPANDED_VIEWPORT")) {
      info->geometry.base_width = info->geometry.max_width = 320;
      info->geometry.base_height = info->geometry.max_height = 240;
      info->geometry.aspect_ratio = 4.0f/3.0f;
   }''')
    rep(p,'   width  = spec.DisplayRect.w;\n   height = spec.DisplayRect.h;', '   width = FB_WIDTH;\n   height = FB_HEIGHT;')
    print("Neo Geo Pocket native tilemap extension applied")
    sys.exit(0)

def menu(root):
    p=root/"etc/banana/systems.conf"
    s=p.read_text()
    if "[ngpc]" not in s:
        anchor="[gameandwatch]"
        assert s.count(anchor)==1
        p.write_text(s.replace(anchor,"""[ngpc]
name = Neo Geo Pocket Color
maker = SNK
ext = ngp ngc ngpc npc zip 7z
run = /usr/libexec/banana/run-retroarch mednafen_ngp %ROM%
perf = balanced
always = yes
aliases = ngp, neo geo pocket, neogeo pocket color

"""+anchor,1))
if mode=="--rootfs":
    menu(root)
    assert (root/"usr/lib/libretro/mednafen_ngp_libretro.so").stat().st_size>0
    sys.exit(0)
if mode!="--build": raise SystemExit("unknown NGP mode")
menu(root/"system/rootfs")
pkg=root/"buildroot/package/libretro-mednafen-ngp"
pkg.mkdir(exist_ok=True)
shutil.copyfile(__file__,pkg/"azeezos-2-ngp.py")
(pkg/"libretro-mednafen-ngp.mk").write_text("""LIBRETRO_MEDNAFEN_NGP_VERSION = a50d5ac288a81f2104ddf43195a4efdd15c72227
LIBRETRO_MEDNAFEN_NGP_SITE = $(call github,libretro,beetle-ngp-libretro,$(LIBRETRO_MEDNAFEN_NGP_VERSION))
LIBRETRO_MEDNAFEN_NGP_LICENSE = GPL-2.0

define LIBRETRO_MEDNAFEN_NGP_BUILD_CMDS
	python3 $(BR2_EXTERNAL_BANANA_PATH)/package/libretro-mednafen-ngp/azeezos-2-ngp.py --source $(@D)
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D) platform=unix CC="$(TARGET_CC)" CXX="$(TARGET_CXX)" AR="$(TARGET_AR)"
endef

define LIBRETRO_MEDNAFEN_NGP_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0644 $(@D)/mednafen_ngp_libretro.so $(TARGET_DIR)/usr/lib/libretro/mednafen_ngp_libretro.so
endef

$(eval $(generic-package))
""")
p=root/"buildroot/package/retroarch/cores.in"
s=p.read_text()
if "config BR2_PACKAGE_LIBRETRO_MEDNAFEN_NGP\n" not in s:
    p.write_text(s+'\nconfig BR2_PACKAGE_LIBRETRO_MEDNAFEN_NGP\n\tbool "libretro-mednafen-ngp"\n\tdefault y\n\tdepends on BR2_INSTALL_LIBSTDCPP\n')
print("Neo Geo Pocket Color shelf and pinned Beetle NGP core integrated")
