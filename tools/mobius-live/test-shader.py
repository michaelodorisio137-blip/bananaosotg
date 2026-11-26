from pathlib import Path
import re,json,subprocess,tempfile
s=Path(__file__).with_name('mobius.h').read_text()
with tempfile.TemporaryDirectory() as tmp:
 for name,stage in [('mobVS','vert'),('mobFS','frag')]:
  segment=s.split('static const char* '+name+'=',1)[1].split(';\n',1)[0]
  # GLSL includes semicolons in C literals, but not literal newline immediately following them.
  code=''.join(json.loads(x) for x in re.findall(r'"(?:[^"\\]|\\.)*"',segment))
  p=Path(tmp)/('shader.'+stage);p.write_text(code)
  subprocess.run(['glslangValidator','-S',stage,str(p)],check=True)
print('GLES3 shader syntax verified.')
