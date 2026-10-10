import json,sys,importlib.util
from pathlib import Path
R=Path.cwd();H=R/'Translations/hi';P=Path(__file__).parent
j=lambda p:json.loads(p.read_text())
src=[json.loads(x) for x in (R/'Source/localization-inventory-v3/strings.jsonl').read_text().splitlines()]
t={}
for f in j(H/'semantic-cycle-002-structural-gate.json')['files']:
 d=j(R/f['path'])
 if 'collection' in d:
  for e in d['entries']:t[d['collection'],str(e['id'])]=e['target']
src=[r for r in src if (r['collection'],r['stableId'].rsplit(':',1)[1]) in t]
sp=importlib.util.spec_from_file_location('c',H/'build-semantic-cycle-002-closure.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);nodes=m.runtime_nodes(m.helper().fields)
for node in sys.argv[1:]:
 print('NODE',node,'COMPILED',node in nodes)
 if node in nodes:
  print('BRANCH ORDER',json.dumps(nodes[node],ensure_ascii=False,separators=(',',':')))
 for r in src:
  if node in r.get('nodeNames',[]):
   print('KEY',r['key'],'SID',r['stableId']);print('RU',r['source']);print('HI',t[r['collection'],r['stableId'].rsplit(':',1)[1]])
