import json, hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[3];H=R/'Translations/hi';D=Path(__file__).parent
j=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hs=lambda s:hashlib.sha256(s.encode()).hexdigest()
ih=lambda a:hs('\n'.join(a)+'\n')
def write(name,obj):
 p=D/name;assert not p.exists();p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
def write_lines(name,records):
 p=D/name;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records))
pins=j(D/'start-pins.json');assert all(sha(R/p)==digest for p,digest in pins.items())
manifest=j(H/'independent-review-03/final-artifact-manifest.json')
assert all(sha(R/f['path'])==f['sha256'] and (R/f['path']).stat().st_size==f['bytes'] for f in manifest['artifacts'])
c=j(H/'semantic-cycle-004-closure.json');delta=j(H/'semantic-cycle-004-review-delta.json');pairs=j(D/'delta-pairs.json');proof=j(D/'set-and-prior-applicability-proof.json');context=j(D/'actual-compiled-context.json')
notes={
 'line:entrance_mushroomeater_3_0a58437':'Ritual has no effect because of disorder within mycelium. Causal link, complete negation, elapsed ritual, speaker prefix and pauses retained; no extra ritual outcome asserted.',
 'line:MushroomEater_Entrance_2_4_0e89ef9':'They refers to mushrooms in the preceding compiled instruction. Plural mushrooms are merely part of mycelium; it does not transfer sentience to mushrooms or disclose another referent.',
 'line:MushroomEater_Entrance_2_3_07f08c5':'We cannot communicate with mushrooms directly because we are not part of mycelium. Plural participants, directness, negation and the cause remain exact in the ritual explanation.',
 'line:MushroomEater_Entrance_2_1_0778dd8':'Male MushroomEater learned the information from mycelium. Hindi indirect construction preserves acquisition and source agency without assigning another identity; following compiled line retains danger to it and all of us.',
 'line:Mushroom_end_2_039b8e9':'They points back to lumps of malice, not mushroom count. Increased accumulated amount causes the mushroom cap to cover the whole Earth. Hindi preserves plural antecedent, causal extent and future covering; no competing quantity reading changes the preceding size comparison.',
 'line:Mushroom_end_2_0bbb282':'Corrected full unit now says larger mushrooms. Russian nominative грибы and the compiled larger-mushrooms → more lumps-of-malice comparison support बड़े rather than ज़्यादा. Exact ASCII ellipsis retained; this is the only changed target field.',
 'line:Mushroom_end_2_0699a5b':'Mycelium must now dispose of/vent this malice somewhere. Hindi retains now, necessity, mycelium as agent and malice as object; it does not impose a new recipient or action by the player.',
 'line:Mushroom_end_2_02a5ab8':'Nothing will remain after the Earth-covering prediction. Complete negative universal and future consequence remain intact.',
 'line:Mushroom_end_2_0f27bf6':'More lumps of malice in mycelium correlates with the larger mushrooms in the immediately preceding compiled instruction. Hindi उतनी ही ज़्यादा गाँठें preserves quantity, term, plural agreement and correlating comparison; renewed changed-scene context is clean.'
}
fresh=[]
for p in pairs:
 fresh.append({**p,'fullRussianAndCurrentHindiRead':True,'compiledSceneInstructionContextRead':True,'glossarySha256':c['glossaryLayerSha256'],'compiledBindingSha256':c['compiledRuntimeBindingsSha256'],'result':'clean-no-objective-finding','findingIds':[],'reviewNote':notes[p['key']],'provenance':'fresh independent cycle004 exact-delta read by /root/hi_independent_review_04'})
assert len(fresh)==9 and [r['stableId'] for r in fresh]==delta['deltaIds']
write_lines('per-id-fresh-decisions.jsonl',fresh)
prev=lines(H/'independent-review-03/per-id-current-closure-decisions.jsonl');prior={r['stableId']:r for r in prev};new={r['stableId']:r for r in fresh}
current=[]
for row in c['reviewRows']:
 ss=row['stableId']
 if ss in new:decision={**new[ss],'reviewIndex':row['reviewIndex']}
 else:
  p=prior[ss];assert row['sourceSha256']==p['sourceSha256'] and row['targetSha256']==p['currentTargetSha256']
  decision={**p,'provenance':'exact applicable independent Review03 current-closure decision; no new full-read credit','priorDecisionArtifact':'Translations/hi/independent-review-03/per-id-current-closure-decisions.jsonl'}
 current.append(decision)
assert len(current)==5216
write_lines('per-id-current-closure-decisions.jsonl',current)
mandatory=lines(H/'independent-review-03/mandatory-catalog-per-id-decisions.jsonl');assert len(mandatory)==4805
for r in mandatory:r['provenance']='exact applicable independent Review03 mandatory-catalog decision; no new semantic-read credit';r['priorDecisionArtifact']='Translations/hi/independent-review-03/mandatory-catalog-per-id-decisions.jsonl'
write_lines('mandatory-catalog-per-id-decisions.jsonl',mandatory)
supp=lines(H/'independent-review-03/outside-delta-six-independent-decisions.jsonl');renewed=set(proof['supplementalRenewedContextIds'])
write('six-supplemental-applicability.json',{'allSixExactFullUnitSourceTargetGlossaryBindingMatch':True,'previousRecipeFindingResolvedByNormalPredicate':True,'rows':[{'stableId':r['stableId'],'sourceSha256':r['sourceSha256'],'targetSha256':r['currentTargetSha256'],'priorIndependentResult':r['result'],'fullUnitApplicability':'exact current','sceneContextApplicability':'changed scene freshly renewed in Review04' if r['stableId'] in renewed else 'unchanged context','newFreshDecisionArtifact':'Translations/hi/independent-review-04/per-id-fresh-decisions.jsonl'} for r in supp]})
all22=j(D/'all22-mycelium-pairs.json');context_pairs={r['stableId']:r for ins in context.values() for q in ins for r in q['pairs']}
write_lines('bounded-context-per-id-decisions.jsonl',[{**r,'result':'clean-no-objective-finding','findingIds':[],'fullRussianAndCurrentHindiRead':True,'compiledSceneInstructionContextRead':True,'countedInAssignedDelta':ss in new,'reviewNote':'Complete pair read in actual compiled node instruction order. Source facts, participants, ritual efficacy, negation, masculine speaker/player address, agency, mythic terminology and reveal state preserved.','glossarySha256':c['glossaryLayerSha256'],'compiledBindingSha256':c['compiledRuntimeBindingsSha256']} for ss,r in context_pairs.items()])
write('mycelium-family-regression.json',{'sourceUses':22,'actualSourceForms':proof['myceliumActualForms'],'normalPattern':c['myceliumInflectionPattern'],'all22MatchedNormalAndBroadStemPredicate':True,'all22InNormalGeneratedClosure':True,'ids':c['myceliumAcceptedSourceIds'],'idHashLfFinalNewline':ih(c['myceliumAcceptedSourceIds']),'all22CompletePairsDisplayedAndTermUsesRead':True,'all22UseApprovedTerm':'माइसीलियम','meaningAndTermPairFindings':0,'priorContextEvidence':{'applicableFullUnitIndependentDecisions':16,'sixPreviousSupplementalPairsExactCurrent':6,'changedEndingContextRenewedIds':proof['supplementalRenewedContextIds']},'selectorRegressionBoundary':'All accepted actual Russian source uses, including nominative, genitive, dative, prepositional and instrumental inflections; no claim about hypothetical unrepresented source forms.'})
tech=j(H/'independent-review-03/technical-supplier-and-label-proof.json');assert sha(R/tech['sourceContextPath'])==tech['sourceContextSha256']==c['technicalContextSha256']
write('technical-context-prior-applicability.json',{'proofPath':'Translations/hi/independent-review-03/technical-supplier-and-label-proof.json','proofSha256':sha(H/'independent-review-03/technical-supplier-and-label-proof.json'),'runtimeContextSha256':c['technicalContextSha256'],'compiledBindingSha256':c['compiledRuntimeBindingsSha256'],'allSourceTargetGlossaryContextInputsUnchanged':True,'supplierFragments':7,'rawUiSupplierLabels':17,'independentPriorLabelsExactApplicable':True,'technicalFragmentsCountedAsTranslated':False,'limits':tech['classification']})
write('normal-selector-verification.json',{'command':'.venv/bin/python Translations/hi/build-semantic-cycle-004-closure.py --verify','exitCode':0,'output':'verified 5216 closure; 9 delta; 9 new; 0 invalidated; 0 retired','independentSetAndCompiledSceneReproduction':'set-and-prior-applicability-proof.json','structuralGateSha256':sha(H/'semantic-cycle-004-structural-gate.json'),'wholeCorpusReceiptSha256':sha(H/'semantic-cycle-004-full-corpus.json'),'staticAndCommonRecipes':'normal selector verification also reproduces 178 static rows and authored common-option recipes 2593/245/45; whole-corpus receipt remains exactly applicable'})
usage={'reviewer':'/root/hi_independent_review_04','model':None,'reasoning':None,'inputTokens':None,'cachedInputTokens':None,'outputTokens':None,'reasoningTokens':None,'totalTokens':None,'reason':'Parent collects actual completed-session telemetry and model identity after this reviewer returns. Unknown at immutable cutoff, not zero. Cached input and reasoning are subsets.','coordinator':'Parent reports orchestration separately. Final reporting tail and platform overhead unmeasured.','descendants':0}
limits=j(H/'semantic-cycle-004-author-handoff.json')['limits']
coverage={'status':'clean independent static cycle004 delta and closure acceptance','locale':'hi','gameVersion':'1.3.19','fullSemanticCorpusCoveragePreserved':16538,'freshAssignedFullPairs':9,'currentClosureCount':5216,'exactPriorApplicableClosureDecisions':5207,'mandatoryRequired':4805,'mandatoryFreshThisDelta':0,'mandatoryExactPriorApplicable':4805,'missingMandatoryIds':[],'correctedFullUnitsPassed':1,'consolidatedTextFindings':0,'consolidatedRecipeFindings':0,'exactDeltaFormulaVerified':True,'newDependencies':9,'explicitInvalidatedPrior':0,'retired':0,'all22MyceliumNormalPredicateReconciled':True,'sixSupplementalFullUnitApplicabilityVerified':True,'renewedSupplementalSceneContext':2,'boundedCompiledNodeCount':len(context),'boundedContextFullPairsRead':len(context_pairs),'boundedContextAssignedOverlap':len(set(context_pairs)&set(new)),'myceliumFullPairTermRead':len(all22),'additionalPairReadsNoExtraAcceptanceCoverage':len(set(context_pairs)|{r['stableId'] for r in all22})-9,'wholeCorpusGateRows':16538,'wholeCorpusGateMode':'reuse immutable fresh cycle004 receipt on exact source/authored/code hashes','cleanIndependentAcceptance':True,'rootFinalAcceptance':'pending','runtimeVisualBuildRelease':'not-run','usage':usage,'limits':limits}
write('final-coverage-and-regression-proof.json',coverage)
write('consolidated-full-unit-findings.json',{'schemaVersion':1,'locale':'hi','reviewer':'/root/hi_independent_review_04','cycle':4,'status':'clean','textFindings':[],'recipeFindings':[],'priorFindingsResolved':['HI-R03-SEM-001','HI-R03-DEP-001'],'closureSha256':sha(H/'semantic-cycle-004-closure.json'),'deltaSha256':sha(H/'semantic-cycle-004-review-delta.json')})
assert all(sha(R/p)==digest for p,digest in pins.items())
write('final-unchanged-input-pins.json',{'allStartPinsUnchanged':True,'pinCount':len(pins),'pins':pins,'note':'Review04 only writes its new evidence directory. The one authored correction and operational checkpoint update occurred before start pins. Exact old/current author hashes are reconciled separately.'})
report=f'''# Hindi independent Review04 — cycle004

Verdict: **clean independent static delta and dependency review**. All nine complete Russian/Hindi pairs pass in their actual compiled scenes. No new text or selector findings. Root owns final editorial acceptance and canonical integration; this report does not establish game/runtime or release readiness.

The full correction `line:Mushroom_end_2_0bbb282` now reads `और मशरूम जितने बड़े...`. Russian nominative `грибы` and the compiled sequence compare mushroom size; the following `Тем больше комков злобы в мицелии.` compares the number of malice lumps. Both meanings remain distinct in Hindi. All five ending units, including the two supplemental neighbors, received fresh compiled-context judgment. Exact before/after comparison verifies one target field changed and all other 16,537 accepted targets remain unchanged.

The ordinary closure reproduces exactly: 5,216 IDs, composed of 5,207 exact applicable prior independent decisions and nine freshly read delta IDs. The formula is one corrected ID union nine new dependencies union zero explicitly invalidated prior IDs; the correction already belongs to the new set, yielding nine unique IDs. No prior dependency retired. Closure LF-final-newline ID hash: `{c['closureIdListSha256LfFinalNewline']}`. Delta hash: `{delta['deltaIdListSha256LfFinalNewline']}`.

The normal mycelium predicate matches all 22 actual accepted source uses, independently reconciled against a broader source stem search and the canonical inventory. Observed forms include мицелий, мицелия, мицелию, мицелии and мицелием. All 22 complete pairs preserve the approved माइसीलियम term. The six prior supplemental full-unit decisions match exact source/target/glossary/binding hashes; four retain unchanged context and two have freshly renewed ending context. The prior source-predicate omission is resolved in the normal recipe rather than only in its generated list.

All 4,805 mandatory catalog IDs have exact current independent per-ID decisions; zero are missing and no fresh catalog reread is claimed. All 5,207 prior closure decisions are current. The 705 Review03 pins reconcile as 703 unchanged inputs, one target-file correction, and one operational checkpoint update before review. Review03's 26 sealed artifact hashes were verified. Current start pins remain unchanged. Source inventory, glossary, preserve-exact manifest, stable-ID mapping and compiled runtime bindings remain pinned; no full-restart condition is present.

The nine assigned pairs and {len(context_pairs)} complete pairs across five actual compiled nodes were read in instruction order, including options and calls. Additional all-22 term-pair reads are bounded checks; they do not enlarge assigned delta or corpus acceptance coverage. These reads preserve negation, quantities, agency, speaker/player agreement, ritual outcome, degree of certainty and reveal state. Seven technical supplier fragments and 17 UI labels retain exact applicable independent evidence; technical fragments are not translation IDs.

`.venv/bin/python Translations/hi/build-semantic-cycle-004-closure.py --verify` passed. Its static and common-option recipes reproduced 178 static rows and 2,593/245/45 option rows. The fresh immutable cycle004 whole-corpus guard is reused after exact verification of all 335 authored file hashes, both source inventory hashes, shared validator/input loader and owning validator code. It covers 16,538 units with zero selected-ID, structural or protected-span failures. No repeated parse pool, all-locale scan, build or game launch was performed.

Limits remain explicit: accepted Widow/Cultist duplicate keys lack exact compiled references; Theorist acronym adaptation has no proven defect; plain psychic-service fields have unproved visible use; captured default occupants do not establish every reachable state. No fonts, shaping, wrapping, textures, images, installation, publication or runtime/visual test receives passed credit.

Evidence: `per-id-fresh-decisions.jsonl`, `per-id-current-closure-decisions.jsonl`, `mandatory-catalog-per-id-decisions.jsonl`, `actual-compiled-context.json`, `bounded-context-per-id-decisions.jsonl`, `set-and-prior-applicability-proof.json`, `six-supplemental-applicability.json`, `mycelium-family-regression.json`, `one-full-unit-correction-proof.json`, `whole-corpus-receipt-applicability.json`, `final-coverage-and-regression-proof.json` and `final-unchanged-input-pins.json`. `final-artifact-manifest.json` seals every Review04 artifact except itself. ID hashes use LF with final newline.

Reviewer: `/root/hi_independent_review_04`, no descendants. Actual model/reasoning and input, cached input, output, reasoning and total token telemetry are unknown at this immutable cutoff; parent collects completed-session measurements and coordinator attribution. They are not zero, and subsets must not be added twice. Reporting tail and platform overhead are unmeasured.
'''
p=D/'final-report.md';assert not p.exists();p.write_text(report)
files=[{'path':str(p.relative_to(R)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(D.iterdir()) if p.is_file()]
write('final-artifact-manifest.json',{'schemaVersion':1,'locale':'hi','reviewer':'/root/hi_independent_review_04','status':'immutable clean Review04; root final editorial acceptance pending','authoritativeReport':'final-report.md','authoritativeFindings':'consolidated-full-unit-findings.json','authoritativeCoverage':'final-coverage-and-regression-proof.json','artifactCount':len(files),'artifacts':files,'manifestSelfHashExcluded':True})
print('Sealed clean Review04:',len(files),'artifacts;',len(pins),'unchanged start pins;',len(context_pairs),'compiled-context pairs')
