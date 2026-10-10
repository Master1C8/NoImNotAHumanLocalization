"""Read only the pinned source managed assembly; preserve bounded IL evidence."""
import hashlib,json,sys
from pathlib import Path
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBytes
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Scripts'))
from probe_assets import DEFAULT_GAME
assembly=DEFAULT_GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Assembly-CSharp.dll'
digest=hashlib.sha256(assembly.read_bytes()).hexdigest()
pin=json.loads((ROOT/'Source/glossary-corpus-v2/report.json').read_text())['sourcePins'][str(assembly.relative_to(DEFAULT_GAME))]
assert digest==pin
pe=dnfile.dnPE(str(assembly)); tables=pe.net.mdtables
def resolve(operand):
    token=getattr(operand,'value',None)
    if token is None:return str(operand)
    kind,index=token>>24,token&0xffffff
    if kind==0x70:
        raw,_=pe.net.user_strings.get_with_size(index);return raw.decode('utf-16le')
    table={0x06:'MethodDef',0x0a:'MemberRef',0x04:'Field',0x01:'TypeRef',0x02:'TypeDef',0x2b:'MethodSpec'}.get(kind)
    if table:
        r=getattr(tables,table).rows[index-1]
        return table+':'+str(getattr(r,'Name',getattr(r,'TypeName',getattr(r,'Method',''))))
    return hex(token)
selected=[]
for t in tables.TypeDef.rows:
    for idx in t.MethodList:
        m=idx.row;name=str(m.Name);owner=str(t.TypeName)
        if not m.Rva:continue
        if name=='GetCharacterOnPlace' or name.startswith('<GetCharacterOnPlace>') or owner=='GameplayEndingMushroom' or name in ['TryGiveItemFor','GiveItemFor']:
            body=CilMethodBody(CilMethodBodyReaderBytes(pe.get_data(m.Rva,12000)))
            lines=[{'offset':i.offset,'op':i.opcode.name,'operand':resolve(i.operand) if hasattr(i.operand,'value') else str(i.operand)} for i in body.instructions]
            selected.append({'type':owner,'method':name,'rva':m.Rva,'instructions':lines})
p=OUT/'managed-consumers.json';assert not p.exists();p.write_text(json.dumps({'assemblyPath':str(assembly),'assemblySha256':digest,'matchesOriginalCorpusPin':True,'methods':selected},ensure_ascii=False,indent=2)+'\n')
for m in selected:
    print(m['type'],m['method'])
    for i in m['instructions']:print(i['offset'],i['op'],i['operand'])
