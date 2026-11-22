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
cp "$SRC" "$DST.new"
mv -f "$DST.new" "$DST"
# Preserve every other existing config value, including the user's GBA core.
sed -i -e '/^[[:space:]]*core\.gb[[:space:]]*=/d' \
       -e '/^[[:space:]]*core\.gbc[[:space:]]*=/d' "$SETTINGS"
printf '\ncore.gb = mgba_expanded\ncore.gbc = mgba_expanded\n' >> "$SETTINGS"
sync
printf 'Installed GB/GBC 320x204 expanded core: %s\nGBA selection untouched. Restart the menu to refresh core settings.\n' "$DST" > "$LOG"
exit 0
