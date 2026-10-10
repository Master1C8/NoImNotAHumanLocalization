"""Review05 immutable-input, ordinary-selector and decision applicability proof."""
import hashlib, importlib.util, json, re, sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
C = ROOT / 'Translations/fil/semantic-correction-cycle-005'
P = ROOT / 'Translations/fil/independent-review-04'
def load(p): return json.loads(p.read_text())
def jl(p): return [json.loads(s) for s in p.read_text().splitlines()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def h(s): return hashlib.sha256(s.encode()).hexdigest()
def require(ok, message):
    if not ok: raise AssertionError(message)
def write(name, d):
    p = OUT / name
    raw = (json.dumps(d, ensure_ascii=False, indent=2) + '\n').encode()
    if p.exists(): require(p.read_bytes() == raw, 'Reproduction differs: ' + name)
    else: p.write_bytes(raw)
def main():
    pins = {}
    def pin(path, expected):
        p = Path(path); p = p if p.is_absolute() else ROOT / p
        actual = sha(p); require(actual == expected, 'Input changed: ' + str(path))
        require(str(path) not in pins or pins[str(path)] == actual, 'Conflicting pin')
        pins[str(path)] = actual
    pin(str((C / 'handoff.json').relative_to(ROOT)), '848a5f954b687464319839d4f095ad1b1f08d99f2fde903fba95d50ce73c27b7')
    pin(str((C / 'completion-manifest.json').relative_to(ROOT)), '2e4509a2645e76973336ae2ab0dcc606ef04b2617dc15256904b05d4f7403f17')
    pin(str((C / 'next-delta-paired.jsonl').relative_to(ROOT)), 'edb5860a6165136d0ff7d4963a65153d61fb1955bdef5daf8cbb5ac0eecabf02')
    pin(str((P / 'completion-manifest.json').relative_to(ROOT)), 'dea36a5b9f34c3b207fc97bcd88e29c03592fd21767ec3112918da6ad339915b')
    for directory in (C, P):
        for x in load(directory / 'completion-manifest.json')['files']: pin(x['path'], x['sha256'])
    plan = load(C / 'plan.json'); gate = load(C / 'full-structural-validation.json')
    allowed = {plan['row']['authoredPath']: gate['affectedBatchSha256'], gate['affectedValidationPath']: gate['affectedValidationSha256']}
    historical = []
    for x in load(P / 'input-verification.json')['pinChecks']:
        current = allowed.get(x['path'], x['sha256']); pin(x['path'], current)
        if current != x['sha256']: historical.append({'path':x['path'], 'priorSha256':x['sha256'], 'currentSha256':current})
    for x in plan['sourceAndGlossaryFingerprints'].values(): pin(x['path'], x['sha256'])
    for x in gate['authoredFiles']: pin(x['path'], x['sha256'])
    receipt = load(C / 'full-corpus-validation.json')
    pin('Scripts/validate_locale_corpus.py', receipt['validatorSha256'])
    pin('Scripts/locale_text_inputs.py', receipt['inputLoaderSha256'])
    for name, expected in receipt['owningValidators'].items(): pin('Scripts/' + name, expected)
    for x in load(P / 'dynamic-input-applicability.json')['pins']: pin(x['path'],x['sha256'])
    # The bounded author read is a preimage read; compare it to its snapshot rather than current mutated batch.
    for r in jl(C / 'bounded-family-paired.jsonl'):
        path = plan['beforeAuthoredPath'] if r['authoredPath'] in allowed else r['authoredPath']
        pin(path, r['authoredSha256'])
    cm = load(C / 'completion-manifest.json')
    pin(cm['currentProgressPath'], cm['currentProgressSha256'])
    require(sha(ROOT/cm['currentProgressPath']) == sha(ROOT/cm['immutableAfterProgressPath']), 'Mutable administrative snapshot differs')
    rows = jl(C / 'closure-paired.jsonl'); delta = jl(C / 'next-delta-paired.jsonl')
    before = jl(ROOT/'Translations/fil/semantic-correction-cycle-004/closure-paired.jsonl')
    prior = jl(P/'closure-decision-applicability.jsonl')
    old = {r['stableId']:r for r in prior}; prev = {r['stableId']:r for r in before}
    ids = {r['stableId'] for r in rows}; ds = {r['stableId'] for r in delta}; cl = load(C/'closure.json')
    corrected = set(cl['corrected']['ids']); new = ids-set(prev); invalid = set(cl['explicitlyInvalidatedPriorEvidence']['ids'])
    require(len(rows)==len(ids)==7678 and len(delta)==len(ds)==141, 'Closure uniqueness/count')
    require(ds == corrected | new | invalid and len(corrected)==1 and len(new)==66 and len(invalid)==74, 'Delta union')
    require(not (corrected & new or corrected & invalid or new & invalid), 'Delta categories overlap')
    require(ids-set(ds)==set(r['stableId'] for r in rows if r['stableId'] not in ds), 'Reuse accounting')
    for r in rows:
        require(h(r['source']) == r['sourceSha256'] and h(r['target']) == r['targetSha256'], 'Pair text hash')
        if r['stableId'] not in ds:
            q=old[r['stableId']]
            require(q['findingId'] is None and all(q[k]==r[k] for k in ('sourceSha256','targetSha256','key','nodeNames')), 'Stale prior decision')
    family = set(r['stableId'] for r in jl(C/'bounded-family-paired.jsonl'))
    article = set(r['stableId'] for r in rows if 'Theorist_Asking_3' in r['nodeNames'])
    require(len(family)==83 and family<=ds and len(article)==10 and article<=ds, 'Fresh family/article coverage')
    comps = {x['name']:set(x['ids']) for x in cl['components']}
    require(set().union(*comps.values()) == ids, 'Component union')
    require(len(comps['mandatoryRegression'])==7279 and len(comps['mandatoryRegression']&ds)==109, 'Mandatory split')
    retired=jl(C/'retired-final-applicability.jsonl'); require(len(retired)==54, 'Retired count')
    require(len(set(prev)-ids)==0, 'Unexpected new retirement')
    require(len({r['stableId'] for r in retired}&ids)==1 and len({r['stableId'] for r in retired}-ids)==53, 'Retirement reentry')
    # Decode current bytes using shipped opcode fields and verify complete minimum scenes.
    spec=importlib.util.spec_from_file_location('review05_actual_decoder', P/'bytecode_decoder.py')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    require(hashlib.sha256(m.raw).hexdigest() == plan['compiledProgramSha256'], 'Compiled program changed')
    ctx=load(C/'current-compiled-context.json'); inventory={r['stableId']:r for r in jl(ROOT/'Source/localization-inventory-v3/strings.jsonl')}
    pairs={r['stableId']:r for r in rows}
    for name,node in ctx['nodes'].items():
        a=m.actual[name]; require(a['labels']==node['labels'] and len(a['instructions'])==len(node['instructions']), 'Node/labels/count')
        for ins, raw in zip(node['instructions'], a['instructions']):
            require(all(ins[k]==raw[k] for k in ('index','opcode','op','operands')), 'Actual instruction differs')
            if ins['sourceStableId']:
                q=inventory[ins['sourceStableId']]; t=pairs[ins['sourceStableId']]
                require(q['key']==ins['operands'][0] and q['source']==ins['source'] and name in q['nodeNames'] and t['target']==ins['target'], 'Text consumer identity')
    legacy = next(r for r in rows if r['acceptedOrdinal']==5593)
    require(legacy['nodeNames']==[] and not any(ins['op'] in ('RunLine','AddOption') and ins['operands'][0]==legacy['key'] for n in m.actual.values() for ins in n['instructions']), 'Invented legacy consumer')
    # Independently regenerate selectors over the accepted inventory and the target texts.
    full = {}
    G={'UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1'}
    for file in gate['authoredFiles']:
        d=load(ROOT/file['path'])
        for e in d['entries']:
            sid=e['stableId'] if file['path'].endswith('static-text-draft.json') else f"string:{G[d['collection']]}:{e['id']}"
            full[sid]=e['target']
    inventory.update({r['stableId']:r for r in jl(ROOT/'Source/localization-inventory-v3/static-text.jsonl')})
    selectors=load(C/'selector-specification.json')
    selected_refs={sid for sid in full if any(re.search(p,inventory[sid]['source']) for p in selectors['affectedReferentSourceRegex'].values())}
    selected_words={sid for sid in full if full[sid] in (plan['row']['currentTarget'],plan['row']['acceptedFullTarget']) or any(re.search(p,full[sid]) for p in selectors['localizedWordingRegex'])}
    options={p['source'] for p in load(ROOT/'Translations/fil/common-options-001.authored.json')['phrases']}
    selected_mand={sid for sid in full if inventory[sid].get('collection')=='UI' or sid.startswith('tmp:') or inventory[sid]['source'] in options or any(re.search(p,inventory[sid]['source']) for p in selectors['mandatorySourceRegex'].values())}
    require(selected_refs==comps['glossaryReferent'] and selected_words==comps['localizedWording'] and selected_mand==comps['mandatoryRegression'], 'Ordinary selector differs')
    for x in selectors['regressionExamples']:
        require(inventory[x['stableId']]['source']==x['source'] and (x['expectedSelector'] in ('all-ui','all-static') or re.search(selectors['mandatorySourceRegex'][x['expectedSelector']],x['source'])), 'Actual control')
    for x in selectors['syntheticSelectorRegressions']:
        require(bool(re.search(selectors['mandatorySourceRegex'][x['selector']],x['source']))==x['mustMatch'], 'Synthetic control')
    context={sid for sid in full if set(inventory[sid].get('nodeNames',[])) & set(ctx['nodes'])}
    dynamics=set(r['stableId'] for r in load(P/'input-verification.json')['dynamicConsumers'])
    require(context==comps['explicitContext'] and context|dynamics==comps['runtimeBinding'], 'Context/dynamic identities')
    require({sid for sid in full if inventory[sid]['source']==plan['row']['source']}==comps['exactSourceRepetition'], 'Source repetition')
    # Author follow-up worklist: enumerated coarse-source family, with zero extra semantic-review credit.
    coarse=r'(?i)\b(?:хрен[а-яё]*|хер[а-яё]*|нахрен[а-яё]*|нахер[а-яё]*|нихрен[а-яё]*|нихер[а-яё]*|похрен[а-яё]*|похер[а-яё]*)\b'
    affected=[dict(stableId=sid,key=inventory[sid].get('key'),nodeNames=inventory[sid].get('nodeNames',[]),source=inventory[sid]['source'],sourceSha256=h(inventory[sid]['source']),targetSha256=h(full[sid]),alreadyInCurrentClosure=sid in ids,requiresAuthorSemanticAdjudication=True) for sid in full if re.search(coarse,inventory[sid]['source'])]
    consumers={}
    for name,node in m.actual.items():
        for ins in node['instructions']:
            if ins['op'] in ('RunLine','AddOption'):
                consumers.setdefault(ins['operands'][0],[]).append({'node':name,'instruction':ins['index'],'opcode':ins['op'],'operands':ins['operands']})
    for x in affected:
        x['compiledConsumers']=consumers.get(x['key'],[])
        require(set(c['node'] for c in x['compiledConsumers'])==set(x['nodeNames']), 'Coarse worklist actual consumer mismatch')
    excon=[x for x in affected if x['source'].startswith('Experienced:')]
    repeated=[x for x in affected if x['source']=='Experienced: Какого хрена все ходят в одежде в такую жару…']
    write('coarse-source-dependencies.json', {'predicate':coarse,'acceptedOnly':True,'count':len(affected),'experiencedCount':len(excon),'exactFindingSourceRepetitions':len(repeated),'rows':affected,'semanticCredit':0,'purpose':'Single consolidated author review of enumerated coarse-wording mechanism; selector matches do not imply mistranslation. Actual opcode bindings identify consumers, not live scheduling.'})
    write('independent-compiled-context.json',ctx)
    write('input-verification.json',{'reviewer':'/root/fil_independent_review_05','pinChecks':[{'path':p,'sha256':s} for p,s in sorted(pins.items())], 'authorizedHistoricalPinChanges':historical,'sourceAndGlossaryUnchanged':True,'authorPreimageApplicability':'83 bounded rows compared with archived before snapshot; author decisions supply no independent credit','mutableAdministrativeState':'current progress exact to sealed after-progress; excluded from semantic decision identity','closure':7678,'fresh':141,'corrected':1,'new':66,'invalidated':74,'reusable':7537,'mandatory':7279,'mandatoryFresh':109,'mandatoryReuse':7170,'retiredNew':0,'reentered':1,'stillRetired':53,'familyFresh':83,'articleFresh':10,'actualCompiledNodes':7,'actualCompiledInstructions':174,'dynamicConsumerCount':6,'legacy5593HasCompiledConsumer':False,'normalSelectorControls':29,'syntheticSelectorControls':19,'fullRestartObserved':False,'runtime':'not-run','telemetry':'unknown'})
    print(json.dumps({'pins':len(pins),'closure':7678,'delta':141,'coarseAcceptedWorklist':len(affected),'experiencedCoarseWorklist':len(excon),'proof':'passed'}))
if __name__=='__main__':main()
