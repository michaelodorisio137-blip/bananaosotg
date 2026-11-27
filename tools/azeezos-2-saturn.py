#!/usr/bin/env python3
"""Add GPU-accelerated Saturn to the AzeezOS shelf and firmware."""
from pathlib import Path
import sys, subprocess
mode, root = sys.argv[1], Path(sys.argv[2])

def install_menu(root):
    p=root/"etc/banana/systems.conf"
    s=p.read_text()
    if "[saturn]" not in s:
        anchor="[gameandwatch]"
        if s.count(anchor)!=1: raise SystemExit("Saturn shelf anchor mismatch")
        p.write_text(s.replace(anchor,"""[saturn]
name = Sega Saturn
maker = Sega
ext = cue iso mds ccd chd
run = /usr/libexec/banana/run-retroarch yabasanshiro %ROM%
perf = performance
always = yes
aliases = sega saturn, saturn

"""+anchor,1))
    p=root/"usr/libexec/banana/run-retroarch"
    s=p.read_text()
    old='n64|psx|"") ;;'
    new='n64|psx|saturn|"") ;;'
    if new not in s:
        if s.count(old)!=1: raise SystemExit("Saturn GPU frontend anchor mismatch")
        p.write_text(s.replace(old,new,1))
    subprocess.run(["sh","-n",str(p)],check=True)

if mode=="--rootfs":
    install_menu(root)
    assert (root/"usr/lib/libretro/yabasanshiro_libretro.so").stat().st_size>0
    sys.exit(0)
if mode!="--build": raise SystemExit("unknown Saturn integration mode")
install_menu(root/"system/rootfs")
pkg=root/"buildroot/package/libretro-yabasanshiro"
pkg.mkdir(exist_ok=True)
(pkg/"libretro-yabasanshiro.mk").write_text("""LIBRETRO_YABASANSHIRO_VERSION = 10f50efbbfed745757ce20d34ced7c80f06c68dd
LIBRETRO_YABASANSHIRO_SITE = $(call github,libretro,yabause,$(LIBRETRO_YABASANSHIRO_VERSION))
LIBRETRO_YABASANSHIRO_LICENSE = GPL-2.0

define LIBRETRO_YABASANSHIRO_BUILD_CMDS
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D)/yabause/src/libretro platform=arm64_cortex_a53_gles3 CC="$(TARGET_CC)" CXX="$(TARGET_CXX)" CC_AS="$(TARGET_CC)" AR="$(TARGET_AR)"
endef

define LIBRETRO_YABASANSHIRO_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0644 $(@D)/yabause/src/libretro/yabasanshiro_libretro.so $(TARGET_DIR)/usr/lib/libretro/yabasanshiro_libretro.so
endef

$(eval $(generic-package))
""")
p=root/"buildroot/package/retroarch/cores.in"
s=p.read_text()
if "config BR2_PACKAGE_LIBRETRO_YABASANSHIRO\n" not in s:
    p.write_text(s+'\nconfig BR2_PACKAGE_LIBRETRO_YABASANSHIRO\n\tbool "libretro-yabasanshiro"\n\tdefault y\n\tdepends on BR2_INSTALL_LIBSTDCPP\n')
print("Saturn shelf, ARM64 SH2 dynarec, GLES3 core and RetroArch launch path integrated")
