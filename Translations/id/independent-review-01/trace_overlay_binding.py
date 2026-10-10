"""Inspect only source objects containing the unresolved UI consumer key."""
import sys,json,hashlib,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Scripts'))
import UnityPy
from probe_assets import DEFAULT_GAME,EXPECTED_UNITY
from unity_types import CheckedTypeTreeGenerator,generated_tree
pins=json.loads((ROOT/'Documentation/other-serialized-text-scope-v2.json').read_text())['sourceFiles']
generator=CheckedTypeTreeGenerator(EXPECTED_UNITY)
generator.load_local_dll_folder(str(DEFAULT_GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed'))
found=[]
for rel in pins:
 p=DEFAULT_GAME/rel;sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha==pins[rel]
 if struct.pack('<q',3800) not in p.read_bytes():continue
 env=UnityPy.load(str(p));env.typetree_generator=generator
 for o in env.objects:
  if o.type.name!='MonoBehaviour':continue
  if struct.pack('<q',3800) not in o.get_raw_data():continue
  tree,_=generated_tree(o)
  if '_overlaySubtitlesView' not in tree:continue
  found.append({'sourcePath':rel,'sourceSha256':sha,'pathId':o.path_id,'tree':tree})
out=Path(__file__).resolve().parent/'overlay-subtitle-binding.json';out.write_text(json.dumps(found,ensure_ascii=False,indent=2)+'\n');print(json.dumps(found,ensure_ascii=False,indent=2))
