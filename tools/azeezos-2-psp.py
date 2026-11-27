#!/usr/bin/env python3
"""Dedicated PPSSPP RG DS 4:3 direct rendering core, with buffered fallback."""
from pathlib import Path
import re, sys, shutil, subprocess
mode,root=sys.argv[1],Path(sys.argv[2])
def rep(path,old,new):
    p=root/path
    s=p.read_text()
    if new in s:return
    if s.count(old)!=1:raise SystemExit("PSP anchor mismatch: "+str(path)+" "+repr(old[:90]))
    p.write_text(s.replace(old,new,1))

if mode=="--source":
    # Libretro owns the GL context; no X11 surface support on DRM/EGL RG DS.
    rep("libretro/Makefile.common",
        "COREFLAGS += -DVK_USE_PLATFORM_XLIB_KHR",
        "# AzeezOS: no Xlib surface extensions on DRM/EGL")
    # Adreno custom driver loading is Android-only, not generic ARM64 Linux.
    rep("libretro/Makefile.common",
        "ifeq ($(TARGET_ARCH),arm64)\nSOURCES_CXX += \\\n\t  $(EXTDIR)/libadrenotools/src/driver.cpp",
        "ifeq ($(TARGET_ARCH)-$(PLATFORM_EXT),arm64-android)\nSOURCES_CXX += \\\n\t  $(EXTDIR)/libadrenotools/src/driver.cpp")
    p="libretro/libretro.cpp"
    rep(p,'info->library_name     = "PPSSPP";','info->library_name     = "PPSSPP Azeez 4:3";')
    rep(p,'   retro_base_dir /= "PPSSPP";','''   retro_base_dir /= "PPSSPP";
   if (!File::Exists(Path(retro_base_dir / "compat.ini")))
      retro_base_dir = Path("/usr/share/banana/PPSSPP");''')
    rep(p,'   // Cannot detect refresh rate changes if:', '''   // Keep the host at 480p; the internal PSP VRAM dimensions remain real.
   g_Config.iInternalResolution = 1;
   g_Config.bDisplayCropTo16x9 = false;
   g_Config.iFrameSkip = 0;
   g_Config.bAutoFrameSkip = false;
   g_Config.iMultiSampleLevel = 0;
   g_Config.iTexScalingLevel = 1;
   if (System_GetPropertyBool(SYSPROP_CAN_JIT))
      g_Config.iCpuCore = (int)CPUCore::JIT;

   // Cannot detect refresh rate changes if:''')
    rep(p,'      coreParam.pixelWidth  = coreParam.renderWidth  = g_Config.iInternalResolution * NATIVEWIDTH;\n      coreParam.pixelHeight = coreParam.renderHeight = g_Config.iInternalResolution * NATIVEHEIGHT;','''      coreParam.pixelWidth = 640;
      coreParam.pixelHeight = 480;
      coreParam.renderWidth = NATIVEWIDTH;
      coreParam.renderHeight = NATIVEHEIGHT;''')
    rep(p,'''   info->geometry.aspect_ratio = (float)info->geometry.base_width / (float)info->geometry.base_height;

   PSP_CoreParameter().pixelWidth  = PSP_CoreParameter().renderWidth  = info->geometry.base_width;
   PSP_CoreParameter().pixelHeight = PSP_CoreParameter().renderHeight = info->geometry.base_height;''','''   // Direct rendering writes to the native panel-sized hardware backbuffer.
   // Buffered games keep native PSP-size intermediate render targets.
   if (ctx && ctx->GetGPUCore() != GPUCORE_SOFTWARE) {
      info->geometry.base_width = info->geometry.max_width = 640;
      info->geometry.base_height = info->geometry.max_height = 480;
      info->geometry.aspect_ratio = 4.0f / 3.0f;
   } else {
      info->geometry.aspect_ratio = (float)info->geometry.base_width / info->geometry.base_height;
   }
   PSP_CoreParameter().pixelWidth = info->geometry.base_width;
   PSP_CoreParameter().pixelHeight = info->geometry.base_height;
   PSP_CoreParameter().renderWidth = NATIVEWIDTH;
   PSP_CoreParameter().renderHeight = NATIVEHEIGHT;''')
    rep(p,'   retro_check_backend();','''   retro_check_backend();
   backend = RETRO_HW_CONTEXT_OPENGL;''')
    # Fill without anisotropic scaling: a centered 4:3 camera crop.
    # Applies to both the direct GE viewport and buffered presentation.
    rep("GPU/Common/PresentationCommon.cpp",
        'void CalculateDisplayOutputRect(const DisplayLayoutConfig &config, FRect *rc, float origW, float origH, const FRect &frame, int rotation) {',
        '''void CalculateDisplayOutputRect(const DisplayLayoutConfig &config, FRect *rc, float origW, float origH, const FRect &frame, int rotation) {
#ifdef __LIBRETRO__
    if (frame.w > 0 && frame.h > 0 && origW == 480.0f && origH == 272.0f &&
        rotation == ROTATION_LOCKED_HORIZONTAL &&
        fabsf(frame.w/frame.h-4.0f/3.0f)<0.02f) {
        const float w=frame.h*origW/origH;
        rc->x=frame.x+(frame.w-w)*0.5f;
        rc->y=frame.y;
        rc->w=w;
        rc->h=frame.h;
        return;
    }
#endif'''.replace("#ifdef __LIBRETRO__\n","").replace("#endif",""))
    # Default direct rendering; the existing core option allows buffered
    # fallback for games that need offscreen GPU effects.
    p="libretro/libretro_core_options.h"
    s=(root/p).read_text()
    start=s.index('"ppsspp_skip_buffer_effects"')
    end=s.index('\n   },',start)
    block=s[start:end]
    assert block.count('"disabled"')==1
    (root/p).write_text(s[:start]+block.replace('"disabled"','"enabled"')+s[end:])
    print("PPSSPP native 640x480 direct-render geometry, aspect-preserving crop and buffered fallback installed")
    sys.exit(0)

def install_menu(r):
    p=r/"etc/banana/systems.conf"
    s=p.read_text()
    if "[psp]" not in s:
        anchor="[gameandwatch]"
        assert s.count(anchor)==1
        p.write_text(s.replace(anchor,"""[psp]
name = PlayStation Portable
maker = Sony
ext = iso cso chd pbp elf prx
run = /usr/libexec/banana/run-retroarch ppsspp_azeez %ROM%
perf = performance
always = yes
aliases = psp, playstation portable

"""+anchor,1))
    else:
        p.write_text(re.sub(r"(?ms)(^\[psp\]\n(?:(?!^\[).)*?^run\s*=\s*).*$",r"\g<1>/usr/libexec/banana/run-retroarch ppsspp_azeez %ROM%",s,count=1))
    p=r/"usr/libexec/banana/run-retroarch"
    s=p.read_text()
    if "# Azeez PSP GPU core" not in s:
        # Never route a hardware core into the software-only frontend.
        s,num=re.subn(r'(?m)^n64\|psx(?:\|saturn)?\|""\) ;;$', 'n64|psx|saturn|psp|"") ;;',s,count=1)
        assert num==1,"PSP hardware frontend anchor"
        anchor='[ -f "$CORE" ] || { echo "no core $1" >&2; exit 1; }'
        assert s.count(anchor)==1
        s=s.replace(anchor,'''# Azeez PSP GPU core
if [ "$BANANA_SYSTEM" = psp ]; then
    [ -s /usr/lib/libretro/ppsspp_azeez_libretro.so ] && CORE=/usr/lib/libretro/ppsspp_azeez_libretro.so
fi
'''+anchor,1)
        p.write_text(s)
    subprocess.run(["sh","-n",str(p)],check=True)

if mode=="--rootfs":
    install_menu(root)
    assert (root/"usr/lib/libretro/ppsspp_azeez_libretro.so").stat().st_size>0
    assert (root/"usr/share/banana/PPSSPP/compat.ini").is_file()
    sys.exit(0)
if mode!="--build":raise SystemExit("PSP mode")
install_menu(root/"system/rootfs")
pkg=root/"buildroot/package/libretro-ppsspp-azeez"
pkg.mkdir(exist_ok=True)
shutil.copyfile(__file__,pkg/"azeezos-2-psp.py")
(pkg/"libretro-ppsspp-azeez.mk").write_text("""LIBRETRO_PPSSPP_AZEEZ_VERSION = fa50bb1976065c4f8b1b47af227d367fe9771555
LIBRETRO_PPSSPP_AZEEZ_SITE = https://github.com/hrydgard/ppsspp.git
LIBRETRO_PPSSPP_AZEEZ_SITE_METHOD = git
LIBRETRO_PPSSPP_AZEEZ_GIT_SUBMODULES = YES
LIBRETRO_PPSSPP_AZEEZ_LICENSE = GPL-2.0+
LIBRETRO_PPSSPP_AZEEZ_DEPENDENCIES = host-pkgconf libegl libgles

define LIBRETRO_PPSSPP_AZEEZ_BUILD_CMDS
	python3 $(BR2_EXTERNAL_BANANA_PATH)/package/libretro-ppsspp-azeez/azeezos-2-psp.py --source $(@D)
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D)/libretro platform=arm64-gles CC="$(TARGET_CC)" CXX="$(TARGET_CXX)" AR="$(TARGET_AR)"
endef

define LIBRETRO_PPSSPP_AZEEZ_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0644 $(@D)/libretro/ppsspp_libretro.so $(TARGET_DIR)/usr/lib/libretro/ppsspp_azeez_libretro.so
	mkdir -p $(TARGET_DIR)/usr/share/banana/PPSSPP
	cp -a $(@D)/assets/. $(TARGET_DIR)/usr/share/banana/PPSSPP/
endef

$(eval $(generic-package))
""")
p=root/"buildroot/package/retroarch/cores.in"
s=p.read_text()
if "config BR2_PACKAGE_LIBRETRO_PPSSPP_AZEEZ\n" not in s:
    p.write_text(s+'\nconfig BR2_PACKAGE_LIBRETRO_PPSSPP_AZEEZ\n\tbool "libretro-ppsspp-azeez"\n\tdefault y\n\tdepends on BR2_INSTALL_LIBSTDCPP\n')
print("PSP dedicated 4:3 core and assets integrated")
