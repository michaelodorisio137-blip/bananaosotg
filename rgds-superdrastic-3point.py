#!/usr/bin/env python3
"""Generate real N64-style three-point texture filtering in SuperDrastic's 3D NEON renderer.

Pinned SuperDrastic source contains nearest (0) and four-tap bilinear (1/2).
This adds a third compiled shader kernel path, mode 3, using 8-bit integer
triangular interpolation: each fragment blends exactly three neighboring
texture texels (or the transparent-cutout nearest fallback).
No finished-screen postprocess is involved.

Runs during the Buildroot SuperDrastic BUILD_CMDS before kerngen.py.
Fail closed when upstream changes, to avoid patching unexpected internals.
"""
from pathlib import Path
import sys
if len(sys.argv) != 2:
    sys.exit("Usage: python3 rgds-superdrastic-3point.py <SuperDrastic-source-dir>")
root = Path(sys.argv[1])

def sub(p, before, after, times=1):
    text = p.read_text()
    if after in text: return
    if text.count(before) != times:
        sys.exit("SuperDrastic pinned-source mismatch at " + str(p) + ": " + before[:65])
    p.write_text(text.replace(before, after))

gen = root / "src/rast/kerngen.py"
asm = root / "src/rast/fused_asm.c"
if not (gen.is_file() and asm.is_file()):
    sys.exit("SuperDrastic Gengis assembler sources missing")

sub(gen, "def texture_bilinear(T):", "def texture_bilinear(T, threepoint=False):")
sub(gen, 'if B: texture_bilinear(T)', 'if B: texture_bilinear(T, threepoint=(B == 2))')
sub(gen, "for B in range(2 if T else 1):", "for B in range(3 if T else 1):", times=2)
sub(gen,
'''    e("movi v24.8b, #8"); e("sub v29.8b, v24.8b, v10.8b"); e("sub v30.8b, v24.8b, v11.8b")
    e("umull v24.8h, v29.8b, v30.8b"); e("xtn v24.8b, v24.8h"); e("str d24, [sp, #192]")
    e("umull v24.8h, v10.8b, v30.8b"); e("xtn v24.8b, v24.8h"); e("str d24, [sp, #200]")
    e("umull v24.8h, v29.8b, v11.8b"); e("xtn v24.8b, v24.8h"); e("str d24, [sp, #208]")
    e("umull v24.8h, v10.8b, v11.8b"); e("xtn v24.8b, v24.8h"); e("str d24, [sp, #216]")
''',
'''    e("movi v24.8b, #8"); e("sub v29.8b, v24.8b, v10.8b"); e("sub v30.8b, v24.8b, v11.8b")
    if threepoint:
        # Let u,v be fractions 0..7. Four triangular corner weights sum to 8;
        # convert to 0..64 for the original four-sample accumulation (/64).
        # bottom-left diagonal: w00=max(8-u-v,0), w10=min(u,8-v),
        # w01=min(v,8-u), w11=max(u+v-8,0). Only three can be nonzero.
        e("add v21.8b, v10.8b, v11.8b")
        e("uqsub v24.8b, v24.8b, v21.8b")
        e("shl v24.8b, v24.8b, #3"); e("str d24, [sp, #192]")
        e("umin v24.8b, v10.8b, v30.8b")
        e("shl v24.8b, v24.8b, #3"); e("str d24, [sp, #200]")
        e("umin v24.8b, v11.8b, v29.8b")
        e("shl v24.8b, v24.8b, #3"); e("str d24, [sp, #208]")
        e("movi v24.8b, #8"); e("uqsub v24.8b, v21.8b, v24.8b")
        e("shl v24.8b, v24.8b, #3"); e("str d24, [sp, #216]")
    else:
        e("umull v24.8h, v29.8b, v30.8b"); e("xtn v24.8b, v24.8h"); e("str d24, [sp, #192]")
        e("umull v24.8h, v10.8b, v30.8b"); e("xtn v24.8b, v24.8h"); e("str d24, [sp, #200]")
        e("umull v24.8h, v29.8b, v11.8b"); e("xtn v24.8b, v24.8h"); e("str d24, [sp, #208]")
        e("umull v24.8h, v10.8b, v11.8b"); e("xtn v24.8b, v24.8h"); e("str d24, [sp, #216]")
''')

sub(asm,
    "#define KB(P, D, T, R) extern kern_fn P##D##T##R##00, P##D##T##R##10, P##D##T##R##01, P##D##T##R##11;",
    "#define KB(P, D, T, R) extern kern_fn P##D##T##R##00, P##D##T##R##10, P##D##T##R##01, P##D##T##R##11, P##D##T##R##02, P##D##T##R##12;")
sub(asm,
    "#define KS(P, T) extern kern_fn P##s##T##00, P##s##T##01, P##s##T##10, P##s##T##11;",
    "#define KS(P, T) extern kern_fn P##s##T##00, P##s##T##01, P##s##T##02, P##s##T##10, P##s##T##11, P##s##T##12;")
sub(asm,
r'''#define KR0(P, D, T) { { { &P##D##T##000, &P##D##T##000 }, { &P##D##T##010, &P##D##T##010 } }, \
                       { { &P##D##T##100, &P##D##T##100 }, { &P##D##T##110, &P##D##T##110 } } }
#define KR(P, D, T) { { { &P##D##T##000, &P##D##T##001 }, { &P##D##T##010, &P##D##T##011 } }, \
                      { { &P##D##T##100, &P##D##T##101 }, { &P##D##T##110, &P##D##T##111 } } }''',
r'''#define KR0(P, D, T) { { { &P##D##T##000, &P##D##T##000, &P##D##T##000 }, { &P##D##T##010, &P##D##T##010, &P##D##T##010 } }, \
                       { { &P##D##T##100, &P##D##T##100, &P##D##T##100 }, { &P##D##T##110, &P##D##T##110, &P##D##T##110 } } }
#define KR(P, D, T) { { { &P##D##T##000, &P##D##T##001, &P##D##T##002 }, { &P##D##T##010, &P##D##T##011, &P##D##T##012 } }, \
                      { { &P##D##T##100, &P##D##T##101, &P##D##T##102 }, { &P##D##T##110, &P##D##T##111, &P##D##T##112 } } }''')
sub(asm,
    "#define KSR(P, T) { { &P##s##T##00, &P##s##T##01 }, { &P##s##T##10, &P##s##T##11 } }",
    "#define KSR(P, T) { { &P##s##T##00, &P##s##T##01, &P##s##T##02 }, { &P##s##T##10, &P##s##T##11, &P##s##T##12 } }")
sub(asm,
    "kern_fn *const kernels[3][5][2][2][2];",
    "kern_fn *const kernels[3][5][2][2][3];")
sub(asm,
    "kern_fn *const shade[5][2][2];",
    "kern_fn *const shade[5][2][3];")
sub(asm,
    "int rast_texfilter;             /* 0 nearest (exact), 1 bilinear, 2 sharp bilinear */",
    "int rast_texfilter;             /* 0 nearest, 1 bilinear, 2 sharp bilinear, 3 true 3point */")
sub(asm,
    "[T && rast_texfilter ? 1 : 0]",
    "[T ? (rast_texfilter == 3 ? 2 : rast_texfilter ? 1 : 0) : 0]",
    times=2)
print("Patched SuperDrastic Gengis AArch64 texture kernel generator: 3-point is a native sample mode.")
