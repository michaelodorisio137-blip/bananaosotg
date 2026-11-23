#!/usr/bin/env python3
"""Patch pinned GLideN64 source: unlike txFilterMode=none, this is GL_NEAREST."""
from pathlib import Path
import sys
r=Path(sys.argv[1])
def rep(rel,old,new):
 p=r/rel;s=p.read_text()
 if new in s:return
 if s.count(old)!=1:raise SystemExit("Pinned Mupen source mismatch "+rel+": "+old[:80])
 p.write_text(s.replace(old,new,1))
rep("GLideN64/src/Config.h",
    "#define BILINEAR_STANDARD 1",
    "#define BILINEAR_STANDARD 1\n#define BILINEAR_NEAREST 4 /* force point texture sampling */")
rep("GLideN64/src/Textures.cpp",
    "gDP.otherMode.textureFilter != G_TF_POINT && config.texture.bilinearMode != BILINEAR_3POINT",
    "gDP.otherMode.textureFilter != G_TF_POINT && config.texture.bilinearMode != BILINEAR_3POINT && config.texture.bilinearMode != BILINEAR_NEAREST")
rep("libretro/libretro.c",
    'bilinearMode = !strcmp(var.value, "3point") ? 0 : 1;',
    'bilinearMode = !strcmp(var.value, "3point") ? 0 : (!strcmp(var.value, "nearest") ? 4 : 1);')
rep("libretro/libretro_core_options.h",
    '{"standard", NULL},',
    '{"standard", NULL},\n            {"nearest", NULL},')
print("GLideN64 three modes: 3-point, bilinear, nearest GL_NEAREST.")
