#!/usr/bin/env python3
"""Isolate GPU-required core launches from shared RetroArch settings."""
from pathlib import Path
import re, sys, subprocess
root=Path(sys.argv[1])
p=root/"usr/libexec/banana/run-retroarch"
s=p.read_text()
def rep(a,b):
    global s
    if b in s: return
    if s.count(a)!=1: raise SystemExit("GPU launcher anchor mismatch: "+repr(a))
    s=s.replace(a,b,1)
# A stale or absent menu system id must not send hardware cores to BananaFront.
rep("case $BANANA_SYSTEM in\nn64|psx|saturn|psp|\"\") ;;",
    """# Azeez GPU-only launch routing
case "$1" in
    yabasanshiro) BANANA_SYSTEM=saturn ;;
    ppsspp|ppsspp_azeez) BANANA_SYSTEM=psp ;;
esac
export BANANA_SYSTEM
AZ_GBA_GPU=0
if [ "$BANANA_SYSTEM" = gba ] && [ -s /usr/lib/libretro/mgba_gles_preview_libretro.so ]; then
    if [ "$(setting core.gba)" = mgba_gles_preview ] || [ -f /data/banana/gba-gpu.enable ] || [ -f /data/banana/gba-3d-trace.enable ]; then
        AZ_GBA_GPU=1
    fi
fi
case "$BANANA_SYSTEM:$AZ_GBA_GPU" in
n64:*|psx:*|saturn:*|psp:*|:*|gba:1) ;;""")
# Explicitly select the packaged GPU cores; preserve downloaded alternative if
# the Saturn core is absent. Do not alter unrelated core settings.
rep('[ -f "$CORE" ] || { echo "no core $1" >&2; exit 1; }',
    """# Azeez packaged GPU core resolution
case "$BANANA_SYSTEM" in
    saturn)
        for d in /usr/lib/libretro /data/retroarch/cores; do
            [ -s "$d/yabasanshiro_libretro.so" ] && { CORE="$d/yabasanshiro_libretro.so"; break; }
        done ;;
    psp)
        [ -s /usr/lib/libretro/ppsspp_azeez_libretro.so ] && CORE=/usr/lib/libretro/ppsspp_azeez_libretro.so ;;
esac
[ "$AZ_GBA_GPU" = 1 ] && CORE=/usr/lib/libretro/mgba_gles_preview_libretro.so
[ -f "$CORE" ] || { echo "no core $1" >&2; exit 1; }""")
rep('CFG=/data/retroarch/retroarch.cfg', '''# Preserve the selected GPU core after Native Integer routing.
if [ "$AZ_GBA_GPU" = 1 ]; then
    CORE=/usr/lib/libretro/mgba_gles_preview_libretro.so
fi
CFG=/data/retroarch/retroarch.cfg''')
rep("BKEYS='^(video_shader_enable|video_smooth|",
    "BKEYS='^(video_driver|video_context_driver|video_threaded|video_max_swapchain_images|crt_switch_resolution|auto_overrides_enable|video_shader_enable|video_smooth|")
anchor="# anything RetroArch keeps that retroarch.cfg doesn't place"
rep(anchor, """# Azeez GPU session settings. Reuse the existing crash-safe config backup.
# No changes to the user's global driver, CRT, or integer-scaling preferences.
case "$BANANA_SYSTEM:$AZ_GBA_GPU" in
saturn:*|psp:*|gba:1)
    if [ -z "$BA" ]; then
        grep -E "$BKEYS" "$CFG" > "$BKEEP.new" || :
        mv "$BKEEP.new" "$BKEEP" && sync
        : > "$BCFG"
    fi
    cat > "$BCFG" <<'AZ_GPU'
video_driver = "gl"
video_context_driver = "kms"
video_threaded = "false"
video_max_swapchain_images = "3"
crt_switch_resolution = "0"
auto_overrides_enable = "false"
video_shader_enable = "false"
video_smooth = "false"
video_scale_integer = "false"
aspect_ratio_index = "22"
input_overlay_enable = "false"
AZ_GPU
    BA="|$BCFG"
    echo "Azeez GPU session: $BANANA_SYSTEM $CORE, GL/KMS" >&2
    ;;
esac
"""+anchor)
# Existing card-specific systems.conf overrides may be stale. The new default
# launch path is verified; do not overwrite user's custom systems.conf.
for system,core in (("saturn","yabasanshiro"),("psp","ppsspp_azeez")):
    f=root/"usr/lib/libretro"/(core+"_libretro.so")
    if not f.is_file() or f.stat().st_size==0: raise SystemExit("Missing "+str(f))
    conf=(root/"etc/banana/systems.conf").read_text()
    m=re.search(r"(?m)^\["+system+r"\]\n((?:(?!^\[)[\s\S])*)",conf)
    if not m or ("run = /usr/libexec/banana/run-retroarch "+core+" %ROM%") not in m[1]:
        raise SystemExit("Missing or incorrect menu launcher: "+system)
# Retain diagnostics locally for GPU launches (including early failures).
rep('MON=$(sed -n', r'''AZ_GPU_LOG=
case "$BANANA_SYSTEM:$AZ_GBA_GPU" in
saturn:*|psp:*|gba:1)
    mkdir -p /data/banana/launch-logs /run/banana
    AZ_GPU_LOG=/data/banana/launch-logs/$BANANA_SYSTEM.log
    rm -f /run/banana/retroarch.log
    printf '%s\n' "core=$CORE" "system=$BANANA_SYSTEM" > "$AZ_GPU_LOG"
    if [ "$BANANA_SYSTEM" = saturn ]; then
        grep '^system_directory = ' "$CFG" >> "$AZ_GPU_LOG" || :
        for bios in saturn_bios.bin sega_101.bin mpr-17933.bin; do
            [ ! -f "/data/bios/$bios" ] || ls -l "/data/bios/$bios" >> "$AZ_GPU_LOG"
        done
    fi
    ;;
esac
MON=$(sed -n''')
rep('    retroarch --config $CFG --appendconfig "$L|$RA$RBA$BA" -L "$CORE" "$2" < $FIFO &',
    '''    if [ -n "$AZ_GPU_LOG" ]; then
        retroarch --config $CFG --appendconfig "$L|$RA$RBA$BA" --verbose --log-file /run/banana/retroarch.log -L "$CORE" "$2" < $FIFO >> "$AZ_GPU_LOG" 2>&1 &
    else
        retroarch --config $CFG --appendconfig "$L|$RA$RBA$BA" -L "$CORE" "$2" < $FIFO &
    fi''')
rep('/usr/libexec/banana/ra-secrets scrub; rm -f $RA', r'''if [ -n "$AZ_GPU_LOG" ]; then
    [ ! -f /run/banana/retroarch.log ] || tail -c 262144 /run/banana/retroarch.log >> "$AZ_GPU_LOG"
    printf 'exit=%s\n' "$S" >> "$AZ_GPU_LOG"
fi
/usr/libexec/banana/ra-secrets scrub; rm -f $RA''')
p.write_text(s)
subprocess.run(["sh","-n",str(p)],check=True)
print("PASS: Saturn and PSP GPU launcher isolation, packaged core and menu checks")
