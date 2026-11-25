#include "patch.h"
#include <cassert>
#include <iostream>
using namespace azeez::mods;
static void le(Bytes& p,uint32_t n){for(int i=0;i<4;i++)p.push_back(uint8_t(n>>(8*i)));}
static void number(Bytes& p,uint64_t n){for(;;){auto x=uint8_t(n&127);n>>=7;if(!n){p.push_back(x|128);break;}p.push_back(x);--n;}}
static bool rejects(const Bytes& src,const Bytes& p){try{azeez::mods::apply(src,p);return false;}catch(const std::runtime_error&){return true;}}
int main(){
    Bytes src={1,2,3,4},p={'P','A','T','C','H',0,0,1,0,1,9,'E','O','F'};
    assert(azeez::mods::apply(src,p)==Bytes({1,9,3,4}));assert(src==Bytes({1,2,3,4}));
    Bytes rle={'P','A','T','C','H',0,0,2,0,0,0,3,7,'E','O','F'};
    assert(azeez::mods::apply(src,rle)==Bytes({1,2,7,7,7}));rle.pop_back();assert(rejects(src,rle));
    Bytes target={1,9,3,4,9,3,4};Bytes b={'B','P','S','1'};
    number(b,src.size());number(b,target.size());number(b,0);
    number(b,0);number(b,1);b.push_back(9);number(b,4|2);number(b,4); // source copy 2 from offset 2
    number(b,8|3);number(b,2); // target copy 3 from offset 1
    le(b,crc(src,src.size()));le(b,crc(target,target.size()));le(b,crc(b,b.size()));
    assert(azeez::mods::apply(src,b)==target);
    assert(rejects(Bytes({2,2,3,4}),b));b.back()^=1;assert(rejects(src,b));
    std::cout<<"PASS: IPS literal/RLE, BPS source/target copy, CRC and malformed patch rejection\n";
}
