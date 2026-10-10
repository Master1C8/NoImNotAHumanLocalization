"""Re-execute validators; intercept only their validation-sidecar write boundary."""
import contextlib,hashlib,io,json,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path.cwd(); E=ROOT/'Translations/sw/independent-review-01'
sys.path.insert(0,str(ROOT/'scripts'))
import validate_game_text_batch as game
import validate_static_text_draft as static
manifest=json.loads((ROOT/'Translations/sw/semantic-correction-cycle-01/final-payload-manifest.json').read_text())
reports=[]
for artifact in manifest['artifacts']:
 path=ROOT/artifact['path']; assert hashlib.sha256(path.read_bytes()).hexdigest()==artifact['sha256']
 captured=[]
 def capture(destination,data,*args,**kwargs):
  assert destination==path.with_suffix('.validation.json'), str(destination)
  captured.append(json.loads(data));return len(data)
 sys.argv=['validator',str(path)]
 with patch.object(Path,'write_text',capture),contextlib.redirect_stdout(io.StringIO()):
  (static if path.name=='static-text-draft.json' else game).main()
 assert len(captured)==1
 reports.append(captured[0])
assert len(reports)==187
assert sum(r.get('authoredRows',r.get('rows')) for r in reports)==16538
result={'schemaVersion':1,'reviewer':'/root/sw_independent_review','mechanism':'Canonical validators executed against original authored inputs; only successful JSON report sidecar write intercepted in memory. No authored sidecar writes; validation checks were not mocked.','validators':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [ROOT/'scripts/validate_game_text_batch.py',ROOT/'scripts/validate_static_text_draft.py',ROOT/'scripts/probe_assets.py']],'payloadManifestSha256':hashlib.sha256((ROOT/'Translations/sw/semantic-correction-cycle-01/final-payload-manifest.json').read_bytes()).hexdigest(),'validatedArtifacts':len(reports),'validatedUnits':16538,'structuralResult':'passed','semanticAcceptance':'not established by validators','runtime':'not-run-per-owner','reports':reports}
with (E/'structural-recheck-01.json').open('x') as out:json.dump(result,out,ensure_ascii=False,indent=2);out.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='reports'}))
