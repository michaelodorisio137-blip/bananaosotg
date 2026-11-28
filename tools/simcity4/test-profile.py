#!/usr/bin/env python3
"""Verify exact preservation and isolation with synthetic DBPF fixtures."""
import hashlib, json, struct, subprocess, sys, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as root:
    root=Path(root); source=root/"original"; source.mkdir(); docs=root/"documents";docs.mkdir(); out=root/"profile"
    def put(p, suffix=b""):
        p.parent.mkdir(parents=True,exist_ok=True)
        b=bytearray(96);b[:4]=b"DBPF";struct.pack_into("<III",b,36,0,96,0)
        p.write_bytes(b+suffix)
    for n in ["SimCity_"+str(i)+".dat" for i in range(1,6)]+["EP1.dat","Sound.dat"]:put(source/n)
    put(source/"Plugins"/"landmark.SC4Model",b"model")
    put(source/"Regions"/"London"/"City - Kensington.sc4",b"city")
    put(docs/"Plugins"/"network.dat",b"network")
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for base in (source,docs) for p in base.rglob("*") if p.is_file()}
    subprocess.run([sys.executable,str(Path(__file__).with_name("prepare-profile.py")),str(source),str(out),"--documents",str(docs)],check=True)
    assert (out/"GameData/Plugins/landmark.SC4Model").read_bytes()==(source/"Plugins/landmark.SC4Model").read_bytes()
    assert (out/"UserData/Plugins/network.dat").read_bytes()==(docs/"Plugins/network.dat").read_bytes()
    city=out/"UserData/Regions/London/City - Kensington.sc4"
    assert city.read_bytes()==(source/"Regions/London/City - Kensington.sc4").read_bytes()
    city.write_bytes(b"changed")
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in before.items())
    assert len(json.loads((out/"inventory.json").read_text()))==10
    print("PASS: profile copies, DBPF bounds, separate user plugins, original source isolation")
