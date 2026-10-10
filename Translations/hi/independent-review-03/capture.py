import json, hashlib, importlib.util, sys
from pathlib import Path
R=Path(__file__).resolve().parents[3]; H=R/'Translations/hi'; D=Path(__file__).parent
j=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ih=lambda ids:hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest()
def write(name,obj):
 p=D/name
 assert not p.exists(),p
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
c=j(H/'semantic-cycle-003-closure.json');delta=j(H/'semantic-cycle-003-review-delta.json')
old=j(H/'independent-review-02/final-unchanged-input-pins.json')['pins']
plan=j(H/'semantic-cycle-003-application-plan.json')
changed_paths={p[k] for p in plan['files'] for k in ['path','beforeValidationPath']}
changed_paths.add('Documentation/hi-text-checkpoint.json')
checks=[]
for p,h in old.items():
 if p not in changed_paths: checks.append({'path':p,'expected':h,'actual':sha(R/p),'matches':sha(R/p)==h})
assert all(p['matches'] for p in checks)
paths=set(old)|{str(p.relative_to(R)) for p in H.glob('semantic-cycle-003*') if p.is_file()}|{'Translations/hi/build-semantic-cycle-003-closure.py','Translations/hi/independent-review-02/final-report.md','Translations/hi/independent-review-02/per-id-final-decisions.jsonl','Translations/hi/independent-review-02/final-coverage-and-closure-proof.json'}
write('start-pins.json',{p:sha(R/p) for p in sorted(paths)})
write('unchanged-prior-pin-proof.json',{'unchangedCount':len(checks),'intentionallyChangedPaths':sorted(changed_paths),'checks':checks})
src={r['stableId']:r for p in ['Source/localization-inventory-v3/strings.jsonl','Source/localization-inventory-v3/static-text.jsonl'] for r in map(json.loads,(R/p).read_text().splitlines())}
m={r['stableId']:r for r in c['reviewRows']}
pairs=[{**m[s],'deltaOrdinal0':i,'key':src[s].get('key'),'nodeNames':src[s].get('nodeNames',[])} for i,s in enumerate(delta['deltaIds'])]
(D/'delta-pairs.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in pairs))
sp=importlib.util.spec_from_file_location('cycle2',H/'build-semantic-cycle-002-closure.py'); mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
nodes=mod.runtime_nodes(mod.helper().fields)
names=set(n for r in pairs for n in r['nodeNames'])
tech=j(R/c['technicalContextPath'])
names.update(r['node'] for r in tech['technicalFragments'])
write('actual-compiled-nodes.json',{n:nodes.get(n) for n in sorted(names)})
write('delta-consumer-map.json',[{'stableId':r['stableId'],'key':r['key'],'nodeNames':r['nodeNames'],'references':[{'node':n,'instruction':i} for n in r['nodeNames'] for i in nodes.get(n,[]) if r['key'] in i['strings']]} for r in pairs])
print('Captured',len(pairs),'delta pairs,',len(names),'compiled context nodes,',len(checks),'unchanged prior pins')
