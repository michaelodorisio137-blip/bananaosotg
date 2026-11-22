#!/usr/bin/env python3
"""Expose real native texture filtering in SuperDrastic and GLideN64.

SuperDrastic: Gengis rasterizer 0 nearest, 1 bilinear, 2 sharp bilinear,
3 N64 three-point once rgds-superdrastic-3point.py is applied during its build.
GLideN64: built-in BilinearMode "standard" vs "3point".
These controls do NOT apply full-screen postprocessing.
"""
from pathlib import Path
import sys
if len(sys.argv) != 2:
    sys.exit("Usage: python3 rgds-texture-patch.py /path/to/BananaLinux")
root = Path(sys.argv[1])

def sub(rel, old, new):
    p = root / rel
    text = p.read_text()
    if new in text: return
    if text.count(old) != 1:
        sys.exit("RG DS texture patch upstream mismatch in " + rel + ": " + old[:90])
    p.write_text(text.replace(old, new, 1))

sd = "ui/src/settings.cpp"
sub(sd,
'''add(SD, "nds", "3D resolution", "How sharp DS games' 3D is drawn.", dcfg, "hires_3d", { "1x", "2x" }, { "0", "1" });''',
'''add(SD, "nds", "3D texture filtering", "True Gengis Engine texture sampling on polygons and sprites. Does not blur the completed screen.",
                sd, "DSFLIP_RAST_TEXFILTER", { "Nearest", "Bilinear", "Sharp bilinear", "N64 3-point" }, { "0", "1", "2", "3" });
            items.back().def = "3";
            items.back().hints = { "Original DS point sampling.", "Four texels blended in the 3D rasterizer.", "Four texels with a sharper blend.", "Three texels blended with triangular weights (experimental)." };
            add(SD, "nds", "3D resolution", "How sharp DS games' 3D is drawn.", dcfg, "hires_3d", { "1x", "2x" }, { "0", "1" });''')

run = "system/rootfs/usr/libexec/banana/run-drastic"
sub(run,
'''kv_export /data/banana/superdrastic.conf DSFLIP_ DSHOOK_  # (read, never run: kv-env)''',
'''kv_export /data/banana/superdrastic.conf DSFLIP_ DSHOOK_  # (read, never run: kv-env)
# RG DS native 3D texture sampling, independent of display shader.
# 0 nearest, 1 bilinear, 2 sharp bilinear, 3 N64-style three-point.
[ -n "$DSFLIP_RAST_TEXFILTER" ] || DSFLIP_RAST_TEXFILTER=3
case "$DSFLIP_RAST_TEXFILTER" in 0|1|2|3) ;; *) DSFLIP_RAST_TEXFILTER=3 ;; esac
export DSFLIP_RAST_TEXFILTER
echo "run-drastic: Gengis 3D texture filtering $DSFLIP_RAST_TEXFILTER" >&2''')

sub(sd,
'''add(PS, "picture", "Screen border", "What fills the space around a game's picture.",''',
'''add(PS, "picture", "Nintendo 64 textures",
                "GLideN64's own 3D texture filtering, not a screen shader.",
                menu, "rgds_n64_texfilter", { "N64 3-point", "Bilinear" }, { "3point", "standard" });
            items.back().hints = { "Original N64-style three-point texture sampling.", "Four-point PC-style bilinear sampling." };
            add(PS, "picture", "Screen border", "What fills the space around a game's picture.",''')

defaults = "ui/src/settings_defaults.cpp"
sub(defaults,
'''{ "ra_shader", "off", ENUM, SHADERS, 0, 0, true },''',
'''{ "ra_shader", "off", ENUM, SHADERS, 0, 0, true },
            { "rgds_n64_texfilter", "3point", ENUM, N64_TEXTURE_FILTER, 0, 0, true },''')
sub(defaults,
'''const char* const SHADERS[] = { "off", "lcd", "crt", "sharp", "bilinear", "threepoint", nullptr };''',
'''const char* const SHADERS[] = { "off", "lcd", "crt", "sharp", "bilinear", "threepoint", nullptr };
        const char* const N64_TEXTURE_FILTER[] = { "3point", "standard", nullptr };''')

ra = "system/rootfs/usr/libexec/banana/run-retroarch"
anchor = '# Shaders: Shaders > Load Preset opens the image'
n64hook = r'''# RG DS native N64 core texturing (GLideN64), independent of screen shaders.
# Options: mupen64plus-BilinearMode = "3point" or "standard".
if [ "$BANANA_SYSTEM" = n64 ]; then
    case $(setting rgds_n64_texfilter) in standard) t=standard ;; *) t=3point ;; esac
    opt=/data/retroarch/config/Mupen64Plus-Next/Mupen64Plus-Next.opt
    mkdir -p "$(dirname "$opt")"
    if ! grep -qxF "mupen64plus-BilinearMode = \"$t\"" "$opt" 2>/dev/null; then
        sed -i '/^mupen64plus-BilinearMode = /d' "$opt" 2>/dev/null
        printf 'mupen64plus-BilinearMode = "%s"\n' "$t" >> "$opt"
    fi
fi
'''
sub(ra, anchor, n64hook + anchor)
print("SuperDrastic native filtering and GLideN64 texture-filter controls added.")
