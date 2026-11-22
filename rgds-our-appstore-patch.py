#!/usr/bin/env python3
"""Integrate Our Apps into BananaLinux without replacing the stock Store."""
from pathlib import Path
import shutil
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: rgds-our-appstore-patch.py /path/to/BananaLinux")
repo = Path(sys.argv[1]).resolve()
source = Path(__file__).resolve().parent / "our-apps/catalog.json"
if not source.is_file():
    raise SystemExit("Missing our-apps/catalog.json")

system = repo / "system/rootfs/etc/banana/systems.conf"
src = system.read_text()
section = """# Our Apps: separate catalog for RG DS custom apps and accessories.
[ourappstore]
name = Our Apps
maker = RG DS custom
folder = /usr/share/banana/apps/ourstore
ext = app
run = /usr/libexec/banana/run-our-appstore %ROM%
perf = balanced

"""
if "[ourappstore]" not in src:
    anchor = "# the apps installed from the Store (shown once one is)"
    if anchor not in src:
        raise SystemExit("BananaOS systems.conf changed: insertion point missing")
    system.write_text(src.replace(anchor, section + anchor, 1))

launcher = repo / "system/rootfs/usr/libexec/banana/run-our-appstore"
launcher.parent.mkdir(parents=True, exist_ok=True)
launcher.write_text("""#!/bin/sh
# Dedicated custom-app Store, native KMS on both RG DS panels.
# Shares installed-app locations with BananaOS, not its catalog/cache.
S=/data/store
mkdir -p "$S/our-apps" "$S/apps" "$S/tiles"
cd "$S" || exit 1
export DK_DATA="$S/our-apps" DK_TOP=DSI-2 DK_TOUCH_BOTTOM=fe5e0000.i2c
export RNDS_STORE_CLI=/usr/share/banana/apps/ourstore/rocknixds-store
export RNDS_STORE_DATA="$S/our-apps" RNDS_STORE_PLATFORM=banana
export RNDS_STORE_CATALOG=https://raw.githubusercontent.com/michaelodorisio137-blip/bananaosotg/main/our-apps/catalog.json
exec /usr/bin/rocknixds-store-ui --backend kms
""")
launcher.chmod(0o755)

appdir = repo / "system/rootfs/usr/share/banana/apps/ourstore"
appdir.mkdir(parents=True, exist_ok=True)
(appdir / "OurApps.app").touch()
(appdir / "gamelist.xml").write_text("""<?xml version="1.0" encoding="utf-8"?>
<gameList><game><path>./OurApps.app</path><name>Our Apps</name>
<desc>Download and update our RG DS native apps over Wi-Fi. Separate from the original Store.</desc>
<developer>RG DS custom</developer><genre>Tool</genre></game></gameList>
""")

localcat = repo / "store/our-apps/catalog.json"
localcat.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(source, localcat)

mk = repo / "buildroot/package/rocknixds-store/rocknixds-store.mk"
old = mk.read_text()
marker = "# Our Apps custom catalog installed separately from BananaOS's Store."
if marker not in old:
    anchor = "\t$(INSTALL) -m 0644 $(BR2_EXTERNAL_BANANA_PATH)/../store/catalog.json $(TARGET_DIR)/usr/share/banana/apps/store/catalog.json\n"
    if anchor not in old:
        raise SystemExit("Store Buildroot makefile changed: insertion point missing")
    extra = """\t# Our Apps custom catalog installed separately from BananaOS's Store.
\t$(INSTALL) -D -m 0755 $(@D)/store/device/rocknixds-store $(TARGET_DIR)/usr/share/banana/apps/ourstore/rocknixds-store
\t$(INSTALL) -D -m 0644 $(BR2_EXTERNAL_BANANA_PATH)/../store/our-apps/catalog.json $(TARGET_DIR)/usr/share/banana/apps/ourstore/catalog.json
"""
    mk.write_text(old.replace(anchor, anchor + extra, 1))
print("Our Apps integrated: separate tile, catalog and cache; original Store unchanged.")
