"""Immutable Serbian cycle 002 independent review evidence; no input mutation."""
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SR = ROOT / 'Translations/sr'
OLD = SR / 'independent-review-01'
sys.path.insert(0, str(ROOT / 'Scripts'))
import preserve_exact

def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ts(s): return hashlib.sha256(s.encode()).hexdigest()
def ids_sha(ids): return ts(''.join(i + '\n' for i in ids))
def save(name, data):
    p = OUT / name
    assert not p.exists(), p
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
def save_lines(name, rows):
    p = OUT / name
    assert not p.exists(), p
    p.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))

c = read(SR / 'semantic-cycle-002-closure.json')
prior = read(SR / 'semantic-cycle-001-closure.json')
correction = read(SR / 'semantic-cycle-002-corrections.json')
plan = read(SR / 'semantic-cycle-002-adjudication.json')
risk = read(SR / 'semantic-cycle-002-dynamic-risk.json')
catalog = read(SR / 'semantic-cycle-002-regressions.json')
manifest = read(ROOT / 'Source/preserve-exactly-v4.json')
canonical = [r['stableId'] for r in manifest['tableRows'] + manifest['staticRows']]
rules = {r['stableId']: r for r in manifest['tableRows'] + manifest['staticRows']}
assert len(canonical) == len(rules) == 16538
source = {}
for n in ('strings.jsonl', 'static-text.jsonl'):
    for r in map(json.loads, (ROOT / 'Source/localization-inventory-v3' / n).read_text().splitlines()):
        assert r['stableId'] not in source
        source[r['stableId']] = r
target = {}
location = {}
guids = {'UI': '0cbd8a7a4f543344bb95659de87f67a5', 'Dialogs': '444ff14f1967f5a4c8eb9e4cf4c913f1', 'ChecksDialogs': '389c6d80595013c41b85a7197838c4b6'}
authored = []
for f in c['currentAuthoredFileHashes']:
    p = ROOT / f['path']
    assert sha(p) == f['sha256']
    b = read(p)
    for e in b['entries']:
        i = e.get('stableId') or 'string:' + guids[b['collection']] + ':' + str(e['id'])
        assert i not in target
        target[i] = e['target']; location[i] = f['path']
    side = read(p.with_suffix('.validation.json'))
    assert side['structuralResult'] == 'passed'
    assert side.get('batchSha256', side.get('draftSha256')) == f['sha256']
    authored.append(dict(f, actualSha256=sha(p), result='passed'))
assert set(target) == set(canonical)
file_set = ts(''.join(f['path'] + '\t' + f['sha256'] + '\n' for f in sorted(authored, key=lambda f: f['path'])))
assert file_set == c['currentAuthoredFileSetSha256'] == correction['currentAuthoredFileSetSha256']

pins = {}
def pin(path, expected):
    actual = sha(path)
    assert actual == expected, str(path)
    pins[str(Path(path).relative_to(ROOT)) if Path(path).is_relative_to(ROOT) else str(path)] = {'expectedSha256': expected, 'actualSha256': actual, 'result': 'passed'}
for r in read(OLD / 'verification.json')['pins']:
    pin(ROOT / r['path'], r['expectedSha256'])
for f in read(OLD / 'artifact-manifest.json')['files']:
    pin(ROOT / f['path'], f['sha256'])
progress = read(SR / 'semantic-review-progress.json')
for key in ('cycle002ApplicationVerification', 'cycle002RetiredDependencyReasons', 'cycle002HandoffAddendum', 'postCorrectionEvidence'):
    p = progress[key]; pin(ROOT / p['path'], p['sha256'])
prep = progress['independentReviewPreparation']
for a, b in [('closure','closureSha256'), ('deltaReviewRows','deltaReviewRowsSha256'), ('regressionCatalog','regressionCatalogSha256'), ('handoff','handoffSha256'), ('builder','builderSha256'), ('adjudicationEvidence','adjudicationEvidenceSha256'), ('boundedDynamicRisk','boundedDynamicRiskSha256')]:
    pin(ROOT / prep[a], prep[b])
for f in correction['currentStructuralSidecarHashes']:
    pin(ROOT / f['path'], f['sha256'])
pin(ROOT / 'Translations/sr/static-authored-map.json', correction['staticAuthoredRecipeSha256'])
pin(ROOT / 'Translations/sr/static-text-draft.json', correction['staticDraftSha256'])
pin(ROOT / 'Translations/sr/dialogue-common-002.authored.json', correction['dialogueCommonRecipeSha256'])
pin(ROOT / correction['fullPreserveExactReport'], correction['fullPreserveExactReportSha256'])
review_glossary = read(ROOT / 'Documentation/glossary-translations/sr/review.json')
pin(ROOT / 'Documentation/glossary-research/final-v1/glossary.json', review_glossary['source_sha256'])
pin(ROOT / 'Documentation/glossary-translations/sr/authored.json', review_glossary['authored_sha256'])
pin(ROOT / 'Documentation/glossary-translations/sr/layer.json', review_glossary['layer_sha256'])
for n in ('final-self-audit-1.json', 'final-self-audit-2.json'):
    g = read(ROOT / 'Documentation/glossary-translations/sr' / n)
    assert g['source_sha256'] == review_glossary['source_sha256']
    assert g['authored_sha256'] == review_glossary['authored_sha256']
    assert g['layer_sha256'] == review_glossary['layer_sha256']

for name, comp in c['componentLists'].items():
    assert comp['count'] == len(comp['ids']) == len(set(comp['ids']))
    assert comp['ids'] == [i for i in canonical if i in set(comp['ids'])]
    assert ids_sha(comp['ids']) == comp['idsSha256']
current_set = set(c['closureIds']['ids']); prior_set = set(prior['closureIds'])
changed = set(c['changedIds']['ids']); new = current_set - prior_set
invalidated = set(c['explicitlyInvalidatedPriorIds']['ids']); retired = prior_set - current_set
delta = changed | new | invalidated
assert len(current_set) == 604 and len(delta) == 77 and len(changed) == 17 and len(new) == 59 and len(invalidated) == 2 and len(retired) == 142
assert len(changed & new) == 1 and not (changed & invalidated) and not (new & invalidated)
assert current_set == set().union(*(set(v['ids']) for v in c['componentLists'].values()))
for n, values in [('closureIds',current_set), ('changedIds',changed), ('newDependencyIds',new), ('explicitlyInvalidatedPriorIds',invalidated), ('retiredDependencyIds',retired), ('deltaReviewIds',delta)]:
    comp = c[n]
    assert comp['ids'] == [i for i in canonical if i in values]
    assert comp['count'] == len(values) and ids_sha(comp['ids']) == comp['idsSha256']
assert ids_sha(prior['closureIds']) == prior['closureIdsSha256']
delta_rows = list(map(json.loads,(ROOT / c['deltaReviewRows']).read_text().splitlines()))
assert [r['stableId'] for r in delta_rows] == c['deltaReviewIds']['ids']
for r in delta_rows:
    i = r['stableId']
    assert r['source'] == source[i]['source'] and r['target'] == target[i]
    assert r['sourceSha256'] == ts(r['source']) and r['targetSha256'] == ts(r['target'])

old_read = list(map(json.loads,(OLD / 'read-evidence.jsonl').read_text().splitlines()))
old_extra = list(map(json.loads,(OLD / 'additional-context-read-evidence.jsonl').read_text().splitlines()))
previous_evidence = {r['stableId']: r for r in old_read + old_extra}
assert len(previous_evidence) == 1138
retirement = read(SR / 'semantic-cycle-002-retirement-reasons.json')
assert [r['stableId'] for r in retirement['rows']] == c['retiredDependencyIds']['ids']
for r in retirement['rows']:
    i = r['stableId']; e = previous_evidence[i]
    assert e['source'] == source[i]['source'] and e['target'] == target[i]
    assert e['semanticVerdict'] == 'passed within reviewed context'
    assert r['priorComponents'] == [n for n,v in prior['componentLists'].items() if i in set(v['ids'])]
    assert i not in current_set and r['reason']

consumers = read(OLD / 'runtime-consumers.json')
pin(Path(consumers['sourceDll']), consumers['sourceDllSha256'])
characters = read(OLD / 'character-runtime-data.json')
pin(Path(characters['sourcePath']), characters['sourceSha256'])
for snippet in consumers['generatedSourceEvidence']:
    p = Path(snippet['path']); pin(p,snippet['fileSha256'])
    assert ''.join(p.read_text().splitlines(keepends=True)[snippet['firstLine']-1:snippet['lastLine']]) == snippet['exactText']
bindings = ROOT / 'Source/glossary-corpus-v2/runtime-bindings.json'
pin(bindings, consumers['bindingsSha256'])
program = bytes(read(bindings)['sharedassets0.assets:2743']['compiledYarnProgram'])
assert hashlib.sha256(program).hexdigest() == consumers['compiledProgramSha256']

def var(buf, i):
    n = 0; shift = 0
    while True:
        v=buf[i]; i+=1; n|=(v&127)<<shift; shift+=7
        if v<128:return n,i
def fields(buf):
    i=0; result=[]
    while i<len(buf):
        key,i=var(buf,i); f,w=key>>3,key&7
        if w==0:v,i=var(buf,i)
        elif w==2:n,i=var(buf,i);v=buf[i:i+n];i+=n
        elif w==5:v=struct.unpack('<f',buf[i:i+4])[0];i+=4
        else:raise ValueError(w)
        result.append((f,v))
    return result
def operand(buf):
    f,v=fields(buf)[0];return v.decode() if f==1 else v
nodes={}
for f,v in fields(program):
    if f!=2:continue
    pair=dict(fields(v));name=pair[1].decode(); instructions=[];labels={}
    for f,v in fields(pair[2]):
        if f==2:
            raw=fields(v);instructions.append({'index':len(instructions),'opcode':next((v for f,v in raw if f==1),0),'operands':[operand(v) for f,v in raw if f==2]})
        if f==3:
            lab=dict(fields(v));labels[lab[1].decode()]=lab.get(2,0)
    nodes[name]={'instructions':instructions,'labels':labels}
selected_nodes=sorted({n for r in delta_rows for n in r['nodeNames']})
keymap={r.get('key'):r for r in source.values() if r.get('collection')=='Dialogs'}
scene_evidence={}
prior_yarn=read(OLD / 'yarn-context.json')['nodes']
for n in selected_nodes:
    actual=nodes[n]
    assert [{k:v for k,v in i.items() if k in ('index','opcode','operands')} for i in prior_yarn[n]['instructions']] == actual['instructions']
    assert prior_yarn[n]['labels'] == actual['labels']
    enriched=[]
    for ins in actual['instructions']:
        ins=dict(ins)
        key=next((o for o in ins['operands'] if isinstance(o,str) and o.startswith('line:')),None)
        if key:
            r=keymap[key];i=r['stableId'];ins.update(stableId=i,source=r['source'],target=target[i],inDelta=i in delta)
        enriched.append(ins)
    scene_evidence[n]={'instructions':enriched,'labels':actual['labels']}
save('compiled-delta-context.json',{'compiledProgramSha256':consumers['compiledProgramSha256'],'bindingsSha256':consumers['bindingsSha256'],'nodes':scene_evidence,'scope':'Independently decoded serialized topology; exact prior topology reused only after equality checks; current targets bound by stable ID. No execution.'})

domains={r['node']:r['possibleLabels'] for r in consumers['samePlaceLabelCandidates']}
cases=[];limits=[]
for r in delta_rows:
    i=r['stableId']
    if '{0}' not in r['target']:continue
    rr=next(x for x in risk['rows'] if x['stableId']==i)
    category=rr['consumerCategory']
    if category=='LocalizeItem': labels=consumers['deficitLabels']
    elif category=='GetCharacterOnPlace': labels=domains[r['nodeNames'][0]]
    else:raise AssertionError(category)
    for label in labels:
        li=label.get('labelStableId')
        if not li:
            limits.append({'stableId':i,'candidateEnum':label['enum'],'status':'unknown UI key/label; no actual input or output invented'});continue
        value=target[li]
        cases.append({'stableId':i,'consumerCategory':category,'labelStableId':li,'enum':label['enum'],'rawLabel':value,'assembledTarget':r['target'].replace('{0}',value),'boundary':'Literal raw-label insertion only; no executed scene reachability'})
save('raw-label-cases.json',{'cases':cases,'unknownInputs':limits,'allKnownChangedConsumersCovered':True,'substitutionSemantics':consumers['substitutionSemantics']})

reasons = [
 'Dreamy/daydreaming diminutive now matches the fairytale-enjoyer glossary, rather than sleepy.',
 'Refusal to accept a bribe is preserved.', 'Permission to enter is preserved.', 'Question whether agreement has now been reached is preserved.',
 'Suitability question and initial assent remain; label follows a neutral demonstrative and colon, permitting plural cigarettes and every known nominative item.',
 'Female speaker retains habitual familiarity with the approach and understanding of the player intent.',
 'Full thanks-and-gift context retains possession, small amount and hoped usefulness; colon admits all raw item labels.', 'Strong polite gratitude is preserved.',
 'Refusal to accept a bribe is preserved.', 'Permission to enter is preserved.',
 'Conditional offer, possession and formal suitability question retained; colon avoids requiring accusative raw item labels.',
 'Patrol versus the still more frightening Guests distinction and capitalized glossary concept retained.', 'Polite plea to be let inside is preserved.',
 'Complete item offer retains the small amount and hoped usefulness, with a nominative inventory list.', 'Strong polite gratitude is preserved.',
 'Refusal to accept a bribe is preserved.', 'Permission to enter is preserved.',
 'Brief offer and informal request retained; neutral inventory list accepts every known raw item.', 'Hesitation and request to wait are preserved.',
 'Both Enerjeka mentions retain the approved brand and naturally inflected accusative.', 'Disappointed reaction, wait request and varied inventory are preserved.',
 'Refusal to accept a bribe is preserved.', 'Permission to enter is preserved.',
 'Found item, host address and shelter until morning remain complete; something plus colon supports all nominative items.',
 'Knife retained for himself, bandages, old empty flask and its limited usefulness are all preserved.', 'Plea not to dismiss him immediately and bag search are preserved.',
 'Request to leave is preserved.', 'Promise to handle the problem and permission to enter are preserved.',
 'Source feminine pronoun and vulgar expulsion/house possession relation retained; possible male source defaults remain a classified source inconsistency.',
 'Changed dreamy student label fits the same nominative subject slot; source female wolf metaphor remains intact rather than being rewritten from inferred state.',
 'Advice to leave is preserved.', 'Permission to enter is preserved.',
 'Missing legs, walking-proof pun and confrontational colloquial voice retained.', 'Certainty that the trick will work is preserved.',
 'Complete waving-at-entry invisibility joke, action order and male player agreement retained; colon permits all raw item labels.',
 'Refusal to accept a bribe is preserved.', 'Permission to enter is preserved.',
 'Uncertainty, item identification, offer, at least one day and pessimistic self-correction remain; ellipsis avoids singular agreement on plural cigarettes.',
 'Male blind visitor retains his hesitation, remembered possession and polite wait request.',
 'Refusal to accept a bribe is preserved.', 'Permission to enter is preserved.', 'Cost comparison retains its threat context.',
 'Complete threat retains husband, tomorrow, yellow suits, unscheduled raid, paperwork, dogs and possible daily repetition.',
 'Advance payment and let-me-warm-up condition retained; dash handles every item without a singular copula.',
 'Strong nose/scent metaphor, human versus Guest distinction and speaker agency retained.',
 'Request to leave is preserved.', 'Player promises to expel the resident before admitting the newcomer.',
 'Instrumental question and pointing retained without feminine agreement that conflicts with Bald; nominative label after dash is independent.',
 'Comfortable corner already occupied remains intact.',
 'Request to leave is preserved.', 'Player promises to expel the resident before admitting the newcomer.',
 'Tentative future action retains proposed sitting outside, short rest, subsequent departure and reason concerning these guests; ваљда retains the tentativeness.',
 'Hardship prediction and deliberately affectionate diminutive speech trait retained; no objective alteration established.',
 'Exclamation, armchair and prior occupancy retained; occupied agrees with chair, and dash independently admits singular Anger and plural Sirin label две сестре.',
 'Request to leave is preserved.', 'Player promises to expel the resident before admitting the newcomer.',
 'Perceived blood on resident hands, uncertainty about admitting them and nerve-thrill question retained; source male default is not new target gender evidence.',
 'Finding SR-IR02-01: one admissible UI label is a prepositional fragment, not a nominative person noun, so the new copula sentence fails for Blind.',
 'Refusal to share a roof, insult and inability to restrain himself remain; source masculine default noted, not silently reassigned.',
 'Terse occupant question no longer adds singular copula; admits страшна баба and plural две сестре without disagreement.',
 'Request to leave is preserved.', 'Player promises to expel the resident before admitting the newcomer.',
 'Reported prohibition and expulsion demand retained; ту особу supports every known singular male/female occupant.',
 'Existence question uses nominative singular raw label; all three actual known candidates are singular, and changed dreamy-student meaning is retained.',
 'Request to leave is preserved.', 'Player promises to expel the resident before admitting the newcomer.',
 'Expulsion, demon comparison, religious register and promised grace retained.',
 'Lifetime insufficiency to pray away sins and rebuke for associating with such people retained.',
 'Current dreamy-student label fits the independent question and dash; nominative label is not subjected to case or gender agreement.',
 'Request to leave is preserved.', 'Player promises to expel the resident before admitting the newcomer.',
 'Expulsion before too late retained; source masculine default classified separately where Tough is a possible label.',
 'Life experience, uncertainty about admission and prediction of trouble from such men retained; source male/default inconsistency classified, not introduced by correction.',
 'Neutral identifying question followed by label supports Buddy, Gravedigger and female Tough without added male demonstrative.',
 'Exact ellipsis retained.', 'Request to leave is preserved.', 'Promise to handle the situation and permission to enter are preserved.'
]
assert len(reasons)==len(delta_rows)==77
finding_id='string:444ff14f1967f5a4c8eb9e4cf4c913f1:110504457169608704'
proposal='Hunter: Код тебе је већ неко — {0}.'
preserve_exact.check_value(rules[finding_id],proposal)
finding={'findingId':'SR-IR02-01','stableId':finding_id,'source':source[finding_id]['source'],'sourceSha256':ts(source[finding_id]['source']),'currentTarget':target[finding_id],'currentTargetSha256':ts(target[finding_id]),'proposedTarget':proposal,'proposedTargetSha256':ts(proposal),'targetFile':location[finding_id],'key':source[finding_id]['key'],'nodeNames':source[finding_id]['nodeNames'],'objectiveReason':'GetCharacterOnPlace(Hunter) can return Blind whose literal UI label is без очију. The corrected existential sentence assembles Код тебе је већ без очију: it has no resident subject, and без очију reads as a predicate saying an omitted person is already eyeless, rather than identifying the resident already present. The prior accusative problem is fixed for person-noun labels but not for this known prepositional label. Add an explicit indefinite occupant, then separate the verbatim display label; no source fact, identity or name is added.','newEvidenceAgainstAcceptedCorrection':'The previously saved example already contained без очију but neither initial review nor author adjudication addressed its non-noun syntactic category. Current full-domain assembled-output reading establishes that boundary failure from unchanged evidence.','inputLabel':'без очију','inputLabelStableId':'string:0cbd8a7a4f543344bb95659de87f67a5:104046912809275392','assembledCurrentExample':target[finding_id].replace('{0}','без очију'),'assembledProposedExample':proposal.replace('{0}','без очију'),'proposalSafety':'complete unit preserve-exact passed; all known candidate examples recorded below; unknown Neighbour label excluded','knownProposedCases':[{'enum':x['enum'],'assembledTarget':proposal.replace('{0}',target[x['labelStableId']])} for x in domains['Hunter_Entrance_Occupied'] if x.get('labelStableId')]}
save('findings.json',{'status':'one consolidated full-unit objective proposal; not applied','count':1,'authoredFileSetSha256':file_set,'findings':[finding]})
read_records=[]
for ordinal,(r,reason) in enumerate(zip(delta_rows,reasons),1):
    read_records.append(dict(r,readOrdinal=ordinal,semanticRead='Full exact Russian/current Serbian unit read by independent reviewer, with approved pinned glossary and independently decoded scene order.',decision='objective finding' if r['stableId']==finding_id else 'passed within reviewed context',findingId='SR-IR02-01' if r['stableId']==finding_id else None,reason=reason,inputAuthoredFileSetSha256=file_set))
save_lines('read-evidence.jsonl',read_records)

regressions={}; reuse_rows=[]
for name,reg in catalog['catalog'].items():
    assert len(reg['ids'])==reg['count'] and ids_sha(reg['ids'])==reg['idsSha256']
    fresh=[i for i in reg['ids'] if i in delta]; reused=[i for i in reg['ids'] if i not in delta]
    for i in reused:
        e=previous_evidence[i]
        assert e['source']==source[i]['source'] and e['target']==target[i]
        assert e['sourceSha256']==ts(source[i]['source']) and e['targetSha256']==ts(target[i])
        assert e['semanticVerdict']=='passed within reviewed context'
        assert i not in invalidated
        reuse_rows.append({'catalog':name,'stableId':i,'sourceSha256':e['sourceSha256'],'targetSha256':e['targetSha256'],'priorEvidencePath':'Translations/sr/independent-review-01/read-evidence.jsonl' if i in {r['stableId'] for r in old_read} else 'Translations/sr/independent-review-01/additional-context-read-evidence.jsonl','priorReadOrdinal':e['readOrdinal'],'result':'applicable unchanged full-unit prior independent semantic evidence; not reread in cycle002'})
    defects=['SR-IR02-01'] if finding_id in reg['ids'] else []
    regressions[name]=dict(reg,freshReadIds=fresh,freshReadCount=len(fresh),unchangedPriorEvidenceIds=reused,unchangedPriorEvidenceCount=len(reused),semanticResult='changes required' if defects else 'passed',findingIds=defects)
save_lines('prior-evidence-applicability.jsonl',reuse_rows)
save('mandatory-regressions.json',{'catalogSha256':sha(SR/'semantic-cycle-002-regressions.json'),'authoredFileSetSha256':file_set,'regressions':regressions,'contextOnlyGates':catalog['contextOnlyGates'],'unboundFormatRows':[r['stableId'] for r in risk['rows'] if not r['compiledInstructions']],'unknownSamePlaceUiKeys':['characterName_Alkonost','characterName_Neighbour','characterName_Twins'],'sourceDefaults':'Source gender/default inconsistencies remain separate from introduced target grammar. No invented UI label, identity or reachability.'})
save('retirement-verification.json',{'result':'142 exact retirements verified against previous component membership, current selector nonmembership and unchanged passing prior read evidence','count':142,'priorChangedRetired':len(retired & set(prior['changedIds'])),'priorContextOnlyRetired':len(retired-set(prior['changedIds'])),'sourceReportSha256':sha(SR/'semantic-cycle-002-retirement-reasons.json'),'idsSha256':ids_sha(c['retiredDependencyIds']['ids']),'rows':retirement['rows'],'effect':'Retirement only removes current dependency selection; prior unchanged semantic evidence remains valid.'})
save('dismissed-candidates-applicability.json',{'priorEvidenceSha256':sha(OLD/'dismissed-candidates.json'),'rows':read(OLD/'dismissed-candidates.json')['rows'],'result':'Both complete source/target pairs and their pinned compiled context unchanged; no new evidence invalidates the Bestson resemblance or phone-referral dismissals.'})
for r in read(OLD/'dismissed-candidates.json')['rows']:
    assert r['source']==source[r['stableId']]['source'] and r['target']==target[r['stableId']]

overlay=dict(target);overlay[finding_id]=proposal
for i in canonical:preserve_exact.check_value(rules[i],overlay[i])
save('proposal-full-exact-preflight.json',{'status':'passed; complete 16538-unit in-memory overlay with one full-unit proposal','checkedRows':16538,'authoredWrites':False,'authoredFileSetSha256':file_set,'proposalIds':[finding_id]})
preserve_exact.validate('sr',OUT/'preserve-exact-final.json')
assert sha(OUT/'preserve-exact-final.json')==sha(SR/'preserve-exact-cycle-002.json')
save('verification.json',{'pins':pins,'authoredFiles':authored,'authoredFileSetSha256':file_set,'authoredUnits':16538,'closureIds':c['closureIds'],'exactDeltaIds':c['deltaReviewIds'],'changedIds':c['changedIds'],'newDependencyIds':c['newDependencyIds'],'explicitlyInvalidatedPriorIds':c['explicitlyInvalidatedPriorIds'],'retiredDependencyIds':c['retiredDependencyIds'],'componentLists':c['componentLists'],'overlapId':list(changed&new),'selector':'build_delta_review.py ran without --write, all immutable outputs reproduced; independently checked component union, canonical order and exact set arithmetic here.','selectorRegression':'Unchanged Ballerina choice 110504457144442887 remains in scene context independently of changedIds; all affected changed-label nodes (Ballerina, Nun, Wolfhound) selected.','application':'verify_cycle_002_application.py ran without --write and reconstructed prior authored bytes by reversing only 17 targets;328 unchanged files and12 normalization-only formatting changes in13 changed files.','compiledSceneNodes':len(scene_evidence),'knownLiteralInsertionCases':len(cases),'hashEncoding':'Exact file bytes; exact UTF-8 source/target strings; canonical stable IDs with final LF; sorted path TAB file SHA256 LF for authored sets.'})
save('summary.json',{'status':'complete independent delta review; changes required','locale':'sr','gameVersion':'1.3.19','sourceLocale':'ru','reviewerTask':'/root/sr_independent_review_02','authoredFileSetSha256':file_set,'closureSha256':sha(SR/'semantic-cycle-002-closure.json'),'closureCount':604,'deltaReviewed':77,'deltaPassed':76,'objectiveFindings':1,'correctedIdsReviewed':17,'correctedIdsPassed':16,'newDependencyIds':59,'explicitlyInvalidatedPriorIds':2,'retiredDependencies':142,'semanticResult':'not clean; one bounded raw-label template proposal requires author/coordinator adjudication','editorialAcceptance':False,'allOriginal26Corrections':'unchanged passing prior independent evidence retained; none reversed','mandatoryRegressions':'all current catalog memberships checked, exact unchanged prior semantic evidence reused per-ID, current changed/new/invalidated units reread; Hunter consumer failure remains','fullPreserveExact':'passed final current16538 and in-memory proposed16538; final current report byte-identical to cycle002 report','glossaryApprovalMetadataLimit':'Pinned layer agrees with source/authored/self-audits; local review.json still records independent_review pending. The assignment treats the layer as approved. No new glossary editorial certification or CMS parity is claimed.','runtimeVisualFontsPackagingRelease':'not run; game launch prohibited; no inherited runtime certification','imagesTextures':'excluded by owner','canonicalIntegration':'pending coordinator; no Git/index/branch mutation','telemetry':{'servedModel':'GPT-6 family identity exposed; exact served model unknown','reasoningSetting':'unknown','inputTokens':'unknown','cachedInputTokens':'unknown','outputTokens':'unknown','reasoningTokens':'unknown','totalTokens':'unknown','cutoff':'review evidence production; exact session/request telemetry not exposed; reporting tail and platform overhead unmeasured','delegation':'none'},'writes':'new immutable evidence only in Translations/sr/independent-review-02; no authored/source/glossary/prior evidence/shared recipe/state or Git mutation','remainingTechnicalLimits':['13 format-slot rows lack compiled instruction binding: no actual domain/output invented.','3 same-place enum keys lack source UI labels: no actual inputs invented.','Static source/config consumers prove possible candidates and literal substitution, not executed reachability.','Header-verified source configuration extraction inherits its bounded registry limitation.','No runtime, font, visual, layout, package, release or canonical integration acceptance.']})
save('final-gates.json',{'authoredFileSetSha256':file_set,'authoredHashesRechecked':341,'allFinalPinsUnchanged':True,'closureSha256':sha(SR/'semantic-cycle-002-closure.json'),'deltaRowsSha256':sha(ROOT/c['deltaReviewRows']),'mandatoryCatalogSha256':sha(SR/'semantic-cycle-002-regressions.json'),'fullExactReportSha256':sha(OUT/'preserve-exact-final.json'),'semanticVerdict':'changes required; SR-IR02-01; no authored application'})
print(json.dumps({'deltaRead':77,'passed':76,'findings':1,'knownLiteralInsertionCases':len(cases),'sceneNodes':len(scene_evidence),'preserveExact':16538,'authoredHashesUnchanged':True}))
