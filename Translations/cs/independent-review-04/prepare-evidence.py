import contextlib,hashlib,importlib.util,io,json,re,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
R='Translations/cs/'; P=R+'independent-review-03/'
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def txt(s):return hashlib.sha256(s.encode()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def write(n,d):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def ih(ids):return txt(''.join(s+'\n' for s in ids))
h=read(R+'semantic-correction-cycle-008-handoff.json');c=read(R+'semantic-correction-cycle-008-closure.json');prev=read(c['priorClosurePath']);pins={}
def pin(p,v):assert sha(p)==v,(p,sha(p),v);pins[p]=v
for v in h['evidence'].values():pin(v['path'],v['sha256'])
for k,v in c.items():
 if k.endswith('Path') and k[:-4]+'Sha256' in c:pin(v,c[k[:-4]+'Sha256'])
for p,k in [('Source/localization-inventory-v3/strings.jsonl','sourceInventorySha256'),('Source/localization-inventory-v3/static-text.jsonl','staticInventorySha256'),('Documentation/text-source-acceptance-v1.json','sourceAcceptanceSha256'),('Source/preserve-exactly-v4.json','preserveExactManifestSha256'),('Documentation/glossary-translations/cs/layer.json','glossaryFingerprint'),('Source/glossary-corpus-v2/runtime-bindings.json','runtimeBindingsSha256')]:pin(p,c[k])
b=read(R+'semantic-correction-cycle-008-before.json');pin('Documentation/glossary-research/final-v1/glossary.json',b['sourceGlossarySha256']);pin(h['firstPass']['path'],h['firstPass']['sha256'])
manifest=read(P+'evidence-manifest.json')
for v in manifest['files']:pin(v['path'],v['sha256']);assert (ROOT/v['path']).stat().st_size==v['bytes']
ip=read(P+'input-pins.json')
for p,v in ip['refs'].items():pin(p,v)
pa=read(P+'prior-decision-applicability.json')
for v in pa['refs']:
 if v['same']:pin(v['path'],v['currentSha256'])
ap=Path(pa['managedAssemblyPath']);assert ap.exists() and hashlib.sha256(ap.read_bytes()).hexdigest()==pa['managedAssemblySha256'];pins[str(ap)]=pa['managedAssemblySha256']
files=sorted(p for p in (ROOT/R).iterdir() if re.fullmatch(r'(dialogue|ui|checks)-batch-\d{3}\.json|static-text-draft\.json',p.name)); hashes={str(p.relative_to(ROOT)):sha(str(p.relative_to(ROOT))) for p in files}
assert len(hashes)==411 and txt(''.join(p+'\t'+v+'\n' for p,v in hashes.items()))==c['authoredFileSetSha256']
filedelta=[p for p,v in hashes.items() if v!=ip['authoredFiles'][p]];assert filedelta==[R+'dialogue-batch-192.json']
assert {r['path']:r['sha256'] for r in b['authoredFileHashes']}==ip['authoredFiles'];assert txt(b['authoredBatchPreimageUtf8'])==ip['authoredFiles'][filedelta[0]]
oldbatch=json.loads(b['authoredBatchPreimageUtf8']);newbatch=read(filedelta[0]);unchanged={k:v for k,v in oldbatch.items() if k!='entries'};assert unchanged=={k:v for k,v in newbatch.items() if k!='entries'}
entrydelta=[(x,y) for x,y in zip(oldbatch['entries'],newbatch['entries']) if x!=y];assert len(oldbatch['entries'])==len(newbatch['entries']) and len(entrydelta)==1
source={r['stableId']:r for p in ['Source/localization-inventory-v3/strings.jsonl','Source/localization-inventory-v3/static-text.jsonl'] for r in map(json.loads,(ROOT/p).read_text().splitlines())};current={};owners={};guid={'UI':'0cbd8a7a4f543344bb95659de87f67a5','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'}
for p in files:
 batch=json.loads(p.read_text())
 for e in batch['entries']:
  sid=e.get('stableId') or f"string:{guid[batch['collection']]}:{e['id']}";assert sid not in current;current[sid]=e['target'];owners[sid]=str(p.relative_to(ROOT))
assert len(current)==16538
for r in c['reviewRows']:
 sid=r['stableId'];assert r['source']==source[sid]['source'] and r['target']==current[sid];assert txt(r['source'])==r['sourceSha256'] and txt(r['target'])==r['targetSha256']
for name,v in c['components'].items():assert len(v['ids'])==v['count'] and ih(v['ids'])==v['sha256'];assert set(v['ids'])-set(prev['components'][name]['ids'])<=set(c['correctedIds']) and set(prev['components'][name]['ids'])<=set(v['ids'])
for k in ['closureIds','correctedIds','newDependencyIds','retiredDependencyIds','explicitInvalidatedPriorIds','nextDeltaIds']:
 if k+'Sha256' in c:assert ih(c[k])==c[k+'Sha256']
assert c['closureIds']==prev['closureIds'] and len(c['closureIds'])==1131
assert set(c['nextDeltaIds'])==set(c['correctedIds'])|(set(c['closureIds'])-set(prev['closureIds']))|set(c['explicitInvalidatedPriorIds'])
assert c['newDependencyIds']==c['retiredDependencyIds']==c['explicitInvalidatedPriorIds']==[] and len(c['nextDeltaIds'])==1
oldrows={r['stableId']:r for r in prev['reviewRows']};newrows={r['stableId']:r for r in c['reviewRows']};rowdelta=[s for s in c['closureIds'] if oldrows[s]!=newrows[s]];assert rowdelta==c['nextDeltaIds']
fresh=[json.loads(l) for l in (ROOT/(P+'reviewed-rows.jsonl')).read_text().splitlines()];assert len(fresh)==561 and all(r['fullSourceAndTargetRead'] for r in fresh)
assert {r['stableId'] for r in fresh}==set(prev['nextDeltaIds']); assert len(pa['rows'])==570
retained=[]
for r in fresh+pa['rows']:
 sid=r['stableId']; old=oldrows[sid];assert r['sourceSha256']==old['sourceSha256'] and r['targetSha256']==old['targetSha256']
 if sid not in rowdelta:assert newrows[sid]==old;retained.append({'stableId':sid,'sourceSha256':r['sourceSha256'],'targetSha256':r['targetSha256'],'priorEvidence':P+('reviewed-rows.jsonl' if 'fullSourceAndTargetRead' in r else 'prior-decision-applicability.json'),'priorDecision':r.get('disposition',r.get('priorDecision'))})
assert len(retained)==1130
spec=importlib.util.spec_from_file_location('selector',ROOT/c['selectorPath']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
buffer=io.StringIO()
with contextlib.redirect_stdout(buffer):m.main()
assert sha(R+'semantic-correction-cycle-008-closure.json')==h['evidence']['closure']['sha256']
program=bytes(read('Source/glossary-corpus-v2/runtime-bindings.json')['sharedassets0.assets:2743']['compiledYarnProgram']);assert hashlib.sha256(program).hexdigest()==c['compiledYarnProgramSha256'];nodes=m.compiled_nodes(program);keys={r['key']:r for r in source.values() if r.get('collection')=='Dialogs'}
contexts={}
for name in ['Provocateur_Asking_4_3','Provocateur_Asking_4_3_1','Provocateur_Asking_4_3_1_1']:
 if name not in nodes:continue
 rows=[]
 for i,x in enumerate(nodes[name]):
  item={'index':i,**x};r=keys.get(x['operands'][0]) if x['operands'] else None
  if r and x['opcode'] in (2,4):item.update(stableId=r['stableId'],source=r['source'],target=current[r['stableId']])
  rows.append(item)
 contexts[name]=rows
write('compiled-context.json',{'programSha256':c['compiledYarnProgramSha256'],'nodes':contexts,'limit':'Actual compiled static instruction order; numeric/bool operands omitted by pinned decoder; no gameplay reachability claimed.'})
reg=read(P+'regression-result.json'); ids=c['components']['mandatoryRegressions']['ids'];assert len(ids)==178 and c['catalogHits']==reg['catalogGroupHits'] and set(ids)==set(reg['reusedIds'])|set(reg['freshIds'])
assert all(newrows[s]==oldrows[s] for s in ids)
write('regression-result.json',{'status':'passed on exact unchanged independent review03 decisions','catalogPath':c['regressionCatalogPath'],'catalogSha256':c['regressionCatalogSha256'],'groups':c['catalogHits'],'ids':ids,'idsSha256':ih(ids),'priorResultSha256':sha(P+'regression-result.json'),'freshSemanticRereads':0,'priorFreshDecisions':6,'priorExactRetainedDecisions':172,'decisionRows':[r for r in retained if r['stableId'] in ids],'cycleSpecificCorrectedId':c['nextDeltaIds'][0]})
receipt=read(R+'semantic-correction-cycle-008-full-corpus-receipt.json');assert receipt['rows']==16538 and receipt['structuralResult']==receipt['exactResult']=='passed'
assert {r['path']:r['sha256'] for r in receipt['authoredFiles']}==hashes
for p,k in [('Scripts/validate_locale_corpus.py','validatorSha256'),('Scripts/locale_text_inputs.py','inputLoaderSha256')]:pin(p,receipt[k])
for p,v in receipt['owningValidators'].items():pin('Scripts/'+p,v)
assert receipt['sourceInventorySha256']==c['sourceInventorySha256'] and receipt['staticInventorySha256']==c['staticInventorySha256']
write('whole-corpus-receipt-applicability.json',{'status':'reused exact current receipt','receiptPath':R+'semantic-correction-cycle-008-full-corpus-receipt.json','receiptSha256':sha(R+'semantic-correction-cycle-008-full-corpus-receipt.json'),'rows':16538,'all411AuthoredAndSourceAndValidatorPinsExact':True,'structuralResult':'passed','exactResult':'passed','boundary':receipt['boundary'],'runtime':'not-run'})
# Reproduce the legacy serializer and reconcile every batch020 prior source/target row.
b20=read(R+'dialogue-batch-020.json');before7=read(R+'semantic-correction-cycle-007-before.json');reverse=[r for r in before7['rows'] if r['authoredFile']==R+'dialogue-batch-020.json'];assert len(reverse)==2
for r in reverse:
 e=next(e for e in b20['entries'] if str(e['id'])==r['stableId'].split(':')[-1]);assert e['target']==r['after'];e['target']=r['before']
expanded=json.dumps(b20,ensure_ascii=False,indent=2)+'\n'
def legacy(batch):
 header=json.dumps({k:v for k,v in batch.items() if k!='entries'},ensure_ascii=False,indent=2)[:-2]+',\n  "entries": [\n'
 return header+',\n'.join('    '+json.dumps(e,ensure_ascii=False) for e in batch['entries'])+'\n  ]\n}\n'
legacybytes=legacy(b20);historical=read(R+'semantic-correction-cycle-008-batch020-reconciliation.json');assert txt(expanded)==historical['review03ReverseExpandedSha256'];assert txt(legacybytes)==historical['historicalPinnedPreimageSha256'];assert len(legacybytes.encode())==3839
controls=[]
for n in ['019','021']:
 p=R+'dialogue-batch-'+n+'.json';assert legacy(read(p))==(ROOT/p).read_text();controls.append({'path':p,'sha256':sha(p),'exactByteMatch':True})
fp=[]
for v in historical['firstPassEvidence']:
 pin(v['path'],v['sha256']);fp += [json.loads(l) for l in (ROOT/v['path']).read_text().splitlines() if json.loads(l)['authoredFile']==R+'dialogue-batch-020.json']
assert len(fp)==32
for r,e in zip(fp,b20['entries']):assert r['stableId']==f"string:{guid['Dialogs']}:{e['id']}" and r['source']==source[r['stableId']]['source'] and r['target']==e['target'] and r['targetSha256']==txt(e['target']) and r['sourceSha256']==txt(r['source'])
first=next(i for i,(x,y) in enumerate(zip(expanded.encode(),legacybytes.encode())) if x!=y);assert first==405
write('batch020-reconciliation.json',{'classification':'serialization-only historical reverse mismatch independently reproduced','reversedEdits':2,'expandedSha256':txt(expanded),'legacySha256':txt(legacybytes),'historicalPinnedSha256':historical['historicalPinnedPreimageSha256'],'legacyBytes':3839,'firstDivergenceOffsetZeroBased':first,'all32SourceIdsOrderTargetsReconciled':True,'firstPassEvidence':historical['firstPassEvidence'],'adjacentFormatControls':controls,'limits':'Original persisted preimage unavailable separately. Matching exact historical SHA and unchanged neighboring byte controls establish reconstruction; no historical persisted file inspection claimed; no semantic restart.'})
write('set-reconciliation.json',{'closureCount':1131,'closureSha256':sha(R+'semantic-correction-cycle-008-closure.json'),'closureIdsSha256':c['closureIdsSha256'],'components':{k:{'count':v['count'],'sha256':v['sha256']} for k,v in c['components'].items()},'correctedIds':c['correctedIds'],'newIds':[],'retiredIds':[],'invalidatedIds':[],'deltaIds':c['nextDeltaIds'],'deltaIdsSha256':c['nextDeltaIdsSha256'],'targetDiffIds':rowdelta,'other1130RowsExact':True,'authoredFileDiff':filedelta,'other410FilesExact':True,'selectorByteReproduction':json.loads(buffer.getvalue()),'missing':c['missingAcceptedIds'],'extra':c['extraIds'],'topologyGaps':c['topologyGaps']})
write('prior-decision-applicability.json',{'570Review03PriorRowsVerified':570,'561Review03FreshRowsVerified':561,'changedFreshRowSupersededByNewRead':1,'retainedDecisionRows':retained,'sourceGlossaryCompiledBindingsCatalogManagedAssemblyExact':True,'firstPass16538EvidenceSha256':h['firstPass']['sha256'],'sourcePlaceholdersAndAmbiguities':'Prior poem/rifle/summons dispositions retained unchanged.'})
write('input-pins.json',{'reviewer':'/root/cs_independent_review_04','refs':pins,'authoredFiles':hashes,'authoredFileSetSha256':c['authoredFileSetSha256'],'closureSha256':sha(R+'semantic-correction-cycle-008-closure.json'),'handoffSha256':sha(R+'semantic-correction-cycle-008-handoff.json')})
write('delta-rows.json',{'rows':[dict(newrows[s],key=source[s].get('key'),nodeNames=source[s].get('nodeNames'),authoredPath=owners[s]) for s in c['nextDeltaIds']],'count':1,'deltaIdsSha256':c['nextDeltaIdsSha256']})
print('PASS pins,1131 closure,1 exact delta,178 catalog,16538 receipt,32 historical rows. Compiled context saved.')
