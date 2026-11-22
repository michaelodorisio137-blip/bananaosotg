#!/usr/bin/env python3
"""Experimental mGBA render geometry, based on mgba-emu/mgba issue #1960.

320x204 = 65,280 rendered pixels, 55 below the experiment's *reported*
~65,335 crash point. This is NOT an HD/Mode7 renderer; normal mGBA is kept
as a separate built binary. The experiment can alter GBA H/VBlank timing and
break some games; never ship it as a replacement for the unmodified core.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    sys.exit("Usage: python3 rgds-mgba-viewport-source.py /path/to/libretro-mgba")

root=Path(sys.argv[1])
changes={
    "include/mgba/gba/interface.h": [
        ("GBA_VIDEO_HORIZONTAL_PIXELS = 240,", "GBA_VIDEO_HORIZONTAL_PIXELS = 320,"),
        ("GBA_VIDEO_VERTICAL_PIXELS = 160,", "GBA_VIDEO_VERTICAL_PIXELS = 204,"),
    ],
    "include/mgba/internal/gba/renderers/video-software.h":[
        ("uint8_t endX;", "uint16_t endX;"),
        ("uint32_t scanlineDirty[5];", "uint32_t scanlineDirty[7];"),
    ],
    "include/mgba/internal/gba/video.h":[
        ("uint8_t end;", "uint16_t end;"),
        ("uint8_t start;", "uint16_t start;"),
    ],
    "src/platform/libretro/libretro.c":[
        ("#define VIDEO_WIDTH_MAX  256", "#define VIDEO_WIDTH_MAX  320"),
    ],
}
for rel, replacements in changes.items():
    p=root/rel
    if not p.is_file(): sys.exit("Missing mGBA source: "+str(p))
    s=p.read_text()
    for before,after in replacements:
        if after in s: continue
        if s.count(before)!=1:
            sys.exit("mGBA pinned source changed: "+rel+" / "+before)
        s=s.replace(before,after,1)
    p.write_text(s)
print("mGBA experimental renderer: GBA 320x204 = 65280 logical pixels.")
print("Unmodified mGBA must remain available as the primary, safe core.")
