"""Bounded prefix parse for character place/name context, excluding reference registry."""
import json,hashlib,struct,sys
from pathlib import Path
import dnfile,UnityPy
from UnityPy.helpers import TypeTreeHelper
from UnityPy.helpers.TypeTreeNode import TypeTreeNode
from UnityPy.streams import EndianBinaryReader
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Scripts'))
from probe_assets import DEFAULT_GAME,EXPECTED_UNITY
from unity_types import CheckedTypeTreeGenerator,generated_tree
p=DEFAULT_GAME/'NoImNotAHuman_Data/sharedassets0.assets'
pin=json.loads((ROOT/'Documentation/localization-state.json').read_text())['sourceInputs']['NoImNotAHuman_Data/sharedassets0.assets']
assert hashlib.sha256(p.read_bytes()).hexdigest()==pin
managed=DEFAULT_GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed'
pe=dnfile.dnPE(str(managed/'Assembly-CSharp.dll'))
enum=next(t for t in pe.net.mdtables.TypeDef.rows if str(t.TypeName)=='ECharacterType')
names={}
for f in enum.FieldList:
    for c in pe.net.mdtables.Constant.rows:
        if c.Parent.row is f.row and c.Type==8:names[struct.unpack('<i',c.Value.value)[0]]=str(f.row.Name)
g=CheckedTypeTreeGenerator(EXPECTED_UNITY);g.load_local_dll_folder(str(managed))
env=UnityPy.load(str(p));env.typetree_generator=g
mother,_=generated_tree(env.file.objects[2602]);rows=[]
for ref in mother['_charactersData']:
    assert ref['m_FileID']==0
    obj=env.file.objects[ref['m_PathID']];nodes=obj.generate_monobehaviour_node().to_dict_list()
    cut=next(i for i,n in enumerate(nodes) if n['m_Level']==1 and n['m_Name']=='references')
    nodes=nodes[:cut]
    for n in nodes:
        n.pop('m_Children',None)
        if n['m_Level']==1 and n['m_Name']=='m_Enabled':n['m_MetaFlag']|=0x4000
    schema=TypeTreeNode.from_list(nodes);reader=EndianBinaryReader(obj.get_raw_data(),endian=obj.reader.endian)
    t=TypeTreeHelper.read_typetree(schema,reader,as_dict=True,assetsfile=obj.assets_file,byte_size=obj.byte_size,check_read=False)
    head=obj.parse_monobehaviour_head();assert t['m_Name']==head.m_Name and t['m_Script']=={'m_FileID':head.m_Script.m_FileID,'m_PathID':head.m_Script.m_PathID}
    rows.append({'pathId':obj.path_id,'objectSha256':hashlib.sha256(obj.get_raw_data()).hexdigest(),'name':t['m_Name'],'type':t['_characterType'],'enumName':names[t['_characterType']],'place':t['_place'],'room':t['_room'],'localization':t['_nameLocalizationKey']})
result={'assetSha256':pin,'resourceMotherPathId':2602,'enumNameByValue':names,'rows':rows,'parseScope':'Generated prefix schema through all ordinary fields; ManagedReferencesRegistry is omitted because complete generated parse fails at ref type nodes. Native MonoBehaviour identity validated; no full round trip or source-inventory modification claimed.'}
out=OUT/'character-place-prefix-context.json';assert not out.exists();out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for r in rows:print(r['enumName'],r['place'],r['localization']['m_TableEntryReference'])
