#!/usr/bin/env python3
"""Expose SuperDrastic's already-implemented *rasterizer* texture filtering.

No emulator recompilation needed: JorreFog/SuperDrastic's Gengis Engine
already reads DSFLIP_RAST_TEXFILTER (0=nearest, 1=bilinear, 2=sharp
bilinear) in rast.c and applies it in fused_asm.c's per-polygon texel
sampler. This is NOT the whole-screen shader setting.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2: sys.exit("Usage: python3 rgds-texfilter-patch.py /path/to/BananaLinux")
root=Path(sys.argv[1])
settings=root/"ui/src/settings.cpp"
source=settings.read_text()
before='''\t\t\tadd(SD, "nds", "Shader", shaderHelp, sd, "DSFLIP_SHADER", shaderNames, shaderValues);'''
after=before+'''
            add(SD, "nds", "3D texture filtering",
                "Actual Gengis Engine 3D polygon texel sampling, independent of the picture shader.",
                sd, "DSFLIP_RAST_TEXFILTER",
                { "Original (nearest)", "Bilinear", "Sharp bilinear" }, { "0", "1", "2" });
            items.back().def = "0";
            items.back().hints = {
                "Original DS texture sampling. No filtering.",
                "Samples four texture texels per 3D polygon pixel, not the finished screen.",
                "A sharper 4-texel filter. Not N64 three-point filtering."
            };'''
if after not in source:
    if source.count(before)!=1: sys.exit("SuperDrastic settings page has changed upstream")
    settings.write_text(source.replace(before,after,1))
print("SuperDrastic renderer filtering row installed: nearest/bilinear/sharp bilinear.")
