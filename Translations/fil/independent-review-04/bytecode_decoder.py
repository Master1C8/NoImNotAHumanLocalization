import json,hashlib,struct
from pathlib import Path
import dnfile
ROOT=Path(__file__).resolve().parents[3]
def load(p):return json.loads(p.read_text())
h=load(ROOT/"Translations/fil/semantic-correction-cycle-004/handoff.json")
# Independently decode actual program with enum/field constants from shipped assembly.
assembly=Path(load(ROOT/'dynamic-producer-context.json')['assemblyPath']).parent/'YarnSpinner.dll';pe=dnfile.dnPE(str(assembly));owners={id(f.row):str(t.TypeName) for t in pe.net.mdtables.TypeDef for f in t.FieldList};constants={}
for c in pe.net.mdtables.Constant:
 owner=owners.get(id(c.Parent.row))
 if owner in ['Program','Node','Instruction','Operand','OpCode']:constants[owner+'.'+str(c.Parent.row.Name)]=int.from_bytes(bytes(c.Value.value),'little')
ops={v:k.split('.')[-1] for k,v in constants.items() if k.startswith('OpCode.')}
def vi(b,p):
 v=0;s=0
 while True:
  z=b[p];p+=1;v|=(z&127)<<s
  if not z&128:return v,p
  s+=7;assert s<=70

def wire(b):
 p=0;fs=[]
 while p<len(b):
  tag,p=vi(b,p);f,w=tag>>3,tag&7
  if w==0:v,p=vi(b,p)
  elif w==2:n,p=vi(b,p);v=b[p:p+n];p+=n
  elif w==5:v=b[p:p+4];p+=4
  elif w==1:v=b[p:p+8];p+=8
  else:raise AssertionError(w)
  fs.append((f,w,v))
 assert p==len(b);return fs

def operand(b):
 fs=wire(b);assert len(fs)==1;f,w,v=fs[0]
 if f==constants['Operand.StringValueFieldNumber']:return v.decode()
 if f==constants['Operand.BoolValueFieldNumber']:return bool(v)
 if f==constants['Operand.FloatValueFieldNumber']:return struct.unpack('<f',v)[0]
 raise AssertionError(f)
raw=bytes(load(ROOT/'Source/glossary-corpus-v2/runtime-bindings.json')['sharedassets0.assets:2743']['compiledYarnProgram']);assert hashlib.sha256(raw).hexdigest()==h['compiledProgramSha256'];actual={}
for f,w,entry in wire(raw):
 if f!=constants['Program.NodesFieldNumber']:continue
 fs=wire(entry);name=next(v.decode() for f,w,v in fs if f==1);node=next(v for f,w,v in fs if f==2);ins=[];labels={}
 for f,w,v in wire(node):
  if f==constants['Node.InstructionsFieldNumber']:
   ff=wire(v);op=next((v for f,w,v in ff if f==constants['Instruction.OpcodeFieldNumber']),0);args=[operand(v) for f,w,v in ff if f==constants['Instruction.OperandsFieldNumber']];ins.append(dict(index=len(ins),opcode=op,op=ops[op],operands=args))
  elif f==3:
   ff=wire(v);labels[next(v.decode() for f,w,v in ff if f==1)]=next((v for f,w,v in ff if f==2),0)
 actual[name]=dict(labels=labels,instructions=ins)
