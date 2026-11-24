#!/usr/bin/env python3
"""Add *native* point-sampled N64 textures to pinned Mupen64Plus-Next GLideN64.

This is not a fullscreen postprocessing shader. It disables shader 3/4-point
interpolation and uses exact texture samples in both GLideN64 shader paths,
while retaining N64-style three-point and conventional bilinear selections.
"""
from pathlib import Path
import sys
r=Path(sys.argv[1])
def rep(rel,old,new):
    p=r/rel;s=p.read_text()
    if new in s: return
    if s.count(old)!=1:raise SystemExit("Pinned Mupen source mismatch "+rel+": "+old[:100])
    p.write_text(s.replace(old,new,1))
rep("GLideN64/src/Config.h",
    "#define BILINEAR_STANDARD 1",
    "#define BILINEAR_STANDARD 1\n#define BILINEAR_NEAREST 4 /* force point sampled 3D textures */")
rep("GLideN64/src/Textures.cpp",
    "gDP.otherMode.textureFilter != G_TF_POINT && config.texture.bilinearMode != BILINEAR_3POINT",
    "gDP.otherMode.textureFilter != G_TF_POINT && config.texture.bilinearMode != BILINEAR_3POINT && config.texture.bilinearMode != BILINEAR_NEAREST")
# The shader generator has a limited four-way switch for its 3point/standard
# subroutines. Ensure the new mode uses an existing subroutine definition;
# the separate per-program uniform then selects point sampling at runtime.
for shader in ("Fast", "Accurate"):
    rel="GLideN64/src/Graphics/OpenGLContext/GLSL/glsl_CombinerProgramBuilder"+shader+".cpp"
    rep(rel,
        "switch (config.texture.bilinearMode + config.texture.enableHalosRemoval * 2)",
        "switch ((config.texture.bilinearMode == BILINEAR_NEAREST ? BILINEAR_STANDARD : config.texture.bilinearMode) + config.texture.enableHalosRemoval * 2)")
# Both fast and accurate GLSL paths respect uTextureFilterMode == 0:
# fast reads from the texture's GL_NEAREST sampler, accurate texelFetches
# the indexed texel. Do not let game-requested bilinear override the user.
rep("GLideN64/src/Graphics/OpenGLContext/GLSL/glsl_CombinerProgramUniformFactoryCommon.cpp",
    "int textureFilter = gDP.otherMode.textureFilter;",
    "int textureFilter = config.texture.bilinearMode == BILINEAR_NEAREST ? 0 : gDP.otherMode.textureFilter;")
rep("libretro/libretro.c",
    'bilinearMode = !strcmp(var.value, "3point") ? 0 : 1;',
    'bilinearMode = !strcmp(var.value, "3point") ? 0 : (!strcmp(var.value, "nearest") ? 4 : 1);')
rep("libretro/libretro_core_options.h",
    '{"standard", NULL},',
    '{"standard", NULL},\n            {"nearest", NULL},')
# A core option exposed through RetroArch is useful even when the BananaOS
# top-level settings page is unavailable or a user uses custom RetroArch.
print("PASS: N64 nearest GPU sampling / shader override / UI core option, plus existing 3-point and bilinear")
