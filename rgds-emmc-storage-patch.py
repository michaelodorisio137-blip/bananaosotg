#!/usr/bin/env python3
"""Enable optional internal eMMC boot with a FAT32 SD card as /data.

On a standard microSD-booted BananaOS card this patch changes no behaviour:
only the original RG DS when its root filesystem is on MMC-type eMMC
will attempt to mount the single removable SD partition as /data.
"""
from pathlib import Path
import shutil
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: rgds-emmc-storage-patch.py /path/to/BananaLinux")
repo = Path(sys.argv[1]).resolve()
rcs = repo / "system/rootfs/etc/init.d/rcS"
if not rcs.is_file():
    raise SystemExit("BananaLinux rcS missing")
body = rcs.read_text()
marker = "# RG DS internal eMMC boot: use external FAT32 card for all user data"
if marker not in body:
    anchor = "# exFAT, so the card can be read and filled on any computer\n"
    if anchor not in body:
        raise SystemExit("BananaLinux rcS data-mount anchor changed")
    change = r'''# RG DS internal eMMC boot: use external FAT32 card for all user data
# /run/banana/disk continues naming INTERNAL eMMC for kernel updates.
# If this is a normal SD boot, or a RG DS Plus, nothing is different.
# External card is never partitioned/formatted by this code.
if [ "$(cat /etc/banana/board 2>/dev/null)" = rgds ] &&
   [ "$(cat /sys/class/block/"$(basename "$DISK")"/device/type 2>/dev/null)" = MMC ]; then
    for sys in /sys/class/block/mmcblk[0-9]*; do
        [ -f "$sys/device/type" ] || continue
        [ "$(cat "$sys/device/type" 2>/dev/null)" = SD ] || continue
        part="/dev/$(basename "$sys")p1"
        [ -b "$part" ] || continue
        if mount -t vfat -o rw,noatime,utf8 "$part" /data 2>/dev/null ||
           mount -t exfat -o rw,noatime,fmask=0000,dmask=0000 "$part" /data 2>/dev/null; then
            echo "$part" > /run/banana/data-partition
            logger -t banana "RG DS internal OS: /data mounted from $part"
            break
        fi
    done
fi
'''
    body = body.replace(anchor, change + anchor, 1)
    before = "data || {\n"
    if body.count(before) != 1:
        raise SystemExit("BananaLinux rcS default data mount changed")
    body = body.replace(before, "if ! grep -q ' /data ' /proc/mounts; then\n" + before, 1)
    tail = "/usr/libexec/banana/data-layout\n"
    if body.count(tail) != 1:
        raise SystemExit("BananaLinux rcS data-layout anchor changed")
    body = body.replace(tail, "fi\n" + tail, 1)
    rcs.write_text(body)
# Keep the eMMC installer available on the temporary SD system over SSH.
installer_source = Path(__file__).with_name("install-rgds-emmc.py")
installer_target = repo / "system/rootfs/usr/libexec/banana/install-rgds-emmc.py"
if not installer_source.is_file():
    raise SystemExit("Internal installation tool not found beside source patch")
shutil.copyfile(installer_source, installer_target)
installer_target.chmod(0o755)
print("Internal RG DS boot option: external SD FAT32 at /data, fallback eMMC data; no SD boot changes.")
