#pragma once
#include "azeezos_ai_cheats.h"
#include "install.h"
#include <cctype>
namespace banana::azmods {
using namespace azeez::mods;
struct Candidate {std::string name,url;};
inline bool patchUrl(const std::string& u){
    const std::string prefix="https://raw.githubusercontent.com/";
    if(u.compare(0,prefix.size(),prefix)||u.size()>1024||u.size()<prefix.size()+10||u.substr(u.size()-4)!=".bps")return false;
    for(size_t i=prefix.size();i<u.size();++i){
        unsigned char c=u[i];if(!(std::isalnum(c)||c=='/'||c=='-'||c=='_'||c=='.'))return false;
    }
    return u.find("/../",prefix.size())==std::string::npos&&u.find("//",prefix.size())==std::string::npos;
}
inline std::vector<Candidate> parse(const std::string& text){
    std::istringstream in(text);std::string line;std::vector<Candidate> out;
    while(out.size()<8&&std::getline(in,line)){
        auto sep=line.find('|');if(sep==std::string::npos)continue;
        auto name=line.substr(0,sep),url=line.substr(sep+1);
        if(name.empty()||name.size()>80||!patchUrl(url))continue;
        if(std::none_of(out.begin(),out.end(),[&](const Candidate& c){return c.url==url;}))out.push_back({name,url});
    }
    return out;
}
inline size_t downloadBody(char* p,size_t sz,size_t n,void* user){
    auto& b=*static_cast<Bytes*>(user);
    constexpr size_t cap=16*1024*1024;
    if(sz&&n>cap/sz)return 0;
    size_t len=sz*n;if(len>cap-b.size())return 0;
    try{b.insert(b.end(),p,p+len);}catch(...){return 0;}return len;
}
inline Bytes download(const std::string& url){
    if(!patchUrl(url))throw std::runtime_error("Only direct GitHub raw BPS patch URLs supported");
    Curl c;if(!c.load())throw std::runtime_error("HTTPS unavailable");
    void* h=c.init();if(!h)throw std::runtime_error("HTTPS initialization failed");
    Bytes body;
    c.setopt(h,10002,url.c_str());c.setopt(h,10001,&body);c.setopt(h,20011,downloadBody);
    c.setopt(h,13,60L);c.setopt(h,78,15L);c.setopt(h,99,1L);c.setopt(h,64,1L);c.setopt(h,81,2L);
    c.setopt(h,52,0L);
    long status=0;int rc=c.perform(h);c.getinfo(h,0x200002,&status);c.cleanup(h);
    if(rc||status!=200)throw std::runtime_error("Patch download failed (HTTP "+std::to_string(status)+")");
    return body;
}
struct Job{
    std::mutex lock;
    bool done=false,ok=false;
    std::string message,path;
    std::vector<Candidate> rows;
};
inline std::shared_ptr<Job> search(std::string rom,std::string game,std::string prompt){
    auto j=std::make_shared<Job>();
    std::thread([j,rom,game,prompt]{
        std::vector<Candidate> rows;std::string err;
        try{
            auto id=aicheat::fingerprint(rom);
            if(id.empty())throw std::runtime_error("Cannot read game file");
            auto text=aicheat::online("Find legally distributed BPS ROM patches for "+game+" file CRC32-size "+id+
                ". Desired mod: "+prompt+". Return up to eight lines, each exactly NAME|https://raw.githubusercontent.com/owner/repo/ref/path.bps . "
                "Only actual direct BPS patch URLs verified from sources; no ROM downloads, ZIP files, invented links or prose.",err);
            rows=parse(text);if(rows.empty()&&err.empty())err="No supported direct BPS patches found.";
        }catch(const std::exception& e){err=e.what();}
        std::lock_guard<std::mutex> g(j->lock);j->rows=std::move(rows);j->ok=!j->rows.empty();j->message=j->ok?"Select patch; inspect source before installing.":err;j->done=true;
    }).detach();return j;
}
inline std::shared_ptr<Job> installPatch(std::string rom,Candidate c){
    auto j=std::make_shared<Job>();
    std::thread([j,rom,c]{
        std::string err,path;
        try{
            auto dot=rom.find_last_of('.');if(dot==std::string::npos||rom.find_first_of("\r\n")!=std::string::npos)throw std::runtime_error("Unsupported filename");
            auto ext=rom.substr(dot);std::transform(ext.begin(),ext.end(),ext.begin(),[](unsigned char x){return std::tolower(x);});
            if(ext!=".gba"&&ext!=".gb"&&ext!=".gbc"&&ext!=".nes"&&ext!=".sfc"&&ext!=".smc"&&ext!=".nds"&&ext!=".z64"&&ext!=".md")throw std::runtime_error("Uncompressed ROM required");
            auto p=download(c.url);if(!starts(p,"BPS1",4)||p.size()<16)throw std::runtime_error("Not a BPS patch");
            uint32_t source=le32(p,p.size()-12),patchCRC=crc(p,p.size());
            std::string tmp="/run/banana/azeez-mod-XXXXXX";int fd=mkstemp(&tmp[0]);
            if(fd<0)throw std::runtime_error("Cannot stage patch");
            size_t at=0;while(at<p.size()){auto n=write(fd,p.data()+at,p.size()-at);if(n<=0)break;at+=size_t(n);}
            int closeResult=close(fd);
            try{
                if(at!=p.size()||closeResult)throw std::runtime_error("Patch staging failed");
                char id[12];snprintf(id,sizeof id,"%08x",patchCRC);
                std::string dst=rom.substr(0,dot)+" (Mod "+id+")"+rom.substr(dot);
                azeez::mods::install(rom,tmp,dst,source,patchCRC);path=dst;
            }catch(...){unlink(tmp.c_str());throw;}
            unlink(tmp.c_str());
        }catch(const std::exception& e){err=e.what();}
        std::lock_guard<std::mutex> g(j->lock);j->ok=!path.empty();j->path=path;j->message=j->ok?"Installed as separate ROM. Original preserved.":err;j->done=true;
    }).detach();return j;
}
}
