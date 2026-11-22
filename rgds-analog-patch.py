#!/usr/bin/env python3
"""Integrate analog right-stick touchscreen modes into SuperDrastic.

The untouched left stick continues using DraStic's existing joystick-to-D-pad
path. The right stick is fed into SuperDrastic's SDL mouse/stylus path via
superdrastic-analog.patch, at the actual input level (not a screen shader).
No claim is made to implementing RTCom/CPAD guest-RAM analog cheat hooks.
"""
from pathlib import Path
import shutil, sys
if len(sys.argv) != 2: sys.exit("Usage: python3 rgds-analog-patch.py /path/to/BananaLinux")
root=Path(sys.argv[1])
s=root/"ui/src/settings.cpp"
patch=Path(__file__).with_name("superdrastic-analog.patch")
if not patch.is_file(): sys.exit("Missing superdrastic-analog.patch")
dest=root/"buildroot/patches/superdrastic/0002-rgds-right-analog-stylus.patch"
dest.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(patch,dest)
body=s.read_text()
anchor='''add(SD, "nds", "3D resolution", "How sharp DS games' 3D is drawn.", dcfg, "hires_3d", { "1x", "2x" }, { "0", "1" });'''
addition='''            add(SD, "nds", "Right-stick touch",
                "Use the RG DS's analog right stick as the DS stylus. Real touchscreen always takes priority.",
                sd, "DSFLIP_ANALOG_TOUCH", { "Off", "Virtual touch stick", "FPS touch aim" },
                { "off", "touch", "fps" });
            items.back().def = "off";
            items.back().hints = {
                "No synthetic touch. All original controls are preserved.",
                "Holding the right stick away from centre produces touch-drag at its analog position.",
                "Right stick steers an emulated touch pen continuously. Useful for touch-aim games."
            };
            add(SD, "nds", "Stick deadzone", "Right-stick synthetic touch deadzone.", sd,
                "DSFLIP_ANALOG_DEADZONE", { "10%", "20%", "30%" }, { "10", "20", "30" });
            items.back().def = "20";
            add(SD, "nds", "Stick sensitivity", "Adjust the movement speed of the right stick.", sd,
                "DSFLIP_ANALOG_SENSITIVITY", { "50%", "100%", "150%", "200%" }, { "50", "100", "150", "200" });
            items.back().def = "100";
'''
if addition.strip() not in body:
    if body.count(anchor)!=1: sys.exit("SuperDrastic settings changed upstream; cannot add analog menu")
    s.write_text(body.replace(anchor,addition+anchor,1))
print("Analog right-stick stylus installed in SuperDrastic with on-device controls.")
