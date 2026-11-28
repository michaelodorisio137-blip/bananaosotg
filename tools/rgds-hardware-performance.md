# RG DS hardware-specific performance rules

Original RG DS (not Plus): RK3568, four Cortex-A55 cores, Mali-G52 2EE, 3 GB RAM, two 640x480 panels. Pinned BananaLinux already configures Cortex-A55 and Mesa Panfrost 25.0.7. Its board patch specifies 60.0013 Hz. Preserve device timing, thermal protections and supported OPPs; no overvolting or thermal bypass.

## Performance decisions
- Fixed 320x240 logical canvas / 640x480 native output. Keep original guest clocks, native 2D pixel alignment, touch transforms, save formats. Do not confuse output resolution with guest rendering cost.
- CPU-heavy paths: ARM64 dynarecs, NEON row/palette operations, preserve upstream Gengis dirty-bin reuse; no blind global fast-math, unsafe timing changes, or arbitrary CPU pinning. Benchmark thread allocation instead of assuming four workers are optimal.
- GPU-heavy paths: GLES3 and Panfrost, direct KMS/DRM presentation, no CPU readback on normal frames, fewer FBO transitions, use hardware filtering only where semantically correct. Benchmark N64 triple buffers vs baseline; preserve framebuffer effects. Use GPU producer reflection only.
- PS1: prefer NEON GPU and dynamic recompiler, maintain interlace/24-bit handling; use native framebuffer by default. GBA: preserve software fallback, optimize exterior-only GPU pass, distinguish actual polygons from affine backgrounds.
- Use sustained clocks rather than unsafe thermal changes; compare maximum profile against existing governor using measurements. Keep device cooling controls. Avoid per-frame logging or polling, do not run collectors during normal play unless requested.
- Cache game list metadata/cover thumbnails on verified internal storage, keep ROMs on removable media; cache invalidation and limits required before activation.
- For each test core, compare the same game, scene, save state and settings with the previous version. Collect emulated speed, frame-time p95/p99, audio underruns, CPU/GPU clocks, CPU threads, temperatures, output pixel alignment and touch. Test sustained runs. A passed compiler is not a performance result.
- Use native engine frame metrics for FPS/audio; the read-only capture script records OS counters only (not FPS or GPU busy). Delta cumulative ticks between samples, convert with device CLK_TCK. If fields are NA, the kernel does not expose them. CPU processor number is the last scheduled CPU, not affinity. Only opt-in diagnostic capture over SSH; no automatic background process.

Sources: https://anbernic.com/products/rgds ; https://www.rock-chips.com/a/en/products/RK35_Series/2021/0113/1276.html ; https://arm-software.github.io/libGPUCounters/mali-g52_counter_reference.html ; https://github.com/JorreFog/BananaLinux/blob/main/docs/PERFORMANCE-0.5.0.md (Plus measurements, not directly transferable).
