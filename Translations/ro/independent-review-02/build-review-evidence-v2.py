# Recovery v2: static TMP source inventory has stableId/source, no table key.
# Preserve the earlier failed script and the already verified recipe artifact.
"""Deterministic evidence construction after the independent model's full pair reads.

Writes only this new review directory. It does not perform semantic review or
apply translations. Replacement wording below was authored by the reviewer.
"""
from pathlib import Path
import json, hashlib, importlib.util, collections, copy
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LOCALE = ROOT / 'Translations/ro'
CLOSURE = LOCALE / 'remedial-cycle-002-closure-v2'

def read(path):
    return json.loads(Path(path).read_text())
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def text_sha(value):
    return hashlib.sha256(value.encode()).hexdigest()
def write(name, value):
    path = OUT / name
    payload=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    if path.exists():
        assert path.read_text()==payload, path
        return
    path.write_text(payload)
def jsonl(name, rows):
    path = OUT/name
    assert not path.exists(), path
    path.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))

spec = importlib.util.spec_from_file_location('closure_recipe', LOCALE/'remedial-cycle-002-closure-recipe-v2.py')
recipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recipe)
e = recipe.build()
manifest = read(CLOSURE/'manifest.json')
recipe.verify()
rows, byid = e['rows'], e['byid']
bykey = {r['key']:r for r in rows if r['key']}

# Independent regeneration already emitted to this directory, with only output
# path provenance differing in its manifest.
reproduced = OUT/'reproduced-closure'
comparisons=[]
for p in sorted(CLOSURE.iterdir()):
    q=reproduced/p.name
    if p.name=='manifest.json':
        normalized=json.dumps(read(q),ensure_ascii=False,sort_keys=True).replace(str(reproduced.relative_to(ROOT)),str(CLOSURE.relative_to(ROOT)))
        equal=normalized==json.dumps(read(p),ensure_ascii=False,sort_keys=True)
        comparisons.append({'file':p.name,'equalAfterOutputPathNormalization':equal,'originalSha256':sha(p),'reproducedSha256':sha(q)})
    else:
        equal=p.read_bytes()==q.read_bytes()
        comparisons.append({'file':p.name,'byteEqual':equal,'originalSha256':sha(p),'reproducedSha256':sha(q)})
    assert equal,p
write('recipe-reproduction.json',{'recipeSha256':sha(LOCALE/'remedial-cycle-002-closure-recipe-v2.py'),'files':comparisons,'closure':len(e['closure']),'previous':len(e['previous']),'corrected':len(e['changed']),'new':len(e['closure']-e['previous']),'correctedPreviouslyReviewed':len(e['changed']&e['previous']),'correctedOutsidePrevious':len(e['changed']-e['previous']),'explicitlyInvalidatedPrior':len(e['invalidated_prior']),'retired':len(e['retired']),'exactDelta':len(e['delta']),'formula':'278 corrected union 1377 new union 26 explicitly invalidated = 1403; 252 corrected IDs overlap the new set'})

# Source alignment is checked independently of the historical target ledger.
source_rows=[json.loads(l) for l in (ROOT/'Source/localization-inventory-v3/strings.jsonl').read_text().splitlines()]
source_rows += [json.loads(l) for l in (ROOT/'Source/localization-inventory-v3/static-text.jsonl').read_text().splitlines()]
source={r['stableId']:r for r in source_rows}
assert len(source)==len(source_rows)
for r in rows:
    assert r['stableId'] in source and r['source']==source[r['stableId']]['source']
    if r['stableId'].startswith('string:') and r['key']:assert r['key']==source[r['stableId']]['key']

prior_rows=[json.loads(l) for l in (LOCALE/'independent-review-01/per-id-decisions-final.jsonl').read_text().splitlines()]
prior={r['stableId']:r for r in prior_rows}
assert len(prior)==len(prior_rows)
assert e['previous'] <= set(prior)
for sid in e['previous']:
    assert prior[sid]['fullSourceAndCurrentTargetRead']
    assert prior[sid]['sourceSha256']==text_sha(byid[sid]['source'])
    assert prior[sid]['targetSha256']==text_sha(e['before'][sid])
for sid in e['previous']-e['invalidated_prior']:
    assert e['values'][sid]==e['before'][sid]
write('prior-decision-applicability.json',{'previousClosureIds':3090,'unchangedPriorUnitEvidenceReusable':3064,'changedPriorInvalidated':26,'retired':0,'sourceAndBeforeTargetLedgerHashesVerified':True,'rejected16310IndependentlyAdjudicatedNow':True,'limit':'Unit evidence is reusable on unchanged source/glossary/target/binding. Prior review01 overall closure completeness was rejected; its omitted dependencies are addressed separately, not converted into a historical clean verdict.'})

# Full-unit replacements, directly authored by the independent reviewer.
proposals = {
8018:('De ce nu sunteți încă în zona de carantină?','negative-chronology','до сих пор не asks why he is still not in quarantine; nu mai says no longer and presupposes an earlier stay. Actual option talk_doc_3 invokes Doctor_Asking_3.','talk_doc_3'),
8757:('Credeam că mergeți azi-noapte după mama ei','past-night-reference','The actual talk_couple_3 option invokes Couple_Asking_3, whose first reply says the wife spent three hours getting ready and it was already too late to leave, then postpones the trip. la noapte points to the upcoming night, contradicting that completed failed departure.','talk_couple_3'),
11963:('Spală-te','washing-action-location','The armpit self-examination option invokes selfchek_wash_armpits, which calls WashArmpits. The approved wash term is generic Spală-te and explicitly covers axillary irritation; adding pe față identifies the wrong body part. Keep the safe generic action rather than adding a body site.','selfcheck_armpit_imposter'),
12078:('Trebuie să mă spăl. Sper să ajute.','washing-action-location','This is the armpit-irritation exchange immediately before the washing option and WashArmpits callback. pe față adds a conflicting body site; retain the source hope without promising cure.','selfcheck_armpit_imposter'),
12104:('Spală-te','washing-action-location','Exact-source repetition of Умыться with the same current Spală-te pe față. Its selfcheck_hands branch actually invokes the shared selfchek_wash_armpits callback. The generic approved term preserves the action without inventing face washing; record the hands/armpits source-binding peculiarity separately.','selfcheck_hands')}
findings=[]
for ordinal,(target,group,reason,node) in proposals.items():
    r=rows[ordinal];sid=r['stableId'];path,index=e['locations'][sid]
    assert target!=e['values'][sid]
    findings.append({'findingId':f'ro-ir02-{ordinal}','ordinal':ordinal,'stableId':sid,'key':r['key'],'source':r['source'],'currentTarget':e['values'][sid],'proposedTarget':target,'authoredPath':path,'entryIndex':index,'defectGroup':group,'reason':reason,'actualCompiledNode':node,'inExactDelta':sid in e['delta'],'inCurrentClosure':sid in e['closure']})
write('consolidated-findings.json',{'reviewer':'/root/ro_independent_review_02','reviewDeltaUnits':1403,'objectiveProposals':len(findings),'defectGroups':3,'proposals':findings,'policy':'One consolidated full-unit batch. No authored values were changed. Adjudicate and apply together, repair the canonical closure selector/catalog, then review exact next delta.'})

rules=read(ROOT/'Source/preserve-exactly-v4.json')
rules={r['stableId']:r for r in rules['tableRows']+rules['staticRows']}
values=dict(e['values'])
for f in findings:
    recipe.check_value(rules[f['stableId']],f['proposedTarget'])
    values[f['stableId']]=f['proposedTarget']
for sid,value in values.items():recipe.check_value(rules[sid],value)
write('proposal-preflight.json',{'currentFullCorpusRows':16538,'projectedFullCorpusRows':16538,'proposedReplacements':5,'result':'passed pinned complete preserve-exact contract','replacedDependencies':'No renderer, game VM, layout engine, package or live state is exercised. Structural safety does not itself prove semantic correctness.','authoredApplied':False})

# Verify every actual transfer option, guard and callback, including the distinct
# Firefighter response; expose precise instructions rather than a name-only match.
transfer=[]
for witness in read(LOCALE/'independent-review-01/item-transfer-contract-verification.json')['rows']:
    r=byid[witness['stableId']];ins=e['nodes'][witness['node']]
    idx=next(i['index'] for i in ins if i['opcode']==4 and r['key'] in i['operands'])
    guard=ins[idx-6:idx]
    assert [x['opcode'] for x in guard]==[6,7,12,7,7,12]
    assert [x['operands'] for x in guard]==[['Povistka'],[1.0],['GetItemCount'],[0.0],[2.0],['Number.GreaterThan']]
    assert ins[idx]['operands'][-1] is True
    cb=next(i['index'] for i in ins if i['opcode']==12 and i['operands']==['TryGiveItemFor'])
    args=ins[cb-4:cb]
    assert [x['opcode'] for x in args]==[6,7,6,7]
    assert args[0]['operands']==['Povistka'] and args[1]['operands']==[1.0] and args[3]['operands']==[3.0]
    assert ins[cb+1]['opcode']==10
    expected='FEMA_GivingPostcard_Firefighter' if witness['node']=='talk_firefighter_1' else 'FEMA_GivingPostcard'
    assert ins[cb+2]['operands']==[expected]
    transfer.append({'ordinal':r['ordinal'],'stableId':r['stableId'],'node':witness['node'],'optionInstruction':ins[idx],'existingItemGuardInstructions':guard,'transferInstructions':args+[ins[cb]],'recipient':args[2]['operands'][0],'successfulResponseNode':expected,'visibleOperandOrder':[bykey[o]['ordinal'] for i in ins if i['opcode'] in [2,4] for o in i['operands'] if isinstance(o,str) and o in bykey],'target':e['values'][r['stableId']]})
assert len(transfer)==245
write('transfer-bindings.json',{'programSha256':e['program_sha'],'bindings':transfer,'count':245,'readBoundary':'All 245 full pairs and each ordered option/guard/recipient/callback binding checked. Static compilation and managed inventory removal establish the mechanism; no live state executed.'})

node_members=collections.defaultdict(list)
for n,ins in e['nodes'].items():
    for i in ins:
        for o in i['operands']:
            if isinstance(o,str) and o in bykey:
                node_members[bykey[o]['stableId']].append({'node':n,'instruction':i['index'],'opcode':i['opcode']})
review_rows=[json.loads(l) for l in (OUT/'delta-rows.jsonl').read_text().splitlines()]
groups=read(OUT/'read-groups.json')
group_for={sid:g['group'] for g in groups for sid in g['stableIds']}
assert len(group_for)==1403 and set(group_for)==e['delta']
find_by={f['stableId']:f for f in findings}
ledger=[]
for r in review_rows:
    sid=r['stableId'];f=find_by.get(sid)
    ledger.append({'ordinal':r['ordinal'],'stableId':sid,'key':r['key'],'source':r['source'],'target':r['after'],'sourceSha256':text_sha(r['source']),'targetSha256':text_sha(r['after']),'fullSourceAndCurrentTargetRead':True,'readGroup':group_for[sid],'readMethod':'Independent model read of complete Russian/current Romanian pair; identical pairs grouped with every ordinal and stable ID retained, then actual compiled placements checked.','decision':'objective-correction-proposed' if f else 'no-objective-correction-in-reviewed-unit','findingId':f['findingId'] if f else None,'compiledPlacements':node_members[sid],'components':r['components'],'mandatoryRegressions':r['mandatoryRegressions']})
jsonl('per-id-decisions.jsonl',ledger)

catalog=[]
for name,members in e['catalog'].items():
    assert members<=e['closure']
    new=members&e['delta'];retained=members-e['delta']
    assert retained<=e['previous']-e['invalidated_prior']
    descriptor=manifest['currentRegressionCatalog'][name]
    assert sha(ROOT/descriptor['path'])==descriptor['sha256']
    catalog.append({'class':name,'totalIds':len(members),'independentDeltaReads':len(new),'unchangedPriorEvidenceReused':len(retained),'componentSha256':descriptor['sha256'],'findingIds':[f['findingId'] for f in findings if f['stableId'] in members],'applicability':'Empty supplemental witness lists do not remove the hidden label/placeholder rows in retained v3 UI and placeholder classes.' if not members else 'Complete named list reconciled; independent reads plus reusable unchanged prior decisions.'})
write('mandatory-catalog.json',{'unionIds':len(e['components']['mandatory-regressions']),'deltaReadUnionIds':len(e['components']['mandatory-regressions']&e['delta']),'classes':catalog,'newRegressionRequired':'Add contextual washing actions, including shared Умыться option 12104, and chronological option→reply checks. Existing regression results cannot be clean until proposals are adjudicated.'})

# Explicit supplemental reads and bounded real dependencies; these do not change
# the authoritative 1403-ID count.
supp_ord=[12104,16310,6757,6758,6759,6760,6761,6762,12072,12092,12093,12094,12095,12096,12097,8016,8015,8014,8013,8012,8011,8010,8009,8008,8007,8006,8005,8004,8003,7981,7980,8755,8754,8753,8752,8751,2586,2585,2584,2583,2582]
supp=[]
for ordinal in sorted(set(supp_ord)):
    r=rows[ordinal];sid=r['stableId']
    if sid in e['delta']:continue
    supp.append({'ordinal':ordinal,'stableId':sid,'source':r['source'],'target':e['values'][sid],'fullSourceAndCurrentTargetRead':True,'compiledPlacements':node_members[sid],'decision':'objective-correction-proposed' if sid in find_by else 'no-objective-correction-in-context-unit','findingId':find_by[sid]['findingId'] if sid in find_by else None})
jsonl('supplemental-context-decisions.jsonl',supp)
focused=['talk_doc_3','Doctor_Asking_3','Doctor_Asking_3_Backstory','Doctor_Asking_3_Disappointed','talk_couple_3','Couple_Asking_3','selfcheck_armpit_imposter','selfcheck_hands','selfchek_wash_armpits','Firefighter_Teeth_DontShoot','BigLebowski_Entrance_Occupied','FEMA_GivingPostcard','FEMA_GivingPostcard_Firefighter']
write('focused-compiled-context.json',{'programSha256':e['program_sha'],'nodes':{n:e['nodes'][n] for n in focused},'allActualSelectedNodes':manifest['otherEvidence']['consumer-topology.json'],'twoUnmappedCorrectedLines':[(d['ordinal'],d['key']) for d in e['unmapped']],'sourceFamilyLimit':'Source key-stem contexts for 12206 and 15596 do not establish a compiled runtime edge.'})
write('adjudication-and-source-limits.json',{'rejected16310':{'decision':'author rejection upheld; current target accepted','source':'некому напоминать','analysis':'некому + infinitive is an impersonal construction with an absent potential actor: there is nobody to remind. Missing recipients would be некого (кого?), not некому. The known children-at-home context also supports the father being absent; neither child death nor nobody left to receive a reminder is asserted.','currentFullUnit':e['values'][rows[16310]['stableId']],'compiledNode':'Firefighter_Teeth_DontShoot'},'genericDogPlural9181And9196':{'decision':'retain ele','analysis':'Both actual Buddy_Asking_3_5 and Buddy_Asking_3_6 move from his dog to the generic animal de companie aphorism. Romanian animal is neuter, plural animalele licenses feminine plural ele. This does not conflict with singular câine→el/lui and does not establish biological sex.'},'dynamicDomain':{'sourceObjects':13,'mappedNonemptyLabels':11,'nullLabelObjects':['Neighbour','EmptyCharacter'],'selfObject':'BigLebowski','assembledInputs':read(CLOSURE/'dynamic-consumer-context.json'),'analysis':'All 11 available full name substitutions fit the uninflected slot and preserve the rhyme in the following line. Two null cells are explicit missing/empty inputs, not fabricated labels. Live feasibility, self exclusion, trimming and spawn combinations remain unrun.'},'handsWashingSourceBinding':{'findingType':'existing source/consumer peculiarity; no source mutation','analysis':'selfcheck_hands displays dirty nails but directly calls selfchek_wash_armpits→WashArmpits. It is statically known, not an invented hand-wash edge. Generic Spală-te avoids adding a face location and does not claim to repair the source action dispatch.'},'callbackContextLimit':{'outsideCurrentClosureOrdinals':[6757,6758,6759,6760,6761,6762],'analysis':'Actual successful transfer response nodes are outside the 4467-ID selector. Their six full pairs were additionally read and are valid as source renderings; minimum downstream context should be retained in the next normal recipe rather than inferred from the transfer function name. The source Player prefixes are retained exactly; live speaker assignment is not certified.'}})

limits=[]
for rel in ['Translations/ro/dialogue-batch-003.json','Translations/ro/dialogue-batch-006.json','Translations/ro/ui-batch-003.json','Translations/ro/ui-batch-004.json','Translations/ro/ui-batch-005.json']:
    data=read(ROOT/rel);current_ids=[]
    for entry in data['entries']:
        assert set(entry)=={'id','target'}
        sid=f"string:{recipe.GUIDS[data['collection']]}:{entry['id']}"
        assert sid in byid and byid[sid]['collection']==data['collection']
        assert e['locations'][sid][0]==rel and entry['target']==e['values'][sid]
        current_ids.append(sid)
    historical_ids=[r['stableId'] for r in rows if r.get('batchPath')==rel]
    assert current_ids==historical_ids,(rel,len(current_ids),len(historical_ids))
    assert data['schemaVersion']==1 and data['locale']=='ro' and data['sourceLocale']=='ru' and data['gameVersion']=='1.3.19'
    assert data['sourceInventorySha256']==e['pins']['sourceInventory'] and data['glossaryFingerprint']==e['pins']['approvedGlossary']
    limits.append({'path':rel,'currentSha256':sha(ROOT/rel),'entries':len(current_ids),'currentEntryFields':['id','target'],'exactIdOrderEqualsPinnedFullPassBatchRows':True,'currentSchemaAndVersionPinsValid':True,'currentTargetsExactlyAccountedByPinnedFullPassPlus71And278Corrections':True,'exactHistoricalNonTargetParity':'unverified: original bytes unavailable','reviewCoverageImplication':'Mapping, source alignment, target receipts and current schema are verifiable. Do not infer original byte or metadata equality from current conformance.'})
write('preimage-boundary.json',{'files':limits,'17Of18CurrentCycleByteReversals':'The pinned author receipt reproduces 17 exact old hashes; immutable full target/source reconciliation and v2 recipe independently verify current fields.','ui004BoundedSerializationRecovery':'Tested indent None/2/4, UTF-8/ASCII escaping, sorted/preserved keys, compact/default separators, final newline absent/LF/CRLF; no old SHA-256 match. No original bytes recovered.','restartAssessment':'No full-restart event established: stable-ID order, source content, approved glossary, current mapping and complete full-pass target receipts remain verified. Historical whole-file non-target parity remains unverified. Root must retain that limitation, not report a recovered preimage.'})

pins=[]
for path in [ROOT/'Source/localization-inventory-v3/strings.jsonl',ROOT/'Source/localization-inventory-v3/static-text.jsonl',ROOT/'Source/preserve-exactly-v4.json',ROOT/'Documentation/glossary-translations/ro/layer.json',LOCALE/'semantic-review-progress.json',LOCALE/'remedial-cycle-002-plan.json',LOCALE/'remedial-cycle-002-closure-recipe-v2.py',CLOSURE/'manifest.json',LOCALE/'remedial-cycle-002-validation-and-preimage.json',LOCALE/'dialogue-repeats-001.authored.json',LOCALE/'dialogue-repeats-002.authored.json',ROOT/'Documentation/ro-text-progress.json',ROOT/'Documentation/NON_THAI_INTEGRATION.md']:
    pins.append({'path':str(path.relative_to(ROOT)),'sha256':sha(path)})
pins+=manifest['afterAuthoredFiles']
for path,digest in e['files'].items():assert sha(ROOT/path)==digest
write('input-pins.json',{'pins':pins,'authoredFiles':415,'sourceAlignmentVerifiedRows':16538,'note':'All current authored hashes are taken from and checked against authoritative v2 manifest, not stale batch entries in Documentation/ro-text-progress.json.'})
write('review-result.json',{'reviewer':'/root/ro_independent_review_02','game':'No, I\'m not a Human','version':'1.3.19','locale':'ro','sourceLocale':'ru','verdict':'corrections required; unchanged-hash clean acceptance not granted','exactDeltaRead':1403,'distinctFullPairGroupsRead':671,'supplementalFullContextPairsRead':len(supp),'fullSemanticPassPreviouslyVerified':16538,'previousIndependentClosure':3090,'currentClosure':4467,'correctedAuthorIds':278,'newClosureIds':1377,'invalidatedPriorIds':26,'retiredIds':0,'proposals':5,'proposalGroups':3,'closureLimits':'Shared washing option 12104 and six actual downstream transfer-response rows are outside the current closure. Supplemental reads are recorded; retain them through the next normal selector/catalog recipe.','fullRestartRequired':False,'currentCorpusPreserveExact':'16538 passed','projectedProposalCorpusPreserveExact':'16538 passed','repeatExpansion':'2828 passed, including 245 transfer options','glossaryCli':'guide/work read-only: 201 source and 201 ro, ordered IDs aligned; independent content re-export not performed','sourceProgramSha256':e['program_sha'],'closureManifestSha256':sha(CLOSURE/'manifest.json'),'finalAuthoredHashesUnchanged':True,'runtime':'not run; prohibited','imagesTextures':'excluded','integration':'root coordinator owns gate and Git','telemetry':{'exactServedModel':'unknown','reasoningSetting':'unknown','inputTokens':None,'cachedInputTokens':None,'outputTokens':None,'reasoningTokens':None,'totalTokens':None,'limitation':'No per-request/session usage counters exposed to this reviewer. Parent may reconcile existing actual telemetry; no estimates from text size used. No descendants launched; root orchestration must be accounted separately. Reporting tail unmeasured.'}})
print(json.dumps({'result':'evidence written','delta':1403,'findings':len(findings),'supplemental':len(supp),'recipeArtifacts':len(comparisons),'catalog':len(catalog)}))
