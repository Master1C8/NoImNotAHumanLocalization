import hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'Scripts'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def txt(s):return hashlib.sha256(s.encode()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def write(n,d):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
c=read('Translations/cs/semantic-correction-cycle-006-closure.json');h=read('Translations/cs/semantic-correction-cycle-006-handoff.json')
refs={'Translations/cs/semantic-correction-cycle-006-handoff.json':sha(ROOT/'Translations/cs/semantic-correction-cycle-006-handoff.json')}
for k,v in c.items():
 if k.endswith('Path') and k[:-4]+'Sha256' in c:
  assert sha(ROOT/v)==c[k[:-4]+'Sha256'],k
  refs[v]=sha(ROOT/v)
for p,pin in [('Source/localization-inventory-v3/strings.jsonl','sourceInventorySha256'),('Source/localization-inventory-v3/static-text.jsonl','staticInventorySha256'),('Documentation/text-source-acceptance-v1.json','sourceAcceptanceSha256'),('Source/preserve-exactly-v4.json','preserveExactManifestSha256'),('Documentation/glossary-translations/cs/layer.json','glossaryFingerprint'),('Source/glossary-corpus-v2/runtime-bindings.json','runtimeBindingsSha256')]:
 assert sha(ROOT/p)==c[pin];refs[p]=sha(ROOT/p)
for key in ['firstPassFrozen','originalIndependentReview','reconciliation','boundedRemedialRead']:
 v=h[key];assert sha(ROOT/v['path'])==v['sha256'];refs[v['path']]=v['sha256']
cp=read('Documentation/cs-text-checkpoint.json');refs['Documentation/cs-text-checkpoint.json']=sha(ROOT/'Documentation/cs-text-checkpoint.json')
assert sha(ROOT/'Documentation/glossary-research/final-v1/glossary.json')==cp['inputs']['sourceGlossarySha256'];refs['Documentation/glossary-research/final-v1/glossary.json']=cp['inputs']['sourceGlossarySha256']
files=sorted(p for p in (ROOT/'Translations/cs').iterdir() if re.fullmatch(r'(dialogue|ui|checks)-batch-\d{3}\.json|static-text-draft\.json',p.name));hashes={str(p.relative_to(ROOT)):sha(p) for p in files}
assert txt(''.join(k+'\t'+v+'\n' for k,v in hashes.items()))==c['authoredFileSetSha256']
source={r['stableId']:r for p in ['Source/localization-inventory-v3/strings.jsonl','Source/localization-inventory-v3/static-text.jsonl'] for r in map(json.loads,(ROOT/p).read_text().splitlines())}
current={};owners={};guid={'UI':'0cbd8a7a4f543344bb95659de87f67a5','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'}
for p in files:
 b=json.loads(p.read_text())
 for e in b['entries']:
  sid=e.get('stableId') or f"string:{guid[b['collection']]}:{e['id']}";assert sid not in current;current[sid]=e['target'];owners[sid]=str(p.relative_to(ROOT))
assert len(current)==16538
for r in c['reviewRows']:
 sid=r['stableId'];assert r['source']==source[sid]['source'] and r['target']==current[sid];assert txt(r['source'])==r['sourceSha256'] and txt(r['target'])==r['targetSha256']
for component in c['components'].values():assert len(component['ids'])==component['count'] and txt(''.join(s+'\n' for s in component['ids']))==component['sha256']
for key in ['closureIds','correctedIds','newDependencyIds','retiredDependencyIds','nextDeltaIds']:assert txt(''.join(s+'\n' for s in c[key]))==c[key+'Sha256']
assert txt(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in c['reviewRows']))==c['reviewRowsSha256']
prior=read(c['priorClosurePath']);assert set(c['nextDeltaIds'])==set(c['correctedIds'])|(set(c['closureIds'])-set(prior['closureIds']))|set(c['explicitInvalidatedPriorIds'])
assert set(c['retiredDependencyIds'])==set(prior['closureIds'])-set(c['closureIds'])
# Undo each application in reverse to verify every intermediate authored version and prior independent pins.
reconstruction=[];modified_paths=set();batches={str(p.relative_to(ROOT)):json.loads(p.read_text()) for p in files}
for item in reversed(h['authorCorrectionApplications']):
 a=read(item['application']);before=read(item['before']);assert sha(ROOT/item['application'])==item['applicationSha256'] and sha(ROOT/item['before'])==item['beforeSha256']
 refs[item['application']]=item['applicationSha256'];refs[item['before']]=item['beforeSha256']
 for r in before['rows']:
  assert txt(r['before'])==r['beforeSha256'] and txt(r['after'])==r['afterSha256']
  modified_paths.add(owners[r['stableId']]);b=batches[owners[r['stableId']]];e=next(e for e in b['entries'] if str(e.get('id'))==r['stableId'].split(':')[-1]);assert e['target']==r['after'];e['target']=r['before']
 bh={p:(txt(json.dumps(b,ensure_ascii=False,indent=2)+'\n') if p in modified_paths else hashes[p]) for p,b in batches.items()};assert bh==before['allAuthoredFileHashesBefore'] if 'allAuthoredFileHashesBefore' in before else txt(''.join(k+'\t'+v+'\n' for k,v in bh.items()))==before['authoredFileSetSha256Before']
 reconstruction.append({'cycle':item['cycle'],'beforeVerified':True,'files':len(bh)})
old=read('Translations/cs/independent-review-01/input-pins.json');assert bh==old['authoredFiles'];assert txt(''.join(k+'\t'+v+'\n' for k,v in bh.items()))==read(h['originalIndependentReview']['path'])['authoredFileSetSha256']
# Read all prior references except the old changed authored/closure recipe records; classify exact pin reuse.
prior_refs=[]
for p,pin in old['refs'].items():prior_refs.append({'path':p,'priorSha256':pin,'currentSha256':sha(ROOT/p),'same':sha(ROOT/p)==pin})
from preserve_exact import check_value
manifest=read('Source/preserve-exactly-v4.json');rules={r['stableId']:r for r in manifest['tableRows']+manifest['staticRows']};assert set(rules)==set(current)
for sid,v in current.items():check_value(rules[sid],v)
spec=importlib.util.spec_from_file_location('s',ROOT/c['selectorPath']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.main()
program=bytes(read('Source/glossary-corpus-v2/runtime-bindings.json')['sharedassets0.assets:2743']['compiledYarnProgram']);assert hashlib.sha256(program).hexdigest()==c['compiledYarnProgramSha256'];nodes=m.compiled_nodes(program)
keys={r['key']:r for r in source.values() if r.get('collection')=='Dialogs'};delta=set(c['nextDeltaIds']);contexts={}
for name,instructions in nodes.items():
 if not any(x['operands'] and x['operands'][0] in keys and keys[x['operands'][0]]['stableId'] in delta for x in instructions):continue
 enriched=[]
 for i,x in enumerate(instructions):
  item={'index':i,**x};r=keys.get(x['operands'][0]) if x['operands'] else None
  if r and x['opcode'] in (2,4):item.update(stableId=r['stableId'],source=r['source'],target=current[r['stableId']],inDelta=r['stableId'] in delta)
  enriched.append(item)
 contexts[name]=enriched
write('compiled-context.json',{'programSha256':c['compiledYarnProgramSha256'],'nodes':contexts,'limit':'Static instruction and branch order, not reachability. String operands decoded; bool/numeric operands omitted by pinned recipe.'})
write('input-pins.json',{'refs':refs,'authoredFiles':hashes,'authoredFileSetSha256':c['authoredFileSetSha256'],'priorReferenceApplicability':prior_refs,'intermediateReconstruction':reconstruction,'closureSha256':sha(ROOT/h['currentClosure']['path'])})
rows=[]
for sid in c['nextDeltaIds']:
 r=next(r for r in c['reviewRows'] if r['stableId']==sid);rows.append({**r,'key':source[sid].get('key'),'nodeNames':source[sid].get('nodeNames',[]),'authoredPath':owners[sid]})
write('delta-rows.json',{'rows':rows,'count':len(rows),'deltaIdsSha256':c['nextDeltaIdsSha256']})
write('deterministic-preflight.json',{'result':'passed','preserveExactlyRows':len(current),'deltaRows':len(rows),'closureRows':len(c['reviewRows']),'componentHashesVerified':True,'selectorByteReproduction':True,'deltaFormulaVerified':True,'intermediateAuthoredVersionsVerified':True,'priorIndependentAuthoredReconstructionVerified':True,'contextNodes':len(contexts),'runtime':'not run'})
print('Prepared',len(rows),'delta rows;',len(contexts),'compiled nodes; hashes/formula/preflight verified')
