#!/usr/bin/env python3
"""Add a conservative, user-adjustable RG DS-only Full & Warm speaker EQ.

The original RG DS uses AW87391 analog amps (unlike DS Plus AW88166).
No independently measured original RG DS frequency response was available
as of 2026-11-21. This is a provisional voicing, NOT calibration data.
It is packaged as the board-specific "tuned" profile; all settings and
other board profiles remain untouched.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    sys.exit("Usage: python3 rgds-eq-patch.py /path/to/BananaLinux")

root = Path(sys.argv[1])
eqdir = root / "ui/assets/speaker-eq"
if not eqdir.is_dir() or not (eqdir / "rgds-plus.txt").is_file():
    sys.exit("Upstream BananaOS speaker EQ assets not found; cannot add RG DS preset")

target = eqdir / "rgds.txt"
if target.exists():
    print("RG DS speaker preset already supplied upstream; preserving it.")
    sys.exit(0)

# Equalizer APO syntax accepted by BananaOS speaker_eq.cpp / eq.h.
# The existing 7-band EQ sliders remain independently adjustable.
# The high-pass removes inaudible deep-bass content that can strain
# very small drivers; the mid-bass/lower-mid boost adds perceived body.
# Negative preamp plus eq_design's automatic peak headroom avoids PCM clipping.
profile = """# Anbernic original RG DS — Full & Warm (provisional; not measured).
# Two front-facing speakers at sides of upper display, AW87391 analog amps.
# The RG DS Plus is a different acoustic and amplifier design: do not reuse
# this preset for it. Existing RG DS Plus measured EQ remains untouched.
# Voicing target: more audible low-mid weight, softened nasal upper mids and
# sharpness, preserving detail without boosting deep bass.
# Speaker output only. BananaOS leaves headphones / Bluetooth unchanged.
# All seven manual EQ sliders stay available and start at 0 dB offset.
# Refine against acoustic measurement when measurements become available.
Preamp: -4.0 dB
Filter 1: ON HPQ Fc 145 Hz Q 0.707
Filter 2: ON PK Fc 250 Hz Gain 2.0 dB Q 1.41
Filter 3: ON PK Fc 500 Hz Gain 3.0 dB Q 1.41
Filter 4: ON PK Fc 1000 Hz Gain -1.0 dB Q 1.41
Filter 5: ON PK Fc 2000 Hz Gain -2.0 dB Q 1.41
Filter 6: ON PK Fc 4000 Hz Gain -1.0 dB Q 1.41
Filter 7: ON PK Fc 8000 Hz Gain -2.0 dB Q 1.41
"""
target.write_text(profile)
print("Installed RG DS Full & Warm speaker preset: ui/assets/speaker-eq/rgds.txt")
