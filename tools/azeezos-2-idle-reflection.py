#!/usr/bin/env python3
"""Low-rate bottom-screen reflection of an existing linear KMS scanout."""
from pathlib import Path
import sys, shutil
base=Path(sys.argv[1])
root=base/"ui/src"
def rep(rel,a,b):
    p=root/rel;s=p.read_text()
    if b in s:return
    if s.count(a)!=1:raise SystemExit("reflection anchor mismatch: "+rel+" "+repr(a))
    p.write_text(s.replace(a,b,1))
# Expose the distinct hardware core through the existing per-system core selector.
# Anchor the existing GBA-specific gpSP entry, preserving default ordering.
rep("settings.cpp",'{ "gpsp", "gpSP" },',
    '{ "gpsp", "gpSP" }, { "mgba_gles_preview", "mGBA Hardware (GLES3 Preview) - Azeez" },')
# Discover every installed libretro core, including those without metadata.
rep("settings.cpp",'\t};\n\tstatic bool coreInstalled(const std::string& core)',r'''
        { "saturn", "Sega Saturn", { { "yabasanshiro", "YabaSanshiro" }, { "mednafen_saturn", "Beetle Saturn" }, { "yabause", "Yabause" }, { "kronos", "Kronos" } } },
        { "psp", "PlayStation Portable", { { "ppsspp_azeez", "PPSSPP Azeez 4:3" }, { "ppsspp", "PPSSPP" } } },
        { "virtualboy", "Virtual Boy", { { "vboycolor", "VBoy Color (Azeez)" }, { "mednafen_vb", "Beetle VB (original / expanded)" } } },
        { "pcengine", "PC Engine", { { "mednafen_pce_fast", "Beetle PCE Fast" } } },
        { "ngpc", "Neo Geo Pocket Color", { { "mednafen_ngp", "Beetle NGP" } } },
    };
    static std::vector<std::string> azInstalledCores()
    {
        std::vector<std::string> out;
        for(const char* path : {"/usr/lib/libretro", "/data/retroarch/cores"}) {
            DIR* d=opendir(path);
            if(!d)continue;
            while(auto* e=readdir(d)){
                std::string n=e->d_name, suffix="_libretro.so";
                if(n.size()<=suffix.size() || n.compare(n.size()-suffix.size(),suffix.size(),suffix)!=0)continue;
                n.resize(n.size()-suffix.size());
                if(n.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_+-.")!=std::string::npos)continue;
                struct stat st={};
                std::string full=std::string(path)+"/"+e->d_name;
                if(stat(full.c_str(),&st)!=0 || !S_ISREG(st.st_mode) || st.st_size==0)continue;
                out.push_back(n);
            }
            closedir(d);
        }
        std::sort(out.begin(),out.end());
        out.erase(std::unique(out.begin(),out.end()),out.end());
        return out;
    }
    static bool coreInstalled(const std::string& core)''')
rep("settings.cpp",'\t\t\tif (coreInstalled(c.first)) { names.push_back(c.second); values.push_back(c.first); }',r'''
            if (coreInstalled(c.first)) { names.push_back(c.second); values.push_back(c.first); }
        names.insert(names.begin(),"Automatic (recommended)");
        values.insert(values.begin(),"auto");
        for(const auto& c:azInstalledCores()){
            if(std::find(values.begin(),values.end(),c)!=values.end())continue;
            names.push_back(c+" (compatibility unverified)");
            values.push_back(c);
        }''')
rep("settings.cpp",'\t\t\tfor (const auto& c : sys.cores) sig += coreInstalled(c.first) ? \'1\' : \'0\';',r'''
            for (const auto& c : sys.cores) sig += coreInstalled(c.first) ? '1' : '0';
        for(const auto& c:azInstalledCores())sig+="|"+c;''')
rep("settings.cpp",'if (names.size() < 2) continue;', 'if (names.empty()) continue;')
# Defaults for fresh settings; the OTA startup migration handles existing cards.
rep("settings_defaults.cpp",'{ "core.gba", "gpsp", CORE, nullptr, 0, 0 },',
    '{ "core.gba", "mgba_gles_preview", CORE, nullptr, 0, 0 },')
rep("kms.h","int leasedScreen() const { return leased; }",
    """int leasedScreen() const { return leased; }
        // Read an existing linear scanout; no new emulator frame or GL readback.
        bool idleReflection(uint32_t* rgba, int w, int h);""")
rep("kms.cpp","#include <xf86drmMode.h>",r"""#include <xf86drmMode.h>
#include <drm_fourcc.h>
#include <linux/dma-buf.h>
#include <sys/ioctl.h>
#include <cstdio>""")
rep("kms.cpp","\tint Display::lease(int s)",r"""
    bool Display::idleReflection(uint32_t* out,int w,int h)
    {
        auto fail=[](const char* why){
            static const char* last=nullptr;
            if(last!=why){fprintf(stderr,"Azeez reflection: %s\n",why);last=why;}
            return false;
        };
        if(fd<0 || leased!=0 || !out || w<=0 || h<=0 || w>80 || h>60)return fail("top panel not leased or invalid dimensions");
        uint32_t plane=primaryPlane(fd,p[0].crtc);
        if(!plane)return fail("no primary plane");
        drmModePlane* pl=drmModeGetPlane(fd,plane);
        if(!pl)return fail("cannot read plane");
        uint32_t fbId=pl->crtc_id==p[0].crtc?pl->fb_id:0;
        drmModeFreePlane(pl);
        if(!fbId)return fail("no active top framebuffer");
        // Do not assume tiled/AFBC layouts or rotate a non-upright plane.
        uint64_t sx=0,sy=0,sw=0,sh=0,rot=DRM_MODE_ROTATE_0;
        auto props=drmModeObjectGetProperties(fd,plane,DRM_MODE_OBJECT_PLANE);
        if(!props)return fail("cannot read plane properties");
        for(unsigned i=0;i<props->count_props;i++){
            auto prop=drmModeGetProperty(fd,props->props[i]);
            if(!prop)continue;
            uint64_t v=props->prop_values[i];
            if(!strcmp(prop->name,"SRC_X"))sx=v;
            if(!strcmp(prop->name,"SRC_Y"))sy=v;
            if(!strcmp(prop->name,"SRC_W"))sw=v;
            if(!strcmp(prop->name,"SRC_H"))sh=v;
            if(!strcmp(prop->name,"rotation"))rot=v;
            drmModeFreeProperty(prop);
        }
        drmModeFreeObjectProperties(props);
        if(rot!=DRM_MODE_ROTATE_0 || ((sx|sy|sw|sh)&65535))return fail("non-upright or fractional source");
        sx>>=16;sy>>=16;sw>>=16;sh>>=16;
        drmModeFB2* f=drmModeGetFB2(fd,fbId);
        if(!f)return fail("GETFB2 unavailable");
        // GETFB2 returns new GEM handles: close every distinct handle, including on failure.
        int dm=-1; bool ok=false; const char* why="unsupported framebuffer layout";
        void* map=MAP_FAILED; size_t bytes=0; bool syncStarted=false;
        unsigned bpp=f->pixel_format==DRM_FORMAT_RGB565?2:
            (f->pixel_format==DRM_FORMAT_XRGB8888 || f->pixel_format==DRM_FORMAT_ARGB8888 ||
             f->pixel_format==DRM_FORMAT_XBGR8888 || f->pixel_format==DRM_FORMAT_ABGR8888)?4:0;
        do {
            if(!bpp || !f->handles[0] || f->handles[1] || f->handles[2] || f->handles[3] ||
               ((f->flags&DRM_MODE_FB_MODIFIERS) && f->modifier!=DRM_FORMAT_MOD_LINEAR) ||
               !sw || !sh || sx+sw>f->width || sy+sh>f->height ||
               f->width>4096 || f->height>4096 ||
               f->pitches[0]<(uint64_t)f->width*bpp)break;
            uint64_t end=(uint64_t)f->offsets[0]+(uint64_t)f->pitches[0]*f->height;
            if(!end || end>128u*1024u*1024u)break;
            bytes=(size_t)end;
            // BananaFront presents DRM dumb buffers. Try their native read-only
            // mapping first (not PRIME export, which some drivers reject).
            // For other linear buffers retain the fenced DMA-BUF path.
            drm_mode_map_dumb dumb={};dumb.handle=f->handles[0];
            if(!drmIoctl(fd,DRM_IOCTL_MODE_MAP_DUMB,&dumb))
                map=mmap(nullptr,bytes,PROT_READ,MAP_SHARED,fd,dumb.offset);
            if(map==MAP_FAILED){
                why="PRIME export failed";
                if(drmPrimeHandleToFD(fd,f->handles[0],DRM_CLOEXEC,&dm))break;
                why="producer busy";
                pollfd pfd={dm,POLLIN,0};
                if(poll(&pfd,1,0)!=1 || !(pfd.revents&POLLIN))break;
                why="DMA-BUF size or mmap failed";
                off_t size=lseek(dm,0,SEEK_END);
                if(size<0 || (uint64_t)size<end)break;
                map=mmap(nullptr,bytes,PROT_READ,MAP_SHARED,dm,0);
                if(map==MAP_FAILED)break;
                why="DMA-BUF read synchronization failed";
                dma_buf_sync ds={DMA_BUF_SYNC_START|DMA_BUF_SYNC_READ};
                if(ioctl(dm,DMA_BUF_IOCTL_SYNC,&ds))break;
                syncStarted=true;
            }
            const uint8_t* base=(const uint8_t*)map+f->offsets[0];
            // Four stratified samples per small pixel; vertically flipped.
            for(int y=0;y<h;y++)for(int x=0;x<w;x++){
                unsigned rr=0,gg=0,bb=0;
                for(int j=0;j<2;j++)for(int i=0;i<2;i++){
                    uint64_t px=sx+((4*x+1+2*i)*sw)/(4*w);
                    uint64_t py=sy+sh-1-((4*y+1+2*j)*sh)/(4*h);
                    const uint8_t* p=base+py*f->pitches[0]+px*bpp;
                    if(bpp==2){
                        uint16_t v;memcpy(&v,p,2);
                        rr+=((v>>11)&31)*255/31;gg+=((v>>5)&63)*255/63;bb+=(v&31)*255/31;
                    }else if(f->pixel_format==DRM_FORMAT_XBGR8888 || f->pixel_format==DRM_FORMAT_ABGR8888){
                        rr+=p[0];gg+=p[1];bb+=p[2];
                    }else{rr+=p[2];gg+=p[1];bb+=p[0];}
                }
                out[y*w+x]=0xff000000u|((rr/4)<<16)|((gg/4)<<8)|(bb/4);
            }
            ok=true;
        }while(false);
        if(syncStarted){dma_buf_sync ds={DMA_BUF_SYNC_END|DMA_BUF_SYNC_READ};ioctl(dm,DMA_BUF_IOCTL_SYNC,&ds);}
        if(map!=MAP_FAILED)munmap(map,bytes);
        if(dm>=0)::close(dm);
        for(unsigned i=0;i<4;i++){
            if(!f->handles[i])continue;
            bool seen=false;for(unsigned j=0;j<i;j++)if(f->handles[j]==f->handles[i])seen=true;
            if(!seen){drm_gem_close g={};g.handle=f->handles[i];drmIoctl(fd,DRM_IOCTL_GEM_CLOSE,&g);}
        }
        drmModeFreeFB2(f);
        return ok ? true : fail(why);
    }

	int Display::lease(int s)""")
# Install the pinned producer-side capture patch for BananaFront.
pkg=base/"buildroot/package/bananafront"
shutil.copyfile(Path(__file__).with_name("azeezos-reflection-producer.py"),pkg/"azeezos-reflection-producer.py")
mk=pkg/"bananafront.mk"
m=mk.read_text()
a="define BANANAFRONT_BUILD_CMDS\n"
assert m.count(a)==1
mk.write_text(m.replace(a,a+"\tpython3 $(BR2_EXTERNAL_BANANA_PATH)/package/bananafront/azeezos-reflection-producer.py $(@D)\n",1))
# Single-screen game panel only; existing idle timer and explicit off mode remain authoritative.
rep("main.cpp","bool linkSeen = false, pipeWarned = false;",r"""bool linkSeen = false, pipeWarned = false;
        bool azReflecting=false, azWakeTouch=false, azRequestedReflection=false;
        unlink("/run/banana/az-reflect-request");
        unlink("/run/banana/az-reflect-frame");
        double azReflectionAt=0;
        const bool azReflectionEnabled=getConfValue(o.data+"/settings.conf","azeez_idle_reflection","on")!="off";
        rnds::TexPtr azReflection;
        auto azCaptureReflection=[&]() {
            constexpr int w=40,h=30;
            uint32_t src[w*h];
            bool producer=false;
            {
                std::ifstream f("/run/banana/az-reflect-frame",std::ios::binary);
                producer=bool(f.read(reinterpret_cast<char*>(src),sizeof src));
            }
            if(!producer && !disp.idleReflection(src,w,h))return false;
            rnds::Bitmap b;b.w=w;b.h=h;b.px.resize(w*h*4);
            // 3x3 low-resolution blur, with a darkening factor; backlight supplies the rest.
            for(int y=0;y<h;y++)for(int x=0;x<w;x++){
                unsigned r=0,g=0,bl=0;
                for(int dy=-1;dy<=1;dy++)for(int dx=-1;dx<=1;dx++){
                    unsigned v=src[std::max(0,std::min(h-1,y+dy))*w+std::max(0,std::min(w-1,x+dx))];
                    r+=(v>>16)&255;g+=(v>>8)&255;bl+=v&255;
                }
                size_t k=(y*w+x)*4;
                b.px[k]=r*3/45;b.px[k+1]=g*3/45;b.px[k+2]=bl*3/45;b.px[k+3]=255;
            }
            azReflection=be.upload(b,true);
            return !!azReflection;
        };""")
rep("main.cpp","\t\t\t\tif (want && !disp.flipPending())\n\t\t\t\t{\n\t\t\t\t\tsettingsView.gameRender();",r"""                const bool azIdle=azReflectionEnabled && panelScreen==1 && bottomIdle.dimmed && bottomIdle.percent>0;
                if(azIdle && !azRequestedReflection){
                    unlink("/run/banana/az-reflect-frame");
                    std::ofstream("/run/banana/az-reflect-request") << "1\n";
                    azRequestedReflection=true;azReflectionAt=0;
                    logf("Azeez reflection: producer requested");
                }
                if(azIdle && t>=azReflectionAt && !disp.flipPending()){
                    bool captured=azCaptureReflection();
                    azReflectionAt=t+(captured?200:1500);
                    if(captured){if(!azReflecting)logf("Azeez reflection: capture active");azReflecting=true;want=true;}
                    else if(azReflecting){azReflecting=false;azReflection.reset();want=true;}
                }
                if(!azIdle){
                    if(azRequestedReflection){
                        unlink("/run/banana/az-reflect-request");
                        unlink("/run/banana/az-reflect-frame");
                        azRequestedReflection=false;
                    }
                    if(azReflecting){azReflecting=false;azReflection.reset();want=true;}
                    azReflectionAt=0;
                }
				if (want && !disp.flipPending())
				{
                    if(azReflecting && azReflection){
                        be.beginScreen(panelScreen);
                        be.draw(azReflection,0,0,disp.width(),disp.height(),rnds::Color(1,1,1,1));
                        be.endScreen();
                    }else settingsView.gameRender();""")
rep("main.cpp","if (settingsView.gameButton(ev.code, nowMs())) want = true;",
    """if (settingsView.gameButton(ev.code, nowMs())) { bottomIdle.activity(nowMs()); want = true; }""")
rep("main.cpp","\t\t\t\t\t\tbottomIdle.activity(nowMs());\n\t\t\t\t\t\tSettings::GameAction a;",r"""                        // First touch wakes the reflection without activating a hidden menu tile.
                        if(azReflecting && ev.type==InputEvent::TOUCH_DOWN){
                            azWakeTouch=true;bottomIdle.activity(nowMs());want=true;return;
                        }
                        if(azWakeTouch && ev.type==InputEvent::TOUCH_UP){
                            azWakeTouch=false;bottomIdle.activity(nowMs());want=true;return;
                        }
						bottomIdle.activity(nowMs());
						Settings::GameAction a;""")
rep("main.cpp","\t\t\t\t\t\t\tsettingsView.gameTouchMove(ev.x, ev.y);",
    "\t\t\t\t\t\t\tif(!azWakeTouch) settingsView.gameTouchMove(ev.x, ev.y);")
rep("main.cpp","if (pidFd >= 0) ::close(pidFd);",r"""unlink("/run/banana/az-reflect-request");
        unlink("/run/banana/az-reflect-frame");
        if (pidFd >= 0) ::close(pidFd);""")
print("Idle reflection integrated: 5 Hz producer tap plus linear scanout fallback.")
