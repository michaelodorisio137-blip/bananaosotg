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

print('USB storage source changes installed for original RG DS.')
print('Build with: make rgds')
print('Generated image: output/rgds/images/banana-rgds.img.gz')
