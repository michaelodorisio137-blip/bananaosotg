#!/usr/bin/env python3
"""Install the DS-inspired upper screen, clock, calendar and screenshot preview."""
from pathlib import Path
import shutil
import sys

if len(sys.argv) != 2:
    sys.exit("Usage: python3 rgds-menu-patch.py /path/to/BananaLinux")
repo = Path(sys.argv[1])
theme = Path(__file__).with_name("rgds-ds-classic.json")
if not theme.exists():
    sys.exit("Missing RG DS menu theme JSON")

def sub(path, old, new):
    body = path.read_text()
    if new in body:
        return
    if old not in body:
        sys.exit("RG DS menu patch mismatch in " + str(path) + ": " + old[:65])
    path.write_text(body.replace(old, new, 1))

themes = repo / "system/rootfs/usr/share/banana/themes"
themes.mkdir(parents=True, exist_ok=True)
shutil.copyfile(theme, themes / "rgds-ds-classic.json")

layout = repo / "ui/src/layout.cpp"
sub(layout, '"clock", "date", "battery"',
    '"clock", "date", "calendar.hour", "calendar.minute", "calendar.day", "calendar.first", "calendar.days", "calendar.label", "battery"')
anchor = 'if (nId == HOOK("date")) { out = EV(date); return true; }'
more = r'''if (nId == HOOK("calendar.hour") || nId == HOOK("calendar.minute") ||
                nId == HOOK("calendar.day") || nId == HOOK("calendar.first") ||
                nId == HOOK("calendar.days") || nId == HOOK("calendar.label"))
            {
                usedTime = true;
                time_t t = time(nullptr);
                struct tm nowtm = {};
                localtime_r(&t, &nowtm);
                if (nId == HOOK("calendar.hour")) out = EV((double)nowtm.tm_hour);
                else if (nId == HOOK("calendar.minute")) out = EV((double)nowtm.tm_min);
                else if (nId == HOOK("calendar.day")) out = EV((double)nowtm.tm_mday);
                else if (nId == HOOK("calendar.first")) out = EV((double)((nowtm.tm_wday - (nowtm.tm_mday - 1) % 7 + 7) % 7));
                else if (nId == HOOK("calendar.days"))
                {
                    const int y = nowtm.tm_year + 1900, m = nowtm.tm_mon;
                    const int days[] = {31,28,31,30,31,30,31,31,30,31,30,31};
                    const bool leap = y % 4 == 0 && (y % 100 != 0 || y % 400 == 0);
                    out = EV((double)(days[m] + (m == 1 && leap)));
                }
                else
                {
                    char label[48];
                    strftime(label, sizeof label, "%B %Y", &nowtm);
                    out = EV(std::string(label));
                }
                return true;
            }'''
sub(layout, anchor, anchor + "\n\t\t\t" + more)

# Screenshots are available alongside existing metadata; preserve box art.
libh = repo / "ui/src/library.h"
rndsh = repo / "ui/rnds/RndsUI.h"
libcpp = repo / "ui/src/library.cpp"
sub(libh, 'std::string box, cart, label;', 'std::string box, cart, label, preview;')
sub(rndsh, 'std::string box;\t\t// the 2D box cover (top screen)',
    'std::string box;\t\t// the 2D box cover (top screen)\n\t\tstd::string preview; // screenshot preview')
sub(libcpp,
    'std::string name, sortname, genre, date, image, thumb, cart, boxback;',
    'std::string name, sortname, genre, date, image, thumb, cart, boxback, screenshot;')
sub(libcpp,
    'e.image = rel(xmlText(b, "image")); e.thumb = rel(xmlText(b, "thumbnail"));',
    'e.image = rel(xmlText(b, "image")); e.thumb = rel(xmlText(b, "thumbnail")); e.screenshot = rel(xmlText(b, "screenshot"));')
sub(libcpp,
    'if (exists(it->second.cart)) g.cart = it->second.cart;',
    'if (exists(it->second.cart)) g.cart = it->second.cart;\n\t\t\t\t\t\tif (exists(it->second.screenshot)) g.preview = it->second.screenshot;')
sub(libcpp,
    'if (g.label.empty()) g.label = media.find(dir, "label", stem);',
    'if (g.label.empty()) g.label = media.find(dir, "label", stem);\n\t\t\t\t\tif (g.preview.empty()) g.preview = media.find(dir, "screenshot", stem);\n\t\t\t\t\tif (g.preview.empty()) g.preview = media.find(dir, "screenshots", stem);')
sub(libcpp,
    'r.box = g.box; r.cart = g.cart; r.label = g.label;',
    'r.box = g.box; r.cart = g.cart; r.label = g.label; r.preview = g.preview;')
sub(layout,
    '"label", "art", "rom"',
    '"label", "art", "preview", "rom"')
anchor = 'else if (fId == GAMEF("rom")) out = EV(g.rom);'
sub(layout, anchor,
    'else if (fId == GAMEF("preview")) out = EV(g.preview);\n\t\t\t' + anchor)

# Use our menu on new installations, and upgrade stock dark-theme SD cards
# once; users who selected another theme keep their preference.
conf = repo / "system/rootfs/etc/banana/settings.conf"
defs = repo / "ui/src/settings_defaults.cpp"
sub(conf, 'theme = dark\n', 'theme = user:rgds-ds-classic\n')
sub(defs,
    '{ "theme", "dark", TEXT, nullptr, 0, 0 }',
    '{ "theme", "user:rgds-ds-classic", TEXT, nullptr, 0, 0 }')

rcs = repo / 'system/rootfs/etc/init.d/rcS'
anchor = '/usr/libexec/banana/data-layout\n'
migration = r'''# RG DS: install the DS-inspired menu over the untouched stock dark theme once.
RGDS_THEME_MARK=/data/banana/.rgds-classic-menu-v1
if [ ! -e "$RGDS_THEME_MARK" ]; then
    [ -f /data/banana/settings.conf ] &&
        sed -i 's/^ *theme *= *dark *$/theme = user:rgds-ds-classic/' /data/banana/settings.conf
    : > "$RGDS_THEME_MARK"
fi
'''
sub(rcs, anchor, anchor + migration)
print("RG DS menu: preview left, live clock upper-right, live monthly calendar lower-right.")
