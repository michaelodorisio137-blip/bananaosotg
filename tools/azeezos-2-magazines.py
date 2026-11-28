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
if "[magazines]" not in s: conf.write_text(s.rstrip()+"\n\n"+section.strip()+"\n")
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
Selecting a guide opens the native reader. Play game launches its associated ROM. Supported single-screen games
using the top-screen RetroArch/BananaFront game panel display the pages below.
Touch Previous/Next to change page; save/load/menu/quit use existing commands.
Original magazine files are not included. Use tools/magazine-import.py on a computer to import PDFs/CBZs and optional page-to-ROM links. Automatic matching is not guaranteed.
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
struct Guide { std::string rom; std::vector<std::string> pages; std::vector<std::string> links; };
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
    if((!g.rom.empty() && g.rom[0]!='/') || g.rom.find('\0')!=std::string::npos) return {};
    std::string dir=manifest.substr(0,manifest.find_last_of('/')+1), p;
    while(g.pages.size()<2048 && std::getline(f,p)) {
        if(!p.empty() && p.back()=='\r') p.pop_back();
        std::string link;
        auto tab=p.find('\t');
        if(tab!=std::string::npos) { link=p.substr(tab+1);p.resize(tab);if(link.empty() || link[0]!='/' || link.find('\0')!=std::string::npos) link.clear(); }
        if(p.empty() || p[0]=='/' || p.find("..")!=std::string::npos || p.find('\\')!=std::string::npos || p.find('\0')!=std::string::npos) continue;
        auto dot=p.find_last_of('.');
        if(dot==std::string::npos) continue;
        std::string ext=p.substr(dot);
        std::transform(ext.begin(),ext.end(),ext.begin(),[](unsigned char c){return char(std::tolower(c));});
        if(ext==".png" || ext==".jpg" || ext==".jpeg") { g.pages.push_back(dir+p);g.links.push_back(link); }
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

# Reader uses the existing native Settings view; no separate app or process.
sub("settings.h","ACHIEVEMENTS } page = LIST;","ACHIEVEMENTS, MAGAZINE } page = LIST;")
sub("settings.h","void magazineOpen(const std::string& manifest);",'''void magazineOpen(const std::string& manifest);
        void openMagazine(const std::string& manifest);
        void magazineDraw(int screen, bool playing);
        void magazineStep(int step);
        std::string magazineManifest, magazineDefaultRom, magazineRequest, magazineRequestRom;
        std::vector<std::string> magazineLinks;
        int magazineZoom=1, magazinePanX=0, magazinePanY=0;
        bool magazineTakeLaunch(std::string& path, std::string& rom) {
            if(magazineRequest.empty()) return false;
            path=magazineRequest;rom=magazineRequestRom;magazineRequest.clear();magazineRequestRom.clear();return true;
        }
        std::string magazineBookmark() const;
        void magazineRemember();''')
sub("settings.h","Result press(Key k);","Result press(Key k);\n        Result magazinePress(Key k);\n        Result magazineTouch(float x, float y);")
sub("settings.cpp","Settings::Result Settings::press(Key k)\n\t{","Settings::Result Settings::press(Key k)\n\t{\n        if(page==MAGAZINE) return magazinePress(k);")
sub("settings.cpp","if (!downOnRow) return NONE;\n\t\tdownOnRow = false;","if (!downOnRow) return NONE;\n\t\tdownOnRow = false;\n        if(page==MAGAZINE) return magazineTouch(cx,cy);")
sub("settings.cpp","void Settings::renderPage()\n\t{",'''void Settings::renderPage()
    {
        if(page==MAGAZINE) {
            SPal p=pal(light);
            be->beginScreen(0);box("screen",false,0,0,640,480);
            text("Magazines",true,28,24,20,p.accent);
            text(fit(magazineManifest.substr(magazineManifest.find_last_of('/')+1),true,22,592),true,22,24,76,p.ink);
            wrapped("Read Nintendo Power and Player's Guides. Use L/R or Previous/Next for pages. Tap a quadrant to inspect it at 2x. A launches the linked game; B returns.",20,24,135,592,6,p.ink);
            std::string link=magazinePage<magazineLinks.size()&&!magazineLinks[magazinePage].empty()?magazineLinks[magazinePage]:magazineDefaultRom;
            text(link.empty()?"No game linked on this page":fit("Game: "+link.substr(link.find_last_of('/')+1),true,18,592),true,18,24,350,p.accent);
            be->endScreen();
            magazineDraw(1,false);return;
        }''')
sub("settings_gamepanel.cpp","magazinePages=azmag::read(manifest).pages;\n        magazinePage=0; magazineTexture.reset(); magazineLoaded=false;",'''auto guide=azmag::read(manifest);
        magazineManifest=manifest; magazineDefaultRom=guide.rom;
        magazinePages=std::move(guide.pages);magazineLinks=std::move(guide.links);
        magazinePage=0; magazineTexture.reset(); magazineLoaded=false;
        magazineZoom=1;magazinePanX=magazinePanY=0;
        if(!magazinePages.empty()) {
            size_t at=0;std::ifstream f(magazineBookmark());
            if(f>>at && at<magazinePages.size()) magazinePage=at;
        }''')
# Move page drawing out of the game panel so it also serves the native reader.
p=ui/"settings_gamepanel.cpp";s=p.read_text()
start=s.index("        if(!magazinePages.empty()) {\n            if(!magazineLoaded)")
end=s.index("\n        }",s.index("be->endScreen();return;",start))+len("\n        }")
s=s[:start]+'''        if(!magazinePages.empty()) { be->endScreen();magazineDraw(gScreen,true);return; }'''+s[end:]
p.write_text(s)
sub("settings_gamepanel.cpp","void Settings::gameClose()",r'''std::string Settings::magazineBookmark() const {
        unsigned long long h=14695981039346656037ull;
        for(unsigned char c:magazineManifest) { h^=c;h*=1099511628211ull; }
        return data+"/magazine-"+std::to_string(h)+".page";
    }
    void Settings::magazineRemember() {
        if(magazineManifest.empty() || magazinePages.empty()) return;
        std::string path=magazineBookmark();
        std::ofstream f(path+".new");f<<magazinePage<<"\n";f.close();
        if(f) rename((path+".new").c_str(),path.c_str());
    }
    void Settings::magazineStep(int step) {
        if(magazinePages.empty()) return;
        size_t n=magazinePage;
        if(step<0 && n>0) --n;
        if(step>0 && n+1<magazinePages.size()) ++n;
        if(n!=magazinePage) {
            magazinePage=n;magazineTexture.reset();magazineLoaded=false;
            magazineZoom=1;magazineRemember();
        }
    }
    void Settings::openMagazine(const std::string& manifest) {
        open();magazineOpen(manifest);page=MAGAZINE;
    }
    Settings::Result Settings::magazinePress(Key k) {
        if(k==Key::B) { magazineRemember();magazineTexture.reset();close();return CLOSED; }
        if(k==Key::L || k==Key::LEFT) magazineStep(-1);
        if(k==Key::R || k==Key::RIGHT) magazineStep(1);
        if(k==Key::X) magazineZoom=magazineZoom==1?2:1;
        if(k==Key::A) {
            std::string r=magazinePage<magazineLinks.size()?magazineLinks[magazinePage]:"";
            if(r.empty()) r=magazineDefaultRom;
            if(!r.empty()) {
                magazineRemember();magazineRequest=magazineManifest;magazineRequestRom=r;
                magazineTexture.reset();close();return CLOSED;
            }
        }
        return MOVED;
    }
    Settings::Result Settings::magazineTouch(float x,float y) {
        if(y>=430) {
            if(x<160) return magazinePress(Key::L);
            if(x<320) return magazinePress(Key::R);
            if(x<480) return magazinePress(Key::A);
            return magazinePress(Key::B);
        }
        if(y>24) {
            magazineZoom=magazineZoom==1?2:1;
            magazinePanX=x>=320;magazinePanY=y>=224;
        }
        return MOVED;
    }
    void Settings::magazineDraw(int screen,bool playing) {
        SPal p=pal(light);
        be->beginScreen(screen);box("screen",false,0,0,640,480);
        if(!magazinePages.empty() && !magazineLoaded) {
            magazineLoaded=true;const auto& path=magazinePages[magazinePage];
            if(azmag::regular(path,16*1024*1024)) {
                auto b=rnds::decodeFile(path);if(!b.empty()) magazineTexture=be->upload(b,true);
            }
        }
        if(magazineTexture && magazineTexture->w>0 && magazineTexture->h>0) {
            float k=magazineZoom*std::min(640.f/magazineTexture->w,400.f/magazineTexture->h);
            float w=magazineTexture->w*k,h=magazineTexture->h*k;
            float x=w<=640?(640-w)/2:(magazinePanX?640-w:0);
            float y=h<=400?24+(400-h)/2:24+(magazinePanY?400-h:0);
            be->draw(magazineTexture,X(x),X(y),X(w),X(h),Color(1,1,1,1));
        } else text("Guide page unavailable",true,22,24,190,p.ink);
        box("screen",false,0,0,640,24);box("screen",false,0,424,640,56);
        text("Magazines  |  Page "+std::to_string(magazinePages.empty()?0:magazinePage+1)+" / "+std::to_string(magazinePages.size()),true,16,12,3,p.accent);
        const char* play[]={"Previous","Next","Save","Load","Menu","Quit"};
        const char* read[]={"Previous","Next","Play game","Back"};
        int n=playing?6:4;float step=640.f/n;
        for(int i=0;i<n;i++){box("slot",false,3+i*step,430,step-6,45);text(playing?play[i]:read[i],true,15,10+i*step,443,p.ink);}
        be->endScreen();
    }
    void Settings::gameClose()''')
sub("settings_gamepanel.cpp","if (down || ly<430 || ly>=480 || lx<0 || lx>=640) return G_NONE;",'''if(down || ly>=480 || lx<0 || lx>=640) return G_NONE;
            if(ly<430) {
                if(ly>24) {magazineZoom=magazineZoom==1?2:1;magazinePanX=lx>=320;magazinePanY=ly>=224;}
                return G_NONE;
            }''')
sub("settings_gamepanel.cpp","if(action==0 && magazinePage>0) { --magazinePage; magazineTexture.reset(); magazineLoaded=false; }\n            if(action==1 && magazinePage+1<magazinePages.size()) { ++magazinePage; magazineTexture.reset(); magazineLoaded=false; }","if(action==0) magazineStep(-1);\n            if(action==1) magazineStep(1);")
# Reader opens first. Launch requests are consumed by the main loop using the same path validator.
p=ui/"main.cpp";s=p.read_text()
start=s.index('            if(lib.systemOf(g).id=="magazines") {')
end=s.index('\n            std::string page = internalPage',start)
s=s[:start]+'''            if(lib.systemOf(g).id=="magazines") {
                std::lock_guard<std::mutex> l(worker.uiLock);
                settingsView.openMagazine(lib.gameAt(g).path);dirty=true;rep.key=Key::NONE;
                continue;
            }'''+s[end:]
p.write_text(s)
sub("main.cpp","int g = lib.pendingLaunch();\n\t\tif (g >= 0)",'''std::string magPath,magRom;
        if(settingsView.magazineTakeLaunch(magPath,magRom)) {
            bool found=false;
            for(int si=0;si<lib.systemCount()&&!found;++si) {
                const auto& shelf=lib.shelf(si);
                if(shelf.favorites || shelf.def.id=="magazines" || shelf.def.id=="nds") continue;
                const auto& r=shelf.def.run;
                if(r.find("run-retroarch")==std::string::npos && r.find("run-bananafront")==std::string::npos && r.find("run-ps1")==std::string::npos) continue;
                for(const auto& entry:shelf.games) if(entry.path==magRom) {found=true;break;}
            }
            if(found && settings["retroarch_panel"]!="off" &&
               getConfValue("/data/retroarch/retroarch.cfg","video_monitor_index","2")!="1" &&
               launchPath(lib,magRom)) {magazinePending=magPath;magazineRom=magRom;}
            else {
                logf("Magazines: unavailable ROM or panel: %s",magRom.c_str());
                settingsView.openMagazine(magPath);dirty=true;
            }
        }
        int g = lib.pendingLaunch();
        if (g >= 0)''')

print("PASS: native Magazines reader and local game-linked guide companion")
