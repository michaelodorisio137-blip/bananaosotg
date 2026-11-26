#!/usr/bin/env python3
"""Experimental Gengis RGB-only filtering for BananaDS at native/hires resolution."""
from pathlib import Path
import sys
import shutil

root=Path(sys.argv[2])
def edit(path,a,b):
    s=path.read_text()
    if b in s: return
    if s.count(a)!=1: raise SystemExit("BananaDS filter anchor mismatch: "+str(path)+" "+repr(a[:100]))
    path.write_text(s.replace(a,b,1))

if sys.argv[1]=="--integrate":
    pkg=root/"buildroot/package/bananads"
    shutil.copyfile(__file__,pkg/"azeezos-2-bananads-filter.py")
    edit(pkg/"bananads.mk","BANANADS_POST_PATCH_HOOKS += BANANADS_MELONDS_PATCH",
        """BANANADS_POST_PATCH_HOOKS += BANANADS_MELONDS_PATCH
define BANANADS_AZEEZ_FILTER
	python3 $(BR2_EXTERNAL_BANANA_PATH)/package/bananads/azeezos-2-bananads-filter.py --source $(@D)
endef
BANANADS_POST_PATCH_HOOKS += BANANADS_AZEEZ_FILTER""")
    edit(root/"ui/src/settings.cpp",'add(BD, "nds", "Edge marking",',
        '''add(BD, "nds", "3D texture sampling (experimental)", "Gengis polygon texture sampling; native 2D is untouched. Filtered modes may be slower.",
                bds, "render.texfilter", { "Nearest", "Bilinear", "N64 3-point" }, { "0", "1", "3" });
            items.back().def = "0";
            add(BD, "nds", "Edge marking",''')
    sys.exit(0)

g=root/"bananads/gengis"
edit(g/"gx.h","void gx_init(void);",
    "extern int gx_texture_filter;\nvoid gx_init(void);")
edit(root/"bananads/src/emu.cpp",'const int threads = (int)cfg_.num("render.gengis_threads", 3);',
    '''const long tf = cfg_.num("render.texfilter", 0);
        gx_texture_filter = tf == 1 || tf == 3 ? (int)tf : 0;
        const int threads = (int)cfg_.num("render.gengis_threads", 3);''')
edit(g/"gx.c","const int defer = gx_defer && !gx_ref;",
    "const int defer = gx_defer && !gx_ref && !gx_texture_filter;")
edit(g/"fused.c","int use_neon = 2;",
    '''/* Fixed for a game session before worker threads start. */
int gx_texture_filter = 0;

static inline uint32_t az_texel(const poly_t *p, uint16_t u, uint16_t v) {
    uint32_t i = texcoord(u,p->ms,p->tw) + (uint32_t)texcoord(v,p->mt,p->th)*p->tw;
    return p->paletted ? p->pal[p->idx8[i]] : p->texels32[i];
}
static inline uint32_t az_filtered(const poly_t *p, uint32_t U, uint32_t V, uint32_t nearest) {
    /* Preserve hardware alpha test, translucent edges and transparent cutouts.
       Only blend RGB across fully opaque texels. Coordinates have 19 frac bits. */
    if (!gx_texture_filter || (nearest >> 24) != 31) return nearest;
    U -= 1u << 18; V -= 1u << 18;
    uint16_t u = (uint16_t)((int16_t)(U >> 16) >> 3);
    uint16_t v = (uint16_t)((int16_t)(V >> 16) >> 3);
    unsigned x=(U>>11)&255u, y=(V>>11)&255u;
    uint32_t c[4]={az_texel(p,u,v),az_texel(p,u+1,v),az_texel(p,u,v+1),az_texel(p,u+1,v+1)};
    unsigned w[4], div;
    if (gx_texture_filter==3) {
        div=256;
        if (x+y<=256) { w[0]=256-x-y; w[1]=x; w[2]=y; w[3]=0; }
        else { w[0]=0; w[1]=256-y; w[2]=256-x; w[3]=x+y-256; }
    } else {
        div=65536; w[0]=(256-x)*(256-y); w[1]=x*(256-y); w[2]=(256-x)*y; w[3]=x*y;
    }
    for (unsigned i=0;i<4;i++) if (w[i] && (c[i]>>24)!=31) return nearest;
    uint32_t result=31u<<24;
    for (unsigned ch=0;ch<24;ch+=8) {
        unsigned sum=0;
        for (unsigned i=0;i<4;i++) sum+=((c[i]>>ch)&63u)*w[i];
        result|=((sum+div/2)/div)<<ch;
    }
    return result;
}

int use_neon = 2;''')
edit(g/"fused.c","uint32_t tr = t & 0xff, tg = (t >> 8) & 0xff, tb = (t >> 16) & 0xff, ta = t >> 24;",
    '''if (m && P->mode != 3) t = az_filtered(P, U0 + (uint32_t)(du * st), V0 + (uint32_t)(dv * st), t);
            uint32_t tr = t & 0xff, tg = (t >> 8) & 0xff, tb = (t >> 16) & 0xff, ta = t >> 24;''')
edit(g/"fused.c","    /* batches: runs of lines with pixels,",
    '''    /* Filtered polygons use the scalar reference path; nearest and
       untextured polygons retain the existing assembly acceleration. */
    if (gx_texture_filter && (flags & 2) && P.mode != 3) bf = 0;
    /* batches: runs of lines with pixels,''')
print("BananaDS native polygon texture filtering source patch applied")
