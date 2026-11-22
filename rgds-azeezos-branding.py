#!/usr/bin/env python3
"""Brand the RG DS custom BananaOS build as AzeezOS in all visible surfaces.

Keep internal firmware ABI paths, board IDs, filesystem labels, startup device
paths, service names and package format unchanged for compatibility.
Requires Pillow on the build host to regenerate the pixel-art logos.
"""
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: rgds-azeezos-branding.py /path/to/BananaLinux")
root = Path(sys.argv[1]).resolve()
if not (root / "ui/src/settings.cpp").exists():
    raise SystemExit("Not a BananaLinux checkout")
def change(path, pairs):
    f = root / path
    src = f.read_text()
    for old, new in pairs:
        if old not in src and new not in src:
            raise SystemExit("Upstream branding anchor missing: " + path + ": " + old[:90])
        src = src.replace(old, new)
    f.write_text(src)

change("buildroot/board/rgds/post-build.sh", [
    ("NAME=BananaOS", "NAME=AzeezOS"),
    ("PRETTY_NAME=\"BananaOS %s\"", "PRETTY_NAME=\"AzeezOS %s\""),
    ("HOME_URL=\"https://github.com/JorreFog/BananaLinux\"", "HOME_URL=\"https://github.com/michaelodorisio137-blip/bananaosotg\""),
])
post = (root / "buildroot/board/rgds/post-build.sh").read_text()
if "ID=bananaos" not in post:
    raise SystemExit("Compatible machine identity was unexpectedly changed")

# Only presentation strings change. Never change paths, on-disk settings or API keys.
settings_path = root / "ui/src/settings.cpp"
s = settings_path.read_text()
s = s.replace("BananaOS", "AzeezOS")
for old, new in [
    ('"Banana "', '"AzeezOS "'),
    ('"Banana closes', '"AzeezOS closes'),
    ('"When Banana ', '"When AzeezOS '),
    ("The people who made this version of Banana", "The people who made this version of AzeezOS"),
    ('"For working on Banana itself:', '"For working on AzeezOS itself:'),
]:
    s = s.replace(old, new)
settings_path.write_text(s)

main_path = root / "ui/src/main.cpp"
s = main_path.read_text()
s = s.replace('"Banana closes', '"AzeezOS closes')
main_path.write_text(s)

readme = root / "system/rootfs/etc/banana/README.txt"
s = readme.read_text()
s = s.replace("BananaOS", "AzeezOS")
s = s.replace("\nBANANA\n", "\nAZEEZOS\n")
readme.write_text(s)

# The logo generator draws the matching hard-edged pixel wordmark in the
# existing Pixelify Sans; suffix OS stays white. Also writes splash word.png.
logo_script = root / "tools/make-logo.py"
s = logo_script.read_text()
old = 'WORD, SUFFIX = "BANANA", "OS"'
new = 'WORD, SUFFIX = "AZEEZ", "OS"'
if old not in s and new not in s:
    raise SystemExit("Upstream wordmark generator has changed")
logo_script.write_text(s.replace(old, new))
font = root / "ui/assets/rnds/fonts/PixelifySans-Medium.ttf"
bananas = root / "ui/assets/banana"
out = root / "ui/assets/rnds"
splash = root / "ui/assets/splash"
subprocess.run([sys.executable, str(logo_script), str(font), str(bananas), str(out), str(splash)], check=True)
for p in (out / "logo@1x.png", out / "logo@1.6x.png", splash / "word.png"):
    if not p.is_file() or p.stat().st_size < 70:
        raise SystemExit("AzeezOS visual asset missing: " + str(p))
print("AzeezOS: boot wordmark, menu logo, About/Credits, update descriptions and OS name updated.")
print("Preserved: ID=bananaos, /data/banana paths, banana-root partitions, internal updater formats.")
