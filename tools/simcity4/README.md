# SimCity 4 native RG DS bring-up

Pinned engine: codingncaffeine/Open-City-Builder at 6d46a1f76a57fbe0e1b9241f16fc4bea49b138c7 (GPL-3.0). No original game files or user backups enter the repository or CI.

First gate: compile the actual C++20 Linux engine on ARM64, using SDL3 touch-to-mouse, 640x480, scale 1. This is a single-panel bring-up, not a completed two-screen port. Ubuntu ARM64 is not the RG DS Buildroot ABI; no Ubuntu executable is published as installable firmware. Next gates: device ABI build, GPU context verification (OpenGL 3.3 or GLES adaptation), touch hardware calibration and second-panel native controls, simulation speed and save round-trip with copied real city data.

Use prepare-profile.py with the original installation and optional Documents/SimCity 4 directory. It makes an isolated copy with SHA256 inventory and DBPF index bounds. Do not run on the source installation. Separate user Documents are preserved under UserData pending engine-specific path wiring; do not claim those mods loaded. Existing custom models/lots/transport plugins need explicit engine tests; Windows DLLs cannot execute natively. Do not remove competing plugins or reorder them without a comparison against the original game.

No claim of full-speed or mod compatibility until real hardware and save comparison.
