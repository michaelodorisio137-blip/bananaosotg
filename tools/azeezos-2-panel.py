#!/usr/bin/env python3
"""Native in-game cheat research and reset UI. Does not enable untested cheats."""
from pathlib import Path
import shutil, sys
root=Path(sys.argv[1])
ui=root/"ui/src"
shutil.copyfile(Path(__file__).with_name("azeezos-2-ai-cheats.h"),ui/"azeezos_ai_cheats.h")
def sub(p,a,b,count=1):
    p=ui/p
    s=p.read_text()
    if s.count(a)!=count:
        raise SystemExit(f"2.0 anchor mismatch: {p}: {a[:90]!r}, got {s.count(a)}")
    p.write_text(s.replace(a,b))
sub("settings.h",'enum GameAction { G_NONE, G_SAVE, G_LOAD, G_MENU, G_FFWD, G_QUIT, G_LOADSLOT };',
    'enum GameAction { G_NONE, G_SAVE, G_LOAD, G_MENU, G_FFWD, G_QUIT, G_LOADSLOT, G_RESET };')
# Keep the helper definition out of the main settings header.
sub("settings.h",'std::string gTitle, gSystem;',
    '''std::string gTitle, gSystem;
        bool gAiPanel = false, gAiReset = false, gAiPending = false, gAiFound = false;
        size_t gAiPage = 0;
        std::string gAiPrompt, gAiText, gAiStatus;
        std::shared_ptr<void> gAiJob;''')
sub("settings_gamepanel.cpp",'#include "settings_curl.h"','#include "settings_curl.h"\n#include "azeezos_ai_cheats.h"')
sub("settings_gamepanel.cpp",'gTitle = title; gSystem = system; gScreen = screen; gTouch = touch;',
    '''gTitle = title; gSystem = system; gScreen = screen; gTouch = touch;
        gAiPanel = gAiReset = gAiPending = gAiFound = false;
        gAiPage = 0; gAiPrompt.clear(); gAiText.clear(); gAiStatus.clear(); gAiJob.reset();''')
sub("settings_gamepanel.cpp",'raw.reset();\n\t\tgAchOpen = false;',
    'raw.reset();\n        gAiJob.reset(); gAiPanel = gAiPending = false;\n\t\tgAchOpen = false;')
sub("settings_gamepanel.cpp",'bool changed = false;\n\t\tif (raw)',
    '''bool changed = false;
        if (gAiPending && gAiJob) {
            auto r=std::static_pointer_cast<aicheat::Result>(gAiJob);
            std::lock_guard<std::mutex> lock(r->lock);
            if(r->ready) {
                gAiPending=false; gAiFound=r->ok; gAiText=r->text;
                gAiStatus=r->ok?"Research draft - not tested":"Search failed";
                gAiPage=0; changed=true; wake=true;
            }
        }
        if (raw)''')
sub("settings_gamepanel.cpp",'float lx = x / s, ly = y / s;\n\t\tint hit = -1;',
    '''float lx = x / s, ly = y / s;
        if (gAiPanel && !gKeysOpen) {
            if (down) return G_NONE;
            if (ly >= 420 && ly < 480) {
                if (lx < 160) { gAiPanel=false; gAiReset=false; }
                else if (lx < 320) { if(!gAiPending) { gKeysOpen=true; gKeyPage=0; gKeyShift=0; gKeyTyped=gAiPrompt; } }
                else if (lx < 480) {
                    if (!gAiPending && !gAiPrompt.empty()) {
                        gAiJob=aicheat::search(gRomPath,gTitle,gSysId,gAiPrompt);
                        gAiPending=true; gAiFound=false; gAiText.clear(); gAiPage=0; gAiStatus="Searching online...";
                    }
                } else if (gAiFound && gAiJob) {
                    auto r=std::static_pointer_cast<aicheat::Result>(gAiJob);
                    std::lock_guard<std::mutex> lock(r->lock);
                    gAiStatus=aicheat::saveDraft(data,*r)?"Unverified draft saved":"Unable to save draft";
                }
            } else if (ly >= 365 && ly < 420) {
                if(lx < 320) { if(gAiPage) --gAiPage; }
                else if((gAiPage+1)*220 < gAiText.size()) ++gAiPage;
            }
            return G_NONE;
        }
        if (!gKeysOpen && !gAchOpen && !gStates && !gbaPanel.pagesShown() &&
            !(gameComp && gameComp->active() && gcView != GC_GAME) && ly >= 425 && ly < 480) {
            if (down) return G_NONE;
            if (lx < 320) { gAiPanel=true; gAiReset=false; }
            else {
                if (gAiReset) { gAiReset=false; return G_RESET; }
                gAiReset=true;
            }
            return G_NONE;
        }
        if (!down && ly < 425) gAiReset=false;
\t\tint hit = -1;''')
sub("settings_gamepanel.cpp",'case 7: gKeysOpen = false; break;',
    'case 7: if(gAiPanel) gAiPrompt=gKeyTyped; gKeysOpen = false; break;')
sub("settings_gamepanel.cpp",'if (code == -1) { gKeyShift ^= 1; return; }',
    '''if (code == -1) { gKeyShift ^= 1; return; }
        if (gAiPanel) {
            if(code==KEY_ENTER) { gAiPrompt=gKeyTyped; gKeysOpen=false; }
            else if(code==KEY_BACKSPACE) { if(!gKeyTyped.empty()) gKeyTyped.pop_back(); }
            else if(gKeyTyped.size()<240) {
                if(code==KEY_SPACE) gKeyTyped+=' ';
                else if(label && label[0] && !label[1]) {
                    char ch=label[0];
                    if(gKeyPage==0 && !gKeyShift && ch>='A' && ch<='Z') ch+=32;
                    gKeyTyped+=ch;
                }
            }
            return;
        }''')
sub("settings_gamepanel.cpp",'text("Keyboard", true, 24, 16, 6, p.ink);',
    'text(gAiPanel ? "AI Cheats" : "Keyboard", true, 24, 16, 6, p.ink);')
sub("settings_gamepanel.cpp",'const std::string typed = gKeyTyped.empty() ? "Tap a key: the game hears it on the other screen" : gKeyTyped;',
    'const std::string typed = gKeyTyped.empty() ? (gAiPanel ? "Describe the cheat you want" : "Tap a key: the game hears it on the other screen") : gKeyTyped;')
sub("settings_gamepanel.cpp",'if (gAchOpen) { gameAchFrame(p); be->endScreen(); return; }',
    '''if(gAiPanel) {
            box("bubble",false,18,14,604,54);
            text("AI Cheats",true,24,30,25,p.accent);
            text(fit(gTitle,true,18,350),true,18,230,30,p.ink);
            box("slot",false,18,78,604,68);
            text("Request:",true,16,30,88,p.muted);
            text(fit(gAiPrompt.empty()?"Tap Type to enter a cheat":gAiPrompt,true,18,570),true,18,30,113,p.ink);
            text(fit(gAiStatus.empty()?"Online research - no code applied":gAiStatus,true,18,590),true,18,22,157,p.accent);
            if(!gAiText.empty()) {
                std::string part=gAiText.substr(gAiPage*220,220);
                wrapped(part,17,24,190,590,7,p.ink);
            } else {
                wrapped("Find source-backed codes for this game's file. Research is not proof that a cheat works. Live testing is not enabled in this preview.",18,24,190,590,5,p.muted);
            }
            if(!gAiText.empty()) {
                box("slot",false,18,365,298,45); box("slot",false,324,365,298,45);
                text("Previous",true,19,35,377,p.ink); text("Next",true,19,342,377,p.ink);
            }
            const char* labels[]={"Back","Type","Search","Save draft"};
            for(int i=0;i<4;i++) {
                box("slot",false,8+i*160,425,150,48);
                text(labels[i],true,18,20+i*160,440,p.ink);
            }
            be->endScreen(); return;
        }
        if (gAchOpen) { gameAchFrame(p); be->endScreen(); return; }''')
sub("settings_gamepanel.cpp",'''std::string hint = gTouch ? "Tap a tile, or hold F with the button under it" : "Hold F with the button under each tile";
\t\tfloat hw = text(hint, false, 15, 0, 0, p.muted, false, 0, true);
\t\ttext(hint, false, 15, 320 - hw / 2, 438, p.muted);''',
    '''if(gTouch && !gStates) {
            box("slot",false,18,425,298,48); box("slot",gAiReset,324,425,298,48);
            text("AI Cheats",true,19,34,438,p.accent);
            text(gAiReset?"Restart? Tap again":"Restart game",true,19,340,438,gAiReset?p.onPick:p.ink);
        } else {
            text("Hold F with the button under each tile",false,15,18,438,p.muted);
        }''')
# The real panel command path and headless panel-tap test path both use this enum.
sub("main.cpp",'a == Settings::G_QUIT ? "QUIT\\n" : nullptr;',
    'a == Settings::G_RESET ? "RESET\\n" : a == Settings::G_QUIT ? "QUIT\\n" : nullptr;',2)
print("PASS: native AI Cheats research panel, local prompt keyboard, unverified drafts, and confirmed emulator reset.")
