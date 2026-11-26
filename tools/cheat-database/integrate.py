#!/usr/bin/env python3
from pathlib import Path
import sys,shutil
root=Path(sys.argv[1]);here=Path(__file__).parent
ui=root/"ui/src"
shutil.copyfile(here/"page.h",ui/"azeez_cheat_db.h")
def rep(rel,a,b):
    p=root/rel;s=p.read_text()
    if b in s:return
    if s.count(a)!=1:raise SystemExit("cheat integration anchor "+rel+" "+repr(a[:90]))
    p.write_text(s.replace(a,b,1))
for pkg,mode,ident in [("retroarch","ra","RETROARCH"),("bananafront","bf","BANANAFRONT")]:
    p=root/"buildroot/package"/pkg
    shutil.copyfile(here/"frontend.py",p/"azeez-cheat-db.py")
    anchor="define "+ident+"_BUILD_CMDS"
    rep("buildroot/package/"+pkg+"/"+pkg+".mk",anchor,anchor+"\n\tpython3 $(BR2_EXTERNAL_BANANA_PATH)/package/"+pkg+"/azeez-cheat-db.py "+mode+" $(@D)")
# Branding: keep stable config keys and on-disk paths for migration.
p=ui/"settings.cpp";s=p.read_text().replace("BananaFront","AzeezFront").replace("BananaOS's own: lighter","AzeezOS's own: lighter");p.write_text(s)
rep("ui/src/settings.h","G_RESET };","G_RESET, G_DB_APPLY };")
rep("ui/src/settings.h","std::string gTitle, gSystem;","std::string gTitle, gSystem;\n        bool gDbOpen=false;\n        std::shared_ptr<void> gDb;")
rep("ui/src/settings_gamepanel.cpp",'#include "azeezos_ai_cheats.h"','#include "azeezos_ai_cheats.h"\n#include "azeez_cheat_db.h"')
rep("ui/src/settings_gamepanel.cpp","gTitle = title; gSystem = system; gScreen = screen; gTouch = touch;",
    "gTitle = title; gSystem = system; gScreen = screen; gTouch = touch;\n        gDbOpen=false;gDb.reset();")
rep("ui/src/settings_gamepanel.cpp","float lx = x / s, ly = y / s;",
    """float lx = x / s, ly = y / s;
        if(gDbOpen && gDb){
            if(down)return G_NONE;
            auto d=std::static_pointer_cast<azdb::Page>(gDb);
            if(ly>=425){
                if(lx<160){if(d->fileView)gDbOpen=false;else {d->fileView=true;d->offset=0;}}
                else if(lx<320)d->offset=d->offset>=6?d->offset-6:0;
                else if(lx<480){size_t n=d->fileView?d->files.size():d->rows.size();if(d->offset+6<n)d->offset+=6;}
                else if(!d->fileView){
                    if(d->write()){d->status="Apply requested; emulator compatibility varies.";return G_DB_APPLY;}
                    d->status="Could not save cheats";
                }
            }else if(ly>=110&&ly<398){
                size_t i=d->offset+(size_t)((ly-110)/48);
                if(d->fileView){if(!d->select(i))d->status="Invalid cheat file";}
                else if(i<d->rows.size())d->rows[i].enabled=!d->rows[i].enabled;
            }
            return G_NONE;
        }""")
rep("ui/src/settings_gamepanel.cpp","if (lx < 215) { gAiPanel=true; gAiReset=false; }",
    """if(lx<160){gDb=std::make_shared<azdb::Page>();std::static_pointer_cast<azdb::Page>(gDb)->open(gSysId,gRomPath);gDbOpen=true;gAiReset=false;}
            else if (lx < 320) { gAiPanel=true; gAiReset=false; }""")
rep("ui/src/settings_gamepanel.cpp","else if(lx<430){gModOpen=true;","else if(lx<480){gModOpen=true;")
rep("ui/src/settings_gamepanel.cpp",'if (gKeysOpen) { gameKeysFrame(p); be->endScreen(); return; }',
    """if(gDbOpen && gDb){
            auto d=std::static_pointer_cast<azdb::Page>(gDb);
            box("bubble",false,18,14,604,54);text("Cheats",true,24,30,25,p.accent);
            text(fit(gTitle,true,18,390),true,18,210,30,p.ink);
            text(fit(d->status,true,16,600),true,16,20,82,p.muted);
            size_t n=d->fileView?d->files.size():d->rows.size();
            for(size_t j=0;j<6&&j+d->offset<n;j++){
                size_t i=j+d->offset;int y=110+j*48;
                bool on=!d->fileView&&d->rows[i].enabled;
                std::string label=d->fileView?d->files[i].stem().string():((on?"ON  ":"OFF  ")+d->rows[i].desc);
                box("slot",on,18,y,604,44);text(fit(label,true,18,570),true,18,30,y+12,on?p.onPick:p.ink);
            }
            const char* labs[]={"Back","Previous","Next",d->fileView?"":"Apply"};
            for(int i=0;i<4;i++){box("slot",false,8+i*160,425,150,48);text(labs[i],true,18,20+i*160,440,p.ink);}
            be->endScreen();return;
        }
        if (gKeysOpen) { gameKeysFrame(p); be->endScreen(); return; }""")
rep("ui/src/settings_gamepanel.cpp",'box("slot",false,8,425,205,48);box("slot",false,218,425,205,48);box("slot",gAiReset,428,425,204,48);',
    'box("slot",false,8,425,150,48);box("slot",false,168,425,150,48);box("slot",false,328,425,150,48);box("slot",gAiReset,488,425,144,48);')
rep("ui/src/settings_gamepanel.cpp",'text("AI Cheats",true,19,24,438,p.accent);text("Mods",true,19,244,438,p.accent);',
    'text("Cheats",true,19,24,438,p.accent);text("AI Cheats",true,19,184,438,p.accent);text("Mods",true,19,348,438,p.accent);')
rep("ui/src/settings_gamepanel.cpp",'text(gAiReset?"Tap to restart":"Restart game",true,18,438,438,','text(gAiReset?"Confirm":"Restart",true,18,500,438,')
p=ui/"main.cpp";s=p.read_text()
anchor='a == Settings::G_RESET ? "RESET\\n"'
assert s.count(anchor)==2
p.write_text(s.replace(anchor,'a == Settings::G_DB_APPLY ? "AZEEZ_CHEATS_APPLY\\n" : '+anchor))
print("Offline cheats page, RetroArch and AzeezFront frontend hooks integrated")
