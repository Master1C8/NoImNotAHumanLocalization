import json,sys,hashlib
from pathlib import Path
base=Path(__file__).resolve().parent
root=base.parents[2]
d=json.loads((base/'decoded-yarn-context.json').read_text())
c=json.loads((root/'Translations/fil/semantic-correction-cycle-001.closure.json').read_text())
rows=[json.loads(x) for x in (root/'Translations/fil/semantic-correction-cycle-001.paired.jsonl').read_text().splitlines()]
bykey={r['key']:r for r in rows if r.get('key')}
names=c['runtimeNodes']
a=int(sys.argv[1]);b=int(sys.argv[2])
selected={n:d['nodes'][n] for n in names[a-1:b]}
raw=json.dumps(selected,ensure_ascii=False,indent=2).encode()
out=base/f'compiled-input-{a:02d}-{b:02d}.json'
if out.exists():assert out.read_bytes()==raw
else:out.write_bytes(raw)
print('COMPILED INPUT',out.name,'nodes',len(selected),'sha256',hashlib.sha256(raw).hexdigest())
for i,n in enumerate(names[a-1:b],a):
 node=d['nodes'][n];print('NODE',i,n,'LABELS',node['labels'])
 for ins in node['instructions']:
  print(ins['index'],ins['op'],ins['operands'])
  if ins['op'] in ('RunLine','AddOption'):
   r=bykey.get(ins['operands'][0])
   if r:print(r['acceptedOrdinal'],r['source'],'→',r['target'])
   else:print('LINE OUTSIDE CLOSURE')
