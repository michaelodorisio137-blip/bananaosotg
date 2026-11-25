#pragma once
// Bounded native IPS/BPS patch decoder. Returns a new ROM, never changes the source.
#include <vector>
#include <cstdint>
#include <stdexcept>
#include <algorithm>
#include <limits>
#include <zlib.h>
namespace azeez::mods {
using Bytes=std::vector<uint8_t>;
constexpr size_t Limit=128*1024*1024;
inline uint32_t crc(const Bytes& b,size_t n){return uint32_t(crc32(0,b.data(),uInt(n)));}
inline uint32_t le32(const Bytes& b,size_t i){
    if(i>b.size()||b.size()-i<4)throw std::runtime_error("truncated CRC");
    return uint32_t(b[i])|(uint32_t(b[i+1])<<8)|(uint32_t(b[i+2])<<16)|(uint32_t(b[i+3])<<24);
}
inline bool starts(const Bytes& p,const char* s,size_t n){return p.size()>=n&&std::equal(p.begin(),p.begin()+n,s);}
inline Bytes ips(const Bytes& source,const Bytes& p){
    if(!starts(p,"PATCH",5)||source.size()>Limit||p.size()>Limit)throw std::runtime_error("invalid IPS");
    Bytes out=source;size_t i=5;
    auto num=[&](unsigned n){if(i>p.size()||p.size()-i<n)throw std::runtime_error("truncated IPS");size_t x=0;while(n--)x=(x<<8)|p[i++];return x;};
    for(;;){
        if(i+3>p.size())throw std::runtime_error("missing EOF");
        if(p[i]=='E'&&p[i+1]=='O'&&p[i+2]=='F'){
            i+=3;if(p.size()-i==3)out.resize(num(3));
            else if(p.size()!=i)throw std::runtime_error("invalid IPS footer");
            return out;
        }
        size_t at=num(3),n=num(2);
        if(n){
            if(n>p.size()-i||at>Limit-n)throw std::runtime_error("bad IPS range");
            if(at+n>out.size())out.resize(at+n);
            std::copy_n(p.begin()+i,n,out.begin()+at);i+=n;
        }else{
            n=num(2);auto v=num(1);
            if(!n||at>Limit-n)throw std::runtime_error("bad IPS RLE range");
            if(at+n>out.size())out.resize(at+n);
            std::fill_n(out.begin()+at,n,uint8_t(v));
        }
    }
}
inline Bytes bps(const Bytes& source,const Bytes& p){
    if(!starts(p,"BPS1",4)||p.size()<16||source.size()>Limit||p.size()>Limit)throw std::runtime_error("invalid BPS");
    size_t end=p.size()-12,i=4;
    if(le32(p,end)!=crc(source,source.size())||le32(p,end+8)!=crc(p,p.size()-4))throw std::runtime_error("source or patch CRC mismatch");
    auto number=[&](){
        uint64_t x=0,shift=1;
        for(unsigned k=0;k<9;++k){
            if(i>=end)throw std::runtime_error("truncated BPS");
            uint8_t v=p[i++];uint64_t add=uint64_t(v&127)*shift;
            if(x>UINT64_MAX-add)throw std::runtime_error("BPS number overflow");
            x+=add;if(v&128)return x;
            if(shift>UINT64_MAX/128)throw std::runtime_error("BPS number overflow");
            shift*=128;if(x>UINT64_MAX-shift)throw std::runtime_error("BPS number overflow");x+=shift;
        }
        throw std::runtime_error("oversized BPS number");
    };
    uint64_t sn=number(),tn=number(),meta=number();
    if(sn!=source.size()||tn>Limit||meta>end-i)throw std::runtime_error("BPS size mismatch");
    i+=size_t(meta);Bytes out;out.reserve(size_t(tn));int64_t sr=0,tr=0;
    auto relative=[&](int64_t& at){
        auto v=number();if(v>2*Limit)throw std::runtime_error("BPS offset out of bounds");
        at+=(v&1)?-int64_t(v>>1):int64_t(v>>1);
        if(at<0||at>int64_t(Limit))throw std::runtime_error("BPS offset out of bounds");
    };
    while(out.size()<tn){
        uint64_t cmd=number(),n=(cmd>>2)+1;
        if(n>tn-out.size())throw std::runtime_error("BPS output overflow");
        switch(cmd&3){
        case 0:
            if(out.size()>source.size()||n>source.size()-out.size())throw std::runtime_error("BPS source read overflow");
            for(uint64_t k=0;k<n;++k)out.push_back(source[out.size()]);
            break;
        case 1:
            if(n>end-i)throw std::runtime_error("BPS literal overflow");
            out.insert(out.end(),p.begin()+i,p.begin()+i+size_t(n));i+=size_t(n);break;
        case 2:
            relative(sr);
            if(uint64_t(sr)>source.size()||n>source.size()-size_t(sr))throw std::runtime_error("BPS source copy overflow");
            for(uint64_t k=0;k<n;++k)out.push_back(source[size_t(sr++)]);
            break;
        case 3:
            relative(tr);
            for(uint64_t k=0;k<n;++k){
                if(uint64_t(tr)>=out.size())throw std::runtime_error("BPS target copy overflow");
                out.push_back(out[size_t(tr++)]);
            }
            break;
        }
    }
    if(i!=end||le32(p,end+4)!=crc(out,out.size()))throw std::runtime_error("BPS output CRC mismatch");
    return out;
}
inline Bytes apply(const Bytes& source,const Bytes& patch){
    if(starts(patch,"PATCH",5))return ips(source,patch);
    if(starts(patch,"BPS1",4))return bps(source,patch);
    throw std::runtime_error("unsupported patch format");
}
}
