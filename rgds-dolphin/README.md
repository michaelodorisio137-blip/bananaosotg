# RG DS Dolphin Speed (experimental Android APK)

An ARM64 Android 14 Dolphin variant tuned for Anbernic RG DS (RK3568 / Mali-G52 2EE / 640x480). This is **not** a claim of full-speed GameCube emulation. It uses Dolphin's existing JIT and renderer, applying speed-biased defaults while keeping a recognizable image.

## What the patched APK changes

- Separate Android application ID `org.rgds.dolphinspeed.debug`: can be installed alongside regular Dolphin.
- Targets ARM64 only; release-optimized C++ in a debug-signed sideloadable APK.
- Emulated GameCube CPU clock defaults to **75%**, with the clock override enabled.
- Native **1x internal resolution**, suitable for the 640x480 RG DS screen.
- Asynchronous "skip drawing" shader compilation: brief missing objects are possible rather than shader stalls.
- "Fast" texture cache (0 samples), optional GPU texture decoding, and VI skip enabled.
- 2x anisotropic filtering helps texture clarity without 2x internal rendering cost.
- Defaults already supplied by upstream Dolphin remain in effect: ARM64 JIT, dual-core CPU/GPU threading on Android, DSP-HLE, EFB/XFB texture copies, and EFB CPU-access skipping.

**Existing per-game Dolphin overrides can supersede these defaults.** User settings are stored separately due to the distinct application ID. If a game malfunctions, disable VI Skip, restore 100% CPU clock, select a stricter texture cache, or turn off GPU texture decoding in Settings. If objects vanish while entering a new area, switch shader compilation to Specialized/Synchronous.

## Build

The workflow at `.github/workflows/build-rgds-dolphin.yml` checks out a pinned Dolphin source revision, applies `rgds-dolphin/patch_rgds_dolphin.py`, builds the Android debug APK, and uploads the resulting artifact.

Open **Actions > RG DS Dolphin Speed APK > latest successful run > Artifacts** and extract the `rgds-dolphin-speed-apk` artifact. Install the APK using Android 14 on the RG DS; this APK does **not** run under BananaOS Linux. No copyrighted games or BIOS images are included.

The branch contains a *build recipe and source-level patch*, not a precompiled APK. Device performance, Vulkan/OpenGL ES driver behavior, and control mappings have **not yet been benchmarked**.

## Limitations

Accuracy hacks may break individual titles, game logic, texture updates, or audio timing. The RK3568's four Cortex-A55 cores may remain CPU-limited despite these settings. The current patch does not create a dedicated dual-screen gameplay UI or an independent rewritten GameCube emulator. Its purpose is to establish a repeatable, measurable baseline for more intensive RG DS-specific work.

Upstream: https://github.com/dolphin-emu/dolphin
License: Dolphin's GPL-2.0-or-later source code remains under its existing license.
