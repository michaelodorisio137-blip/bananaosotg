#!/usr/bin/env python3
"""Native integer viewport: output exactly 640x480, preserve emulated timing."""
from pathlib import Path
import sys
p=Path(sys.argv[1])/"src/platform/libretro/libretro.c"
s=p.read_text()
def rep(a,b):
 global s
 if s.count(a)!=1: raise SystemExit("Integer viewport source mismatch: "+repr(a[:80]))
 s=s.replace(a,b,1)
rep("#include <mgba/internal/gb/gb.h>","#include <mgba/internal/gb/gb.h>\n#include <mgba/internal/gb/renderers/software.h>")
rep("#include <mgba/internal/gba/gba.h>","#include <mgba/internal/gba/gba.h>\n#include <mgba/internal/gba/renderers/video-software.h>")
rep("static struct mCore* core;\n", "static struct mCore* core;\n"+r"""
/* RG DS experimental GB/GBC background overscan.
 * Native PPU output is kept perfectly intact and centred at 27,8.
 * The surrounding region is a VRAM tilemap preview, not extra GB LCD pixels:
 * window/sprites outside 160x144 are intentionally not fabricated.
 * Do NOT modify GB_VIDEO_HORIZONTAL_PIXELS or GB_VIDEO_VERTICAL_PIXELS:
 * those constants govern genuine Game Boy timing and hardware attribute maps.
 */
#ifdef M_CORE_GB
#define RGDS_GB_EXT_W 214
#define RGDS_GB_EXT_H 160
#define RGDS_GB_INSET_X 27
#define RGDS_GB_INSET_Y 8
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


#ifdef M_CORE_GBA
/* Render real VRAM background samples beyond native LCD bounds without
 * altering the PPU's timing, bitmap stride, save states or native output.
 * Out-of-range bitmap/affine samples are transparent to the game backdrop. */
static mColor rgdsGBABorder[320 * 240];
static unsigned rgdsRead16(const uint8_t* v, unsigned addr) {
    return (unsigned)v[addr] | ((unsigned)v[addr+1] << 8);
}
static bool rgdsGBASample(const struct GBAVideoSoftwareRenderer* r,
                          unsigned i, int sx, int sy, mColor* color) {
    const struct GBAVideoSoftwareBackground* b = &r->bg[i];
    const uint8_t* v = (const uint8_t*)r->d.vram;
    unsigned mode = GBARegisterDISPCNTGetMode(r->dispcnt);
    if (!b->enabled || r->d.disableBG[i]) return false;
    if ((mode == 0) || (mode == 1 && i < 2)) {
        unsigned x = (unsigned)(sx + b->x) & ((b->size & 1) ? 511 : 255);
        unsigned y = (unsigned)(sy + b->y) & ((b->size & 2) ? 511 : 255);
        unsigned block = (x >> 8) + ((y >> 8) * ((b->size & 1) ? 2 : 1));
        unsigned map = (b->screenBase + block * 2048 + (((y & 255) >> 3)*32 + ((x & 255) >> 3))*2) & 0xFFFF;
        unsigned tile = rgdsRead16(v, map);
        unsigned px = x & 7, py = y & 7, n;
        if (tile & 0x400) px = 7-px;
        if (tile & 0x800) py = 7-py;
        if (b->multipalette) {
            unsigned addr = b->charBase + (tile & 1023)*64 + py*8 + px;
            if (addr >= 0x10000) return false;
            n = v[addr];
        } else {
            unsigned addr = b->charBase + (tile & 1023)*32 + py*4 + px/2;
            if (addr >= 0x10000) return false;
            n = (v[addr] >> ((px & 1)*4)) & 15;
            if (!n) return false;
            n += (tile >> 12)*16;
        }
        if (!n) return false;
        *color = r->normalPalette[n];
        return true;
    }
    if (i < 2 || (mode == 1 && i != 2) || (mode >= 3 && i != 2)) return false;
    /* mGBA's affine origins are reset at frame completion. Use the latched
       reference and matrix for exterior pixels; native scanline effects
       remain exclusively in the unmodified LCD framebuffer. */
    int x = (b->refx + sx*b->dx + sy*b->dmx) >> 8;
    int y = (b->refy + sx*b->dy + sy*b->dmy) >> 8;
    if (mode <= 2) {
        unsigned size = 128U << b->size;
        if (b->overflow) {x &= size-1; y &= size-1;}
        if (x<0 || y<0 || (unsigned)x>=size || (unsigned)y>=size) return false;
        unsigned map = (b->screenBase + ((unsigned)y>>3)*(size>>3) + ((unsigned)x>>3)) & 0xFFFF;
        unsigned addr = b->charBase + v[map]*64 + (y&7)*8 + (x&7);
        if (addr>=0x10000 || !v[addr]) return false;
        *color = r->normalPalette[v[addr]]; return true;
    }
    if (mode > 5) return false;
    unsigned w = mode==5 ? 160 : 240, h = mode==5 ? 128 : 160;
    if (x<0 || y<0 || (unsigned)x>=w || (unsigned)y>=h) return false;
    unsigned off = mode != 3 && GBARegisterDISPCNTIsFrameSelect(r->dispcnt) ? 0xA000 : 0;
    unsigned at = off + (y*w+x)*(mode==4?1:2);
    if (at >= 0x14000) return false;
    if (mode==4) { if (!v[at]) return false; *color=r->normalPalette[v[at]]; }
    else *color=mColorFrom555(rgdsRead16(v,at));
    return true;
}
static void rgdsGBARender(const mColor* native) {
    const struct GBA* gba = (const struct GBA*)core->board;
    const struct GBAVideoSoftwareRenderer* r=(const struct GBAVideoSoftwareRenderer*)gba->video.renderer;
    for (int y=0;y<240;++y) for(int x=0;x<320;++x) {
        if (x>=40 && x<280 && y>=40 && y<200) {
            rgdsGBABorder[y*320+x]=native[(y-40)*VIDEO_WIDTH_MAX+x-40];
            continue;
        }
        mColor pixel = r->normalPalette[0];
        if (r->d.vram && !GBARegisterDISPCNTIsForcedBlank(r->dispcnt)) {
            /* Lower index wins equal priority. Transparent tile pixels
               expose the next actual BG layer, then the backdrop. */
            int priority=4;
            for(unsigned i=0;i<4;++i) {
                mColor c;
                if (r->bg[i].priority < (unsigned)priority &&
                    rgdsGBASample(r,i,x-40,y-40,&c)) {
                    pixel=c;priority=r->bg[i].priority;
                }
            }
        }
        rgdsGBABorder[y*320+x]=pixel;
    }
}
#endif
static mColor rgdsIntegerFrame[640*480];
static void rgdsIntegerOutput(const mColor* native) {
    const mColor* src = NULL;
    unsigned stride=0, scale=0, crop=0;
#ifdef M_CORE_GB
    if (rgdsGBCanExtend()) {
        rgdsGBRenderBorder(native);
        src=rgdsGBBorder; stride=RGDS_GB_EXT_W; scale=3; crop=1;
    }
#endif
#ifdef M_CORE_GBA
    if (core->platform(core)==mPLATFORM_GBA) {
        rgdsGBARender(native);
        src=rgdsGBABorder; stride=320; scale=2;
    }
#endif
    if (!src) return;
    /* 214*3 = 642. Crop 1 physical pixel from each OUTER border, never the
       original GB LCD. 160*3 = 480. GBA 320*2=640, 240*2=480. */
    for (unsigned y=0;y<480;++y)
        for(unsigned x=0;x<640;++x)
            rgdsIntegerFrame[y*640+x]=src[(y/scale)*stride+(x+crop)/scale];
    videoCallback(rgdsIntegerFrame,640,480,640*sizeof(mColor));
}
""")
rep("\tinfo->library_name = projectName;",'\tinfo->library_name = "mGBA Maximum Integer RGDS";')
rep("\tinfo->geometry.max_height = height;", """\tinfo->geometry.max_height = height;
\tinfo->geometry.base_width = info->geometry.max_width = 640;
\tinfo->geometry.base_height = info->geometry.max_height = 480;
\tinfo->geometry.aspect_ratio = 4.0/3.0;""")
start=s.index("\tif (!skipFrame) {",s.index("void retro_run(void)"))
end=s.index("\n\t}",s.index("videoCallback(NULL, width, height, VIDEO_WIDTH_MAX * sizeof(mColor));",start))+3
s=s[:start]+"""\tif (!skipFrame) {
\t\trgdsIntegerOutput(outputBuffer);
\t} else {
\t\tvideoCallback(NULL,640,480,640*sizeof(mColor));
\t}"""+s[end:]
p.write_text(s)
print("PASS: native 640x480 integer viewport output; no emulated LCD constants changed.")
