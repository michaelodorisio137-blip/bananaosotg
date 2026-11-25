#pragma once
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <sys/stat.h>
#include <unistd.h>
namespace azeez {
struct SavedCheat { uint32_t address; unsigned value; };
inline bool digest(const std::string& s){
    return s.size()==64 && s.find_first_not_of("0123456789abcdef")==std::string::npos;
}
inline std::string sessionKey(const std::string& path){
    std::ifstream f(path);std::string rom,core,extra;
    if(!(f>>rom>>core)||(f>>extra)||!digest(rom)||!digest(core))return "";
    return rom+"-"+core;
}
class Catalog {
    std::string file_;
    uint32_t base_,size_;
    bool valid(uint32_t a,unsigned v)const{return a>=base_&&a-base_<size_&&v<=255;}
public:
    Catalog(const std::string& data,const std::string& key,uint32_t base,uint32_t size):base_(base),size_(size){
        if(key.size()!=129||key[64]!='-'||!digest(key.substr(0,64))||!digest(key.substr(65)))return;
        std::string dir=data+"/confirmed-cheats";
        mkdir(dir.c_str(),0700);
        struct stat st{};
        if(lstat(dir.c_str(),&st)||!S_ISDIR(st.st_mode))return;
        file_=dir+"/"+key+".txt";
    }
    bool ready()const{return !file_.empty();}
    std::vector<SavedCheat> load()const{
        std::vector<SavedCheat> out;
        if(!ready())return out;
        std::ifstream f(file_);
        std::string line;
        while(out.size()<64 && std::getline(f,line)){
            if(line.size()>100)break;
            std::istringstream s(line);unsigned long long a;unsigned v;std::string extra;
            if((s>>std::hex>>a>>std::dec>>v)&&!(s>>extra)&&a<=UINT32_MAX&&valid(uint32_t(a),v))
                out.push_back({uint32_t(a),v});
        }
        return out;
    }
    bool put(uint32_t a,unsigned v){
        if(!ready()||!valid(a,v))return false;
        auto rows=load();
        auto it=std::find_if(rows.begin(),rows.end(),[&](auto c){return c.address==a;});
        if(it!=rows.end())it->value=v;
        else if(rows.size()<64)rows.push_back({a,v});
        else return false;
        return writeRows(rows);
    }
    bool erase(uint32_t a){
        if(!ready())return false;
        auto rows=load();auto n=rows.size();
        rows.erase(std::remove_if(rows.begin(),rows.end(),[&](auto c){return c.address==a;}),rows.end());
        return rows.size()!=n&&writeRows(rows);
    }
private:
    bool writeRows(const std::vector<SavedCheat>& rows){
        std::ostringstream s;
        for(auto c:rows)s<<std::hex<<c.address<<" "<<std::dec<<c.value<<"\n";
        auto contents=s.str();std::string temp=file_+".XXXXXX";
        int fd=mkstemp(&temp[0]);if(fd<0)return false;
        size_t at=0;
        while(at<contents.size()){
            auto n=write(fd,contents.data()+at,contents.size()-at);
            if(n<=0)break;
            at+=size_t(n);
        }
        bool ok=at==contents.size()&&fsync(fd)==0;
        if(close(fd))ok=false;
        if(ok&&rename(temp.c_str(),file_.c_str())==0)return true;
        unlink(temp.c_str());return false;
    }
};
}
