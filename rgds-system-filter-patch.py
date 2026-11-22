#!/usr/bin/env python3
"""Give every installed RetroArch/BananaFront system its own optional screen filter.

This is purposely labeled SCREEN filtering. The independent native renderer
texture-filtering controls are added only where a core exposes them (Gengis,
GLideN64); other cores are not silently blurred at their texture stage.
"""
from pathlib import Path
import sys
if len(sys.argv) != 2:
    sys.exit("Usage: python3 rgds-system-filter-patch.py /path/to/BananaLinux")
root = Path(sys.argv[1])

def sub(path, old, new):
    p = root / path
    s = p.read_text()
    if new in s: return
    if s.count(old) != 1:
        sys.exit("RG DS per-system filter patch source mismatch: " + path)
    p.write_text(s.replace(old, new, 1))

defs="ui/src/settings_defaults.cpp"
sub(defs,
  'const char* const N64_TEXTURE_FILTER[] = { "3point", "standard", nullptr };',
  'const char* const N64_TEXTURE_FILTER[] = { "3point", "standard", nullptr };\n'
  '        const char* const RGDS_SCREEN_OVERRIDES[] = { "inherit", "off", "bilinear", "threepoint", "lcd", "crt", "sharp", nullptr };')
sub(defs,
  '{ "rgds_n64_texfilter", "3point", ENUM, N64_TEXTURE_FILTER, 0, 0, true },',
  '{ "rgds_n64_texfilter", "3point", ENUM, N64_TEXTURE_FILTER, 0, 0, true },\n'
  '            { "ra_shader_override", "inherit", ENUM, RGDS_SCREEN_OVERRIDES, 0, 0, true, true },')

menu="ui/src/settings.cpp"
anchor = '''add(PS, "picture", "Screen border", "What fills the space around a game's picture.",'''
section = '''// RG DS: independent per-system GPU screen filter, never a texture override.
            // Existing systems and their original rendering defaults are unchanged
            // until a system's override is explicitly selected.
            for (const auto& system : RA_SYSTEMS)
            {
                std::string label = std::string(system.label) + " screen filter";
                std::string key = std::string("ra_shader_override.") + system.id;
                add(PS, "picture", label.c_str(),
                    "GPU filter applied to the finished frame for this system only; not a texture filter.",
                    menu, key.c_str(),
                    { "Global", "Off", "Bilinear", "N64 3-point", "LCD", "CRT", "Sharp pixels" },
                    { "inherit", "off", "bilinear", "threepoint", "lcd", "crt", "sharp" });
                items.back().hints = {
                    "Use the global Shader setting.", "Original output.", "4-tap screen interpolation.",
                    "3-tap screen interpolation.", "LCD grid.", "CRT effect.", "Sharp scaling." };
            }
            '''
sub(menu,anchor,section+anchor)

ra="system/rootfs/usr/libexec/banana/run-retroarch"
sub(ra,'''look=$(setting ra_shader)
SHADE=/data/banana/.ra-shader''',
'''look=$(setting ra_shader)
# A system-specific screen shader overrides only the global screen shader.
if [ -n "$BANANA_SYSTEM" ]; then
    choice=$(setting "ra_shader_override.$BANANA_SYSTEM")
    case $choice in off|lcd|crt|sharp|bilinear|threepoint) look=$choice ;; esac
fi
SHADE=/data/banana/.ra-shader''')
bf="system/rootfs/usr/libexec/banana/run-bananafront"
sub(bf,'''case $(setting ra_shader) in lcd) SH=zfast-lcd ;; crt) SH=zfast-crt ;; sharp) SH=sharp-bilinear ;; bilinear) SH=rgds-bilinear ;; threepoint) SH=rgds-threepoint ;; *) SH= ;; esac''',
'''RGDS_LOOK=$(setting ra_shader)
if [ -n "$BANANA_SYSTEM" ]; then
    choice=$(setting "ra_shader_override.$BANANA_SYSTEM")
    case $choice in off|lcd|crt|sharp|bilinear|threepoint) RGDS_LOOK=$choice ;; esac
fi
case $RGDS_LOOK in lcd) SH=zfast-lcd ;; crt) SH=zfast-crt ;; sharp) SH=sharp-bilinear ;; bilinear) SH=rgds-bilinear ;; threepoint) SH=rgds-threepoint ;; *) SH= ;; esac''')
print("System-specific screen shader controls added to every standard RetroArch/BananaFront system.")
