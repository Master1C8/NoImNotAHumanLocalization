import json,pathlib,sys,hashlib
sys.path.insert(0,'Scripts');from probe_assets import DEFAULT_GAME,EXPECTED_UNITY;from unity_types import CheckedTypeTreeGenerator,generated_tree
import UnityPy
O=pathlib.Path(__file__).parent;path=DEFAULT_GAME/'NoImNotAHuman_Data/level1';env=UnityPy.load(str(path));objects=env.file.objects
G=CheckedTypeTreeGenerator(EXPECTED_UNITY);G.load_local_dll_folder(str(DEFAULT_GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed'));env.typetree_generator=G
T={}
def tree(pid):
 if pid not in T:
  ob=objects[pid]
  try:T[pid]=ob.read_typetree()
  except:T[pid]=generated_tree(ob)[0]
 return T[pid]
def go_path(pid):
 out=[]
 while pid:
  gt=tree(pid);out.append({'gameObjectId':pid,'name':gt.get('m_Name'),'active':gt.get('m_IsActive')});comps=[x['component']['m_PathID'] for x in gt.get('m_Component',[])];trs=[x for x in comps if objects[x].type.name in ['Transform','RectTransform']]
  if not trs:break
  father=tree(trs[0]).get('m_Father',{}).get('m_PathID',0);pid=tree(father)['m_GameObject']['m_PathID'] if father else 0
 return out[::-1]
ids=[3842,3856,4228,4275];rows=[]
for pid in ids:
 tt=tree(pid);go=tt['m_GameObject']['m_PathID'];gt=tree(go);comps=[]
 for x in gt['m_Component']:
  cp=x['component']['m_PathID'];ob=objects[cp]
  if ob.type.name=='MonoBehaviour':
   try:ct=generated_tree(ob)[0]
   except Exception as e:ct={'error':str(e),'head':str(ob.parse_monobehaviour_head())}
   comps.append({'pathId':cp,'tree':ct})
 row={'stableId':f'tmp:level1:{pid}:m_text','path':go_path(go),'siblingsComponents':comps};rows.append(row);print(row['stableId'],row['path'])
result={'sourceAsset':str(path),'sourceSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':rows};(O/'static-context.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
