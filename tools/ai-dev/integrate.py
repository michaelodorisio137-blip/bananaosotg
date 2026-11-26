#!/usr/bin/env python3
from pathlib import Path
import sys,shutil
root=Path(sys.argv[1])
ui=root/"ui/src"
shutil.copyfile(Path(__file__).parent/"stage.py",root/"system/rootfs/usr/libexec/banana/azeez-stage-ai.py")
for cfg in (root/"buildroot/configs").glob("banana_*_defconfig"):
    s=cfg.read_text()
    if "BR2_PACKAGE_LIBOPENSSL_BIN=y" not in s:cfg.write_text(s.rstrip()+"\nBR2_PACKAGE_LIBOPENSSL_BIN=y\n")
shutil.copyfile(Path(__file__).parent/"client.h",ui/"azeez_dev_client.h")
def sub(p,a,b):
    p=ui/p;s=p.read_text()
    if s.count(a)!=1:raise SystemExit(f"AI dev anchor mismatch {p}: {a[:100]!r} ({s.count(a)})")
    p.write_text(s.replace(a,b))
sub("settings.h","std::string gModNote, gModPath;","std::string gModNote, gModPath;\n        bool gDevOpen=false,gDevPending=false,gDevConfirm=false;\n        std::shared_ptr<void> gDevJob;\n        std::string gDevId,gDevNote,gDevUrl,gDevConversation;\n        bool gDevContinue=false;")
sub("settings_gamepanel.cpp",'#include "azeez_mod_browser.h"','#include "azeez_mod_browser.h"\n#include "azeez_dev_client.h"')
sub("settings_gamepanel.cpp","gModOpen=gModPending=gModInstalled=false;",'''gDevOpen=gDevPending=gDevConfirm=false;gDevJob.reset();gDevNote.clear();gDevUrl.clear();gDevId.clear();
        {std::ifstream f(data+"/ai-dev-last-request");f>>gDevId;if(!azdev::validId(gDevId))gDevId.clear();}
        gDevContinue=!gDevId.empty();gDevConversation.clear();
        {std::ifstream f(data+"/ai-dev-chat.txt");char buf[6000];f.read(buf,sizeof buf);gDevConversation.assign(buf,size_t(f.gcount()));}
        gModOpen=gModPending=gModInstalled=false;''')
sub("settings_gamepanel.cpp","if(gModPending && gModJob){",'''if(gDevPending&&gDevJob){
            auto r=std::static_pointer_cast<azdev::Result>(gDevJob);
            std::lock_guard<std::mutex> l(r->lock);
            if(r->done){gDevPending=false;gDevNote=r->message;if(!r->url.empty())gDevUrl=r->url;
                if(r->ok&&!r->conversation.empty()){gDevConversation=r->conversation;std::ofstream f(data+"/ai-dev-chat.txt",std::ios::trunc);f<<gDevConversation;}
                if(r->ok&&azdev::validId(r->id)){gDevId=r->id;gDevContinue=true;std::ofstream f(data+"/ai-dev-last-request");f<<gDevId<<"\\n";}
                changed=true;wake=true;}
        }
        if(gModPending && gModJob){''')
sub("settings_gamepanel.cpp","if(gModOpen && !gKeysOpen){",'''if(gDevOpen&&!gKeysOpen){
            if(down)return G_NONE;
            if(ly>=14&&ly<68&&lx>=440&&!gDevPending&&!gAiPrompt.empty()){
                gDevConfirm=false;gDevJob=azdev::chat(gAiPrompt,gDevConversation);gDevPending=true;gDevNote="Asking AI...";
            }else if(ly>=340&&ly<368&&!gDevPending&&!gDevId.empty()){
                gDevContinue=!gDevContinue;gDevConfirm=false;
                gDevNote=gDevContinue?"Next build extends the last successful proposal.":"Next build starts from the base firmware.";
            }else if(ly>=370&&ly<420&&!gDevPending&&!gDevId.empty()){
                gDevConfirm=false;
                if(lx<320){gDevJob=azdev::review(gDevId);gDevNote="Requesting protected review of successful build...";}
                else{gDevJob=azdev::stage(gDevId,data);gDevNote="Checking reviewed signature and downloading...";}
                gDevPending=true;
            }else if(ly>=425&&!gDevPending){
                if(lx<160){gDevOpen=false;gAiPanel=false;gDevConfirm=false;}
                else if(lx<320){gKeysOpen=true;gKeyPage=0;gKeyShift=0;gKeyTyped=gAiPrompt;gDevConfirm=false;}
                else if(lx<480&&!gAiPrompt.empty()){
                    if(!gDevConfirm){gDevConfirm=true;gDevNote=gDevContinue?"Confirm: build on last proposal with recent chat context.":"Confirm: build from base with recent chat context.";}
                    else{gDevConfirm=false;gDevJob=azdev::submit(gAiPrompt,gDevContinue?gDevId:std::string{},gDevConversation);gDevPending=true;gDevNote="Submitting feature request...";}
                }else if(lx>=480&&!gDevId.empty()){
                    gDevConfirm=false;gDevJob=azdev::poll(gDevId);gDevPending=true;gDevNote="Checking build...";
                }
            }
            return G_NONE;
        }
        if(gModOpen && !gKeysOpen){''')
sub("settings_gamepanel.cpp","if (lx < 215) { gAiPanel=true; gAiReset=false; }\n            else if(lx<430){gModOpen=true;gAiPanel=true;gAiReset=false;gAiPrompt.clear();}",'''if (lx < 160) { gAiPanel=true; gAiReset=false; }
            else if(lx<320){gModOpen=true;gAiPanel=true;gAiReset=false;gAiPrompt.clear();}
            else if(lx<480){gDevOpen=true;gAiPanel=true;gAiReset=false;gAiPrompt.clear();}''')
sub("settings_gamepanel.cpp",'text(gModOpen ? "Mods" : gAiPanel ? "AI Cheats" : "Keyboard"','text(gDevOpen ? "AI Dev" : gModOpen ? "Mods" : gAiPanel ? "AI Cheats" : "Keyboard"')
sub("settings_gamepanel.cpp","if(gModOpen){\n            box",'''if(gDevOpen){
            box("bubble",false,18,14,604,54);text("AI Dev Chat",true,24,30,25,p.accent);
            box("slot",false,440,20,174,40);text("Ask AI",true,18,465,29,p.accent);
            wrapped(gAiPrompt.empty()?"Type a firmware feature request":gAiPrompt,19,24,83,590,4,p.ink);
            wrapped(gDevNote.empty()?"Build an isolated, reviewable firmware proposal. No automatic installation.":gDevNote,20,24,190,590,4,p.accent);
            if(!gDevId.empty())text("Request: "+gDevId,true,15,24,295,p.muted);
            if(!gDevUrl.empty())text(fit(gDevUrl,true,14,590),true,14,24,325,p.ink);
            if(!gDevId.empty()){
                text(gDevContinue?"Build base: Last proposal (tap to change)":"Build base: Stock preview (tap to change)",true,15,24,344,p.accent);
                box("slot",false,18,370,294,45);text("Request review",true,18,35,383,p.accent);
                box("slot",false,328,370,294,45);text("Stage update",true,18,345,383,p.accent);
            }
            const char* labs[]={"Back","Type",gDevConfirm?"Confirm":"Build","Status"};
            for(int i=0;i<4;i++){box("slot",false,8+i*160,425,150,48);text(labs[i],true,18,20+i*160,440,p.ink);}
            be->endScreen();return;
        }
        if(gModOpen){
            box''')
sub("settings_gamepanel.cpp",'box("slot",false,8,425,205,48);box("slot",false,218,425,205,48);box("slot",gAiReset,428,425,204,48);\n            text("AI Cheats",true,19,24,438,p.accent);text("Mods",true,19,244,438,p.accent);\n            text(gAiReset?"Tap to restart":"Restart game",true,18,438,438,gAiReset?p.onPick:p.ink);','''const char* labs[]={"AI Cheats","Mods","AI Dev",gAiReset?"Confirm":"Restart"};
            for(int i=0;i<4;i++){box("slot",i==3&&gAiReset,8+i*160,425,150,48);text(labs[i],true,18,20+i*160,440,i==3&&gAiReset?p.onPick:p.ink);}''')
print("PASS: AI development request keyboard, submit confirmation and build status")
