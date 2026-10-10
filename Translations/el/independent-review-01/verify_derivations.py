import json,subprocess,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
m=json.loads((ROOT/'Translations/el/correction-cycle-001-closure-manifest.json').read_text()); applied=json.loads((ROOT/'Translations/el/correction-cycle-001-applied.json').read_text()); results=[]
for row in applied['files']:
 p=ROOT/row['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['afterSha256']
 if p.name.startswith('dialogue-ordered-'):
  output=p.with_name(p.name.replace('ordered','batch').replace('.authored',''))
  c=[str(ROOT/'.venv/bin/python'),str(ROOT/'Translations/el/expand_ordered.py'),str(p),str(output),'--verify'];r=subprocess.run(c,cwd=ROOT,capture_output=True,text=True);results.append({'command':c,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0,r.stderr
c=[str(ROOT/'.venv/bin/python'),'Translations/el/expand_static.py','Translations/el/static-lexicon-001.authored.json','Translations/el/static-text-draft.json','--verify'];r=subprocess.run(c,cwd=ROOT,capture_output=True,text=True);results.append({'command':c,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
rp=json.loads((ROOT/'Translations/el/dialogue-repeats-001.authored.json').read_text());b=json.loads((ROOT/'Translations/el/dialogue-batch-001.json').read_text());print('repeat keys',list(rp));print('repeat rows',len(b['entries']))
for group in m['components'].values():assert hashlib.sha256((ROOT/group['path']).read_bytes()).hexdigest()==group['sha256']
for row in m['currentTargetFiles']:assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256']
for row in m['unchangedReproductionInputs']:assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256']
p=HERE/'derivations.json';assert not p.exists();p.write_text(json.dumps({'result':'passed','changedOrderedMaps':26,'staticDraft':'verified','commands':results},indent=2)+'\n');print('passed',len(results))
