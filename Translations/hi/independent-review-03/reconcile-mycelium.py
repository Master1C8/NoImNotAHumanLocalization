import json,re,hashlib,importlib.util
from pathlib import Path
R=Path(__file__).resolve().parents[3];D=Path(__file__).parent;H=R/'Translations/hi'
j=lambda p:json.loads(p.read_text())
c=j(H/'semantic-cycle-003-closure.json');closed={r['stableId'] for r in c['reviewRows']}
source=[json.loads(x) for x in (R/'Source/localization-inventory-v3/strings.jsonl').read_text().splitlines()]
srcmap={(r['collection'],r['stableId'].rsplit(':',1)[1]):r for r in source}
targets={};paths={}
for f in j(H/'semantic-cycle-003-structural-gate.json')['files']:
 obj=j(R/f['path'])
 if 'collection' not in obj:continue
 for e in obj['entries']:
  sid=srcmap[obj['collection'],str(e['id'])]['stableId'];targets[sid]=e['target'];paths[sid]=f['path']
family=[r for r in source if r['stableId'] in targets and re.search(r'(?i)\bмицели\w*\b',r['source'])]
missing=[r for r in family if r['stableId'] not in closed]
assert len(missing)==6
sp=importlib.util.spec_from_file_location('cycle2',H/'build-semantic-cycle-002-closure.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);nodes=m.runtime_nodes(m.helper().fields)
names={n for r in missing for n in r.get('nodeNames',[])}
out={'familyCount':len(family),'familyForms':sorted(set(w for r in family for w in re.findall(r'(?i)\bмицели\w*\b',r['source']))),'missingCount':len(missing),'completeSourceFamily':[{'stableId':r['stableId'],'key':r['key'],'source':r['source'],'target':targets[r['stableId']],'authoredPath':paths[r['stableId']],'inCycle003Closure':r['stableId'] in closed,'nodeNames':r.get('nodeNames',[])} for r in family],'actualCompiledNodes':{n:nodes.get(n) for n in sorted(names)},'boundedFullNodeContext':[{'stableId':r['stableId'],'key':r['key'],'source':r['source'],'target':targets[r['stableId']],'nodeNames':r.get('nodeNames',[])} for r in source if r['stableId'] in targets and names.intersection(r.get('nodeNames',[]))]}
p=D/'mycelium-inflection-closure-finding-evidence.json';assert not p.exists();p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
for r in out['completeSourceFamily']:
 if not r['inCycle003Closure']:print(r['key'],r['stableId'],'\nRU:',r['source'],'\nHI:',r['target'],'\nNODES:',r['nodeNames'])
print('Family',len(family),'missing',len(missing),'forms',out['familyForms'])
