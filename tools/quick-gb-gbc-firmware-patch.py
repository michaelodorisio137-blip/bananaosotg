#!/usr/bin/env python3
"""Activate the existing RG DS firmware-built expanded GB/GBC libretro core.

Runs on an *extracted firmware rootfs*, not on the user's SD card.
The update writes the inactive OS slot with the standard BananaOS updater.
Existing ROMs, settings, and data partition stay untouched until a first-boot
one-shot migration selects the newly installed core for GB and GBC.
"""
from pathlib import Path
import sys

if len(sys.argv) not in (2, 3):
    sys.exit("Usage: quick-gb-gbc-firmware-patch.py [--verify] ROOTFS")
verify = len(sys.argv) == 3 and sys.argv[1] == "--verify"
root = Path(sys.argv[-1])
core = root / "usr/lib/libretro/mgba_expanded_libretro.so"
assert core.is_file() and core.stat().st_size > 100_000, "Native expanded mGBA core missing"

marker = "NEW GB GBC Expanded"
script = root / "usr/libexec/banana/data-layout"
assert script.is_file()
text = script.read_text()
migration = r'''
# NEW GB GBC Expanded: one-time migration after this firmware is installed.
# On updates, /data/banana/settings.conf already exists and the readonly
# /etc/banana/settings.conf default is NOT copied again. Select both cores
# explicitly in the persistent settings used by BananaFront and RetroArch.
if [ ! -f "$D/banana/.new-gb-gbc-expanded-v1" ]; then
    S="$D/banana/settings.conf"
    if [ -f "$S" ]; then
        cp "$S" "$D/banana/settings.before-new-gb-gbc.conf"
        sed -i -e '/^[[:space:]]*core\.gb[[:space:]]*=/d' \
               -e '/^[[:space:]]*core\.gbc[[:space:]]*=/d' "$S"
        printf '\ncore.gb = mgba_expanded\ncore.gbc = mgba_expanded\n' >> "$S"
        sync
        if grep -q '^core\.gb = mgba_expanded$' "$S" &&
           grep -q '^core\.gbc = mgba_expanded$' "$S"; then
            printf 'NEW GB GBC Expanded firmware: selected mGBA Expanded 320x204 for GB and GBC\n' > "$D/banana/NEW-GB-GBC-FIRMWARE-STATUS.txt"
            touch "$D/banana/.new-gb-gbc-expanded-v1"
        else
            printf 'NEW GB GBC Expanded firmware: FAILED to save emulator selection\n' > "$D/banana/NEW-GB-GBC-FIRMWARE-STATUS.txt"
        fi
    fi
fi
'''
if not verify:
    assert text.count("exit 0") == 1, "data-layout exit anchor moved"
    if marker not in text:
        script.write_text(text.replace("exit 0", migration + "\nexit 0", 1))
else:
    assert marker in text, "Firmware first-boot selection is absent"

# Distinguish the new experimental core in the actual compiled on-device
# Settings menu. Binary string length only decreases; bytes/offsets retained.
ui_candidates = [root/"usr/bin/banana-ui", root/"usr/libexec/banana/banana-ui"]
original = b"mGBA Expanded 320x204 (experimental)\x00"
updated = b"NEW - mGBA Expanded 320x204\x00"
found_ui = False
for path in ui_candidates:
    if not path.is_file():
        continue
    blob = path.read_bytes()
    assert len(updated) <= len(original)
    if original in blob and not verify:
        blob = blob.replace(original, updated + b"\x00" * (len(original)-len(updated)))
        path.write_bytes(blob)
        print("NEW emulator label installed into", path)
    if updated in blob:
        found_ui = True
assert found_ui, "Could not label expanded GB/GBC emulator NEW in banana-ui"

# Existing runtime launchers already use core.gb / core.gbc with priority to
# the native /usr/lib/libretro path. Check these explicit guarantees.
for name in ("run-retroarch", "run-bananafront"):
    launcher = (root/"usr/libexec/banana"/name).read_text()
    assert "core.$BANANA_SYSTEM" in launcher, name+" lacks per-system emulator choice"
    assert "/usr/lib/libretro" in launcher, name+" does not load OS-native libretro core"

print("Native RG DS firmware verified: GB and GBC will use the new expanded core after reboot.")
