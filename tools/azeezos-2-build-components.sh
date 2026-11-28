#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export BR2_DL_DIR="${BR2_DL_DIR:-$PWD/dl}"
mkdir -p "$BR2_DL_DIR"
target=BananaLinux/output/rgds/target
packages=(); files=()
add() { packages+=("$1"); shift; files+=("$@"); }
for component in "$@"; do
  case "$component" in
    ui) add banana-ui usr/bin/banana-ui ;;
    ui-reflection) add banana-ui usr/bin/banana-ui; add bananafront usr/bin/bananafront; add libretro-ppsspp-azeez usr/lib/libretro/ppsspp_azeez_libretro.so usr/share/banana/PPSSPP; add bananads usr/bin/bananads ;;
    gba) add libretro-mgba usr/lib/libretro/mgba_integer_libretro.so usr/lib/libretro/mgba_expanded_libretro.so ;;
    snes) add libretro-bananasnes usr/lib/libretro/bananasnes_libretro.so ;;
    n64) add libretro-mupen64plus-next usr/lib/libretro/mupen64plus_next_libretro.so ;;
    nes) add libretro-fceumm usr/lib/libretro/fceumm_libretro.so ;;
    ps1) add libretro-pcsx-rearmed usr/lib/libretro/pcsx_rearmed_libretro.so ;;
    genesis) add libretro-genesis-plus-gx-wide usr/lib/libretro/genesis_plus_gx_wide_libretro.so ;;
    snes-hd) add libretro-bsnes-hd usr/lib/libretro/bsnes_hd_beta_libretro.so ;;
    ds) add bananads usr/bin/bananads ;;
    front) add bananafront usr/bin/bananafront ;;
    retroarch) add retroarch usr/bin/retroarch ;;
    virtualboy) add libretro-mednafen-vb usr/lib/libretro/mednafen_vb_libretro.so ;;
    pce) add libretro-mednafen-pce-fast usr/lib/libretro/mednafen_pce_fast_libretro.so ;;
    ngp) add libretro-mednafen-ngp usr/lib/libretro/mednafen_ngp_libretro.so ;;
    saturn) add libretro-yabasanshiro usr/lib/libretro/yabasanshiro_libretro.so ;;
    psp) add libretro-ppsspp-azeez usr/lib/libretro/ppsspp_azeez_libretro.so usr/share/banana/PPSSPP ;;
    all) bash "$0" ui gba snes n64 nes ps1 genesis snes-hd ds front retroarch virtualboy pce ngp saturn psp; make -C BananaLinux openssl-rgds; exit ;;
    *) echo "Unknown component: $component" >&2; exit 2 ;;
  esac
done
((${#packages[@]})) || exit 2
for pkg in "${packages[@]}"; do make -C BananaLinux "$pkg-rgds"; done
mkdir -p component-output
for f in "${files[@]}"; do
  test -e "$target/$f"
  if [[ "$f" == *.so || "$f" == usr/bin/* ]]; then
    test -s "$target/$f"
    readelf -h "$target/$f" | grep -q AArch64
  fi
  mkdir -p "component-output/$(dirname "$f")"
  cp -a "$target/$f" "component-output/$f"
done
# Strip only non-runtime PPSSPP debugger metadata excluded by artifact upload.
rm -f component-output/usr/share/banana/PPSSPP/debugger/.git component-output/usr/share/banana/PPSSPP/debugger/.nojekyll
git rev-parse HEAD > component-output/SOURCE-COMMIT
(cd component-output; find usr -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS; sha256sum -c SHA256SUMS)
echo "Development binaries only: not a firmware update. Hardware validation required." > component-output/README.txt
