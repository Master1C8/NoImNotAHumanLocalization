import sys,pathlib,json,hashlib
sys.path.insert(0,'Scripts');from probe_assets import DEFAULT_GAME
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBytes
O=pathlib.Path(__file__).parent;p=DEFAULT_GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Assembly-CSharp.dll';pe=dnfile.dnPE(str(p));m=pe.net.mdtables.MethodDef.rows
owner={q.row_index:str(t.TypeName) for t in pe.net.mdtables.TypeDef.rows for q in t.MethodList}
def resolve(op):
 if not hasattr(op,'value'):return str(op) if op is not None else None
 token=int(op.value);kind,idx=token>>24,token&0xffffff
 if kind==0x70:
  x=pe.net.user_strings.get(idx);return str(x)
 if kind==0x2b:
  r=pe.net.mdtables.MethodSpec.rows[idx-1];return 'MethodSpec:'+str(r.Method.row.Name)+' token='+hex(token)+' signature='+r.Instantiation.value.hex()
 table={0x06:'MethodDef',0x0a:'MemberRef',0x04:'Field',0x02:'TypeDef',0x01:'TypeRef',0x2b:'MethodSpec'}.get(kind)
 if table:
  rows=getattr(pe.net.mdtables,table).rows
  if idx<=len(rows):
   r=rows[idx-1];return table+':'+str(getattr(r,'Name',getattr(r,'TypeName',r)))+(' ['+owner.get(idx,'')+']' if kind==6 else '')
 return hex(token)
selected={}
for i,mm in enumerate(m,1):
 name=str(mm.Name);own=owner.get(i,'')
 if 'GetCharacterOnPlace' in name or name in ['GetPlace','get_Place','GetPhoneNumber','GetCourierOrder','LocalizeItem','PeekDeficitItem','GetLocalization'] or 'PhonePin' in own or name in ['UnlockAllPhones','UnlockPhones']:
  if mm.Rva:
   b=CilMethodBody(CilMethodBodyReaderBytes(pe.get_data(mm.Rva,20000)));selected[own+'.'+name]=[{'offset':x.offset,'op':x.opcode.name,'operand':resolve(x.operand)} for x in b.instructions]
r={'assemblyPath':str(p),'assemblySha256':hashlib.sha256(p.read_bytes()).hexdigest(),'methods':selected};(O/'managed-context-v2.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('Normalized methods',len(selected))
