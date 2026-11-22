#!/usr/bin/env python3
"""Install switchable GPU *screen* bilinear / three-point filters.

RetroArch: one-pass GLSL through its existing shader preset mechanism.
BananaFront / DS: fragment shaders through SuperDrastic's existing path.
Does not claim core-level per-texture filtering; keeps all old options.
"""
from pathlib import Path
import sys
if len(sys.argv) != 2:
    sys.exit("Usage: python3 rgds-filter-patch.py /path/to/BananaLinux")
root = Path(sys.argv[1])

def sub(path, old, new):
    text = path.read_text()
    if new in text:
        return
    if text.count(old) != 1:
        sys.exit("RG DS filter patch upstream mismatch at " + str(path) + ": " + old[:80])
    path.write_text(text.replace(old, new, 1))

glsl = root / "system/rootfs/usr/share/libretro/shaders/glsl/rgds"
glsl.mkdir(parents=True, exist_ok=True)
glsl.joinpath("threepoint.glslp").write_text('shaders = "1"\nshader0 = "threepoint.glsl"\nfilter_linear0 = "false"\n')
glsl.joinpath("bilinear.glslp").write_text('shaders = "1"\nshader0 = "bilinear.glsl"\nfilter_linear0 = "true"\n')
# Public-domain style GLSL based on the standard 3-tap triangular interpolation
# convention: the three surrounding texels inside either half of the texel quad.
# Separate graphics postprocess only; core textures remain untouched.
glsl.joinpath("threepoint.glsl").write_text(r"""#if defined(VERTEX)
#if __VERSION__ >= 130
#define ATTR in
#define VARY out
#else
#define ATTR attribute
#define VARY varying
#endif
ATTR vec4 VertexCoord;
ATTR vec4 TexCoord;
uniform mat4 MVPMatrix;
VARY vec2 rgds_uv;
void main() { gl_Position = MVPMatrix * VertexCoord; rgds_uv = TexCoord.xy; }
#elif defined(FRAGMENT)
#if __VERSION__ >= 130
#define VARY in
#define SAMPLE texture
out vec4 FragColor;
#else
#define VARY varying
#define SAMPLE texture2D
#define FragColor gl_FragColor
#endif
#ifdef GL_ES
precision highp float;
#endif
uniform sampler2D Texture;
uniform vec2 TextureSize;
VARY vec2 rgds_uv;
void main()
{
    vec2 cell = rgds_uv * TextureSize - vec2(0.5);
    vec2 b = floor(cell);
    vec2 f = fract(cell);
    vec2 stepUV = 1.0 / TextureSize;
    vec4 a = SAMPLE(Texture, (b + vec2(0.5, 0.5)) * stepUV);
    vec4 bx = SAMPLE(Texture, (b + vec2(1.5, 0.5)) * stepUV);
    vec4 by = SAMPLE(Texture, (b + vec2(0.5, 1.5)) * stepUV);
    vec4 d = SAMPLE(Texture, (b + vec2(1.5, 1.5)) * stepUV);
    FragColor = f.x + f.y <= 1.0
        ? a * (1.0 - f.x - f.y) + bx * f.x + by * f.y
        : d * (f.x + f.y - 1.0) + bx * (1.0 - f.y) + by * (1.0 - f.x);
}
#endif
""")
glsl.joinpath("bilinear.glsl").write_text(r"""#if defined(VERTEX)
#if __VERSION__ >= 130
#define ATTR in
#define VARY out
#else
#define ATTR attribute
#define VARY varying
#endif
ATTR vec4 VertexCoord;
ATTR vec4 TexCoord;
uniform mat4 MVPMatrix;
VARY vec2 rgds_uv;
void main() { gl_Position = MVPMatrix * VertexCoord; rgds_uv = TexCoord.xy; }
#elif defined(FRAGMENT)
#if __VERSION__ >= 130
#define VARY in
#define SAMPLE texture
out vec4 FragColor;
#else
#define VARY varying
#define SAMPLE texture2D
#define FragColor gl_FragColor
#endif
#ifdef GL_ES
precision highp float;
#endif
uniform sampler2D Texture;
VARY vec2 rgds_uv;
void main() { FragColor = SAMPLE(Texture, rgds_uv); }
#endif
""")
# SuperDrastic has its own uniform and varying names, but the same GLSL
# fragment math can be used by SuperDrastic, BananaDS, and BananaFront.
ds = root / "system/rootfs/usr/lib/superdrastic/shaders"
ds.mkdir(parents=True, exist_ok=True)
ds.joinpath("rgds-threepoint.frag").write_text(r"""#ifdef GL_ES
precision highp float;
#endif
uniform sampler2D u_texture;
uniform vec2 u_texture_size;
varying vec2 v_texcoord;
void main()
{
    vec2 cell = v_texcoord * u_texture_size - vec2(0.5);
    vec2 b = floor(cell);
    vec2 f = fract(cell);
    vec2 px = 1.0 / u_texture_size;
    vec4 a  = texture2D(u_texture, (b + vec2(0.5, 0.5)) * px);
    vec4 bx = texture2D(u_texture, (b + vec2(1.5, 0.5)) * px);
    vec4 by = texture2D(u_texture, (b + vec2(0.5, 1.5)) * px);
    vec4 d  = texture2D(u_texture, (b + vec2(1.5, 1.5)) * px);
    gl_FragColor = f.x + f.y <= 1.0
        ? a * (1.0 - f.x - f.y) + bx * f.x + by * f.y
        : d * (f.x + f.y - 1.0) + bx * (1.0 - f.y) + by * (1.0 - f.x);
}
""")
ds.joinpath("rgds-bilinear.frag").write_text(r"""#ifdef GL_ES
precision highp float;
#endif
uniform sampler2D u_texture;
uniform vec2 u_texture_size;
varying vec2 v_texcoord;
void main()
{
    vec2 texel = v_texcoord * u_texture_size - vec2(0.5);
    vec2 b = floor(texel);
    vec2 f = fract(texel);
    vec2 stepUV = 1.0 / u_texture_size;
    vec4 a = texture2D(u_texture, (b + vec2(0.5, 0.5)) * stepUV);
    vec4 c = texture2D(u_texture, (b + vec2(1.5, 0.5)) * stepUV);
    vec4 d = texture2D(u_texture, (b + vec2(0.5, 1.5)) * stepUV);
    vec4 e = texture2D(u_texture, (b + vec2(1.5, 1.5)) * stepUV);
    gl_FragColor = mix(mix(a, c, f.x), mix(d, e, f.x), f.y);
}
""")

ra = root / "system/rootfs/usr/libexec/banana/run-retroarch"
sub(ra,
    '    sharp) SP=interpolation/sharp-bilinear-simple.glslp ;;',
    '    sharp) SP=interpolation/sharp-bilinear-simple.glslp ;;\n    bilinear) SP=rgds/bilinear.glslp ;;\n    threepoint) SP=rgds/threepoint.glslp ;;')
bf = root / "system/rootfs/usr/libexec/banana/run-bananafront"
sub(bf, 'sharp) SH=sharp-bilinear ;; *) SH= ;; esac',
    'sharp) SH=sharp-bilinear ;; bilinear) SH=rgds-bilinear ;; threepoint) SH=rgds-threepoint ;; *) SH= ;; esac')
settings = root / "ui/src/settings.cpp"
sub(settings, '"DraStic fast LCD + colours" };',
    '"DraStic fast LCD + colours", "RG DS 3-point", "RG DS Bilinear" };')
sub(settings, '"drastic-zfast-lcd-nds-color" };',
    '"drastic-zfast-lcd-nds-color", "rgds-threepoint", "rgds-bilinear" };')
sub(settings,
    'menu, "ra_shader", { "Off", "LCD", "CRT", "Sharp pixels" }, { "off", "lcd", "crt", "sharp" });',
    'menu, "ra_shader", { "Off", "LCD", "CRT", "Sharp pixels", "Bilinear", "N64 3-point" }, { "off", "lcd", "crt", "sharp", "bilinear", "threepoint" });')
sub(settings,
    'items.back().hints = { "The picture as it is.", "A handheld\'s LCD grid.", "A CRT\'s scanlines.", "Sharp pixels at any size." };',
    'items.back().hints = { "The picture as it is.", "A handheld\'s LCD grid.", "A CRT\'s scanlines.", "Sharp pixels at any size.", "4-tap image sampling; not a core texture filter.", "3-tap image sampling; not a core texture filter." };')
defaults = root / "ui/src/settings_defaults.cpp"
sub(defaults,
    'const char* const SHADERS[] = { "off", "lcd", "crt", "sharp", nullptr };',
    'const char* const SHADERS[] = { "off", "lcd", "crt", "sharp", "bilinear", "threepoint", nullptr };')
print("Added selectable GPU full-screen filtering: Off/Bilinear/N64 3-point.")
print("Applied to RetroArch, BananaFront, and DS shader selection; NOT internal core textures.")
