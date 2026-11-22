#!/usr/bin/env python3
"""RG DS original only: write a verified BananaOS SD-format image to internal eMMC.

Run from a TEMPORARY BananaOS SD boot. Default is non-destructive preflight.
Only --apply, on the original RG DS, from SD-booted BananaOS, and after
typing an exact confirmation, writes internal eMMC. Existing Android and
all internal files WILL BE ERASED. The removable microSD is never written.
"""
import argparse
import gzip
import hashlib
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile

MIB = 1024 * 1024


def refuse(message):
    raise SystemExit("REFUSED: " + message)


def block_info():
    candidates = []
    for node in Path("/sys/class/block").glob("mmcblk*"):
        if not re.fullmatch(r"mmcblk[0-9]+", node.name):
            continue
        try:
            media = (node / "device/type").read_text().strip()
            capacity = int((node / "size").read_text()) * 512
        except OSError:
            continue
        candidates.append((str(Path("/dev") / node.name), media, capacity))
    return candidates


def image_info(path):
    with path.open("rb") as f:
        f.seek(512)
        header = f.read(512)
        if header[:8] != b"EFI PART":
            refuse("Firmware is not a BananaOS GPT image")
        entries_lba = struct.unpack_from("<Q", header, 72)[0]
        entry_size = struct.unpack_from("<I", header, 84)[0]
        number = struct.unpack_from("<I", header, 80)[0]
        if not (2 <= entries_lba <= 64 and 128 <= entry_size <= 256 and 3 <= number <= 128):
            refuse("Unexpected firmware partition table")
        names = []
        for i in range(3):
            f.seek(entries_lba * 512 + entry_size * i)
            entry = f.read(entry_size)
            name = entry[56:128].decode("utf-16-le", errors="ignore").rstrip("\x00")
            names.append(name)
        if names != ["boot", "banana-root-a", "banana-root-b"]:
            refuse("Not an expected RG DS BananaOS image: " + str(names))
        f.seek(32768)
        if not any(f.read(4096)):
            refuse("No bootloader found at Rockchip's sector-64 boot offset")


def prepare(path, dest):
    h = hashlib.sha256()
    n = 0
    try:
        with gzip.open(path, "rb") as src, dest.open("wb") as out:
            while True:
                buf = src.read(4 * MIB)
                if not buf:
                    break
                h.update(buf)
                n += len(buf)
                out.write(buf)
            out.flush()
            os.fsync(out.fileno())
    except (OSError, EOFError) as e:
        refuse("Firmware gzip is damaged or cannot be decompressed: " + str(e))
    if n < 128 * MIB or n % 512:
        refuse("Unexpected firmware size or alignment")
    image_info(dest)
    return n, h.hexdigest()


def verify(target, n, expected):
    h = hashlib.sha256()
    with open(target, "rb", buffering=0) as src:
        while n:
            buf = src.read(min(4 * MIB, n))
            if not buf:
                refuse("Unexpected end of eMMC while verifying")
            h.update(buf)
            n -= len(buf)
    if h.hexdigest() != expected:
        refuse("eMMC read-back did not match. Do not boot or remove power until recovery is arranged.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", required=True, type=Path, help="banana-rgds.img.gz on temporary system's SD data partition")
    p.add_argument("--apply", action="store_true", help="Erase internal Android and write BananaOS")
    args = p.parse_args()
    if Path("/etc/banana/board").read_text().strip() != "rgds":
        refuse("Only original RG DS (not Plus) BananaOS builds are supported")
    model = Path("/proc/device-tree/model").read_bytes().rstrip(b"\x00")
    if model != b"Anbernic RG DS":
        refuse("Hardware model does not match original Anbernic RG DS")
    boot_disk = Path("/run/banana/disk").read_text().strip()
    devices = block_info()
    boot = [d for d in devices if d[0] == boot_disk and d[1] == "SD"]
    emmc = [d for d in devices if d[1] == "MMC" and 28e9 <= d[2] <= 40e9]
    if len(boot) != 1 or len(emmc) != 1:
        refuse("Must boot from removable SD with exactly one recognized 32GB internal eMMC")
    target, _, capacity = emmc[0]
    if boot_disk == target:
        refuse("Never flash the booted root device")
    if not args.image.is_file() or "rgds.img" not in args.image.name:
        refuse("Supply an RG DS firmware .img.gz, not a Plus image")
    if not str(args.image).endswith(".img.gz"):
        refuse("Only .img.gz firmware files are accepted")
    if os.path.realpath(args.image).startswith("/run/") or args.image.is_symlink():
        refuse("Put the firmware in the SD data partition before running the installer")
    print("BOARD: original RG DS")
    print("RUNNING FROM REMOVABLE SD:", boot_disk)
    print("INTERNAL ANDROID TARGET:", target, "(", round(capacity / 1e9, 2), "GB )")
    print("FIRMWARE:", args.image)
    print("REMOVABLE SD CONTENTS: no writes by this tool")
    print("ANDROID AND ALL FILES IN INTERNAL STORAGE: WILL BE ERASED IF APPLIED")

    # Decompress to the removable SD, checking gzip CRC/GPT/bootloader before
    # opening the eMMC for writing. Need temporary room for ~600MB uncompressed.
    scratch = Path("/data/banana/downloads")
    scratch.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(scratch).free < 1024 * MIB:
        refuse("Need at least 1 GiB free on temporary SD data partition for verified image")
    handle, tmpname = tempfile.mkstemp(prefix="rgds-emmc-checked-", suffix=".img", dir=scratch)
    os.close(handle)
    img = Path(tmpname)
    try:
        n, checksum = prepare(args.image, img)
        if n >= capacity:
            refuse("Firmware image is too large for detected eMMC")
        print("FIRMWARE VERIFIED:", n, "bytes / sha256", checksum)
        if not args.apply:
            print("DRY RUN PASSED. No internal storage was modified.")
            return
        if os.geteuid() != 0:
            refuse("Root permissions required for --apply")
        if not sys.stdin.isatty():
            refuse("Interactive terminal required; no automated destructive installation")
        confirm = "ERASE ANDROID INSTALL BANANAOS"
        print("\nThis replaces internal Android and its recovery/user data.")
        print("A partition-table backup does NOT restore Android. Have stock recovery firmware available.")
        if input("Type " + confirm + " to proceed: ").strip() != confirm:
            refuse("Confirmation declined; internal eMMC unchanged")

        # A small GPT layout backup is useful diagnostically but is not an Android backup.
        snapshot = scratch / "rgds-original-emmc-partitions.txt"
        if snapshot.exists():
            refuse("Previous eMMC partition snapshot already exists; move it to a safe backup first")
        table = subprocess.run(["sfdisk", "--dump", target], capture_output=True, text=True)
        if table.returncode != 0 or not table.stdout.strip():
            refuse("Could not back up eMMC partition table; no writes made")
        snapshot.write_text(table.stdout)
        with img.open("rb") as src, open(target, "r+b", buffering=0) as out:
            nleft = n
            while nleft:
                chunk = src.read(min(4 * MIB, nleft))
                if not chunk:
                    refuse("Image read failed during internal installation")
                out.write(chunk)
                nleft -= len(chunk)
            os.fsync(out.fileno())
        subprocess.run(["sync"], check=True)
        verify(target, n, checksum)
        print("\nVERIFIED: internal eMMC contains the BananaOS boot/system image.")
        print("Shut down the RG DS. REMOVE temporary boot SD.")
        print("Insert the untouched 1TB FAT32 card and boot. /data will mount from it.")
        print("The first internal boot will initialize an INTERNAL recovery data partition.")
    finally:
        img.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
