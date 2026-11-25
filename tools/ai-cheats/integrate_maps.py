#!/usr/bin/env python3
"""Discover additional RAM maps on BananaFront without guessing core addresses."""
from pathlib import Path
import sys
ui=Path(sys.argv[1])/"ui/src"
def sub(p,a,b):
    p=ui/p;s=p.read_text()
    if s.count(a)!=1:raise SystemExit(f"RAM map anchor mismatch {p}: {a[:100]!r} ({s.count(a)})")
    p.write_text(s.replace(a,b))
sub("settings.h","bool gScanOpen=false,","bool gScanEligible=false,gScanNew=false;\n        bool gScanOpen=false,")
sub("settings_gamepanel.cpp","if(!enabled) return;","gScanEligible=enabled;gScanNew=false;\n        if(!enabled) return;")
sub("settings_gamepanel.cpp","std::string Settings::gameScanRequest(double t) {",'''std::string Settings::gameScanRequest(double t) {
        if(gScanEligible&&!gLiveScan&&link&&link->attached()){
            const auto* r=link->raw();
            uint32_t size=0,base=0;
            for(unsigned i=0;i<std::min(r->region_count,unsigned(BCOMP_MAX_REGIONS));++i){
                auto m=r->regions[i];
                if((m.flags&BCOMP_R_RAM)&&!(m.flags&(BCOMP_R_ROM|BCOMP_R_IO|BCOMP_R_VRAM|BCOMP_R_SRAM))
                   &&m.size>size&&uint64_t(m.start)+m.size<=0x100000000ULL){size=m.size;base=m.start;}
            }
            if(size){
                gLiveScan=std::make_shared<azeez::LiveScan>(base,std::min(size,uint32_t(32768)));
                gScanNew=true;
            }
        }''')
sub("settings_gamepanel.cpp","bool changed = gLiveScan && std::static_pointer_cast<azeez::LiveScan>(gLiveScan)->changed();","bool changed = gScanNew;gScanNew=false;\n        if(gLiveScan && std::static_pointer_cast<azeez::LiveScan>(gLiveScan)->changed())changed=true;")
sub("main.cpp",'if (pkOn || gcOn || (panel && (sd.id=="gba"||sd.id=="gb"||sd.id=="gbc")))','if (pkOn || gcOn || panel)')
sub("settings_gamepanel.cpp",'text(c&&c->savedView?"Confirmed one-shot cheats":"8-bit candidates - offline test",true,18,24,150,p.muted);','text(c&&c->savedView?"Confirmed one-shot cheats":c?"8-bit candidates - offline test":"8-bit candidates - read only",true,18,24,150,p.muted);')
# Hide the unavailable catalog and testing controls in dynamically mapped read-only mode.
sub("settings_gamepanel.cpp",'box("slot",false,405,17,215,46);\n            text(c&&c->savedView?"Back to scan":"Saved cheats",true,18,420,30,p.accent);','if(c){box("slot",false,405,17,215,46);text(c->savedView?"Back to scan":"Saved cheats",true,18,420,30,p.accent);}')
sub("settings_gamepanel.cpp",'box("slot",false,8,365,310,48);box("slot",false,324,365,150,48);box("slot",false,484,365,148,48);\n                text(scanLabs[0],true,19,35,378,p.ink);text(scanLabs[1],true,19,335,378,p.ink);text(scanLabs[2],true,19,500,378,p.ink);','box("slot",false,8,365,310,48);box("slot",false,324,365,c?150:308,48);\n                text(scanLabs[0],true,19,35,378,p.ink);text(scanLabs[1],true,19,335,378,p.ink);\n                if(c){box("slot",false,484,365,148,48);text(scanLabs[2],true,19,500,378,p.ink);}')
print("PASS: automatic bounded read-only RAM discovery for other BananaFront cores")
