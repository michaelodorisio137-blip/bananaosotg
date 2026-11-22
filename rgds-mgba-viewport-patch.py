#!/usr/bin/env python3
"""Add the *optional* mGBA 320x204 experiment to original RG DS firmware.

Build unmodified mGBA first, save its .so, patch the same pinned source,
build once more as mgba_expanded_libretro.so. The existing GBA core selection
menu already detects installed cores: add its label, do not alter defaults.
"""
from pathlib import Path
import shutil,sys
if len(sys.argv)!=2: sys.exit("Usage: python3 rgds-mgba-viewport-patch.py /path/to/BananaLinux")
root=Path(sys.argv[1])
source=Path(__file__).with_name("rgds-mgba-viewport-source.py")
if not source.is_file(): sys.exit("Missing wide-viewport source patch")
dest=root/"buildroot/package/libretro-mgba/rgds-mgba-viewport-source.py"
shutil.copyfile(source,dest)

p=root/"buildroot/package/libretro-mgba/libretro-mgba.mk"
old='''define LIBRETRO_MGBA_INSTALL_TARGET_CMDS
\t$(INSTALL) -D -m 0644 $$(find $(@D) -name mgba_libretro.so | head -1) $(TARGET_DIR)/usr/lib/libretro/mgba_libretro.so
endef'''
new='''# Original RG DS experimental mGBA core: build once in untouched 240x160
# mode, then rebuild a second 320x204 variant. The standard binary and user
# default are preserved; this never silently changes any game.
define LIBRETRO_MGBA_RGDS_EXPANDED
\t@set -eu; \\
\torig=$$(find $(@D) -type f -name mgba_libretro.so | head -1); \\
\ttest -s "$$orig"; \\
\tcp "$$orig" $(@D)/mgba_original_libretro.so; \\
\tpython3 $(BR2_EXTERNAL_BANANA_PATH)/package/libretro-mgba/rgds-mgba-viewport-source.py $(@D); \\
\tcmake --build $(@D) --parallel $(PARALLEL_JOBS); \\
\ttest -s "$$orig"; \\
\tcp "$$orig" $(@D)/mgba_expanded_libretro.so
endef
LIBRETRO_MGBA_POST_BUILD_HOOKS += LIBRETRO_MGBA_RGDS_EXPANDED

define LIBRETRO_MGBA_INSTALL_TARGET_CMDS
\t$(INSTALL) -D -m 0644 $(@D)/mgba_original_libretro.so $(TARGET_DIR)/usr/lib/libretro/mgba_libretro.so
\t$(INSTALL) -D -m 0644 $(@D)/mgba_expanded_libretro.so $(TARGET_DIR)/usr/lib/libretro/mgba_expanded_libretro.so
endef'''
s=p.read_text()
if new not in s:
    if s.count(old)!=1: sys.exit("Upstream libretro-mgba.mk build recipe changed")
    p.write_text(s.replace(old,new,1))
ui=root/"ui/src/settings.cpp"
s=ui.read_text()
before='{ "gba", "Game Boy Advance", { { "gpsp", "gpSP" }, { "mgba", "mGBA" },'
after='{ "gba", "Game Boy Advance", { { "gpsp", "gpSP" }, { "mgba", "mGBA" }, { "mgba_expanded", "mGBA Expanded 320x204 (experimental)" },'
if after not in s:
    if s.count(before)!=1: sys.exit("Game Boy Advance core selection list changed")
    ui.write_text(s.replace(before,after,1))
print("RG DS core selector: gpSP / standard mGBA / experimental mGBA 320x204.")
print("Default core and every standard emulator path preserved.")
