#!/usr/bin/env python3
import hashlib,importlib.util,json,os,subprocess,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location("stage",Path(__file__).with_name("stage.py"))
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
class StageTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name)
        self.id="a"*32;self.rid=123;self.archive=self.d/"bundle.zip"
        self.private=self.d/"private.pem"
        subprocess.run(["openssl","genpkey","-algorithm","RSA","-pkeyopt","rsa_keygen_bits:2048","-out",str(self.private)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.run(["openssl","pkey","-in",str(self.private),"-pubout","-out",str(self.d/"ai-dev-trust.pem")],check=True)
    def tearDown(self):self.tmp.cleanup()
    def make(self,wrong_hash=False,wrong_id=False,extra=False):
        fw=b"synthetic firmware for unit test"
        m={"board":"rgds","request_id":"b"*32 if wrong_id else self.id,"proposal_run":self.rid,
           "sha256":"0"*64 if wrong_hash else hashlib.sha256(fw).hexdigest()}
        manifest=self.d/"manifest.json";manifest.write_text(json.dumps(m))
        sig=self.d/"manifest.sig"
        subprocess.run(["openssl","dgst","-sha256","-sign",str(self.private),"-out",str(sig),str(manifest)],check=True)
        with zipfile.ZipFile(self.archive,"w") as z:
            z.write(manifest,"manifest.json");z.write(sig,"manifest.sig");z.writestr("firmware.update.tar",fw)
            if extra:z.writestr("../escape","bad")
        return fw
    def runStage(self,approved=True):
        runs=[{"display_title":"AzeezOS AI "+self.id,"conclusion":"success","id":self.rid}]
        if approved:runs.append({"display_title":"AzeezOS Approve "+str(self.rid),"conclusion":"success","id":124})
        digest=hashlib.sha256(self.archive.read_bytes()).hexdigest()
        def api(path,token):
            if "workflows" in path:return {"workflow_runs":runs}
            return {"artifacts":[{"name":"AzeezOS-Reviewed-123","expired":False,"id":3,"digest":"sha256:"+digest}]}
        def download(aid,token,path):path.write_bytes(self.archive.read_bytes());return digest
        with patch.dict(os.environ,{"AZEEZOS_GITHUB_TOKEN":"fake"}),patch.object(stage,"api",api),patch.object(stage,"download",download):
            return stage.stage(self.id,self.d)
    def test_verified(self):
        fw=self.make();dst=self.runStage();self.assertEqual(dst.read_bytes(),fw)
        with self.assertRaises(RuntimeError):self.runStage()
        self.assertEqual(dst.read_bytes(),fw)
    def test_no_approval(self):
        self.make()
        with self.assertRaises(RuntimeError):self.runStage(False)
    def test_tampered(self):
        self.make(wrong_hash=True)
        with self.assertRaises(RuntimeError):self.runStage()
    def test_wrong_id(self):
        self.make(wrong_id=True)
        with self.assertRaises(RuntimeError):self.runStage()
    def test_extra_file(self):
        self.make(extra=True)
        with self.assertRaises(RuntimeError):self.runStage()
if __name__=="__main__":unittest.main()
