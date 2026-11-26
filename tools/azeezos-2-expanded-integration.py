#!/usr/bin/env python3
"""Install renderer patches, add optional wide cores and retain stock cores."""
from pathlib import Path
import sys, shutil
root=Path(sys.argv[1])
def rep(rel,old,new):
    p=root/rel; s=p.read_text()
    if new in s: return
    if s.count(old)!=1: raise SystemExit("viewport integration mismatch: "+rel+" "+repr(old))
    p.write_text(s.replace(old,new,1))
for name,kind,ident in (("fceumm","nes","FCEUMM"),("mupen64plus-next","n64","MUPEN64PLUS_NEXT"),("pcsx-rearmed","psx","PCSX_REARMED")):
    pkg="buildroot/package/libretro-"+name
    shutil.copyfile(Path(__file__).with_name("azeezos-2-expanded-source.py"),root/pkg/"azeezos-2-expanded-source.py")
    anchor="define LIBRETRO_"+ident+"_BUILD_CMDS"
    rep(pkg+"/libretro-"+name+".mk",anchor,anchor+"\n\tpython3 $(BR2_EXTERNAL_BANANA_PATH)/package/libretro-"+name+"/azeezos-2-expanded-source.py "+kind+" $(@D)")
cores=[
 ("genesis-plus-gx-wide","GENESIS_PLUS_GX_WIDE","libretro","Genesis-Plus-GX-Wide","b7ad005431f5f0b55e559f6d598d1ed2479bf13b","genesis_plus_gx_wide","$(TARGET_MAKE_ENV) $(MAKE) -C $(@D) -f Makefile.libretro platform=unix CC=\"$(TARGET_CC)\" CXX=\"$(TARGET_CXX)\"","$(@D)/genesis_plus_gx_wide_libretro.so","Non-commercial"),
 ("bsnes-hd","BSNES_HD","DerKoun","bsnes-hd","fc26b25ea236f0f877f0265d2a2c37dfd93dfde9","bsnes_hd_beta","mkdir -p $(@D)/bsnes/obj $(@D)/bsnes/out\n\t$(TARGET_MAKE_ENV) $(MAKE) -C $(@D)/bsnes target=libretro binary=library platform=linux compiler=\"$(TARGET_CXX)\"","$(@D)/bsnes/out/bsnes_hd_beta_libretro.so","GPL-3.0")
]
p=root/"buildroot/package/retroarch/cores.in"
s=p.read_text()
for name,ident,owner,repo,commit,soname,build,so,license in cores:
    pkg=root/("buildroot/package/libretro-"+name)
    pkg.mkdir(exist_ok=True)
    sym="LIBRETRO_"+ident
    mk=f"""{sym}_VERSION = {commit}
{sym}_SITE = $(call github,{owner},{repo},$({sym}_VERSION))
{sym}_LICENSE = {license}

define {sym}_BUILD_CMDS
\t{build}
endef

define {sym}_INSTALL_TARGET_CMDS
\t$(INSTALL) -D -m 0644 {so} $(TARGET_DIR)/usr/lib/libretro/{soname}_libretro.so
endef

$(eval $(generic-package))
"""
    (pkg/("libretro-"+name+".mk")).write_text(mk)
    if "config BR2_PACKAGE_"+sym+"\n" not in s:
        s+="\nconfig BR2_PACKAGE_"+sym+"\n\tbool \"libretro-"+name+"\"\n\tdefault y\n\tdepends on BR2_INSTALL_LIBSTDCPP\n"
p.write_text(s)
rep("ui/src/settings.cpp",'{ "genesis_plus_gx", "Genesis Plus GX" },','{ "genesis_plus_gx", "Genesis Plus GX" }, { "genesis_plus_gx_wide", "Genesis Plus GX Wide" },')
rep("ui/src/settings.cpp",'{ "bsnes", "bsnes" },','{ "bsnes", "bsnes" }, { "bsnes_hd_beta", "bsnes HD Mode 7" },')
print("Expanded NES, N64, PS1 source hooks and optional Genesis GX Wide / bsnes HD packages integrated.")
