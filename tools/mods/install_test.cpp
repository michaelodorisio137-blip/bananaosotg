#include "install.h"
#include <cassert>
#include <filesystem>
#include <iostream>
using namespace azeez::mods;
static void writeFile(const std::string& p,const Bytes& b){
    std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char*>(b.data()),b.size());assert(f);
}
int main(){
    char dir[]="/tmp/azeez-mod-XXXXXX";assert(mkdtemp(dir));
    std::string src=std::string(dir)+"/original.gba",patch=std::string(dir)+"/mod.ips",dst=std::string(dir)+"/mod.gba";
    Bytes s={1,2,3,4},p={'P','A','T','C','H',0,0,1,0,1,9,'E','O','F'};
    writeFile(src,s);writeFile(patch,p);
    auto a=crc(s,s.size()),b=crc(p,p.size());
    bool rejected=false;try{install(src,patch,dst,a^1,b);}catch(const std::runtime_error&){rejected=true;}
    assert(rejected&&!std::filesystem::exists(dst));
    install(src,patch,dst,a,b);
    assert(readFile(dst)==Bytes({1,9,3,4})&&readFile(src)==s);
    rejected=false;try{install(src,patch,dst,a,b);}catch(const std::runtime_error&){rejected=true;}
    assert(rejected&&readFile(dst)==Bytes({1,9,3,4}));
    std::filesystem::remove_all(dir);
    std::cout<<"PASS: source revision mismatch, successful installation, source preservation, no overwrite\n";
}
