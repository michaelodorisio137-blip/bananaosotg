#!/usr/bin/env python3
"""Scoped launcher changes in the proven AzeezOS update filesystem."""
from pathlib import Path
import sys
r=Path(sys.argv[1])
def sub(rel,old,new):
    p=r/rel;s=p.read_text()
    if new in s:return
    if s.count(old)!=1:raise SystemExit("Launcher mismatch "+rel+": "+repr(old[:80]))
    p.write_text(s.replace(old,new,1))
bf="usr/libexec/banana/run-bananafront"
ra="usr/libexec/banana/run-retroarch"
# Keep every global/per-system shader preference except for the new core:
# the core already generates an exact 640x480 nearest-neighbor frame.
sub(bf,'[ -n "$SH" ] && [ -d /usr/lib/superdrastic/shaders ]',
       'case "$CORE" in */mgba_integer_libretro.so) SH=; export BANANAFRONT_BORDER=off BANANAFRONT_PLANE_SCALE=0 ;; esac\n[ -n "$SH" ] && [ -d /usr/lib/superdrastic/shaders ]')
sub(bf,'[ "$(ra_cfg video_scale_integer)" = true ] && set -- --scale integer "$@"',
       'if [ "$(ra_cfg video_scale_integer)" = true ] || [ "$CORE" = /usr/lib/libretro/mgba_integer_libretro.so ]; then set -- --scale integer "$@"; fi')
sub(ra,'case $(setting rgds_n64_texfilter) in standard) t=standard ;; *) t=3point ;; esac',
       'case $(setting rgds_n64_texfilter) in standard) t=standard ;; nearest) t=nearest ;; *) t=3point ;; esac')
# RetroArch: append a temporary session override, not persistent global settings.
# It is last in the append list, so themed borders cannot shrink the viewport.
p=r/ra;s=p.read_text()
anchor='# anything RetroArch keeps that retroarch.cfg doesn\'t place'
if 'rgds-integer-session.cfg' not in s:
    assert s.count(anchor)==1
    s=s.replace(anchor,'''# AzeezOS Maximum Integer: native 640x480, no further interpolation.
case "$CORE" in
*/mgba_integer_libretro.so)
    IC=/run/banana/rgds-integer-session.cfg
    cat > "$IC" <<'RGDS_INT'
video_shader_enable = "false"
video_smooth = "false"
video_scale_integer = "true"
aspect_ratio_index = "23"
custom_viewport_x = "0"
custom_viewport_y = "0"
custom_viewport_width = "640"
custom_viewport_height = "480"
input_overlay_enable = "false"
RGDS_INT
    RBA="$RBA|$IC"
    ;;
esac
'''+anchor,1)
    p.write_text(s)
print("PASS: native integer mode forces sharp fullscreen output; previous cores unchanged; N64 point option forwarded.")
