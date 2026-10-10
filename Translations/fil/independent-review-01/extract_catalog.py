import sys,json,hashlib
from pathlib import Path
import UnityPy,dnfile
from UnityPy.helpers import TypeTreeHelper
from UnityPy.helpers.TypeTreeNode import TypeTreeNode
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];sys.path.insert(0,str(ROOT/'Scripts'))
from unity_types import CheckedTypeTreeGenerator,generated_tree
managed=Path(json.loads((ROOT/'dynamic-producer-context.json').read_text())['assemblyPath']).parent
p=managed.parents[1]/'NoImNotAHuman_Data/sharedassets0.assets'
expected=json.loads((ROOT/'Source/localization-inventory-v3/summary.json').read_text())['sourcePins']['NoImNotAHuman_Data/sharedassets0.assets']
assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
e=UnityPy.load(str(p));g=CheckedTypeTreeGenerator('6000.3.10f1');g.load_local_dll_folder(str(managed));e.typetree_generator=g
# Stripped managed-reference metadata has no class nodes. Recover the exact serialized
# reference type names through the pure Python parser and shipped managed assembly.
TypeTreeHelper.read_typetree_boost=None;TypeTreeHelper.write_typetree_boost=None
schemas={}
def refnode(ref,asset):
 typ=ref['type'];cls=typ['class'];ns=typ['ns'];asm=typ['asm']
 if not cls:return None
 key=(asm,ns,cls)
 if key not in schemas:
  full=ns+'.'+cls if ns else cls
  nodes=g.get_nodes(asm,full)
  schemas[key]=TypeTreeNode.from_list([dict(m_Type=x.m_Type,m_Name=x.m_Name,m_Level=x.m_Level,m_MetaFlag=x.m_MetaFlag) for x in nodes])
 return schemas[key]
TypeTreeHelper.get_ref_type_node=refnode
characters=[];other=None
for obj in e.objects:
 if obj.type.name!='MonoBehaviour':continue
 head=obj.parse_monobehaviour_head()
 cls=head.m_Script.read().m_ClassName
 if cls not in ['CharacterSOData','OtherGameSOData']:continue
 tree,schema=generated_tree(obj)
 if cls=='OtherGameSOData':other=dict(pathId=obj.path_id,tree=tree,rawSha256=hashlib.sha256(obj.get_raw_data()).hexdigest())
 else:characters.append(dict(pathId=obj.path_id,name=head.m_Name,rawSha256=hashlib.sha256(obj.get_raw_data()).hexdigest(),fields={k:v for k,v in tree.items() if 'place' in k.lower() or 'type' in k.lower()}))
pe=dnfile.dnPE(str(managed/'Assembly-CSharp.dll'));owners={id(f.row):str(t.TypeName) for t in pe.net.mdtables.TypeDef for f in t.FieldList};enums={}
for c in pe.net.mdtables.Constant:
 o=owners.get(id(c.Parent.row))
 if o in ['ECharacterType','EConsumable','EPhoneSubscriber','ECharacterPlace','EInfoMessageType','EDream']:
  enums.setdefault(o,{})[str(c.Parent.row.Name)]=int.from_bytes(bytes(c.Value.value),'little',signed=True)
out=dict(assetPath=str(p),assetSha256=expected,unityVersion=str(e.file.unity_version),managedReferenceSchemaKeys=[list(k) for k in schemas],byteExactRoundtrip=True,characters=characters,otherGameData=other,enums=enums)
q=BASE/'independent-source-catalog.json';assert not q.exists();q.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('CATALOG',json.dumps(out,ensure_ascii=False))
