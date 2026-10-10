import json,hashlib,pathlib,re,runpy
R=pathlib.Path(__file__).resolve().parents[3];C=R/'Translations/fa/audit-cycle-001';O=pathlib.Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
mod=runpy.run_path(str(C/'build-audit-closure.py'));mod['main']()
f=read(C/'first-pass.snapshot.json');d=read(C/'file-delta-manifest.json');plan=read(C/'correction-plan.json');cl=read(C/'closure.json');before={x['path']:C/'before'/pathlib.Path(x['path']).name for x in d['files']}
ids=[];segment_evidence=[];guid=mod['GUID'];full={}
for s in f['reviewedSegments']:
 p=before.get(s['path'],R/s['path']);assert sha(p)==s['sha256'],s['path'];b=read(p)
 entries=b['entries'];sid=[x.get('stableId') or f"string:{guid[b['collection']]}:{x['id']}" for x in entries]
 if 'entryStart' in s: entries=entries[s['entryStart']:s['entryEndExclusive']];sid=sid[s['entryStart']:s['entryEndExclusive']]
 # segmented common-option receipt keys are verified by explicit indices below
 if len(sid)!=s['units']:
  print('SEGMENT',s);raise Exception('segment schema')
 h=hashlib.sha256((''.join(x+'\n' for x in sid)).encode()).hexdigest();assert h==s['reviewedIdsSha256'],s
 ids+=sid;segment_evidence.append({'path':s['path'],'units':len(sid),'inputSha256':sha(p),'idSha256':h})
assert len(ids)==len(set(ids))==16538
assert hashlib.sha256((''.join(x+'\n' for x in ids)).encode()).hexdigest()==f['reviewedIdsSha256']
manifest=read(R/'Source/preserve-exactly-v4.json');assert set(ids)=={x['stableId'] for x in manifest['tableRows']+manifest['staticRows']}
actual_deltas=[]
for x in d['files']:
 a=read(C/'before'/pathlib.Path(x['path']).name);b=read(C/'after'/pathlib.Path(x['path']).name)
 assert len(a['entries'])==len(b['entries']);assert {k:v for k,v in a.items() if k!='entries'}=={k:v for k,v in b.items() if k!='entries'}
 for aa,bb in zip(a['entries'],b['entries']):
  assert {k:v for k,v in aa.items() if k!='target'}=={k:v for k,v in bb.items() if k!='target'}
  if aa['target']!=bb['target']:
   sid=aa.get('stableId') or f"string:{guid[a['collection']]}:{aa['id']}";pp=next(r for r in plan['rows'] if r['stableId']==sid);assert pp['before']==aa['target'] and pp['acceptedTarget']==bb['target'];actual_deltas.append(sid)
assert set(actual_deltas)=={r['stableId'] for r in plan['rows']} and len(actual_deltas)==76
report={'schemaVersion':1,'firstPassReceiptSegments':segment_evidence,'firstPassUniqueIds':16538,'exactFullUnitTargetDeltas':76,'deltas':actual_deltas,'closureComponents':cl['componentHashes'],'pins':{str(p.relative_to(R)):sha(p) for p in [C/'closure.json',C/'selector-spec.json',C/'first-pass.snapshot.json',C/'file-delta-manifest.json',C/'correction-plan.json',R/'Documentation/glossary-translations/fa/layer.json',R/'Source/glossary-corpus-v1/sharedassets0.assets-2743.json']},'currentAuthoredHashes':{str(p.relative_to(R)):sha(p) for p in sorted((R/'Translations/fa').glob('*batch-*.json')) if re.fullmatch(r'(ui|dialogue|checks)-batch-\d{3}\.json',p.name)}|{'Translations/fa/static-text-draft.json':sha(R/'Translations/fa/static-text-draft.json')}}
(O/'input-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('VERIFIED',len(ids),len(actual_deltas))
