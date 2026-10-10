#!/usr/bin/env python3
"""Seal the independent cycle006 review; writes only new review06 evidence."""
import hashlib, importlib.util, json, sys
from datetime import datetime, timezone
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
C = ROOT / 'Translations/fil/semantic-correction-cycle-006'
R = ROOT / 'Translations/fil/independent-review-05'
REVIEWER = '/root/fil_independent_review_06'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(s): return hashlib.sha256(s.encode()).hexdigest()
def load(p): return json.loads(p.read_text())
def rows(p): return [json.loads(x) for x in p.read_text().splitlines()]
def write(name, value):
    p = OUT / name
    assert not p.exists(), name
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
def jl(name, values):
    p = OUT / name
    assert not p.exists(), name
    p.write_text(''.join(json.dumps(v, ensure_ascii=False, separators=(',', ':')) + '\n' for v in values))
def main():
    expected = {'handoff.json':'a2486ad7be464fd7c64e2f47a75014ce1b30d0e37b16c91903d11ed163edeac7',
        'completion-manifest.json':'e904a586a40f3972be27d2dbbe1c1f1cf97b3b33adb56d8ae1fffae20e3fdad7',
        'next-delta-paired.jsonl':'717310d1e947e6cebe439a91e82277d29240fb74bb01fd6914eea26adc08cfc8',
        'closure.json':'24a1e0f8629f55b31d601c1b722c127d2eb34247f7d10c0ab1e9b9e85500124c'}
    for name,h in expected.items(): assert sha(C/name) == h
    manifest=load(C/'completion-manifest.json')
    pins=manifest['files']+manifest['currentExternalPins']
    checks=[]
    for p in pins:
        assert sha(ROOT/p['path'])==p['sha256'],p['path']
        checks.append(dict(path=p['path'],sha256=p['sha256'],result='exact'))
    assert sha(R/'completion-manifest.json')=='670f0c2d0932d0aba8d09abc33a642bcc52016da430f454a5c8e2f7217d4cc3b'
    assert sha(R/'final-verdict.json')=='4146376b871a2bd51fcde27577c5763dc12d6f22e405ba3eb95a71bfec5c75f4'
    assert (OUT/'full-corpus-validation.json').read_bytes()==(C/'full-corpus-validation.json').read_bytes()
    sys.path.insert(0,str(C))
    import build_closure
    reproduced, files=build_closure.build()
    for name, raw in files.items(): assert (C/name).read_bytes()==raw,name
    closure=load(C/'closure.json'); pairs=rows(C/'closure-paired.jsonl'); fresh=rows(C/'next-delta-paired.jsonl')
    priorPairs={x['stableId']:x for x in rows(ROOT/'Translations/fil/semantic-correction-cycle-005/closure-paired.jsonl')}
    priorDec={x['stableId']:x for x in rows(R/'closure-decision-applicability.jsonl')}
    prev=set(priorPairs); cur={x['stableId'] for x in pairs}; changed=set(closure['corrected']['ids'])
    delta={x['stableId'] for x in fresh}; invalid=set(closure['explicitlyInvalidatedPriorEvidence']['ids'])
    reuse=cur-delta; applicable=set()
    current={x['stableId']:x for x in pairs}
    topology=load(C/'current-bounded-consumers.json')
    decoder=ROOT/'Translations/fil/independent-review-04/bytecode_decoder.py'
    ds=importlib.util.spec_from_file_location('review06_decoder',decoder);dec=importlib.util.module_from_spec(ds);ds.loader.exec_module(dec)
    assert hashlib.sha256(dec.raw).hexdigest()==closure['compiledProgramSha256']
    # Reconcile the accepted collection/row, not a bare key shared by historical tables.
    # The canonical selected source preserves ChecksDialogs and Dialogs as distinct IDs.
    # Yarn's active by-key owner is the current Dialogs row, as in the pinned recipe.
    acceptedSourceIds=set()
    collectionGuids={'UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1'}
    for f in load(C/'full-corpus-validation.json')['authoredFiles']:
        doc=load(ROOT/f['path'])
        for e in doc['entries']:
            acceptedSourceIds.add(e['stableId'] if 'stableId' in e else f"string:{collectionGuids[doc['collection']]}:{e['id']}")
    sourceRows=[r for r in rows(ROOT/'Source/localization-inventory-v3/strings.jsonl') if r['stableId'] in acceptedSourceIds]
    byKey={r['key']:r['stableId'] for r in sourceRows}
    def sitesFor(p):return actualSites.get(p['key'],[]) if byKey.get(p['key'])==p['stableId'] else []
    # The decoder stores node names as mapping keys; independently reconcile full site operands.
    actualSites={}
    for name,node in dec.actual.items():
        for i in node['instructions']:
            if i['op'] in ['RunLine','AddOption']:
                actualSites.setdefault(i['operands'][0],[]).append(dict(node=name,instruction=i['index'],opcode=i['op'],operands=i['operands']))
    for p in pairs:
        assert digest(p['source'])==p['sourceSha256'] and digest(p['target'])==p['targetSha256']
        assert p['consumerIdentity']['sites']==sitesFor(p)
        if p['stableId'] in priorPairs:
            old=priorPairs[p['stableId']];d=priorDec[p['stableId']]
            assert (p['sourceSha256'],p['key'],p['nodeNames'])==(old['sourceSha256'],old['key'],old['nodeNames'])
            if p['targetSha256']==old['targetSha256'] and d['decision']!='objective-correction-required' and d['findingId'] is None:applicable.add(p['stableId'])
    assert len(cur)==7848 and len(delta)==423 and len(reuse)==7425
    assert delta==changed|(cur-applicable)|invalid and len(cur-applicable)==219 and len(invalid)==204 and len(cur-prev)==195
    assert changed<=delta and len(changed)==56
    assert all(s in applicable for s in reuse)
    for w in topology['windows']:
        for i in w['windowInstructions']:
            actual=dec.actual[w['node']]['instructions'][i['index']]
            assert i['op']==actual['op'] and i['operands']==actual['operands']
            if i['sourceStableId']:
                p=current[i['sourceStableId']]
                assert i['source']==p['source'] and i['target']==p['target'] and i['sourceStableId'] in delta
    assert len(topology['windows'])==122
    plan=load(C/'plan.json');assert len(plan['rows'])==56
    for r in plan['rows']:assert current[r['stableId']]['target']==r['acceptedFullTarget'] and current[r['stableId']]['source']==r['source']
    findings=[]
    for ordinal,reason,proposal,context in [
      (2834,'Inclusive tayo includes the addressee in the duration of the underground stay. The next actual RunLine places the addressee upstairs (там, наверху), while the speaker and his companion are down here. Preserve the exclusive group with kami.',
       'Miner: Makinig ka, kakaiba ang daloy ng oras dito. Walang araw o orasan. Kaya malay natin kung gaano na kami katagal dito.',
       dict(node='Miner_Entrance_2_1',instruction=1,nextInstruction=2,nextSource='Miner: Ты хоть поешь там, наверху, а то, глядишь, сам скоро, как я, с фонарём засядешь. А жратвы-то здесь нет нифига.',glossaryId='miner')),
      (16128,'The source says she performed all work around the house (всё по дому делала). Ipinanglinis ng bahay specifies only cleaning, omitting the breadth of her household work. Preserve all household tasks rather than replacing the whole category with one task.',
       'Mother: Mga kamay… Ipinangyakap ko ang mga ito sa mga anak ko, ginamit sa lahat ng gawain sa bahay, at ipinanghaplos sa asawa ko. Pero alam mo? Wala pa ring putanginang nagpapahalaga.',
       dict(node='Mother_Hands_DontShoot',instruction=1,sourcePhrase='всё по дому делала',targetPhrase='ipinanglinis ng bahay',glossaryId='mother-with-child'))]:
        p=next(x for x in fresh if x['acceptedOrdinal']==ordinal)
        findings.append(dict(findingId=f'fil-review06-{ordinal}',acceptedOrdinal=ordinal,stableId=p['stableId'],source=p['source'],target=p['target'],sourceSha256=p['sourceSha256'],targetSha256=p['targetSha256'],consumerIdentitySha256=p['consumerIdentitySha256'],reason=reason,proposedFullTarget=proposal,context=context,objective=True,authorEditApplied=False))
    byFinding={r['stableId']:r for r in findings}
    notes={479:'Irritated why-question and wish for peace retained with mild Bwisit; no new action.',487:'Father indifference and rules preserved; putsa supplies mild coarse register.',700:'Wife remains third-person subject and her own children remain objects of neglect.',1528:'Dismissive indifference preserved through colloquial pake.',1773:'Inability to contact friends and sudden problems for each retained; kagaguhan matches coarse noun.',1780:'Temporary shelter request and absent/evicted/other alternatives retained.',1888:'Sweaters/jackets and dismissive indifference remain; mild bwisit.',1889:'Heat, fraer address and uncertainty about others remain; mild putsa.',1926:'Direct boring-person rebuke and dismissive coarse noun preserved.',1936:'Failure to understand and refusal of this arrangement retained.',2679:'Believed dead then found him themselves after a few days; daughter with shotgun arrives first; rough contradiction preserved.',3510:'Social norms and other nonsense no longer function; source coarse category retained.',4038:'Dismissive resignation retained, no new decision.',5325:'Bad situation, address, cough and exhaustion retained; mild coarse register.',5843:'Truth-versus-nonsense uncertainty remains attributed to Intruder.',5861:'Dismissive coarse assessment of affirmation alternative preserved.',5865:'Exact repeated coarse alternative matches corresponding branch.',6056:'Debt explanation and proposed monthly mortgage deduction preserved; coarse disapproval retained.',6098:'Dismissal of interlocutor story preserved; colloquial pake.',6103:'Exact repeated dismissal retained on its separate branch.',6295:'Debt-collector trouble precedes seeking friends help; coarse event label retained.',6380:'Contrast between nonsense and safety preserved as player alternative.',6518:'Other fools, pointless sweaters/jackets in heat and gets-you address remain; bwisit retains irritation.',6545:'Coarse rhetorical question about everyone wearing clothes in heat retained; exact repetition matches6555.',6555:'Review05 objective voice finding resolved with Bwisit; all facts and ellipsis retained, no prior clean credit assigned.',7025:'Emphatic repudiation of mere myth and Committee longstanding knowledge remain in Jacob speech.',8609:'Full-force paternal beating and mothers indifference remain separate actions; no gender or agency transfer.',8919:'Private-room TV and total lack of films retained with comic diminutive equivalent lintik.',9091:'Sugar-free disbelief and coarse dismissiveness retained.',9128:'Former cigar preference, present scarcity and interrupted minister callback retained.',9262:'Counterfactual beer/football companionship and interrupted introduction retained; source family warmth plus roughness.',9772:'Unbound standalone coarse assessment retained; no compiled site invented.',11134:'Resigned consent to one photograph remains, no shooting action.',11578:'Resignation to peeling hands retained; source idiom rendered as bahala na with mild putsa.',11721:'Fraer address, gun-drawing objection and command to put it away retained; mild source curse rather than added threat.',11954:'Dismissive rhetorical indifference remains before tongue sign reveal.',12842:'Without-glasses difficulty or complete blindness remain alternatives, not confirmed diagnosis.',12947:'Irritated question connects dirt under nails to alleged Visitor status; no new certainty.',13005:'Fathers deed and family paying its cost remain; homeless/poor/no-peace list complete.',14031:'Resigned dismissal retains emotion and mild coarse marker.',14053:'Next-time shooting instruction, refusal to beg and indifference complete.',14059:'Indifference retains gun scene context; no new action.',14076:'Manong address, exhaustion and indifference retained.',14615:'Dismissive source event assessment retained; surrounding separate branches preserved.',14631:'Armpit problem and rhetorical everyone-has-problems defense retained.',14663:'Resigned cooperation and satisfied-you question retained.',14664:'Denied drunk allegation and interrupted alcohol fragment retained, no completion invented.',14665:'Parallel full denial retained as alternate branch.',14682:'Rude butt-showing rhetorical question and contempt for checks retained.',14883:'Committee photography on arrival for records retains timing and attribution.',14929:'Astonished armpit-check complaint retains coarse colloquial reaction, no new medical fact.',14954:'Concealment joke and damned bad luck remain; no confession invented.',16039:'Prior nervousness explanation remains speaker belief, not diagnosis.',16045:'No surviving grandmother photograph and her dislike remain.',16095:'Actual instruction0 is followed by ShowSign Anger AURAPHOTO; gawin mo na correctly authorizes photograph, with mild putsa, and adds no firearm.',16187:'Possibility that previous signs are nonsense remains uncertain, not asserted.'}
    assert set(notes)=={r['acceptedOrdinal'] for r in plan['rows']}
    freshDecisions=[]
    for p in fresh:
        finding=byFinding.get(p['stableId'])
        reason=notes.get(p['acceptedOrdinal'],'Full source/current-target unit independently read with actual applicable scene/branch context; meaning, participant roles, chronology, modality, glossary facts and source-specific voice remain acceptable. Equivalent wording is not a defect.')
        if finding:reason=finding['reason']
        freshDecisions.append(dict(p,reviewer=REVIEWER,decision='objective-correction-required' if finding else 'accepted-independent-reviewed-unit',findingId=finding['findingId'] if finding else None,evidenceMode='fresh-full-source-current-target-and-actual-context-read',reason=reason,authorIndependentCredit=0))
    jl('fresh-decisions.jsonl',freshDecisions)
    write('findings.json',dict(reviewer=REVIEWER,status='notclean',completeAssignedPass=True,freshFullPairsRead=423,objectiveFindings=findings,preferenceAlternativesAreNotDefects=True,dismissedConcerns=[dict(ordinal=14033,reason='In the actual scene about parents piercing infants ears without their decision, Russian не нужно can express unwanted intervention. Ayaw preserves the consent concern; a literal need-versus-want rewrite is not required.'),dict(ordinal=6557,reason='Matinding problema is an acceptable contextual interpretation of the intense situation, not an independently supported reason to rewrite.'),dict(surface='coarse-register distribution',reason='Coarse idioms are judged over complete utterances. Colloquial pake, malay, nilalaklak and semantic abuse verbs may carry roughness without mapping each Russian root to a new swear; avoid generic-swear or strength quotas. All56 actual corrections retain source-specific content and use mild markers where the source is mild.')]))
    correctionDecisions=[next(d for d in freshDecisions if d['stableId']==r['stableId']) for r in plan['rows']]
    write('applied-correction-decisions.json',dict(count=56,accepted=56,rejected=0,experiencedAccepted=6,review05Finding6555Resolved=True,photoActionResolved=True,fullUnitDecisions=correctionDecisions))
    closureDecisions=[]
    byFresh={d['stableId']:d for d in freshDecisions}
    for p in pairs:
        if p['stableId'] in byFresh:d=byFresh[p['stableId']];decision=d['decision'];finding=d['findingId'];reason=d['reason'];mode='fresh-independent-full-pair'
        else:decision='exact-prior-independent-decision-reused';finding=None;reason='Exact unchanged full source/target plus original key/node and rederived actual compiled sites/opcodes/operands; outside explicit invalidation.';mode='prior-independent-reuse'
        closureDecisions.append(dict(stableId=p['stableId'],acceptedOrdinal=p['acceptedOrdinal'],sourceSha256=p['sourceSha256'],targetSha256=p['targetSha256'],key=p['key'],nodeNames=p['nodeNames'],consumerIdentitySha256=p['consumerIdentitySha256'],components=p['components'],decision=decision,findingId=finding,evidenceMode=mode,reason=reason,priorEvidenceSha256=sha(R/'closure-decision-applicability.jsonl') if mode=='prior-independent-reuse' else None))
    jl('closure-decision-applicability.jsonl',closureDecisions)
    mandatory=rows(C/'mandatory-regression-catalog.jsonl');mandatoryIds={r['stableId'] for r in mandatory}
    assert len(mandatory)==7349 and len(mandatoryIds&delta)==273 and len(mandatoryIds&reuse)==7076
    mandatoryDec=[dict(d,catalogSha256=sha(C/'mandatory-regression-catalog.jsonl')) for d in closureDecisions if d['stableId'] in mandatoryIds]
    jl('mandatory-regression-applicability.jsonl',mandatoryDec)
    retirees=rows(C/'retired-applicability.jsonl');retired=[]
    for r in retirees:
        if r['currentComponents']:
            assert r['stableId'] in delta
            d=byFresh[r['stableId']]
            retired.append(dict(r,reviewer=REVIEWER,independentResult=d['decision'],findingId=d['findingId'],freshDecisionSha256=sha(OUT/'fresh-decisions.jsonl')))
        else:
            assert r['stableId'] not in cur and r['currentTargetExact'] and r['priorCleanDecision']
            assert r['consumerIdentity']['sites']==sitesFor(r)
            retired.append(dict(r,reviewer=REVIEWER,independentResult='retirement-applicable; unchanged prior clean full-pair and actual consumer evidence verified',independentNewReadCredit=0))
    assert len(retired)==78 and sum(not r['currentComponents'] for r in retired)==77
    jl('retired-final-applicability.jsonl',retired)
    spec=load(C/'selector-specification.json');from source_predicates import source_matches
    controls=[]
    for t in spec['regressionExamples']:
        assert source_matches(t['expectedSelector'],spec['mandatorySourceRegex'][t['expectedSelector']],t['source'],spec)
        controls.append(dict(t,actual=True,result='passed'))
    for t in spec['syntheticSelectorRegressions']:
        observed=source_matches(t['selector'],spec['mandatorySourceRegex'][t['selector']],t['source'],spec)
        assert observed==t['mustMatch'];controls.append(dict(t,observed=observed,actual=False,result='passed'))
    assert len(controls)==111
    write('selector-controls.json',dict(actual=63,synthetic=48,passed=111,generatedIdAppend=False,closureReproducedBytes=True,controls=controls))
    write('input-verification.json',dict(cycleExpectedHashes=expected,cycleFiles=len(manifest['files']),externalPins=len(manifest['currentExternalPins']),pinChecks=checks,review05ManifestSha256=sha(R/'completion-manifest.json'),review05VerdictSha256=sha(R/'final-verdict.json'),freshCorpusReceiptExact=True,reviewer=REVIEWER))
    write('dependency-proof.json',dict(closureSha256=sha(C/'closure.json'),acceptedOrderSha256=closure['acceptedOrderSha256'],currentClosure=7848,previousClosure=7678,corrected=closure['corrected'],currentMinusPrevious=closure['newCurrentMinusPrevious'],currentMinusExactApplicablePrior=closure['currentMinusExactApplicablePrior'],explicitInvalidations=closure['explicitlyInvalidatedPriorEvidence'],exactFresh=closure['exactNextDelta'],exactReuse=closure['reusableUnchangedIndependentPairs'],formula='corrected union(currentClosure minus exact applicable prior full-pair and actual consumer decisions) union explicit invalidations',setFormulaIndependentlyReconciled=True,ordinaryRecipeOutputsByteExact=True,mandatory=dict(total=7349,fresh=273,reuse=7076,findings=[2834,16128]),retirement=dict(stillRetired=77,new=25,previous53StillRetired=52,previous53Reentered=1,reenteredFreshAccepted=True,receiptRows=78),Review05Fresh140Accounting=load(C/'handoff.json')['Review05Fresh140Accounting'],Review05Finding6555Reuse=False,accepted9614Unchanged=next(p for p in pairs if p['acceptedOrdinal']==9614)['targetSha256']==priorPairs[next(p for p in pairs if p['acceptedOrdinal']==9614)['stableId']]['targetSha256'],sourceGlossaryBindingsUnchanged=True,fullRestart=False,fullRestartReason='Source/inventory/glossary, stable mapping, parser, runtime binding and prior complete coverage pins remain exact. Findings are bounded unchanged context rows, not an unbounded affected family.',limits='Deterministic proof and retained semantic evidence are not a new full16538 model reread.'))
    contextIds={i['sourceStableId'] for w in topology['windows'] for i in w['windowInstructions'] if i['sourceStableId']}
    assert len(contextIds)==420 and contextIds<=delta
    write('consumer-context-proof.json',dict(consumerFileSha256=sha(C/'current-bounded-consumers.json'),compiledProgramSha256=closure['compiledProgramSha256'],decoderSha256=sha(decoder),windowsRead=122,actualTextContextUnitsRead=420,fullControlTopologyNodesPinned=110,fullControlTopologyInstructionsPinned=2002,allWindowOpcodesOperandsIndependentlyReconciled=True,actualFullPairConsumersIndependentlyReconciled=7848,dynamicConsumersExact=6,unboundCandidates=3,photoAction=dict(node='Anger_Photo',instruction=0,nextCommand='ShowSign Anger AURAPHOTO',decision='accepted; photograph action, no gun'),additionalFindingContext=dict(Miner_Entrance_2_1=dec.actual['Miner_Entrance_2_1'],BigLebowski_Ears_DontShoot=dec.actual['BigLebowski_Ears_DontShoot']),runtime='not-run'))
    cutoff=datetime.now(timezone.utc).isoformat()
    telemetry=dict(input=None,cachedInput=None,output=None,reasoning=None,total=None,status='unknown; actual per-request telemetry not exposed',coordinatorAttribution='parent reports orchestration separately; no estimation',unmeasuredReportingTail='seal report and final response cannot measure themselves')
    verdict=dict(schemaVersion=1,reviewer=REVIEWER,model='GPT-6; exact model ID and reasoning setting not exposed',locale='fil',gameVersion='1.3.19',sourceLocale='ru',status='notclean',objectiveFindings=2,findingOrdinals=[2834,16128],freshFullPairsRead=423,freshAccepted=421,acceptedCorrections=56,experiencedCorrectionsAccepted=6,review05Finding6555Resolved=True,authorIndependentCredit=0,currentClosure=7848,exactPriorDecisionReuse=7425,closureAccepted=7846,mandatoryRegression=dict(total=7349,fresh=273,reuse=7076,freshAccepted=271,objectiveFindings=2,status='notclean'),retirements=dict(stillRetired=77,new=25,priorStillRetired=52,reenteredFreshAccepted=1),actualCompiledContext=dict(windowsRead=122,contextUnits=420,nodesPinned=110,instructionsPinned=2002,dynamicConsumersApplicable=6,unboundCandidates=3),pinsUnchangedAtSeal=True,sourceAndGlossaryUnchanged=True,fullStructuralAndExactGate='passed16538/456; independently rerun receipt exact to author',historicalFullSemanticCoverage='preserved on pinned16538-unit identity; no full restart',cleanIndependentAcceptance=False,findingsPath='Translations/fil/independent-review-06/findings.json',nextAction='Root adjudicates both consolidated context findings; author applies any accepted complete replacements together and produces one exact subsequent delta. Root owns acceptance/build/integration.',limits=['Static editorial/context review only; no game launch, live runtime, font/layout/texture/image/package/release verification.','All423 full pairs read;7425 unchanged independent decisions reused by exact source/target and actual consumer identity.','All56 corrections accepted; two objective findings are older context rows, consolidated in this verdict.','No authored/localization/glossary/shared helper/Git/index/commit/other locale/publication edits; no further agents.'],telemetry=telemetry,cutoffUtc=cutoff)
    write('final-verdict.json',verdict)
    report=OUT/'REPORT.md';assert not report.exists()
    report.write_text('# Filipino independent review 06\n\nNo, I’m not a Human v1.3.19 / fil / Russian source. Reviewer: '+REVIEWER+'.\n\n**Not clean:** all423 full source/current-target pairs were read;421 accepted,2 objective findings (2834 and16128). All56 cycle006 full replacements are accepted, including six Experienced units,6555 with exact repetition, and the Anger photograph action. Author125 readings receive zero independent credit.\n\nThe miner’s exclusive underground group becomes inclusive `tayo`, contradicting the next actual line addressing the player upstairs. Mother’s all-household-work claim becomes cleaning only. See `findings.json` for complete source/current target, proposed full replacements, exact hashes and actual context. Ear-piercing need/want wording was adjudicated as a valid consent-context rendering rather than a preference defect.\n\nThe ordinary selector reproduces the complete closure7848 and exact union423:56 corrected,219 current-minus-exact-applicable-prior and204 explicitly invalidated, with overlaps counted once.7425 unchanged full pairs and actual consumers retain independent decisions. Mandatory7349 equals273 fresh plus7076 reuse;271 fresh accepted and2 findings. Retirement proof reconciles25 new plus52 prior still-retired rows, and one fresh-accepted reentry. The78-row receipt includes that reentry;77 remain retired.\n\nAll63 actual and48 synthetic selector controls pass, including literal horseradish and unrelated-word negatives. No generated ID append. Current source/glossary/original program/decoder/mapping pins remain exact.122 actual bounded windows/420 text context rows were read;110 nodes/2002 control instructions are pinned, not claimed as a new full semantic read. Six dynamic consumers retain exact evidence; three candidates have no compiled consumer and receive none. Review05 all141-read/140-accepted history is preserved;6555 gains this fresh decision rather than reuse, and9614 stays unchanged.\n\nCycle seal, exact application/41 batches and ordinary closure were rerun. Fresh structural/exact full-corpus gate passed16538 units/456 inputs and produced bytes identical to the sealed author receipt. The initial additional decoder probe under system Python lacked dnfile; the project .venv probe succeeded. This environment mismatch caused no mutation and is not a product failure.\n\nOnly new review06 evidence was written. Root owns adjudication, acceptance, builds and canonical integration. Runtime, rendering, textures, packaging and release are not run. Actual input/cached-input/output/reasoning/total tokens are unknown; no per-request telemetry is exposed. Parent orchestration is separately accountable; report/final tail remains unmeasured.\n')
    # Recheck all current input pins immediately before sealing.
    for p in pins:assert sha(ROOT/p['path'])==p['sha256'],p['path']
    outFiles=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='completion-manifest.json']
    write('completion-manifest.json',dict(schemaVersion=1,locale='fil',reviewer=REVIEWER,status='sealed independent notclean verdict',cutoffUtc=cutoff,files=outFiles,currentInputPins=checks,cycleCompletionManifestSha256=expected['completion-manifest.json'],finalVerdictSha256=sha(OUT/'final-verdict.json'),freshFullPairs=423,freshAccepted=421,objectiveFindings=2,closure=7848,reuse=7425,mandatory=7349,retired=77,pinsRecheckedAtSeal=True,telemetry=telemetry,runtime='not-run',stopRule='Assigned required review complete; seal and return consolidated findings. No optional sweeps.'))
    print(json.dumps(dict(status='notclean',fresh=423,accepted=421,findings=2,verdictSha256=sha(OUT/'final-verdict.json'),manifestSha256=sha(OUT/'completion-manifest.json'))))
if __name__=='__main__':main()
