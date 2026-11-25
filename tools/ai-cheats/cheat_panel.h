#pragma once
#include "trial.h"
#include "catalog.h"
#include <ifaddrs.h>
#include <net/if.h>
#include <cstdlib>
namespace azeez {
inline bool networkOffline(){
    ifaddrs* list=nullptr;
    if(getifaddrs(&list)!=0)return false;
    bool offline=true;
    for(auto* p=list;p;p=p->ifa_next)
        if(!(p->ifa_flags&IFF_LOOPBACK)&&(p->ifa_flags&IFF_UP)&&(p->ifa_flags&IFF_RUNNING)){offline=false;break;}
    freeifaddrs(list);return offline;
}
inline bool hardcoreOff(){
    std::ifstream f("/data/retroarch/retroarch.cfg");
    if(!f)return false;
    std::string line;
    while(std::getline(f,line))if(line.find("cheevos_hardcore_mode_enable")!=std::string::npos &&
        line.find("true")!=std::string::npos)return false;
    return true;
}
class CheatPanel {
    std::string data_;
    uint32_t base_,size_;
public:
    Trial trial;
    unsigned selection=0,value=99;
    bool savedView=false;
    std::string note;
    CheatPanel(std::string data,uint32_t base,uint32_t size):data_(std::move(data)),base_(base),size_(size){}
    Catalog catalog()const{return Catalog(data_,sessionKey("/run/banana/azeez-cheat-session"),base_,size_);}
    bool permitted()const{return catalog().ready()&&networkOffline()&&hardcoreOff();}
    bool active()const{
        auto s=trial.state();
        return s!=Trial::Idle&&s!=Trial::Confirmed&&s!=Trial::Reverted&&s!=Trial::Failed;
    }
    bool begin(uint32_t address,unsigned v){
        if(address<base_||address-base_>=size_||!permitted()){note="Requires RetroArch, offline network and hardcore off.";return false;}
        if(!trial.begin(address,v)){note="Resolve previous trial first.";return false;}
        note="Testing one write; check the game.";return true;
    }
    std::string request(double now){
        if(!active())return "";
        if(!permitted()){trial.interrupt();note="Connection or hardcore changed. Trial stopped; verify game.";return "";}
        return trial.request(now);
    }
    bool confirm(){
        if(!trial.confirm())return false;
        bool ok=catalog().put(trial.address(),trial.value());
        note=ok?"Confirmed cheat saved.":"Confirmed but saving failed.";
        return ok;
    }
    std::string status()const{
        switch(trial.state()){
        case Trial::Idle:return note.empty()?"Choose a candidate and test value.":note;
        case Trial::AwaitUser:return "Did it work? Confirm to save, or Undo.";
        case Trial::Unknown:return "Write outcome uncertain. Undo if safe, or restart.";
        case Trial::Confirmed:return note;
        case Trial::Reverted:return "Original value restored and verified.";
        case Trial::Failed:return "Trial failed or value already equal.";
        default:return "Reading or testing memory...";
        }
    }
};
}
