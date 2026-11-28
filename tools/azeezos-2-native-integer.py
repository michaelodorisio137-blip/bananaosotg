#!/usr/bin/env python3
"""Opt-in native integer presentation; does not claim new core overscan."""
from pathlib import Path
import sys
import subprocess

root=Path(sys.argv[-1])
def replace(rel,old,new):
    p=root/rel
    s=p.read_text()
    if new in s: return
    if s.count(old)!=1: raise SystemExit("native integer anchor mismatch: "+rel+" "+repr(old[:80]))
    p.write_text(s.replace(old,new,1))

if sys.argv[1]=="--ui":
    # OS-wide BIOS directory picker.
    replace("ui/src/settings.cpp", 'const char* S = "System";', '''const char* S = "System";
        add(S, "gear", "BIOS folder", "Choose the shared emulator BIOS directory. Open a folder and press Y to select it.", "", "bios_folder_pick", {}, {}, Item::PAGE);''')
    replace("ui/src/settings.cpp", '{ "System", { "Updates",', '{ "System", { "BIOS folder", "Updates",')
    replace("ui/src/settings.cpp", 'if (it.key == "scrape") { startScrape(); return MOVED; }', '''if (it.key == "bios_folder_pick") { pickFolder(3, getConfValue(data + "/settings.conf", "bios_folder", "/data/bios"), "BIOS folder"); return MOVED; }
            if (it.key == "scrape") { startScrape(); return MOVED; }''')
    replace("ui/src/settings.cpp", 'else if (it.kind == Item::PAGE && it.key == "ds_name")', '''else if (it.kind == Item::PAGE && it.key == "bios_folder_pick") { v = getConfValue(data + "/settings.conf", "bios_folder", "/data/bios"); nameValue = true; }
            else if (it.kind == Item::PAGE && it.key == "ds_name")''')
    replace("ui/src/settings_defaults.cpp", '{ "game_sort", "title", ENUM, GAME_SORT, 0, 0 },', '{ "game_sort", "title", ENUM, GAME_SORT, 0, 0 },\n\t\t\t{ "bios_folder", "/data/bios", TEXT, nullptr, 0, 0 },')
    replace("ui/src/settings.h", "void pickFolder(int purpose,", "bool biosFolderPicking = false;\n\t\tvoid pickFolder(int purpose,")
    replace("ui/src/settings_files.cpp", "enum Pick { NO_PICK, PICK_DOWNLOAD, PICK_UNPACK };", "enum Pick { NO_PICK, PICK_DOWNLOAD, PICK_UNPACK, PICK_BIOS };")
    replace("ui/src/settings_files.cpp", "fm->pick = purpose == 2 ? Files::PICK_UNPACK : Files::PICK_DOWNLOAD;", "biosFolderPicking = purpose == 3;\n\t\tfm->pick = purpose == 3 ? Files::PICK_BIOS : purpose == 2 ? Files::PICK_UNPACK : Files::PICK_DOWNLOAD;")
    replace("ui/src/settings_files.cpp", 'pick == PICK_UNPACK ? "Unpacking " : "Downloading "', 'pick == PICK_BIOS ? "Selecting " : pick == PICK_UNPACK ? "Unpacking " : "Downloading "')
    replace("ui/src/settings_files.cpp", 'pick == PICK_UNPACK ? "Unpack here" : "Download here"', 'pick == PICK_BIOS ? "Use folder" : pick == PICK_UNPACK ? "Unpack here" : "Download here"')
    replace("ui/src/settings_files.cpp", '"B goes back to the download as it was."', '"B cancels folder selection."')
    replace("ui/src/settings_files.cpp", 'B goes up; from the cards, back to the download as it was.', 'B goes up; from the cards, cancels selection.')
    replace("ui/src/settings_servers.cpp", 'void Settings::folderPicked(const std::string& dir)\n\t{', '''void Settings::folderPicked(const std::string& dir)
    {
        if (biosFolderPicking)
        {
            biosFolderPicking = false;
            page = LIST;
            if (dir.empty() || dir[0] != '/' || dir.find_first_of("\\r\\n\\"\\\\") != std::string::npos)
                { message = "Unsupported BIOS folder name."; return; }
            setConfValue(data + "/settings.conf", "bios_folder", dir);
            message = "BIOS folder saved.";
            return;
        }''')
    replace("ui/src/settings_servers.cpp", 'void Settings::pickCancelled()\n\t{', '''void Settings::pickCancelled()
    {
        if (biosFolderPicking) { biosFolderPicking = false; page = LIST; return; }''')
    replace("ui/src/settings.cpp",
        'add(PS, "picture", "Integer scaling",',
        '''add(PS, "picture", "Native integer mode", "Use whole native pixels across supported emulators. Expanded renderers show real extra background where available; unsupported modes may retain borders.",
                menu, "azeez_native_integer", { "Off", "On" }, { "off", "on" });
            items.back().hints = { "Keep each emulator's existing display settings.", "Sharp square pixels; no fractional zoom." };
            add(PS, "picture", "GBA HD affine backgrounds", "Render rotating and scaling GBA backgrounds at 2x sample density while preserving native sprites and text.", menu, "azeez_gba_hd_affine", { "On", "Off" }, { "on", "off" });
            add(PS, "picture", "Integer scaling",''')
    replace("ui/src/settings_defaults.cpp",
        '{ "ra_border", "off", ENUM, ON_OFF, 0, 0, true },',
        '{ "ra_border", "off", ENUM, ON_OFF, 0, 0, true },\n\t\t\t{ "azeez_native_integer", "off", ENUM, ON_OFF, 0, 0, true },\n\t\t\t{ "azeez_gba_hd_affine", "on", ENUM, ON_OFF, 0, 0, true },')
    p=root/"ui/src/settings.cpp"
    s=p.read_text().replace("BananaDS","melonDS")
    # Label the modified implementation in selectors, not internal section keys.
    s=s.replace('{ "SuperDrastic", "melonDS" }','{ "SuperDrastic", "melonDS (Azeez Enhanced)" }')
    s=s.replace('{ "", "SuperDrastic", "melonDS" }','{ "", "SuperDrastic", "melonDS (Azeez Enhanced)" }')
    s=s.replace('global == "bananads" ? "melonDS"','global == "bananads" ? "melonDS (Azeez Enhanced)"')
    s=s.replace('getConfValue("/etc/banana/settings.conf", "nds_emulator", "superdrastic")','getConfValue("/etc/banana/settings.conf", "nds_emulator", "bananads")')
    # RG DS has one global 3D target selector and matching per-game overrides.
    old_start=s.index('add(BD, "nds", "3D resolution", "How sharp DS games')
    old_end=s.index('add(BD, "nds", "Edge marking",',old_start)
    s=s[:old_start]+s[old_end:]
    s=s.replace('GAME_RES_VALUES[] = { "", "1", "2", "3", "4" }','GAME_RES_VALUES[] = { "", "1", "2" }')
    s=s.replace('GAME_RES_NAMES[] = { "", "1x", "2x", "3x (experimental)", "4x (experimental)" }','GAME_RES_NAMES[] = { "", "240p (320x240)", "480p (640x480)" }')
    s=s.replace('for (int i = 1; i < 5; i++) if (r == GAME_RES_VALUES[i]) pgRes = i;', 'for (int i = 1; i < 3; i++) if (r == GAME_RES_VALUES[i]) pgRes = i; if (r == "3" || r == "4") pgRes = 2;')
    s=s.replace('(pgRes + d + 5) % 5','(pgRes + d + 3) % 3')
    s=s.replace('std::string gres = getConfValue("/data/bananads/bananads.conf", "render.scale", "1");','std::string gres = getConfValue("/data/bananads/bananads.conf", "render.expanded_scale", "1");')
    s=s.replace('gres == "4" ? "4x (experimental)" : gres == "3" ? "3x (experimental)" : gres == "2" ? "2x" : "1x"','gres == "2" ? "480p (640x480)" : "240p (320x240)"')
    anchor='add(BD, "nds", "Edge marking",'
    assert s.count(anchor)==1
    s=s.replace(anchor,'''add(BD, "nds", "Expanded 3D camera", "Experimental: expand the 3D scene together with the 2D viewport in Native integer mode. Turn off if a game has visual problems.",
                menu, "azeez_ds_wide3d", { "On", "Off" }, { "on", "off" });
            add(BD, "nds", "Expanded 3D resolution", "Actual 3D raster size in expanded mode. Both keep DS 2D pixels at exact 2x on the 640x480 panels. Native is the faster mode.",
                bds, "render.expanded_scale", { "240p (320x240)", "480p (640x480)" }, { "1", "2" });
            items.back().def = "1";
            add(BD, "nds", "DS integer presentation", "Use a centered 320x240 canvas on RG DS. Off restores the original presentation unless global Native integer mode is on.",
                menu, "azeez_ds_integer", { "On", "Off" }, { "on", "off" });
            '''+anchor,1)
    p.write_text(s)
    p=root/"ui/src/settings_defaults.cpp"
    s=p.read_text().replace('{ "nds_emulator", "superdrastic",','{ "nds_emulator", "bananads",')
    anchor='{ "azeez_gba_hd_affine", "on", ENUM, ON_OFF, 0, 0, true },'
    assert s.count(anchor)==1
    p.write_text(s.replace(anchor,anchor+'\n\t\t\t{ "azeez_ds_wide3d", "on", ENUM, ON_OFF, 0, 0, true },\n\t\t\t{ "azeez_ds_integer", "on", ENUM, ON_OFF, 0, 0, true },'))
    sys.exit(0)

base="usr/libexec/banana/"
bf=base+"run-bananafront"
ra=base+"run-retroarch"
ds=base+"run-drastic"
bd=base+"run-bananads"
# Renderer flag and core selection before the frontend starts.
for launcher in (ra,bf):
    marker='CFG=/data/retroarch/retroarch.cfg'
    replace(launcher,marker,'''if [ "$(setting azeez_native_integer)" = on ]; then
    export AZEEZ_EXPANDED_VIEWPORT=1
    export AZEEZ_GBA_HD_AFFINE="$(setting azeez_gba_hd_affine)"
    case "$BANANA_SYSTEM" in
        nes) VCORE=fceumm ;;
        megadrive) VCORE=genesis_plus_gx_wide ;;
        snes) VCORE=bananasnes ;;
        gb|gbc|gba) VCORE=mgba_integer ;;
        *) VCORE= ;;
    esac
    if [ -n "$VCORE" ] && [ -f "/usr/lib/libretro/${VCORE}_libretro.so" ]; then
        CORE="/usr/lib/libretro/${VCORE}_libretro.so"
    fi
fi
'''+marker)
replace(bf,'[ -n "$SH" ] && [ -d /usr/lib/superdrastic/shaders ]',
    '''if [ "$(setting azeez_native_integer)" = on ]; then
    SH=
    export BANANAFRONT_BORDER=off BANANAFRONT_PLANE_SCALE=0
fi
[ -n "$SH" ] && [ -d /usr/lib/superdrastic/shaders ]''')
replace(bf,'if [ "$(ra_cfg video_scale_integer)" = true ] || [ "$CORE" = /usr/lib/libretro/mgba_integer_libretro.so ]; then',
    'if [ "$(setting azeez_native_integer)" = on ] || [ "$(ra_cfg video_scale_integer)" = true ] || [ "$CORE" = /usr/lib/libretro/mgba_integer_libretro.so ]; then')
# Use existing border-config backup/recovery, not the button backup.
replace(ra,"BKEYS='^(aspect_ratio_index|",
    "BKEYS='^(video_shader_enable|video_smooth|aspect_ratio_index|")
replace(ra,'if [ "$(setting ra_border)" = on ] && [ -n "$BANANA_SYSTEM" ]; then',
    '''AZ_INT=0
case "$CORE" in */mgba_integer_libretro.so) AZ_INT=1 ;; esac
[ "$(setting azeez_native_integer)" = on ] && AZ_INT=1
case "$AZEEZ_N64_MODE" in 240p|480p) AZ_INT=1 ;; esac
if [ "$AZ_INT" = 0 ] && [ "$(setting ra_border)" = on ] && [ -n "$BANANA_SYSTEM" ]; then''')
p=root/ra
s=p.read_text()
start=s.index("# AzeezOS Maximum Integer: native 640x480, no further interpolation.")
end=s.index("# anything RetroArch keeps that retroarch.cfg doesn't place",start)
s=s[:start]+'''# AzeezOS native integer presentation. Core-provided geometry remains intact.
if [ "$AZ_INT" = 1 ]; then
    grep -E "$BKEYS" "$CFG" > "$BKEEP.new" || :
    mv "$BKEEP.new" "$BKEEP" && sync
    {
        printf '%s\\n' 'video_shader_enable = "false"' 'video_smooth = "false"' 'video_scale_integer = "true"' 'input_overlay_enable = "false"'
        # 21 = square pixel aspect in RetroArch 1.22; preserve dynamic geometry.
        printf '%s\\n' 'aspect_ratio_index = "21"' 'video_viewport_bias_x = "0.500000"' 'video_viewport_bias_y = "0.500000"'
    } > "$BCFG"
    BA="|$BCFG"
fi
'''+s[end:]
s=s.replace('$RA$BA$RBA','$RA$RBA$BA')
p.write_text(s)
# DS integer shader includes matching touchscreen mapping.
readmode=r'''az_native_integer() {
    for f in /data/banana/settings.conf /etc/banana/settings.conf; do
        v=$(sed -n '/^ *azeez_native_integer *= */{s///;h};${x;p}' "$f" 2>/dev/null)
        case "$v" in on) return 0 ;; off) return 1 ;; esac
    done
    return 1
}
'''
replace(ds,'# the 3D always through the Gengis Engine',
    readmode+'''if az_native_integer; then
    export DSFLIP_SHADER=ds-integer DSFLIP_SHADER_DIR=/usr/lib/superdrastic/shaders
fi
# the 3D always through the Gengis Engine''')
replace(bd,'cd $D\nexec /usr/bin/bananads "$ROM"',
    readmode+'''az_ds_setting() {
    for f in /data/banana/settings.conf /etc/banana/settings.conf; do
        v=$(awk -v k="$1" '$0 ~ ("^ *" k " *= *") {sub(/^[^=]*= */,""); v=$0} END {print v}' "$f" 2>/dev/null)
        if [ -n "$v" ]; then printf '%s' "$v"; return; fi
    done
}
# DS exact presentation is independent of legacy fast-mode settings.
# Never override render.scale or render.texfilter: environment/per-game
# overrides and bananads.conf remain the authoritative renderer controls.
if az_native_integer || [ "$(az_ds_setting azeez_ds_integer)" != off ]; then
    export AZEEZ_EXPANDED_VIEWPORT=1 BANANADS_KMS_SHADER=none
    if [ "$(az_ds_setting azeez_ds_wide3d)" != off ]; then
        export AZEEZ_DS_WIDE3D=1 MELONDS_GEOMREJECT=0 BANANADS_RENDER_GEOM_REJECT=off
    fi
fi
cd $D
exec /usr/bin/bananads "$ROM"''')
p=root/"etc/banana/settings.conf"
s=p.read_text()
if "azeez_native_integer =" not in s:
    p.write_text(s+"\n# Native integer presentation (opt-in)\nazeez_native_integer = off\n")
# Migrate the default DS emulator once; explicit per-game choices survive.
p=root/"etc/banana/settings.conf"
s=p.read_text().replace("nds_emulator = superdrastic","nds_emulator = bananads")
if "azeez_ds_wide3d =" not in s:
    s+="\nazeez_ds_wide3d = on\n"
if "azeez_ds_integer =" not in s:
    s+="\nazeez_ds_integer = on\n"
p.write_text(s)
p=root/(base+"run-nds")
s=p.read_text()
if "# AzeezOS melonDS transition" not in s:
    anchor="want=$(awk"
    assert s.count(anchor)==1
    s=s.replace(anchor,'''# AzeezOS melonDS transition
M=/data/banana/.azeez-melonds-default
C=/data/banana/settings.conf
if [ ! -e "$M" ]; then
    mkdir -p /data/banana
    if [ -f "$C" ]; then
        sed -i 's/^ *nds_emulator *= *.*/nds_emulator = bananads/' "$C"
    fi
    touch "$M"
fi
'''+anchor,1)
    s=s.replace("*) want=superdrastic ;;","*) want=bananads ;;")
    p.write_text(s)
subprocess.run(["sh","-n",str(p)],check=True)
for f in (ra,bf,ds,bd):
    subprocess.run(["sh","-n",str(root/f)],check=True)
print("Native integer presentation installed for RetroArch, BananaFront, SuperDrastic, BananaDS")
