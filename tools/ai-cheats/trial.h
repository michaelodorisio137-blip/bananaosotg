#pragma once
#include <cstdint>
#include <string>
#include <cstdio>
#include <sstream>
namespace azeez {
// One-shot trial. Caller must restrict addresses to the emulated writable RAM
// range and require an explicit user action. Never use for netplay/hardcore.
class Trial {
public:
    enum State { Idle, ReadOriginal, WriteTrial, VerifyTrial, AwaitUser,
                 ReadUndo, WriteUndo, VerifyUndo, Confirmed, Reverted, Unknown, Failed };
private:
    State state_=Idle;
    uint32_t address_=0;
    unsigned old_=0,value_=0;
    bool haveOld_=false, awaiting_=false;
    double sent_=0;
    std::string partial_;
    void next(State s){state_=s;awaiting_=false;partial_.clear();}
    bool isWrite()const{return state_==WriteTrial||state_==WriteUndo;}
    bool isRead()const{return state_==ReadOriginal||state_==VerifyTrial||state_==ReadUndo||state_==VerifyUndo;}
public:
    State state()const{return state_;}
    uint32_t address()const{return address_;}
    unsigned value()const{return value_;}
    unsigned original()const{return old_;}
    void interrupt(){if(state_==ReadOriginal)next(Failed);else if(state_!=Idle&&state_!=Confirmed&&state_!=Reverted&&state_!=Failed)next(Unknown);}
    bool canSave()const{return state_==Confirmed;}
    bool begin(uint32_t address,unsigned value){
        if(value>255||!(state_==Idle||state_==Confirmed||state_==Reverted||state_==Failed))return false;
        address_=address;value_=value;haveOld_=false;next(ReadOriginal);return true;
    }
    bool confirm(){
        if(state_!=AwaitUser)return false;
        next(Confirmed);return true;
    }
    bool undo(){
        if(!haveOld_||(state_!=AwaitUser&&state_!=Unknown))return false;
        next(ReadUndo);return true;
    }
    std::string request(double now){
        if(!(isWrite()||isRead()))return "";
        if(awaiting_){
            if(now-sent_>2500)next(state_==ReadOriginal?Failed:Unknown);
            return "";
        }
        char b[80];
        if(isWrite())std::snprintf(b,sizeof b,"WRITE_CORE_MEMORY %x %02X\n",address_,state_==WriteTrial?value_:old_);
        else std::snprintf(b,sizeof b,"READ_CORE_MEMORY %x 1\n",address_);
        awaiting_=true;sent_=now;return b;
    }
    void feed(const char* data,size_t n){
        if(!awaiting_)return;
        partial_.append(data,n);
        if(partial_.size()>4096){next(state_==ReadOriginal?Failed:Unknown);return;}
        size_t e;
        while((e=partial_.find('\n'))!=std::string::npos){
            std::string line=partial_.substr(0,e);partial_.erase(0,e+1);
            std::istringstream in(line);std::string tag,a,v,extra;
            if(!(in>>tag>>a))continue;
            if(tag!=(isWrite()?"WRITE_CORE_MEMORY":"READ_CORE_MEMORY"))continue;
            unsigned long addr;
            try{size_t z;addr=std::stoul(a,&z,16);if(z!=a.size())continue;}catch(...){continue;}
            if(addr!=address_)continue;
            if(!(in>>v)||(in>>extra)){next(state_==ReadOriginal?Failed:Unknown);return;}
            if(isWrite()){
                if(v!="1"){next(Unknown);return;}
                next(state_==WriteTrial?VerifyTrial:VerifyUndo);return;
            }
            if(v.size()!=2||v.find_first_not_of("0123456789abcdefABCDEF")!=std::string::npos){next(state_==ReadOriginal?Failed:Unknown);return;}
            unsigned x=unsigned(std::stoul(v,nullptr,16));
            switch(state_){
                case ReadOriginal:
                    if(x==value_){next(Failed);return;} // no observable change, not a test
                    old_=x;haveOld_=true;next(WriteTrial);return;
                case VerifyTrial:next(x==value_?AwaitUser:Unknown);return;
                case ReadUndo:
                    if(x==old_){next(Reverted);return;}
                    if(x!=value_){next(Unknown);return;} // game changed it: don't clobber newer state
                    next(WriteUndo);return;
                case VerifyUndo:next(x==old_?Reverted:Unknown);return;
                default:return;
            }
        }
    }
};
}
