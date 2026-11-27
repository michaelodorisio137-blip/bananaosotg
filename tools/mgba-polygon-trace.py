#!/usr/bin/env python3
"""Opt-in live CRIS candidate entry/return capture. No CPU instructions replaced."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
def rep(rel,a,b):
    p=root/rel;s=p.read_text()
    if s.count(a)!=1:raise SystemExit("polygon trace anchor mismatch: "+rel+" "+repr(a))
    p.write_text(s.replace(a,b,1))
p="src/arm/arm.c"
rep(p,"void ARMRun(struct ARMCore* cpu) {",r"""
/* Leave the normal ARMRunLoop completely unchanged unless tracing is active. */
void (*azPolygonTraceHook)(struct ARMCore*,uint32_t);
static void azPolygonTraceStep(struct ARMCore* cpu) {
    uint32_t pc=cpu->gprs[ARM_PC]-(cpu->executionMode==MODE_THUMB?2:4);
    azPolygonTraceHook(cpu,pc);
}
void ARMRun(struct ARMCore* cpu) {""")
rep(p,"\tif (cpu->executionMode == MODE_THUMB) {\n\t\tThumbStep(cpu);",
    "\tif (azPolygonTraceHook) azPolygonTraceStep(cpu);\n\tif (cpu->executionMode == MODE_THUMB) {\n\t\tThumbStep(cpu);")
rep(p,"void ARMRunLoop(struct ARMCore* cpu) {",r"""void ARMRunLoop(struct ARMCore* cpu) {
    if (azPolygonTraceHook) {
        if(cpu->executionMode==MODE_THUMB) {
            while(cpu->cycles<cpu->nextEvent){azPolygonTraceStep(cpu);ThumbStep(cpu);}
        } else {
            while(cpu->cycles<cpu->nextEvent){azPolygonTraceStep(cpu);ARMStep(cpu);}
        }
        cpu->irqh.processEvents(cpu);
        return;
    }""")
p="src/platform/libretro/libretro.c"
rep(p,"static struct mCore* core;\n","static struct mCore* core;\n"+r"""
#include <mgba/internal/arm/arm.h>
#include <stdio.h>
extern void (*azPolygonTraceHook)(struct ARMCore*,uint32_t);
static FILE* azTrace;
static uint32_t azTraceSites[3],azTraceFrame,azTraceCount[3];
static struct { uint32_t pc,sp,site; uint32_t ptr[4]; } azReturn[16];
static unsigned azDepth;
static bool azTraceRam(uint32_t a) {
    return (a>=0x02000000 && a<=0x0203ffe0) ||
           (a>=0x03000000 && a<=0x03007fe0);
}
static void azTraceMemory(uint32_t addr) {
    if(!azTraceRam(addr)){fputs(",-",azTrace);return;}
    fputc(',',azTrace);
    for(unsigned i=0;i<32;i++)fprintf(azTrace,"%02x",(unsigned)core->rawRead8(core,addr+i,-1)&255);
}
static void azTraceRecord(struct ARMCore* c,uint32_t pc,unsigned site,bool ret,const uint32_t* args) {
    fprintf(azTrace,"%u,%s,%u,%08x,%08x,%u",azTraceFrame,ret?"return":"entry",site,
            (unsigned)pc,(unsigned)c->prefetch[0],c->executionMode==MODE_THUMB);
    for(unsigned i=0;i<16;i++)fprintf(azTrace,",%08x",(unsigned)c->gprs[i]);
    for(unsigned i=0;i<4;i++)azTraceMemory(args[i]);
    azTraceMemory(c->gprs[ARM_SP]);
    fputc('\n',azTrace);
}
static void azTraceCPU(struct ARMCore* c,uint32_t pc) {
    if(azDepth && pc==azReturn[azDepth-1].pc && (uint32_t)c->gprs[ARM_SP]==azReturn[azDepth-1].sp) {
        --azDepth;
        azTraceRecord(c,pc,azReturn[azDepth].site,true,azReturn[azDepth].ptr);
    }
    for(unsigned i=0;i<3;i++) {
        if(pc!=azTraceSites[i] || azTraceCount[i]>=128)continue;
        ++azTraceCount[i];
        uint32_t args[4];
        for(unsigned j=0;j<4;j++)args[j]=c->gprs[j];
        azTraceRecord(c,pc,i,false,args);
        if(azDepth<16) {
            azReturn[azDepth].pc=c->gprs[ARM_LR]&~1u;
            azReturn[azDepth].sp=c->gprs[ARM_SP];
            azReturn[azDepth].site=i;
            memcpy(azReturn[azDepth].ptr,args,sizeof(args));
            ++azDepth;
        }
        break;
    }
}
static void azTraceStop(void) {
    azPolygonTraceHook=NULL;
    if(azTrace)fclose(azTrace);
    azTrace=NULL;azDepth=0;
}
static void azTraceStart(void) {
    azTraceStop();
    if(core->platform(core)!=mPLATFORM_GBA)return;
    /* Explicit selection: candidate ROM offsets are NOT verified entrypoints. */
    FILE* marker=fopen("/data/banana/gba-3d-trace.enable","r");
    if(!marker)return;
    char profile[32]={0};
    int read=fscanf(marker,"%31s",profile);
    fclose(marker);
    if(read!=1)return;
    if(!strcmp(profile,"tgr")) {
        azTraceSites[0]=0x080048c8;azTraceSites[1]=0x08004998;azTraceSites[2]=0x080061e4;
    } else if(!strcmp(profile,"mtm")) {
        azTraceSites[0]=0x080044a0;azTraceSites[1]=0x08004570;azTraceSites[2]=0x08005d7c;
    } else return;
    azTrace=fopen("/data/banana/gba-3d-trace.csv","w");
    if(!azTrace)return;
    uint32_t crc=0;core->checksum(core,&crc,mCHECKSUM_CRC32);
    fprintf(azTrace,"# profile=%s crc32=%08x romcode=",profile,(unsigned)crc);
    for(unsigned i=0;i<4;i++)fprintf(azTrace,"%02x",(unsigned)core->rawRead8(core,0x080000ac+i,-1)&255);
    fputs("\n# candidate sites only; actual ABI and polygon role not yet verified\n",azTrace);
    fputs("frame,event,site,pc,opcode,thumb,r0,r1,r2,r3,r4,r5,r6,r7,r8,r9,r10,r11,r12,sp,lr,pc_prefetch,arg0_ram,arg1_ram,arg2_ram,arg3_ram,stack_ram\n",azTrace);
    azDepth=0;azTraceFrame=0;memset(azTraceCount,0,sizeof(azTraceCount));
    azPolygonTraceHook=azTraceCPU;
}
static void azTraceTick(void) {
    if(!azTrace)return;
    ++azTraceFrame;
    fflush(azTrace);
    if(azTraceFrame>=3600 || (azTraceCount[0]>=128 && azTraceCount[1]>=128 && azTraceCount[2]>=128 && !azDepth))azTraceStop();
}
""")
# Apply BEFORE the GLES bridge, whose source anchors include these lines.
rep(p,"\tcore->loadROM(core, rom);\n\tdeferredSetup = true;","\tcore->loadROM(core, rom);\n\tdeferredSetup = true;\n\tazTraceStart();")
rep(p,"\tcore->runFrame(core);","\tcore->runFrame(core);\n\tazTraceTick();")
rep(p,"void retro_unload_game(void) {\n","void retro_unload_game(void) {\n\tazTraceStop();\n")
print("Live read-only CRIS candidate trace installed; normal rendering unchanged.")
