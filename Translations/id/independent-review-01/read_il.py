"""Bounded static CIL inspection of the pinned original game assembly."""
import hashlib,json,sys
from pathlib import Path
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBytes
GAME=Path('/Volumes/KINGSTONMAC/Applications/No Im not a Human.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human')
P=GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Assembly-CSharp.dll'
assert hashlib.sha256(P.read_bytes()).hexdigest()=='c674f171c61b644e6e746e0ced079ffa365abee2336d04ea9e67cbbc93e88213'
pe=dnfile.dnPE(str(P)); owners={m.row_index:str(t.TypeNamespace)+'.'+str(t.TypeName) for t in pe.net.mdtables.TypeDef for m in t.MethodList}
fieldowners={f.row_index:str(t.TypeName) for t in pe.net.mdtables.TypeDef for f in t.FieldList}
def resolve(value):
 if not hasattr(value,'value'): return str(value)
 token=value.value; table=token>>24;index=token&0xffffff
 if table==0x70:
  s=pe.net.user_strings.get(index);return repr(s.value) if s else str(value)
 mapping={0x06:'MethodDef',0x0A:'MemberRef',0x04:'Field',0x01:'TypeRef',0x02:'TypeDef',0x2B:'MethodSpec'}
 name=mapping.get(table)
 if not name:return str(value)
 row=getattr(pe.net.mdtables,name).rows[index-1]
 if name=='MethodDef':return owners[index]+'.'+str(row.Name)
 if name=='Field':return fieldowners[index]+'.'+str(row.Name)
 if name in ['TypeDef','TypeRef']:return str(row.TypeNamespace)+'.'+str(row.TypeName)
 if name=='MemberRef':
  cl=row.Class.row;return str(getattr(cl,'TypeName',getattr(cl,'Name','')))+'.'+str(row.Name)
 return str(value)
needle=sys.argv[1] if len(sys.argv)>1 else 'message_bodyEaterVisit'
matches=[];failures=[]
for index,m in enumerate(pe.net.mdtables.MethodDef.rows,1):
 if not m.Rva:continue
 try: body=CilMethodBody(CilMethodBodyReaderBytes(pe.get_data(m.Rva,100000)))
 except Exception as e:failures.append({'method':index,'error':str(e)});continue
 lines=[{'offset':hex(i.offset),'opcode':str(i.opcode),'operand':resolve(i.operand) if i.operand is not None else ''} for i in body.instructions]
 qualified=owners[index]+'.'+str(m.Name)
 if needle.lower() in qualified.lower() or any(needle.lower() in x['operand'].lower() for x in lines): matches.append({'token':hex(0x06000000+index),'method':qualified,'instructions':lines})
out={'assemblySha256':hashlib.sha256(P.read_bytes()).hexdigest(),'needle':needle,'matches':matches,'parseFailures':failures}
output=Path(__file__).resolve().parent/('il-'+''.join(c if c.isalnum() else '_' for c in needle)+'.json')
output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2))
