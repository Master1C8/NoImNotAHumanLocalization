"""Compact reader v5. Internal visited-counter plumbing is omitted from display.
All text, option destinations, commands and non-counter state/branch calls remain.
The complete immutable decoded node remains available via context_batch_v3.
"""
import context_batch_v3 as c
import sys,json
start,stop=map(int,sys.argv[1:3]); names=[]; orphan=[]
for r in c.closure[start:stop]:
 if r['collection']!='Dialogs':continue
 matches=c.consumers.get(r['key'],[])
 if not matches:orphan.append(r)
 for name,_ in matches:
  if name not in names:names.append(name)
for name in names:
 print('NODE',name); control=[]
 for ins in c.nodes[name]:
  args=ins['operands']; op=ins['opcode']
  if op in (2,4) and args and args[0] in c.source:
   k=args[0]; mark=c.index.get(k,'context')
   print(str(mark)+'@'+str(ins['index'])+(' OPTION' if op==4 else '')+' '+c.source[k]['source']+' => '+c.targets.get(k,'[target unavailable]'))
   if op==4:control.append([ins['index'],'option',args[1:]])
  elif op in (3,6,10,12,13,14,16):
   if op in (13,14) and args and args[0].startswith('$Yarn.Internal.Visiting.'):continue
   if op==12 and args and args[0] in ('visited','Number.Add'):continue
   if op==6 and args==[name]:continue
   control.append([ins['index'],op,args])
 print('CONTROL',json.dumps(control,ensure_ascii=False,separators=(',',':')))
for r in orphan:print('ORPHAN',c.index[r['key']],r['source'],'=>',r['target'])
print('PRESENTED_CLOSURE_INDICES',json.dumps(sorted({c.index[a] for n in names for ins in c.nodes[n] for a in ins['operands'] if isinstance(a,str) and a in c.index}|{c.index[r['key']] for r in orphan})))
