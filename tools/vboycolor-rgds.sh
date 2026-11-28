#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
src="$PWD/vboycolor-src"
test "$(git -C "$src" rev-parse HEAD)" = 9d1e5178a913d7244cd8d9ae0c3054f79915fc62
test "$(git -C "$src/third_party/beetle-vb-libretro" rev-parse HEAD)" = 38e7a0ec9ac7079ca1c1e3dd9aaf5b56f527efca
test "$(find "$src/colorpacks" -name '*.vbcp' | wc -l)" -eq 17
cmake -S "$src/platform/libretro" -B /tmp/vbc-host -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/vbc-host --parallel 4
python3 - <<'PY'
import ctypes
core=ctypes.CDLL('/tmp/vbc-host/vboycolor_libretro.so')
assert core.retro_api_version()==1
for name in ('retro_run','retro_load_game','retro_set_environment','retro_serialize','retro_unserialize'):
    assert getattr(core,name)
print('PASS: host shared core load and libretro API exports')
PY
# Exact BananaLinux Buildroot toolchain, rather than a foreign Linux sysroot.
make -C BananaLinux host-cmake-rgds toolchain-rgds
host="$PWD/BananaLinux/output/rgds/host"
test -s "$host/share/buildroot/toolchainfile.cmake"
cmake -S "$src/platform/libretro" -B /tmp/vbc-arm64 \
    -DCMAKE_TOOLCHAIN_FILE="$host/share/buildroot/toolchainfile.cmake" \
    -DCMAKE_BUILD_TYPE=Release -DVBC_STATIC_RUNTIME=ON
cmake --build /tmp/vbc-arm64 --parallel 4
mkdir -p vboycolor-out
install -m 0644 /tmp/vbc-arm64/vboycolor_libretro.so vboycolor-out/vboycolor_libretro.so
install -m 0644 "$src/platform/libretro/vboycolor_libretro.info" vboycolor-out/vboycolor_libretro.info
install -m 0644 "$src/LICENSE" vboycolor-out/LICENSE
install -m 0644 "$src/THIRD-PARTY-NOTICES.md" vboycolor-out/THIRD-PARTY-NOTICES.md
readelf -h vboycolor-out/vboycolor_libretro.so | grep -q AArch64
readelf -Ws vboycolor-out/vboycolor_libretro.so > /tmp/vbc-symbols
grep -q 'retro_load_game' /tmp/vbc-symbols
grep -q 'retro_run' /tmp/vbc-symbols
git rev-parse HEAD > vboycolor-out/SOURCE-COMMIT
git -C "$src" rev-parse HEAD > vboycolor-out/VBOYCOLOR-COMMIT
git -C "$src/third_party/beetle-vb-libretro" rev-parse HEAD > vboycolor-out/BEETLE-COMMIT
# Corresponding exact source, including embedded pack data and Beetle source.
tar -czf vboycolor-out/vboycolor-corresponding-source.tar.gz --exclude=.git -C "$src" .
(cd vboycolor-out; sha256sum vboycolor_libretro.so vboycolor_libretro.info LICENSE THIRD-PARTY-NOTICES.md vboycolor-corresponding-source.tar.gz > SHA256SUMS; sha256sum -c SHA256SUMS)
