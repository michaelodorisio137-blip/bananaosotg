#!/usr/bin/env python3
"""Label test revisions by actual packaged core identity; leave filenames and save paths unchanged."""
from pathlib import Path
import sys,re,json
root=Path(sys.argv[-1])
# Explicit version per core. Bump independently when the corresponding source is revised.
# The runtime manifest contains only cores actually rebuilt and installed in the OTA.
NAMES={
 "mgba":"T1mgba","mgba_integer":"T1mgba-integer","mgba_expanded":"T1mgba-expanded",
 "mgba_gles_preview":"T1mgba-hd","gpsp":"T1gpsp","bananagba":"T1bananagba",
 "gambatte":"T1gambatte","fceumm":"T1fceumm","banananes":"T1banananes",
 "snes9x":"T1snes9x","bananasnes":"T1bananasnes","bsnes_hd_beta":"T1bsnes-hd",
 "picodrive":"T1picodrive","genesis_plus_gx_wide":"T1genesis-gx-wide",
 "pcsx_rearmed":"T1pcsx","mupen64plus_next":"T1mupen64plus",
 "mednafen_vb":"T1beetle-vb","vboycolor":"T1vboycolor",
 "mednafen_pce_fast":"T1pce","mednafen_ngp":"T1ngp","yabasanshiro":"T1yabasanshiro",
 "ppsspp_azeez":"T1ppsspp","vice_x64sc":"T1vice","fuse":"T1fuse","fake08":"T1fake08",
 "bananads":"T1melonDS"}
if sys.argv[1]=="--rootfs":
    dest=root/"etc/banana/emulator-tests.conf"
    # Explicit install list prevents labeling inherited old binaries as new.
    ids=sys.argv[2:-1]
    if any(x not in NAMES for x in ids):raise SystemExit("Unknown test core ID")
    lines=[]
    for x in ids:
        binary=root/("usr/bin/bananads" if x=="bananads" else "usr/lib/libretro/"+x+"_libretro.so")
        if not binary.is_file() or binary.stat().st_size==0: raise SystemExit("Missing rebuilt core "+x)
        lines.append(x+" = "+NAMES[x])
    dest.write_text("\n".join(lines)+"\n")
    sys.exit(0)
p=root/"ui/src/settings.cpp"
s=p.read_text()
a='names.push_back(c.second); values.push_back(c.first);'
assert s.count(a)==1
s=s.replace(a,'''std::string test=getConfValue("/etc/banana/emulator-tests.conf", c.first, "");
                // Downloaded binaries override system binaries and must not inherit their test label.
                if(access((std::string("/data/retroarch/cores/")+c.first+"_libretro.so").c_str(),F_OK)==0) test.clear();
                names.push_back(test.empty()?c.second:test); values.push_back(c.first);''')
# Explicitly expose the GPU core when installed, even if the older table did not contain it.
if '"mgba_gles_preview"' not in s:
    a='{ "gba", "Game Boy Advance", {'
    assert s.count(a)==1
    s=s.replace(a,a+' { "mgba_gles_preview", "mGBA Hardware (GLES3 Preview)" },')
# Existing DS selector entries; keep internal names, only change their displayed names.
a='items.back().hints = { "DraStic: the fastest.'
i=s.find(a)
assert i>=0
s=s[:i]+'''{
            std::string test=getConfValue("/etc/banana/emulator-tests.conf","bananads","");
            if(!test.empty() && items.back().names.size()==2) items.back().names[1]=test;
        }
        '''+s[i:]
a='const std::string emuValue = pgEmu ?'
i=s.find(a)
assert i>=0
end=s.index(';',i)+1
s=s[:end]+'''
        std::string testDS=getConfValue("/etc/banana/emulator-tests.conf","bananads","");
        if(!testDS.empty() && (pgEmu==2 || (!pgEmu && global=="bananads")))
            emuValue=pgEmu?testDS:"As in Settings ("+testDS+")";
'''+s[end:]
s=s.replace('const std::string emuValue = pgEmu ?', 'std::string emuValue = pgEmu ?')
p.write_text(s)
print("PASS: runtime test labels in emulator Settings, installed binary identities preserved")
