#!/usr/bin/env python3
"""Stage a separately reviewed, signed AI firmware update. Never apply or reboot here."""
import hashlib,json,os,re,shutil,subprocess,sys,tempfile,urllib.request,urllib.parse,zipfile
from pathlib import Path
BASE="https://api.github.com/repos/michaelodorisio137-blip/bananaosotg"
CAP=256*1024*1024
def api(path,token):
    q=urllib.request.Request(BASE+path,headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","User-Agent":"AzeezOS"})
    with urllib.request.urlopen(q,timeout=30) as r:
        b=r.read(2*1024*1024+1)
    if len(b)>2*1024*1024:raise RuntimeError("Oversized GitHub response")
    return json.loads(b)
class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        p=urllib.parse.urlparse(newurl)
        if p.scheme!="https" or not p.hostname or p.username or p.password:raise RuntimeError("Unsafe download redirect")
        # No Authorization header crosses to the object storage host.
        return urllib.request.Request(newurl,headers={"User-Agent":"AzeezOS"})
def download(aid,token,path):
    q=urllib.request.Request(BASE+"/actions/artifacts/"+str(aid)+"/zip",headers={"Authorization":"Bearer "+token,"User-Agent":"AzeezOS"})
    h=hashlib.sha256();n=0
    with urllib.request.build_opener(Redirect()).open(q,timeout=45) as r,open(path,"wb") as f:
        while True:
            b=r.read(1024*1024)
            if not b:break
            n+=len(b)
            if n>CAP:raise RuntimeError("Artifact exceeds download limit")
            f.write(b);h.update(b)
    return h.hexdigest()
def stage(request,data):
    if not re.fullmatch("[a-f0-9]{32}",request):raise RuntimeError("Invalid request identifier")
    token=os.environ.get("AZEEZOS_GITHUB_TOKEN","")
    if not token or "\n" in token or "\r" in token:raise RuntimeError("Configure GitHub token")
    trust=data/"ai-dev-trust.pem"
    openssl=shutil.which("openssl")
    if not trust.is_file() or not openssl:raise RuntimeError("Trusted signing public key and OpenSSL required")
    runs=api("/actions/workflows/validate-custom.yml/runs?branch=azeezos-2.0&event=workflow_dispatch&per_page=50",token)["workflow_runs"]
    source=next((x for x in runs if x["display_title"]=="AzeezOS AI "+request and x["conclusion"]=="success"),None)
    if not source:raise RuntimeError("No successful matching AI proposal")
    rid=int(source["id"])
    approved=next((x for x in runs if x["display_title"]=="AzeezOS Approve "+str(rid) and x["conclusion"]=="success"),None)
    if not approved:raise RuntimeError("Proposal has not been separately reviewed and signed")
    artifacts=api("/actions/runs/"+str(approved["id"])+"/artifacts",token)["artifacts"]
    a=next((x for x in artifacts if x["name"]=="AzeezOS-Reviewed-"+str(rid) and not x["expired"]),None)
    if not a:raise RuntimeError("Approved artifact missing or expired")
    updates=data/"updates";updates.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ai-stage-",dir=updates) as temp:
        t=Path(temp);z=t/"artifact.zip"
        digest=download(int(a["id"]),token,z)
        if a.get("digest")!="sha256:"+digest:raise RuntimeError("Artifact checksum mismatch")
        with zipfile.ZipFile(z) as archive:
            names=archive.namelist()
            if len(names)!=3 or set(names)!={"manifest.json","manifest.sig","firmware.update.tar"}:raise RuntimeError("Unexpected artifact contents")
            for name in names:
                info=archive.getinfo(name)
                if info.file_size>(CAP if name.endswith(".tar") else 65536):raise RuntimeError("Oversized artifact entry")
                with archive.open(info) as src,open(t/name,"wb") as dst:shutil.copyfileobj(src,dst,1024*1024)
        subprocess.run([openssl,"dgst","-sha256","-verify",str(trust),"-signature",str(t/"manifest.sig"),str(t/"manifest.json")],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        manifest=json.loads((t/"manifest.json").read_text())
        if manifest.get("request_id")!=request or manifest.get("proposal_run")!=rid or manifest.get("board")!="rgds":
            raise RuntimeError("Signed manifest identity mismatch")
        with open(t/"firmware.update.tar","rb") as f:
            digest=hashlib.file_digest(f,"sha256").hexdigest() if hasattr(hashlib,"file_digest") else digest_stream(f)
        if manifest.get("sha256")!=digest:raise RuntimeError("Signed firmware checksum mismatch")
        dst=updates/("banana-rgds-ai-"+str(rid)+".update.tar")
        if dst.exists():raise RuntimeError("Update already staged")
        # renameat2 NOREPLACE or hardlink, never overwrite.
        try:os.link(t/"firmware.update.tar",dst)
        except OSError:
            import ctypes
            libc=ctypes.CDLL(None,use_errno=True)
            if not hasattr(libc,"renameat2") or libc.renameat2(-100,os.fsencode(t/"firmware.update.tar"),-100,os.fsencode(dst),1)!=0:
                raise RuntimeError("Cannot publish safely on this filesystem")
        return dst
def digest_stream(f):
    h=hashlib.sha256()
    for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
if __name__=="__main__":
    try:
        result=stage(sys.argv[1],Path(sys.argv[2]))
        print("Verified update staged. Quit game and open System > Updates.")
    except Exception as e:
        print("Stage failed: "+str(e)[:180]);sys.exit(1)
