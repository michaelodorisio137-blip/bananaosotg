#!/usr/bin/env python3
"""Generate a reviewable unified diff against the integrated, pinned UI only."""
import json,os,re,subprocess,sys,urllib.request
from pathlib import Path
root=Path(sys.argv[1]).resolve()
request=os.environ.get("FEATURE_REQUEST","").strip()
key=os.environ.get("AZEEZOS_OPENAI_API_KEY","")
if not re.fullmatch(r"[a-f0-9]{32}",os.environ.get("REQUEST_ID","")):
    raise SystemExit("Invalid device request ID.")
if not key or not request or len(request)>800:
    raise SystemExit("Configure AZEEZOS_OPENAI_API_KEY in Actions and provide a request (1-800 chars).")
allowed=["settings_gamepanel.cpp","settings.h","azeezos_ai_cheats.h","cheat_panel.h","live_scan.h","azeez_mod_browser.h"]
# Select small relevant excerpts, not secrets or untrusted build logs.
parts=[]
for name in allowed:
    p=root/"ui/src"/name
    if not p.is_file():continue
    s=p.read_text()
    if len(s)>65000:
        lines=s.splitlines()
        matched=set()
        for i,line in enumerate(lines):
            if any(x in line for x in ("gAiPanel","gModOpen","gScanOpen","gCheatPanel","gameRender(","gameTouch(","gameUpdate(")):
                matched.update(range(max(0,i-8),min(len(lines),i+12)))
        s="\n".join(f"{i+1}: {lines[i]}" for i in sorted(matched))
    parts.append(f"FILE ui/src/{name}\n{s}")
prompt=("You are implementing a feature on AzeezOS. Return only a valid unified git diff with a/ and b/ paths, "
        "no fences. Modify only the listed UI files, preserve existing features, use exact context, never add shell "
        "execution, credential access or automatic firmware installation. If impossible return NO_PATCH. "
        "Request: "+request+"\n\n"+"\n\n".join(parts))
body=json.dumps({"model":os.environ.get("AZEEZOS_AI_MODEL","gpt-5-mini"),"store":False,"input":prompt,"max_output_tokens":5000}).encode()
req=urllib.request.Request("https://api.openai.com/v1/responses",data=body,headers={"Content-Type":"application/json","Authorization":"Bearer "+key})
with urllib.request.urlopen(req,timeout=150) as r:
    obj=json.load(r)
if obj.get("status")!="completed":raise SystemExit("AI did not finish")
diff="\n".join(p["text"] for m in obj.get("output",[]) if m.get("type")=="message"
               for p in m.get("content",[]) if p.get("type")=="output_text").strip()
if not diff.startswith("diff --git ") or len(diff)>100000:raise SystemExit("No valid patch returned")
paths=re.findall(r"^diff --git a/(\S+) b/(\S+)$",diff,re.M)
if not paths or any(a!=b or a not in ["ui/src/"+n for n in allowed] for a,b in paths):
    raise SystemExit("Patch attempts to modify files outside approved UI scope")
if any(line.startswith(("new file mode","deleted file mode","rename from","rename to","GIT binary patch","old mode","new mode")) for line in diff.splitlines()):
    raise SystemExit("File creation/deletion/rename/binary/mode changes are not allowed")
out=Path("ai-dev-output");out.mkdir(exist_ok=True)
(out/"feature.patch").write_text(diff+"\n")
patch_path=str((out/"feature.patch").resolve())
# Validate the actual paths Git will apply, not just AI-supplied diff headers.
stats=subprocess.check_output(["git","-C",str(root),"apply","--numstat","-z",patch_path])
actual=[]
for entry in stats.rstrip(b"\0").split(b"\0"):
    fields=entry.split(b"\t",2)
    if len(fields)!=3 or not fields[0].isdigit() or not fields[1].isdigit():
        raise SystemExit("Invalid or binary patch entry")
    actual.append(fields[2].decode("utf-8"))
if not actual or any(p not in ["ui/src/"+n for n in allowed] for p in actual):
    raise SystemExit("Git patch changes an unapproved path")
subprocess.run(["git","-C",str(root),"apply","--check",patch_path],check=True)
(out/"request.txt").write_text(request+"\n")
print("Generated a patch that applies to the pinned integrated UI; review and build required.")
