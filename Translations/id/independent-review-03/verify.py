"""Read-only pin, delta and prior-independent-decision reconciliation."""
import hashlib, importlib.util, json, subprocess
from pathlib import Path

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
C = 'Translations/id/semantic-correction-cycle-03/'
def raw(p): return (R / p).read_bytes()
def load(p): return json.loads(raw(p))
def rows(p): return list(map(json.loads, raw(p).decode().splitlines()))
def sha(b): return hashlib.sha256(b).hexdigest()
def save(name, value):
    p = O / name
    data=(json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()
    if p.exists():
        assert p.read_bytes()==data, p
    else:
        p.write_bytes(data)
checks = []
def check(path, pin, owner):
    actual = sha(raw(path)); assert actual == pin, (path, pin, actual)
    checks.append({'path':path, 'sha256':pin, 'owner':owner})
def walk(j, owner):
    if isinstance(j, dict):
        if 'path' in j and 'sha256' in j: check(j['path'], j['sha256'], owner)
        for v in j.values(): walk(v, owner)
    elif isinstance(j, list):
        for v in j: walk(v, owner)

handoff = load(C+'independent-delta-handoff.json')
walk(handoff, C+'independent-delta-handoff.json')
manifest = load(C+'artifact-manifest.json')
walk(manifest, C+'artifact-manifest.json')
for p in [C+'component-manifest.json',C+'delta-manifest.json',C+'mandatory-regression-catalog.json',
          'Translations/id/independent-review-02/evidence-manifest.json']:
    walk(load(p),p)
prior_manifest = load('Translations/id/semantic-correction-cycle-02/artifact-manifest.json')
check('Translations/id/semantic-correction-cycle-02/artifact-manifest.json',manifest['previousCycleArtifactManifestSha256'],'current manifest')
for group in ['sourceAndGlossary','manuals','authoredMapsAndSelectorRecipe']:
    walk(prior_manifest[group], 'prior manifest '+group)
prior_closure_manifest = load('Translations/id/semantic-correction-cycle-02/component-manifest.json')
walk(prior_closure_manifest, 'prior component manifest')
for p in ['Translations/id/independent-review-01/evidence-manifest.json']:
    if (R/p).exists(): walk(load(p),p)

source = {r['stableId']:r for name in ['strings','static-text']
          for r in rows('Source/localization-inventory-v3/'+name+'.jsonl')}
rules = load('Source/preserve-exactly-v4.json')
order = [r['stableId'] for r in rules['tableRows']+rules['staticRows']]
valid = set(order); assert len(valid)==len(order)==16538
guids={'Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'}
def batchmap(p):
    j=load(p)
    return {(e.get('stableId') or 'string:'+guids[j['collection']]+':'+str(e['id'])):e['target'] for e in j['entries']}
targets={}; owners={}; before={}; replacements={r['path']:r for r in load(C+'application-plan.json')['files']}
for entry in manifest['targetInputs']:
    p=entry['path']; current=batchmap(p)
    assert not targets.keys() & current.keys()
    targets.update(current); owners.update({sid:p for sid in current})
    prior=next(x for x in prior_manifest['targetInputs'] if x['path']==p)
    if p in replacements:
        rep=replacements[p];check(rep['beforeBackup'],rep['beforeBackupSha256'],'before snapshot')
        assert rep['beforeSha256']==rep['beforeBackupSha256']==prior['sha256']
        assert rep['afterSha256']==entry['sha256']
        before.update(batchmap(rep['beforeBackup']))
    else:
        assert prior['sha256']==entry['sha256'];before.update(current)
assert targets.keys()==before.keys()==valid
changed={sid for sid in order if targets[sid]!=before[sid]}
adj=load(C+'adjudication.json')['rows']
assert changed=={r['stableId'] for r in adj}
assert all(before[r['stableId']]==r['before'] and targets[r['stableId']]==r['after'] for r in adj)
def ids(p): return set(raw(p).decode().splitlines())
previous=ids('Translations/id/semantic-correction-cycle-02/closure.ids.txt')
closure=ids(C+'closure.ids.txt');new=closure-previous;retired=previous-closure
invalidated=ids(C+'invalidated-prior.ids.txt');delta=changed|new|invalidated
assert new==ids(C+'new-dependencies.ids.txt') and retired==ids(C+'retired-dependencies.ids.txt')
assert delta==ids(C+'delta-review.ids.txt') and changed==ids(C+'changed.ids.txt')
delta_rows=rows(C+'delta-review-rows.jsonl');closure_rows=rows(C+'closure-review-rows.jsonl')
assert {r['stableId'] for r in delta_rows}==delta
for r in closure_rows:
    assert r['source']==source[r['stableId']]['source'] and r['target']==targets[r['stableId']]
    assert r['targetFile']==owners[r['stableId']]
    assert r['targetFileSha256']==sha(raw(r['targetFile']))

spec=importlib.util.spec_from_file_location('ctx', R/'Translations/id/independent-review-01/compiled_context.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);nodes,programsha=m.load()
check('Source/glossary-corpus-v2/runtime-bindings.json',sha(raw('Source/glossary-corpus-v2/runtime-bindings.json')),'current compiled input')
saved=load('Translations/id/independent-review-02/selector-omission-context.json')
assert saved['compiledProgramSha256']==programsha
assert all(nodes[n]==ins for n,ins in saved['nodes'].items())
prior_nodes=load('Translations/id/independent-review-02/compiled-delta-nodes.json')
assert prior_nodes['programSha256']==programsha
for n,blob in prior_nodes['nodes'].items():
    assert nodes[n]==[{k:i[k] for k in ['index','opcode','operands']} for i in blob['instructions']]
needed={n for r in delta_rows for n in r['nodeNames']}
needed.update(['Daughter_Ears_DontShoot','Bald_Photo','Bald_Photo_Gun','Daughter_Asking_3_1','Daughter_Asking_3_2'])
bykey={r['key']:r for r in source.values() if r.get('collection')=='Dialogs'}
context={}
correspondence=[]
for n in sorted(needed):
    context[n]=[]
    for ins in nodes[n]:
        i=dict(ins);a=ins['operands']
        if ins['opcode'] in (2,4) and a[0] in bykey:
            r=bykey[a[0]];i.update(stableId=r['stableId'],source=r['source'],target=targets.get(r['stableId']))
        context[n].append(i)
for r in delta_rows:
    matches=[{'node':n,**i} for n in r['nodeNames'] for i in nodes[n]
             if i['opcode'] in (2,4) and i['operands'][0]==r['key']]
    assert matches or r['collection']=='UI'
    correspondence.append({'stableId':r['stableId'],'sourceOrderIndex':r['sourceOrderIndex'],'occurrences':matches})
save('compiled-context.json',{'programSha256':programsha,'nodes':context,'deltaCorrespondence':correspondence,
                            'limit':'Wire-decoded original compiled instructions; no VM or reachability proof.'})

# Reconcile exact independent evidence, never substitute author semantic-pass entries.
prior_decisions={r['stableId']:r for r in rows('Translations/id/independent-review-02/reused-decisions.jsonl')}
prior_decisions.update({r['stableId']:r for r in rows('Translations/id/independent-review-02/coverage.jsonl')})
assert len(prior_decisions)==1433
prior_review_rows={r['stableId']:r for r in rows('Translations/id/semantic-correction-cycle-02/closure-review-rows.jsonl')}
reuse=[]
for sid in order:
    if sid not in closure-delta:continue
    r=prior_review_rows[sid];d=prior_decisions[sid]
    assert r['source']==source[sid]['source'] and r['target']==targets[sid]
    assert d.get('status',d.get('priorDecision'))=='no-objective-correction-found'
    if 'sourceSha256' in d:assert d['sourceSha256']==sha(r['source'].encode())
    if 'targetSha256' in d:assert d['targetSha256']==sha(targets[sid].encode())
    reuse.append({'stableId':sid,'sourceOrderIndex':order.index(sid)+1,
                 'sourceSha256':sha(r['source'].encode()),'targetSha256':sha(targets[sid].encode()),
                 'mode':'exact applicable prior independent decision',
                 'decisionEvidence':'Translations/id/independent-review-02/coverage.jsonl' if 'deltaIndex' in d else 'Translations/id/independent-review-02/reused-decisions.jsonl',
                 'status':'no-objective-correction-found',
                 'contextApplicability':'same original source, glossary and decoded compiled program; unchanged full target unit; changed introductions reviewed separately'})
save('reused-decisions.json',reuse)
catalog=load(C+'mandatory-regression-catalog.json');groups={k:ids(v['path']) for k,v in catalog['groups'].items()}
mandatory=set().union(*groups.values());assert len(mandatory)==845
oldgroups={k:ids(v['path']) for k,v in prior_closure_manifest['regressionGroups'].items()};oldmandatory=set().union(*oldgroups.values())
assert len(oldmandatory)==836 and len(mandatory-oldmandatory)==9 and not oldmandatory-mandatory
assert mandatory<=closure and len(mandatory&delta)==10
regressions=[]
for sid in order:
    if sid not in mandatory:continue
    regressions.append({'stableId':sid,'sourceOrderIndex':order.index(sid)+1,
                        'groups':[k for k,v in groups.items() if sid in v],
                        'sourceSha256':sha(source[sid]['source'].encode()),'targetSha256':sha(targets[sid].encode()),
                        'mode':'current independent full-unit delta read' if sid in delta else 'exact applicable prior independent decision',
                        'status':'no-objective-correction-found'})
save('mandatory-regression-decisions.json',regressions)
phone=load('Translations/id/semantic-correction-cycle-02/source-only-context-manifest.json')
check(phone['contextRowsPath'],phone['contextRowsSha256'],'source-only phone context')
phonerows=rows(phone['contextRowsPath']);assert len(phonerows)==60
inventory=rows(phone['selector']['inventoryPath'])
selected=[r for r in inventory if r.get('collection')=='NotCharacterDialogs' and (r.get('key') or '').startswith('line:phone_daughtersfriend_')]
assert phonerows==[{k:r[k] for k in ['stableId','collection','key','nodeNames','source','sourceSha256']} for r in selected]
assert not valid & {r['stableId'] for r in phonerows}
retiredrows=rows(C+'retired-dependencies.jsonl');assert {r['stableId'] for r in retiredrows}==retired
assert all(before[sid]==targets[sid] for sid in retired)
result=subprocess.run([str(R/'.venv/bin/python'),'Translations/id/closure-selector-recipe-v3.py','--verify'],cwd=R,capture_output=True,text=True,check=True)
selector=json.loads(result.stdout)
save('verification-initial.json',{'hashChecks':len(checks),'hashMismatches':[], 'pins':checks,
 'fullBeforeCurrentUnits':len(valid),'actualChangedStableIds':len(changed), 'unintendedChanges':0,
 'selector':selector,'arithmetic':{'previous':len(previous),'current':len(closure),'corrected':len(changed),'new':len(new),'invalidated':len(invalidated),'retired':len(retired),'delta':len(delta),'correctedNewOverlap':len(changed&new)},
 'reusedClosureDecisions':len(reuse),'mandatory':{'uniqueIds':len(mandatory),'currentDeltaReads':len(mandatory&delta),'reusedExactPriorDecisions':len(mandatory-delta),'newUniqueIds':9},
 'sourceOnlyPhoneContext':{'rows':len(phonerows),'acceptedOverlap':0,'priorIndependentReview':'Translations/id/independent-review-02/review.json','mode':'exact unchanged source-only context applicability'},
 'retired':{'count':len(retired),'valuesUnchanged':True,'recordedFormerComponentsAndReasons':True},
 'compiledProgramSha256':programsha,'checksBoundary':'Source and authored file identity, per-unit before/current equality, deterministic dependency selection, prior-independent-decision and static instruction correspondence; does not execute consumers.'})
print(json.dumps({'hashChecks':len(checks),'selector':selector,'reused':len(reuse),'mandatoryDelta':len(mandatory&delta),'mandatoryReuse':len(mandatory-delta)}))
