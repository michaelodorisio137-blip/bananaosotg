#!/usr/bin/env python3
"""TurboGrafx-16 / PC Engine shelf and opt-in native VDC background extension."""
from pathlib import Path
import sys, shutil
mode, root = sys.argv[1], Path(sys.argv[2])
def rep(path, old, new):
    p=root/path
    s=p.read_text()
    if new in s: return
    if s.count(old)!=1: raise SystemExit("PCE anchor mismatch: "+str(p)+" "+repr(old[:100]))
    p.write_text(s.replace(old,new,1))

if mode=="--source":
    p="mednafen/pce_fast/vdc.c"
    rep(p,"static void DrawOverscan(",'''/* Sample the existing VDC background tile cache without changing scroll,
 * sprite evaluation, VRAM, or the emulated scanline clock. */
static uint16 az_pce_bg_pixel(const vdc_t *vdc, int x)
{
   unsigned wx = (unsigned)(vdc->BG_XOffset + x);
   unsigned shift = bat_width_shift_tab[(vdc->MWR >> 4) & 3];
   unsigned row = ((vdc->BG_YOffset >> 3) & bat_height_mask_tab[(vdc->MWR >> 6) & 1]) << shift;
   unsigned tile = vdc->VRAM[row + ((wx >> 3) & ((1u << shift)-1))];
   uint64_t bits = vdc->bg_tile_cache[(tile & 0xFFF)*8 + (vdc->BG_YOffset & 7)];
   if ((vdc->MWR & 3) == 3)
      bits &= (vdc->MWR & 0x80) ? 0xCCCCCCCCCCCCCCCCULL : 0x3333333333333333ULL;
   bits |= cblock_exlut[tile >> 12];
   return vce.color_table_cache[((const uint8 *)&bits)[wx & 7]];
}
static void DrawOverscan(''')
    rep(p,'   bool skip = espec->skip || IsHES;', '''   bool skip = espec->skip || IsHES;
   const bool az_native = getenv("AZEEZ_EXPANDED_VIEWPORT") != NULL && !IsHES;''')
    rep(p,'      DisplayRect->h = MDFN_GetSettingUI("pce_fast.slend") - DisplayRect->y + 1;', '''      DisplayRect->h = MDFN_GetSettingUI("pce_fast.slend") - DisplayRect->y + 1;
      if (az_native) {
         DisplayRect->y = 0;
         DisplayRect->h = 240;
      }''')
    rep(p,'   do\n   {\n      const bool SHOULD_DRAW', '''   defined_width[0] = az_native ? 320 : 256;
   if (az_native) defined_width[1] = 320;
   do
   {
      const bool SHOULD_DRAW''')
    rep(p,'                  if(target_offset < 0)\n', '''                  if (az_native && vce.dot_clock < 2)
                     target_offset = (320 - width) / 2;
                  if(target_offset < 0)
''')
    rep(p,'                  DrawOverscan(vdc, target_ptr16, DisplayRect, false, target_offset, target_offset + width);', '''                  DrawOverscan(vdc, target_ptr16, DisplayRect, false, target_offset, target_offset + width);
                  if (az_native && vce.dot_clock < 2 && (vdc->CR & 0x80) &&
                      (userle & ULE_BG0) && target_offset > 0 && width > 0) {
                     int x;
                     for (x=0; x<target_offset; ++x)
                        target_ptr16[x] = az_pce_bg_pixel(vdc, x-target_offset);
                     for (x=target_offset+width; x<320; ++x)
                        target_ptr16[x] = az_pce_bg_pixel(vdc, x-target_offset);
                  }''')
    # Preserve high-dot-clock native output. Clear each line's unused tail
    # so mixed-mode games cannot show stale data in a wider scanout.
    rep(p,'         if(vdc->burst_mode)\n         {', '''         if (az_native && SHOULD_DRAW && fc_vrm && DisplayRect->w < 512) {
            int x;
            for (x=DisplayRect->w; x<512; ++x)
               target_ptr16[x] = vce.color_table_cache[0x100];
         }
         if(vdc->burst_mode)
         {''')
    rep(p,'\tDisplayRect->w = defined_width[vce.dot_clock];\n}', '\tDisplayRect->w = defined_width[az_native ? max_dc : vce.dot_clock];\n}')
    p="libretro.c"
    rep(p,'   environ_cb(RETRO_ENVIRONMENT_SET_GEOMETRY, &system_av_info);', '''   if (getenv("AZEEZ_EXPANDED_VIEWPORT") && width == 320 && height == 240)
      system_av_info.geometry.aspect_ratio = 4.0f/3.0f;
   environ_cb(RETRO_ENVIRONMENT_SET_GEOMETRY, &system_av_info);''')
    print("PCE native VDC viewport applied")
    sys.exit(0)

def menu(root):
    p=root/"etc/banana/systems.conf"
    s=p.read_text()
    if "[pcengine]" not in s:
        anchor="[gameandwatch]"
        assert s.count(anchor)==1
        p.write_text(s.replace(anchor,"""[pcengine]
name = TurboGrafx-16 / PC Engine
maker = NEC
ext = pce sgx zip 7z
run = /usr/libexec/banana/run-retroarch mednafen_pce_fast %ROM%
perf = balanced
always = yes
aliases = tg16, turbografx, turbografx-16, pc engine, supergrafx

"""+anchor,1))
if mode=="--rootfs":
    menu(root)
    assert (root/"usr/lib/libretro/mednafen_pce_fast_libretro.so").stat().st_size>0
    sys.exit(0)
if mode!="--build": raise SystemExit("unknown PCE mode")
menu(root/"system/rootfs")
pkg=root/"buildroot/package/libretro-mednafen-pce-fast"
pkg.mkdir(exist_ok=True)
shutil.copyfile(__file__,pkg/"azeezos-2-pce.py")
(pkg/"libretro-mednafen-pce-fast.mk").write_text("""LIBRETRO_MEDNAFEN_PCE_FAST_VERSION = 4cf066e22533186d0cfad85a0fec2aced93e4e29
LIBRETRO_MEDNAFEN_PCE_FAST_SITE = $(call github,libretro,beetle-pce-fast-libretro,$(LIBRETRO_MEDNAFEN_PCE_FAST_VERSION))
LIBRETRO_MEDNAFEN_PCE_FAST_LICENSE = GPL-2.0

define LIBRETRO_MEDNAFEN_PCE_FAST_BUILD_CMDS
	python3 $(BR2_EXTERNAL_BANANA_PATH)/package/libretro-mednafen-pce-fast/azeezos-2-pce.py --source $(@D)
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D) platform=unix CC="$(TARGET_CC)" CXX="$(TARGET_CXX)" AR="$(TARGET_AR)"
endef

define LIBRETRO_MEDNAFEN_PCE_FAST_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0644 $(@D)/mednafen_pce_fast_libretro.so $(TARGET_DIR)/usr/lib/libretro/mednafen_pce_fast_libretro.so
endef

$(eval $(generic-package))
""")
p=root/"buildroot/package/retroarch/cores.in"
s=p.read_text()
if "config BR2_PACKAGE_LIBRETRO_MEDNAFEN_PCE_FAST\n" not in s:
    p.write_text(s+'\nconfig BR2_PACKAGE_LIBRETRO_MEDNAFEN_PCE_FAST\n\tbool "libretro-mednafen-pce-fast"\n\tdefault y\n\tdepends on BR2_INSTALL_LIBSTDCPP\n')
print("TurboGrafx-16 / PC Engine shelf and Beetle PCE Fast build integrated")
