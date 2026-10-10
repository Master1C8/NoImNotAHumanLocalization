import json,sys
from pathlib import Path
import context_batch_v3 as c
scope=json.loads(Path('Documentation/static-text-scope-v2.json').read_text())['rows']
a,b=map(int,sys.argv[1:])
for i,r in enumerate(c.closure[a:b],a):
 matches=[]
 for x in scope:
  if x['stableId']==r['stableId'] or any(v.get('sourceStableId')==r['stableId'] for v in x.get('localizedStringBindings',[])):
   matches.append({'staticId':x['stableId'],'ancestry':[(v['name'],v.get('initialActive')) for v in x.get('sceneAncestry',[])],'bindings':x.get('localizedStringBindings',[])})
 print(i,r['key'],json.dumps(r['source'],ensure_ascii=False),' => ',json.dumps(r['target'],ensure_ascii=False),' CONSUMERS ',json.dumps(matches,ensure_ascii=False) if matches else 'no individual serialized TMP match; table/managed binding or source inventory only')
