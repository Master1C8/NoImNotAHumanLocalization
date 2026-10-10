import json, hashlib, re, importlib.util
from pathlib import Path
R=Path(__file__).resolve().parents[3];H=R/'Translations/hi';D=Path(__file__).parent
j=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hs=lambda s:hashlib.sha256(s.encode()).hexdigest()
ih=lambda a:hs('\n'.join(a)+'\n')
def write(name,obj):
 p=D/name;assert not p.exists();p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def rows(p):return [json.loads(x) for x in p.read_text().splitlines()]
handoff=j(H/'semantic-cycle-004-author-handoff.json');c=j(H/'semantic-cycle-004-closure.json');old=j(H/'semantic-cycle-003-closure.json');delta=j(H/'semantic-cycle-004-review-delta.json');full=j(H/'semantic-cycle-004-full-corpus.json');prev=j(H/'independent-review-03/final-unchanged-input-pins.json')
for p,digest in handoff['artifacts'].items():assert sha(R/p)==digest,p
changed=handoff['correction']['authoredFile'];exceptions={changed,'Documentation/hi-text-checkpoint.json'}
checks=[{'path':p,'expected':digest,'actual':sha(R/p),'matches':sha(R/p)==digest} for p,digest in prev['pins'].items() if p not in exceptions]
assert len(prev['pins'])==705 and all(x['matches'] for x in checks)
assert all(sha(R/p)==digest for p,digest in prev['additionalVerifiedInputs'].items())
assert prev['pins'][changed]==handoff['correction']['beforeSha256'] and sha(R/changed)==handoff['correction']['afterSha256']
paths=set(prev['pins'])|set(prev['additionalVerifiedInputs'])|set(handoff['artifacts'])
paths.update(str(p.relative_to(R)) for p in (H/'independent-review-03').iterdir() if p.is_file())
paths.update(str(p.relative_to(R)) for p in H.glob('semantic-cycle-004-*') if p.is_file())
paths.update(str(p.relative_to(R)) for n in ['semantic-cycle-004-before-files','semantic-cycle-004-after-files'] for p in (H/n).iterdir() if p.is_file())
write('start-pins.json',{p:sha(R/p) for p in sorted(paths)})
write('unchanged-prior-pin-proof.json',{'previousPinCount':705,'unchangedCount':len(checks),'allowedUpdatedPaths':sorted(exceptions),'checks':checks,'additionalPreviousInputsMatch':True})
source=rows(R/'Source/localization-inventory-v3/strings.jsonl')+rows(R/'Source/localization-inventory-v3/static-text.jsonl');byid={r['stableId']:r for r in source};assert len(byid)==len(source)
lookup={(r['collection'],r['stableId'].rsplit(':',1)[1]):r['stableId'] for r in source if 'collection' in r}
targets={};owners={}
for f in full['authoredFiles']:
 assert sha(R/f['path'])==f['sha256']
 data=j(R/f['path'])
 for e in data['entries']:
  sid=e.get('stableId') or lookup[data['collection'],str(e['id'])]
  assert sid not in targets;targets[sid]=e['target'];owners[sid]=f['path']
ids=[r['stableId'] for r in source if r['stableId'] in targets];accepted=[byid[x] for x in ids]
assert len(ids)==len(set(ids))==len(targets)==16538 and ih(ids)==c['sourceOrderIdListSha256LfFinalNewline']
assert sha(R/'Source/localization-inventory-v3/strings.jsonl')==full['sourceInventorySha256']==c['sourceInventorySha256']
assert sha(R/'Source/localization-inventory-v3/static-text.jsonl')==full['staticInventorySha256']==c['staticInventorySha256']
assert sha(R/'Scripts/validate_locale_corpus.py')==full['validatorSha256']
assert sha(R/'Scripts/locale_text_inputs.py')==full['inputLoaderSha256']
assert all(sha(R/'Scripts'/p)==digest for p,digest in full['owningValidators'].items())
assert full['structuralResult']==full['exactResult']=='passed' and full['rows']==16538
write('whole-corpus-receipt-applicability.json',{'receiptPath':'Translations/hi/semantic-cycle-004-full-corpus.json','receiptSha256':sha(H/'semantic-cycle-004-full-corpus.json'),'rows':16538,'authoredFiles':len(full['authoredFiles']),'allExactInputsAndCodeMatch':True,'freshExecutionRequired':False,'boundary':full['boundary'],'runtime':'not-run'})
spec=importlib.util.spec_from_file_location('context',H/'build-semantic-cycle-002-closure.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);nodes=m.runtime_nodes(m.helper().fields)
sid=handoff['correction']['stableId'];key=byid[sid]['key'];node_names={n for n,ins in nodes.items() if any(key in q['strings'] for q in ins)};assert node_names=={'Mushroom_end_2'}
scene_keys={v for n in node_names for q in nodes[n] for v in q['strings'] if v.startswith('line:')}
scene={r['stableId'] for r in accepted if r.get('key') in scene_keys};assert len(scene)==5 and scene==set(c['currentChangedSceneIds'])
broad=[r['stableId'] for r in accepted if re.search(r'(?i)\bмицели\w*\b',r['source'])]
normal=[r['stableId'] for r in accepted if re.search(c['myceliumInflectionPattern'],r['source'])]
assert len(normal)==22 and normal==broad==c['myceliumAcceptedSourceIds']
catalog=j(R/c['catalogPath']);required=set()
for group in catalog['groups']:
 assert len(group['ids'])==group['count'] and ih(group['ids'])==group['idsSha256'];required.update(group['ids'])
assert len(required)==4805
components={n:set(v) for n,v in old['components'].items()}
components['changed'].add(sid);components['sceneContext'].update(scene);components['repetition'].update(r['stableId'] for r in accepted if r['source']==byid[sid]['source']);components['glossaryReferent'].update(normal);components['mandatoryRegression'].update(required)
for n,members in components.items():assert [x for x in ids if x in members]==c['components'][n] and ih(c['components'][n])==c['componentIdListSha256LfFinalNewline'][n]
current=set().union(*components.values());prior={r['stableId'] for r in old['reviewRows']};assert len(prior)==5207 and len(current)==5216
invalid=(scene|{r['stableId'] for r in accepted if r['source']==byid[sid]['source']})&prior;assert not invalid
new=current-prior;exact_delta=[x for x in ids if x in ({sid}|new|invalid)]
assert exact_delta==delta['deltaIds'] and len(exact_delta)==9 and not prior-current and ih(exact_delta)==delta['deltaIdListSha256LfFinalNewline']
current_rows={r['stableId']:r for r in c['reviewRows']};assert len(current_rows)==5216
for ss,row in current_rows.items():assert row['source']==byid[ss]['source'] and row['target']==targets[ss] and row['sourceSha256']==hs(row['source']) and row['targetSha256']==hs(row['target'])
assert ih([x for x in ids if x in current])==c['closureIdListSha256LfFinalNewline']
previous=rows(H/'independent-review-03/per-id-current-closure-decisions.jsonl');assert len(previous)==len({r['stableId'] for r in previous})==5207 and {r['stableId'] for r in previous}==prior
for row in previous:
 ss=row['stableId'];assert row['sourceSha256']==hs(byid[ss]['source']) and row['currentTargetSha256']==hs(targets[ss]);assert row['glossarySha256']==c['glossaryLayerSha256'] and row['compiledBindingSha256']==c['compiledRuntimeBindingsSha256'];assert not row['findingIds']
mandatory=rows(H/'independent-review-03/mandatory-catalog-per-id-decisions.jsonl');assert len(mandatory)==4805 and {r['stableId'] for r in mandatory}==required
prevmap={r['stableId']:r for r in previous}
for row in mandatory:
 ss=row['stableId'];assert all(row[k]==prevmap[ss][k] for k in ('sourceSha256','currentTargetSha256','glossarySha256','compiledBindingSha256','result','findingIds'))
supp=rows(H/'independent-review-03/outside-delta-six-independent-decisions.jsonl');assert len(supp)==6
for row in supp:
 ss=row['stableId'];assert row['source']==byid[ss]['source'] and row['target']==targets[ss] and row['sourceSha256']==hs(byid[ss]['source']) and row['currentTargetSha256']==hs(targets[ss]);assert row['glossarySha256']==c['glossaryLayerSha256'] and row['compiledBindingSha256']==c['compiledRuntimeBindingsSha256']
assert {r['stableId'] for r in supp}==set(normal)-prior
renewed=[x for x in ids if x in scene&{r['stableId'] for r in supp}];assert len(renewed)==2
write('set-and-prior-applicability-proof.json',{'accepted':16538,'previousClosure':5207,'currentClosure':5216,'closureIdHashLfFinalNewline':c['closureIdListSha256LfFinalNewline'],'exactDelta':exact_delta,'deltaIdHashLfFinalNewline':ih(exact_delta),'corrected':1,'newDependencies':len(new),'invalidated':0,'retired':0,'myceliumActualForms':sorted(set(w for r in accepted for w in re.findall(r'(?i)\bмицели\w*\b',r['source']))),'myceliumNormalPredicateIds':normal,'myceliumSourceIdHashLfFinalNewline':ih(normal),'all22BroadReconciled':True,'componentsExactlyReproduced':True,'compiledChangedNode':sorted(node_names),'compiledChangedSceneIds':[x for x in ids if x in scene],'priorClosureDecisionsExactCurrent':5207,'mandatoryExactCurrentIndependent':4805,'supplementalExactUnitDecisions':6,'supplementalRenewedContextIds':renewed})
def pair(ss):return {'stableId':ss,'key':byid[ss].get('key'),'source':byid[ss]['source'],'target':targets[ss],'sourceSha256':hs(byid[ss]['source']),'targetSha256':hs(targets[ss]),'nodeNames':byid[ss].get('nodeNames',[]),'authoredPath':owners[ss]}
write('delta-pairs.json',[pair(x) for x in exact_delta]);write('all22-mycelium-pairs.json',[pair(x) for x in normal])
context_names={n for ss in exact_delta for n in byid[ss].get('nodeNames',[])}|node_names
contexts={n:[{**q,'pairs':[pair(r['stableId']) for v in q['strings'] if v.startswith('line:') for r in accepted if r.get('key')==v]} for q in nodes[n]] for n in sorted(context_names)}
write('actual-compiled-context.json',contexts)
before=j(H/'semantic-cycle-004-before-files'/Path(changed).name);after=j(R/changed);expected=j(H/'semantic-cycle-004-after-files'/Path(changed).name)
assert after==expected
assert {k for k in before if before[k]!=after[k]}=={'entries'}
bm={str(e['id']):e for e in before['entries']};am={str(e['id']):e for e in after['entries']};eid=sid.rsplit(':',1)[1]
assert bm.keys()==am.keys() and {k for k in bm if bm[k]!=am[k]}=={eid}
assert {k for k in bm[eid] if bm[eid][k]!=am[eid][k]}=={'target'}
assert bm[eid]['target']==handoff['correction']['before'] and am[eid]['target']==handoff['correction']['after']
write('one-full-unit-correction-proof.json',{'stableId':sid,'key':key,'source':byid[sid]['source'],'before':bm[eid]['target'],'after':am[eid]['target'],'oneTargetFieldOnly':True,'allOtherAcceptedTargetsUnchanged':16537,'beforeFileSha256':sha(H/'semantic-cycle-004-before-files'/Path(changed).name),'afterFileSha256':sha(R/changed),'historicalSidecarSha256':sha(R/changed.replace('.json','.validation.json'))})
print('Verified exact9 delta,5216 closure,5207 applicable prior,4805 mandatory,22 mycelium; captured',len(contexts),'compiled nodes')
