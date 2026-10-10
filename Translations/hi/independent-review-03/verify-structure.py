"""Run canonical validators read-only, compare their proposed sidecars byte-for-byte."""
import contextlib, functools, hashlib, importlib.util, io, json, sys
from pathlib import Path
R=Path(__file__).resolve().parents[3]; D=Path(__file__).parent
sys.path.insert(0,str(R/'Scripts'))
original_loads=json.loads
json.loads=functools.lru_cache(maxsize=None)(original_loads)
original_write=Path.write_text
receipts=[]
def blocked_write(p,text,*a,**kw):
 assert p.is_relative_to(R/'Translations/hi') and p.name.endswith('.validation.json'),p
 assert p.read_text()==text,('sidecar reproduction differs',p)
 receipts.append({'path':str(p.relative_to(R)),'proposedSidecarSha256':hashlib.sha256(text.encode()).hexdigest(),'byteExactExistingSidecar':True,'written':False})
 return len(text)
Path.write_text=blocked_write
try:
 gate=json.loads((R/'Translations/hi/semantic-cycle-003-structural-gate.json').read_text())
 for script,key in [('validate_game_text_batch.py','batch'),('validate_static_text_draft.py','draft')]:
  spec=importlib.util.spec_from_file_location(script[:-3],R/'Scripts'/script);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  files=[r for r in gate['files'] if (r['path'].endswith('static-text-draft.json'))==(key=='draft')]
  for f in files:
   sys.argv=[script,str(R/f['path'])]
   with contextlib.redirect_stdout(io.StringIO()):mod.main()
finally:
 Path.write_text=original_write;json.loads=original_loads
out=D/'full-structural-readonly-revalidation.json';assert not out.exists()
out.write_text(json.dumps({'status':'passed','ordinaryBatchCount':len(receipts)-1,'staticDraftCount':1,'boundary':'canonical validator predicates, exact real inputs; cached JSON decoding only; sidecar write suppressed and compared byte-for-byte','receipts':receipts},ensure_ascii=False,indent=2)+'\n')
print('Passed',len(receipts),'canonical validator checks; no sidecar writes')
