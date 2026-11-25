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

# AzeezOS: shared game-library region sort (all console shelves).
# Keep the actual ROM paths, game titles, favorites, and saves untouched.
libh = repo / "ui/src/library.h"
libcpp = repo / "ui/src/library.cpp"
main = repo / "ui/src/main.cpp"
menu = repo / "ui/src/settings.cpp"
sub(libh, 'std::string sort;\t\t// the sort title',
    'int region = 12; // AzeezOS region group, Unknown by default\n\t\tstd::string sort;\t\t// the sort title')
sub(libh, 'bool dsCartIcons = false;', 'bool dsCartIcons = false;\n\t\tbool sortByRegion = false;')
anchor = 'static std::string sortKey(const Game& g) { return lower(g.sort.empty() ? g.title : g.sort); }'
region_code = r'''
	// Region comes from explicit gamelist metadata or recognized ROM filename tags.
	// Only match whole tokens: language tags and words inside titles are not regions.
	static int regionToken(const std::string& token)
	{
		const std::string t = lower(trim(token));
		if (t == "usa" || t == "us" || t == "u" || t == "united states" || t == "north america" || t == "ntsc-u" || t == "ntsc-u/c" || t == "canada") return 0;
		if (t == "europe" || t == "eu" || t == "eur" || t == "e" || t == "pal" || t == "uk" || t == "united kingdom" || t == "france" || t == "germany" || t == "spain" || t == "italy" || t == "netherlands" || t == "sweden" || t == "scandinavia") return 1;
		if (t == "japan" || t == "jp" || t == "jpn" || t == "j" || t == "ntsc-j") return 2;
		if (t == "world" || t == "w" || t == "worldwide" || t == "global" || t == "international" || t == "region free" || t == "region-free") return 3;
		if (t == "korea" || t == "south korea" || t == "kor" || t == "kr" || t == "k") return 5;
		if (t == "china" || t == "chn" || t == "cn" || t == "hong kong") return 6;
		if (t == "taiwan" || t == "tw") return 7;
		if (t == "asia" || t == "asi") return 8;
		if (t == "australia" || t == "aus" || t == "new zealand") return 9;
		if (t == "brazil" || t == "br" || t == "latin america" || t == "mexico") return 10;
		if (t == "russia" || t == "russian federation" || t == "rus" || t == "south africa" || t == "other") return 11;
		return 12;
	}

	static unsigned regionMask(const std::string& s)
	{
		unsigned mask = 0;
		size_t start = 0;
		while (start < s.size())
		{
			size_t end = s.find_first_of(",;|+", start);
			int r = regionToken(s.substr(start, end == std::string::npos ? end : end - start));
			if (r != 12) mask |= 1u << r;
			if (end == std::string::npos) break;
			start = end + 1;
		}
		return mask;
	}

	static int regionGroup(const std::string& metadata, const std::string& stem)
	{
		unsigned mask = regionMask(metadata);
		if (!mask)
		{
			// Parse trailing No-Intro / Redump / GoodTools tags only.
			std::string rest = trim(stem);
			while (!rest.empty() && (rest.back() == ')' || rest.back() == ']'))
			{
				size_t at = rest.rfind(rest.back() == ')' ? '(' : '[');
				if (at == std::string::npos || at == 0) break;
				mask |= regionMask(rest.substr(at + 1, rest.size() - at - 2));
				rest = trim(rest.substr(0, at));
			}
		}
		if (!mask) return 12;
		if (mask & (1u << 3)) return 3;
		if (mask & (mask - 1)) return 4;
		for (int i = 0; i < 12; ++i) if (mask & (1u << i)) return i;
		return 12;
	}

	static const char* regionName(int region)
	{
		static const char* const names[] = {
			"USA / North America", "Europe", "Japan", "World", "Multi-region",
			"Korea", "China", "Taiwan", "Asia", "Australia / NZ",
			"Latin America", "Other", "Unknown"
		};
		return names[region >= 0 && region <= 12 ? region : 12];
	}

	static bool regionLess(const Game& a, const Game& b, bool enabled)
	{
		if (enabled && a.region != b.region) return a.region < b.region;
		return sortKey(a) < sortKey(b);
	}
'''
sub(libcpp, anchor, anchor + "\n" + region_code)
# The existing preview patch has added screenshot to the XML entry by now.
sub(libcpp, 'boxback, screenshot;', 'boxback, screenshot, region;')
sub(libcpp, 'e.date = xmlText(b, "releasedate");', 'e.date = xmlText(b, "releasedate"); e.region = xmlText(b, "region");')
sub(libcpp, 'auto it = gl.find(rel);', 'auto it = gl.find(rel);\n\t\t\t\t\tg.region = regionGroup(it == gl.end() ? "" : it->second.region, stem);')
for shelf in ("sh", "fav"):
    sub(libcpp,
        'std::sort(' + shelf + '.games.begin(), ' + shelf + '.games.end(), [](const Game& a, const Game& b) { return sortKey(a) < sortKey(b); });',
        'std::sort(' + shelf + '.games.begin(), ' + shelf + '.games.end(), [this](const Game& a, const Game& b) { return regionLess(a, b, sortByRegion); });')
sub(libcpp, 'return sortKey(srch.games[a]) < sortKey(srch.games[b]);',
    'return regionLess(srch.games[a], srch.games[b], sortByRegion);')
sub(libcpp, 'r.plays = std::to_string(g.plays);',
    'if (sortByRegion) r.sub = std::string(regionName(g.region)) + " | " + r.sub;\n\t\tr.plays = std::to_string(g.plays);')
sub(menu, 'add(ML, "picture", "Motion",',
    'add(ML, "picture", "Game sort", "Sort every console by title or ROM region. Unknown regions stay at the end.", menu, "game_sort", { "Alphabetical", "Region" }, { "title", "region" });\n\t\t\tadd(ML, "picture", "Motion",')
sub(defs, 'const char* const DS_CART_ART[] = { "box", "icon", nullptr };',
    'const char* const DS_CART_ART[] = { "box", "icon", nullptr };\n\t\tconst char* const GAME_SORT[] = { "title", "region", nullptr };')
sub(defs, '{ "ds_cart_art", "box", ENUM, DS_CART_ART, 0, 0 },',
    '{ "ds_cart_art", "box", ENUM, DS_CART_ART, 0, 0 },\n\t\t\t{ "game_sort", "title", ENUM, GAME_SORT, 0, 0 },')
sub(conf, 'ds_cart_art = box\n', 'ds_cart_art = box\n# Game list ordering: title or region, then title.\ngame_sort = title\n')
sub(main, 'Host lib(o.systems, o.roms, o.data, o.assets);',
    'Host lib(o.systems, o.roms, o.data, o.assets);\n\tlib.sortByRegion = settings["game_sort"] == "region";')
sub(main, 'sound.enabled = settings["sounds"] != "off";\n\t\t\tbottomReload();',
    'sound.enabled = settings["sounds"] != "off";\n\t\t\tif (lib.sortByRegion != (settings["game_sort"] == "region")) {\n\t\t\t\tlib.sortByRegion = settings["game_sort"] == "region";\n\t\t\t\tafterShelves(lib, *ui);\n\t\t\t}\n\t\t\tbottomReload();')
print("AzeezOS: global alphabetical or region game sort installed.")
