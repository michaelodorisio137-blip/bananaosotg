#!/usr/bin/env python3
from pathlib import Path
import sys
repo=Path(sys.argv[1])
conf=repo/"system/rootfs/etc/banana/settings.conf"
defs=repo/"ui/src/settings_defaults.cpp"
def sub(path, old, new):
    body=path.read_text()
    if new in body: return
    if body.count(old)!=1: raise SystemExit("Region anchor mismatch: "+str(path)+": "+repr(old[:80]))
    path.write_text(body.replace(old,new,1))
# AzeezOS: shared game-library region sort (all console shelves).
# Keep the actual ROM paths, game titles, favorites, and saves untouched.
libh = repo / "ui/src/library.h"
libcpp = repo / "ui/src/library.cpp"
main = repo / "ui/src/main.cpp"
menu = repo / "ui/src/settings.cpp"
sub(libh, 'std::string sort;\t\t// the sort title',
    'int region = 12; // AzeezOS region group, Unknown by default\n\t\tstd::string developer, publisher;\n\t\tstd::string sort;\t\t// the sort title')
sub(libh, 'bool dsCartIcons = false;', 'bool dsCartIcons = false;\n\t\tstd::string gameSort = "title";')
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

	static std::string groupLabel(const Game& g, const std::string& mode)
	{
		if (mode == "region") return regionName(g.region);
		if (mode == "genre") return trim(g.genre);
		if (mode == "developer") return trim(g.developer);
		if (mode == "publisher") return trim(g.publisher);
		return "";
	}
	static std::string groupKey(const Game& g, const std::string& mode)
	{
		std::string v = lower(groupLabel(g, mode));
		if (v == "unknown" || v == "n/a" || v == "not available" || v == "-") v.clear();
		return v;
	}
	static bool regionLess(const Game& a, const Game& b, const std::string& mode)
	{
		if (mode == "region" && a.region != b.region) return a.region < b.region;
		if (mode == "genre" || mode == "developer" || mode == "publisher")
		{
			const std::string x = groupKey(a, mode), y = groupKey(b, mode);
			if (x.empty() != y.empty()) return !x.empty();
			if (x != y) return x < y;
		}
		if (sortKey(a) != sortKey(b)) return sortKey(a) < sortKey(b);
		return a.path < b.path;
	}
'''
sub(libcpp, anchor, anchor + "\n" + region_code)
# The existing preview patch has added screenshot to the XML entry by now.
sub(libcpp, 'boxback, screenshot;', 'boxback, screenshot, region, developer, publisher;')
sub(libcpp, 'e.date = xmlText(b, "releasedate");', 'e.date = xmlText(b, "releasedate"); e.region = xmlText(b, "region"); e.developer = xmlText(b, "developer"); e.publisher = xmlText(b, "publisher");')
sub(libcpp, 'auto it = gl.find(rel);', 'auto it = gl.find(rel);\n\t\t\t\t\tg.region = regionGroup(it == gl.end() ? "" : it->second.region, stem);\n\t\t\t\t\tif (it != gl.end()) { g.developer = it->second.developer; g.publisher = it->second.publisher; }')
for shelf in ("sh", "fav"):
    sub(libcpp,
        'std::sort(' + shelf + '.games.begin(), ' + shelf + '.games.end(), [](const Game& a, const Game& b) { return sortKey(a) < sortKey(b); });',
        'std::sort(' + shelf + '.games.begin(), ' + shelf + '.games.end(), [this](const Game& a, const Game& b) { return regionLess(a, b, gameSort); });')
sub(libcpp, 'return sortKey(srch.games[a]) < sortKey(srch.games[b]);',
    'return regionLess(srch.games[a], srch.games[b], gameSort);')
sub(libcpp, 'r.plays = std::to_string(g.plays);',
    'if (gameSort != "title" && gameSort != "genre") r.sub = (groupKey(g, gameSort).empty() ? "Unknown" : groupLabel(g, gameSort)) + " | " + r.sub;\n\t\tif (gameSort == "genre" && groupKey(g, gameSort).empty()) r.sub = "Unknown | " + r.sub;\n\t\tr.plays = std::to_string(g.plays);')
sub(menu, 'add(ML, "picture", "Motion",',
    'add(ML, "picture", "Game sort", "Sort every console by title, region, genre, developer or publisher. Missing metadata stays at the end.", menu, "game_sort", { "Alphabetical", "Region", "Genre", "Developer", "Publisher" }, { "title", "region", "genre", "developer", "publisher" });\n\t\t\tadd(ML, "picture", "Motion",')
sub(defs, 'const char* const DS_CART_ART[] = { "box", "icon", nullptr };',
    'const char* const DS_CART_ART[] = { "box", "icon", nullptr };\n\t\tconst char* const GAME_SORT[] = { "title", "region", "genre", "developer", "publisher", nullptr };')
sub(defs, '{ "ds_cart_art", "box", ENUM, DS_CART_ART, 0, 0 },',
    '{ "ds_cart_art", "box", ENUM, DS_CART_ART, 0, 0 },\n\t\t\t{ "game_sort", "title", ENUM, GAME_SORT, 0, 0 },')
sub(conf, 'ds_cart_art = box\n', 'ds_cart_art = box\n# Game list ordering: title or region, then title.\ngame_sort = title\n')
sub(main, 'Host lib(o.systems, o.roms, o.data, o.assets);',
    'Host lib(o.systems, o.roms, o.data, o.assets);\n\tlib.gameSort = settings["game_sort"].empty() ? "title" : settings["game_sort"];')
sub(main, 'sound.enabled = settings["sounds"] != "off";\n\t\t\tbottomReload();',
    'sound.enabled = settings["sounds"] != "off";\n\t\t\tif (lib.gameSort != (settings["game_sort"].empty() ? "title" : settings["game_sort"])) {\n\t\t\t\tlib.gameSort = settings["game_sort"].empty() ? "title" : settings["game_sort"];\n\t\t\t\tafterShelves(lib, *ui);\n\t\t\t}\n\t\t\tbottomReload();')
sub(libcpp, 'lower(g.genre) + " " + g.year;', 'lower(g.genre) + " " + g.year + " " + lower(g.developer) + " " + lower(g.publisher);')
print("AzeezOS: alphabetical, region, genre, developer and publisher sort installed.")
