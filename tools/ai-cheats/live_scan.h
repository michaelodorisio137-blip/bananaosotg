#pragma once
#include "ram_scan.h"
#include <cstdio>
#include <sstream>
#include <string>
#include <memory>
namespace azeez {
// A single in-flight request; only fully received snapshots enter the scanner.
class LiveScan {
    uint32_t base_, size_;
    static constexpr uint32_t chunk=256;
    std::vector<uint8_t> bytes_;
    std::unique_ptr<RamScan> scan_;
    std::string partial_;
    bool pending_=false, waiting_=false, fresh_=false;
    double sent_=0;
    Filter filter_=Filter::Changed;
public:
    std::string status="Start a baseline, then change a value in the game.";
    LiveScan(uint32_t base,uint32_t size):base_(base),size_(size){}
    bool busy() const {return pending_;}
    size_t count() const {return scan_?scan_->count():0;}
    bool baseline() const {return bool(scan_);}
    bool changed(){bool v=fresh_;fresh_=false;return v;}
    void start(bool reset,Filter f){
        if(pending_)return;
        if(reset)scan_.reset();
        else if(!scan_)return;
        bytes_.clear();partial_.clear();filter_=f;pending_=true;waiting_=false;
        status="Reading live RAM (non-atomic snapshot)...";fresh_=true;
    }
    void fail(const std::string& reason){
        pending_=waiting_=false;partial_.clear();bytes_.clear();status=reason;fresh_=true;
    }
    std::string request(double now){
        if(!pending_)return "";
        if(waiting_){
            if(now-sent_>2500)fail("Memory read timed out; core may not support it.");
            return "";
        }
        uint32_t at=base_+uint32_t(bytes_.size());
        unsigned n=std::min(chunk,size_-uint32_t(bytes_.size()));
        char b[64];std::snprintf(b,sizeof b,"READ_CORE_MEMORY %x %u\n",at,n);
        waiting_=true;sent_=now;return b;
    }
    void feed(const char* p,size_t n){
        if(!pending_||!waiting_)return;
        partial_.append(p,n);
        if(partial_.size()>65536){fail("Invalid memory reply.");return;}
        size_t end;
        while((end=partial_.find('\n'))!=std::string::npos){
            std::string line=partial_.substr(0,end);partial_.erase(0,end+1);
            std::istringstream s(line);std::string tag,addr,t;
            if(!(s>>tag>>addr)||tag!="READ_CORE_MEMORY")continue;
            unsigned long a;
            try{size_t z;a=std::stoul(addr,&z,16);if(z!=addr.size())continue;}catch(...){continue;}
            if(a!=base_+bytes_.size())continue;
            size_t want=std::min<size_t>(chunk,size_-bytes_.size());
            std::vector<uint8_t> block;
            while(s>>t){
                if(t.size()!=2||t.find_first_not_of("0123456789abcdefABCDEF")!=std::string::npos){fail("Core rejected memory read.");return;}
                block.push_back(uint8_t(std::stoul(t,nullptr,16)));
                if(block.size()>want){fail("Oversized memory reply.");return;}
            }
            if(block.size()!=want){fail("Partial memory region; scan not changed.");return;}
            bytes_.insert(bytes_.end(),block.begin(),block.end());
            waiting_=false;
            if(bytes_.size()==size_){
                if(!scan_)scan_=std::make_unique<RamScan>(base_,std::move(bytes_));
                else scan_->filter(base_,bytes_,filter_);
                pending_=false;bytes_.clear();status=std::to_string(count())+" candidate addresses";fresh_=true;
            }
            return;
        }
    }
    std::vector<RamScan::Candidate> results(size_t n=5)const{
        return scan_?scan_->results(n):std::vector<RamScan::Candidate>{};
    }
};
}
