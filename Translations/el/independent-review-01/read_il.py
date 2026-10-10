import json,hashlib
from pathlib import Path
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBytes
root=Path(__file__).resolve().parents[3]
p=json.load(open(root/'dynamic-producer-context.json')); path=Path(p['assemblyPath']); assert hashlib.sha256(path.read_bytes()).hexdigest()==p['assemblySha256']
pe=dnfile.dnPE(str(path)); tables=pe.net.mdtables; owners={m.row_index:str(t.TypeName) for t in tables.TypeDef.rows for m in t.MethodList}
def resolve(v):
 if not hasattr(v,'value'): return str(v) if v is not None else None
 n=int(v.value); typ=n>>24; idx=n&0xffffff
 if typ==0x70:
  raw,_=pe.net.user_strings.get_with_size(idx);return raw.decode('utf-16le')
 names={6:'MethodDef',10:'MemberRef',4:'Field',2:'TypeDef',1:'TypeRef',43:'MethodSpec'}
 if typ in names:
  row=getattr(tables,names[typ]).rows[idx-1]
  return names[typ]+':'+str(getattr(row,'Name',getattr(row,'TypeName','generic')))+((' ['+owners.get(idx,'')+']') if typ==6 else '')
 return str(v)
output={}
for i,m in enumerate(tables.MethodDef.rows,1):
 name=owners[i]+'.'+str(m.Name)
 if not m.Rva:continue
 if not any(s.lower() in name.lower() for s in ['Deficit','ItemHintView','LocalizeItem','Bribe','GetCharacterOnPlace']):continue
 body=CilMethodBody(CilMethodBodyReaderBytes(pe.get_data(m.Rva,12000)))
 output[name]={'rva':m.Rva,'instructions':[{'offset':x.offset,'op':x.opcode.name,'operand':resolve(x.operand)} for x in body.instructions]}
fields={str(t.TypeName):[str(f.row.Name) for f in t.FieldList] for t in tables.TypeDef.rows if str(t.TypeName)=='EConsumable'}
result={'assemblyPath':str(path),'assemblySha256':p['assemblySha256'],'enumFields':fields,'methods':output}
pout=root/'Translations/el/independent-review-01/dynamic-consumer-il.json';assert not pout.exists();pout.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
