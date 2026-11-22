#!/usr/bin/env python3
"""Modify pinned BananaFront input.c to mirror the GBA shoulder pairs.

Runs as a Buildroot POST_EXTRACT hook (before its strict patch phase).
Changes only game_buttons[0], only when the GBA launcher sets the env flag.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    sys.exit("Usage: rgds-bananafront-shoulders.py /path/to/BananaFront/src/input.c")

source = Path(sys.argv[1])
if not source.is_file():
    sys.exit(f"Missing BananaFront input file: {source}")

original = source.read_text()
marker = "// RG DS: GBA only. Mirror either shoulder row onto GBA L/R."
if marker in original:
    print("BananaFront GBA shoulder mirror already applied.")
    sys.exit(0)

anchor = "    game_buttons[0] = hotkey_down ? 0 : b & ~job_mask;\n"
addition = """    // RG DS: GBA only. Mirror either shoulder row onto GBA L/R.
    if (getenv("BANANAFRONT_GBA_MIRROR")) {
        if (game_buttons[0] & (1u << RETRO_DEVICE_ID_JOYPAD_L2))
            game_buttons[0] |= 1u << RETRO_DEVICE_ID_JOYPAD_L;
        if (game_buttons[0] & (1u << RETRO_DEVICE_ID_JOYPAD_R2))
            game_buttons[0] |= 1u << RETRO_DEVICE_ID_JOYPAD_R;
    }
"""
if original.count(anchor) != 1:
    sys.exit("BananaFront input layout changed: expected one game_buttons[0] assignment.")
if "#include <stdlib.h>" not in original:
    sys.exit("BananaFront input layout changed: getenv needs <stdlib.h>.")
source.write_text(original.replace(anchor, anchor + addition, 1))
print("Applied RG DS GBA shoulder mapping to BananaFront.")
