#!/usr/bin/env python3
"""DS themes, default sharp + image adjustment shader, custom OTA feed."""
from pathlib import Path
import sys,json,re,colorsys
R=Path(sys.argv[1])
def P(x):
 p=R/x
 if not p.exists():raise RuntimeError("Missing "+x)
 return p
def sub(x,a,b):
 p=P(x);s=p.read_text()
 if b in s:return
 if s.count(a)!=1:raise RuntimeError("Upstream mismatch: "+x+": "+a[:60])
 p.write_text(s.replace(a,b,1))
td=P("usr/share/banana/themes")
src=td/"rgds-ds-classic.json"
t=json.loads(src.read_text());t["name"]="DS Original - Blue"
src.write_text(json.dumps(t,indent=2)+"\n")
colors={"Red":"#ce5363","Pink":"#dd8db6","Orange":"#d89745","Yellow":"#c2a63c","Green":"#4eaa76","Aqua":"#4aaca6","Purple":"#8865bd","Lavender":"#a88bd7","Brown":"#94745d","Gray":"#858d9a","Black":"#454957"}
def hue(v,target):
 if isinstance(v,dict):return {k:hue(w,target) for k,w in v.items()}
 if isinstance(v,list):return [hue(w,target) for w in v]
 if not isinstance(v,str) or not re.fullmatch(r"#[0-9a-fA-F]{6}",v):return v
 h,l,s=colorsys.rgb_to_hls(*[int(v[i:i+2],16)/255 for i in (1,3,5)])
 if not (0.50<h<0.70 and s>0.1):return v
 hh,ll,ss=colorsys.rgb_to_hls(*[int(target[i:i+2],16)/255 for i in (1,3,5)])
 return "#"+"".join("%02x"%round(255*z) for z in colorsys.hls_to_rgb(hh,l,min(1,s*max(0.55,ss/0.4))))
for name,color in colors.items():
 v=hue(t,color);v["name"]="DS Original - "+name;v["accent"]=color
 (td/("rgds-ds-"+name.lower()+".json")).write_text(json.dumps(v,indent=2)+"\n")
darkmap={"#eaf2fa":"#151e2b","#ffffff":"#202d3d","#bcd9ed":"#293e56","#87aac9":"#3b536e","#e3edf6":"#26364a","#cdddea":"#2b3a4b","#b7c9dc":"#44566d","#fafcff":"#263648","#8faac8":"#526e8c","#cae0f2":"#314660","#a8cae8":"#3e5e82","#243a50":"#f0f3f8","#607689":"#b8c9dd","#294f73":"#cce2ff","#253f59":"#ebf0f8","#667e92":"#b3c1d4","#405b73":"#d9e2f0","#68869e":"#a3bad0","#273c51":"#dceaff","#395d7d":"#a1c4e8","#23466b":"#e2edff","#22445f":"#e2edff","#42627c":"#cadbec","#173d63":"#eff5ff","#3f5b74":"#bfcfdf","#598fc1":"#87b9ec"}
def dark(v):
 if isinstance(v,dict):return {k:dark(w) for k,w in v.items()}
 if isinstance(v,list):return [dark(w) for w in v]
 return darkmap.get(v.lower(),v) if isinstance(v,str) else v
v=dark(t);v.update(name="DS Dark Mode",base="dark",accent="#87b9ec")
v["colors"]={"screenBg":"#151e2b","ink":"#f0f3f8","muted":"#b8c9dd"}
v["vars"].update(bg="#151e2b",card="#202d3d",ink="#f0f3f8",soft="#b8c9dd",hi="#87b9ec")
(td/"rgds-ds-dark.json").write_text(json.dumps(v,indent=2)+"\n")
out=P("usr/share/libretro/shaders/glsl")/"rgds";out.mkdir(exist_ok=True)
(out/"sharp-image-adjust.glslp").write_text("""# RG DS full-screen Sharp Bilinear then Image Adjustment GLSL
shaders = "2"
shader0 = "../interpolation/shaders/sharp-bilinear-simple.glsl"
filter_linear0 = "true"
scale_type0 = "viewport"
scale0 = "1.0"
shader1 = "../misc/shaders/image-adjustment.glsl"
filter_linear1 = "false"
scale_type1 = "viewport"
scale1 = "1.0"
ia_target_gamma = "2.2"
ia_monitor_gamma = "2.2"
ia_saturation = "1.0"
ia_contrast = "1.0"
ia_luminance = "1.0"
ia_black_level = "0.0"
ia_bright_boost = "0.0"
""")
sd=P("usr/lib/superdrastic/shaders")
sharp=sd/"sharp-bilinear.frag"
if not sharp.exists():raise RuntimeError("Missing BananaFront sharp shader")
frag=sharp.read_text();i=frag.rfind("}")
if i<0:raise RuntimeError("Invalid GLSL source")
(sd/"rgds-sharp-adjust.frag").write_text(frag[:i]+"\n    gl_FragColor.rgb = clamp(gl_FragColor.rgb, 0.0, 1.0); // neutral image adjustment\n"+frag[i:])
sub("usr/libexec/banana/run-retroarch","    sharp) SP=interpolation/sharp-bilinear-simple.glslp ;;","    sharp) SP=interpolation/sharp-bilinear-simple.glslp ;;\n    sharpadjust) SP=rgds/sharp-image-adjust.glslp ;;")
sub("usr/libexec/banana/run-bananafront","sharp) SH=sharp-bilinear ;;","sharp) SH=sharp-bilinear ;; sharpadjust) SH=rgds-sharp-adjust ;;")
cfg=P("etc/banana/settings.conf");txt=cfg.read_text()
if "ra_shader = sharpadjust" not in txt:
 txt=re.sub(r"(?m)^ra_shader = .*","ra_shader = sharpadjust",txt,count=1)
 txt+="\nrgds_update_channel = custom\n"
 cfg.write_text(txt)
migration="""
# RG DS next firmware: migrate stock shader preference once on existing SD cards.
if [ ! -f "$D/banana/.rgds-sharp-adjust-v2" ]; then
  S="$D/banana/settings.conf"
  [ -f "$S" ] && sed -i 's/^ra_shader = off *$/ra_shader = sharpadjust/' "$S"
  rm -f "$D/banana/.ra-shader"
  touch "$D/banana/.rgds-sharp-adjust-v2"
fi
"""
sub("usr/libexec/banana/data-layout","exit 0",migration+"\nexit 0")
up=P("usr/libexec/banana/update")
s=up.read_text()
ln=next((x for x in s.splitlines() if x.startswith("FEED=")),None)
if not ln:raise RuntimeError("No update FEED")
new="""# RG DS OTA: default custom GitHub releases, official channel selectable.
case $(sed -n 's/^ *rgds_update_channel *= *//p' "$DATA/settings.conf" 2>/dev/null | tail -1) in
official) RGDS_FEED=https://api.github.com/repos/JorreFog/BananaLinux/releases?per_page=10 ;;
*) RGDS_FEED=https://api.github.com/repos/michaelodorisio137-blip/bananaosotg/releases?per_page=10 ;;
esac
FEED=$RGDS_FEED
[ -n "$BANANA_UPDATE_FEED" ] && FEED=$BANANA_UPDATE_FEED"""
if "RGDS_FEED=" not in s:up.write_text(s.replace(ln,new,1))
print("OK: DS 13 color themes; RetroArch combined shader; BananaFront equivalent; custom OTA.")
