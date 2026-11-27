#!/usr/bin/env python3
"""Build third mGBA core and expose it for GB, GBC and GBA."""
from pathlib import Path
import shutil,sys
root=Path(sys.argv[1])
pkg=root/"buildroot/package/libretro-mgba"
shutil.copyfile(Path(__file__).with_name("next-integer-viewport-source.py"),pkg/"next-integer-viewport-source.py")
p=pkg/"libretro-mgba.mk";s=p.read_text()
anchor='\tpython3 $(BR2_EXTERNAL_BANANA_PATH)/package/libretro-mgba/rgds-mgba-viewport-source.py $(@D);'
assert s.count(anchor)==1
# Temporarily patch the stock source BEFORE the existing expanded build.
# Restore it, so all three cores remain separate and independently selectable.
lines=[
'\tcp $(@D)/src/platform/libretro/libretro.c $(@D)/libretro.stock.c;',
'\tcp $(@D)/src/gba/renderers/video-software.c $(@D)/video-software.stock.c;',
'\tpython3 $(BR2_EXTERNAL_BANANA_PATH)/package/libretro-mgba/next-integer-viewport-source.py $(@D);',
'\tcmake --build $(@D) --parallel $(PARALLEL_JOBS);',
'\ttest -s "$$orig";',
'\tcp "$$orig" $(@D)/mgba_integer_libretro.so;',
'\tmv $(@D)/libretro.stock.c $(@D)/src/platform/libretro/libretro.c;',
'\tmv $(@D)/video-software.stock.c $(@D)/src/gba/renderers/video-software.c;',
'\ttouch $(@D)/src/gba/renderers/video-software.c;',
'\ttouch $(@D)/src/platform/libretro/libretro.c;',
]
s=s.replace(anchor,(' \\'+'\n').join(lines)+' \\'+'\n'+anchor,1)
anchor='\t$(INSTALL) -D -m 0644 $(@D)/mgba_expanded_libretro.so $(TARGET_DIR)/usr/lib/libretro/mgba_expanded_libretro.so'
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n\t$(INSTALL) -D -m 0644 $(@D)/mgba_integer_libretro.so $(TARGET_DIR)/usr/lib/libretro/mgba_integer_libretro.so',1)
p.write_text(s)
p=root/"ui/src/settings.cpp";s=p.read_text()
a='{ "mgba_expanded", "NEW - mGBA Expanded 320x204" },'
assert s.count(a)==3, s.count(a)
s=s.replace(a,a+' { "mgba_integer", "mGBA Maximum Integer (NEW)" },')
p.write_text(s)
print("PASS: separate stock, expanded and maximum integer cores and menu entries.")
