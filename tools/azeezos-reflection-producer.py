#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1])/"src/kms.c"
s=p.read_text()
anchor="static void on_flip(int fd, unsigned seq, unsigned sec, unsigned usec, void* data)"
code=r"""
/* Sample already mapped producer buffers only while bottom UI requests it.
 * 40x30 at 5Hz; atomic publication to tmpfs, no full-frame copy or GPU readback.
 * Use the CPU source even when a GPU shader is selected to avoid waiting on GPU.
 */
static void az_reflect_publish(void)
{
    static double next;
    double now=bf_now_ms();
    if(now<next)return;
    next=now+200;
    if(!K.leased || access("/run/banana/az-reflect-request",F_OK)!=0 || K.shown<0)return;
    const buf_t* b=&K.b[K.shown];
    if(!b->map || !b->w || !b->h || (b->fmt!=DRM_FORMAT_RGB565 && b->fmt!=DRM_FORMAT_XRGB8888))return;
    uint32_t out[40*30];
    for(unsigned y=0;y<30;y++)for(unsigned x=0;x<40;x++){
        unsigned sx=(2*x+1)*b->w/80, sy=(59-2*y)*b->h/60;
        const uint8_t* row=(const uint8_t*)b->map+(size_t)sy*b->pitch;
        uint32_t v;
        if(b->fmt==DRM_FORMAT_RGB565){
            unsigned p=((const uint16_t*)row)[sx],r=p>>11,g=(p>>5)&63,bl=p&31;
            v=(r*255/31)<<16|(g*255/63)<<8|(bl*255/31);
        }else v=((const uint32_t*)row)[sx];
        out[y*40+x]=0xff000000u|v;
    }
    FILE* f=fopen("/run/banana/az-reflect-frame.tmp","wb");
    if(!f)return;
    size_t n=fwrite(out,1,sizeof out,f);
    int rc=fclose(f);
    if(n==sizeof out && rc==0)rename("/run/banana/az-reflect-frame.tmp","/run/banana/az-reflect-frame");
}
"""
assert s.count(anchor)==1
s=s.replace(anchor,code+"\n"+anchor,1)
anchor="    K.last_flip = bf_now_ms();"
assert s.count(anchor)==1
s=s.replace(anchor,anchor+"\n    az_reflect_publish();",1)
p.write_text(s)
