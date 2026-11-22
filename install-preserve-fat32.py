#!/usr/bin/env python3
"""Install BananaOS on a FAT32 SD card without formatting its existing library.

Linux only. FIRST use GParted to move the FAT32 filesystem to start at >= 1 GiB;
leave that space unallocated (and at least 1 MiB free at the end). This script
does not resize/move the filesystem. It safely refuses unsuitable layouts.
Dry-run by default. Requires sfdisk, sgdisk, blkid, dd and root for --apply.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

SECTOR = 512
MIN_START = 1024 * 1024 * 1024 // SECTOR  # 1 GiB: leaves room for OS/bootloader
GPT_TAIL = 2048  # 1 MiB of free tail room
BOOTLOADER_START = 64  # RK3568 U-Boot raw image, sector 64 (32 KiB)
BOOTLOADER_END = 16 * 1024 * 1024 // SECTOR


def run(*args, capture=True):
    return subprocess.run(list(map(str, args)), check=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None,
                          text=True)


def layout(path):
    return json.loads(run("sfdisk", "--json", path).stdout)["partitiontable"]


def part_info(p):
    return int(p["start"]), int(p["size"])


def die(msg):
    raise SystemExit("REFUSED: " + msg)


def mounted(disk):
    lines = run("lsblk", "-nrpo", "MOUNTPOINTS", disk).stdout.splitlines()
    return any(line.strip() for line in lines)


def source_image(path, directory):
    if not path.is_file():
        die("Firmware image not found: " + str(path))
    if path.name.endswith(".img.gz"):
        out = directory / "firmware.img"
        print("Decompressing firmware image for inspection...")
        with gzip.open(path, "rb") as source, out.open("wb") as dest:
            shutil.copyfileobj(source, dest, length=4 * 1024 * 1024)
        return out
    if path.name.endswith(".img"):
        return path
    die("Supply the banana-rgds.img or banana-rgds.img.gz file, not the artifact ZIP.")


def backup_table(disk):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dest = Path.cwd() / ("sd-partition-table-" + stamp + ".txt")
    dest.write_text(run("sfdisk", "--dump", disk).stdout)
    print("Original partition table backed up to:", dest)
    return dest


def dd(source, disk, start, count):
    run("dd", "if=" + str(source), "of=" + disk, "bs=512",
        "skip=" + str(start), "seek=" + str(start), "count=" + str(count),
        "conv=notrunc,fsync", "status=progress", capture=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--disk", required=True, help="Whole SD device, e.g. /dev/sdb; NOT /dev/sdb1")
    ap.add_argument("--image", required=True, type=Path, help="Completed BananaOS RG DS .img.gz")
    ap.add_argument("--apply", action="store_true", help="Actually write partitions + firmware")
    a = ap.parse_args()
    for c in ("sfdisk", "sgdisk", "blkid", "lsblk", "dd", "blockdev"):
        if not shutil.which(c):
            die("Missing Linux tool: " + c)
    disk = os.path.realpath(a.disk)
    if not Path(disk).exists() or not Path(disk).is_block_device():
        die("Target must be a whole block device.")
    info = json.loads(run("lsblk", "-J", "-o", "NAME,TYPE,PATH", disk).stdout)["blockdevices"][0]
    if info["type"] != "disk" or info["path"] != disk:
        die("Target must be the full SD disk, not a partition.")
    if mounted(disk):
        die("Unmount every SD partition before running this installer.")
    logical = int(run("blockdev", "--getss", disk).stdout)
    total = int(run("blockdev", "--getsz", disk).stdout)
    if logical != SECTOR:
        die("Only 512-byte-sector SD cards are supported.")
    actual = layout(disk)
    parts = actual.get("partitions") or []
    if len(parts) != 1:
        die("Expected exactly ONE existing FAT32 partition. Multiple partitions need a separate migration.")
    part = parts[0]
    start, size = part_info(part)
    end = start + size - 1
    if start < MIN_START:
        die("First move the FAT32 filesystem right with GParted, leaving at least 1 GiB unallocated at the FRONT.")
    if total - 1 - end < GPT_TAIL:
        die("Leave at least 1 MiB unallocated at the END for the GPT backup header.")
    node = part.get("node")
    if not node:
        die("Couldn't identify existing FAT32 partition.")
    filesystem = run("blkid", "-o", "value", "-s", "TYPE", node).stdout.strip()
    if filesystem != "vfat":
        die("Existing data partition is not FAT32 (blkid says " + repr(filesystem) + ").")
    if total < 8 * 1024 * 1024 * 1024 // SECTOR:
        die("Unexpectedly small target disk.")
    with tempfile.TemporaryDirectory(prefix="rgds-install-") as temporary:
        image = source_image(a.image, Path(temporary))
        src = layout(str(image))
        if src.get("label", "").lower() != "gpt" or src.get("sectorsize", 512) != 512:
            die("Firmware image does not have the expected GPT/sector size.")
        systems = src.get("partitions", [])
        if len(systems) != 3:
            die("Firmware image should have exactly three partitions.")
        slices = [part_info(p) for p in systems]
        last_os = max(x + n - 1 for x, n in slices)
        if slices[0][0] != BOOTLOADER_END:
            die("Unexpected boot partition offset; refusing to flash bootloader.")
        if last_os + GPT_TAIL >= start:
            die("Existing FAT32 overlaps the firmware's boot/system area.")
        for i, (pos, count) in enumerate(slices):
            if pos < BOOTLOADER_END or count <= 0:
                die("Invalid system partition geometry at index " + str(i))
        print("\nRG DS preservation plan:")
        print("  TARGET:", disk, "|", round(total * SECTOR / 1e9, 2), "GB")
        print("  DATA: ", node, "| FAT32 | sectors", start, "through", end)
        print("  DATA FILESYSTEM: untouched; preserved at EXACT same start/end")
        for i, (pos, count) in enumerate(slices, 1):
            print("  OS partition", i, "| start", pos, "| length", count, "sectors")
        print("  U-Boot sectors", BOOTLOADER_START, "through", BOOTLOADER_END - 1)
        print("  PARTITION TABLE: reconstructed as GPT; data becomes partition 4")
        if not a.apply:
            print("\nDRY RUN COMPLETE. NO WRITES MADE. Re-run with --apply after backing up important data.")
            return

        if os.geteuid() != 0:
            die("Use sudo for --apply.")
        backup_table(disk)
        print("\nWARNING: wrong disk or power loss may permanently destroy data.")
        token = "INSTALL " + disk
        if input("Type " + repr(token) + " to authorize the write: ").strip() != token:
            die("Confirmation did not match; no changes made.")

        # Rebuild only metadata; FAT32 data sectors must never be reformatted/written.
        run("sgdisk", "--clear", disk)
        specs = [
            (1, slices[0][0], slices[0][0] + slices[0][1] - 1, "0700", "boot"),
            (2, slices[1][0], slices[1][0] + slices[1][1] - 1, "8300", "banana-root-a"),
            (3, slices[2][0], slices[2][0] + slices[2][1] - 1, "8300", "banana-root-b"),
            (4, start, end, "0700", "banana-data"),
        ]
        cmd = ["sgdisk"]
        for number, first, last, kind, name in specs:
            cmd += ["--new=%s:%s:%s" % (number, first, last),
                    "--typecode=%s:%s" % (number, kind),
                    "--change-name=%s:%s" % (number, name)]
        run(*cmd, disk)
        run("sgdisk", "--verify", disk)
        now = layout(disk)["partitions"]
        if len(now) != 4 or part_info(now[3]) != (start, size):
            die("GPT data bounds did not match original; STOP. Use the saved partition-table backup.")
        print("Writing U-Boot and the three OS partitions, leaving data sectors untouched...")
        dd(image, disk, BOOTLOADER_START, BOOTLOADER_END - BOOTLOADER_START)
        for pos, count in slices:
            dd(image, disk, pos, count)
        run("sync", capture=False)
        print("\nCOMPLETE. FAT32 data partition retained at its original physical location.")
        print("Power off, safely eject the card, insert it in RG DS and boot.")
        print("If boot fails, DO NOT FORMAT the card; retain your partition-table backup.")


if __name__ == "__main__":
    main()
