#!/usr/bin/env python3
"""Install the native R4 database used by DraStic, keeping any existing user file."""
from pathlib import Path
import sys, shutil, struct, hashlib
src,root=map(Path,sys.argv[1:])
p=src/"Cheat Databases/usrcheat.dat"
with p.open("rb") as f:
    assert f.read(12)==b"R4 CheatCode", "invalid R4 cheat header"
assert p.stat().st_size>1_000_000
out=root/"usr/share/drastic"
out.mkdir(parents=True,exist_ok=True)
shutil.copyfile(p,out/"usrcheat.dat")
shutil.copyfile(src/"LICENSE",out/"usrcheat.LICENSE")
(out/"usrcheat.SOURCE").write_text("https://github.com/szTheory/NDS-Cheat-Databases/tree/0173af14d33e2c045e7c5e30c71d369624a33020\n")
launcher=root/"usr/libexec/banana/run-drastic"
if launcher.exists():
    s=launcher.read_text()
    anchor="cd $D\n"
    add='''# Install native DraStic cheats once; do not overwrite the player's saved database.
if [ ! -s "$D/usrcheat.dat" ] && [ -s /usr/share/drastic/usrcheat.dat ]; then
    cp /usr/share/drastic/usrcheat.dat "$D/usrcheat.dat.new" &&
        mv "$D/usrcheat.dat.new" "$D/usrcheat.dat"
fi
'''
    assert s.count(anchor)==1
    launcher.write_text(s.replace(anchor,add+anchor))
print("PASS: DraStic R4 database",p.stat().st_size,"bytes",hashlib.sha256(p.read_bytes()).hexdigest())
