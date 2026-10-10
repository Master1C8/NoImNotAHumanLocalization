import json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Scripts'))
from unity_types import CheckedTypeTreeGenerator,generated_tree
import UnityPy
OLD=ROOT/'Translations/el/independent-review-01';HERE=Path(__file__).parent
il=json.loads((OLD/'dynamic-consumer-il.json').read_text());assembly=Path(il['assemblyPath']);asset=assembly.parents[2]/'NoImNotAHuman_Data/sharedassets0.assets';generator=CheckedTypeTreeGenerator('6000.3.10f1');generator.load_local_dll_folder(str(assembly.parent));env=UnityPy.load(str(asset));env.typetree_generator=generator
obj=next(o for o in env.objects if o.path_id==2723);tree,schema=generated_tree(obj);old=json.loads((OLD/'deficit-domain.json').read_text())['tree'];differences={k:{'prior':old.get(k),'actual':tree.get(k)} for k in set(tree)|set(old) if tree.get(k)!=old.get(k)}
output={'tree':tree,'differences':differences,'deficitDomainUnchanged':tree['_deficitConsumables']==old['_deficitConsumables'],'nativeHeaderAndNoOp':'passed by generated_tree','asset':str(asset)}
p=HERE/'fresh-domain-inspection.json';assert not p.exists();p.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'differences':differences,'deficitDomainUnchanged':output['deficitDomainUnchanged']}))
