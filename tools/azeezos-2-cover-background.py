#!/usr/bin/env python3
"""Per-game blurred box art on the bottom in-game companion screen."""
from pathlib import Path
import sys
root=Path(sys.argv[1])/"ui/src"
def rep(path,old,new):
    p=root/path
    s=p.read_text()
    if new in s:return
    if s.count(old)!=1:raise SystemExit("Cover art anchor mismatch: "+path+" "+repr(old[:100]))
    p.write_text(s.replace(old,new,1))
rep("settings.h","void gameOpen(const std::string& title, const std::string& system, int screen, bool touch);",'''void gameOpen(const std::string& title, const std::string& system, int screen, bool touch);
        void gameCover(const std::string& path) { gCoverPath=path; gCoverTex.reset(); gCoverTried=false; }''')
rep("settings.h","std::string gTitle, gSystem;",'''std::string gTitle, gSystem;
        std::string gCoverPath;
        rnds::TexPtr gCoverTex;
        bool gCoverTried=false, gCoverDrawing=false;''')
rep("main.cpp","const std::string& title, const std::string& sysName)\n\t{","const std::string& title, const std::string& sysName, const std::string& coverPath)\n\t{")
rep("main.cpp","settingsView.gameOpen(title, sysName, panelScreen, input.hasTouch(panelScreen));",'''settingsView.gameCover(panelScreen == 1 ? coverPath : std::string());
            settingsView.gameOpen(title, sysName, panelScreen, input.hasTouch(panelScreen));''')
rep("main.cpp","gamePanel(pid, status, gameScreen, cmdFd, outFd, lib.gameAt(game).title, sd.name);","gamePanel(pid, status, gameScreen, cmdFd, outFd, lib.gameAt(game).title, sd.name, lib.gameAt(game).box);")
rep("settings_gamepanel.cpp","void Settings::gameFrame()\n\t{",'''// The cover is fitted and blurred once per game, not once per frame.
    static rnds::Bitmap azBlurCover(const std::string& path)
    {
        rnds::Bitmap original=rnds::decodeFile(path);
        if(original.empty() || original.alpha) return {};
        rnds::Bitmap b=rnds::cover(original,80,60);
        if(b.empty() || b.px.size()!=80u*60u*4u) return {};
        // Three separable box passes approximate a Gaussian at 640x480.
        // Resolve transparent art onto neutral grey before averaging.
        for(size_t i=0;i<b.px.size();i+=4) {
            unsigned a=b.px[i+3];
            for(int k=0;k<3;k++)b.px[i+k]=(b.px[i+k]*a+64*(255-a)+127)/255;
            b.px[i+3]=255;
        }
        for(int pass=0;pass<3;pass++) for(int axis=0;axis<2;axis++){
            auto tmp=b.px;
            for(int y=0;y<60;y++)for(int x=0;x<80;x++)for(int k=0;k<3;k++){
                unsigned sum=0;
                for(int d=-3;d<=3;d++){
                    int sx=std::max(0,std::min(79,x+(axis==0?d:0)));
                    int sy=std::max(0,std::min(59,y+(axis==1?d:0)));
                    sum+=tmp[(sy*80+sx)*4+k];
                }
                b.px[(y*80+x)*4+k]=(sum+3)/7;
            }
        }
        return b;
    }
    void Settings::gameFrame()
\t{''')
rep("settings_gamepanel.cpp",'''\t\tbe->beginScreen(gScreen);
\t\tbox("screen", false, 0, 0, 640, 480);
\t\tif (gKeysOpen)''','''\t\tbe->beginScreen(gScreen);
        gCoverDrawing=false;
\t\tbox("screen", false, 0, 0, 640, 480);
        if (gScreen==1 && !gCoverPath.empty() && !gCoverTried) {
            gCoverTried=true;
            auto art=azBlurCover(gCoverPath);
            if(!art.empty())gCoverTex=be->upload(art,true);
        }
        if(gScreen==1 && gCoverTex) {
            be->draw(gCoverTex,0,0,X(640),X(480),Color(1,1,1,1));
            // Contrast veil, chosen to match the existing theme.
            be->fill(0,0,X(640),X(480),light?Color(1,1,1,.34f):Color(0,0,0,.44f));
            gCoverDrawing=true;
        }
\t\tif (gKeysOpen)''')
rep("settings_gamepanel.cpp","\t\tgameFrame();\n\t\tevict();","\t\tgameFrame();\n        gCoverDrawing=false;\n\t\tevict();")
rep("settings_gamepanel.cpp","\tvoid Settings::gameClose()\n\t{","\tvoid Settings::gameClose()\n\t{\n        gameCover(\"\"); gCoverDrawing=false;")
rep("settings.cpp","be->draw(c.tex, std::round(X(x)) - c.ox, std::round(X(y)) - c.oy, (float)c.tex->w, (float)c.tex->h, Color(1, 1, 1, 1));","be->draw(c.tex, std::round(X(x)) - c.ox, std::round(X(y)) - c.oy, (float)c.tex->w, (float)c.tex->h, Color(1, 1, 1, gCoverDrawing && (kind==\"slot\" || kind==\"bubble\" || kind==\"hero\") ? .82f : 1.f));")
print("Per-game bottom-screen blurred cover and translucent game-panel controls integrated")
