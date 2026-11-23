#!/bin/bash
# AzeezOS / RG DS GB+GBC expanded-viewport installer. Port script.
# Installs to writable SD data and selects the experimental core for GB and GBC.
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/AzeezGBViewport/mgba_expanded_libretro.so"
DST="/data/retroarch/cores/mgba_expanded_libretro.so"
SETTINGS="/data/banana/settings.conf"
LOG="/data/banana/gb-gbc-viewport.log"
mkdir -p /data/banana /data/retroarch/cores
if [ ! -s "$SRC" ]; then
  printf 'FAILED: experimental GB/GBC core is missing from %s\n' "$SRC" > "$LOG"
  exit 1
fi
if [ ! -f "$SETTINGS" ]; then
  cp /etc/banana/settings.conf "$SETTINGS"
fi
# A real, separately identified expanded core. Reject the old build which
# used standard mGBA's options identity and confused on-device diagnostics.
if ! grep -aq 'mGBA Expanded RGDS' "$SRC"; then
  printf 'FAILED: older package had standard mGBA identity; refusing to install.\n' > "$LOG"
  exit 1
fi
cp "$SRC" "$DST.new"
mv -f "$DST.new" "$DST"
# Preserve every other existing config value, including the user's GBA core.
sed -i -e '/^[[:space:]]*core\.gb[[:space:]]*=/d' \
       -e '/^[[:space:]]*core\.gbc[[:space:]]*=/d' "$SETTINGS"
printf '\ncore.gb = mgba_expanded\ncore.gbc = mgba_expanded\n' >> "$SETTINGS"
sync
if ! grep -Eq '^core\\.gb = mgba_expanded
 "$SETTINGS" ||
   ! grep -Eq '^core\\.gbc = mgba_expanded
 "$SETTINGS" ||
   ! test -s "$DST"; then
  printf 'FAILED: GB/GBC emulator selection was not saved correctly.\n' > "$LOG"
  exit 1
fi
printf 'AzeezOS GB/GBC expanded viewport: INSTALLED\n' > "$LOG"
printf 'Game Boy selected core: mgba_expanded\nGame Boy Color selected core: mgba_expanded\n' >> "$LOG"
printf 'Installed shared core: %s\n' "$DST" >> "$LOG"
printf 'Core identity: mGBA Expanded RGDS\nTarget video size: 320x204\n' >> "$LOG"
printf 'GBA core selection: unchanged\n' >> "$LOG"
printf 'The firmware UI may retain old core names until updated.\n' >> "$LOG"
printf 'The new core is loaded by the existing GB and GBC launch scripts.\n' >> "$LOG"
cp "$LOG" "$DIR/AzeezGBViewport/INSTALL-STATUS.txt"
exit 0
