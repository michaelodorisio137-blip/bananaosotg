#!/bin/bash
# Return GB/GBC to stock Gambatte; leave GBA and the experimental .so alone.
set -eu
SETTINGS=/data/banana/settings.conf
LOG=/data/banana/gb-gbc-viewport.log
[ -f "$SETTINGS" ] || exit 1
sed -i -e '/^[[:space:]]*core\.gb[[:space:]]*=/d' \
       -e '/^[[:space:]]*core\.gbc[[:space:]]*=/d' "$SETTINGS"
printf '\ncore.gb = gambatte\ncore.gbc = gambatte\n' >> "$SETTINGS"
sync
printf 'Restored Gambatte for GB and GBC. GBA selection untouched.\n' > "$LOG"
exit 0
