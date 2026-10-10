"""Read original assembly method bodies and serialized occupant metadata, no game launch."""
import sys,json,hashlib
from pathlib import Path
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBytes
R=Path(__file__).resolve().parents[3];O=Path(__file__).parent
sys.path.insert(0,str(R/'Scripts'))
from probe_assets import DEFAULT_GAME, EXPECTED_UNITY
import UnityPy
from unity_types import CheckedTypeTreeGenerator
from UnityPy.helpers import TypeTreeHelper
from UnityPy.streams import EndianBinaryReader,EndianBinaryWriter
p=DEFAULT_GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Assembly-CSharp.dll'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(p)=='c674f171c61b644e6e746e0ced079ffa365abee2336d04ea9e67cbbc93e88213'
pe=dnfile.dnPE(str(p));tables=pe.net.mdtables
owner={id(x.row):str(t.TypeName) for t in tables.TypeDef.rows for a in ['MethodList','FieldList'] for x in getattr(t,a)}
def resolve(x):
 value=getattr(x,'value',None)
 if value is None:return str(x)
 tid,index=value>>24,value&0xffffff
 if tid==0x70:
  data,_=pe.net.user_strings.get_with_size(index);return data.decode('utf-16le')
 table={0x0a:'MemberRef',0x06:'MethodDef',0x04:'Field',0x01:'TypeRef',0x02:'TypeDef',0x2b:'MethodSpec'}.get(tid)
 if not table:return str(value)
 row=getattr(tables,table).rows[index-1]
 if table=='MethodSpec':row=row.Method.row
 name=next((str(getattr(row,a)) for a in ['Name','TypeName'] if hasattr(row,a)),str(value))
 return owner.get(id(row),'')+'.'+name
methods={};enum={}
for t in tables.TypeDef.rows:
 name=str(t.TypeName)
 if name=='ECharacterType':
  fields={id(x.row):str(x.row.Name) for x in t.FieldList}
  for c in tables.Constant.rows:
   if id(c.Parent.row) in fields:enum[int.from_bytes(c.Value.value,'little',signed=True)]=fields[id(c.Parent.row)]
 for x in t.MethodList:
  m=x.row;mn=str(m.Name)
  if (name=='<>c__DisplayClass224_0' or (name=='CharacterSOData' and mn in ['get_Place','get_Room','get_CharacterType']) or (name=='CharactersManager' and mn in ['get_CharactersInside','GetPlace']) or (name=='DialogCommandsInstance' and mn=='GetCharacterOnPlace')) and m.Rva:
   body=CilMethodBody(CilMethodBodyReaderBytes(pe.get_data(m.Rva,60000)))
   methods[name+'.'+mn]=[{'offset':i.offset,'op':i.opcode.name,'operand':resolve(i.operand) if i.operand is not None else None} for i in body.instructions]
print('IL methods',len(methods))
gen=CheckedTypeTreeGenerator(EXPECTED_UNITY);gen.load_local_dll_folder(str(p.parent))
records=[];pins={str(p):sha(p)}
for filename in ['resources.assets','sharedassets0.assets']:
 asset=DEFAULT_GAME/'NoImNotAHuman_Data'/filename;pins[str(asset)]=sha(asset)
 env=UnityPy.load(str(asset));env.typetree_generator=gen
 for obj in env.objects:
  if obj.type.name!='MonoBehaviour':continue
  try:head=obj.parse_monobehaviour_head();name=head.m_Name
  except Exception:continue
  if head.m_Script.read().m_ClassName!='CharacterSOData':continue
  node=obj.generate_monobehaviour_node()
  raw=obj.get_raw_data();reader=EndianBinaryReader(raw,endian=obj.reader.endian)
  config=TypeTreeHelper.TypeTreeConfig(True,obj.assets_file,False);tree={};children=[]
  for child in node.m_Children:
   if child.m_Name=='references':break
   if child.m_Name=='m_Enabled':child.m_MetaFlag|=0x4000
   tree[child.m_Name]=TypeTreeHelper.read_value(child,reader,config);children.append(child)
  boundary=reader.Position
  writer=EndianBinaryWriter(endian=obj.reader.endian)
  for child in children:TypeTreeHelper.write_value(tree[child.m_Name],child,writer,TypeTreeHelper.TypeTreeConfig(True,obj.assets_file,False))
  assert writer.bytes==raw[:boundary],(name,'prefix roundtrip')
  assert tree['m_Name']==head.m_Name and tree['m_Script']=={'m_FileID':head.m_Script.m_FileID,'m_PathID':head.m_Script.m_PathID}

  if '_characterType' in tree:records.append({'asset':filename,'pathId':obj.path_id,'name':name,'characterType':tree['_characterType'],'character':enum.get(tree['_characterType']),'room':tree.get('_room'),'place':tree.get('_place'),'canExile':tree.get('_canExile'),'allowedDays':tree.get('_allowedDays'),'rawSha256':hashlib.sha256(raw).hexdigest(),'parsedPrefixBytes':boundary,'totalBytes':len(raw),'prefixRoundtrip':'exact; trailing polymorphic registry excluded from field inspection'})
print('DATA count',len(records),'place51',[(r['pathId'],r['name'],r['character']) for r in records if r['place']==51])
out={'assemblySha256':sha(p),'methods':methods,'characterEnum':enum,'assetPins':pins,'characterRecords':records,'physicalRuntime':'not run'}
q=O/'occupant-domain-raw-v2.json';assert not q.exists();q.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
