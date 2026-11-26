#!/usr/bin/env python3
"""Opt-in native integer presentation; does not claim new core overscan."""
from pathlib import Path
import sys
import subprocess

root=Path(sys.argv[-1])
def replace(rel,old,new):
    p=root/rel
    s=p.read_text()
    if new in s: return
    if s.count(old)!=1: raise SystemExit("native integer anchor mismatch: "+rel+" "+repr(old[:80]))
    p.write_text(s.replace(old,new,1))

if sys.argv[1]=="--ui":
    replace("ui/src/settings.cpp",
        'add(PS, "picture", "Integer scaling",',
        '''add(PS, "picture", "Native integer mode", "Use whole native pixels across supported emulators. Expanded renderers show real extra background where available; unsupported modes may retain borders.",
                menu, "azeez_native_integer", { "Off", "On" }, { "off", "on" });
            items.back().hints = { "Keep each emulator's existing display settings.", "Sharp square pixels; no fractional zoom." };
            add(PS, "picture", "Integer scaling",''')
    replace("ui/src/settings_defaults.cpp",
        '{ "ra_border", "off", ENUM, ON_OFF, 0, 0, true },',
        '{ "ra_border", "off", ENUM, ON_OFF, 0, 0, true },\n\t\t\t{ "azeez_native_integer", "off", ENUM, ON_OFF, 0, 0, true },')
    sys.exit(0)

base="usr/libexec/banana/"
bf=base+"run-bananafront"
ra=base+"run-retroarch"
ds=base+"run-drastic"
bd=base+"run-bananads"
# Renderer flag and core selection before the frontend starts.
for launcher in (ra,bf):
    marker='CFG=/data/retroarch/retroarch.cfg'
    replace(launcher,marker,'''if [ "$(setting azeez_native_integer)" = on ]; then
    export AZEEZ_EXPANDED_VIEWPORT=1
    case "$BANANA_SYSTEM" in
        nes) VCORE=fceumm ;;
        megadrive) VCORE=genesis_plus_gx_wide ;;
        snes) VCORE=bsnes_hd_beta ;;
        gb|gbc|gba) VCORE=mgba_integer ;;
        *) VCORE= ;;
    esac
    if [ -n "$VCORE" ] && [ -f "/usr/lib/libretro/${VCORE}_libretro.so" ]; then
        CORE="/usr/lib/libretro/${VCORE}_libretro.so"
    fi
fi
'''+marker)
replace(bf,'[ -n "$SH" ] && [ -d /usr/lib/superdrastic/shaders ]',
    '''if [ "$(setting azeez_native_integer)" = on ]; then
    SH=
    export BANANAFRONT_BORDER=off BANANAFRONT_PLANE_SCALE=0
fi
[ -n "$SH" ] && [ -d /usr/lib/superdrastic/shaders ]''')
replace(bf,'if [ "$(ra_cfg video_scale_integer)" = true ] || [ "$CORE" = /usr/lib/libretro/mgba_integer_libretro.so ]; then',
    'if [ "$(setting azeez_native_integer)" = on ] || [ "$(ra_cfg video_scale_integer)" = true ] || [ "$CORE" = /usr/lib/libretro/mgba_integer_libretro.so ]; then')
# Use existing border-config backup/recovery, not the button backup.
replace(ra,"BKEYS='^(aspect_ratio_index|",
    "BKEYS='^(video_shader_enable|video_smooth|aspect_ratio_index|")
replace(ra,'if [ "$(setting ra_border)" = on ] && [ -n "$BANANA_SYSTEM" ]; then',
    '''AZ_INT=0
case "$CORE" in */mgba_integer_libretro.so) AZ_INT=1 ;; esac
[ "$(setting azeez_native_integer)" = on ] && AZ_INT=1
if [ "$AZ_INT" = 0 ] && [ "$(setting ra_border)" = on ] && [ -n "$BANANA_SYSTEM" ]; then''')
p=root/ra
s=p.read_text()
start=s.index("# AzeezOS Maximum Integer: native 640x480, no further interpolation.")
end=s.index("# anything RetroArch keeps that retroarch.cfg doesn't place",start)
s=s[:start]+'''# AzeezOS native integer presentation. Core-provided geometry remains intact.
if [ "$AZ_INT" = 1 ]; then
    grep -E "$BKEYS" "$CFG" > "$BKEEP.new" || :
    mv "$BKEEP.new" "$BKEEP" && sync
    {
        printf '%s\\n' 'video_shader_enable = "false"' 'video_smooth = "false"' 'video_scale_integer = "true"' 'input_overlay_enable = "false"'
        # 21 = square pixel aspect in RetroArch 1.22; preserve dynamic geometry.
        printf '%s\\n' 'aspect_ratio_index = "21"' 'video_viewport_bias_x = "0.500000"' 'video_viewport_bias_y = "0.500000"'
    } > "$BCFG"
    BA="|$BCFG"
fi
'''+s[end:]
s=s.replace('$RA$BA$RBA','$RA$RBA$BA')
p.write_text(s)
# DS integer shader includes matching touchscreen mapping.
readmode=r'''az_native_integer() {
    for f in /data/banana/settings.conf /etc/banana/settings.conf; do
        v=$(sed -n '/^ *azeez_native_integer *= */{s///;h};${x;p}' "$f" 2>/dev/null)
        case "$v" in on) return 0 ;; off) return 1 ;; esac
    done
    return 1
}
'''
replace(ds,'# the 3D always through the Gengis Engine',
    readmode+'''if az_native_integer; then
    export DSFLIP_SHADER=ds-integer DSFLIP_SHADER_DIR=/usr/lib/superdrastic/shaders
fi
# the 3D always through the Gengis Engine''')
replace(bd,'cd $D\nexec /usr/bin/bananads "$ROM"',
    readmode+'''if az_native_integer; then
    export AZEEZ_EXPANDED_VIEWPORT=1 BANANADS_KMS_SHADER=none
    # The renderer keeps native or 2x 3D according to the existing setting.
fi
cd $D
exec /usr/bin/bananads "$ROM"''')
p=root/"etc/banana/settings.conf"
s=p.read_text()
if "azeez_native_integer =" not in s:
    p.write_text(s+"\n# Native integer presentation (opt-in)\nazeez_native_integer = off\n")
for f in (ra,bf,ds,bd):
    subprocess.run(["sh","-n",str(root/f)],check=True)
print("Native integer presentation installed for RetroArch, BananaFront, SuperDrastic, BananaDS")
