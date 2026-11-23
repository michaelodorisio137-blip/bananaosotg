#!/bin/bash
# NEW - GB/GBC Expanded Viewport: install shared wide mGBA core from SD.
# Never modifies the system partition or GBA emulator selection.
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/AzeezGBViewport/mgba_expanded_libretro.so"
DST="/data/retroarch/cores/mgba_expanded_libretro.so"
SETTINGS="/data/banana/settings.conf"
LOG="/data/banana/gb-gbc-viewport.log"
STATUS="$DIR/AzeezGBViewport/INSTALL-STATUS.txt"
mkdir -p /data/banana /data/retroarch/cores "$DIR/AzeezGBViewport"
fail() {
  printf 'NEW - GB/GBC Expanded Viewport FAILED: %s\n' "$1" | tee "$LOG" "$STATUS"
  exit 1
}
[ -s "$SRC" ] || fail "Experimental GB/GBC core is missing: $SRC"
# Unlike the earlier experimental package, this one has an independent core
# identity, so the menu does not reuse normal mGBA's core options.
grep -q 'mGBA Expanded RGDS' "$SRC" || fail "Wrong/older mGBA core; download the revised package."
if [ ! -f "$SETTINGS" ]; then
  [ -f /etc/banana/settings.conf ] || fail "System settings template not found"
  cp /etc/banana/settings.conf "$SETTINGS"
fi
if [ ! -e /data/banana/settings.gb-gbc-before-expanded.conf ]; then
  cp "$SETTINGS" /data/banana/settings.gb-gbc-before-expanded.conf
fi
cp "$SRC" "$DST.new" || fail "Could not copy the expanded core to SD."
mv -f "$DST.new" "$DST"
# The launchers read these per-system selectors on each game start.
sed -i -e '/^[[:space:]]*core\.gb[[:space:]]*=/d' \
       -e '/^[[:space:]]*core\.gbc[[:space:]]*=/d' "$SETTINGS"
printf '\ncore.gb = mgba_expanded\ncore.gbc = mgba_expanded\n' >> "$SETTINGS"
sync
grep -q '^core\.gb = mgba_expanded$' "$SETTINGS" || fail "GB core setting not saved."
grep -q '^core\.gbc = mgba_expanded$' "$SETTINGS" || fail "GBC core setting not saved."
[ -s "$DST" ] || fail "Expanded libretro core missing after install."
{
  echo "NEW - GB/GBC Expanded Viewport: INSTALLED"
  echo "Game Boy = mGBA Expanded RGDS"
  echo "Game Boy Color = mGBA Expanded RGDS"
  echo "Video output for both = 320x204 (GB/GBC original 160x144 centred)"
  echo "Installed file: $DST"
  echo "GBA core selection: unchanged"
  echo "The stock firmware's emulator Settings menu won't list this core until the OS UI is updated."
  echo "Launch GB or GBC games from the game library as usual."
} > "$LOG"
cp "$LOG" "$STATUS"
exit 0
