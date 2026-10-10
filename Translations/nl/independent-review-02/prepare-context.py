from pathlib import Path
import json,hashlib,struct
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).parent
binding=ROOT/'Source/glossary-corpus-v2/runtime-bindings.json'
report=json.loads((ROOT/'Source/glossary-corpus-v2/report.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(binding)==report['runtimeBindingsSha256']
b=bytes(json.loads(binding.read_text())['sharedassets0.assets:2743']['compiledYarnProgram'])
assert hashlib.sha256(b).hexdigest()==report['currentScope']['compiledProgramSha256']
def decode(b):
 p=0; out=[]
 def var():
  nonlocal p
  n=s=0
  while True:
   q=b[p];p+=1;n|=(q&127)<<s;s+=7
   if q<128:return n
 while p<len(b):
  t=var();f,w=t>>3,t&7
  if w==0:v=var()
  elif w==2:l=var();v=b[p:p+l];p+=l
  elif w==5:v=struct.unpack('<f',b[p:p+4])[0];p+=4
  elif w==1:v=b[p:p+8];p+=8
  else:raise ValueError((p,w))
  out.append((f,w,v))
 return out
nodes={}
for f,w,e in decode(b):
 if f!=2:continue
 d=decode(e);name=next(v.decode() for f,w,v in d if f==1);nb=next(v for f,w,v in d if f==2)
 instructions=[]
 for f,w,v in decode(nb):
  if f!=2:continue
  ins=[]
  for x,y,z in decode(v):
   if y==2:z=[(a,c.decode(errors='replace') if d==2 else c) for a,d,c in decode(z)]
   ins.append((x,z))
  instructions.append(ins)
 nodes[name]=instructions
rows=[json.loads(l) for l in (ROOT/'Translations/nl/semantic-cycle-2/closure/delta-review-rows.jsonl').read_text().splitlines()]
selected=sorted({n for r in rows for n in r['nodeNames']})
scene={n:{'instructions':nodes[n], 'reviewedDeltaRowsInThisNode':[r['stableId'] for r in rows if n in r['nodeNames']]} for n in selected}
old=json.loads((ROOT/'Translations/nl/independent-review-01/consumer-context.json').read_text())
for field in ['getterCpp','localizationCpp']:
 assert sha(ROOT/old[field]['path'])==old[field]['sha256']
obj={'bindingPath':str(binding.relative_to(ROOT)),'bindingSha256':sha(binding),'compiledProgramSha256':hashlib.sha256(b).hexdigest(),'scenes':scene,'unboundDeltaRows':[r['stableId'] for r in rows if not r['nodeNames']], 'reusedGetterAndLocalizationEvidence':'Translations/nl/independent-review-01/consumer-context.json', 'reusedGetterAndLocalizationEvidenceSha256':sha(ROOT/'Translations/nl/independent-review-01/consumer-context.json')}
p=OUT/'consumer-context.json';assert not p.exists();p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
for n in selected:
 if 'Occupied' in n:
  print(n)
  for i,ins in enumerate(nodes[n]):
   if any(f==2 and any(k==1 and isinstance(v,str) and ('GetCharacterOnPlace' in v or v.startswith('line:')) for k,v in z) for f,z in ins):print(i,ins)
print('Bound nodes:',len(selected),'unbound delta:',len(obj['unboundDeltaRows']))
