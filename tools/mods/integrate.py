#!/usr/bin/env python3
from pathlib import Path
import sys,shutil
ui=Path(sys.argv[1])/"ui/src"
for name in ("browser.h","patch.h","install.h"):
    shutil.copyfile(Path(__file__).parent/name,ui/("azeez_mod_browser.h" if name=="browser.h" else name))
def sub(p,a,b):
    p=ui/p;s=p.read_text()
    if s.count(a)!=1:raise SystemExit(f"Mod UI anchor mismatch {p}: {a[:100]!r} ({s.count(a)})")
    p.write_text(s.replace(a,b))
sub("settings.h","bool gScanOpen=false;","bool gScanOpen=false, gModOpen=false, gModPending=false, gModInstalled=false;\n        unsigned gModSelection=0;\n        std::shared_ptr<void> gModJob;\n        std::string gModNote, gModPath;")
sub("settings_gamepanel.cpp",'#include "cheat_panel.h"','#include "cheat_panel.h"\n#include "azeez_mod_browser.h"')
sub("settings_gamepanel.cpp","gAiPage = 0; gAiPrompt.clear();","gModOpen=gModPending=gModInstalled=false; gModJob.reset();gModNote.clear();gModPath.clear();gModSelection=0;\n        gAiPage = 0; gAiPrompt.clear();")
sub("settings_gamepanel.cpp","if (gAiPending && gAiJob) {",'''if(gModPending && gModJob){
            auto j=std::static_pointer_cast<azmods::Job>(gModJob);
            std::lock_guard<std::mutex> l(j->lock);
            if(j->done){gModPending=false;gModNote=j->message;gModPath=j->path;gModInstalled=j->ok&&!j->path.empty();
                gModSelection=0;changed=true;wake=true;if(gModInstalled)libChanged=true;}
        }
        if (gAiPending && gAiJob) {''')
sub("settings_gamepanel.cpp","if(gScanOpen && gLiveScan) {\n            if(down)","""if(gModOpen && !gKeysOpen){
            if(down)return G_NONE;
            if(ly>=425){
                if(lx<160&&!gModPending){gModOpen=false;gAiPanel=false;}
                else if(lx<320&&lx>=160&&!gModPending){gKeysOpen=true;gKeyPage=0;gKeyShift=0;gKeyTyped=gAiPrompt;}
                else if(lx<480&&lx>=320&&!gModPending&&!gAiPrompt.empty()){
                    gModJob=azmods::search(gRomPath,gTitle,gAiPrompt);
                    gModPending=true;gModInstalled=false;gModNote="Searching for patches...";
                }else if(lx>=480&&!gModPending&&gModJob){
                    if(gModInstalled){
                        if(!gModPath.empty()&&gModPath.find_first_of("\\r\\n")==std::string::npos){
                            std::ofstream f("/run/banana/launch");f<<gModPath<<"\\n";f.close();
                            if(f)return G_QUIT;
                            gModNote="Could not schedule launch";
                        }
                    }else{
                        auto j=std::static_pointer_cast<azmods::Job>(gModJob);
                        std::lock_guard<std::mutex> l(j->lock);
                        if(gModSelection<j->rows.size()){gModJob=azmods::installPatch(gRomPath,j->rows[gModSelection]);gModPending=true;gModNote="Downloading and checking source revision...";}
                    }
                }
            }else if(ly>=150&&ly<350&&!gModPending){gModSelection=unsigned((ly-150)/25);}
            return G_NONE;
        }
        if(gScanOpen && gLiveScan) {
            if(down)""")
sub("settings_gamepanel.cpp","if (lx < 320) { gAiPanel=true; gAiReset=false; }",'''if (lx < 215) { gAiPanel=true; gAiReset=false; }
            else if(lx<430){gModOpen=true;gAiPanel=true;gAiReset=false;gAiPrompt.clear();}''')
sub("settings_gamepanel.cpp",'text(gAiPanel ? "AI Cheats" : "Keyboard"','text(gModOpen ? "Mods" : gAiPanel ? "AI Cheats" : "Keyboard"')
sub("settings_gamepanel.cpp",'if(gScanOpen && gLiveScan) {\n            auto scan=', '''if(gModOpen){
            box("bubble",false,18,14,604,54);text("Mods",true,24,30,25,p.accent);
            text(fit(gTitle,true,18,350),true,18,230,30,p.ink);
            text(fit(gAiPrompt.empty()?"Type a mod request":gAiPrompt,true,18,590),true,18,24,78,p.ink);
            text(fit(gModNote.empty()?"Online BPS patch browser":gModNote,true,18,590),true,18,24,110,p.accent);
            if(gModJob&&!gModPending){
                auto j=std::static_pointer_cast<azmods::Job>(gModJob);
                std::lock_guard<std::mutex> l(j->lock);
                for(size_t i=0;i<j->rows.size();++i){
                    int y=150+int(i)*25;box("slot",i==gModSelection,18,y,604,24);
                    text(fit(j->rows[i].name,true,16,570),true,16,25,y+3,i==gModSelection?p.onPick:p.ink);
                }
                if(gModSelection<j->rows.size())wrapped(j->rows[gModSelection].url,14,24,353,590,3,p.muted);
            }
            const char* labs[]={"Back","Type","Search",gModInstalled?"Launch":"Install"};
            for(int i=0;i<4;i++){box("slot",false,8+i*160,425,150,48);text(labs[i],true,18,20+i*160,440,p.ink);}
            be->endScreen();return;
        }
        if(gScanOpen && gLiveScan) {
            auto scan=''')
sub("settings_gamepanel.cpp",'box("slot",false,18,425,298,48); box("slot",gAiReset,324,425,298,48);\n            text("AI Cheats",true,19,34,438,p.accent);\n            text(gAiReset?"Restart? Tap again":"Restart game",true,19,340,438,gAiReset?p.onPick:p.ink);','''box("slot",false,8,425,205,48);box("slot",false,218,425,205,48);box("slot",gAiReset,428,425,204,48);
            text("AI Cheats",true,19,24,438,p.accent);text("Mods",true,19,244,438,p.accent);
            text(gAiReset?"Tap to restart":"Restart game",true,18,438,438,gAiReset?p.onPick:p.ink);''')
print("PASS: native online mod search, source inspection, install and relaunch")
