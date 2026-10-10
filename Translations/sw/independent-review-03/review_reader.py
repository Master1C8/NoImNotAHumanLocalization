"""Current cycle03 read adapter; generates no translation wording."""
import importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
CYCLE=ROOT/'Translations/sw/semantic-correction-cycle-03'
def rows(p):return [json.loads(x) for x in p.read_text().splitlines()]
spec=importlib.util.spec_from_file_location('prior_reader',ROOT/'Translations/sw/independent-review-02/review_reader.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
nodes=p.nodes;program_hash=p.program_hash
current={r['stableId']:r for r in rows(CYCLE/'projected-targets.jsonl')}
source=p.source
keyrows={r['key']:dict(r,target=current[r['stableId']]['target']) for r in source.values() if r.get('collection')=='Dialogs' and r['stableId'] in current}
delta=rows(CYCLE/'review-delta.jsonl')
consumers={}
for n,instructions in nodes.items():
 for ins in instructions:
  a=ins['operands']
  if ins['opcode'] in (2,4) and a and a[0] in keyrows:consumers.setdefault(a[0],[]).append([n,ins['index'],ins['opcode'],a[1:]])
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='read':
  a,b=map(int,sys.argv[2:4])
  for j,r in enumerate(delta[a:b],a):
   print(j,r['sourceIndex'],r['key'],r['reasons'],consumers.get(r['key'],[]));print('RU',r['source']);print('SW',r['target'])
 elif mode=='context':
  names=list(dict.fromkeys(n for r in delta for n,_,_,_ in consumers.get(r['key'],[])))
  a,b=map(int,sys.argv[2:4]);keys={r['key'] for r in delta}
  for n in names[a:b]:
   print('NODE',n)
   for ins in nodes[n]:
    op=ins['opcode'];a=ins['operands']
    if op in (2,4) and a and a[0] in keyrows:
     r=keyrows[a[0]];print(ins['index'],'OPTION' if op==4 else 'LINE','DELTA' if r['key'] in keys else 'CONTEXT',r['key'],a[1:]);print('RU',r['source']);print('SW',r['target'])
    elif not(op in (13,14) and a and str(a[0]).startswith('$Yarn.Internal.Visiting.')) and not(op==12 and a and a[0] in ('visited','Number.Add')):print(ins['index'],'OP',op,a)
 elif mode=='stats':
  names=list(dict.fromkeys(n for r in delta for n,_,_,_ in consumers.get(r['key'],[])))
  print('nodes',len(names),'no-consumer',[(r['sourceIndex'],r['key']) for r in delta if not consumers.get(r['key'])]);print(names)
