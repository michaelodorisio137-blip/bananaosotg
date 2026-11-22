#!/usr/bin/env python3
"""Install an opt-in native Circle Pad patch mailbox for DraStic.

Works with separately game-patched NDS ROMs or emulator-ready ARM9 CPAD
Action Replay cheats. It supplies actual signed analog coordinates to guest
DS RAM 0x027FFDF0, using SuperDrastic's existing RAM discovery mechanism.
No writes occur with the mode set Off (default). Game-specific hooks are
NOT bundled, since their exact patches depend on the ROM revision.
"""
from pathlib import Path
import shutil, sys
if len(sys.argv)!=2: sys.exit("Usage: python3 rgds-cpad-patch.py /path/to/BananaLinux")
root=Path(sys.argv[1])
patch=Path(__file__).with_name("superdrastic-cpad.patch")
if not patch.is_file(): sys.exit("Missing superdrastic-cpad.patch")
dest=root/"buildroot/patches/superdrastic/0003-rgds-cpad-guest-ram.patch"
dest.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(patch,dest)
menu=root/"ui/src/settings.cpp"
source=menu.read_text()
anchor='''            add(SD, "nds", "Stick deadzone", "Right-stick synthetic touch deadzone.", sd,'''
new='''            add(SD, "nds", "Analog game patches",
                "Send real analog stick positions to a compatible, separately patched DS game over guest RAM.",
                sd, "DSFLIP_CPAD", { "Off", "Left stick", "Dual sticks" },
                { "off", "left", "dual" });
            items.back().def = "off";
            items.back().hints = {
                "Original DS behavior. No emulated RAM is changed.",
                "Use with a Circle Pad compatible ROM/cheat: left stick is a real analog axis.",
                "Left stick movement and right stick camera/aim for games with a dual-stick CPAD hook."
            };
            add(SD, "nds", "Analog patch layout",
                "The extended Circle Pad protocol is required by certain game-specific patches.",
                sd, "DSFLIP_CPAD_LAYOUT", { "Standard (packed)", "Extended" },
                { "packed", "extended" });
            items.back().def = "packed";
'''
if new.strip() not in source:
    if source.count(anchor)!=1: sys.exit("SuperDrastic analog menu mismatch")
    menu.write_text(source.replace(anchor,new+anchor,1))
print("Optional real Circle Pad patch guest-RAM bridge included (off unless selected).")
