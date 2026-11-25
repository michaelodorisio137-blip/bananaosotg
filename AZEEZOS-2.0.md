# AzeezOS 2.0 development preview

Based on the 0.5.3.9 GBA bitmap fix OTA. Only the new UI binary and its sort default/version are overlaid onto that root filesystem; existing cores are preserved. Do not publish this to the production OTA feed.

Implemented in dev.1: region sort, touch-accessible AI Cheats research panel for the existing single-screen RetroArch/BananaFront game panel, separate prompt keyboard, source-backed online lookup through OpenAI Responses API, save unverified research drafts, and confirmed game reset via RESET. The API key must be provided in the banana-ui service environment (AZEEZOS_OPENAI_API_KEY or OPENAI_API_KEY); no credentials are included or stored by this module. The model defaults to gpt-5-mini and is configurable with AZEEZOS_AI_MODEL. Only game metadata, file CRC32/size and prompt are sent. No ROM upload. API billing is separate.

Not implemented in dev.1: AI memory search, candidate application, user-confirmed working cheat catalog, cheat toggles, dual-screen DS overlay, Mods browser, AI self-upgrading agent, permanent six-tab dashboard. Do not describe this preview as a complete 2.0. No AI output is executed. The source-backed draft is not a verified cheat. Reset resets the current core and does not replace the ROM. Requires hardware validation.

Next: authenticated build service, per-emulator cheat adapters, exact ROM SHA-256 identity, temporary test and restore, live memory differential search, confirmation, persistent enabled cheats, DS overlay, mod downloads/patch verification, signed build manifests and recovery.

## Development preview 2
- Adds a read-only differential RAM search page for the existing single-screen game panel. Initial supported ranges: GBA IWRAM (32 KiB) and GB/GBC WRAM (8 KiB). Uses the existing RetroArch command pipe or BananaFront shared-memory transport, with bounded reads, explicit failures and no incomplete snapshot committed. Scans are non-atomic while gameplay runs. Companion-active games are excluded until the reply arbitration is validated.
- The 8/16/32-bit search algorithm and transport tests pass locally (source blob hashes verified). The exposed live page currently searches 8-bit values only. Do not claim on-device verification.
- A separate one-shot write/readback/undo state machine and tests exist. It is not wired to the device UI, does not freeze values and cannot yet persist a cheat. Do not execute model-generated code.
- Preview builds remain separate from production OTA. Main branch and existing stable root filesystem are not modified by this work.

## Release acceptance gates (all required before final 2.0)
1. Pinned upstream integration and clean ARM64 compile; checksum-verified update artifact and tested rollback.
2. Physical RG DS tests: boot, controls, Wi-Fi, OTG, SD preservation, dual displays, audio, save states, all existing viewport and texture filtering options, and region sort.
3. AI cheats: exact ROM/core identification; offline-only test, readback, explicit confirmation, restore/recovery, persistent list and enable/disable, both one-screen and DS game integrations.
4. Mod browser: actual source-backed search, matching ROM revision, download integrity, non-destructive patch installation, restart and revert; do not overwrite original ROMs.
5. AI development: authenticated build requests, isolated code changes, test logs, signed/verified updates, explicit installation and recovery.
6. No placeholder tabs or simulated success. A preview artifact is not the finished release; unsupported modes must be clearly identified. 

## Development preview 3
- Native live-scan page now includes explicit one-shot byte trial, readback, user confirmation, conditional undo, a paged persistent catalog, manual reapply and deletion. Catalog identity is SHA-256 of the exact content file and actual RetroArch core. ZIP container identity is not the decompressed ROM identity.
- Writes are limited to the same bounded RAM ranges as live scan, RetroArch sessions with an actual session identity, no active network interface and Hardcore off. BananaFront shared memory is read-only, and companion-active games remain excluded. No periodic freeze, DS adapter or automatic AI code execution. Hardware validation remains mandatory.
- The original production firmware is preserved. Preview 3 patches the existing baseline launcher in place only to add the session identity, and overlays the new UI binary.
- Native IPS/BPS patch decoding and tests are added separately as the mod installer foundation. No browser, download or game-restart integration yet.
