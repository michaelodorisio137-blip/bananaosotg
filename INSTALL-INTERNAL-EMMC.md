# Original RG DS: BananaOS on internal 32 GB eMMC

**Status: experimental. Source-level validation passed; an actual internal boot has NOT been verified on hardware.**

Goal: use internal eMMC for the BananaOS bootloader and OS, the existing **1 TB FAT32 microSD** for /data (games, saves, app installs and settings), and USB OTG for additional storage/accessories.

## Important

**The internal installation REPLACES Android and all its eMMC data.** Back up any Android data you want to keep, and obtain the manufacturer's stock recovery resources. This is an intentional OS replacement, not Android dual boot. Do not use the image on an RG DS Plus or any other device.

**Never flash the 1 TB card.** It can remain exactly as it is, with a single FAT32 partition. BananaOS will create its expected folders on it if needed.

## Phase A: temporary SD boot

1. Download the **BananaOS-RGDS-eMMC-OurApps-USB-OTG** artifact from the successful build on the `rgds-emmc-boot` branch. Extract the GitHub artifact ZIP.
2. Use a **separate, temporary microSD** (4 GB or larger) and flash `banana-rgds.img.gz` to that card using an ordinary image-flashing tool. This temporary card will be erased.
3. Boot the original RG DS from the temporary card. Test input, Wi-Fi and basic functions first. The eMMC has not been touched.
4. Copy `banana-rgds-emmc.img.gz` (from the same artifact) onto the temporary card, e.g. into `banana/downloads/`. Keep at least 1 GiB free for temporary decompression.
5. Enable BananaOS's built-in **SSH** in Settings > Network. SSH requires a user-supplied public key in `banana/ssh/authorized_keys` on the temporary card (it does not accept passwords). The user can copy that file over the existing SMB file-sharing feature or an SD reader.
6. From a trusted computer on the same LAN, SSH into the RG DS as root using your matching private key. The default firmware includes the installer at `/usr/libexec/banana/install-rgds-emmc.py`.

## Phase B: dry-run then deliberate internal install

On the temporary BananaOS installation, run:

```sh
python3 /usr/libexec/banana/install-rgds-emmc.py \
  --image /data/banana/downloads/banana-rgds-emmc.img.gz
```

This dry-run verifies the hardware, SD boot status, the 32 GB eMMC target, firmware GPT names, gzip integrity and image size, without writing eMMC.

Only if all checks pass and **you explicitly want to erase internal Android**, run:

```sh
python3 /usr/libexec/banana/install-rgds-emmc.py \
  --image /data/banana/downloads/banana-rgds-emmc.img.gz --apply
```

The installer requires the exact typed phrase `ERASE ANDROID INSTALL BANANAOS`, makes a GPT layout snapshot on the temporary card, writes the image to internal eMMC and checks its read-back. Do not interrupt power during the write.

## Phase C: final 1 TB card

Shut down, remove the temporary boot microSD, insert your existing **1 TB FAT32 card**, then power up. The eMMC system looks for the SD's first FAT32 partition and mounts it at `/data` before initializing library folders. No SD formatting or partitioning is intended.

If it fails to boot, do **not** format your 1 TB card. Reinsert the temporary BananaOS card and use recovery diagnostics. If the U-Boot ROM selection or eMMC recovery flow fails, a hardware-specific recovery procedure may be necessary; this workflow cannot guarantee a working eMMC boot without testing on the console.

## USB and Our Apps

- FAT32/exFAT USB mass storage is provided by the experimental USB OTG watcher in this build.
- Other USB hardware types still need specific drivers and app support.
- Our Apps has a separate Store tile and a [catalog](./our-apps/catalog.json) that currently contains no released packages. Once an app has a verified Linux aarch64 GitHub release and an entry in the catalog, it can be downloaded and updated on the RG DS via Wi-Fi.
