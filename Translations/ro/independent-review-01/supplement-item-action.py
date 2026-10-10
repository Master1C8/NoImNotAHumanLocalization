"""One bounded identical-source consumer dependency family; no authored mutation."""
import hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('recipe',ROOT/'Translations/ro/correction-cycle-001-recipe-v3.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=json.loads(m.PROGRESS.read_text());rows=[]
for x in p['reviewSegments']:rows.extend(json.loads(l) for l in (ROOT/x['path']).read_text().splitlines())
_,values,locations=m.authored();closure=[json.loads(l) for l in (ROOT/'Translations/ro/correction-cycle-001-closure-v3/review-rows.jsonl').read_text().splitlines()];closed={r['stableId'] for r in closure}
rules=json.loads(m.MANIFEST.read_text());rules={r['stableId']:r for r in rules['tableRows']+rules['staticRows']};from preserve_exact import check_value
sys.path.insert(0,str(OUT));from compiled_context import load
nodes,h=load();bind={}
for name,ins in nodes.items():
 for i in ins:
  if i['opcode'] in [2,4] and i['operands']:bind.setdefault(i['operands'][0],[]).append({'node':name,'instruction':i['index'],'instructions':ins})
family=[];contexts={}
for r in sorted(rows,key=lambda r:r['ordinal']):
 if r['source']!='Выдать явку в КЧС':continue
 assert values[r['stableId']]=='Emite un ordin de prezentare la Comitet'
 target='Înmânează ordinul de prezentare la Comitet';check_value(rules[r['stableId']],target)
 placements=bind.get(r['key'],[])
 for b in placements:contexts[b['node']]=b['instructions']
 family.append({'findingId':f'ro-ir01-{r["ordinal"]:05d}','ordinal':r['ordinal'],'stableId':r['stableId'],'collection':r['collection'],'key':r['key'],'source':r['source'],'currentTarget':values[r['stableId']],'proposedTarget':target,'reason':'The Player hands an already owned Povistka document to the resident. Compiled GetItemCount(Povistka)>0 guards this choice, then TryGiveItemFor transfers it and FEMA_GivingPostcard follows. Emite instead tells the Player to issue/create an order. Approved fema-notice identifies an existing document received from Firefighter. Preserve the transfer action.','defectGroup':'existing-item-transfer','authoredPath':locations[r['stableId']][0],'insideAuthoritativeClosure':r['stableId'] in closed,'fullUnitRead':True,'compiledPlacements':[{'node':b['node'],'instruction':b['instruction']} for b in placements],'consumerLimit':'Where a current Russian table key is supplemental/unbound, no live reachability is asserted; the source action and target still differ.'})
old=json.loads((OUT/'findings.json').read_text())['findings'];combined=sorted(old+family,key=lambda x:x['ordinal']);assert len({f['stableId'] for f in combined})==len(combined)
def write(name,data):
 path=OUT/name;assert not path.exists();path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
write('item-action-family.json',{'exactSource':'Выдать явку в КЧС','familyCount':len(family),'sourceOrderCanonical':True,'programSha256':h,'findings':family,'consumerNodes':contexts,'notAFullSemanticRestart':True})
write('consolidated-findings.json',{'schemaVersion':1,'status':'Author adjudication required; closure not accepted','findingCount':len(combined),'closureFindingCount':sum(f['insideAuthoritativeClosure'] for f in combined),'dependencyFindingCount':sum(not f['insideAuthoritativeClosure'] for f in combined),'defectGroups':sorted({f['defectGroup'] for f in combined}),'findings':combined,'proposedTargetsPreserveExactlyPassed':True,'authoredEdits':0,'supersedesForConsolidation':'findings.json (retained immutable initial31; this is the complete review proposal set)'})
found={f['stableId']:f for f in combined};path=OUT/'per-id-decisions-final.jsonl';assert not path.exists()
with path.open('w') as file:
 for line in (OUT/'per-id-decisions.jsonl').read_text().splitlines():
  r=json.loads(line)
  if r['stableId'] in found:r['decision']='correction-proposed';r['findingId']=found[r['stableId']]['findingId']
  file.write(json.dumps(r,ensure_ascii=False)+'\n')
print('identical source family',len(family),'bound',sum(bool(x['compiledPlacements']) for x in family),'total proposals',len(combined),'closure',sum(f['insideAuthoritativeClosure'] for f in combined),'dependency',sum(not f['insideAuthoritativeClosure'] for f in combined))
