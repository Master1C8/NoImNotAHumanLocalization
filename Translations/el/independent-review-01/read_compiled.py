import json,struct,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def var(b,i):
 n=0;shift=0
 while True:
  v=b[i];i+=1;n|=(v&127)<<shift
  if v<128:return n,i
  shift+=7

def fields(b):
 i=0;out=[]
 while i<len(b):
  t,i=var(b,i);n,w=t>>3,t&7
  if w==0:v,i=var(b,i)
  elif w==2:s,i=var(b,i);v=b[i:i+s];i+=s
  elif w==5:v=struct.unpack('<f',b[i:i+4])[0];i+=4
  elif w==1:v=b[i:i+8];i+=8
  else:raise ValueError((i,n,w))
  out.append((n,w,v))
 return out

def operand(b):
 f=fields(b);assert len(f)==1
 n,w,v=f[0]
 return v.decode() if n==1 else v
bind=json.loads((ROOT/'Source/glossary-corpus-v2/runtime-bindings.json').read_text());raw=bytes(bind['sharedassets0.assets:2743']['compiledYarnProgram']);nodes={}
for n,w,v in fields(raw):
 if n!=2:continue
 pair=dict((n,v) for n,w,v in fields(v));name=pair[1].decode();node=fields(pair[2]);instructions=[];labels={}
 for n,w,v in node:
  if n==2:
   parts=fields(v);op=next((v for n,w,v in parts if n==1),0);args=[operand(v) for n,w,v in parts if n==2];instructions.append({'pc':len(instructions),'opcode':op,'args':args})
  if n==3:
   kv=dict((n,v) for n,w,v in fields(v));labels[kv[1].decode()]=kv.get(2,0)
 nodes[name]={'instructions':instructions,'labels':labels}
source={r['key']:r for x in (ROOT/'Source/localization-inventory-v3/strings.jsonl').read_text().splitlines() if (r:=json.loads(x))['collection']=='Dialogs'}
if sys.argv[1]=='export':
 p=Path(__file__).parent/'compiled-context.json';assert not p.exists();p.write_text(json.dumps({'compiledSha256':hashlib.sha256(raw).hexdigest(),'runtimeBindingPath':'Source/glossary-corpus-v2/runtime-bindings.json','runtimeBindingSha256':hashlib.sha256((ROOT/'Source/glossary-corpus-v2/runtime-bindings.json').read_bytes()).hexdigest(),'nodes':nodes},ensure_ascii=False,separators=(',',':'))+'\n');print('exported',len(nodes))
else:
 for name in sys.argv[1:]:
  d=nodes[name];print(name,d['labels'])
  for r in d['instructions']:
   print(r['pc'],r['opcode'],r['args'],source.get(r['args'][0],{}).get('source','') if r['args'] else '')
