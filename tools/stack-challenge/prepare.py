#!/usr/bin/env python3
"""Prepare original LCD segment atlas from upstream SVG. Host only."""
import copy, io, json, re, shutil, sys
from pathlib import Path
import xml.etree.ElementTree as E
import cairosvg
from PIL import Image
src=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
(out/'cores').mkdir(exist_ok=True)
(out/'cores/__init__.py').write_text('')
for n in ('E0C6200.py','E0C6200sound.py','rom.py'):
    shutil.copy2(src/'cores'/n,out/'cores'/n)
shutil.copy2(Path(__file__).with_name('stack.py'),out/'stack.py')
shutil.copy2(src/'LICENSE',out/'LICENSE.BrickEmuPy')
svg=E.parse(src/'assets/RadioShackStackChallenge.svg').getroot()
ns='{http://www.w3.org/2000/svg}'
ids=[e.get('id') for e in svg.iter() if re.fullmatch(r'\d+_\d+',e.get('id',''))]
assert len(ids)>100,len(ids)
# Crop to the original LCD reflector. Maintain aspect ratio.
W,H=358,480;X=(640-W)//2
def raster(root):
    root.set('width',str(W));root.set('height',str(H))
    root.set('viewBox','956.562 398.994 2378.438 3184.536')
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=E.tostring(root),output_width=W,output_height=H))).convert('RGBA')
def save(im,name):
    box=im.getbbox()
    assert box,name
    im.crop(box).tobytes()
    (out/name).write_bytes(im.crop(box).tobytes())
    return {'file':name,'rect':[X+box[0],box[1],box[2]-box[0],box[3]-box[1]]}
bg=copy.deepcopy(svg)
for e in bg.iter():
    if e.get('id') in ids:e.set('display','none')
result={'background':save(raster(bg),'background.rgba'),'segments':[]}
# Numeric segment elements are the exact original LCD mapping.
for ident in ids:
    root=E.Element(ns+'svg')
    for defs in svg.findall(ns+'defs'):root.append(copy.deepcopy(defs))
    def visit(e,parents):
        if e.get('id')==ident:
            here=root
            for p in parents:
                if p.tag==ns+'g':
                    child=E.SubElement(here,p.tag,{k:v for k,v in p.attrib.items() if k!='id'})
                    here=child
            here.append(copy.deepcopy(e))
            return True
        return any(visit(c,parents+[e]) for c in e)
    assert visit(svg,[])
    im=raster(root)
    if not im.getbbox():continue
    index,bit=map(int,ident.split('_'))
    result['segments'].append({'index':index,'bit':bit,**save(im,ident+'.rgba')})
assert len(result['segments'])>100
(out/'display.json').write_text(json.dumps(result))
print('LCD segments:',len(result['segments']))
