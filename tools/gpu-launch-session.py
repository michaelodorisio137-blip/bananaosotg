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
    vboycolor|mednafen_vb) BANANA_SYSTEM=virtualboy ;;
esac
export BANANA_SYSTEM
AZ_SELECTED=$(setting "core.$BANANA_SYSTEM")
case "$AZ_SELECTED" in ""|auto|*[!A-Za-z0-9_+.-]*) AZ_SELECTED= ;; esac
AZ_CHOSEN=
if [ -n "$AZ_SELECTED" ]; then
    for d in /data/retroarch/cores /usr/lib/libretro; do
        [ -s "$d/${AZ_SELECTED}_libretro.so" ] && { AZ_CHOSEN="$d/${AZ_SELECTED}_libretro.so"; break; }
    done
fi
# Explicit downloaded and unclassified cores use RetroArch; its core negotiates the graphics API.
AZ_OTHER=0
case "$AZ_SELECTED" in
    ""|gpsp|mgba|mgba_integer|mgba_expanded|gambatte|fceumm|snes9x|bananasnes|genesis_plus_gx_wide|picodrive|mednafen_vb|vboycolor) ;;
    *) [ -z "$AZ_CHOSEN" ] || AZ_OTHER=1 ;;
esac
case "$AZ_CHOSEN" in /data/retroarch/cores/*) AZ_OTHER=1 ;; esac
AZ_GBA_GPU=0
if [ "$BANANA_SYSTEM" = gba ] && [ -s /usr/lib/libretro/mgba_gles_preview_libretro.so ]; then
    if [ "$AZ_SELECTED" = mgba_gles_preview ] || { [ -z "$AZ_CHOSEN" ] && { [ -f /data/banana/gba-gpu.enable ] || [ -f /data/banana/gba-3d-trace.enable ]; }; }; then
        AZ_GBA_GPU=1
    fi
fi
case "$BANANA_SYSTEM:$AZ_GBA_GPU:$AZ_OTHER" in
n64:*|psx:*|saturn:*|psp:*|virtualboy:*|:*|gba:1:*|*:*:1) ;;""")
# Explicitly select the packaged GPU cores; preserve downloaded alternative if
# the Saturn core is absent. Do not alter unrelated core settings.
rep('[ -f "$CORE" ] || { echo "no core $1" >&2; exit 1; }',
    """# Azeez packaged GPU core resolution (defaults only)
if [ -z "$AZ_CHOSEN" ]; then
case "$BANANA_SYSTEM" in
    saturn)
        for d in /usr/lib/libretro /data/retroarch/cores; do
            [ -s "$d/yabasanshiro_libretro.so" ] && { CORE="$d/yabasanshiro_libretro.so"; break; }
        done ;;
    psp)
        [ -s /usr/lib/libretro/ppsspp_azeez_libretro.so ] && CORE=/usr/lib/libretro/ppsspp_azeez_libretro.so ;;
    virtualboy)
        [ -s /usr/lib/libretro/mednafen_vb_libretro.so ] && CORE=/usr/lib/libretro/mednafen_vb_libretro.so ;;
esac
else
    CORE="$AZ_CHOSEN"
fi
[ "$AZ_GBA_GPU" = 1 ] && CORE=/usr/lib/libretro/mgba_gles_preview_libretro.so
[ -f "$CORE" ] || { echo "no core $1" >&2; exit 1; }""")
rep('CFG=/data/retroarch/retroarch.cfg', '''# Honor an explicit installed core after Native Integer routing.
[ -z "$AZ_CHOSEN" ] || CORE="$AZ_CHOSEN"
if [ "$AZ_GBA_GPU" = 1 ]; then
    CORE=/usr/lib/libretro/mgba_gles_preview_libretro.so
fi
if [ "$BANANA_SYSTEM" = virtualboy ] && [ "${CORE##*/}" = mednafen_vb_libretro.so ]; then
    export AZEEZ_EXPANDED_VIEWPORT=1
fi
CFG=/data/retroarch/retroarch.cfg''')
rep("BKEYS='^(video_shader_enable|video_smooth|",
    "BKEYS='^(video_driver|video_context_driver|video_threaded|video_max_swapchain_images|crt_switch_resolution|auto_overrides_enable|system_directory|video_shader_enable|video_smooth|")
anchor="# anything RetroArch keeps that retroarch.cfg doesn't place"
rep(anchor, """# Azeez GPU session settings. Reuse the existing crash-safe config backup.
# No changes to the user's global driver, CRT, or integer-scaling preferences.
if [ "$BANANA_SYSTEM" = virtualboy ] && [ "${CORE##*/}" = mednafen_vb_libretro.so ]; then
    if [ -z "$BA" ]; then
        grep -E "$BKEYS" "$CFG" > "$BKEEP.new" || :
        mv "$BKEEP.new" "$BKEEP" && sync
    fi
    cat > "$BCFG" <<'AZ_VB'
video_shader_enable = "false"
video_smooth = "false"
video_scale_integer = "true"
aspect_ratio_index = "21"
video_viewport_bias_x = "0.500000"
video_viewport_bias_y = "0.500000"
input_overlay_enable = "false"
AZ_VB
    BA="|$BCFG"
fi
case "$BANANA_SYSTEM:$AZ_GBA_GPU:$AZ_OTHER" in
saturn:*|psp:*|gba:1:*|*:*:1)
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
aspect_ratio_index = "0"
input_overlay_enable = "false"
AZ_GPU
    if [ "$BANANA_SYSTEM" = saturn ]; then
        # Locate the required BIOS without altering user's configured files.
        BIOSDIR=$(sed -n 's/^system_directory = "\\(.*\\)"/\\1/p' "$CFG" | tail -n 1)
        AZ_SATURN_BIOS=
        SDROM=$(cat /run/banana/sd2/roms 2>/dev/null || :)
        ROMDIR=$(dirname "$2")
        for d in "$BIOSDIR" /data/bios /data/bios/saturn /data/bios/Saturn /data/retroarch/system /data/retroarch/system/saturn "$ROMDIR" "$ROMDIR/bios" "${ROMDIR%/*}/bios" "${SDROM%/roms}/bios" "${SDROM%/roms}/bios/saturn"; do
            [ -n "$d" ] && [ -d "$d" ] || continue
            for f in "$d"/*; do
                [ -f "$f" ] || continue
                n=$(basename "$f" | tr '[:upper:]' '[:lower:]')
                case "$n" in saturn_bios.bin|sega_101.bin|mpr-17933.bin) ;; *) continue ;; esac
                [ "$(wc -c < "$f")" -eq 524288 ] || continue
                mkdir -p /run/banana/saturn-bios
                rm -f /run/banana/saturn-bios/saturn_bios.bin /run/banana/saturn-bios/sega_101.bin /run/banana/saturn-bios/mpr-17933.bin
                ln -s "$f" "/run/banana/saturn-bios/$n" || continue
                AZ_SATURN_BIOS="$f"
                printf 'system_directory = "/run/banana/saturn-bios"\\n' >> "$BCFG"
                break 2
            done
        done
        if [ -z "$AZ_SATURN_BIOS" ]; then
            echo "Azeez Saturn: no recognized 512 KiB BIOS found" >&2
        fi
    fi
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
        grep '^system_directory = ' "$BCFG" >> "$AZ_GPU_LOG" || :
        printf 'bios=%s\n' "${AZ_SATURN_BIOS:-NOT FOUND}" >> "$AZ_GPU_LOG"
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
# On each installed OTA version, select the bundled revised DS/GBA emulators
# once before the UI reads settings. Subsequent user choices are respected.
migration=root/"usr/libexec/banana/azeez-updated-core-defaults"
migration.write_text(r'''#!/bin/sh
set -eu
D=/data/banana
C=$D/settings.conf
M=$D/.azeez-core-defaults-version
V=$(cat /etc/banana/version)
[ -n "$V" ] || exit 1
[ "$(cat "$M" 2>/dev/null || :)" != "$V" ] || exit 0
[ -s /usr/bin/bananads ] && [ -s /usr/lib/libretro/mgba_gles_preview_libretro.so ] || exit 0
mkdir -p "$D"
[ -f "$C" ] || cp /etc/banana/settings.conf "$C"
tmp=$(mktemp "$D/.core-defaults.XXXXXX")
trap 'rm -f "$tmp"' EXIT HUP INT TERM
# Preserve all unrelated settings and per-game overrides.
awk '!/^[ \t]*(nds_emulator|core[.]gba)[ \t]*=/' "$C" > "$tmp"
printf '%s\n' 'nds_emulator = bananads' 'core.gba = mgba_gles_preview' >> "$tmp"
# Restore the expanded core as default; color remains selectable until it supports the viewport.
if [ -s /usr/lib/libretro/mednafen_vb_libretro.so ]; then
    awk '!/^[ \t]*core[.]virtualboy[ \t]*=/' "$tmp" > "$tmp.vb"
    printf '%s\n' 'core.virtualboy = mednafen_vb' >> "$tmp.vb"
    mv "$tmp.vb" "$tmp"
fi
chmod 0644 "$tmp"
mv "$tmp" "$C"
printf '%s\n' "$V" > "$M.new"
mv "$M.new" "$M"
sync
echo "AzeezOS $V: selected updated DS and GBA renderers"
''')
migration.chmod(0o755)
session=root/"usr/bin/banana-ui-session"
ss=session.read_text()
a="exec /usr/bin/banana-ui"
if ss.count(a)!=1: raise SystemExit("UI startup anchor mismatch")
ss=ss.replace(a,'/usr/libexec/banana/azeez-updated-core-defaults >> "$LOG" 2>&1 || :\n'+a)
session.write_text(ss)
subprocess.run(["sh","-n",str(migration)],check=True)
subprocess.run(["sh","-n",str(session)],check=True)
bf=root/"usr/libexec/banana/run-bananafront"
bs=bf.read_text()
a="CFG=/data/retroarch/retroarch.cfg"
assert bs.count(a)==1
bs=bs.replace(a,r'''# An explicit installed choice outranks automatic native-integer substitutions.
AZ_SELECTED=$(setting "core.$BANANA_SYSTEM")
case "$AZ_SELECTED" in ""|auto|*[!A-Za-z0-9_+.-]*) ;;
*) for d in /data/retroarch/cores /usr/lib/libretro; do
    [ -s "$d/${AZ_SELECTED}_libretro.so" ] && { CORE="$d/${AZ_SELECTED}_libretro.so"; break; }
done ;;
esac
CFG=/data/retroarch/retroarch.cfg'''.replace("\\$", "$"),1)
bf.write_text(bs)
subprocess.run(["sh","-n",str(bf)],check=True)
subprocess.run(["sh","-n",str(p)],check=True)
print("PASS: Saturn and PSP GPU launcher isolation, packaged core and menu checks")
