"""Read-only independent correction003 accounting; writes only this review directory."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
L = ROOT / 'Translations/ro'
C = L / 'correction-cycle-003-closure'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def h(s):
    return hashlib.sha256(s.encode()).hexdigest()

def read(p):
    return json.loads(p.read_text())

def lines(p):
    return [json.loads(x) for x in p.read_text().splitlines()]

def ids(p):
    return p.read_text().splitlines()

def write(name, d):
    p = OUT / name
    assert not p.exists(), 'Immutable review output already exists: ' + name
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')

pins = {}
def pin(p, expected=None):
    got = sha(p)
    assert expected is None or got == expected, str(p)
    pins[str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)] = got
    return got

m = read(C / 'manifest.json')
pin(C / 'manifest.json', '451443f38751fb62953c2d37522077dc85a49a6a6f3a51f7167db55bbf544de3')
for key in ('previousComponents','currentComponents','previousRegressionCatalog','currentRegressionCatalog','otherEvidence'):
    for d in m[key].values():
        pin(ROOT / d['path'], d['sha256'])
for key in ('changedIds','closureIds','nextReviewDeltaIds','previousIndependentReads','cleanSupplementalReads','invalidatedPriorIds','retiredPriorIds','reviewRows','reusedDynamicConsumerContext'):
    d=m[key]; pin(ROOT / d['path'],d['sha256'])
for d in m['afterAuthoredFiles']+m['authoredMaps']:
    pin(ROOT / d['path'],d['sha256'])
plan=read(L/'correction-cycle-003-plan.json')
validation=read(L/'correction-cycle-003-validation.json')
pin(L/'correction-cycle-003-plan.json',m['pins']['cycle003Plan'])
pin(L/'correction-cycle-003-validation.json','76a3d12de65ffd6f3f10cee36483aede1bcc08e9be3ab6d0b029a03564edf490')
for path,key in [('Source/localization-inventory-v3/strings.jsonl','sourceInventory'),('Source/localization-inventory-v3/static-text.jsonl','staticInventory'),('Documentation/glossary-translations/ro/layer.json','approvedGlossary'),('Source/preserve-exactly-v4.json','preserveExactManifest'),('Translations/ro/independent-review-01/compiled_context.py','compiledDecoder'),('Source/glossary-corpus-v2/runtime-bindings.json','compiledRuntimeBindings'),('Source/glossary-corpus-v2/current-dialogs-scope.json','compiledScopePin')]:
    pin(ROOT/path,m['pins'][key])
for d in read(L/'independent-review-02/audit-manifest.json')['files']:
    pin(ROOT/d['path'],d['sha256'])
pin(L/'independent-review-02/audit-manifest.json',m['pins']['review02Audit'])
pin(L/'remedial-cycle-002-closure-v2/manifest.json',m['pins']['previousClosureManifest'])
progress=read(L/'semantic-review-progress.json')
pin(L/'semantic-review-progress.json',m['pins']['firstPassProgress'])
assert progress['reviewedUnits']==progress['acceptedUnits']==16538
allrows=[]
for d in progress['reviewSegments']:
    p=ROOT/d['path'];pin(p,d['sha256']);allrows.extend(lines(p))
assert [r['ordinal'] for r in allrows]==list(range(16538))
allmap={r['stableId']:r for r in allrows}
rows=lines(C/'review-rows.jsonl'); byid={r['stableId']:r for r in rows}
changed=set(ids(C/'changed-ids.txt')); closure=set(ids(C/'closure-ids.txt'))
old=set(ids(L/'remedial-cycle-002-closure-v2/closure-ids.txt'))
supp=lines(L/'independent-review-02/supplemental-context-decisions.jsonl')
clean={r['stableId'] for r in supp if r['decision']=='no-objective-correction-in-context-unit'}
credited=old|clean
delta=changed|(closure-credited)|(changed&credited)
assert delta==set(ids(C/'next-review-delta-ids.txt'))==changed
assert len(old)==4467 and len(closure)==4498 and len(clean-old)==30 and len(closure-old)==31
assert not old-closure
assert [r['stableId'] for r in rows]==ids(C/'closure-ids.txt')
for name in ('changed-ids.txt','closure-ids.txt','next-review-delta-ids.txt'):
    seq=ids(C/name); assert seq==[r['stableId'] for r in allrows if r['stableId'] in set(seq)]
prior={}
for path in ('independent-review-01/per-id-decisions-final.jsonl','independent-review-02/per-id-decisions.jsonl','independent-review-02/supplemental-context-decisions.jsonl'):
    p=L/path;pin(p)
    for r in lines(p): prior[r['stableId']]=(str(p.relative_to(ROOT)),r)
reuse=[]
for r in rows:
    if r['stableId'] in changed: continue
    path,p=prior[r['stableId']]
    assert p['fullSourceAndCurrentTargetRead']
    assert (p.get('sourceSha256') or h(p['source']))==h(r['source'])
    assert (p.get('targetSha256') or h(p['target']))==h(r['after'])
    assert p['decision'].startswith('no-objective-correction')
    reuse.append({'ordinal':r['ordinal'],'stableId':r['stableId'],'sourceSha256':h(r['source']),'targetSha256':h(r['after']),'priorDecisionPath':path,'decision':'exact unchanged prior full-unit decision applicable'})
assert len(reuse)==4493
write('prior-decision-applicability.json',{'rows':reuse,'unchangedRows':4493,'freshDeltaRows':5,'sourceGlossaryAndCompiledBindingUnchanged':True,'olderWholeFileByteParity':'unverified; reuse binds actual stable-ID source/current targets, not unavailable older bytes'})
reversals=[]
for d in validation['currentCycleExactByteReconstruction']:
    p=ROOT/d['path'];data=read(p);assert sha(p)==d['postApplicationSha256']
    for fix in plan['decisions']:
        if fix['authoredPath']!=d['path']:continue
        e=data['entries'][fix['entryIndex']]
        assert str(e['id'])==fix['stableId'].rsplit(':',1)[1] and e['target']==fix['after']
        e['target']=fix['before']
    reverse=h(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    assert reverse==d['preApplicationSha256']==d['reverseReconstructionSha256']
    reversals.append({**d,'independentlyReproduced':True})
write('application-and-preimage-boundary.json',{'currentCycleFourExactReverseMatches':reversals,'historicalFiveFiles':validation['historicalUnrecoveredFiles'],'historicalNonTargetParity':'unverified; no original bytes recovered','restartAssessment':'No changed or unverifiable stable-ID mapping, source, glossary, current target coverage or compiled binding established. Missing historical bytes alone do not invalidate the hash-bound unit decisions reproduced here.'})
spec=importlib.util.spec_from_file_location('review03_decoder',L/'independent-review-01/compiled_context.py')
decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
nodes,programsha=decoder.load();ctx=read(C/'compiled-consumer-context.json')
assert programsha==ctx['programSha256']==plan['compiledAdjudication']['programSha256']
for name,ins in ctx['affectedSceneNodes'].items():assert nodes[name]==ins
callers={n for n,ins in nodes.items() if any('selfchek_wash_armpits' in i['operands'] for i in ins)}
assert callers=={'selfcheck_armpit_imposter','selfcheck_hands'}
assert any(i['operands']==['WashArmpits',0.0] for i in nodes['selfchek_wash_armpits'])
keyids={}
for r in allrows:
    if r.get('key'):keyids.setdefault(r['key'],set()).add(r['stableId'])
def resolved(names):
    return {sid for n in names for i in nodes[n] for op in i['operands'] if isinstance(op,str) for sid in keyids.get(op,set())}
assert resolved(callers|{'selfchek_wash_armpits'})==set(ids(C/'component-wash-callback-family.ids.txt'))
success={'FEMA_GivingPostcard','FEMA_GivingPostcard_Firefighter'}
assert resolved(success)==set(ids(C/'component-item-transfer-success-responses.ids.txt'))
trans=read(L/'independent-review-02/transfer-bindings.json');assert len(trans['bindings'])==245
for b in trans['bindings']:
    ins=nodes[b['node']]
    for i in [b['optionInstruction']]+b['existingItemGuardInstructions']+b['transferInstructions']:
        assert ins[i['index']]==i
    assert b['optionInstruction']['opcode']==4 and b['optionInstruction']['operands'][-1] is True
    assert ['GetItemCount'] in [i['operands'] for i in b['existingItemGuardInstructions']]
    assert ['Number.GreaterThan'] in [i['operands'] for i in b['existingItemGuardInstructions']]
    ti=b['transferInstructions'];assert ti[-1]['operands']==['TryGiveItemFor']
    assert ti[0]['operands']==['Povistka'] and ti[2]['operands']==[b['recipient']]
    assert ins[ti[-1]['index']+1]['opcode']==10
    assert ins[ti[-1]['index']+2]['operands']==[b['successfulResponseNode']]
    assert b['successfulResponseNode'] in success
    assert byid[b['stableId']]['after']==b['target']=='Înmânează ordinul de prezentare la Comitet'
write('compiled-binding-verification.json',{'programSha256':programsha,'affectedNodesVerified':list(ctx['affectedSceneNodes']),'washCallerNodes':sorted(callers),'sharedCommand':'WashArmpits','transferBindingsVerified':245,'successfulResponseIds':[r['stableId'] for r in rows if r['ordinal'] in range(6757,6763)],'sourcePeculiarity':'Hands impurity branch calls the shared armpit wash callback; retained without source or binding repair.','boundary':'Decoded source instructions and exact operands/order/conditions; not a VM, live reachability, speaker dispatch or visual test.'})
catalog=[]
fresh=set(ids(C/'component-affected-compiled-scenes.ids.txt'))
for name,d in m['currentRegressionCatalog'].items():
    members=set(ids(ROOT/d['path']));assert len(members)==d['rows']
    assert members<=closure and members<=set(reuse_row['stableId'] for reuse_row in reuse)|changed
    catalog.append({'class':name,**d,'freshExactDeltaReads':len(members&changed),'freshSupplementalContextReads':len(members&(fresh-changed)),'unchangedPriorDecisionsApplicable':len(members-changed),'result':'clean','applicability':'Current complete class and exact hash retained; changed members freshly read, every other member matched to an unchanged full-unit decision. Empty witness subclasses do not remove hidden-label and placeholder members in retained UI/markup classes.'})
write('mandatory-catalog.json',{'classes':catalog,'unionIds':len(set().union(*(set(ids(ROOT/d['path'])) for d in m['currentRegressionCatalog'].values()))),'allApplicableClassesReconciled':True,'renderingChecks':'Romanian Latin script; no bidi/RTL/shaping change introduced. Fonts, textures, rendered layout and runtime remain not-run under text-only scope.'})
write('recipe-and-coverage.json',{'normalRecipeCommand':'.venv/bin/python Translations/ro/correction-cycle-003-closure-recipe.py verify','normalRecipeResult':'verified','closureManifestSha256':sha(C/'manifest.json'),'oldClosure':4467,'currentClosure':4498,'addedIds':31,'cleanSupplementalAddedIds':30,'retiredIds':0,'exactDelta':5,'unchangedHashBoundDecisions':4493,'freshScenePairsRead':48,'freshSupplementalPairsRead':43,'semanticFirstPass':16538,'repeatCommand':'.venv/bin/python Scripts/expand_exact_text_batch.py Translations/ro/dialogue-repeats-001.authored.json Translations/ro/dialogue-batch-001.json --verify','repeatResult':'verified 2828 rows, including 245 document-transfer labels','boundary':'Canonical-order lists, prior/current set accounting and actual current target receipts independently reconciled; no full closure semantic reread.'})
for p in [L/'correction-cycle-003-closure-recipe.py',ROOT/'Documentation/glossary-research/final-v1/glossary.json',ROOT/'Documentation/glossary-research/final-v1/evidence.json',ROOT/'Documentation/glossary-research/final-v1/sources.md',ROOT/'Scripts/validate_locale_corpus.py',ROOT/'Scripts/locale_text_inputs.py',ROOT/'Scripts/expand_exact_text_batch.py',ROOT/'Documentation/localization-state.json']:
    pin(p)
for p in [Path('/Users/antonkrutov/.codex/instructions/sitefor-mods.md'),Path('/Users/antonkrutov/.codex/instructions/game-localization-prompt.md'),Path('/Users/antonkrutov/.codex/instructions/game-localization-audit-workflow.md'),Path('/Users/antonkrutov/.codex/skills/vn-game-localize/SKILL.md')]:pin(p)
write('input-pins.json',{'pins':[{'path':p,'sha256':v} for p,v in sorted(pins.items())],'authoredFiles':len(m['afterAuthoredFiles']),'note':'Exact current closure manifest pins take precedence over stale older batch fields in the summary checkpoint.'})
print(json.dumps({'verifiedPins':len(pins),'unchangedDecisions':4493,'delta':5,'transferBindings':245,'catalogClasses':len(catalog)}))
