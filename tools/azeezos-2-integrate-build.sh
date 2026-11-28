#!/bin/bash
set -euo pipefail
set -eu
python3 -m py_compile apply.py tools/next-n64-integration.py tools/next-n64-source.py
python3 apply.py BananaLinux
python3 verify-preservation.py BananaLinux
python3 tools/next-n64-integration.py BananaLinux
python3 tools/next-integer-viewport-integration.py BananaLinux
python3 tools/azeezos-2-expanded-integration.py BananaLinux
python3 -m py_compile tools/next-integer-viewport-source.py tools/next-integer-rootfs.py
python3 tools/azeezos-2-region.py BananaLinux
python3 -m py_compile tools/azeezos-2-native-integer.py
python3 tools/azeezos-2-native-integer.py --ui BananaLinux
python3 -m py_compile tools/azeezos-2-bananads-filter.py
python3 tools/azeezos-2-bananads-filter.py --integrate BananaLinux
python3 tools/azeezos-2-panel.py BananaLinux
python3 tools/ai-cheats/integrate.py BananaLinux
python3 tools/ai-cheats/integrate_trial.py BananaLinux
python3 tools/mods/integrate.py BananaLinux
python3 tools/ai-dev/integrate.py BananaLinux
python3 -m py_compile tools/ai-dev/{generate,sign,stage}.py
python3 tools/ai-cheats/integrate_nds.py BananaLinux
python3 tools/ai-cheats/integrate_maps.py BananaLinux
python3 tools/cheat-database/integrate.py BananaLinux
g++ -std=c++17 -Wall -Wextra -Werror tools/mods/patch_test.cpp -lz -o /tmp/mod-patch-test
/tmp/mod-patch-test
g++ -std=c++17 -Wall -Wextra -Werror tools/mods/install_test.cpp -lz -o /tmp/mod-install-test
/tmp/mod-install-test
python3 tools/ai-cheats/launcher_identity.py BananaLinux/system/rootfs
python3 tools/azeezos-2-idle-reflection.py BananaLinux
python3 tools/azeezos-2-magazines.py BananaLinux
g++ -std=c++17 -Wall -Wextra -Werror tools/ai-cheats/catalog_test.cpp -o /tmp/catalog-test
/tmp/catalog-test
g++ -std=c++17 -Wall -Wextra -Werror tools/ai-cheats/live_scan_test.cpp -o /tmp/live-scan-test
/tmp/live-scan-test
g++ -std=c++17 -Wall -Wextra -Werror tools/ai-cheats/trial_test.cpp -o /tmp/cheat-trial-test
/tmp/cheat-trial-test
for f in kms.cpp settings_gamepanel.cpp main.cpp library.cpp settings.cpp settings_defaults.cpp settings_files.cpp settings_servers.cpp nds/overlay.cpp complink.cpp; do
  g++ -std=c++17 -fsyntax-only -IBananaLinux/ui/src -IBananaLinux/ui -IBananaLinux/ui/rnds $(pkg-config --cflags freetype2 libdrm zlib) BananaLinux/ui/src/$f
done
grep -q 'Nearest neighbor (NEW)' BananaLinux/ui/src/settings.cpp
grep -q '"nearest"' BananaLinux/ui/src/settings_defaults.cpp
grep -q 'nearest) t=nearest' BananaLinux/system/rootfs/usr/libexec/banana/run-retroarch
grep -q 'next-n64-source.py' BananaLinux/buildroot/package/libretro-mupen64plus-next/libretro-mupen64plus-next.mk
sh -n BananaLinux/system/rootfs/usr/libexec/banana/run-retroarch
git -C BananaLinux diff --check
