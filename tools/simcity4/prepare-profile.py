#!/usr/bin/env python3
"""Copy an original SC4 installation into an isolated test profile. No writes to source."""
import argparse, hashlib, json, os, shutil, struct, tempfile
from pathlib import Path
REQUIRED=["SimCity_"+str(i)+".dat" for i in range(1,6)]+["EP1.dat","Sound.dat"]
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def dbpf(p):
    with p.open("rb") as f: h=f.read(96)
    if len(h)<64 or h[:4]!=b"DBPF": raise ValueError("Invalid DBPF header: "+str(p))
    count,offset,size=struct.unpack_from("<III",h,36)
    if offset+size>p.stat().st_size: raise ValueError("Invalid DBPF index: "+str(p))
    return {"index_count":count,"index_offset":offset,"index_size":size}
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("installation",type=Path)
    ap.add_argument("profile",type=Path)
    ap.add_argument("--documents",type=Path,help="Optional separate Documents/SimCity 4 directory")
    a=ap.parse_args()
    src=a.installation.resolve(strict=True); dst=a.profile.resolve()
    if dst.exists() or src==dst or src in dst.parents or dst in src.parents: raise ValueError("Use a new, separate profile directory")
    if a.documents:
        docs=a.documents.resolve(strict=True)
        if docs==dst or docs in dst.parents or dst in docs.parents: raise ValueError("Documents and output must be separate")
    for name in REQUIRED:
        dbpf(src/name)
    dst.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(tempfile.mkdtemp(prefix=".sc4-profile-",dir=dst.parent))
    try:
        game=tmp/"GameData"; game.mkdir()
        entries=[]
        for base, target, names in [(src,game,None)]+([(docs,tmp/"UserData",{"Regions","Plugins"})] if a.documents else []):
            target.mkdir(exist_ok=True)
            seen=set()
            for p in sorted(base.rglob("*")):
                rel=p.relative_to(base)
                if names and rel.parts[0] not in names: continue
                if p.is_symlink(): raise ValueError("Refusing symlink: "+str(p))
                if p.is_dir(): continue
                if not p.is_file(): raise ValueError("Unexpected file type: "+str(p))
                key=str(rel).casefold()
                if key in seen: raise ValueError("Case collision: "+str(p))
                seen.add(key)
                out=target/rel;out.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(p,out)
                digest=sha(p)
                if sha(out)!=digest: raise IOError("Copy hash mismatch: "+str(p))
                item={"path":str(out.relative_to(tmp)),"bytes":p.stat().st_size,"sha256":digest}
                if p.suffix.lower() in {".sc4",".sc4lot",".sc4model",".sc4desc",".dat"}:
                    try: item["dbpf"]=dbpf(p)
                    except ValueError as e: item["warning"]=str(e)
                if p.suffix.lower()==".dll" and rel.parts[0].casefold()=="plugins": item["warning"]="Windows DLL requires a native equivalent"
                entries.append(item)
        (tmp/"inventory.json").write_text(json.dumps(entries,indent=2)+"\n")
        (tmp/"home").mkdir()
        tmp.rename(dst)
        print("Prepared",dst,"files:",len(entries),"city files:",sum(e["path"].lower().endswith(".sc4") for e in entries))
        print("Original files untouched; inventory includes SHA256 and DBPF index bounds.")
    finally:
        if tmp.exists(): shutil.rmtree(tmp)
if __name__=="__main__": main()
