#!/usr/bin/env python3
"""Connect bounded, read-only live memory search to the native game panel."""
from pathlib import Path
import shutil,sys
ui=Path(sys.argv[1])/"ui/src"
for name in ("ram_scan.h","live_scan.h"):
    shutil.copyfile(Path(__file__).with_name("ai-cheats")/name,ui/name)
def sub(p,a,b):
    p=ui/p;s=p.read_text()
    if s.count(a)!=1:raise SystemExit(f"live scan anchor mismatch {p}: {a[:90]!r} ({s.count(a)})")
    p.write_text(s.replace(a,b))
sub("settings.h","bool gameKeysOpen() const",'''void gameScanEnable(bool enabled);
        std::string gameScanRequest(double now);
        void gameScanFeed(const char* p,size_t n);
        bool gameKeysOpen() const''')
sub("settings.h","std::shared_ptr<void> gAiJob;",'''std::shared_ptr<void> gAiJob, gLiveScan;
        bool gScanOpen=false;''')
sub("settings_gamepanel.cpp",'#include "azeezos_ai_cheats.h"','#include "azeezos_ai_cheats.h"\n#include "live_scan.h"')
sub("settings_gamepanel.cpp","void Settings::gameRom(",'''void Settings::gameScanEnable(bool enabled) {
        gLiveScan.reset(); gScanOpen=false;
        if(!enabled) return;
        if(gSysId=="gba") gLiveScan=std::make_shared<azeez::LiveScan>(0x03000000,0x8000);
        else if(gSysId=="gb"||gSysId=="gbc") gLiveScan=std::make_shared<azeez::LiveScan>(0xc000,0x2000);
    }
    std::string Settings::gameScanRequest(double t) {
        return gLiveScan?std::static_pointer_cast<azeez::LiveScan>(gLiveScan)->request(t):"";
    }
    void Settings::gameScanFeed(const char* p,size_t n) {
        if(gLiveScan) std::static_pointer_cast<azeez::LiveScan>(gLiveScan)->feed(p,n);
    }

    void Settings::gameRom(''')
sub("settings_gamepanel.cpp","gAiJob.reset(); gAiPanel = gAiPending = false;","gAiJob.reset(); gAiPanel = gAiPending = false; gLiveScan.reset(); gScanOpen=false;")
sub("settings_gamepanel.cpp","bool changed = false;\n        if (gAiPending","bool changed = gLiveScan && std::static_pointer_cast<azeez::LiveScan>(gLiveScan)->changed();\n        if (gAiPending")
sub("settings_gamepanel.cpp","if (gAiPanel && !gKeysOpen) {",'''if(gScanOpen && gLiveScan) {
            if(down) return G_NONE;
            auto scan=std::static_pointer_cast<azeez::LiveScan>(gLiveScan);
            if(ly>=425) { if(lx<160) gScanOpen=false;
                else if(lx<320) scan->start(true,azeez::Filter::Changed);
                else if(lx<480) scan->start(false,azeez::Filter::Changed);
                else scan->start(false,azeez::Filter::Unchanged);
            } else if(ly>=365 && ly<420) {
                scan->start(false,lx<320?azeez::Filter::Decreased:azeez::Filter::Increased);
            }
            return G_NONE;
        }
        if (gAiPanel && !gKeysOpen) {
            if(!down && ly<68 && lx>=470 && gLiveScan) {gScanOpen=true; return G_NONE;}''')
sub("settings_gamepanel.cpp",'if(gAiPanel) {\n            box("bubble"', '''if(gScanOpen && gLiveScan) {
            auto scan=std::static_pointer_cast<azeez::LiveScan>(gLiveScan);
            box("bubble",false,18,14,604,54);
            text("Live RAM search",true,24,30,25,p.accent);
            text(gSysId=="gba"?"GBA IWRAM":"GB WRAM",true,18,430,30,p.ink);
            wrapped(scan->status,18,24,82,590,3,p.ink);
            text("8-bit candidates (read-only)",true,18,24,150,p.muted);
            int y=184;
            for(auto c:scan->results(5)) {
                char line[80]; snprintf(line,sizeof line,"%08llX   value %u",(unsigned long long)c.address,c.value);
                text(line,true,20,30,y,p.ink); y+=31;
            }
            box("slot",false,18,365,298,48);box("slot",false,324,365,298,48);
            text("Decreased",true,19,35,378,p.ink);text("Increased",true,19,342,378,p.ink);
            const char* labs[]={"Back","Baseline","Changed","Same"};
            for(int i=0;i<4;i++){box("slot",false,8+i*160,425,150,48);text(labs[i],true,18,20+i*160,440,p.ink);}
            be->endScreen();return;
        }
        if(gAiPanel) {
            box("bubble"''')
sub("settings_gamepanel.cpp",'text(fit(gTitle,true,18,350),true,18,230,30,p.ink);','''text(fit(gTitle,true,18,gLiveScan?225:350),true,18,220,30,p.ink);
            if(gLiveScan) { box("slot",false,475,17,145,46);text("Live scan",true,18,488,30,p.accent); }''')
# No companion and live scan can use the same stdout pipe simultaneously.
sub("main.cpp","settingsView.gameOpen(title, sysName, panelScreen, input.hasTouch(panelScreen));",'''settingsView.gameOpen(title, sysName, panelScreen, input.hasTouch(panelScreen));
            settingsView.gameScanEnable(outFd>=0 && !companion.active() && !gameComp.active());''')
sub("main.cpp","if (outFd >= 0)\n\t\t\t{\n\t\t\t\t// the companion's reads",'''if(outFd>=0 && !companion.active() && !gameComp.active()) {
                auto q=settingsView.gameScanRequest(t);
                if(!q.empty()) pipeWrite(cmdFd,q.data(),q.size());
            }
            if (outFd >= 0 && (companion.active() || gameComp.active()))
            {
                // the companion's reads''')
sub("main.cpp","if (companion.active()) companion.feed(buf, (size_t)n);\n\t\t\t\t\telse",'''if (companion.active()) companion.feed(buf, (size_t)n);
                    else if(!gameComp.active()) settingsView.gameScanFeed(buf,(size_t)n);
                    else''')
sub("main.cpp","if (pkOn || gcOn)\n\t\t{",'''if (pkOn || gcOn || (panel && (sd.id=="gba"||sd.id=="gb"||sd.id=="gbc")))
        {''')
sub("main.cpp",'else logf("game companion: %s (%s)", gameComp.game()->title.c_str(), gameComp.game()->file.c_str());','else if(gcOn) logf("game companion: %s (%s)", gameComp.game()->title.c_str(), gameComp.game()->file.c_str());')
print("PASS: live read-only memory search integrated into game panel")
