// Included inside banana::nds in overlay.cpp, after the native font helpers.
class AzeezScanPage final : public OverlayPage {
    Overlay& ov;
    banana::CompLink& link;
    std::unique_ptr<azeez::LiveScan> scanner;
    uint32_t start=0,regionSize=0,offset=0,regionSeq=0;
    bool dirty=true,closeAsked=false;
    std::string note="Waiting for BananaDS memory map";
    int X(float x)const{return int(std::lround(x*ov.scale()));}
    void text(rnds::Backend& be,const std::string& s,float sz,int x,int y,Color color){
        int px=0,py=0;
        auto bmp=textA8(s,true,sz,ov.scale(),&px,&py);
        if(!bmp.empty()){
            auto t=be.upload(bmp,true);
            if(t)be.draw(t,float(X(x)-px),float(X(y)-py),float(t->w),float(t->h),color);
        }
    }
    void setWindow(){
        if(offset>=regionSize){scanner.reset();return;}
        scanner=std::make_unique<azeez::LiveScan>(start+offset,std::min(uint32_t(32768),regionSize-offset));
        dirty=true;
    }
public:
    AzeezScanPage(Overlay& o,banana::CompLink& l):ov(o),link(l){}
    void opened()override{dirty=true;}
    bool tick(double now)override{
        if(link.attached()){
            const auto* raw=link.raw();
            auto seq=__atomic_load_n(&raw->regions_seq,__ATOMIC_ACQUIRE);
            if(seq!=regionSeq||!scanner){
                if(!scanner||seq!=regionSeq){
                    start=regionSize=offset=0;
                    for(unsigned i=0;i<std::min(raw->region_count,unsigned(BCOMP_MAX_REGIONS));++i){
                        auto r=raw->regions[i];
                        if((r.flags&BCOMP_R_RAM)&&!(r.flags&(BCOMP_R_ROM|BCOMP_R_IO|BCOMP_R_VRAM|BCOMP_R_SRAM))
                           &&r.size>regionSize&&uint64_t(r.start)+r.size<=0x100000000ULL){
                            start=r.start;regionSize=r.size;
                        }
                    }
                    regionSeq=seq;
                    if(regionSize)setWindow();
                    else if(note!="No readable RAM region"){note="No readable RAM region";dirty=true;}
                }
            }
            if(scanner){
                if(link.waiting()){
                    auto r=link.receive();
                    if(!r.empty())scanner->feed(r.data(),r.size());
                }
                if(!link.waiting()){
                    auto q=scanner->request(now);
                    if(!q.empty()&&!link.send(q))scanner->fail("Memory transport unavailable");
                }
                if(scanner->changed())dirty=true;
            }
        }
        bool result=dirty;dirty=false;return result;
    }
    void touch(const Touch& t)override{
        if(t.type!=Touch::UP)return;
        float x=t.x/ov.scale(),y=t.y/ov.scale();
        if(y<55&&x>440){closeAsked=true;return;}
        if(!scanner||scanner->busy())return;
        if(y>=410){
            if(x<160)scanner->start(true,azeez::Filter::Changed);
            else if(x<320)scanner->start(false,azeez::Filter::Changed);
            else if(x<480)scanner->start(false,azeez::Filter::Decreased);
            else scanner->start(false,azeez::Filter::Increased);
        }else if(y>=350&&y<400){
            if(x<320){if(offset>=32768)offset-=32768;}
            else if(regionSize-offset>32768)offset+=32768;
            setWindow();
        }
        dirty=true;
    }
    bool wantsClose()override{bool c=closeAsked;closeAsked=false;return c;}
    void draw(rnds::Backend& be,int w,int h,const Rect&)override{
        auto p=pal(false);
        be.fill(0,0,float(w),float(h),p.screenBg);
        text(be,"DS live RAM search",24,20,20,p.ink);
        text(be,"Back to game",17,455,20,p.ink);
        if(!scanner){text(be,note,19,20,100,p.ink);return;}
        char line[100];snprintf(line,sizeof line,"Window %08X / %u KiB RAM",start+offset,regionSize/1024);
        text(be,line,18,20,75,p.muted);
        text(be,scanner->status,18,20,105,p.ink);
        text(be,"Read-only, 8-bit candidates",17,20,140,p.muted);
        int y=175;
        for(auto c:scanner->results(5)){
            snprintf(line,sizeof line,"%08llX   %u",(unsigned long long)c.address,c.value);
            text(be,line,20,20,y,p.ink);y+=30;
        }
        auto button=[&](int x,int y,int width,const char* name){
            be.fill(float(X(x)),float(X(y)),float(X(width)),float(X(42)),p.panelBody);
            text(be,name,17,x+8,y+12,p.ink);
        };
        button(8,350,305,"Previous window");button(325,350,305,"Next window");
        const char* names[]={"Baseline","Changed","Decreased","Increased"};
        for(int i=0;i<4;++i)button(8+i*160,425,150,names[i]);
    }
};
