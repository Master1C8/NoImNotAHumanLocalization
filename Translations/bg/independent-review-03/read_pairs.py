import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3]
d=json.loads((R/'Translations/bg/semantic-delta-cycle-003.json').read_text())
nodes=json.loads((R/'Translations/bg/independent-review-01/compiled-nodes.json').read_text()); uses={}
for name,n in nodes.items():
 for ins in n['instructions']:
  for op in ins['operands']:
   for field in op:
    if len(field)>2 and isinstance(field[2],str) and field[2].startswith('line:'): uses.setdefault(field[2],[]).append((name,ins['index'],ins['opcode']))
a,b=map(int,sys.argv[1:3])
for i,r in enumerate(d['nextReviewRows'][a:b],a):
 u=uses.get(r['key'],[])
 print(str(i)+' '+r['stableId'].split(':')[-1]+' '+','.join(n+':'+str(x)+(' option' if op==4 else '') for n,x,op in u))
 print('R '+r['source']);print('B '+r['target'])
