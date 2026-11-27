#!/usr/bin/env python3
"""Experimental Switch-style mGBA GLES3 libretro bridge, separate from stock."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
def rep(rel,a,b):
    p=root/rel
    s=p.read_text()
    if s.count(a)!=1: raise SystemExit("GPU anchor mismatch: "+rel+" "+repr(a))
    p.write_text(s.replace(a,b,1))

rep("CMakeLists.txt",
    'target_link_libraries(${BINARY_NAME}_libretro ${OS_LIB})'.replace('\\',''),
    '''target_link_libraries(${BINARY_NAME}_libretro ${OS_LIB})
    find_library(AZ_GLES_LIBRARY NAMES GLESv2 REQUIRED)
    target_compile_definitions(${BINARY_NAME}_libretro PRIVATE BUILD_GLES3)
    target_link_libraries(${BINARY_NAME}_libretro ${AZ_GLES_LIBRARY})'''.replace('\\',''))
p="src/platform/libretro/libretro.c"
rep(p,'#include "libretro.h"','#include "libretro.h"\n#include <GLES3/gl3.h>')
rep(p,"static struct mCore* core;\n","static struct mCore* core;\n"+r'''
/* A distinct opt-in hardware core. The existing software viewport core is
 * untouched. GPU texture is owned by this bridge, never read back per frame.
 * Expanded surroundings are a separate renderer task, not simulated here. */
static struct retro_hw_render_callback azHW;
static GLuint azTex, azReadFbo;
static bool azRequested, azActive, azStarted;
static void azContextDestroy(void) {
    if (azActive && core) {
        mCoreConfigSetIntValue(&core->config,"hwaccelVideo",0);
        if (azStarted) core->reloadConfigOption(core,"hwaccelVideo",NULL);
        core->setVideoGLTex(core,(unsigned)-1);
    }
    if (azReadFbo) glDeleteFramebuffers(1,&azReadFbo);
    if (azTex) glDeleteTextures(1,&azTex);
    azReadFbo=azTex=0;
    azActive=false;
}
static void azContextReset(void) {
    if (!core || !azRequested) return;
    glGenTextures(1,&azTex);
    glGenFramebuffers(1,&azReadFbo);
    if (!azTex || !azReadFbo) { azContextDestroy(); return; }
    core->setVideoGLTex(core,azTex);
    mCoreConfigSetIntValue(&core->config,"videoScale",2);
    mCoreConfigSetIntValue(&core->config,"hwaccelVideo",1);
    azActive=true;
    if (azStarted) core->reloadConfigOption(core,"hwaccelVideo",NULL);
}
static void azPresent(void) {
    GLuint target=(GLuint)azHW.get_current_framebuffer();
    glDisable(GL_SCISSOR_TEST);
    glDisable(GL_BLEND);
    glDisable(GL_DEPTH_TEST);
    glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER,target);
    glViewport(0,0,640,480);
    glClearColor(0,0,0,1);
    glClear(GL_COLOR_BUFFER_BIT);
    glBindFramebuffer(GL_READ_FRAMEBUFFER,azReadFbo);
    glFramebufferTexture2D(GL_READ_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,azTex,0);
    if (glCheckFramebufferStatus(GL_READ_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE) {
        /* mGBA output has row zero at GL y=0. Flip for the libretro FBO. */
        glBlitFramebuffer(0,0,480,320,80,400,560,80,GL_COLOR_BUFFER_BIT,GL_NEAREST);
    }
    glBindFramebuffer(GL_FRAMEBUFFER,target);
    videoCallback(RETRO_HW_FRAME_BUFFER_VALID,640,480,0);
}
''')
rep(p,'\tinfo->library_name = projectName;','\tinfo->library_name = "mGBA GLES3 RGDS (experimental)";')
rep(p,'\tinfo->geometry.max_height = height;','''\tinfo->geometry.max_height = height;
    if (azRequested) {
        info->geometry.base_width=info->geometry.max_width=640;
        info->geometry.base_height=info->geometry.max_height=480;
        info->geometry.aspect_ratio=4.0/3.0;
    }''')
rep(p,'    core->reset(core);\n\t_setupMaps(core);','    core->reset(core);\n    azStarted=true;\n\t_setupMaps(core);')
rep(p,'\tcore->runFrame(core);\n\tunsigned width, height;','\tcore->runFrame(core);\n\tunsigned width, height;')
rep(p,'\tif (!skipFrame) {\n#if defined(COLOR_16_BIT) && defined(COLOR_5_6_5)','''    if (azActive) {
        if (!skipFrame) azPresent();
        else videoCallback(NULL,640,480,0);
    } else if (!skipFrame) {
#if defined(COLOR_16_BIT) && defined(COLOR_5_6_5)''')
rep(p,'\tcore->loadROM(core, rom);\n\tdeferredSetup = true;','''\tcore->loadROM(core, rom);
    azRequested=azActive=azStarted=false;
    if (core->platform(core)==mPLATFORM_GBA && core->supportsFeature(core,mCORE_FEATURE_OPENGL)) {
        memset(&azHW,0,sizeof(azHW));
        azHW.context_type=RETRO_HW_CONTEXT_OPENGLES3;
        azHW.version_major=3;
        azHW.version_minor=0;
        azHW.context_reset=azContextReset;
        azHW.context_destroy=azContextDestroy;
        azHW.bottom_left_origin=true;
        azRequested=true;
        if (!environCallback(RETRO_ENVIRONMENT_SET_HW_RENDER,&azHW)) azRequested=false;
    }
\tdeferredSetup = true;''')
rep(p,'\tmCoreConfigDeinit(&core->config);\n\tcore->deinit(core);','''    azContextDestroy();
    azRequested=azStarted=false;
\tmCoreConfigDeinit(&core->config);
\tcore->deinit(core);
    core=NULL;''')
print("mGBA GLES3 bridge source applied; centered native LCD at 2x, no exterior expansion yet")
