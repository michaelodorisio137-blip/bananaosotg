#!/usr/bin/env python3
"""CI guard: preserve all upstream BananaOS settings except explicitly approved defaults.

Run after apply.py inside a fresh JorreFog/BananaLinux git checkout.
This check rejects unexpected tracked-source modifications and unexpected
settings/default changes. It cannot replace an on-device functional test.
"""
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 2:
    sys.exit("Usage: python3 verify-preservation.py /path/to/BananaLinux")
root = Path(sys.argv[1]).resolve()
if not (root / ".git").exists():
    sys.exit("Expected a fresh Git checkout of BananaLinux")

def git(*args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)

def upstream(path):
    return git("show", "HEAD:" + path)

def patched(path):
    return (root / path).read_text()

# Every tracked file changed by our overlay must be on this explicit allowlist.
# All unlisted emulator sources, launchers, UI, assets, scripts and features
# remain byte-for-byte those of the upstream checkout.
allowed_changed = {
    "system/rootfs/usr/libexec/banana/sd2",
    "system/rootfs/etc/init.d/rcS",
    "ui/src/fileops.cpp",
    "system/rootfs/etc/banana/settings.conf",
    "ui/src/settings_defaults.cpp",
    "system/rootfs/usr/libexec/banana/nds-buttons",
    "system/rootfs/usr/libexec/banana/run-retroarch",
    "system/rootfs/usr/libexec/banana/run-bananafront",
    "ui/src/main.cpp",      # optional startup-audio playback
    "ui/src/sound.cpp",     # optional menu-music mixer
    "ui/src/splash.cpp",    # original RG DS DUNGEON O boot renderer
    "ui/src/settings.cpp",  # additive filter choices, existing options retained
    "ui/src/layout.cpp",    # explicit DS-style clock, calendar and preview hooks
    "ui/src/library.cpp",   # game screenshot preview metadata
    "ui/src/library.h",
    "ui/rnds/RndsUI.h",
    "ui/src/settings.cpp",              # requested renderer controls
    "ui/src/splash.cpp",                # DUNGEON O boot
    "system/rootfs/usr/libexec/banana/run-drastic",
    "buildroot/package/superdrastic/superdrastic.mk",
}
changed = set(git("diff", "--name-only").splitlines())
unexpected = sorted(changed - allowed_changed)
if unexpected:
    sys.exit("Unexpected BananaOS source modifications: " + ", ".join(unexpected))
missing = sorted({
    "system/rootfs/etc/banana/settings.conf",
    "ui/src/settings_defaults.cpp",
} - changed)
if missing:
    sys.exit("Expected control-default changes are missing: " + ", ".join(missing))

# Require the shipped settings template to be *identical* to upstream except
# three explicitly requested shoulder-button defaults.
template = "system/rootfs/etc/banana/settings.conf"
expected = upstream(template)
for before, after in (
    ("nds_btn_l2 = swap", "nds_btn_l2 = l"),
    ("nds_btn_r2 = ff", "nds_btn_r2 = r"),
    ("ra_btn_r2.gba = ff", "ra_btn_r2.gba = game"),
    ("theme = dark", "theme = user:rgds-ds-classic"),
):
    if expected.count(before + "\n") != 1:
        sys.exit("Upstream settings template changed around " + before)
    expected = expected.replace(before + "\n", after + "\n", 1)
if patched(template) != expected:
    sys.exit("settings.conf has unrelated edits; refusing firmware build")

# The settings menu's definitions must likewise differ in ONLY two defaults.
defaults = "ui/src/settings_defaults.cpp"
expected = upstream(defaults)
for before, after in (
    ('const char* const SHADERS[] = { "off", "lcd", "crt", "sharp", nullptr };',
     'const char* const SHADERS[] = { "off", "lcd", "crt", "sharp", "bilinear", "threepoint", nullptr };\n'
     '        const char* const N64_TEXTURE_FILTER[] = { "3point", "standard", nullptr };\n'
     '        const char* const RGDS_SCREEN_OVERRIDES[] = { "inherit", "off", "bilinear", "threepoint", "lcd", "crt", "sharp", nullptr };'),
    ('{ "ra_shader", "off", ENUM, SHADERS, 0, 0, true },',
     '{ "ra_shader", "off", ENUM, SHADERS, 0, 0, true },\n'
     '            { "rgds_n64_texfilter", "3point", ENUM, N64_TEXTURE_FILTER, 0, 0, true },\n'
     '            { "ra_shader_override", "inherit", ENUM, RGDS_SCREEN_OVERRIDES, 0, 0, true, true },'),
    ('{ "theme", "dark", TEXT, nullptr, 0, 0 }',
     '{ "theme", "user:rgds-ds-classic", TEXT, nullptr, 0, 0 }'),
    ('{ "nds_btn_l2", "swap", ENUM, NDS_BTN, 0, 0, true },',
     '{ "nds_btn_l2", "l", ENUM, NDS_BTN, 0, 0, true },'),
    ('{ "nds_btn_r2", "ff", ENUM, NDS_BTN, 0, 0, true },',
     '{ "nds_btn_r2", "r", ENUM, NDS_BTN, 0, 0, true },'),
):
    if expected.count(before) != 1:
        sys.exit("Upstream settings definitions changed around " + before)
    expected = expected.replace(before, after, 1)
if patched(defaults) != expected:
    sys.exit("settings_defaults.cpp has unrelated edits; refusing firmware build")

# Confirm the new features are additive assets. The original RG DS was not
# shipped with a board-specific tuned profile; the Plus's measured profile
# must remain identical to its upstream content.
eq = root / "ui/assets/speaker-eq/rgds.txt"
if not eq.is_file():
    sys.exit("Original RG DS speaker EQ preset missing")
eq_text = eq.read_text()
for token in ("Preamp: -4.0 dB", "Filter 1: ON HPQ Fc 145 Hz", "Filter 7: ON PK Fc 8000 Hz"):
    if token not in eq_text:
        sys.exit("Original RG DS speaker EQ preset corrupted: " + token)
plus = "ui/assets/speaker-eq/rgds-plus.txt"
if patched(plus) != upstream(plus):
    sys.exit("Existing measured RG DS Plus speaker EQ changed")
if not (root / "system/rootfs/usr/share/banana/themes/rgds-ds-classic.json").is_file():
    sys.exit("DS-style menu theme missing")

# The native SuperDrastic 3D filtering option must be independent of the
# on-panel shader and accept compiled 0/1/2 modes plus custom 3-point mode.
settings_ui = patched("ui/src/settings.cpp")
if ('sd, "DSFLIP_RAST_TEXFILTER",' not in settings_ui or
    '"Nearest", "Bilinear", "Sharp bilinear", "N64 3-point"' not in settings_ui):
    sys.exit("SuperDrastic polygon texture filtering UI missing")
if 'menu, "ra_shader", { "Off", "LCD", "CRT", "Sharp pixels", "Bilinear", "N64 3-point" }' not in settings_ui:
    sys.exit("Global screen filter choices missing")
if 'RG DS DUNGEON O custom dual-panel startup' not in patched("ui/src/splash.cpp"):
    sys.exit("Custom original RG DS boot renderer missing")
for shader in ("rgds-threepoint.frag", "rgds-bilinear.frag"):
    if not (root / "system/rootfs/usr/lib/superdrastic/shaders" / shader).is_file():
        sys.exit("Custom DS screen shader missing: " + shader)
for shader in ("threepoint.glslp", "threepoint.glsl", "bilinear.glslp", "bilinear.glsl"):
    if not (root / "system/rootfs/usr/share/libretro/shaders/glsl/rgds" / shader).is_file():
        sys.exit("RetroArch screen shader missing: " + shader)

for rel in (
    "system/rootfs/usr/share/libretro/shaders/glsl/rgds/threepoint.glsl",
    "system/rootfs/usr/share/libretro/shaders/glsl/rgds/threepoint.glslp",
    "system/rootfs/usr/share/libretro/shaders/glsl/rgds/bilinear.glsl",
    "system/rootfs/usr/lib/superdrastic/shaders/rgds-threepoint.frag",
    "system/rootfs/usr/lib/superdrastic/shaders/rgds-bilinear.frag",
    "buildroot/package/superdrastic/rgds-superdrastic-3point.py",
):
    if not (root / rel).is_file():
        sys.exit("Requested renderer asset missing: " + rel)

# New original RG DS analog touchscreen modes: explicit opt-in, preserve 3D
# texture filtering and every existing setting. The native SuperDrastic patch
# must be present for the Settings rows to be functional.
for token in ('"DSFLIP_ANALOG_TOUCH"', '"DSFLIP_ANALOG_DEADZONE"', '"DSFLIP_ANALOG_SENSITIVITY"'):
    if token not in patched("ui/src/settings.cpp"):
        sys.exit("RG DS analog controls missing from SuperDrastic Settings: " + token)
an_alog = root / "buildroot/patches/superdrastic/0002-rgds-right-analog-stylus.patch"
if not an_alog.is_file() or "rgds_analog_tick" not in an_alog.read_text():
    sys.exit("SuperDrastic analog SDL input patch missing")

# The optional native CPAD mode writes genuine analog coordinates to guest RAM
# for separately patched DS games; without an opt-in it remains inactive.
if ('"DSFLIP_CPAD"' not in patched("ui/src/settings.cpp") or
    '"DSFLIP_CPAD_LAYOUT"' not in patched("ui/src/settings.cpp")):
    sys.exit("Circle Pad patch controls missing from SuperDrastic menu")
cpad_file = root / "buildroot/patches/superdrastic/0003-rgds-cpad-guest-ram.patch"
if not cpad_file.is_file() or "rgds_cpad_store" not in cpad_file.read_text():
    sys.exit("Real analog guest-memory bridge missing")

# This protects important existing features from accidental removal in source.
for path, tokens in {
    "system/rootfs/etc/banana/settings.conf": (
        "pokemon_companion = off", "game_companion = off",
        "speaker_eq = on", "quick_resume = off",
        "ra_frontend = auto", "core.gba = gpsp",
        "ra_btn_back.gba = companion",
    ),
    "ui/src/main.cpp": (
        "Host lib(", "lib.dsCartIcons", "lib.twelveHour",
        "normalizeSettings(", "settings[\"timezone\"]",
    ),
}.items():
    source = patched(path)
    for token in tokens:
        if token not in source:
            sys.exit("Preserved feature missing from " + path + ": " + token)

print("PASS: No unexpected modified BananaOS source files")
print("PASS: All unspecified settings.conf options exactly match upstream")
print("PASS: All unspecified settings-menu defaults exactly match upstream")
print("PASS: Existing dual-screen companions, menu settings and saves retained")
print("Allowed changes:", ", ".join(sorted(changed)))
