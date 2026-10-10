import json,pathlib,struct,hashlib
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
asset=R/'Source/glossary-corpus-v1/sharedassets0.assets-2743.json';raw=bytes(json.loads(asset.read_text())['compiledYarnProgram'])
def vi(b,i):
 v=0;s=0
 while True:
  c=b[i];i+=1;v|=(c&127)<<s
  if c<128:return v,i
  s+=7

def fields(b):
 out=[];i=0
 while i<len(b):
  tag,i=vi(b,i);n,w=tag>>3,tag&7
  if w==0:v,i=vi(b,i)
  elif w==2:l,i=vi(b,i);v=b[i:i+l];i+=l
  elif w==5:v=struct.unpack('<f',b[i:i+4])[0];i+=4
  elif w==1:v=struct.unpack('<d',b[i:i+8])[0];i+=8
  else:raise ValueError((n,w,i))
  out.append((n,w,v))
 return out
nodes={}
for n,w,v in fields(raw):
 if n==2:
  entry=fields(v);name=next(x[2].decode() for x in entry if x[0]==1);node=next(x[2] for x in entry if x[0]==2);nf=fields(node);instructions=[];labels={}
  for a,b,c in nf:
   if a==2:
    ins=fields(c);opcode=next((d for a,b,d in ins if a==1),0);ops=[]
    for a,b,d in ins:
     if a==2:
      q=fields(d);ops.append({str(e):z.decode() if isinstance(z,bytes) else z for e,_,z in q})
    instructions.append({'index':len(instructions),'opcode':opcode,'operands':ops})
   elif a==3:
    q=fields(c);labels[next(z.decode() for e,_,z in q if e==1)]=next((z for e,_,z in q if e==2),0)
  nodes[name]={'instructions':instructions,'labels':labels,'rawNodeSha256':hashlib.sha256(node).hexdigest()}
cl=json.loads((R/'Translations/fa/audit-cycle-001/closure.json').read_text());names={n for r in cl['reviewRows'] for n in r['nodeNames']};missing=names-set(nodes);assert not missing,missing
result={'assetSha256':hashlib.sha256(asset.read_bytes()).hexdigest(),'compiledProgramSha256':hashlib.sha256(raw).hexdigest(),'closureNodeCount':len(names),'nodes':{n:nodes[n] for n in sorted(names)}}
(O/'compiled-context.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for n in ['Fatman_Entrance_Occupied','Buddy_Entrance_Occupied','MushroomEater_Entrance_3_6','Ballerina_Photo','Intruder_Hands_Gun','selfcheck_armpit_imposter','selfcheck_hands']:
 print(n,json.dumps(nodes.get(n),ensure_ascii=False))
