#!/usr/bin/env python3
from pathlib import Path
import sys,shutil
root=Path(sys.argv[1])
def edit(path,a,b):
 p=root/path;s=p.read_text()
 if s.count(a)!=1:raise SystemExit(f"anchor mismatch {path}: {a!r}")
 p.write_text(s.replace(a,b,1))
edit("CMakeLists.txt","PRIVATE BUILD_GLES3)","PRIVATE BUILD_GLES3 AZ_MOBIUS_CAPTURE)")
p="src/arm/arm.c"
edit(p,"static inline void ARMStep(struct ARMCore* cpu) {", """#ifdef AZ_MOBIUS_CAPTURE
extern void azMobiusHit(uint32_t ctx);
#endif
static inline void ARMStep(struct ARMCore* cpu) {
#ifdef AZ_MOBIUS_CAPTURE
    if (cpu->prefetch[0]==0xe92d4ff0u && cpu->prefetch[1]==0xe24ddc01u)
        azMobiusHit((uint32_t)cpu->gprs[0]);
#endif""")
p="src/platform/libretro/libretro.c"
shutil.copyfile(Path(__file__).with_name("mobius.h"),root/"src/platform/libretro/mobius.h")
edit(p,"static struct mCore* core;\n","static struct mCore* core;\n#include \"mobius.h\"\n")
edit(p,"mGBA Hardware RGDS (Experimental)","mGBA Mobius HLE Prototype")
edit(p,"static void azContextDestroy(void) {","static void azContextDestroy(void) {\n    mobDestroyGL();")
edit(p,"videoCallback(RETRO_HW_FRAME_BUFFER_VALID,w,h,0);","mobDraw(w,h);\n        videoCallback(RETRO_HW_FRAME_BUFFER_VALID,w,h,0);")
edit(p,"core->loadROM(core, rom);","core->loadROM(core, rom);\n    mobReset();")
edit(p,"core->runFrame(core);", """if (mobEnabled) {
        bool chord=inputCallback(0,RETRO_DEVICE_JOYPAD,0,RETRO_DEVICE_ID_JOYPAD_SELECT)
            && inputCallback(0,RETRO_DEVICE_JOYPAD,0,RETRO_DEVICE_ID_JOYPAD_L)
            && inputCallback(0,RETRO_DEVICE_JOYPAD,0,RETRO_DEVICE_ID_JOYPAD_R);
        if(chord&&!mobHeld) {mobOverlay=!mobOverlay; if(logCallback)logCallback(RETRO_LOG_INFO,"Mobius experimental overlay %s\\n",mobOverlay?"ON":"OFF");}
        mobHeld=chord;mobCount=0;
    }
    core->runFrame(core);""")
print("Mobius prototype: live ARM hook, original rasterizer retained, opt-in GLES3 polygon overlay, N64-style three-point sampler.")
