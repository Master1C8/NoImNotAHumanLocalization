import json,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
D=lambda p:hashlib.sha256(p.read_bytes()).hexdigest(); T=lambda s:hashlib.sha256(s.encode()).hexdigest()
f=json.load(open(OUT/'findings.json'))
for x in f['findings']:
 if x.get('closureIndex')==1586:x['glossaryIds']=['babushka']
 if x.get('closureIndex')==1404:x['glossaryIds']=['taxi-driver']
 if x.get('closureIndex')==1110:x['glossaryIds']=['human','fema-wife']
 if x.get('closureIndex')==864:x['glossaryIds']=['death','cultist-three']
f['supersedes']='findings.json';f['supersessionReason']='Canonical speaker-code lookup corrects reference IDs for NotTrue (babushka), and supplies direct TaxiDriver, Wifefema and Cultist3 anchors. Replacement wording and count unchanged.'
p=OUT/'findings-v2.json';assert not p.exists();p.write_text(json.dumps(f,ensure_ascii=False,indent=2)+'\n')
source={r['stableId']:r for line in (ROOT/'Source/localization-inventory-v3/strings.jsonl').read_text().splitlines() if (r:=json.loads(line))}
source.update({r['stableId']:r for line in (ROOT/'Source/localization-inventory-v3/static-text.jsonl').read_text().splitlines() if (r:=json.loads(line))})
results=[]
for x in f['findings']:
 b,a=x['before'],x['proposedTarget'];r=source[x['stableId']]
 slots=lambda s:re.findall(r'\{\d+(?:[^}]*)\}',s)
 tags=lambda s:re.findall(r'<[^>]+>',s)
 numbers=lambda s:re.findall(r'\d+',re.sub(r'<[^>]+>|\{[^}]+\}','',s))
 assert slots(b)==slots(a) and tags(b)==tags(a) and numbers(b)==numbers(a)
 assert all(e['value'] in a for e in r.get('exactSpans',[]))
 results.append({'findingId':x['findingId'],'stableId':x['stableId'],'beforeSha256':T(b),'proposalSha256':T(a),'sameFormatSlots':True,'sameTmpTags':True,'sameNumbers':True,'sourceExactSpansRetained':True})
rows=[json.loads(l) for l in (ROOT/'Translations/el/correction-cycle-001-closure-review.jsonl').read_text().splitlines()]
labels={r['key']:r['currentTarget'] for r in rows if r['collection']=='UI' and (r['key'] or '').startswith('consumable_') and r['key'].endswith('_name')}
assert len(labels)==7
raw=json.load(open(OUT/'deficit-domain.json')); domain={3:'Enerjeka',1:'Cigarette',2:'Coffee',6:'CatFood',8:'Kombucha',7:'Povistka'}
actual=[domain[e['Key']] for e in raw['tree']['_deficitConsumables']['_serializedList']]
examples=[]
for item in actual:
 label=labels['consumable_'+item.lower()+'_name']
 for i in [444,456,459]:
  current=rows[i]['currentTarget'].replace('{0}',label); proposed=next(x['proposedTarget'] for x in f['findings'] if x.get('closureIndex')==i).replace('{0}',label)
  examples.append({'closureIndex':i,'item':item,'localizedDictionaryLabel':label,'currentAssembled':current,'proposedAssembled':proposed,'inputEvidence':'OtherGameData:2723 deficit domain plus PeekDeficitItem/LocalizeItem IL and compiled caller','decision':'current imposed article or plural mismatch; proposed unit uses label-independent grammar'})
hints=[]
for item,label in labels.items():
 for name in ['message_got_item','message_given_item']:
  template=next(r['currentTarget'] for r in rows if r['key']==name)
  hints.append({'key':name,'itemKey':item,'count':1,'assembled':template.replace('{0}','1').replace('{1}',label),'decision':'action noun, standalone x-count and label; no inflected sentence dependency','countEvidence':'compiled GetItem commands explicitly use 1 for Coffee/Cigarette/Kombucha/Enerjeka/Povistka; count is boxed Int32 in ItemHintView. Other item/count reachability remains unverified.'})
compiled=json.load(open(OUT/'compiled-context.json'))['nodes'];commands={}
for node,n in compiled.items():
 for inst in n['instructions']:
  if inst['opcode']==3 and inst['args'] and re.match(r'GetItem ',inst['args'][0]):commands.setdefault(inst['args'][0],node)
dynamic={'result':'bounded real-domain assembly reviewed','assemblySha256':json.load(open(OUT/'dynamic-consumer-il.json'))['assemblySha256'],'deficitConsumableEnumNames':actual,'deficitDomainAssetSha256':raw['assetSha256'],'localizedNames':labels,'bribeExamples':examples,'itemHintExamples':hints,'compiledGetItemCommandExamples':commands,'enumCandidatesWithoutAcceptedNameKeys':['Pills','Mushroom','Photo','Cockroach'],'limit':'EConsumable enum membership alone does not prove that every enum value reaches the hint or bribe consumer. Six serialized deficit keys are the real bribe domain. Seven accepted localized keys are checked; missing enum-name keys are technical context, not additional accepted translation IDs. Only the explicitly compiled count-1 examples are claimed as traced values. Dictionary-label UI grammar is independent of x-count, but no exhaustive reachable count domain or runtime execution is claimed.'}
for name,obj in [('proposal-regressions.json',{'status':'passed lexical structure preservation; semantic replacement reviewed, not applied','results':results}),('dynamic-assembled-evidence.json',dynamic)]:
 p=OUT/name;assert not p.exists();p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
manifest={'sourcePins':{},'evidencePins':{},'activeFindings':'findings-v2.json','readDecisions':'decisions.jsonl','verdict':'correction-needed; selector-catalog-incomplete; full-first-pass-preserved; no runtime claim'}
for rel in ['Source/localization-inventory-v3/strings.jsonl','Source/localization-inventory-v3/static-text.jsonl','Documentation/glossary-translations/el/layer.json','Source/preserve-exactly-v4.json','Documentation/text-source-acceptance-v1.json','Translations/el/text-checkpoint.json','Translations/el/build_correction_closure.py','Translations/el/correction-cycle-001-selectors.json','Translations/el/correction-cycle-001-closure-manifest.json','Translations/el/correction-cycle-001-closure-review.jsonl','Translations/el/semantic-review-progress.json','Translations/el/correction-cycle-001-applied.json','Translations/el/correction-cycle-001-adjudication.json','Documentation/glossary-research/final-v1/evidence.json','Source/glossary-corpus-v2/runtime-bindings.json','Source/glossary-corpus-v2/report.json']:
 p=ROOT/rel
 if p.exists():manifest['sourcePins'][rel]=D(p)
for p in sorted(OUT.iterdir()):
 if p.is_file() and p.name!='evidence-manifest.json':manifest['evidencePins'][p.name]=D(p)
p=OUT/'evidence-manifest.json';assert not p.exists();p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'findings':len(f['findings']),'proposalRegressions':len(results),'realDeficitDomainAssembledExamples':len(examples),'acceptedItemNames':len(labels),'evidenceManifestSha256':D(p)}))
