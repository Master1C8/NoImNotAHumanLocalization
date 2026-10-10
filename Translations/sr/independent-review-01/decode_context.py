"""Read pinned compiled Yarn evidence; save immutable review-only context."""
import json, hashlib, struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def var(b,i):
 n=0;s=0
 while True:
  v=b[i];i+=1;n|=(v&127)<<s;s+=7
  if v<128:return n,i

def fields(b):
 i=0;r=[]
 while i<len(b):
  k,i=var(b,i);f,w=k>>3,k&7
  if w==0:v,i=var(b,i)
  elif w==2:n,i=var(b,i);v=b[i:i+n];i+=n
  elif w==5:v=struct.unpack('<f',b[i:i+4])[0];i+=4
  else:raise ValueError(w)
  r.append((f,v))
 return r

def operand(b):
 f,v=fields(b)[0]
 return v.decode() if f==1 else v

bindings=ROOT/'Source/glossary-corpus-v2/runtime-bindings.json'
report=json.loads((ROOT/'Source/glossary-corpus-v2/report.json').read_text())
assert sha(bindings)==report['runtimeBindingsSha256']
b=bytes(json.loads(bindings.read_text())['sharedassets0.assets:2743']['compiledYarnProgram'])
assert hashlib.sha256(b).hexdigest()==report['currentScope']['compiledProgramSha256']
nodes={}
for f,v in fields(b):
 if f!=2:continue
 p=dict(fields(v));name=p[1].decode();instructions=[];labels={};headers={}
 for nf,nv in fields(p[2]):
  if nf==2:
   ins=fields(nv);instructions.append({'index':len(instructions),'opcode':next((v for f,v in ins if f==1),0),'operands':[operand(v) for f,v in ins if f==2]})
  if nf==3:
   lab=dict(fields(nv));labels[lab[1].decode()]=lab.get(2,0)
  if nf==6:
   h=dict(fields(nv));headers[h[1].decode()]=h[2].decode()
 nodes[name]={'instructions':instructions,'labels':labels,'headers':headers}
rows=[json.loads(l) for l in (ROOT/'Translations/sr/semantic-cycle-001-review-rows.jsonl').open()]
source={r['key']:r for r in (json.loads(l) for l in (ROOT/'Source/localization-inventory-v3/strings.jsonl').open()) if r['collection']=='Dialogs'}
closure=json.loads((ROOT/'Translations/sr/semantic-cycle-001-closure.json').read_text());target={}
for f in closure['currentAuthoredFileHashes']:
 batch=json.loads((ROOT/f['path']).read_text())
 if batch.get('collection')=='Dialogs':target.update({str(e['id']):e['target'] for e in batch['entries']})
chosen=sorted({n for r in rows for n in r['nodeNames']})
context={}
for n in chosen:
 node=nodes.get(n)
 if not node:context[n]={'status':'not in compiled nodes; supplemental source table'};continue
 node=dict(node)
 node['instructions']=[dict(i) for i in node['instructions']]
 for i in node['instructions']:
  line=next((o for o in i['operands'] if isinstance(o,str) and o.startswith('line:')),None)
  if line:
   s=source[line];i.update({'stableId':s['stableId'],'source':s['source'],'target':target[s['stableId'].split(':')[-1]],'inReviewSet':s['stableId'] in set(closure['closureIds'])})
 context[n]=node
out={'bindingsSha256':sha(bindings),'compiledProgramSha256':hashlib.sha256(b).hexdigest(),'scope':'Decoded instruction order, labels, calls and source/current target for all closure-associated nodes. Static serialized evidence, not runtime reachability.','nodes':context}
p=OUT/'yarn-context.json';assert not p.exists();p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'nodes':len(context),'compiledNodes':sum('instructions' in v for v in context.values()),'contextSha256':sha(p)}))
