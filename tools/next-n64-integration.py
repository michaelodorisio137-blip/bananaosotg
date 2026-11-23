#!/usr/bin/env python3
"""Real GLideN64 point sampling as a third N64 texture-filter choice."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
def rep(rel,old,new):
 p=root/rel;s=p.read_text()
 if new in s:return
 if s.count(old)!=1:raise SystemExit("N64 source mismatch "+rel+": "+old[:80])
 p.write_text(s.replace(old,new,1))
pkg="buildroot/package/libretro-mupen64plus-next/"
script=Path(__file__).with_name("next-n64-source.py")
dest=root/pkg/"next-n64-source.py"
dest.write_text(script.read_text())
mk=pkg+"libretro-mupen64plus-next.mk"
rep(mk,"define LIBRETRO_MUPEN64PLUS_NEXT_BUILD_CMDS",
"""define LIBRETRO_MUPEN64PLUS_NEXT_BUILD_CMDS
	python3 $(BR2_EXTERNAL_BANANA_PATH)/package/libretro-mupen64plus-next/next-n64-source.py $(@D)""")
rep("ui/src/settings.cpp",'{ "N64 3-point", "Bilinear" }, { "3point", "standard" }',
    '{ "N64 3-point", "Bilinear", "Nearest neighbor (NEW)" }, { "3point", "standard", "nearest" }')
rep("ui/src/settings_defaults.cpp",
    'const char* const N64_TEXTURE_FILTER[] = { "3point", "standard", nullptr };',
    'const char* const N64_TEXTURE_FILTER[] = { "3point", "standard", "nearest", nullptr };')
rep("system/rootfs/usr/libexec/banana/run-retroarch",
    'case $(setting rgds_n64_texfilter) in standard) t=standard ;; *) t=3point ;; esac',
    'case $(setting rgds_n64_texfilter) in standard) t=standard ;; nearest) t=nearest ;; *) t=3point ;; esac')
print("GLideN64 source hook, NEW nearest texture option, and launcher installed.")
