// AzeezOS AI Cheats: deterministic search over snapshots of emulated RAM.
// No process memory access, writes, network, or AI-generated code execution.
#pragma once
#include <cstdint>
#include <cstddef>
#include <vector>
#include <stdexcept>
#include <limits>
#include <algorithm>
namespace azeez {
enum class Filter { Equal, NotEqual, Changed, Unchanged, Increased, Decreased };
class RamScan {
    uint64_t base_;
    unsigned width_, stride_;
    bool big_;
    std::vector<uint8_t> prev_, candidates_;
    size_t count_=0;
    uint32_t read(const std::vector<uint8_t>& b,size_t at) const {
        uint32_t v=0;
        for(unsigned j=0;j<width_;++j)
            v|=uint32_t(b[at+j]) << (8*(big_?width_-1-j:j));
        return v;
    }
    bool validValue(uint32_t v) const {
        return width_==4 || v < (uint32_t(1)<<(width_*8));
    }
public:
    static constexpr size_t MaxBytes=8*1024*1024;
    RamScan(uint64_t base,std::vector<uint8_t> initial,unsigned width=1,
            bool big=false,unsigned stride=1)
        :base_(base),width_(width),stride_(stride),big_(big),prev_(std::move(initial)) {
        if((width!=1 && width!=2 && width!=4) || !stride ||
           prev_.size()<width || prev_.size()>MaxBytes ||
           base>std::numeric_limits<uint64_t>::max()-(prev_.size()-1))
            throw std::invalid_argument("invalid emulated RAM region");
        count_=(prev_.size()-width_)/stride_+1;
        candidates_.assign(count_,1);
    }
    size_t count() const { return count_; }
    void filter(uint64_t base,const std::vector<uint8_t>& current,Filter f,
                uint32_t value=0) {
        if(base!=base_ || current.size()!=prev_.size())
            throw std::invalid_argument("snapshot region changed");
        if((f==Filter::Equal || f==Filter::NotEqual) && !validValue(value))
            throw std::invalid_argument("value exceeds width");
        auto next=current; // allocate before mutating search state
        for(size_t i=0;i<candidates_.size();++i) {
            if(!candidates_[i]) continue;
            size_t at=i*stride_;
            uint32_t a=read(prev_,at), b=read(current,at);
            bool keep=false;
            switch(f) {
                case Filter::Equal: keep=b==value; break;
                case Filter::NotEqual: keep=b!=value; break;
                case Filter::Changed: keep=b!=a; break;
                case Filter::Unchanged: keep=b==a; break;
                case Filter::Increased: keep=b>a; break;
                case Filter::Decreased: keep=b<a; break;
            }
            if(!keep){ candidates_[i]=0; --count_; }
        }
        prev_.swap(next);
    }
    struct Candidate { uint64_t address; uint32_t value; };
    std::vector<Candidate> results(size_t limit=64) const {
        std::vector<Candidate> out;
        limit=std::min(limit,count_);
        out.reserve(limit);
        for(size_t i=0;i<candidates_.size() && out.size()<limit;++i)
            if(candidates_[i]) out.push_back({base_+i*stride_,read(prev_,i*stride_)});
        return out;
    }
};
}
#ifdef AZEEZ_RAM_SCAN_SELFTEST
#include <cassert>
#include <iostream>
int main(){
    using namespace azeez;
    RamScan lives(0x2000000,{3,3,8,3,9});
    lives.filter(0x2000000,{3,3,8,3,9},Filter::Equal,3);
    assert(lives.count()==3);
    lives.filter(0x2000000,{2,3,7,3,9},Filter::Decreased);
    assert(lives.count()==1 && lives.results()[0].address==0x2000000);
    lives.filter(0x2000000,{1,2,6,2,9},Filter::Changed);
    assert(lives.results()[0].value==1);
    lives.filter(0x2000000,{1,2,6,2,9},Filter::Unchanged);
    assert(lives.count()==1);
    lives.filter(0x2000000,{2,2,6,2,9},Filter::Increased);
    assert(lives.count()==1 && lives.results()[0].value==2);
    lives.filter(0x2000000,{2,2,6,2,9},Filter::NotEqual,2);
    assert(lives.count()==0);
    RamScan le(0x100,{0x34,0x12,0x12,0x34},2,false,2);
    le.filter(0x100,{0x34,0x12,0x12,0x34},Filter::Equal,0x1234);
    assert(le.count()==1 && le.results()[0].address==0x100);
    RamScan be(0x100,{0x34,0x12,0x12,0x34},2,true,2);
    be.filter(0x100,{0x34,0x12,0x12,0x34},Filter::Equal,0x1234);
    assert(be.count()==1 && be.results()[0].address==0x102);
    RamScan wide(0,{0xff,0xff,0xff,0xff},4);
    wide.filter(0,{0xff,0xff,0xff,0xff},Filter::Equal,0xffffffff);
    assert(wide.count()==1 && wide.results()[0].value==0xffffffff);
    bool rejected=false;
    try { le.filter(0x101,{0,0,0,0},Filter::Changed); }
    catch(const std::invalid_argument&){rejected=true;}
    assert(rejected && le.count()==1);
    rejected=false;
    try { RamScan bad(0,{1},4); }
    catch(const std::invalid_argument&){rejected=true;}
    assert(rejected);
    assert(be.results(0).empty());
    std::cout<<"PASS: RAM scan narrowing, 8/16/32-bit values, endian, bounds, region identity\n";
}
#endif
