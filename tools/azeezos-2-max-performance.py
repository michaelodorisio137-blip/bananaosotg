#!/usr/bin/env python3
"""Force maximum supported CPU/GPU performance during emulator sessions."""
from pathlib import Path
import re, sys, subprocess
root=Path(sys.argv[1])
base=root/"usr/libexec/banana"
for name in ("run-retroarch","run-bananafront","run-drastic","run-bananads",
             "run-nds","run-ps1","run-gw","run-pico8"):
    p=base/name
    s=p.read_text()
    mark="# AzeezOS maximum emulator performance"
    if mark not in s:
        assert s.startswith("#!/bin/sh\n"), str(p)
        s=s.replace("#!/bin/sh\n","#!/bin/sh\n"+mark+"\n/usr/bin/banana-perf performance\n",1)
    if name=="run-drastic":
        s=re.sub(r'^export DSFLIP_CPUGOV=.*$',"export DSFLIP_CPUGOV=0",s,flags=re.M)
        if "# AzeezOS override DS governor" not in s:
            lines=s.splitlines(keepends=True)
            matches=[i for i,l in enumerate(lines) if l.startswith("kv_export /data/banana/superdrastic.conf DSFLIP_ DSHOOK_")]
            assert len(matches)==1, str(p)
            lines.insert(matches[0]+1,"# AzeezOS override DS governor\nexport DSFLIP_CPUGOV=0\n")
            s="".join(lines)
    elif name=="run-bananads":
        anchor="kv_export /data/banana/bananads.env BANANADS_ MELONDS_"
        if "# AzeezOS override BananaDS governor" not in s:
            assert s.count(anchor)==1
            s=s.replace(anchor,anchor+"\n# AzeezOS override BananaDS governor\nexport BANANADS_CPUGOV=off",1)
    elif name=="run-bananafront":
        s=re.sub(r'^.*setting bananafront_cpugov.*set -- --cpugov.*$',"# AzeezOS: disable per-game adaptive CPU cap",s,flags=re.M)
    p.write_text(s)
    subprocess.run(["sh","-n",str(p)],check=True)
p=root/"etc/banana/systems.conf"
s=p.read_text()
def update(m):
    section=m.group(0)
    if not re.search(r'^run\s*=\s*/usr/libexec/banana/run-(?:retroarch|nds|drastic|bananads|bananafront|ps1|gw|pico8)\b',section,re.M):
        return section
    if re.search(r'^perf\s*=',section,re.M):
        return re.sub(r'^perf\s*=.*$',"perf = performance",section,flags=re.M)
    return section.rstrip()+"\nperf = performance\n\n"
p.write_text(re.sub(r'^\[[^\]\n]+\]\n(?:(?!^\[)[\s\S])*',update,s,flags=re.M))
perf=(root/"usr/bin/banana-perf").read_text()
assert re.search(r'performance\)\s+cpu performance \$hi; gpu performance',perf)
assert "DSFLIP_CPUGOV=0" in (base/"run-drastic").read_text()
assert "BANANADS_CPUGOV=off" in (base/"run-bananads").read_text()
assert not re.search(r'^.*set -- --cpugov', (base/"run-bananafront").read_text(),re.M)
print("Maximum emulator clock profiles and adaptive governor overrides verified")
