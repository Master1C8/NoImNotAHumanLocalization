import sys,json,pathlib,hashlib
sys.path.insert(0,'Scripts');from probe_assets import DEFAULT_GAME,EXPECTED_UNITY
from unity_types import CheckedTypeTreeGenerator
from UnityPy.helpers.TypeTreeNode import TypeTreeNode
from UnityPy.helpers import TypeTreeHelper
from UnityPy.streams import EndianBinaryReader
import UnityPy
O=pathlib.Path(__file__).parent;p=DEFAULT_GAME/'NoImNotAHuman_Data/sharedassets0.assets';e=UnityPy.load(str(p));g=CheckedTypeTreeGenerator(EXPECTED_UNITY);g.load_local_dll_folder(str(DEFAULT_GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed'));e.typetree_generator=g
rows=[]
for o in e.objects:
 if o.type.name!='MonoBehaviour':continue
 try:node=o.generate_monobehaviour_node()
 except:continue
 if node.m_Type!='CharacterSOData':continue
 nodes=node.to_dict_list();cut=next(i for i,n in enumerate(nodes) if n['m_Level']==1 and n['m_Name']=='references');nodes=nodes[:cut]
 for n in nodes:
  n.pop('m_Children',None)
  if n['m_Level']==1 and n['m_Name']=='m_Enabled':n['m_MetaFlag']|=0x4000
 nd=TypeTreeNode.from_list(nodes);reader=EndianBinaryReader(o.get_raw_data(),endian=o.reader.endian)
 t=TypeTreeHelper.read_typetree(nd,reader,as_dict=True,byte_size=len(o.get_raw_data()),check_read=False,assetsfile=o.assets_file)
 assert t['m_Name']==o.parse_monobehaviour_head().m_Name
 rows.append({'pathId':o.path_id,'name':t['m_Name'],'characterType':t['_characterType'],'room':t['_room'],'place':t['_place'],'nameLocalizationKey':t['_nameLocalizationKey'],'schemaSha256':hashlib.sha256(json.dumps(nodes,sort_keys=True).encode()).hexdigest(),'rawSha256':hashlib.sha256(o.get_raw_data()).hexdigest(),'prefixBytesParsed':reader.Position,'rawBytes':len(o.get_raw_data()),'registryParsing':'excluded registry tail only; unrelated emotions not required for room/place/key context'})
result={'sourceAsset':str(p),'sourceSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rows':rows};(O/'resident-inputs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('Character rows',len(rows));print([(r['name'],r['characterType'],r['room'],r['place']) for r in rows])
