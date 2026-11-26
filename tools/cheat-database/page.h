#pragma once
#include <filesystem>
#include <fstream>
#include <map>
#include <vector>
#include <string>
#include <algorithm>
#include <cstdio>
#include <cstdint>
namespace azdb {
namespace fs=std::filesystem;
inline std::string trim(std::string s){
    auto a=s.find_first_not_of(" \t\r\n"),b=s.find_last_not_of(" \t\r\n");
    if(a==std::string::npos)return {};
    s=s.substr(a,b-a+1);if(s.size()>=2&&s.front()=='"'&&s.back()=='"')s=s.substr(1,s.size()-2);
    return s;
}
inline const char* folder(const std::string& s){
    static const std::map<std::string,const char*> m={
        {"gb","Nintendo - Game Boy"},{"gbc","Nintendo - Game Boy Color"},{"gba","Nintendo - Game Boy Advance"},
        {"nes","Nintendo - Nintendo Entertainment System"},{"snes","Nintendo - Super Nintendo Entertainment System"},
        {"megadrive","Sega - Mega Drive - Genesis"},{"n64","Nintendo - Nintendo 64"},{"psx","Sony - PlayStation"},
        {"nds","Nintendo - Nintendo DS"},{"psp","Sony - PlayStation Portable"},{"dreamcast","Sega - Dreamcast"},
        {"saturn","Sega - Saturn"},{"sms","Sega - Master System - Mark III"},{"gamegear","Sega - Game Gear"},
        {"segacd","Sega - Mega-CD - Sega CD"},{"sega32x","Sega - 32X"},{"pce","NEC - PC Engine - TurboGrafx 16"},
        {"zxspectrum","Sinclair - ZX Spectrum +3"},{"arcade","FBNeo - Arcade Games"}};
    auto it=m.find(s);return it==m.end()?nullptr:it->second;
}
struct Row { std::string desc,code; bool enabled=false; unsigned handler=0; };
struct Page {
    std::vector<fs::path> files;
    std::vector<Row> rows;
    std::map<std::string,std::string> fields;
    std::string status,rom,system;
    fs::path chosen;
    size_t offset=0;
    bool fileView=true;
    void open(const std::string& s,const std::string& r){
        *this=Page{};system=s;rom=r;
        const char* f=folder(s);
        if(!f){status="No database for this system";return;}
        std::string name=fs::path(r).stem().string();
        if(name.empty()){status="No running game";return;}
        std::error_code ec;
        for(fs::directory_iterator it(fs::path("/usr/share/libretro/cheats")/f,ec),end;!ec&&it!=end;it.increment(ec)){
            if(!it->is_regular_file(ec)||it->path().extension()!=".cht")continue;
            auto n=it->path().stem().string();
            if(n==name || n.rfind(name+" (",0)==0)files.push_back(it->path());
        }
        std::sort(files.begin(),files.end());
        status=files.empty()?"No exact filename match; region/revision is not guessed.":"Select matching region and code format.";
    }
    fs::path saved() const{
        uint64_t h=14695981039346656037ull;
        for(unsigned char c:system+"\n"+rom+"\n"+chosen.string()){h^=c;h*=1099511628211ull;}
        return fs::path("/data/banana/cheat-selections")/(std::to_string(h)+".cht");
    }
    bool select(size_t i){
        if(i>=files.size())return false;
        chosen=files[i];fields.clear();rows.clear();offset=0;
        std::ifstream in(chosen);std::string l;
        size_t count=0;
        while(std::getline(in,l)&&count++<100000){
            auto e=l.find('=');if(e==std::string::npos)continue;
            auto k=trim(l.substr(0,e));auto v=trim(l.substr(e+1));
            if(k=="cheats"||k.rfind("cheat",0)==0)fields[k]=v;
        }
        unsigned n=0;try{n=std::stoul(fields.at("cheats"));}catch(...){return false;}
        if(!n||n>4096)return false;
        rows.resize(n);
        for(unsigned j=0;j<n;j++){
            auto k="cheat"+std::to_string(j)+"_";
            rows[j].desc=fields[k+"desc"];rows[j].code=fields[k+"code"];
            try{if(fields.count(k+"handler"))rows[j].handler=std::stoul(fields[k+"handler"]);}catch(...){rows[j].handler=99;}
            if(rows[j].desc.empty())rows[j].desc="Cheat "+std::to_string(j+1);
            fields[k+"enable"]="false";
        }
        // Restore selections only; explicit Apply is still required every session.
        std::ifstream pref(saved());
        while(std::getline(pref,l)){
            auto e=l.find('=');if(e==std::string::npos)continue;
            auto k=trim(l.substr(0,e));if(k.size()<8||k.substr(k.size()-7)!="_enable")continue;
            if(fields.count(k)&&trim(l.substr(e+1))=="true"){
                try{auto j=std::stoul(k.substr(5));if(j<rows.size())rows[j].enabled=true;}catch(...){}
            }
        }
        fileView=false;status="Tap cheats, then Apply. Confirm matching game revision.";
        return true;
    }
    bool write(){
        if(chosen.empty()||rows.empty())return false;
        std::error_code ec;fs::create_directories(saved().parent_path(),ec);
        auto emit=[&](const fs::path& p){
            auto temp=p;temp+=".tmp";
            std::ofstream out(temp,std::ios::trunc);
            for(size_t j=0;j<rows.size();++j)fields["cheat"+std::to_string(j)+"_enable"]=rows[j].enabled?"true":"false";
            for(const auto& kv:fields){
                if(kv.first.find_first_of("\r\n\"")!=std::string::npos||kv.second.find_first_of("\r\n\"")!=std::string::npos)continue;
                out<<kv.first<<" = \""<<kv.second<<"\"\n";
            }
            out.close();if(!out)return false;
            std::error_code err;fs::rename(temp,p,err);return !err;
        };
        return emit(saved())&&emit("/run/banana/azeez-db-active.cht");
    }
};
}
