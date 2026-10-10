import json,hashlib
from pathlib import Path
import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
path=Path(json.loads((ROOT/'dynamic-producer-context.json').read_text())['assemblyPath']);pe=dnfile.dnPE(str(path))
mt=pe.net.mdtables
owners={id(x.row):str(t.TypeName) for t in mt.TypeDef for x in t.MethodList+t.FieldList}
def resolve(v):
 if v is None:return None
 if hasattr(v,'value'):
  token=v.value;table=token>>24;rid=token&0xffffff
  if table==0x70:return str(pe.net.user_strings.get(rid).value)
  names={0x04:'Field',0x06:'MethodDef',0x0a:'MemberRef',0x2b:'MethodSpec',0x01:'TypeRef',0x02:'TypeDef'}
  n=names.get(table)
  if n:
   r=getattr(mt,n).rows[rid-1]
   if n=='MethodSpec':return 'MethodSpec:'+resolve(r.Method)
   return n+':'+str(getattr(r,'Name',getattr(r,'TypeName','?')))+' ['+owners.get(id(r),'')+']'
  return str(token)
 return str(v)
selected={};refs=[]
want={'OnPeekedDeficitItem','OnGotCourierOrder','OnGotPhoneNumber','GetDeficitItem','<GetDeficitItem>b__16_0','<GetDeficitItem>b__16_1','GeneratePhoneNumber','<GeneratePhoneNumber>b__0','RestorePhoneNumbers','get_PhoneNumbers','get_DeficitConsumables','GetPlace'}
for t in mt.TypeDef:
 for m in t.MethodList:
  r=m.row
  if not r.Rva:continue
  try: body=read_method_body_from_bytes(pe.get_data(r.Rva,100000))
  except Exception:continue
  ins=[dict(offset=i.offset,op=str(i.opcode),operand=resolve(i.operand)) for i in body.instructions]
  name=str(t.TypeName)+'.'+str(r.Name)
  relevant=[i for i in ins if i['operand'] and any(k in i['operand'] for k in ['OnPeekedDeficitItem','OnGotCourierOrder','OnGotPhoneNumber','EaterVisit','message_bodyEater'])]
  if relevant:refs.append(dict(method=name,references=relevant))
  if str(r.Name) in want or any(i['operand'] and 'EaterVisit' in i['operand'] for i in ins):selected[name]=ins
out=dict(assemblyPath=str(path),assemblySha256=hashlib.sha256(path.read_bytes()).hexdigest(),methods=selected,registrationAndNotificationReferences=refs)
p=BASE/'independent-callbacks.json';assert not p.exists();p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('METHODS',list(selected));print('REFERENCES',json.dumps(refs,ensure_ascii=False))
for n,ins in selected.items():
 print(n)
 for i in ins:print(i['offset'],i['op'],i['operand'])
