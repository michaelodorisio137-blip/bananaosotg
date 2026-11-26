#!/usr/bin/env python3
"""Copy original libretro cheat data, preserving region/revision/format and license."""
import sys, pathlib, shutil, json, hashlib
src, dst=map(pathlib.Path,sys.argv[1:])
root=dst/"usr/share/libretro/cheats"
root.mkdir(parents=True,exist_ok=True)
counts={}
for p in sorted((src/"cht").rglob("*.cht")):
    if p.is_symlink() or not p.is_file(): continue
    rel=p.relative_to(src/"cht")
    if len(rel.parts)<2: continue
    out=root/rel
    out.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(p,out)
    counts[rel.parts[0]]=counts.get(rel.parts[0],0)+1
assert len(counts)>=40 and sum(counts.values())>10000, counts
for p in src.glob("LICENSE*"):
    if p.is_file(): shutil.copyfile(p,root/p.name)
(root/"AZEEZOS-DATABASE.json").write_text(json.dumps({"source":"https://github.com/libretro/libretro-database","commit":"f89f09cbe13f9f7863ecf20d0ebf2c5ce53be029","systems":counts,"files":sum(counts.values())},indent=2)+"\n")
print(json.dumps(counts,indent=2))
print("PASS:",sum(counts.values()),"files,",len(counts),"systems")
