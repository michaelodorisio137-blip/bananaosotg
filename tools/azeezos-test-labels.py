#!/usr/bin/env python3
"""Visible test names for packaged builds and DS-style selectable title-bar palettes."""
from pathlib import Path
import json, sys
repo=Path(__file__).resolve().parent.parent
mode=sys.argv[1]; root=Path(sys.argv[2])
labels={
 "mgba":"T1mgba", "mgba_integer":"T1mgba Integer", "mgba_expanded":"T1mgba Expanded",
 "mgba_gles_preview":"T1mgba HD", "gpsp":"T1gpSP","bananagba":"T1BananaGBA",
 "gambatte":"T1Gambatte","fceumm":"T1FCEUmm","banananes":"T1BananaNES",
 "bananasnes":"T1BananaSNES","snes9x":"T1Snes9x","bsnes_hd_beta":"T1bsnes HD",
 "picodrive":"T1PicoDrive","genesis_plus_gx_wide":"T1Genesis GX Wide",
 "pcsx_rearmed":"T1PCSX ReARMed","mupen64plus_next":"T1Mupen64Plus",
 "mednafen_vb":"T1Beetle VB","vboycolor":"T1VBoy Color",
 "mednafen_pce_fast":"T1PCE Fast","mednafen_ngp":"T1NGP",
 "yabasanshiro":"T1YabaSanshiro","ppsspp_azeez":"T1PPSSPP",
 "vice_x64sc":"T1VICE","fuse":"T1Fuse","fake08":"T1fake08"}
if mode=="--ui":
    p=root/"ui/src/settings.cpp";s=p.read_text()
    a="names.push_back(c.second); values.push_back(c.first);"
    if s.count(a)!=1: raise SystemExit("Test label anchor mismatch")
    s=s.replace(a,'''std::string label = getConfValue("/usr/share/banana/emulator-tests.conf", c.first, "");
                if (access(("/data/retroarch/cores/" + std::string(c.first) + "_libretro.so").c_str(), F_OK) == 0) label.clear();
                names.push_back(label.empty() ? c.second : label); values.push_back(c.first);''')
    s=s.replace('"melonDS (Azeez Enhanced)"','"T1melonDS"')
    p.write_text(s)
    root=root/"system/rootfs"
elif mode!="--rootfs": raise SystemExit("Use --ui or --rootfs")
themes=root/"usr/share/banana/themes"; themes.mkdir(parents=True,exist_ok=True)
source=json.loads((repo/"rgds-ds-classic.json").read_text())
# Original DS favourite-colour RGB555 values, indexed 0..15. Title bar
# tints derive from these base colours; not a claim of bit-identical IPL gradients.
palette=[("Gray",12,16,19),("Brown",23,9,0),("Red",31,0,3),("Pink",31,17,31),
 ("Orange",31,18,0),("Yellow",30,28,0),("Lime Green",21,31,0),("Green",0,31,0),
 ("Dark Green",0,20,7),("Sea Green",9,27,17),("Turquoise",6,23,30),("Blue",0,11,30),
 ("Dark Blue",0,0,18),("Dark Purple",17,0,26),("Violet",26,0,29),("Magenta",31,0,18)]
def rgb(c): return "#"+"".join(f"{v:02x}" for v in c)
def tint(c,w): return rgb([round(v*(1-w)+255*w) for v in c])
def recolor(x, mapping):
    if isinstance(x,str):
        for a,b in mapping.items(): x=x.replace(a,b)
        return x
    if isinstance(x,list): return [recolor(v,mapping) for v in x]
    if isinstance(x,dict): return {k:recolor(v,mapping) for k,v in x.items()}
    return x
for n,(name,r,g,b) in enumerate(palette):
    c=[round(v*255/31) for v in (r,g,b)]
    mapping={"#bcd9ed":tint(c,.50),"#87aac9":rgb(c),"#cae0f2":tint(c,.65),"#598fc1":rgb(c),
             "#a8cae8":tint(c,.55),"inter-semibold":"pixel","inter-bold":"pixel","inter-medium":"pixel","inter":"pixel"}
    t=recolor(source,mapping);t["name"]="DS Classic - "+name
    # Keep the original artwork/layout; only title bars, selection and plain type.
    (themes/f"rgds-ds-color-{n:02}.json").write_text(json.dumps(t,indent=2)+"\n")
# Replace existing default theme's Inter font with the installed pixel fallback.
# Exact original font asset is not bundled; users may install a licensed TTF as
# a custom theme font. Do not identify Pixelify Sans as Nintendo's own font.
t=recolor(source,{"inter-semibold":"pixel","inter-bold":"pixel","inter-medium":"pixel","inter":"pixel"})
(themes/"rgds-ds-classic.json").write_text(json.dumps(t,indent=2)+"\n")
if mode=="--rootfs":
    # Only label cores explicitly supplied by this OTA's build, not inherited binaries.
    active=sys.argv[3:]
    for k in active:
        if k not in labels: raise SystemExit("Unknown label: "+k)
        if not (root/"usr/lib/libretro"/(k+"_libretro.so")).is_file(): raise SystemExit("Missing rebuilt core: "+k)
    f=root/"usr/share/banana/emulator-tests.conf"
    f.write_text("".join(f"{k} = {labels[k]}\n" for k in active))
print("DS palette variants installed; test labels prepared")
