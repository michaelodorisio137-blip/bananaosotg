#include "cheat_panel.h"
#include <cassert>
#include <iostream>
#include <filesystem>
int main(){
    using namespace azeez;
    char dir[]="/tmp/azeez-catalog-XXXXXX";assert(mkdtemp(dir));
    std::string a(64,'a'),b(64,'b'),c(64,'c');
    Catalog good(dir,a+"-"+b,0xc000,0x2000);
    Catalog other(dir,a+"-"+c,0xc000,0x2000);
    assert(good.ready()&&other.ready());
    assert(good.put(0xc123,99)&&good.put(0xc123,42));
    assert(good.load().size()==1&&good.load()[0].value==42);
    assert(other.load().empty());
    assert(!good.put(0xe000,5)&&!good.put(0xc123,256));
    assert(good.erase(0xc123)&&good.load().empty());
    Catalog bad(dir,"../etc/passwd",0xc000,0x2000);assert(!bad.ready());
    std::ofstream f(std::string(dir)+"/identity");f<<a<<" "<<b<<"\n";f.close();
    assert(sessionKey(std::string(dir)+"/identity")==a+"-"+b);
    Trial t;assert(t.begin(0xc123,99));assert(!t.request(1).empty());
    t.interrupt();assert(t.state()==Trial::Failed);
    std::filesystem::remove_all(dir);
    std::cout<<"PASS: exact core/ROM identity, catalog persistence, bounds, deletion, interrupted trial\n";
}
