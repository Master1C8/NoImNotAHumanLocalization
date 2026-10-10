#!/usr/bin/env python3
import json,hashlib,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).parent
load=lambda p:json.loads((ROOT/p).read_text())
sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
d=load('Translations/bg/semantic-delta-cycle-002.json'); c=load('Translations/bg/semantic-closure-cycle-002.json'); old=load('Translations/bg/semantic-closure-cycle-001.json'); plan=load('Translations/bg/correction-batch-002.json')
nodes=load('Translations/bg/independent-review-01/compiled-nodes.json'); usage={}
for name,n in nodes.items():
 for ins in n['instructions']:
  for op in ins['operands']:
   for field in op:
    if len(field)>2 and isinstance(field[2],str) and field[2].startswith('line:'):
     usage.setdefault(field[2],[]).append((name,ins['index'],ins['opcode']))
rows=d['nextReviewRows']
if sys.argv[1]=='pin':
 pins=dict(c['pinnedInputs']);pins.update({p:sha(p) for p in ['Translations/bg/semantic-delta-cycle-002.json','Translations/bg/semantic-closure-cycle-002.json','Translations/bg/build_semantic_delta_cycle_002.py','Translations/bg/build_semantic_closure_cycle_002.py','Translations/bg/independent-review-01/compiled-nodes.json','Translations/bg/independent-review-01/compiled-context.json','Translations/bg/independent-review-01/managed-context.json']})
 for f in d['currentAuthoredFiles']:
  pins[f['path']]=f['sha256'];pins[f['validationPath']]=f['validationSha256']
 bad=[p for p,v in pins.items() if sha(p)!=v];assert not bad,bad
 targets={}
 for f in d['currentAuthoredFiles']:
  for e in load(f['path'])['entries']:
   sid=e.get('stableId') or 'string:'+{'UI':'0cbd8a7a4f543344bb95659de87f67a5','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'}[f['collection']]+':'+str(e['id'])
   assert sid not in targets;targets[sid]=e['target']
 assert len(targets)==16538
 for r in c['reviewRows']:assert r['target']==targets[r['stableId']]
 for r in plan['decisions']:assert targets[r['stableId']]==r['acceptedFullTarget'] and r['currentFullTarget']!=r['acceptedFullTarget']
 mandatory=set(c['components']['mandatoryRegressions']['ids']); delta=set(d['components']['review']['ids']); previous={r['stableId']:r for r in old['reviewRows']}
 applicable=[]
 for r in c['reviewRows']:
  if r['stableId'] in mandatory-delta:
   p=previous[r['stableId']];assert all(r[k]==p[k] for k in ['source','target','key','sceneNodes']); applicable.append(r['stableId'])
 record={'pins':pins,'authoredCount':411,'validationCount':411,'uniqueTargetCount':len(targets),'changedFullUnitCount':len(plan['decisions']),'mandatoryFreshCount':len(mandatory&delta),'mandatoryExactPriorApplicableCount':len(applicable),'priorApplicableIds':applicable,'usageCount':sum(bool(usage.get(r['key'])) for r in rows if r['collection']=='Dialogs'),'noCompiledUseIds':[r['stableId'] for r in rows if r['collection']=='Dialogs' and not usage.get(r['key'])]}
 (OUT/'input-verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n'); print({k:v for k,v in record.items() if k not in ['pins','priorApplicableIds','noCompiledUseIds']})
elif sys.argv[1]=='read':
 a,b=map(int,sys.argv[2:4])
 for i in range(a,min(b,len(rows))):
  r=rows[i]; u=usage.get(r['key']);loc=','.join(n+':'+str(ins)+('c' if op==4 else '') for n,ins,op in (u or [])) or str(r['key']);print(f"{i} {loc}\nR {r['source']}\nB {r['target']}")
elif sys.argv[1]=='glossary':
 for k,v in load('Documentation/glossary-translations/canonical-reviews/artifacts/bg/layer.json').items(): print(k+'='+v['term'])
elif sys.argv[1]=='decision':
 for r in plan['decisions']:print(r['stableId'].split(':')[-1],r['basis'],r['authorDecision'],'BEFORE',r['currentFullTarget'],'AFTER',r['acceptedFullTarget'])
