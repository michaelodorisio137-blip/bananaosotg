#!/usr/bin/env python3
"""Experimental mGBA render geometry, based on mgba-emu/mgba issue #1960.

320x204 = 65,280 rendered pixels, 55 below the experiment's *reported*
~65,335 crash point. This is NOT an HD/Mode7 renderer; normal mGBA is kept
as a separate built binary. The experiment can alter GBA H/VBlank timing and
break some games; never ship it as a replacement for the unmodified core.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    sys.exit("Usage: python3 rgds-mgba-viewport-source.py /path/to/libretro-mgba")

root=Path(sys.argv[1])
changes={
    "include/mgba/gba/interface.h": [
        ("GBA_VIDEO_HORIZONTAL_PIXELS = 240,", "GBA_VIDEO_HORIZONTAL_PIXELS = 320,"),
        ("GBA_VIDEO_VERTICAL_PIXELS = 160,", "GBA_VIDEO_VERTICAL_PIXELS = 204,"),
    ],
    "include/mgba/internal/gba/renderers/video-software.h":[
        ("uint8_t endX;", "uint16_t endX;"),
        ("uint32_t scanlineDirty[5];", "uint32_t scanlineDirty[7];"),
    ],
    "include/mgba/internal/gba/video.h":[
        ("uint8_t end;", "uint16_t end;"),
        ("uint8_t start;", "uint16_t start;"),
    ],
    "src/platform/libretro/libretro.c":[
        ("#define VIDEO_WIDTH_MAX  256", "#define VIDEO_WIDTH_MAX  320"),
    ],
}
for rel, replacements in changes.items():
    p=root/rel
    if not p.is_file(): sys.exit("Missing mGBA source: "+str(p))
    s=p.read_text()
    for before,after in replacements:
        if after in s: continue
        if s.count(before)!=1:
            sys.exit("mGBA pinned source changed: "+rel+" / "+before)
        s=s.replace(before,after,1)
    p.write_text(s)
print("mGBA experimental renderer: GBA 320x204 = 65280 logical pixels.")
print("Unmodified mGBA must remain available as the primary, safe core.")


# GB/GBC keep the *real* LCD/PPU limits (160x144). Changing GB_VIDEO_* to
# 320x204 corrupts timing, tile attribute arrays and SGB. Instead extrapolate
# the currently selected background tilemap into an enlarged framebuffer, then
# overlay the faithfully emulated, native 160x144 framebuffer in the centre.
# This gives useful VRAM beyond-screen graphics without changing hardware
# scanline timing, ROM input, sprite limits or save-state geometry.
p=root/"src/platform/libretro/libretro.c"
s=p.read_text()

inc = "#include <mgba/internal/gb/gb.h>"
new_inc = inc + "\n#include <mgba/internal/gb/renderers/software.h> /* RG DS GB/GBC VRAM border */"
if new_inc not in s:
    if s.count(inc)!=1: sys.exit("GB video software renderer include anchor missing")
    s=s.replace(inc,new_inc,1)

code = r"""
/* RG DS experimental GB/GBC background overscan.
 * Native PPU output is kept perfectly intact and centred at 80,30.
 * The surrounding region is a VRAM tilemap preview, not extra GB LCD pixels:
 * window/sprites outside 160x144 are intentionally not fabricated.
 * Do NOT modify GB_VIDEO_HORIZONTAL_PIXELS or GB_VIDEO_VERTICAL_PIXELS:
 * those constants govern genuine Game Boy timing and hardware attribute maps.
 */
#ifdef M_CORE_GB
#define RGDS_GB_EXT_W 320
#define RGDS_GB_EXT_H 204
#define RGDS_GB_INSET_X 80
#define RGDS_GB_INSET_Y 30
static mColor rgdsGBBorder[RGDS_GB_EXT_W * RGDS_GB_EXT_H];

static bool rgdsGBCanExtend(void) {
    if (!core || core->platform(core) != mPLATFORM_GB) return false;
    const struct GB* gb = (const struct GB*) core->board;
    return gb != NULL;  /* ordinary GB, SGB-enhanced GB, and GBC */
}

static void rgdsGBRenderBorder(const mColor* native) {
    const struct GB* gb = (const struct GB*) core->board;
    const struct GBVideoSoftwareRenderer* r = (const struct GBVideoSoftwareRenderer*) gb->video.renderer;
    if (!r || !r->d.vram) {
        memset(rgdsGBBorder, 0, sizeof(rgdsGBBorder));
    } else {
        const uint8_t* vram = r->d.vram;
        const uint8_t* map = vram + GB_BASE_MAP +
            (GBRegisterLCDCIsTileMap(r->lcdc) ? GB_SIZE_MAP : 0);
        const bool cgb = (gb->model & GB_MODEL_CGB) != 0;
        const bool enabled = GBRegisterLCDCIsEnable(r->lcdc) &&
            (GBRegisterLCDCIsBgEnable(r->lcdc) || cgb) && !r->d.disableBG;
        for (int y = 0; y < RGDS_GB_EXT_H; ++y) {
            const int screenY = y - RGDS_GB_INSET_Y;
            for (int x = 0; x < RGDS_GB_EXT_W; ++x) {
                const int screenX = x - RGDS_GB_INSET_X;
                mColor color = r->palette[0];
                if (enabled) {
                    const unsigned tx = (unsigned)(screenX + r->scx - r->offsetScx) & 255U;
                    const unsigned ty = (unsigned)(screenY + r->scy - r->offsetScy) & 255U;
                    const unsigned mapIndex = ((ty >> 3) << 5) | (tx >> 3);
                    const uint8_t flags = cgb ? map[GB_SIZE_VRAM_BANK0 + mapIndex] : 0;
                    const unsigned px = (flags & 0x20) ? (tx & 7U) : 7U - (tx & 7U);
                    const unsigned py = (flags & 0x40) ? 7U - (ty & 7U) : (ty & 7U);
                    const uint8_t tile = map[mapIndex];
                    const int tileNo = GBRegisterLCDCIsTileData(r->lcdc) ?
                        (int)tile : (int)(int8_t)tile;
                    const unsigned tileBase = (GBRegisterLCDCIsTileData(r->lcdc) ? 0U : 0x1000U) +
                        ((unsigned)(tileNo * 8 + (int)py) * 2U);
                    const uint8_t* tileBank = vram +
                        ((cgb && (flags & 0x08)) ? GB_SIZE_VRAM_BANK0 : 0);
                    const unsigned bit0 = (tileBank[tileBase] >> px) & 1U;
                    const unsigned bit1 = (tileBank[tileBase + 1] >> px) & 1U;
                    const unsigned pixel = bit0 | (bit1 << 1);
                    const unsigned paletteIndex = cgb ? ((flags & 7U) * 4U + pixel)
                                                      : r->lookup[pixel];
                    color = r->palette[paletteIndex];
                }
                rgdsGBBorder[y * RGDS_GB_EXT_W + x] = color;
            }
        }
    }
    /* The actual Game Boy LCD pixels must take priority over the synthetic
       offscreen background, preserving native sprites, window and effects. */
    /* If a GB cartridge auto-selected Super Game Boy, mGBA may place the
       true 160x144 LCD image at 48,40 inside its 256x224 border. The
       expanded core replaces that border, not the actual LCD pixels. */
    const bool sgbFrame = (gb->model & GB_MODEL_SGB) && gb->video.sgbBorders;
    const mColor* nativeLCD = native + (sgbFrame ? 40 * VIDEO_WIDTH_MAX + 48 : 0);
    for (int y = 0; y < GB_VIDEO_VERTICAL_PIXELS; ++y) {
        memcpy(rgdsGBBorder +
               (y + RGDS_GB_INSET_Y) * RGDS_GB_EXT_W + RGDS_GB_INSET_X,
               nativeLCD + y * VIDEO_WIDTH_MAX,
               GB_VIDEO_HORIZONTAL_PIXELS * sizeof(mColor));
    }
}
#endif
"""
anchor = "static struct mCore* core;\n"
# The functions reference core, so declare immediately *after* that variable.
if code not in s:
    if s.count(anchor)!=1: sys.exit("GB border function anchor moved")
    s=s.replace(anchor,anchor+code+"\n",1)

old_geometry = """\tinfo->geometry.max_width = width;
\tinfo->geometry.max_height = height;"""
new_geometry = """\tinfo->geometry.max_width = width;
\tinfo->geometry.max_height = height;
#ifdef M_CORE_GB
\tif (rgdsGBCanExtend()) {
\t\tinfo->geometry.base_width = RGDS_GB_EXT_W;
\t\tinfo->geometry.base_height = RGDS_GB_EXT_H;
\t\tinfo->geometry.max_width = RGDS_GB_EXT_W;
\t\tinfo->geometry.max_height = RGDS_GB_EXT_H;
\t\tinfo->geometry.aspect_ratio = RGDS_GB_EXT_W / (double) RGDS_GB_EXT_H;
\t}
#endif"""
if new_geometry not in s:
    if s.count(old_geometry)!=1: sys.exit("GB libretro geometry anchor moved")
    s=s.replace(old_geometry,new_geometry,1)

old_callback = """\tif (!skipFrame) {
#if defined(COLOR_16_BIT) && defined(COLOR_5_6_5)
\t\tif (videoPostProcess) {
\t\t\tvideoPostProcess(width, height);
\t\t\tvideoCallback(ppOutputBuffer, width, height, VIDEO_WIDTH_MAX * sizeof(mColor));
\t\t} else
#endif
\t\t\tvideoCallback(outputBuffer, width, height, VIDEO_WIDTH_MAX * sizeof(mColor));
\t} else {
\t\tvideoCallback(NULL, width, height, VIDEO_WIDTH_MAX * sizeof(mColor));
\t}"""
new_callback = """\tif (!skipFrame) {
\t\tconst mColor* frame = outputBuffer;
#if defined(COLOR_16_BIT) && defined(COLOR_5_6_5)
\t\tif (videoPostProcess) {
\t\t\tvideoPostProcess(width, height);
\t\t\tframe = ppOutputBuffer;
\t\t}
#endif
#ifdef M_CORE_GB
\t\tif (rgdsGBCanExtend()) {
\t\t\trgdsGBRenderBorder(frame);
\t\t\tframe = rgdsGBBorder;
\t\t\twidth = RGDS_GB_EXT_W;
\t\t\theight = RGDS_GB_EXT_H;
\t\t}
#endif
\t\tvideoCallback(frame, width, height, VIDEO_WIDTH_MAX * sizeof(mColor));
\t} else {
#ifdef M_CORE_GB
\t\tif (rgdsGBCanExtend()) {
\t\t\twidth = RGDS_GB_EXT_W;
\t\t\theight = RGDS_GB_EXT_H;
\t\t}
#endif
\t\tvideoCallback(NULL, width, height, VIDEO_WIDTH_MAX * sizeof(mColor));
\t}"""
if new_callback not in s:
    if s.count(old_callback)!=1: sys.exit("GB libretro output anchor moved")
    s=s.replace(old_callback,new_callback,1)
p.write_text(s)

print("GB/GBC native LCD preserved and centred in a 320x204 VRAM-tilemap border.")
print("SGB-enhanced titles also show the expanded framebuffer; no GB timing constants widened.")


# Give the experimental GB/GBC/GBA core its own libretro identity. RetroArch
# and BananaFront use library_name to locate per-core options and overrides;
# keeping the ordinary "mGBA" name caused an old mGBA options profile to leak
# into the expanded core and concealed which core was actually running.
p=root/"src/platform/libretro/libretro.c"
s=p.read_text()
old="\tinfo->library_name = projectName;"
new='\tinfo->library_name = "mGBA Expanded RGDS";'
if new not in s:
    if s.count(old)!=1: sys.exit("mGBA libretro identity anchor moved")
    s=s.replace(old,new,1)
p.write_text(s)
print("Unique libretro core identity: mGBA Expanded RGDS (independent options).")

# GBA bitmap modes use fixed hardware VRAM dimensions, not the widened LCD
# output geometry. Preserve native row pitch and sampling bounds in modes 3/4.
# Mode 5 already uses its independent 160x128 dimensions; leave it intact.
p = root / "src/gba/renderers/software-bg.c"
s = p.read_text()
start = s.index("void GBAVideoSoftwareRendererDrawBackgroundMode3(")
end = s.index("void GBAVideoSoftwareRendererDrawBackgroundMode5(", start)
bitmap = s[start:end]
if "GBA_VIDEO_HORIZONTAL_PIXELS" in bitmap or "GBA_VIDEO_VERTICAL_PIXELS" in bitmap:
    if bitmap.count("GBA_VIDEO_HORIZONTAL_PIXELS") != 8 or bitmap.count("GBA_VIDEO_VERTICAL_PIXELS") != 4:
        sys.exit("Unexpected mode 3/4 bitmap source; refusing unsafe patch")
    bitmap = bitmap.replace("GBA_VIDEO_HORIZONTAL_PIXELS", "240").replace("GBA_VIDEO_VERTICAL_PIXELS", "160")
    p.write_text(s[:start] + bitmap + s[end:])
assert "GBA_VIDEO_HORIZONTAL_PIXELS" not in bitmap
assert "GBA_VIDEO_VERTICAL_PIXELS" not in bitmap
print("PASS: mode 3/4 bitmap pitch 240 and bounds 240x160, mode 5 unchanged")
