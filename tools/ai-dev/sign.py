#!/usr/bin/env python3
"""Explicit human review gate: sign exactly the selected successful proposal."""
import hashlib,json,os,re,subprocess,tempfile,shutil
from pathlib import Path
rid=os.environ.get("APPROVE_RUN","")
if not re.fullmatch("[0-9]{1,20}",rid):raise SystemExit("Numeric proposal run ID required")
key=os.environ.get("AZEEZOS_SIGNING_KEY","")
if not key:raise SystemExit("Configure the review environment signing key first")
repo="michaelodorisio137-blip/bananaosotg"
run=json.loads(subprocess.check_output(["gh","api",f"repos/{repo}/actions/runs/{rid}"]))
m=re.fullmatch("AzeezOS AI ([a-f0-9]{32})",run.get("display_title",""))
if not m or run.get("conclusion")!="success" or run.get("head_branch")!="azeezos-2.0" or run.get("event")!="workflow_dispatch" or run.get("path")!=".github/workflows/validate-custom.yml":
    raise SystemExit("Not a successful matching AI proposal")
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp)
    subprocess.run(["gh","run","download",rid,"-R",repo,"-n","AzeezOS-AI-Proposal-UNREVIEWED","-D",str(d)],check=True)
    tar=list(d.glob("*.update.tar"))
    if len(tar)!=1 or tar[0].stat().st_size>256*1024*1024:raise SystemExit("Invalid proposal artifact")
    with open(tar[0],"rb") as f: digest=hashlib.file_digest(f,"sha256").hexdigest()
    out=Path("reviewed-output");out.mkdir(exist_ok=True)
    shutil.copyfile(tar[0],out/"firmware.update.tar")
    (out/"manifest.json").write_text(json.dumps({"board":"rgds","request_id":m.group(1),"proposal_run":int(rid),"sha256":digest},sort_keys=True)+"\n")
    pem=d/"private.pem";pem.write_text(key);pem.chmod(0o600)
    subprocess.run(["openssl","dgst","-sha256","-sign",str(pem),"-out",str(out/"manifest.sig"),str(out/"manifest.json")],check=True)
    pem.unlink()
print("Signed explicitly selected proposal",rid)
