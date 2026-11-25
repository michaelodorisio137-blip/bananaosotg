#include "live_scan.h"
#include <cassert>
#include <iostream>
static std::string reply(unsigned address,unsigned n,unsigned first,unsigned other){
    char a[32];std::snprintf(a,sizeof a,"READ_CORE_MEMORY %x",address);
    std::string s=a;
    for(unsigned i=0;i<n;i++){char b[5];std::snprintf(b,sizeof b," %02X",i?other:first);s+=b;}
    return s+"\n";
}
int main(){
    using namespace azeez;
    LiveScan scan(0x100,260);
    scan.start(true,Filter::Changed);
    assert(scan.request(0)=="READ_CORE_MEMORY 100 256\n");
    auto r=reply(0x100,256,5,9);
    scan.feed(r.data(),10);
    assert(scan.busy() && scan.request(1).empty());
    scan.feed(r.data()+10,r.size()-10);
    assert(scan.request(2)=="READ_CORE_MEMORY 200 4\n");
    r=reply(0x200,4,9,9);scan.feed(r.data(),r.size());
    assert(!scan.busy() && scan.count()==260);
    scan.start(false,Filter::Decreased);
    assert(!scan.request(3).empty());
    r=reply(0x100,256,4,9);scan.feed(r.data(),r.size());
    assert(!scan.request(4).empty());
    r=reply(0x200,4,9,9);scan.feed(r.data(),r.size());
    assert(scan.count()==1 && scan.results()[0].address==0x100);
    scan.start(false,Filter::Changed);
    assert(!scan.request(5).empty());
    r="READ_CORE_MEMORY 100 -1 no memory map\n";scan.feed(r.data(),r.size());
    assert(!scan.busy() && scan.count()==1);
    scan.start(false,Filter::Changed);
    assert(!scan.request(6).empty());
    assert(scan.request(3000).empty() && !scan.busy() && scan.count()==1);
    std::cout<<"PASS: fragmented replies, multi-chunk snapshots, filtering, error and timeout preservation\n";
}
