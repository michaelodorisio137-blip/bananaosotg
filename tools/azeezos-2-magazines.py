#!/usr/bin/env python3
"""Native Magazines shelf + explicit local game-guide page companion."""
from pathlib import Path
import sys
root=Path(sys.argv[-1])
fs=root if sys.argv[1]=="--rootfs" else root/"system/rootfs"
conf=fs/"etc/banana/systems.conf"
section="""
[magazines]
name = Magazines
maker = Nintendo Power / Player's Guides
folder = magazines
ext = guide
run = banana-guide
always = yes

"""
s=conf.read_text()
if "[magazines]" not in s: conf.write_text(s+"\n"+section)
doc=fs/"usr/share/banana/magazines/README.txt"
doc.parent.mkdir(parents=True,exist_ok=True)
doc.write_text("""AzeezOS Magazines preview
Put .guide files in your ROM root's magazines folder (also USB roms/magazines).
First line: exact absolute path of a game already in your library.
Following lines: relative JPG or PNG page filenames next to the .guide file,
one per line, in reading order. Example:
 /run/sd2/roms/snes/Super Metroid.sfc
 pages/001.jpg
 pages/002.jpg
Remove the example's leading spaces. Use a descriptive .guide filename or gamelist.xml.
Selecting a guide starts the associated game. Supported single-screen games
using the top-screen RetroArch/BananaFront game panel display the pages below.
Touch Previous/Next to change page; save/load/menu/quit use existing commands.
Original magazine files are not included. PDF/CBZ importing and automatic matching
are not implemented in this preview. Export your own pages to PNG/JPG first.
""")
if sys.argv[1]=="--rootfs": sys.exit(0)
ui=root/"ui/src"
def sub(name,a,b):
    p=ui/name;s=p.read_text()
    if s.count(a)!=1: raise SystemExit("Magazine anchor mismatch: "+name+" "+repr(a[:100]))
    p.write_text(s.replace(a,b,1))
(ui/"azeez_magazines.h").write_text(r'''#pragma once
#include <fstream>
#include <string>
#include <vector>
#include <algorithm>
#include <cctype>
#include <sys/stat.h>
namespace azmag {
struct Guide { std::string rom; std::vector<std::string> pages; };
inline bool regular(const std::string& p, long long max) {
    struct stat st;
    return stat(p.c_str(), &st)==0 && S_ISREG(st.st_mode) && st.st_size>0 && st.st_size<=max;
}
inline Guide read(const std::string& manifest) {
    Guide g;
    if(!regular(manifest, 1024*1024)) return g;
    std::ifstream f(manifest);
    if(!std::getline(f,g.rom)) return {};
    if(!g.rom.empty() && g.rom.back()=='\r') g.rom.pop_back();
    if(g.rom.empty() || g.rom[0]!='/' || g.rom.find('\0')!=std::string::npos) return {};
    std::string dir=manifest.substr(0,manifest.find_last_of('/')+1), p;
    while(g.pages.size()<2048 && std::getline(f,p)) {
        if(!p.empty() && p.back()=='\r') p.pop_back();
        if(p.empty() || p[0]=='/' || p.find("..")!=std::string::npos ||
           p.find('\\')!=std::string::npos || p.find('\0')!=std::string::npos) continue;
        auto dot=p.find_last_of('.');
        if(dot==std::string::npos) continue;
        std::string ext=p.substr(dot);
        std::transform(ext.begin(),ext.end(),ext.begin(),[](unsigned char c){return char(std::tolower(c));});
        if(ext==".png" || ext==".jpg" || ext==".jpeg") g.pages.push_back(dir+p);
    }
    if(g.pages.empty()) return {};
    return g;
}
}
''')
for name in ("main.cpp","settings_gamepanel.cpp"):
    sub(name,'#include "settings.h"','#include "settings.h"\n#include "azeez_magazines.h"')
sub("settings.h","void gameClose();",'''void gameClose();
        void magazineOpen(const std::string& manifest);
        std::vector<std::string> magazinePages;
        size_t magazinePage = 0;
        rnds::TexPtr magazineTexture;
        bool magazineLoaded = false;''')
sub("settings_gamepanel.cpp","void Settings::gameClose()",'''void Settings::magazineOpen(const std::string& manifest)
    {
        magazinePages=azmag::read(manifest).pages;
        magazinePage=0; magazineTexture.reset(); magazineLoaded=false;
    }

    void Settings::gameClose()''')
sub("settings_gamepanel.cpp","gAchOpen = false; gAchCache = ach::List(); gRomPath.clear(); gSysId.clear();","magazinePages.clear(); magazineTexture.reset(); magazineLoaded=false;\n        gAchOpen = false; gAchCache = ach::List(); gRomPath.clear(); gSysId.clear();")
sub("settings_gamepanel.cpp","float lx = x / s, ly = y / s;",'''float lx = x / s, ly = y / s;
        if (!magazinePages.empty()) {
            if (down || ly<430 || ly>=480 || lx<0 || lx>=640) return G_NONE;
            int action=int(lx/106.667f);
            if(action==0 && magazinePage>0) { --magazinePage; magazineTexture.reset(); magazineLoaded=false; }
            if(action==1 && magazinePage+1<magazinePages.size()) { ++magazinePage; magazineTexture.reset(); magazineLoaded=false; }
            if(action==2) return G_SAVE;
            if(action==3) return G_LOAD;
            if(action==4) return G_MENU;
            if(action==5) return G_QUIT;
            return G_NONE;
        }''')
sub("settings_gamepanel.cpp",'box("screen", false, 0, 0, 640, 480);','''box("screen", false, 0, 0, 640, 480);
        if(!magazinePages.empty()) {
            if(!magazineLoaded) {
                magazineLoaded=true;
                const auto& path=magazinePages[magazinePage];
                if(azmag::regular(path,16*1024*1024)) {
                    auto b=rnds::decodeFile(path);
                    if(!b.empty()) magazineTexture=be->upload(b,true);
                }
            }
            if(magazineTexture && magazineTexture->w>0 && magazineTexture->h>0) {
                float k=std::min(640.f/magazineTexture->w,400.f/magazineTexture->h);
                float w=magazineTexture->w*k,h=magazineTexture->h*k;
                be->draw(magazineTexture,X((640-w)/2),X(24+(400-h)/2),X(w),X(h),Color(1,1,1,1));
            } else text("Guide page unavailable",true,22,24,190,p.ink);
            text("Magazines  |  Page "+std::to_string(magazinePage+1)+" / "+std::to_string(magazinePages.size()),true,16,12,3,p.accent);
            const char* labels[]={"Previous","Next","Save","Load","Menu","Quit"};
            for(int i=0;i<6;i++) { box("slot",false,3+i*106.667f,430,100,45); text(labels[i],true,15,10+i*106.667f,443,p.ink); }
            be->endScreen();return;
        }''')
sub("main.cpp","std::string gameRomPath;","std::string magazinePending, magazineRom, magazineActive;\n\tstd::string gameRomPath;")
sub("main.cpp","gameRomPath = rom;",'''gameRomPath = rom;
        magazineActive = rom==magazineRom ? magazinePending : "";
        magazinePending.clear(); magazineRom.clear();''')
sub("main.cpp","settingsView.gbaAttach(gbaHost.get());",'''settingsView.gbaAttach(gbaHost.get());
            settingsView.magazineOpen(panelScreen==1 ? magazineActive : "");''')
sub("main.cpp","bottomIdle.tick(t);","if(magazineActive.empty() || panelScreen!=1) bottomIdle.tick(t);")
sub("main.cpp","lib.clearLaunch();\n\t\t\tstd::string page = internalPage(lib.systemOf(g));",'''lib.clearLaunch();
            if(lib.systemOf(g).id=="magazines") {
                std::string path=lib.gameAt(g).path;
                auto guide=azmag::read(path);
                bool found=false;
                if(!guide.rom.empty()) {
                    for(int si=0;si<lib.systemCount()&&!found;++si) {
                        const auto& shelf=lib.shelf(si);
                        if(shelf.favorites || shelf.def.id=="magazines" || shelf.def.id=="nds") continue;
                        const auto& r=shelf.def.run;
                        if(r.find("run-retroarch")==std::string::npos && r.find("run-bananafront")==std::string::npos && r.find("run-ps1")==std::string::npos) continue;
                        for(const auto& entry:shelf.games) if(entry.path==guide.rom) { found=true;break; }
                    }
                }
                if(found && settings["retroarch_panel"]!="off" &&
                   getConfValue("/data/retroarch/retroarch.cfg","video_monitor_index","2")!="1" &&
                   launchPath(lib,guide.rom)) {
                    magazinePending=path;magazineRom=guide.rom;
                } else {
                    logf("Magazines: missing game/pages or unsupported panel: %s",path.c_str());
                    std::lock_guard<std::mutex> l(worker.uiLock);
                    ui->setLibrary(lib.currentShelf(),g);
                    dirty=true;
                }
                continue;
            }
            std::string page = internalPage(lib.systemOf(g));''')
print("PASS: native Magazines shelf and local single-screen guide companion")
