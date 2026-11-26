#!/usr/bin/env python3
"""Exercise actual generator in a synthetic integrated repo; no network or secrets."""
import os, json, runpy, subprocess, tempfile, unittest, io, sys
from pathlib import Path
from unittest.mock import patch
GEN=Path(__file__).with_name("generate.py").resolve()
class GeneratorTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name)
        self.old=Path.cwd();os.chdir(self.d)
        self.root=self.d/"upstream";self.root.mkdir()
        self.file=self.root/"ui/src/settings.h";self.file.parent.mkdir(parents=True)
        self.file.write_text("first\nsecond\nthird\n")
        subprocess.run(["git","init","-q",str(self.root)],check=True)
        self.git("add",".");self.git("-c","user.name=Test","-c","user.email=test@example.invalid","commit","-qm","base")
        self.id="a"*32
    def tearDown(self):
        os.chdir(self.old);self.tmp.cleanup()
    def git(self,*args):return subprocess.check_output(["git","-C",str(self.root),*args])
    def diff(self,old,new):
        return f"diff --git a/ui/src/settings.h b/ui/src/settings.h\n--- a/ui/src/settings.h\n+++ b/ui/src/settings.h\n@@ -1,3 +1,3 @@\n{old}{new}"
    def run_gen(self,diff,parent="",prior=None):
        reply={"status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":diff}]}]}
        env={"FEATURE_REQUEST":"test","REQUEST_ID":self.id,"AZEEZOS_OPENAI_API_KEY":"fake","PARENT_REQUEST_ID":parent}
        original_run=subprocess.run;original_check=subprocess.check_output
        def fake_check(args,*a,**kw):
            if args[:2]==["gh","api"]:
                return json.dumps({"workflow_runs":[{"display_title":"AzeezOS AI "+parent,"conclusion":"success","head_branch":"azeezos-2.0","event":"workflow_dispatch","path":".github/workflows/validate-custom.yml","id":123}]}).encode()
            return original_check(args,*a,**kw)
        def fake_run(args,*a,**kw):
            if args[:3]==["gh","run","download"]:
                Path(args[args.index("-D")+1],"feature.patch").write_text(prior)
                return subprocess.CompletedProcess(args,0)
            return original_run(args,*a,**kw)
        with patch.dict(os.environ,env),patch.object(sys,"argv",[str(GEN),str(self.root)]),patch("urllib.request.urlopen",return_value=io.BytesIO(json.dumps(reply).encode())),patch.object(subprocess,"check_output",side_effect=fake_check),patch.object(subprocess,"run",side_effect=fake_run):
            runpy.run_path(str(GEN),run_name="__main__")
        return (self.d/"ai-dev-output/feature.patch").read_text()
    def test_cumulative(self):
        a=self.diff("-first\n","+FIRST\n second\n third\n")
        prior=self.run_gen(a)
        self.assertEqual(self.file.read_text(),"first\nsecond\nthird\n")
        self.id="b"*32
        b=self.diff(" FIRST\n-second\n","+SECOND\n third\n")
        result=self.run_gen(b,"a"*32,prior)
        self.git("apply",str(self.d/"ai-dev-output/feature.patch"))
        self.assertEqual(self.file.read_text(),"FIRST\nSECOND\nthird\n")
        self.assertIn("+FIRST",result);self.assertIn("+SECOND",result)
    def test_reject_outside_scope(self):
        a=self.diff("-first\n","+FIRST\n second\n third\n").replace("ui/src/settings.h","outside")
        with self.assertRaises(SystemExit):self.run_gen(a)
if __name__=="__main__":unittest.main()
