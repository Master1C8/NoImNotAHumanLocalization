#!/usr/bin/env python3
"""Offline decoding using field and opcode constants from the shipped managed assembly."""
import hashlib,json,struct
from pathlib import Path
import dnfile
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
managed=Path(json.loads((ROOT/'dynamic-producer-context.json').read_text())['assemblyPath']).parent
assembly=managed/'YarnSpinner.dll';pe=dnfile.dnPE(str(assembly));owners={id(f.row):str(t.TypeName) for t in pe.net.mdtables.TypeDef for f in t.FieldList}
constants={}
for c in pe.net.mdtables.Constant:
 o=owners.get(id(c.Parent.row));n=str(c.Parent.row.Name)
 if o in ['Program','Node','Instruction','Operand','OpCode']:constants[f'{o}.{n}']=int.from_bytes(bytes(c.Value.value),'little')
assert constants['Program.NodesFieldNumber']==2 and constants['Node.InstructionsFieldNumber']==2
assert constants['Instruction.OpcodeFieldNumber']==1 and constants['Instruction.OperandsFieldNumber']==2
assert constants['Operand.StringValueFieldNumber']==1 and constants['Operand.BoolValueFieldNumber']==2 and constants['Operand.FloatValueFieldNumber']==3
opnames={v:k.split('.')[-1] for k,v in constants.items() if k.startswith('OpCode.')}
def vi(b,p):
 v=0;s=0
 while True:
  z=b[p];p+=1;v|=(z&127)<<s
  if not z&128:return v,p
  s+=7;assert s<=70

def wire(b):
 p=0;out=[]
 while p<len(b):
  tag,p=vi(b,p);f,w=tag>>3,tag&7
  if w==0:v,p=vi(b,p)
  elif w==2:n,p=vi(b,p);v=b[p:p+n];p+=n
  elif w==5:v=b[p:p+4];p+=4
  elif w==1:v=b[p:p+8];p+=8
  else:raise ValueError(w)
  out.append((f,w,v))
 assert p==len(b);return out

def operand(b):
 fs=wire(b);assert len(fs)==1;f,w,v=fs[0]
 if f==1:return v.decode('utf8')
 if f==2:return bool(v)
 if f==3:return struct.unpack('<f',v)[0]
 raise ValueError(f)
raw=bytes(json.loads((ROOT/'Source/glossary-corpus-v2/runtime-bindings.json').read_text())['sharedassets0.assets:2743']['compiledYarnProgram'])
closure=json.loads((ROOT/'Translations/fil/semantic-correction-cycle-001.closure.json').read_text());assert hashlib.sha256(raw).hexdigest()==closure['compiledYarnProgramSha256']
want=set(closure['runtimeNodes'])|{'entrance_staticboy','StaticBoy_Entrance_1','StaticBoy_Entrance_2'};nodes={}
for f,w,entry in wire(raw):
 if f!=2:continue
 ef=wire(entry);name=next(v.decode() for f,w,v in ef if f==1);node=next(v for f,w,v in ef if f==2)
 if name not in want:continue
 nf=wire(node);ins=[];labels={}
 for f,w,v in nf:
  if f==2:
   fs=wire(v);opcode=next((v for f,w,v in fs if f==1),0);args=[operand(v) for f,w,v in fs if f==2];ins.append(dict(index=len(ins),opcode=opcode,op=opnames[opcode],operands=args))
  elif f==3:
   fs=wire(v);labels[next(v.decode() for f,w,v in fs if f==1)]=next((v for f,w,v in fs if f==2),0)
 nodes[name]=dict(labels=labels,instructions=ins)
assert set(nodes)==want
out=BASE/'decoded-yarn-context.json';assert not out.exists()
out.write_text(json.dumps(dict(assemblyPath=str(assembly),assemblySha256=hashlib.sha256(assembly.read_bytes()).hexdigest(),schemaConstants=constants,compiledProgramSha256=hashlib.sha256(raw).hexdigest(),nodeCount=len(nodes),nodes=nodes),ensure_ascii=False,indent=2)+'\n')
print('decoded nodes',len(nodes),'instructions',sum(len(x['instructions']) for x in nodes.values()))
for name in ['tv_8_necessary','tv_10_necessary','Twins_Entrance_Bribe','Twins_Entrance_BothOccupied','Twins_Entrance_AlkonostOccupied','Doctor_Entrance_Occupied','Anxiety_Entrance_Occupied','entrance_staticboy']:
 print(name,'labels',nodes[name]['labels'])
 for i in nodes[name]['instructions']:print(i['index'],i['op'],i['operands'])
