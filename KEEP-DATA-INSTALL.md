# RG DS: install BananaOS on a 1 TB FAT32 card without formatting its games

Do NOT use Etcher or Rufus with the normal .img.gz: whole-disk flashing replaces the card partition table. This procedure instead preserves the physical sectors of the original FAT32 data partition. Back up irreplaceable saves; resizing and rewriting GPT is not risk-free.

## Prerequisites

- A Linux PC/GParted Live environment with GParted, sgdisk (gdisk), sfdisk, blkid, dd, Python 3.
- Exactly ONE existing FAT32 partition on the microSD (multiple partitions are refused).
- A completed RG DS image (banana-rgds.img.gz), extracted from its outer GitHub Actions artifact ZIP.
- A computer with space for roughly 600 MiB of decompressed firmware.

## 1: Make room with GParted

1. Plug in the card, identify it by size and model, and unmount its partition.
2. Use Resize/Move to leave 1 GiB free at the BEGINNING of the card and 1 MiB free at the END.
3. Apply the move, and check filesystem integrity before proceeding.
4. Confirm exactly one FAT32 partition remains, starting at or beyond 1 GiB.

Do NOT select Device > Create Partition Table in GParted. If 1 GiB cannot be freed, stop and back up/move some files externally first.

## 2: Dry-run (no writes)

Use lsblk -o NAME,SIZE,FSTYPE,MODEL,MOUNTPOINTS to find the correct whole-disk device. Substitute the actual disk path for /dev/sdX.

    python3 install-preserve-fat32.py --disk /dev/sdX --image banana-rgds.img.gz

The script refuses mounted volumes, wrong file systems, non-512-byte-sector devices, multiple partitions and overlaps. Review the listed start and end sectors.

## 3: Apply

    sudo python3 install-preserve-fat32.py --disk /dev/sdX --image banana-rgds.img.gz --apply

The script backs up the current partition table, asks for explicit typed authorization, reconstructs GPT metadata, keeps FAT32 at the identical physical start and end (as partition 4), and copies bootloader/OS from the image to partitions 1-3. It never invokes mkfs on the data partition. Its checks are not a guarantee against power failures or wrong-device selection.

Eject the card, install in the RG DS and boot. On boot, BananaOS sees partition 4, does not run its empty-card firstboot formatter, and mounts FAT32 through the fallback mount path. Existing files remain, but ROMs must be in the BananaOS folder layout to appear automatically.

## USB access

The custom firmware includes a USB storage watcher, FAT32/exFAT USB mounting, and a Files entry. Other USB accessory types will need individual kernel/driver/UI work. Use safe removal before unplugging drives.

## Our Apps storefront

Our Apps appears on its own menu tile and reuses BananaOS's native Store package manager, with a separate online catalog at our-apps/catalog.json. Native Linux aarch64 apps are downloaded and installed from published GitHub releases, then appear on the Apps shelf. Add catalog entries only when package releases are built and verified; the initial catalog is deliberately empty. The normal BananaOS Store remains available.
