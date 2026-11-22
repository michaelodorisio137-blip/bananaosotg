#!/usr/bin/env python3
"""Patch a BananaLinux source checkout for original RG DS USB mass storage.

Usage: python3 apply.py /path/to/BananaLinux
"""
from pathlib import Path
import sys
import shutil

if len(sys.argv) != 2:
    sys.exit('Usage: python3 apply.py /path/to/BananaLinux')
repo = Path(sys.argv[1]).expanduser().resolve()
sd2 = repo / 'system/rootfs/usr/libexec/banana/sd2'
rcs = repo / 'system/rootfs/etc/init.d/rcS'
usb = repo / 'system/rootfs/usr/libexec/banana/usb-sd2'
fileops = repo / 'ui/src/fileops.cpp'
if not (sd2.is_file() and rcs.is_file() and fileops.is_file() and (repo / 'Makefile').is_file()):
    sys.exit('Not a recognized BananaLinux source checkout (sd2, rcS or Makefile missing).')
source = Path(__file__).with_name('usb-sd2')
if not source.is_file():
    sys.exit('Missing the usb-sd2 script beside apply.py')

body = sd2.read_text()
marker = '# BananaOS original RG DS OTG adapter (experimental)'
insert = '''# BananaOS original RG DS OTG adapter (experimental)
# The Plus keeps its real second-SD support unchanged.
case "$(tr -d '\\000' </proc/device-tree/model 2>/dev/null)" in
    *"RG DS Plus"*) ;;
    *"RG DS"*) exec /usr/libexec/banana/usb-sd2 "${1:-scan}" ;;
esac
'''
if marker not in body:
    anchor = 'M=/run/sd2\n'
    if anchor not in body:
        sys.exit('sd2 has changed upstream; cannot safely locate the insertion point.')
    sd2.with_name('sd2.pre-usb-backup').write_text(body)
    sd2.write_text(body.replace(anchor, insert + anchor, 1))

body = rcs.read_text()
marker = '# BananaOS RG DS USB removable-storage watcher'
insert = '''# BananaOS RG DS USB removable-storage watcher
# Only the original single-slot RG DS uses the spare Files card mount.
case "$(tr -d '\\000' </proc/device-tree/model 2>/dev/null)" in
    *"RG DS Plus"*) ;;
    *"RG DS"*) /usr/libexec/banana/usb-sd2 watch >/dev/null 2>&1 & ;;
esac
'''
if marker not in body:
    anchor = 'bananad &\n'
    if anchor not in body:
        sys.exit('rcS has changed upstream; cannot safely locate the insertion point.')
    rcs.with_name('rcS.pre-usb-backup').write_text(body)
    rcs.write_text(body.replace(anchor, anchor + insert, 1))

shutil.copyfile(source, usb)
usb.chmod(0o755)
body = fileops.read_text()
marker = '/* BananaOS original RG DS USB drive label */'
if marker not in body:
    old = 'if ((t && *t) || mounted(sd2)) out.push_back({ "sd2", "Second SD card", sd2 });'
    new = '''/* BananaOS original RG DS USB drive label */
            std::string secondLabel = access("/run/banana/sd2/usb", F_OK) == 0 ? "USB drive" : "Second SD card";
            if ((t && *t) || mounted(sd2)) out.push_back({ "sd2", secondLabel, sd2 });'''
    if old not in body:
        sys.exit('fileops.cpp has changed upstream; cannot safely locate the second card label.')
    fileops.write_text(body.replace(old, new, 1))

# RG DS shoulder mirroring: L2 mirrors L, R2 mirrors R in both DS emulators.
cfg = repo / 'system/rootfs/etc/banana/settings.conf'
defs = repo / 'ui/src/settings_defaults.cpp'
buttons = repo / 'system/rootfs/usr/libexec/banana/nds-buttons'
for f in (cfg, defs, buttons):
    if not f.is_file():
        sys.exit(f'Missing BananaOS DS button source: {f}')
mirror_changes = [
    (cfg, 'nds_btn_l2 = swap', 'nds_btn_l2 = l'),
    (cfg, 'nds_btn_r2 = ff', 'nds_btn_r2 = r'),
    (defs, '{ "nds_btn_l2", "swap", ENUM, NDS_BTN, 0, 0, true },',
           '{ "nds_btn_l2", "l", ENUM, NDS_BTN, 0, 0, true },'),
    (defs, '{ "nds_btn_r2", "ff", ENUM, NDS_BTN, 0, 0, true },',
           '{ "nds_btn_r2", "r", ENUM, NDS_BTN, 0, 0, true },'),
    (buttons, 'case $1 in l2) echo swap ;; r2) echo ff ;; l3) echo blow ;; *) echo none ;; esac',
              'case $1 in l2) echo l ;; r2) echo r ;; l3) echo blow ;; *) echo none ;; esac'),
]
for f, before, after in mirror_changes:
    body = f.read_text()
    if after not in body:
        if before not in body:
            sys.exit(f'DS button mapping changed upstream: {f}')
        f.write_text(body.replace(before, after, 1))

# Saved SD-card settings survive upgrades. Migrate the *pair* of stock DS
# assignments only once, at the next DS game launch. Custom mappings stay.
body = buttons.read_text()
marker = '# RG DS shoulder mirror: migrate stock settings once'
if marker not in body:
    anchor = 'S=$' + '{NDS_BUTTONS_SETTINGS:-/data/banana/settings.conf}   # (the variable: tests)\n'
    migrate = r'''# RG DS shoulder mirror: migrate stock settings once
if [ "$S" = /data/banana/settings.conf ] && [ -f "$S" ] && [ ! -e /data/banana/.rgds-shoulder-v1 ]; then
    if grep -Eq '^ *nds_btn_l2 *= *swap *$' "$S" &&
       grep -Eq '^ *nds_btn_r2 *= *ff *$' "$S"; then
        sed -i -e 's/^ *nds_btn_l2 *= *swap *$/nds_btn_l2 = l/' \
               -e 's/^ *nds_btn_r2 *= *ff *$/nds_btn_r2 = r/' "$S"
    fi
    : > /data/banana/.rgds-shoulder-v1
fi
'''
    if anchor not in body:
        sys.exit('nds-buttons header changed upstream: cannot add shoulder migration')
    buttons.write_text(body.replace(anchor, anchor + migrate, 1))
print('DS shoulders: L2 -> L and R2 -> R (both emulators).')

# GBA: R2 must be a game button rather than BananaOS's usual fast-forward.
# L2 is already a game button by default; original GBA L1 and R1 stay mapped.
gba_default = 'ra_btn_r2.gba = ff'
gba_mirrored = 'ra_btn_r2.gba = game'
body = cfg.read_text()
if gba_mirrored not in body:
    if gba_default not in body:
        sys.exit('GBA R2 default changed upstream; inspect settings.conf.')
    cfg.write_text(body.replace(gba_default, gba_mirrored, 1))

# Existing users retain settings.conf in /data through firmware updates.
# Update only the stock GBA fast-forward assignment; keep custom choices.
runra = repo / 'system/rootfs/usr/libexec/banana/run-retroarch'
body = runra.read_text()
marker = '# RG DS GBA shoulder mirror: preserve L1/R1 and duplicate them on L2/R2'
if marker not in body:
    anchor = '# Settings > Other systems > Frontend (ra_frontend):'
    change = r'''# RG DS GBA shoulder mirror: preserve L1/R1 and duplicate them on L2/R2
if [ "$BANANA_SYSTEM" = gba ]; then
    S=/data/banana/settings.conf
    if [ -f "$S" ]; then
        sed -i 's/^ *ra_btn_r2\.gba *= *ff *$/ra_btn_r2.gba = game/' "$S"
    fi
fi
'''
    if anchor not in body:
        sys.exit('run-retroarch frontend selection moved upstream.')
    runra.write_text(body.replace(anchor, change + anchor, 1))

# For RetroArch's GBA cores, map RetroPad L2/R2 onto core L/R (10/11).
# RetroArch's core-remap system allows two buttons to trigger the same core
# action; preserve any user-created core or game remap. This only runs for GBA.
body = runra.read_text()
marker = '# RG DS GBA shoulder mirror: RetroArch core remap'
if marker not in body:
    anchor = 'CFG=/data/retroarch/retroarch.cfg\n'
    change = r'''# RG DS GBA shoulder mirror: RetroArch core remap
if [ "$BANANA_SYSTEM" = gba ]; then
    case $c in
        gpsp) core_name=gpSP ;;
        mgba) core_name=mGBA ;;
        vba_next) core_name="VBA Next" ;;
        vbam) core_name="VBA-M" ;;
        *) core_name= ;;
    esac
    if [ -n "$core_name" ]; then
        dir="/data/retroarch/remaps/$core_name"
        mkdir -p "$dir"
        remap="$dir/$core_name.rmp"
        if [ ! -e "$remap" ]; then
            printf 'input_player1_btn_l2 = "10"\ninput_player1_btn_r2 = "11"\n' > "$remap"
        fi
    fi
fi
'''
    if anchor not in body:
        sys.exit('run-retroarch config path moved upstream.')
    runra.write_text(body.replace(anchor, change + anchor, 1))

# BananaFront reads evdev directly, so mirror at the libretro input boundary.
# A narrowly scoped environment flag leaves GB/GBC and every other system alone.
runbf = repo / 'system/rootfs/usr/libexec/banana/run-bananafront'
body = runbf.read_text()
marker = '# RG DS GBA shoulder mirror: BananaFront'
if marker not in body:
    anchor = 'ROM=$2\n'
    change = '''# RG DS GBA shoulder mirror: BananaFront
[ "$BANANA_SYSTEM" = gba ] && export BANANAFRONT_GBA_MIRROR=1
'''
    if anchor not in body:
        sys.exit('run-bananafront ROM assignment changed upstream.')
    runbf.write_text(body.replace(anchor, anchor + change, 1))

# Buildroot's global package patch directory is set in banana_rgds_defconfig.
# Patch only the core input mapper, after hardware buttons and hotkeys have
# been handled, so the original physical button identity remains intact.
patch_dir = repo / 'buildroot/patches/bananafront'
patch_dir.mkdir(parents=True, exist_ok=True)
patch_file = patch_dir / '0001-rgds-gba-shoulder-mirrors.patch'
patch_text = '''--- a/src/input.c
+++ b/src/input.c
@@ -309,5 +309,12 @@ void bf_input_poll(void)
         b = s;
     }
     game_buttons[0] = hotkey_down ? 0 : b & ~job_mask;
+    // RG DS: GBA only. Either shoulder row may actuate GBA L/R.
+    if (getenv("BANANAFRONT_GBA_MIRROR")) {
+        if (game_buttons[0] & (1u << RETRO_DEVICE_ID_JOYPAD_L2))
+            game_buttons[0] |= 1u << RETRO_DEVICE_ID_JOYPAD_L;
+        if (game_buttons[0] & (1u << RETRO_DEVICE_ID_JOYPAD_R2))
+            game_buttons[0] |= 1u << RETRO_DEVICE_ID_JOYPAD_R;
+    }
     for (int p = 1; p < NPORT; p++) game_buttons[p] = pbuttons[p];
 }
'''
patch_file.write_text(patch_text)
print('GBA shoulders: L1/L2 -> L, R1/R2 -> R in BananaFront and RetroArch.')


# Add the original RG DS-only speaker EQ. Preserve upstream Plus tuning and
# every user setting; create a board-specific asset only when absent.
import subprocess
subprocess.run([sys.executable, str(Path(__file__).with_name('rgds-eq-patch.py')), str(repo)], check=True)

# Install the optional SD-card startup audio mixer and transition.
import subprocess
subprocess.run([sys.executable, str(Path(__file__).with_name('rgds-audio-patch.py')), str(repo)], check=True)
subprocess.run([sys.executable, str(Path(__file__).with_name('rgds-menu-patch.py')), str(repo)], check=True)
# New original-RG-DS-native startup, independent screen shaders, actual
# SuperDrastic/N64 texture sampling, and per-emulator screen toggles.
subprocess.run([sys.executable, str(Path(__file__).with_name('rgds-boot-patch.py')), str(repo)], check=True)
subprocess.run([sys.executable, str(Path(__file__).with_name('rgds-filter-patch.py')), str(repo)], check=True)
subprocess.run([sys.executable, str(Path(__file__).with_name('rgds-texture-patch.py')), str(repo)], check=True)
subprocess.run([sys.executable, str(Path(__file__).with_name('rgds-system-filter-patch.py')), str(repo)], check=True)

# Original RG DS native boot, independent screen filtering, and polygon texture filtering.
subprocess.run([sys.executable, str(Path(__file__).with_name('rgds-boot-patch.py')), str(repo)], check=True)
subprocess.run([sys.executable, str(Path(__file__).with_name('rgds-filter-patch.py')), str(repo)], check=True)
subprocess.run([sys.executable, str(Path(__file__).with_name('rgds-texfilter-patch.py')), str(repo)], check=True)

print('USB storage source changes installed for original RG DS.')
print('Build with: make rgds')
print('Generated image: output/rgds/images/banana-rgds.img.gz')
