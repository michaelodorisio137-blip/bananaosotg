#!/usr/bin/env python3
"""Add Beetle VB and opt-in experimental 320x240 renderer scanout."""
from pathlib import Path
import sys, shutil
mode, root = sys.argv[1], Path(sys.argv[2])
def rep(path, old, new):
    p = root / path
    s = p.read_text()
    if new in s: return
    if s.count(old) != 1: raise SystemExit("Virtual Boy anchor mismatch: " + str(p) + " " + repr(old[:100]))
    p.write_text(s.replace(old,new,1))

if mode == "--source":
    p = "mednafen/vb/vip.c"
    rep(p, '#include "vip_draw.inc"', '''#include "vip_draw.inc"
#include <stdlib.h>
/* Extra VIP rows are presentation-only; never write to emulated VRAM,
 * change the 28 hardware drawing blocks, or alter interrupt timing. */
static uint8 az_vb_extra[2][2][384][4];
static bool az_vb_viewport;
static void az_vb_draw_extra(void)
{
   MDFN_ALIGN(8) uint8 extra[2][512 * 8];
   int block, lr, x, k, y;
   for (block = 0; block < 2; ++block) {
      VIP_DrawBlock(28 + block, extra[0] + 8, extra[1] + 8);
      for (lr = 0; lr < 2; ++lr)
         for (x = 0; x < 384; ++x)
            for (k = 0; k < 2; ++k) {
               uint8 packed = 0;
               for (y = 0; y < 4; ++y)
                  packed |= (extra[lr][8 + x + 512 * (4*k+y)] & 3) << (2*y);
               az_vb_extra[DrawingFB][lr][x][2*block+k] = packed;
            }
   }
}
''')
    # Declare viewport before VIP_StartFrame references it.
    rep(p, 'static uint8 FB[2][2][0x6000];', 'static uint8 FB[2][2][0x6000];\nstatic bool az_vb_viewport;')
    # stdlib must also precede the first getenv call.
    rep(p, 'static bool az_vb_viewport;\nstatic void az_vb_draw_extra', 'static void az_vb_draw_extra')
    rep(p, '   espec->DisplayRect.x = 0;', '''   az_vb_viewport = getenv("AZEEZ_EXPANDED_VIEWPORT") != NULL &&
      VB3DMode == VB3DMODE_ANAGLYPH &&
      CopyFBColumnToTarget == CopyFBColumnToTarget_Anaglyph;
   espec->DisplayRect.x = 0;''')
    rep(p, '         espec->DisplayRect.h = 224;\n         break;\n\n      case VB3DMODE_VLI:', '         espec->DisplayRect.h = az_vb_viewport ? 240 : 224;\n         break;\n\n      case VB3DMODE_VLI:')
    f=root/p
    s=f.read_text()
    i=s.index("static INLINE void CopyFBColumnToTarget_Anaglyph_BASE")
    j=s.index("static void CopyFBColumnToTarget_Anaglyph(void)\n",i)
    body=s[i:j]
    if body.count("for(y = 56; y; y--)")!=4 or body.count("uint32 source_bits = *fb_source;")!=2:
        raise SystemExit("VB anaglyph loop mismatch")
    body=body.replace("for(y = 56; y; y--)","for(y = az_vb_viewport ? 60 : 56; y; y--)")
    body=body.replace("uint32 source_bits = *fb_source;", "uint32 source_bits = az_vb_viewport && y <= 4 ? az_vb_extra[fb][lr][Column][4-y] : *fb_source;")
    f.write_text(s[:i]+body+s[j:])
    rep(p, '            SBOUT_InactiveTime = running_timestamp + 1120;', '''            if (az_vb_viewport && DrawingBlock == 27 && !(skip && InstantDisplayHack && AllowDrawSkip))
               az_vb_draw_extra();
            SBOUT_InactiveTime = running_timestamp + 1120;''')
    # getenv is needed before VIP_StartFrame.
    f=root/p
    s=f.read_text()
    f.write_text("#include <stdlib.h>\n"+s)
    p="libretro.cpp"
    rep(p, '   if (width != spec.DisplayRect.w || height != spec.DisplayRect.h)', '''   const bool az_vb_crop = vb_vr_mode() == VB_PRESENT_SOFTWARE &&
      spec.DisplayRect.w == 384 && spec.DisplayRect.h == 240;
   if (az_vb_crop)
      spec.DisplayRect.w = 320;
   if (width != spec.DisplayRect.w || height != spec.DisplayRect.h)''')
    rep(p, 'const uint32_t *pix = surf.pixels;', 'const uint32_t *pix = surf.pixels + (az_vb_crop ? 32 : 0);')
    rep(p, 'const uint16_t *pix = surf.pixels16;', 'const uint16_t *pix = surf.pixels16 + (az_vb_crop ? 32 : 0);')
    print("Virtual Boy experimental 320x240 viewport source applied")
    sys.exit(0)

def menu(root):
    p=root/"etc/banana/systems.conf"
    s=p.read_text()
    if "[virtualboy]" not in s:
        anchor="[gameandwatch]"
        assert s.count(anchor)==1
        p.write_text(s.replace(anchor, """[virtualboy]
name = Virtual Boy
maker = Nintendo
ext = vb vboy bin zip 7z
run = /usr/libexec/banana/run-retroarch mednafen_vb %ROM%
perf = balanced
always = yes
aliases = vb, virtual boy, nintendo virtual boy

"""+anchor,1))
if mode == "--rootfs":
    menu(root)
    assert (root/"usr/lib/libretro/mednafen_vb_libretro.so").stat().st_size > 0
    sys.exit(0)
if mode != "--build": raise SystemExit("unknown Virtual Boy mode")
menu(root/"system/rootfs")
pkg=root/"buildroot/package/libretro-mednafen-vb"
pkg.mkdir(exist_ok=True)
shutil.copyfile(__file__,pkg/"azeezos-2-virtualboy.py")
(pkg/"libretro-mednafen-vb.mk").write_text("""LIBRETRO_MEDNAFEN_VB_VERSION = d5ae54c8e23b573a3b34e888b2d48a588027e92c
LIBRETRO_MEDNAFEN_VB_SITE = $(call github,libretro,beetle-vb-libretro,$(LIBRETRO_MEDNAFEN_VB_VERSION))
LIBRETRO_MEDNAFEN_VB_LICENSE = GPL-2.0

define LIBRETRO_MEDNAFEN_VB_BUILD_CMDS
	python3 $(BR2_EXTERNAL_BANANA_PATH)/package/libretro-mednafen-vb/azeezos-2-virtualboy.py --source $(@D)
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D) platform=unix CC="$(TARGET_CC)" CXX="$(TARGET_CXX)" AR="$(TARGET_AR)"
endef

define LIBRETRO_MEDNAFEN_VB_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0644 $(@D)/mednafen_vb_libretro.so $(TARGET_DIR)/usr/lib/libretro/mednafen_vb_libretro.so
endef

$(eval $(generic-package))
""")
p=root/"buildroot/package/retroarch/cores.in"
s=p.read_text()
if "config BR2_PACKAGE_LIBRETRO_MEDNAFEN_VB\n" not in s:
    p.write_text(s+'\nconfig BR2_PACKAGE_LIBRETRO_MEDNAFEN_VB\n\tbool "libretro-mednafen-vb"\n\tdefault y\n\tdepends on BR2_INSTALL_LIBSTDCPP\n')
print("Virtual Boy shelf and pinned Beetle VB build integrated")
