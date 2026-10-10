#!/usr/bin/env python3
"""Independent cycle007 applicability checks and immutable evidence seal.
Writes only this new review directory. File digests are cached before row loops.
"""
import hashlib, importlib.util, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
C = ROOT / 'Translations/fil/semantic-correction-cycle-007'
R = ROOT / 'Translations/fil/independent-review-06'
REVIEWER = '/root/fil_independent_review_07'
CACHE = {}
def sha(p):
    p = Path(p).resolve()
    if p not in CACHE: CACHE[p] = hashlib.sha256(p.read_bytes()).hexdigest()
    return CACHE[p]
def digest(s): return hashlib.sha256(s.encode()).hexdigest()
def record_hash(d): return digest(json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
def load(p): return json.loads(p.read_text())
def rows(p): return [json.loads(s) for s in p.read_text().splitlines()]
def write(n, d):
    p = OUT/n; assert not p.exists(), n
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n')
def jl(n, data):
    p = OUT/n; assert not p.exists(), n
    p.write_text(''.join(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n' for d in data))
NOTES = {
2797:'The shared purpose is the present Miner/player exchange: preceding actual line says the player will descend and Miner will cover him from above. Inclusive tayo here preserves their proposed cooperation; it does not include the player in the earlier digging group.',
2798:'Lifetime regret and quoted counterfactual about not having been afraid retained; rhetorical persuasion does not state a completed descent.',
2799:'Player descends; Miner stays above and promises to cover him. Bahala sa iyo retains the promise without inventing a guaranteed safe result.',
2804:'Player asks why Miner himself will not descend; action direction and interlocutor retained.',
2805:'Place/hole calls to the player, followed by repeated question about feeling it; source ambiguity retained.',
2806:'Someone among the present interlocutors must act, with urgency now-or-never. Inclusive atin/tayong refers to proposed action in this exchange and is justified by the options and next actual branch.',
2821:'Denial of simple fear, enticing/pulling effect, and wish for one closer look retained; metaphorical hinihigop ka preserves the attraction rather than declaring a completed physical event.',
2822:'Standing near it seems to summon someone, repeated calling, approach and listening instructions all retained.',
2823:'Earlier observation with his group uses exclusive kaming lahat; darkness and inability to see retained.',
2824:'Wish to look and precarious rope consequence remain hypothetical; a wrong/extra pull ends badly without a specific invented casualty.',
2825:'Contradictory yes-and-no answer to having looked retained; continuation explains its qualification.',
2832:'Player asks whether Miner himself has looked into the hole; subject and completed-experience question retained.',
2833:'Player is addressed upstairs, warned he could end up like Miner with a flashlight; lack of food below retained. Accepted rough register preserved.',
2834:'Corrected kami explicitly excludes upstairs player from elapsed underground stay. Strange passage of time, absent sun/clocks and colloquial uncertainty all remain; malay natin scopes uncertainty without changing the exclusive group.',
2835:'Hard-of-hearing request to speak louder, sitting there and uncertain second/third day retained.',
2839:'Promise of further information after player reaches Miner/group retains exclusive amin and conditional timing.',
2840:'Exclusive digging group and near collapse onto their heads retained; no actual collapse invented.',
2841:'Conditional desire to reach Miner and prohibition on excavating this hole retained.',
2842:'An unnamed group member read or heard about something interesting; uncertainty and delayed disclosure retained.',
2846:'Exact repeated near-collapse account on separate branch retains exclusive kami/namin and hypothetical danger.',
2847:'Exact repeated reaching-Miner warning retained on its distinct branch.',
2848:'One of Miner’s group descended; Miner keeps watch to haul him out if needed. Agency, exclusive group and contingency retained.',
2860:'Player option asks whether Miner/group caught a Visitor; kayo and Panauhin retain participant direction and approved concept.',
2861:'Player asks what is interesting down there; no answer or identity disclosed early.',
2862:'Earlier group discovery uses exclusive kami; vague something found remains unnamed.',
2863:'Long tunnels, colloquial male address and unknown destinations retained.',
2864:'More tunnels formerly existed; some recently became buried. Sana expresses lost larger quantity in context, without changing the recent partial blockage.',
2865:'Digging had just begun when group found whole underground network; exclusive naming/kami, timing and extent retained.',
2866:'Miner and male companions planned tunnels to hide from heat; exclusive kami, companions and purpose retained.',
2868:'Player asks why Miner is there; source question preserved.',
2869:'Dust in Miner’s ears makes player hard to hear, cotton simile and colloquial oath retained with mild source curse.',
2870:'Miner denies being trapped and says his group found something; exclusive kami and unrevealed object retained.',
2871:'Short hearing/request-for-clarification interjection retained.',
16128:'Corrected lahat ng gawain sa bahay restores all household work; embraces of own children and caresses of spouse remain distinct uses of hands. No one values it remains coarse, resentful and unqualified.'
}
def main():
    expected={'handoff.json':'abd7402f701307008cb0bfa9e4efff8ec9405bf27d21fdd8b3395c64cf7c9468','completion-manifest.json':'589a09365720919e6d0f45fb15c25388859e217ad426c19b01e566534a1354e2','closure.json':'de46cf6d83b99466d5b8a8fbd73985fb2b4d6e7125a7725bf756f1b9314f838a','next-delta-paired.jsonl':'c5c59ca6b0ebf590b5a66b99ce220cc7fa7940edb58c9515897e136731cd424b'}
    for n,h in expected.items(): assert sha(C/n)==h,n
    manifest=load(C/'completion-manifest.json');pinmap={}
    for p in manifest['files']+manifest['currentExternalPins']+[dict(path=str((C/'completion-manifest.json').relative_to(ROOT)),sha256=expected['completion-manifest.json'])]:
        if p['path'] in pinmap: assert pinmap[p['path']]==p['sha256']
        pinmap[p['path']]=p['sha256']
    for path,h in pinmap.items():assert sha(ROOT/path)==h,path
    checks=[dict(path=p,sha256=h,result='exact') for p,h in sorted(pinmap.items())]
    assert len(manifest['files'])==42 and len(manifest['currentExternalPins'])==1392
    actual={str(p.relative_to(ROOT)) for p in C.rglob('*') if p.is_file() and p.name!='completion-manifest.json'}
    assert actual=={p['path'] for p in manifest['files']}
    assert sha(R/'completion-manifest.json')=='3d1206f42a8d956aa3b39642740e090d480e54128e6e7759fe6748e3cdbc8bfa'
    assert sha(R/'final-verdict.json')=='acebaa1ae29b3137e468cb73cecd4bee53de26715047dac66922d2de88a7d7c9'
    sys.path.insert(0,str(C));import verify_application,build_closure
    # Patch only this process's immutable-file digest helper, not pinned source files.
    verify_application.sha=sha;build_closure.sha=sha
    reproduced,outputs=build_closure.build()
    for name,raw in outputs.items():assert (C/name).read_bytes()==raw,name
    closure=load(C/'closure.json');pairs=rows(C/'closure-paired.jsonl');fresh=rows(C/'next-delta-paired.jsonl')
    priorPairs={p['stableId']:p for p in rows(ROOT/'Translations/fil/semantic-correction-cycle-006/closure-paired.jsonl')}
    priorDecRows=rows(R/'closure-decision-applicability.jsonl');priorDec={p['stableId']:p for p in priorDecRows}
    priorDecisionHash=sha(R/'closure-decision-applicability.jsonl');priorMandatoryHash=sha(R/'mandatory-regression-applicability.jsonl')
    priorRetiredHash=sha(R/'retired-final-applicability.jsonl');mandatoryHash=sha(C/'mandatory-regression-catalog.jsonl')
    cur={p['stableId']:p for p in pairs};delta={p['stableId'] for p in fresh};prior=set(priorPairs);current=set(cur)
    changed=set(closure['corrected']['ids']);invalid=set(closure['explicitlyInvalidatedPriorEvidence']['ids'])
    topology=load(C/'current-bounded-consumers.json');bounded=load(C/'bounded-author-inputs.json')
    decoder=ROOT/'Translations/fil/independent-review-04/bytecode_decoder.py'
    ds=importlib.util.spec_from_file_location('review07_decoder',decoder);dec=importlib.util.module_from_spec(ds);ds.loader.exec_module(dec)
    assert hashlib.sha256(dec.raw).hexdigest()==closure['compiledProgramSha256']
    G={'UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1'};targets={}
    for pin in load(C/'full-corpus-validation.json')['authoredFiles']:
        doc=load(ROOT/pin['path'])
        for e in doc['entries']:
            s=e['stableId'] if 'stableId' in e else f"string:{G[doc['collection']]}:{e['id']}"
            assert s not in targets;targets[s]=e['target']
    inventory=rows(ROOT/'Source/localization-inventory-v3/strings.jsonl');sourceRows=[r for r in inventory if r['stableId'] in targets]
    source={r['stableId']:r for r in sourceRows};source.update({r['stableId']:r for r in rows(ROOT/'Source/localization-inventory-v3/static-text.jsonl') if r['stableId'] in targets})
    order=[r['stableId'] for col in ['UI','ChecksDialogs','Dialogs'] for r in inventory if r['collection']==col and r['stableId'] in targets]+[r['stableId'] for r in load(ROOT/'Translations/fil/static-text-draft.json')['entries']]
    assert len(order)==len(set(order))==len(targets)==len(source)==16538
    assert digest(''.join(s+'\n' for s in order))==closure['acceptedOrderSha256']
    rank={s:i+1 for i,s in enumerate(order)}
    # Preserve selected collection identity for duplicate bare keys; active Dialogs owns Yarn sites.
    byKey={r['key']:r['stableId'] for r in sourceRows};keyIds={}
    for r in sourceRows:keyIds.setdefault(r['key'],[]).append(r['stableId'])
    duplicates={k:v for k,v in keyIds.items() if len(v)>1}
    actualSites={}
    for name,node in dec.actual.items():
        for i in node['instructions']:
            if i['op'] in ['RunLine','AddOption']:actualSites.setdefault(i['operands'][0],[]).append(dict(node=name,instruction=i['index'],opcode=i['op'],operands=i['operands']))
    def identity(s):
        r=source[s];key=r.get('key');sites=actualSites.get(key,[]) if byKey.get(key)==s else []
        return dict(compiledProgramSha256=closure['compiledProgramSha256'],key=key,nodeNames=r.get('nodeNames',[]),sites=sites)
    applicable=set()
    for p in pairs:
        s=p['stableId'];ci=identity(s)
        assert p['acceptedOrdinal']==rank[s] and p['source']==source[s]['source'] and p['target']==targets[s]
        assert digest(p['source'])==p['sourceSha256'] and digest(p['target'])==p['targetSha256']
        assert ci==p['consumerIdentity'] and record_hash(ci)==p['consumerIdentitySha256']
        if s in prior:
            a=priorPairs[s];d=priorDec[s]
            for k in ['stableId','acceptedOrdinal','sourceSha256','key','nodeNames','consumerIdentitySha256']:assert a[k]==d[k]==p[k],(s,k)
            assert a['targetSha256']==d['targetSha256']
            if p['targetSha256']==a['targetSha256'] and d['decision']!='objective-correction-required' and d['findingId'] is None:applicable.add(s)
    assert len(current)==7869 and len(delta)==34 and len(applicable)==7846
    assert len(current-prior)==21 and len(current-applicable)==23 and len(invalid)==11 and len(changed)==2
    assert delta==changed|(current-applicable)|invalid
    reuse=current-delta;assert len(reuse)==7835 and reuse<=applicable
    assert set(NOTES)=={p['acceptedOrdinal'] for p in fresh}
    assert [p['stableId'] for p in fresh]==closure['exactNextDelta']['ids']==(C/'next-review-ids.txt').read_text().splitlines()
    affected=set(topology['freshAffectedContextIds']);assert len(affected)==34 and affected==delta
    for name,node in bounded['nodes'].items():assert node==dec.actual[name],name
    assert len(bounded['nodes'])==9 and sum(len(n['instructions']) for n in bounded['nodes'].values())==94
    for w in topology['freshAffectedWindows']:
        for i in w['windowInstructions']:
            a=dec.actual[w['node']]['instructions'][i['index']]
            assert (i['op'],i['opcode'],i['operands'])==(a['op'],a['opcode'],a['operands'])
            if i['sourceStableId']:
                p=cur[i['sourceStableId']];assert i['source']==p['source'] and i['target']==p['target'] and p['stableId'] in delta
    assert len(topology['freshAffectedWindows'])==10 and topology['retainedConsumerWindowsExact'] and topology['retainedConsumerWindowCount']==120
    assert sha(ROOT/topology['retainedConsumerEvidencePath'])==topology['retainedConsumerEvidenceSha256']
    # Source-based ordinary selector enumeration and all actual/synthetic controls.
    from source_predicates import source_matches
    spec=load(C/'selector-specification.json');enumerations=[]
    for group,key in [('referentSelectors','affectedReferentSourceRegex'),('mandatorySelectors','mandatorySourceRegex')]:
        for item in closure[group]:
            n=item['name']
            if n not in spec[key]:continue
            selected=[s for s in order if source_matches(n,spec[key][n],source[s]['source'],spec)]
            assert selected==item['ids'],n
            enumerations.append(dict(group=group,name=n,count=len(selected),idsSha256=digest(''.join(s+'\n' for s in selected)),sourceEnumeration=True))
    controls=[]
    for t in spec['regressionExamples']:
        assert source[t['stableId']]['source']==t['source']
        observed=source_matches(t['expectedSelector'],spec['mandatorySourceRegex'][t['expectedSelector']],t['source'],spec)
        assert observed;controls.append(dict(t,actual=True,observed=True,result='passed'))
    for t in spec['syntheticSelectorRegressions']:
        observed=source_matches(t['selector'],spec['mandatorySourceRegex'][t['selector']],t['source'],spec)
        assert observed==t['mustMatch'];controls.append(dict(t,actual=False,observed=observed,result='passed'))
    assert len(spec['regressionExamples'])==73 and len(spec['syntheticSelectorRegressions'])==60
    # No mechanical read is credited as new semantic coverage.
    freshDec=[dict(p,reviewer=REVIEWER,decision='accepted-independent-reviewed-unit',findingId=None,evidenceMode='fresh-full-source-current-target-and-actual-context-read',reason=NOTES[p['acceptedOrdinal']],authorIndependentCredit=0) for p in fresh]
    jl('fresh-decisions.jsonl',freshDec);freshHash=sha(OUT/'fresh-decisions.jsonl');byFresh={d['stableId']:d for d in freshDec}
    closureDec=[]
    for p in pairs:
        s=p['stableId'];isFresh=s in delta;d=byFresh.get(s)
        provenance=None
        if not isFresh:
            old=priorDec[s]
            provenance=dict(path=str((R/'closure-decision-applicability.jsonl').relative_to(ROOT)),fileSha256=priorDecisionHash,recordSha256=record_hash(old),stableId=s,acceptedOrdinal=old['acceptedOrdinal'],decision=old['decision'],findingId=old['findingId'],evidenceMode=old['evidenceMode'],upstreamPriorEvidenceSha256=old.get('priorEvidenceSha256'))
        closureDec.append(dict(stableId=s,acceptedOrdinal=p['acceptedOrdinal'],sourceSha256=p['sourceSha256'],targetSha256=p['targetSha256'],key=p['key'],nodeNames=p['nodeNames'],consumerIdentitySha256=p['consumerIdentitySha256'],components=p['components'],decision=d['decision'] if isFresh else 'exact-prior-independent-decision-reused',findingId=None,evidenceMode='fresh-independent-full-pair' if isFresh else 'prior-independent-reuse',reason=d['reason'] if isFresh else 'Exact unchanged clean prior full source/target/key/node and actual compiled site/opcode/operand identity; outside explicit invalidation.',priorEvidenceSha256=None if isFresh else priorDecisionHash,priorProvenance=provenance,freshEvidenceSha256=freshHash if isFresh else None,reviewer=REVIEWER))
    jl('closure-decision-applicability.jsonl',closureDec)
    mandatory=rows(C/'mandatory-regression-catalog.jsonl');mandatoryIds={r['stableId'] for r in mandatory};priorMandatory={r['stableId']:r for r in rows(R/'mandatory-regression-applicability.jsonl')}
    assert len(mandatory)==len(mandatoryIds)==7355 and len(mandatoryIds&delta)==16 and len(mandatoryIds&reuse)==7339
    mandatoryDec=[]
    for d in closureDec:
        s=d['stableId']
        if s not in mandatoryIds:continue
        provenance=None
        if s in reuse:
            old=priorMandatory[s]
            for k in ['sourceSha256','targetSha256','key','nodeNames','consumerIdentitySha256']:assert old[k]==d[k]
            assert old['findingId'] is None and old['decision']!='objective-correction-required'
            provenance=dict(path=str((R/'mandatory-regression-applicability.jsonl').relative_to(ROOT)),fileSha256=priorMandatoryHash,recordSha256=record_hash(old),stableId=s,decision=old['decision'])
        mandatoryDec.append(dict(d,catalogSha256=mandatoryHash,priorMandatoryProvenance=provenance))
    jl('mandatory-regression-applicability.jsonl',mandatoryDec)
    retired=rows(C/'retired-applicability.jsonl');historical=rows(R/'retired-final-applicability.jsonl');historicalMap={r['stableId']:r for r in historical};retiredDec=[]
    assert len(historical)==78 and sum(not r['currentComponents'] for r in historical)==77
    reentry=[r for r in historical if r['currentComponents']];assert len(reentry)==1 and reentry[0]['stableId'] in reuse
    for r in retired:
        s=r['stableId'];assert s not in current and r['currentComponents']==[] and r['currentTargetExact'] and r['priorCleanDecision']
        assert digest(source[s]['source'])==r['sourceSha256'] and digest(targets[s])==r['targetSha256']
        assert source[s].get('key')==r['key'] and source[s].get('nodeNames',[])==r['nodeNames'] and identity(s)==r['consumerIdentity']
        old=historicalMap[s]
        retiredDec.append(dict(r,reviewer=REVIEWER,independentResult='retirement-applicable; unchanged prior clean full-pair and actual consumer evidence verified',independentNewReadCredit=0,priorProvenance=dict(path=str((R/'retired-final-applicability.jsonl').relative_to(ROOT)),fileSha256=priorRetiredHash,recordSha256=record_hash(old))))
    assert len(retiredDec)==77
    jl('retired-final-applicability.jsonl',retiredDec)
    oldFresh=[r for r in priorDecRows if r['decision']=='accepted-independent-reviewed-unit'];assert len(oldFresh)==421
    assert all(targets[r['stableId']] is not None and digest(targets[r['stableId']])==r['targetSha256'] for r in oldFresh)
    invalidOld=[r['stableId'] for r in oldFresh if r['stableId'] in invalid];assert len(invalidOld)==3
    plan=load(C/'plan.json');correctionDec=[byFresh[r['stableId']] for r in plan['rows']]
    assert len(correctionDec)==2 and {r['acceptedOrdinal'] for r in correctionDec}=={2834,16128}
    write('applied-correction-decisions.json',dict(count=2,accepted=2,rejected=0,resolvedReview06FindingOrdinals=[2834,16128],fullUnitDecisions=correctionDec))
    write('findings.json',dict(reviewer=REVIEWER,status='clean',completeAssignedPass=True,freshFullPairsRead=34,objectiveFindings=[],preferenceAlternativesAreNotDefects=True,dismissedConcerns=[dict(surface='2797/2806 inclusive group',reason=NOTES[2797]+' '+NOTES[2806]),dict(surface='rough register and ear-piercing need/want',reason='Prior accepted decisions remain exact; no new material evidence contradicts them. No stylistic reopening or generic swear quota.')]))
    write('selector-controls.json',dict(actual=73,synthetic=60,passed=133,generatedIdAppend=False,closureReproducedBytes=True,sourceEnumerations=enumerations,controls=controls))
    write('input-verification.json',dict(cycleExpectedHashes=expected,cycleFiles=42,externalPins=1392,pinChecks=checks,review06ManifestSha256=sha(R/'completion-manifest.json'),review06VerdictSha256=sha(R/'final-verdict.json'),currentMappingRows=16538,authoredInputs=456,digestsCachedBeforeTableLoops=True,reviewer=REVIEWER))
    write('full-corpus-validation.json',dict(status='passed applicability; sealed fresh full-corpus guard reused',checkedIds=16538,authoredInputs=456,receiptPath=str((C/'full-corpus-validation.json').relative_to(ROOT)),receiptSha256=sha(C/'full-corpus-validation.json'),structuralApplicationGateSha256=sha(C/'full-structural-validation.json'),applicationGateReproducedBytes=True,sourceTargetMappingIndependentlyReconciled=True,newSemanticReadCredit=0,repeatedUnchangedOptionalProbe=False))
    write('dependency-proof.json',dict(closureSha256=sha(C/'closure.json'),acceptedOrderSha256=closure['acceptedOrderSha256'],currentClosure=7869,previousClosure=7848,corrected=closure['corrected'],currentMinusPrevious=closure['newCurrentMinusPrevious'],currentMinusExactApplicablePrior=closure['currentMinusExactApplicablePrior'],explicitInvalidations=closure['explicitlyInvalidatedPriorEvidence'],exactFresh=closure['exactNextDelta'],exactReuse=closure['reusableUnchangedIndependentPairs'],formula=closure['deltaFormula'],setFormulaIndependentlyReconciled=True,ordinaryRecipeOutputsByteExact=True,mandatory=dict(total=7355,fresh=16,reuse=7339,freshAccepted=16,objectiveFindings=0),retirement=dict(historicalRows=78,priorRetired=77,stillRetired=77,reentered=0,newlyRetired=0,previouslyAcceptedReentryActive=reentry[0]['stableId']),Review06Fresh421Accounting=dict(targetChanged=0,physicallyApplicable=421,invalidated=invalidOld,reusable=418),Review06FindingsCleanReuse=False,sourceGlossaryBindingsUnchanged=True,fullRestart=False,fullRestartReason='Source/inventory/glossary/program/parser/accepted mapping and complete first-pass identity unchanged; bounded corrections and complete ordinary closure remain reproducible.',limits='No new full16538 semantic reading credit.'))
    dynamics=topology['unchangedDynamicConsumerPins'];assert len(dynamics)==6
    for d in dynamics:
        s=d['stableId'];assert digest(source[s]['source'])==d['sourceSha256'] and digest(targets[s])==d['targetSha256'] and s in reuse
    duplicateProof=[]
    for k,ids in duplicates.items():
        duplicateProof.append(dict(key=k,stableIds=ids,activeYarnOwner=byKey[k],siteCounts={s:len(identity(s)['sites']) for s in ids}))
    write('consumer-context-proof.json',dict(consumerFileSha256=sha(C/'current-bounded-consumers.json'),compiledProgramSha256=closure['compiledProgramSha256'],decoderSha256=sha(decoder),freshWindowsRead=10,freshActualTextContextUnitsRead=34,fullControlTopologyNodesPinned=9,fullControlTopologyInstructionsPinned=94,allFreshWindowOpcodesOperandsIndependentlyReconciled=True,actualFullPairConsumersIndependentlyReconciled=7869,retiredActualConsumersIndependentlyReconciled=77,selectedMappingRows=16538,duplicateSelectedKeyProof=duplicateProof,retainedCoarseWindows=120,retainedCoarseWindowsExact=True,dynamicConsumersExact=6,dynamicPins=dynamics,dynamicPriorProofPath=str((R/'consumer-context-proof.json').relative_to(ROOT)),dynamicPriorProofSha256=sha(R/'consumer-context-proof.json'),unboundCandidates=3,unboundLimits='Prior three candidates have no compiled consumer; no invented site or runtime acceptance.',inclusiveAndExclusiveDecisions={str(o):NOTES[o] for o in [2797,2806,2834]},householdTotalityDecision=NOTES[16128],runtime='not-run'))
    cutoff=datetime.now(timezone.utc).isoformat();telemetry=dict(input=None,cachedInput=None,output=None,reasoning=None,total=None,status='unknown; actual per-request telemetry not exposed',coordinatorAttribution='parent reports orchestration separately; no estimation',unmeasuredReportingTail='seal report and final response cannot measure themselves')
    limits=['Static editorial/context review only; no game launch, live runtime, font/layout/texture/image/package/release verification.','All34 full source/current-target pairs read;7835 unchanged clean prior independent decisions reused by exact full-pair and actual consumer identity.','All77 current retirees remain outside ordinary selectors; earlier accepted reentry remains active.','Only new review07 evidence written; root owns final acceptance/build/commit/integration.']
    verdict=dict(schemaVersion=1,reviewer=REVIEWER,model='GPT-6; exact model ID and reasoning setting not exposed',locale='fil',gameVersion='1.3.19',sourceLocale='ru',status='clean',objectiveFindings=0,findingOrdinals=[],freshFullPairsRead=34,freshAccepted=34,acceptedCorrections=2,resolvedReview06FindingOrdinals=[2834,16128],authorIndependentCredit=0,currentClosure=7869,exactPriorDecisionReuse=7835,closureAccepted=7869,mandatoryRegression=dict(total=7355,fresh=16,reuse=7339,freshAccepted=16,objectiveFindings=0,status='clean'),retirements=dict(stillRetired=77,new=0,priorStillRetired=77,reentered=0,historicalRows=78,previouslyAcceptedReentryRemainsActive=True),actualCompiledContext=dict(windowsRead=10,contextUnits=34,nodesPinned=9,instructionsPinned=94,retainedCoarseWindowsExact=120,dynamicConsumersApplicable=6,unboundCandidates=3),pinsUnchangedAtSeal=True,sourceAndGlossaryUnchanged=True,fullStructuralAndExactGate='sealed fresh16538/456 guard reused on exact unchanged pins; ordinary application gate reproduced byte-exact',historicalFullSemanticCoverage='preserved on pinned16538-unit identity; no full restart',firstPassProgressSha256=closure['firstPassProgressSha256'],cleanIndependentAcceptance=True,findingsPath=str((OUT/'findings.json').relative_to(ROOT)),nextAction='Root reconciles required evidence, final acceptance, delivery and canonical integration.',limits=limits,telemetry=telemetry,cutoffUtc=cutoff)
    write('final-verdict.json',verdict)
    report=OUT/'REPORT.md';assert not report.exists()
    report.write_text('# Filipino independent review 07\n\nNo, I’m not a Human v1.3.19 / fil / Russian source. Reviewer: '+REVIEWER+'.\n\n**Clean:** all 34 complete source/current-target pairs and their actual bounded branch context were independently read and accepted. Both cycle007 corrections resolve Review06 findings: ordinal2834 uses exclusive `kami` for the underground group, while the next actual line addresses the player upstairs; ordinal16128 restores all household tasks, retaining children, spouse and resentful coarse voice. Inclusive `tayo`/`atin` in the later proposed cooperation is contextually valid. Author reads receive zero independent credit. No objective findings or preference rewrites.\n\nOrdinary source selectors and pinned generation reproduce closure7,869 and exact fresh union34: corrected2, new21, current-minus-applicable23, explicit invalidations11, overlaps counted once. All7,835 unchanged clean prior full-pair/actual-consumer decisions retain exact provenance. Mandatory7,355 equals16 fresh accepted plus7,339 reuse. Review06 all421 accepted fresh targets stay exact;3 dependent decisions receive fresh review and418 remain reusable. Its two finding decisions carry no clean reuse credit.\n\nAll77 current retirees remain exact and outside every current component;0 reentries and0 new retirements. The historical78-row receipt’s earlier accepted reentry remains active and reusable. Source/glossary/program/decoder/selected mapping are unchanged. Full actual consumer sites, opcodes and operands were reconciled for all7,869 active rows and77 retirees. Duplicate Esenin keys retain distinct ChecksDialogs/Dialogs stable identities, with the current Dialogs row owning Yarn sites.\n\nAll73 actual selector examples and60 synthetic controls pass. Selectors enumerate from source with no generated-ID append. Ten fresh windows/34 text pairs were read;9 actual nodes/94 control instructions were pinned and reconciled.120 retained coarse windows stay exact. Six unchanged dynamic-consumer proofs retain applicability; three previously unbound candidates still have no compiled consumer and receive no runtime credit.\n\nSealed current cycle has42 files and1,392 external pins. The fresh complete16538-unit/456-input structural and exact gate is reused on verified unchanged dependencies; ordinary application/closure output is reproduced byte-exact. No optional unchanged probe or universal semantic restart was run. Each immutable evidence digest is cached before table loops; all current pins are rechecked once immediately before sealing.\n\nOnly new review07 evidence was written. Root owns final acceptance, builds and Git integration. Runtime, rendering, textures, installation, packaging and publication are not run. Actual input/cached-input/output/reasoning/total tokens and exact model reasoning setting are unknown because per-request telemetry is not exposed. Parent reports coordinator attribution; the reporting tail is unmeasured.\n')
    # One fresh unique-path pin check immediately before the immutable manifest seal.
    for path,h in pinmap.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h,path
    outFiles=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='completion-manifest.json']
    write('completion-manifest.json',dict(schemaVersion=1,locale='fil',reviewer=REVIEWER,status='sealed independent clean verdict',cutoffUtc=cutoff,files=outFiles,currentInputPins=checks,cycleCompletionManifestSha256=expected['completion-manifest.json'],finalVerdictSha256=sha(OUT/'final-verdict.json'),freshFullPairs=34,freshAccepted=34,objectiveFindings=0,closure=7869,closureAccepted=7869,reuse=7835,mandatory=7355,mandatoryFresh=16,mandatoryReuse=7339,retired=77,pinsRecheckedAtSeal=True,telemetry=telemetry,runtime='not-run',stopRule='Assigned required review complete; sealed clean review returned. No optional sweeps.'))
    print(json.dumps(dict(status='clean',fresh=34,accepted=34,findings=0,closure=7869,reuse=7835,mandatory=7355,retired=77,verdictSha256=sha(OUT/'final-verdict.json'),manifestSha256=sha(OUT/'completion-manifest.json'))))
if __name__=='__main__': main()
