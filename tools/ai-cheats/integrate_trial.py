#!/usr/bin/env python3
"""Integrate one-shot memory trials and the confirmed catalog after integrate.py."""
from pathlib import Path
import shutil,sys
ui=Path(sys.argv[1])/"ui/src"
for name in ("trial.h","catalog.h","cheat_panel.h"):
    shutil.copyfile(Path(__file__).parent/name,ui/name)
def sub(p,a,b):
    p=ui/p;s=p.read_text()
    if s.count(a)!=1:raise SystemExit(f"trial anchor mismatch {p}: {a[:100]!r} ({s.count(a)})")
    p.write_text(s.replace(a,b))
sub("settings.h","gAiJob, gLiveScan;","gAiJob, gLiveScan, gCheatPanel;")
sub("settings_gamepanel.cpp",'#include "live_scan.h"','#include "live_scan.h"\n#include "cheat_panel.h"')
sub("settings_gamepanel.cpp","gLiveScan.reset(); gScanOpen=false;\n        if(!enabled)","gLiveScan.reset(); gCheatPanel.reset(); gScanOpen=false;\n        if(!enabled)")
sub("settings_gamepanel.cpp",'else if(gSysId=="gb"||gSysId=="gbc") gLiveScan=std::make_shared<azeez::LiveScan>(0xc000,0x2000);','''else if(gSysId=="gb"||gSysId=="gbc") gLiveScan=std::make_shared<azeez::LiveScan>(0xc000,0x2000);
        if(gLiveScan) gCheatPanel=std::make_shared<azeez::CheatPanel>(data,gSysId=="gba"?0x03000000:0xc000,gSysId=="gba"?0x8000:0x2000);''')
sub("settings_gamepanel.cpp",'return gLiveScan?std::static_pointer_cast<azeez::LiveScan>(gLiveScan)->request(t):"";','''if(gCheatPanel) {
            auto c=std::static_pointer_cast<azeez::CheatPanel>(gCheatPanel);
            if(c->active()) return c->request(t);
        }
        return gLiveScan?std::static_pointer_cast<azeez::LiveScan>(gLiveScan)->request(t):"";''')
sub("settings_gamepanel.cpp","if(gLiveScan) std::static_pointer_cast<azeez::LiveScan>(gLiveScan)->feed(p,n);",'''if(gCheatPanel) {
            auto c=std::static_pointer_cast<azeez::CheatPanel>(gCheatPanel);
            if(c->active()) { c->trial.feed(p,n); return; }
        }
        if(gLiveScan) std::static_pointer_cast<azeez::LiveScan>(gLiveScan)->feed(p,n);''')
sub("settings_gamepanel.cpp","gLiveScan.reset(); gScanOpen=false;\n","gLiveScan.reset(); gCheatPanel.reset(); gScanOpen=false;\n")
sub("settings_gamepanel.cpp","bool changed = gLiveScan && std::static_pointer_cast<azeez::LiveScan>(gLiveScan)->changed();",'''bool changed = gLiveScan && std::static_pointer_cast<azeez::LiveScan>(gLiveScan)->changed();
        if(gScanOpen && gCheatPanel) {
            auto c=std::static_pointer_cast<azeez::CheatPanel>(gCheatPanel);
            auto note=c->status();
            if(note!=gAiStatus){gAiStatus=note;changed=true;wake=true;}
        }''')
sub("settings_gamepanel.cpp","if(ly>=425) { if(lx<160) gScanOpen=false;",'''auto c=std::static_pointer_cast<azeez::CheatPanel>(gCheatPanel);
            if(c && c->active()) {
                if(ly>=425 && lx<320 && c->trial.state()==azeez::Trial::AwaitUser) c->confirm();
                else if(ly>=425 && lx>=320) c->trial.undo();
                return G_NONE;
            }
            if(c && !scan->busy()){
                if(ly<68 && lx>=400){c->savedView=!c->savedView;c->selection=0;return G_NONE;}
                if(ly>=180 && ly<335){c->selection=unsigned((ly-180)/31);return G_NONE;}
                if(ly>=335 && ly<365){
                    if(lx<160)c->value=c->value?c->value-1:0;
                    else if(lx<320)c->value=std::min(255u,c->value+1);
                    else if(lx<480)c->value=255;
                    else c->value=99;
                    return G_NONE;
                }
                if(ly>=365&&ly<420&&lx>=480){
                    if(c->savedView){auto rows=c->catalog().load();if(c->selection<rows.size())c->begin(rows[c->selection].address,rows[c->selection].value);}
                    else {auto rows=scan->results(5);if(c->selection<rows.size())c->begin(uint32_t(rows[c->selection].address),c->value);}
                    return G_NONE;
                }
                if(c->savedView){
                    if(ly>=425&&lx<160)gScanOpen=false;
                    else if(ly>=365&&ly<420&&lx<160){auto rows=c->catalog().load();if(c->selection<rows.size())c->catalog().erase(rows[c->selection].address);}
                    else if(ly>=365&&ly<420&&lx<320)c->selection=c->selection>=5?c->selection-5:0;
                    else if(ly>=365&&ly<420&&lx<480){auto rows=c->catalog().load();if(c->selection+5<rows.size())c->selection+=5;}
                    return G_NONE;
                }
            }
            if(ly>=425) { if(lx<160) gScanOpen=false;''')
# Saved rows are paged in groups of five; use page-relative touch selection.
sub("settings_gamepanel.cpp","c->selection=unsigned((ly-180)/31);","c->selection=(c->savedView?(c->selection/5)*5:0)+unsigned((ly-180)/31);")
sub("settings_gamepanel.cpp",'text(gSysId=="gba"?"GBA IWRAM":"GB WRAM",true,18,430,30,p.ink);','''auto c=std::static_pointer_cast<azeez::CheatPanel>(gCheatPanel);
            box("slot",false,405,17,215,46);
            text(c&&c->savedView?"Back to scan":"Saved cheats",true,18,420,30,p.accent);
            if(c&&c->active()){
                wrapped(c->status(),22,24,100,590,4,p.ink);
                char line[100];snprintf(line,sizeof line,"Address %08X   value %u",c->trial.address(),c->trial.value());
                text(line,true,20,30,235,p.ink);
                box("slot",false,18,425,298,48);box("slot",false,324,425,298,48);
                text(c->trial.state()==azeez::Trial::AwaitUser?"Confirm & save":"Wait / verify",true,19,35,438,p.ink);
                text("Undo",true,19,342,438,p.ink);
                be->endScreen();return;
            }''')
sub("settings_gamepanel.cpp",'wrapped(scan->status,18,24,82,590,3,p.ink);\n            text("8-bit candidates (read-only)",true,18,24,150,p.muted);','''wrapped(c&&(c->trial.state()!=azeez::Trial::Idle||!c->note.empty())?c->status():scan->status,18,24,82,590,3,p.ink);
            text(c&&c->savedView?"Confirmed one-shot cheats":"8-bit candidates - offline test",true,18,24,150,p.muted);''')
sub("settings_gamepanel.cpp",'''for(auto c:scan->results(5)) {
                char line[80]; snprintf(line,sizeof line,"%08llX   value %u",(unsigned long long)c.address,c.value);
                text(line,true,20,30,y,p.ink); y+=31;
            }''','''if(c&&c->savedView){
                auto rows=c->catalog().load();
                for(size_t i=(c->selection/5)*5;i<rows.size()&&i<(c->selection/5)*5+5;++i){
                    char line[80];snprintf(line,sizeof line,"%08X   value %u",rows[i].address,rows[i].value);
                    if(i==c->selection)box("slot",true,18,y-4,604,30);
                    text(line,true,20,30,y,i==c->selection?p.onPick:p.ink);y+=31;
                }
            }else{
                unsigned i=0;
                for(auto row:scan->results(5)){
                    char line[80];snprintf(line,sizeof line,"%08llX   value %u",(unsigned long long)row.address,row.value);
                    if(c&&i==c->selection)box("slot",true,18,y-4,604,30);
                    text(line,true,20,30,y,c&&i==c->selection?p.onPick:p.ink);y+=31;++i;
                }
            }
            if(c&&!c->savedView){
                std::string v="-    Value "+std::to_string(c->value)+"    +       255       99";
                text(v,true,18,22,338,p.ink);
            }''')
sub("settings_gamepanel.cpp",'''box("slot",false,18,365,298,48);box("slot",false,324,365,298,48);
            text("Decreased",true,19,35,378,p.ink);text("Increased",true,19,342,378,p.ink);
            const char* labs[]={"Back","Baseline","Changed","Same"};''','''const char* scanLabs[]={"Decreased","Increased","Test"};
            const char* saveLabs[]={"Delete","Previous","Next","Apply"};
            if(c&&c->savedView){
                for(int i=0;i<4;++i){box("slot",false,8+i*160,365,150,48);text(saveLabs[i],true,18,18+i*160,378,p.ink);}
            }else{
                box("slot",false,8,365,310,48);box("slot",false,324,365,150,48);box("slot",false,484,365,148,48);
                text(scanLabs[0],true,19,35,378,p.ink);text(scanLabs[1],true,19,335,378,p.ink);text(scanLabs[2],true,19,500,378,p.ink);
            }
            const char* labs[]={"Back",c&&c->savedView?"":"Baseline",c&&c->savedView?"":"Changed",c&&c->savedView?"":"Same"};''')
# Clear stale identity before starting any new game; never send trial writes through read-only CompLink.
sub("main.cpp","gameRomPath = rom;","unlink(\"/run/banana/azeez-cheat-session\");\n        gameRomPath = rom;")
sub("main.cpp","if(!q.empty() && !compLink.send(q)) pipeWrite(cmdFd,q.data(),q.size());",'''if(!q.empty()){
                    if(q.rfind("WRITE_CORE_MEMORY ",0)==0) {
                        if(!compLink.attached())pipeWrite(cmdFd,q.data(),q.size());
                    }else if(!compLink.send(q))pipeWrite(cmdFd,q.data(),q.size());
                }''')
print("PASS: one-shot cheat trials and confirmed catalog wired into game panel")
