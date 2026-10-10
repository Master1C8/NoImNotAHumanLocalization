"""Independent exact input, prior-reading, consumer and retirement reconciliation."""
import sys
sys.dont_write_bytecode=True
import json,hashlib,importlib.util,re
from pathlib import Path
from collections import defaultdict,Counter
R=Path(__file__).resolve().parents[3];B=R/'Translations/bg';O=Path(__file__).parent
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();th=lambda s:hashlib.sha256(s.encode()).hexdigest()
same=lambda a,b:all(a.get(k)==b.get(k) for k in ['source','target','key','sceneNodes','collection'])
idbytes=lambda ids:('\n'.join(ids)+ ('\n' if ids else '')).encode()
assert sha(B/'correction-cycle-004-evidence-sha256.json')=='793dd579458b4b3cb0c7e24c31a9e9e195ba9495f856b82432ce8950eaa02de5'
assert sha(B/'independent-review-03/evidence-sha256.json')=='7528f1c522bf30a4a2f6999568e3dcfed48a684cea7122f720b29a791c733f61'
c=load(B/'semantic-closure-cycle-004.json');d=load(B/'semantic-delta-cycle-004.json');res=load(B/'correction-batch-004-result.json');pairs=load(B/'correction-cycle-004-sourcepairs.json')
pins=dict(c['pinnedInputs'])
for name,h in load(B/'correction-cycle-004-evidence-sha256.json')['files'].items():assert sha(B/name)==h; pins[str((B/name).relative_to(R))]=h
for n in [1,2,3]:
 base=B/f'independent-review-{n:02}';m=load(base/'evidence-sha256.json')
 for name,h in m.get('files',m).items():assert sha(base/name)==h
 pins[str((base/'evidence-sha256.json').relative_to(R))]=sha(base/'evidence-sha256.json')
for rec in res['allAuthoredFiles']:
 for p,h in [(rec['path'],rec['sha256']),(rec['validationPath'],rec['validationSha256'])]:assert sha(R/p)==h; pins[p]=h
for p,h in pins.items():assert sha(R/p)==h,p
historical=load(B/'independent-review-03/input-verification.json')['pins'];drift={p for p,h in historical.items() if sha(R/p)!=h}
allowed={p for r in res['changedFiles'] for p in [r['path'],r['validationPath']]};assert drift==allowed and len(drift)==6
snap=load(B/'correction-cycle-004-baseline/manifest.json')
for item in snap['physicalSnapshots']:assert sha(R/item['snapshotPath'])==item['sha256']==historical[item['path']]
GUID={'UI':'0cbd8a7a4f543344bb95659de87f67a5','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'};targets={}
for rec in res['allAuthoredFiles']:
 for row in load(R/rec['path'])['entries']:
  sid=row.get('stableId') or 'string:'+GUID[rec['collection']]+':'+str(row['id']);assert sid not in targets;targets[sid]=row['target']
source={}
for name in ['strings.jsonl','static-text.jsonl']:
 for l in (R/'Source/localization-inventory-v3'/name).open():
  r=json.loads(l)
  if r['stableId'] in targets:assert r['stableId'] not in source;source[r['stableId']]=r
assert len(targets)==len(source)==16538
current={r['stableId']:r for r in c['reviewRows']}
for sid,r in current.items():assert r['source']==source[sid]['source'] and r['target']==targets[sid] and r['key']==source[sid].get('key')
assert load(Path('/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary-translations.json'))['bg']==load(R/'Documentation/glossary-translations/canonical-reviews/artifacts/bg/layer.json')
old=load(B/'semantic-closure-cycle-003.json');oldrows={r['stableId']:r for r in old['reviewRows']};catalog=defaultdict(list)
for n in [1,2,3]:
 rows={r['stableId']:r for r in load(B/f'semantic-closure-cycle-{n:03}.json')['reviewRows']};base=B/f'independent-review-{n:02}';ids=(base/'read.ids').read_text().splitlines();assert len(ids)==len(set(ids))=={1:1506,2:2110,3:311}[n]
 if n in [2,3]:
  vv=load(base/'per-id-read-verdicts.json');assert {v['stableId'] for v in vv}==set(ids)
  for v in vv:assert v['fullPairRead'] and v['sourceSha256']==th(rows[v['stableId']]['source']) and v['targetSha256']==th(rows[v['stableId']]['target'])
 for sid in ids:catalog[sid].append({'origin':f'Review{n:02} full read','row':rows[sid]})
for r in load(B/'independent-review-02/selector-supplementary-rows.json'):
 if not r['inDelta']:
  sid=r['stableId'];ref=oldrows[sid];assert r['source']==ref['source'] and r['key']==ref['key'];catalog[sid].append({'origin':'Review02 supplementary exact pair + Review03 verified unchanged compiled consumer','row':dict(ref,target=r['target'])})
for r in load(B/'independent-review-03/supplementary-pair-verdicts.json'):
 assert r['fullPairRead'] and same(r,oldrows[r['stableId']]);catalog[r['stableId']].append({'origin':'Review03 supplementary full read','row':r})
assert all(any(same(r,e['row']) for e in catalog[sid]) for sid,r in oldrows.items())
applicable={sid for sid,r in current.items() if any(same(r,e['row']) for e in catalog[sid])};assert len(applicable)==2836
for p in d['priorReadingApplicability']['catalog']:
 r=current[p['stableId']];matches=[e for e in catalog[p['stableId']] if same(r,e['row'])]
 assert p['sourceSha256']==th(r['source']) and p['targetSha256']==th(r['target']) and p['key']==r['key'] and p['sceneNodes']==r['sceneNodes'] and p['collection']==r['collection']
 assert p['creditedOrigin']==matches[-1]['origin'] and p['allExactApplicableOrigins']==[e['origin'] for e in matches]
corrected=set(res['changedIds']);assert len(corrected)==3
for p in pairs['pairs']:
 sid=p['stableId'];assert p['source']==source[sid]['source'] and p['currentFullTarget']==oldrows[sid]['target'] and p['acceptedFullTarget']==targets[sid]
 assert th(p['source'])==p['sourceSha256'] and th(p['currentFullTarget'])==p['beforeTargetSha256'] and th(p['acceptedFullTarget'])==p['afterTargetSha256']
 snapshot=next(s for s in snap['physicalSnapshots'] if s['path']==p['batchPath']);before=load(R/snapshot['snapshotPath']);after=load(R/p['batchPath']);before_entries={e['id']:e for e in before['entries']};after_entries={e['id']:e for e in after['entries']}
 assert set(before_entries)==set(after_entries);changed=[i for i in before_entries if before_entries[i]!=after_entries[i]];assert changed==[int(sid.split(':')[-1])]
 assert before_entries[changed[0]]['target']==p['currentFullTarget'] and after_entries[changed[0]]['target']==p['acceptedFullTarget']
newnodes={n for sid in corrected for n in current[sid]['sceneNodes']};newsource={current[s]['source'] for s in corrected};reason={}
for sid in applicable:
 r=current[sid];why=[]
 if set(r['sceneNodes'])&newnodes:why.append('same compiled Yarn node as cycle004 complete replacement; chronology or assurance now repaired')
 if r['source'] in newsource:why.append('exact Russian repetition of cycle004 corrected unit')
 for group in ['occasionVersusManner','answerResponsibilityVersusAssurance']:
  ids=set(c['glossaryReferentGroups'][group]['ids'])
  if sid in ids and ids&corrected:why.append('bounded affected source idiom family: '+group+'; reinterpret against the repaired distinction, not register preference')
 if why:reason[sid]=why
assert reason=={r['stableId']:r['reasons'] for r in d['invalidatedPriorReasons']} and len(reason)==45
new=set(current)-applicable;review=corrected|new|set(reason);assert len(new)==75 and len(review)==120
assert review=={r['stableId'] for r in d['nextReviewRows']}==set((B/'semantic-cycle-004-review.ids').read_text().splitlines())
assert all(r==current[r['stableId']] for r in d['nextReviewRows']);assert not set(oldrows)-set(current)
for comp in list(c['components'].values())+list(d['components'].values()):
 assert comp['count']==len(comp['ids'])==len(set(comp['ids'])) and (R/comp['path']).read_bytes()==idbytes(comp['ids']) and sha(R/comp['path'])==comp['sha256']
mandatory=set(c['components']['mandatoryRegressions']['ids']);fresh=mandatory&review;prior=mandatory-review;assert len(mandatory)==908 and len(fresh)==1 and len(prior)==907 and prior<=applicable
assert mandatory==set(old['components']['mandatoryRegressions']['ids'])
module=importlib.util.spec_from_file_location('readwire',B/'independent-review-01/inspect_context.py');wire=importlib.util.module_from_spec(module);module.loader.exec_module(wire)
binding=load(R/'Source/glossary-corpus-v2/runtime-bindings.json');program=bytes(binding['sharedassets0.assets:2743']['compiledYarnProgram']);nodes={}
for f,w,v in wire.fields(program):
 if f!=2:continue
 entry=wire.fields(v);name=next(x[2].decode() for x in entry if x[0]==1);nf=wire.fields(next(x[2] for x in entry if x[0]==2));ins=[];labels={}
 for nn,ww,vv in nf:
  if nn==2:
   opcode=0;ops=[]
   for k,wt,val in wire.fields(vv):
    if k==1:opcode=val
    elif k==2:ops.append([(a,w,wire.strings(av) if w==2 else av) for a,w,av in wire.fields(val)])
   ins.append({'index':len(ins),'opcode':opcode,'operands':ops})
  elif nn==3:
   ll=wire.fields(vv);labels[next(x[2].decode() for x in ll if x[0]==1)]=next((x[2] for x in ll if x[0]==2),0)
 nodes[name]={'instructions':ins,'labels':labels}
assert json.loads(json.dumps(nodes))==load(B/'independent-review-01/compiled-nodes.json') and len(nodes)==3255
uses=defaultdict(list)
for name,node in nodes.items():
 for ins in node['instructions']:
  for op in ins['operands']:
   for f in op:
    if isinstance(f[2],str) and f[2].startswith('line:'):uses[f[2]].append({'node':name,'instruction':ins['index'],'opcode':ins['opcode']})
missing=[r['stableId'] for r in d['nextReviewRows'] if not uses[r['key']]];assert [i.split(':')[-1] for i in missing]==['110504451960283141','110504451817676809']
for p in pairs['pairs']:assert uses[current[p['stableId']]['key']]==p['compiledUses']
managed=load(B/'independent-review-01/managed-context.json');base=Path('/Volumes/KINGSTONMAC/Applications/No Im not a Human.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human/NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed')
for f,x in managed.items():assert sha(base/f)==x['sha256'];pins[str(base/f)]=x['sha256']
raw=load(O/'occupant-domain-raw-v2.json');state=load(R/'Documentation/localization-state.json')
for p,h in raw['assetPins'].items():assert sha(Path(p))==h==state['sourceInputs'][p.split('/No Im not a Human/')[-1]];pins[p]=h
out={'schemaVersion':1,'locale':'bg','gameVersion':'1.3.19','reviewer':'/root/bg_independent_review_04','model':'inherited GPT-6; exact serving model and reasoning telemetry unavailable','pins':pins,'sealVerified':sha(B/'correction-cycle-004-evidence-sha256.json'),'priorSealVerified':sha(B/'independent-review-03/evidence-sha256.json'),'currentAuthoredFiles':411,'uniqueFullUnits':16538,'correctedFullUnits':3,'unchangedFullUnits':16535,'unchangedAuthoredFiles':408,'Review03Pins':len(historical),'Review03IntentionalDrift':sorted(drift),'Review03UnchangedPins':len(historical)-len(drift),'physicalBaselineSnapshots':6,'previousClosure':2839,'currentClosure':2911,'newSelection':72,'exactPriorApplicable':2836,'withoutApplicableRead':75,'explicitInvalidationReasons':d['invalidatedPriorReasons'],'nextReviewIds':d['components']['review']['ids'],'retiredDependencies':[],'retirementVerdict':'none; every previous closure ID remains in current normal generation','mandatoryIds':908,'mandatoryFreshIds':d['mandatoryRegressions']['freshIds'],'mandatoryExactPriorIds':d['mandatoryRegressions']['priorExactApplicableIds'],'rawCompiledNodes':3255,'compiledProgramSha256':th(program.decode('latin1')) if False else hashlib.sha256(program).hexdigest(),'compiledUses':{r['stableId']:uses[r['key']] for r in d['nextReviewRows']},'deltaRowsWithoutCompiledUse':missing,'sourceGlossaryInventoryBindingChange':False,'physicalRuntime':'not run','telemetry':'unknown; counters not exposed'}
p=O/'input-verification.json';assert not p.exists();p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'pins':len(pins),'closure':2911,'delta':120,'invalidations':45,'mandatoryFresh':1,'mandatoryPrior':907,'compiledMapped':118,'retired':0}))
