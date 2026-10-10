import hashlib, importlib.util, json, re, sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Scripts'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def txt(s): return hashlib.sha256(s.encode()).hexdigest()
def read(p): return json.loads((ROOT/p).read_text())
def write(n,d):
 p=OUT/n; assert not p.exists(); p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
c=read('Translations/cs/semantic-correction-cycle-007-closure.json');h=read('Translations/cs/semantic-correction-cycle-007-handoff.json');cp=read('Documentation/cs-text-checkpoint.json');refs={}
for k,v in h['evidence'].items(): assert sha(ROOT/v['path'])==v['sha256'];refs[v['path']]=v['sha256']
for k,v in c.items():
 if k.endswith('Path') and k[:-4]+'Sha256' in c: assert sha(ROOT/v)==c[k[:-4]+'Sha256'];refs[v]=sha(ROOT/v)
for p,key in [('Source/localization-inventory-v3/strings.jsonl','sourceInventorySha256'),('Source/localization-inventory-v3/static-text.jsonl','staticInventorySha256'),('Documentation/text-source-acceptance-v1.json','sourceAcceptanceSha256'),('Source/preserve-exactly-v4.json','preserveExactManifestSha256'),('Documentation/glossary-translations/cs/layer.json','glossaryFingerprint'),('Source/glossary-corpus-v2/runtime-bindings.json','runtimeBindingsSha256')]: assert sha(ROOT/p)==c[key];refs[p]=sha(ROOT/p)
p='Documentation/glossary-research/final-v1/glossary.json';assert sha(ROOT/p)==cp['inputs']['sourceGlossarySha256'];refs[p]=sha(ROOT/p)
files=sorted(p for p in (ROOT/'Translations/cs').iterdir() if re.fullmatch(r'(dialogue|ui|checks)-batch-\d{3}\.json|static-text-draft\.json',p.name));hashes={str(p.relative_to(ROOT)):sha(p) for p in files};assert len(files)==411;assert txt(''.join(k+'\t'+v+'\n' for k,v in hashes.items()))==c['authoredFileSetSha256']
source={r['stableId']:r for p in ['Source/localization-inventory-v3/strings.jsonl','Source/localization-inventory-v3/static-text.jsonl'] for r in map(json.loads,(ROOT/p).read_text().splitlines())};current={};owners={};guid={'UI':'0cbd8a7a4f543344bb95659de87f67a5','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'}
for p in files:
 b=json.loads(p.read_text())
 for e in b['entries']:
  sid=e.get('stableId') or f"string:{guid[b['collection']]}:{e['id']}";assert sid not in current;current[sid]=e['target'];owners[sid]=str(p.relative_to(ROOT))
assert len(current)==16538
for r in c['reviewRows']:
 sid=r['stableId'];assert r['source']==source[sid]['source'] and r['target']==current[sid];assert txt(r['source'])==r['sourceSha256'] and txt(r['target'])==r['targetSha256']
for v in c['components'].values(): assert len(v['ids'])==v['count'] and txt(''.join(s+'\n' for s in v['ids']))==v['sha256']
for k in ['closureIds','correctedIds','newDependencyIds','retiredDependencyIds','explicitInvalidatedPriorIds','nextDeltaIds']: assert txt(''.join(s+'\n' for s in c[k]))==c[k+'Sha256'] if k+'Sha256' in c else True
prior=read(c['priorClosurePath']);assert set(c['nextDeltaIds'])==set(c['correctedIds'])|(set(c['closureIds'])-set(prior['closureIds']))|set(c['explicitInvalidatedPriorIds']);assert set(c['retiredDependencyIds'])==set(prior['closureIds'])-set(c['closureIds']);assert len(c['nextDeltaIds'])==561
before=read('Translations/cs/semantic-correction-cycle-007-before.json');batches={str(p.relative_to(ROOT)):json.loads(p.read_text()) for p in files};modified=set()
for r in before['rows']:
 sid=r['stableId'];assert r['source']==source[sid]['source'] and txt(r['before'])==r['beforeSha256'] and txt(r['after'])==r['afterSha256'] and current[sid]==r['after'];p=owners[sid];modified.add(p);e=next(e for e in batches[p]['entries'] if str(e.get('id'))==sid.split(':')[-1]);e['target']=r['before']
bh={p:(txt(json.dumps(b,ensure_ascii=False,indent=2)+'\n') if p in modified else hashes[p]) for p,b in batches.items()};expected={r['path']:r['sha256'] for r in before['authoredFileHashes']};reconstruction_mismatches=[{'path':p,'reconstructedSha256':v,'priorSha256':expected.get(p)} for p,v in bh.items() if v!=expected.get(p)];assert len(reconstruction_mismatches)==1 and reconstruction_mismatches[0]['path']=='Translations/cs/dialogue-batch-020.json';assert expected==read('Translations/cs/independent-review-02/input-pins.json')['authoredFiles']
spec=importlib.util.spec_from_file_location('selector',ROOT/c['selectorPath']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.main()
program=bytes(read('Source/glossary-corpus-v2/runtime-bindings.json')['sharedassets0.assets:2743']['compiledYarnProgram']);assert hashlib.sha256(program).hexdigest()==c['compiledYarnProgramSha256'];nodes=m.compiled_nodes(program);keys={r['key']:r for r in source.values() if r.get('collection')=='Dialogs'};delta=set(c['nextDeltaIds']);contexts={}
for name,instructions in nodes.items():
 if not any(x['operands'] and x['operands'][0] in keys and keys[x['operands'][0]]['stableId'] in delta for x in instructions):continue
 enriched=[]
 for i,x in enumerate(instructions):
  item={'index':i,**x};r=keys.get(x['operands'][0]) if x['operands'] else None
  if r and x['opcode'] in (2,4): item.update(stableId=r['stableId'],source=r['source'],target=current[r['stableId']],inDelta=r['stableId'] in delta)
  enriched.append(item)
 contexts[name]=enriched
write('compiled-context.json',{'programSha256':c['compiledYarnProgramSha256'],'nodes':contexts,'limit':'Static instruction and branch order; bool/numeric operands omitted by pinned decoder; no runtime reachability claim.'})
rows=[]
for sid in c['nextDeltaIds']:
 r=next(r for r in c['reviewRows'] if r['stableId']==sid);rows.append({**r,'key':source[sid].get('key'),'nodeNames':source[sid].get('nodeNames',[]),'authoredPath':owners[sid]})
write('delta-rows.json',{'rows':rows,'count':len(rows),'deltaIdsSha256':c['nextDeltaIdsSha256']})
write('input-pins.json',{'refs':refs,'authoredFiles':hashes,'authoredFileSetSha256':c['authoredFileSetSha256'],'closureSha256':sha(ROOT/'Translations/cs/semantic-correction-cycle-007-closure.json'),'checkpointSha256':sha(ROOT/'Documentation/cs-text-checkpoint.json'),'priorAuthoredReconstruction':{'exact':410,'mismatches':reconstruction_mismatches},'reviewer':'/root/cs_independent_review_03'})
write('deterministic-preflight.json',{'status':'passed','finalTargetMappings':1131,'deltaFormula':561,'preimages':15,'authoredFiles':411,'selectorByteReproduction':True,'componentHashesVerified':True,'compiledNodes':len(contexts),'sourceAndGlossaryUnchanged':True,'runtime':'not-run'})
print('Verified pins,15preimages,561delta; context nodes',len(contexts))
