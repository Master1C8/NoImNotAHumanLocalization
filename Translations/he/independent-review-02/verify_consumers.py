#!/usr/bin/env python3
"""Reproduce closure without writing worker artifacts; check actual consumer assembly."""
import json,pathlib,hashlib,runpy,sys
ROOT=pathlib.Path(__file__).resolve().parents[3];OUT=pathlib.Path(__file__).resolve().parent;C=ROOT/'Translations/he/semantic-correction-cycle-02';IR=ROOT/'Translations/he/independent-review-01'
sys.path.insert(0,str(ROOT/'Scripts'));from preserve_exact import validate
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def save(n,d):
 p=OUT/n;b=(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode();assert not p.exists() or p.read_bytes()==b
 if not p.exists():p.write_bytes(b)
recipe=runpy.run_path(str(C/'build_closure.py'));outputs=[]
def compare_only(p,data):
 assert p.is_file() and p.read_bytes()==data,p;outputs.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=len(data)))
recipe['main'].__globals__['once']=compare_only;recipe['main']()
validate('he',OUT/'preserve-exact-v4.json')
checks=[]
for f in ['character-consumer-domain.json','item-binding-verified.json','dynamic-consumer-il-02.json','place-and-item-binding-il.json']:
 d=read(IR/f);p=pathlib.Path(d.get('sourcePath',d.get('assemblyPath','')));h=d.get('sourceSha256',d.get('assemblySha256'));assert p.is_file() and sha(p)==h;checks.append(dict(evidence=str((IR/f).relative_to(ROOT)),path=str(p),sha256=h))
scenes=read(OUT/'compiled-scene-context.json')['nodes'];fmt=read(IR/'all-format-consumer-context.json');delta=[json.loads(x) for x in (C/'delta-review-rows.jsonl').open()];delta_ids={r['stableId'] for r in delta};windows=[]
for row in fmt['rows']:
 if row['stableId'] not in delta_ids:continue
 for use in row['consumer']:
  n=use['node'];idx=use['instructionIndex'];assert n in scenes
  actual=scenes[n];expected=use['instructions'];matches=[]
  for start in range(len(actual)-len(expected)+1):
   if actual[start:start+len(expected)]==expected and start<=idx<start+len(expected):matches.append(start)
  assert matches,(row['stableId'],n,idx)
  assert actual[idx]['opcode']==2 and actual[idx]['operands'][0]==row.get('key', next(r['key'] for r in delta if r['stableId']==row['stableId']))
  windows.append(dict(stableId=row['stableId'],node=n,instructionIndex=idx,windowStart=matches))
labels={r['key']:r['after'] for r in delta if r['collection']=='UI'};consumer=read(C/'consumer-preflight.json');variants=[]
for row in consumer['assembled']:
 target=next(r['after'] for r in delta if r['stableId']==row['stableId'])
 for v in row['variants']:
  k='characterName_'+v['occupant'] if 'occupant' in v else 'consumable_'+v['item'].lower()+'_name';assert labels[k]==v['value'];assert target.replace('{0}',v['value'])==v['assembled'];variants.append(dict(stableId=row['stableId'],labelKey=k,**v))
assert not any(r.get('key')=='characterName_Twins' for r in map(json.loads,(ROOT/'Source/localization-inventory-v3/strings.jsonl').open()))
save('consumer-verification.json',dict(schemaVersion=1,status='passed static reproduction; no runtime claim',closureReproducedOutputs=outputs,externalAssetPins=checks,compiledConsumerWindowsChecked=windows,assembledCorrectedRows=len(consumer['assembled']),assembledVariants=len(variants),variants=variants,unresolved=consumer['unresolvedCharacterLabels'],limitation='characterName_Twins has no exact accepted UI key. No input fabricated; actual displayed fallback remains unverified. No game launch, renderer, font or layout check.'))
print(json.dumps(dict(reproducedOutputs=len(outputs),consumerWindows=len(windows),variants=len(variants))))
