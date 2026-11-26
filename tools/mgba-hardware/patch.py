#!/usr/bin/env python3
"""Experimental native-resolution GLES3 libretro port; no CPU 3D HLE."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
def edit(path,a,b):
    p=root/path;s=p.read_text()
    if s.count(a)!=1:raise SystemExit(f"Anchor mismatch {path}: {a[:80]!r}")
    p.write_text(s.replace(a,b,1))
p="CMakeLists.txt"
edit(p,'target_link_libraries(${BINARY_NAME}_libretro ${OS_LIB})','''target_link_libraries(${BINARY_NAME}_libretro ${OS_LIB})
	find_library(AZ_GLES NAMES GLESv2 REQUIRED)
	target_compile_definitions(${BINARY_NAME}_libretro PRIVATE BUILD_GLES3)
	target_link_libraries(${BINARY_NAME}_libretro ${AZ_GLES})''')
p="src/platform/libretro/libretro.c"
edit(p,"#include <mgba/internal/gba/gba.h>","#include <mgba/internal/gba/gba.h>\n#include <GLES3/gl3.h>")
edit(p,"static struct mCore* core;\n",r"""static struct mCore* core;
static struct retro_hw_render_callback azHW;
static GLuint azTex, azFbo;
static bool azReady, azStarted, azRequested;
static void azContextReset(void) {
    if (!core || core->platform(core)!=mPLATFORM_GBA) return;
    if (!glGetString(GL_VERSION)) return;
    glGenTextures(1,&azTex);
    glGenFramebuffers(1,&azFbo);
    azReady=azTex && azFbo;
    if (!azReady) return;
    mCoreConfigSetIntValue(&core->config,"hwaccelVideo",1);
    mCoreConfigSetIntValue(&core->config,"videoScale",2);
    core->setVideoGLTex(core,azTex);
    if (azStarted) core->reloadConfigOption(core,"hwaccelVideo",&core->config);
}
static void azContextDestroy(void) {
    if (azReady && core && azStarted) {
        mCoreConfigSetIntValue(&core->config,"hwaccelVideo",0);
        core->reloadConfigOption(core,"hwaccelVideo",&core->config);
    }
    if (azReady && core) core->setVideoGLTex(core,(unsigned)-1);
    if (azFbo) glDeleteFramebuffers(1,&azFbo);
    if (azTex) glDeleteTextures(1,&azTex);
    azTex=azFbo=0;azReady=false;
}
static void azPresent(unsigned w,unsigned h) {
    GLuint target=(GLuint)azHW.get_current_framebuffer();
    glDisable(GL_SCISSOR_TEST);
    glBindFramebuffer(GL_READ_FRAMEBUFFER,azFbo);
    glFramebufferTexture2D(GL_READ_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,azTex,0);
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER,target);
    if (glCheckFramebufferStatus(GL_READ_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE) {
        glBlitFramebuffer(0,0,w,h,0,0,w,h,GL_COLOR_BUFFER_BIT,GL_NEAREST);
        videoCallback(RETRO_HW_FRAME_BUFFER_VALID,w,h,0);
    } else {
        videoCallback(NULL,w,h,0);
    }
    glBindFramebuffer(GL_FRAMEBUFFER,target);
}
""")
edit(p,"\tinfo->library_name = projectName;",'\tinfo->library_name = "mGBA Hardware RGDS (Experimental)";')
edit(p,"\tinfo->geometry.max_height = height;","\tinfo->geometry.max_height = height;\n\tif (azRequested) { info->geometry.max_width=480; info->geometry.max_height=320; }")
edit(p,"    core->reset(core);\n\t_setupMaps(core);","    core->reset(core);\n    azStarted=true;\n\t_setupMaps(core);")
edit(p,"\tcore->loadROM(core, rom);\n\tdeferredSetup = true;",r"""	core->loadROM(core, rom);
	deferredSetup = true;
	azStarted=azRequested=azReady=false;
	if (core->platform(core)==mPLATFORM_GBA) {
	    memset(&azHW,0,sizeof azHW);
	    azHW.context_type=RETRO_HW_CONTEXT_OPENGLES3;
	    azHW.context_reset=azContextReset;
	    azHW.context_destroy=azContextDestroy;
	    azHW.version_major=3;
	    azHW.bottom_left_origin=false;
	    azHW.cache_context=false;
	    azRequested=environCallback(RETRO_ENVIRONMENT_SET_HW_RENDER,&azHW);
	    if (!azRequested && logCallback) logCallback(RETRO_LOG_WARN,"GLES3 unavailable; using stock software rendering.\n");
	}""")
edit(p,"\tif (!skipFrame) {\n#if defined(COLOR_16_BIT) && defined(COLOR_5_6_5)","\tif (azReady) {\n\t\tif (!skipFrame) azPresent(width,height); else videoCallback(NULL,width,height,0);\n\t} else if (!skipFrame) {\n#if defined(COLOR_16_BIT) && defined(COLOR_5_6_5)")
edit(p,"\tmCoreConfigDeinit(&core->config);\n\tcore->deinit(core);","\tif (azReady) azContextDestroy();\n\tazStarted=azRequested=false;\n\tmCoreConfigDeinit(&core->config);\n\tcore->deinit(core);\n\tcore=NULL;")
# GL renderer readback originally allocates BYTES_PER_PIXEL but reads RGBA.
# In 16-bit libretro builds this would overflow during a screenshot.
p="src/gba/renderers/gl.c"
edit(p,"glRenderer->scale * glRenderer->scale * BYTES_PER_PIXEL","glRenderer->scale * glRenderer->scale * 4")
# Match the allocation size on free, if the same expression occurs in source
print("GLES3 bridge patched; native affine rendering at 2x, no viewport extension or HLE claimed.")
