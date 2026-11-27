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
rep("ui/src/settings.cpp",
    'items.back().hints = { "Original N64-style three-point texture sampling.", "Four-point PC-style bilinear sampling." };',
    'items.back().hints = { "Original N64-style three-point texture sampling.", "Four-point PC-style bilinear sampling.", "Nearest-neighbor: one texture texel per sample without blending." };')
rep("system/rootfs/usr/libexec/banana/run-retroarch",
    'case $(setting rgds_n64_texfilter) in standard) t=standard ;; *) t=3point ;; esac',
    'case $(setting rgds_n64_texfilter) in standard) t=standard ;; nearest) t=nearest ;; *) t=3point ;; esac')
rep("ui/src/settings.cpp",
    'add(PS, "picture", "Nintendo 64 textures",',
    '''add(PS, "picture", "Nintendo 64 resolution",
                "Choose native game buffers or a higher-resolution 3D render. Restart the game to apply.",
                menu, "azeez_n64_resolution", { "240p fast (2x display)", "Native 480p", "Original core settings" }, { "240p", "480p", "original" });
            items.back().hints = { "Native game framebuffers, 640x480 presentation.", "640x480 render target; may be slower.", "Restore existing core resolution options." };
            add(PS, "picture", "Nintendo 64 borders",
                "Fill VI margins with nearest sampling, or preserve the original scanout.",
                menu, "azeez_n64_borders", { "Fill VI margins", "Original scanout" }, { "fill", "original" });
            items.back().hints = { "Can use noninteger scaling; game-drawn bars remain.", "Preserves original framing." };
            add(PS, "picture", "Nintendo 64 textures",''')
rep("ui/src/settings_defaults.cpp",
    'const char* const N64_TEXTURE_FILTER[] =',
    '''const char* const AZ_N64_RESOLUTION[] = { "240p", "480p", "original", nullptr };
        const char* const AZ_N64_BORDERS[] = { "fill", "original", nullptr };
        const char* const N64_TEXTURE_FILTER[] =''')
rep("ui/src/settings_defaults.cpp",
    '{ "rgds_n64_texfilter", "3point", ENUM, N64_TEXTURE_FILTER, 0, 0, true },',
    '''{ "rgds_n64_texfilter", "3point", ENUM, N64_TEXTURE_FILTER, 0, 0, true },
            { "azeez_n64_resolution", "240p", ENUM, AZ_N64_RESOLUTION, 0, 0, true },
            { "azeez_n64_borders", "fill", ENUM, AZ_N64_BORDERS, 0, 0, true },''')
rep("system/rootfs/usr/libexec/banana/run-retroarch",
    '# RG DS native N64 core texturing',
    '''# AzeezOS N64 modes; do not rewrite persistent core options or game overrides.
if [ "$BANANA_SYSTEM" = n64 ]; then
    case "$(setting azeez_n64_resolution)" in
        480p) AZEEZ_N64_MODE=480p ;;
        original) AZEEZ_N64_MODE=original ;;
        *) AZEEZ_N64_MODE=240p ;;
    esac
    export AZEEZ_N64_MODE
    if [ "$AZEEZ_N64_MODE" != original ] && [ "$(setting azeez_n64_borders)" != original ]; then
        export AZEEZ_N64_FILL=1
    fi
fi
# RG DS native N64 core texturing''')
print("GLideN64 source hook, nearest filter and N64 presentation options installed.")
