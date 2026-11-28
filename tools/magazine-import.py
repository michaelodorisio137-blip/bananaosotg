#!/usr/bin/env python3
"""Import owned PDF/CBZ pages into an AzeezOS magazines shelf. Requires Pillow; PDF requires PyMuPDF."""
import argparse, csv, re, shutil, tempfile, zipfile
from pathlib import Path
from PIL import Image, ImageOps
from io import BytesIO
Image.MAX_IMAGE_PIXELS=60_000_000
def natural(s): return [int(x) if x.isdigit() else x.casefold() for x in re.split(r'(\d+)',s)]
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive",type=Path)
    ap.add_argument("magazines_folder",type=Path)
    ap.add_argument("--rom",default="",help="Exact ROM path on RG DS; optional")
    ap.add_argument("--links",type=Path,help="CSV: page (1-based),rom (absolute RG DS path)")
    ap.add_argument("--title")
    a=ap.parse_args()
    def valid(s):
        if s and (not s.startswith("/") or any(c in s for c in "\r\n\t\0")): raise ValueError("ROM path must be absolute")
        return s
    rom=valid(a.rom)
    links={}
    if a.links:
        with a.links.open(newline="",encoding="utf-8-sig") as f:
            for row in csv.DictReader(f): links[int(row["page"])]=valid(row["rom"])
    title=a.title or a.archive.stem
    safe=re.sub(r'[<>:"/\\|?*\x00-\x1f]',"_",title).strip(" .")
    if not safe: raise ValueError("Empty title")
    a.magazines_folder.mkdir(parents=True,exist_ok=True)
    dest=a.magazines_folder/safe
    if dest.exists(): raise FileExistsError(dest)
    tmp=Path(tempfile.mkdtemp(prefix=".import-",dir=a.magazines_folder))
    try:
        pages=tmp/"pages";pages.mkdir(); rows=[]
        def save(im):
            if len(rows)>=2048: raise ValueError("Maximum 2048 pages")
            im=ImageOps.exif_transpose(im).convert("RGB");im.thumbnail((1600,2000))
            n=len(rows)+1;name=f"pages/{n:04d}.jpg"
            im.save(tmp/name,quality=88,optimize=True)
            rows.append(name+("\t"+links[n] if links.get(n) else ""))
            if n==1:
                media=tmp.parent/"media"/"box";media.mkdir(parents=True,exist_ok=True)
        ext=a.archive.suffix.lower()
        if ext==".pdf":
            import fitz
            with fitz.open(a.archive) as doc:
                for pg in doc:
                    factor=min(1600/pg.rect.width,2000/pg.rect.height)
                    pix=pg.get_pixmap(matrix=fitz.Matrix(factor,factor),alpha=False,colorspace=fitz.csRGB)
                    save(Image.frombytes("RGB",(pix.width,pix.height),pix.samples))
        elif ext in (".cbz",".zip"):
            with zipfile.ZipFile(a.archive) as z:
                for name in sorted(z.namelist(),key=natural):
                    if Path(name).suffix.lower() in (".jpg",".jpeg",".png",".webp") and not name.startswith("__MACOSX/"):
                        if z.getinfo(name).file_size>50*1024*1024: raise ValueError("Oversized archive entry")
                        with Image.open(BytesIO(z.read(name))) as im: save(im)
        else: raise ValueError("Supported input: PDF, CBZ, ZIP")
        if not rows: raise ValueError("No pages")
        (tmp/(safe+".guide")).write_text(rom+"\n"+"\n".join(rows)+"\n",encoding="utf-8")
        tmp.rename(dest)
        print(dest)
    finally:
        if tmp.exists(): shutil.rmtree(tmp)
if __name__=="__main__": main()
