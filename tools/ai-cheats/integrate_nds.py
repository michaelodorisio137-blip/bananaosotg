#!/usr/bin/env python3
from pathlib import Path
import sys,shutil
ui=Path(sys.argv[1])/"ui/src"
shutil.copyfile(Path(__file__).parent/"nds_scan_page.inc",ui/"nds/azeez_scan_page.inc")
def sub(p,a,b):
    p=ui/p;s=p.read_text()
    if s.count(a)!=1:raise SystemExit(f"DS scan anchor mismatch {p}: {a[:100]!r} ({s.count(a)})")
    p.write_text(s.replace(a,b))
sub("nds/overlay.h","namespace banana::nds","namespace banana { class CompLink; }\nnamespace banana::nds")
sub("nds/overlay.h","std::unique_ptr<OverlayPage> makeTestPage(Overlay& ov);","std::unique_ptr<OverlayPage> makeTestPage(Overlay& ov);\n    std::unique_ptr<OverlayPage> makeAzeezScanPage(Overlay& ov,banana::CompLink& link);")
sub("nds/overlay.cpp",'#include "overlay.h"','#include "overlay.h"\n#include "../complink.h"\n#include "../live_scan.h"')
sub("nds/overlay.cpp","\t// ---- the loop ----",'''#include "azeez_scan_page.inc"
    std::unique_ptr<OverlayPage> makeAzeezScanPage(Overlay& ov,banana::CompLink& link){
        return std::make_unique<AzeezScanPage>(ov,link);
    }

    // ---- the loop ----''')
sub("main.cpp","\t\tif (!panel)\n\t\t{\n\t\t\tinput.close();",'''        if(!panel && sd.id=="nds" && !ndsPage && disp.isOpen() && ndsMode!="test"){
            nds::setAssets(o.assets);
            if(ndsOverlay.create(disp.width(),disp.height())){
                if(compLink.create())ndsPage=nds::makeAzeezScanPage(ndsOverlay,compLink);
                else ndsOverlay.close();
            }
        }
        if (!panel)
        {
            input.close();''')
sub("complink.cpp","shm->status[i] == BCOMP_UNMAPPED || shm->status[i] == BCOMP_TOOBIG","shm->status[i] != BCOMP_OK")
print("PASS: BananaDS read-only scan overlay and strict shared-memory reply validation")
