"""Seal the human/model-reviewed cycle-003 decisions; does not decide wording."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EL = ROOT / 'Translations/el'

def read(p):
    return json.loads(p.read_text())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def put(name, data):
    p = HERE / name
    assert not p.exists(), p
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

manifest = read(EL / 'correction-cycle-003-closure-manifest.json')
pins = read(HERE / 'input-pins.json')['pins']
for p, h in pins.items():
    assert sha(Path(p)) == h, p
delta = [json.loads(x) for x in (EL / 'correction-cycle-003-delta-review.jsonl').read_text().splitlines()]
context = read(HERE / 'compiled-delta-context.json')
occ = {}
for node, data in context['nodes'].items():
    for i in data['instructions']:
        if i['args'] and isinstance(i['args'][0], str) and i['args'][0].startswith('line:'):
            occ.setdefault(i['args'][0], []).append({'node': node, 'pc': i['pc'], 'opcode': i['opcode']})
changed_reasons = {
    '110504457379323908': 'Fixed label is a citation after Ορίστε τι έχω; full small-quantity and hoped-for-usefulness sentence remains. Formal address, possession and offer retained in occupied branch.',
    '110504457375129606': 'Same citation mechanism and complete small-quantity/usefulness sentence retained in separate normal-admission branch; no quantity or usefulness fact omitted.',
    '110504457375129609': 'Explicit το εξής carries the object; following Σας κάνει refers to that proposed offering. Conditional need, possession, formal address and acceptability question remain.',
    '110504457337380869': 'να τι έχω introduces a citation independent of label case; terse Θες preserves the offer. Prior Enerjeka line and subsequent alternative producer order retained.',
    '110504457224134665': 'Separate label citation followed by generic offered-item deixis preserves taking, holding, waving at the entrance and becoming invisible. Masculine αόρατος refers to the canonically male player. All six labels assessed without treating their grammatical gender as player gender.',
    '110504457509347329': 'Standalone citation with explicit generic αυτό as acceptability subject avoids plural Τσιγάρα governing singular κάνει; informal address and offer remain.'
}
decisions = []
for idx, r in enumerate(delta):
    sid = r['stableId']
    short = sid.rsplit(':', 1)[1]
    if short in changed_reasons:
        reason = changed_reasons[short]
    elif r['actualLocalizeItemConsumer']:
        reason = 'Complete actual-consumer unit preserves source meaning and offer facts. Citation/existential/deictic role remains grammatical with the six serialized deficit labels; neighboring producer and branch order checked.'
    elif r['collection'] == 'UI':
        reason = 'Complete UI label or template read; approved terminology, exact placeholders/markup and action/label distinction preserved. Autonym describes the selected Greek locale.'
    elif r['collection'] == 'static':
        reason = 'Complete serialized item-hint sample read; action, x1 and independently styled item label remain distinct. No imposed sentence agreement on the standalone label.'
    elif r['key'].startswith('line:phone_wifefema'):
        reason = 'Complete phone unit read in actual recruiter branch; caller versus respondent agency, candidate identity, threats/jokes, facts, address and unknown-role neutrality preserved.'
    elif r['key'].startswith('line:phone_alkonost'):
        reason = 'Complete husband phone unit read in actual branch order; wife/sister plurality, speaker agency, departing versus farewell conditions, emotional register and chronology preserved.'
    elif r['key'].startswith('line:Miner_'):
        reason = 'Complete Miner unit read in compiled exchange; who descends versus who belays/rescues, unresolved friends, rope, plural referents and tentative chronology preserved.'
    else:
        reason = 'Complete context unit read with its actual node/branch; meaning, speaker/addressee roles, agreement, tone and unchanged neighboring facts preserved.'
    decisions.append({'deltaIndex': idx, 'ordinal': r['ordinal'], 'stableId': sid, 'key': r['key'], 'sourceSha256': r['sourceSha256'], 'currentTargetSha256': r['currentTargetSha256'], 'glossaryFingerprint': manifest['approvedGlossarySha256'], 'fullSourceAndCurrentTargetRead': True, 'fullUnitUnchangedSentencesChecked': True, 'compiledOccurrences': occ.get(r['key'], []), 'actualLocalizeItemConsumer': r['actualLocalizeItemConsumer'], 'decision': 'accepted-current-wording', 'findingId': None, 'reason': reason})
p = HERE / 'decisions.jsonl'
assert not p.exists()
p.write_text('\n'.join(json.dumps(d, ensure_ascii=False, separators=(',', ':')) for d in decisions) + '\n')
put('findings.json', {'reviewer': '/root/el_independent_review_03', 'cycle': 3, 'locale': 'el', 'verdict': 'clean-on-pinned-unchanged-hashes', 'fullUnitObjectiveFindings': [], 'selectorDefects': [], 'acceptedPriorCorrectionFindingIds': ['EL-IR02-001', 'EL-IR02-002', 'EL-IR02-003', 'EL-IR02-004', 'EL-IR02-005', 'EL-IR02-006'], 'acceptanceBasis': 'All 138 complete Russian/Greek delta pairs read, including all remaining sentences; all six complete corrections and all six fixed-label assemblies assessed. No equivalent wording changed for preference.'})
put('coverage.json', {'reviewer': '/root/el_independent_review_03', 'game': "No, I'm not a Human", 'version': '1.3.19', 'sourceLocale': 'ru', 'locale': 'el', 'acceptedCorpusUnits': 16538, 'freshSemanticReads': 138, 'freshAccepted': 138, 'objectiveFindings': 0, 'changedUnitsRead': 6, 'newToPriorAccepted': 24, 'explicitlyInvalidatedUnchangedRead': 114, 'currentClosure': 1704, 'exactPriorAcceptanceReusedInCurrentClosure': 1566, 'verifiedPriorIndependentAcceptedIds': 1751, 'priorReview02FreshReads': 252, 'priorReview02FreshAccepted': 246, 'priorReview02Reused': 1505, 'priorAcceptedConsumerIdsInvalidated': 4, 'retiredIds': 71, 'mandatoryFreshRead': 39, 'mandatoryExactPriorReused': 1230, 'mandatoryTotal': 1269, 'mandatoryRetired': 0, 'unexplainedMissing': 0, 'unexplainedExtra': 0, 'compiledDeltaNodes': 41, 'uncompiledDeltaIds': 0, 'historicalUncompiledQuestions': 29, 'actualLocalizeItemConsumers': 21, 'serializedDeficitKeys': 6, 'acceptedItemLabels': 7, 'correctedAssembliesDirectlyRead': 36, 'unchangedCitationAssemblyControlsVerified': 90, 'itemHintControlsVerified': 14, 'semanticAcceptance': 'clean dependency-aware delta on pinned source/glossary/current text and closure; prior complete semantic coverage remains hash-bound historical evidence', 'runtime': 'not-run', 'visual': 'not-run', 'build': 'not-run', 'gitIntegration': 'coordinator-owned', 'publication': 'not-run'})
put('verification.json', {'closureVerify': {'exitCode': 0, 'closure': 1704, 'delta': 138, 'retired': 71, 'manifestSha256': sha(EL / 'correction-cycle-003-closure-manifest.json')}, 'consumerVerify': {'exitCode': 0, 'positive': 36, 'citationControls': 90, 'itemHintControls': 14, 'reportSha256': sha(EL / 'correction-cycle-003-consumers.validation.json')}, 'freshCorpusReceipt': {'path': 'Translations/el/independent-review-03/corpus.validation.json', 'sha256': sha(HERE / 'corpus.validation.json'), 'rows': 16538, 'structuralResult': 'passed', 'exactResult': 'passed', 'boundary': 'Shared corpus structure, identity, alignment and protected values only; no semantic inference from this receipt.'}, 'independentInputProof': {'exitCode': 0, 'pins': 1365, 'previousInternalEvidencePins': 25, 'priorInputPins': 1316, 'exactPriorCurrentClosureReuse': 1566, 'freshBinaryProgramReproduced': True, 'actualProducerConsumerClassReproduced': 21}, 'derivedReproduction': 'Reused completed cycle003 derivation evidence after current exact input/output hashes matched: four changed maps, 178 static rows and 2,831 repeats. No per-batch parse pools or other-locale scans.', 'technicalMetadata': {'old_m_Script': {'m_FileID': 16777216, 'm_PathID': 41607495680}, 'native_m_Script': {'m_FileID': 1, 'm_PathID': 2480}, 'allGameplayFieldsAndSixDeficitKeys': 'exact match', 'sourceTextOrGameplayBindingChanged': False, 'scope': 'Old cached pointer-header decoding only; original evidence preserved; no universal restart.'}, 'semanticLimit': 'Validators reproduce byte/data contracts; independent decisions.jsonl records the separate complete-unit review. Serialized/compiled assemblies do not prove gameplay reachability, rendering or installation.'})
put('attempt-accounting.json', {'attempts': [{'action': 'Initial sequential closure verify, consumer verify, fresh corpus receipt', 'observer': 'exec wrapper printed output only and omitted live session ID', 'outcome': 'Fresh corpus receipt ultimately exists and matches expected current hashes; initial launcher exit code unobserved. Initial preceding verifier outcomes replaced by explicit captured verification below.'}, {'action': 'Task-owned process reconciliation', 'outcome': 'Sandbox ps denied; narrow escalated ps allowed and showed no matching task process, only the inspection itself. No process stopped.'}, {'action': 'Explicit closure verify after reconciliation', 'sessionId': 5659, 'exitCode': 0, 'outcome': 'Exact pinned manifest reproduced.'}, {'action': 'Explicit consumer verify', 'exitCode': 0, 'outcome': '36 positives and 90 controls reproduced; receipt also binds 14 item hints.'}, {'action': 'Corpus validator retry', 'exitCode': 1, 'outcome': 'Existing-output guard rejected before parsing or writing. Existing first-launch receipt was inspected and reused; no replacement performed.'}, {'action': 'Independent input/applicability verification', 'sessionId': 45329, 'exitCode': 0, 'outcome': '1,365 current pins and exact prior decision/closure/domain applicability passed.'}], 'externalNetworkRequests': 0, 'descendantAgents': 0, 'changes': 'New independent-review-03 evidence only; no authored game wording or source/glossary edits.'})
put('usage.json', {'reviewer': '/root/el_independent_review_03', 'model': 'GPT-6 family exposed by agent instructions; exact API model unknown to reviewer', 'reasoningEffort': 'unknown to reviewer', 'inputTokens': None, 'cachedInputTokens': None, 'outputTokens': None, 'reasoningTokens': None, 'totalTokens': None, 'measurement': 'Parent coordinator collects session telemetry including failed attempts. Unknown values are not zero; this report cannot measure its own tail.', 'descendantAgents': 0})
report = """# Independent Greek cycle-003 delta verdict

Reviewer: `/root/el_independent_review_03`. No, I'm not a Human 1.3.19; Russian → Greek; accepted text only.

**Clean on the pinned unchanged text and closure hashes.** All 138 complete source/target pairs were read; all six full replacements and their remaining sentences were assessed. There are zero new objective full-unit findings and zero new selector defects. No wording was authored or applied.

The six fixed-label corrections are accepted across Enerjeka, Cigarette, Coffee, CatFood, Kombucha and Povistka. Their standalone citations avoid imposing accusative case on Καφές or singular verbal agreement on Τσιγάρα. Jacket retains possession, small quantity, hope of usefulness and formal address in both separate branches; its conditional offer retains acceptability. Unstable retains the terse offer. Wheelchair retains refusal, taking/holding/waving at the entrance and invisibility; the generic offered-item deixis does not assign the cited label's gender to the player. Alt's explicit αυτό is the acceptability subject. All 36 corrected assemblies were directly read. The 15 unchanged consumer templates and their citation/deictic roles were read within the delta, with 90 label controls reproduced; 14 count/label item hints remain separately bound.

The exact current closure is 1,704 IDs: 138 fresh accepted decisions plus 1,566 unchanged exact prior acceptances. Review02's 252 fresh reads (246 acceptances and six correction proposals), 1,505 reused decisions and four explicitly invalidated prior consumer decisions reconcile to 1,751 prior accepted IDs. The new review formula yields 24 IDs absent from that set, including six corrections, plus 114 explicitly invalidated unchanged IDs. Mandatory coverage is 39 fresh + 1,230 exact prior = 1,269. All 71 retired IDs have unchanged accepted target hashes and individual selector retirement reasons; none is mandatory. Component/delta lists retain canonical order and UTF-8 LF with final newline; their hashes reproduce exactly.

The closure verifier and consumer verifier passed with captured zero exits. A fresh shared corpus receipt covers all 16,538 accepted units and is byteidentical to the author receipt. It proves structure and protected values, separately from the semantic verdict. The independent mechanical proof checked 1,365 current input pins, all 25 review02 evidence pins and 1,316 pre-application inputs reconciled against exactly eight changed authored/generated files. Prior successful derivation evidence is reused only after unchanged byte matches for four changed maps, 178 static rows and 2,831 repeats.

Fresh binary decoding reproduces every pinned Yarn instruction and label. All 41 delta nodes and their actual branch/producer order were checked. Every actual LocalizeItem producer supplies the stored deficit item and one display argument; all 21 consumers match the topology and are selected as a class. The serialized domain has six keys; seven accepted consumable labels include Bobeer as a separate item-hint label. No current delta dialogue key lacks a compiled occurrence. The historical 29 uncompiled dialogue questions remain unproved runtime reachability, outside a claim of gameplay acceptance.

The old cached OtherGameData m_Script header is 16777216/41607495680; the checked native header is 1/2480. All gameplay fields and six item keys match exactly. This is a bounded technical decoding note with unchanged source/text binding; it does not invalidate the entire semantic audit. Original evidence is preserved.

No game launch, runtime, rendered layout, fonts, images/textures, saves, installation, build/package, Git/index operation, network request, publication, deployment or descendant-agent launch was performed by this reviewer. Root owns shared acceptance and canonical integration. Model is exposed as GPT-6 family; exact API model/reasoning is unknown here. Token telemetry is coordinator-owned and remains unknown in this immutable reviewer snapshot.

The initial validation launcher lost its observer metadata but produced the fresh receipt; a narrow process inspection reconciled that no task process remained. A subsequent corpus invocation hit the existing-output guard before writing. These attempts are accounted separately in attempt-accounting.json; the initial launcher exit code is explicitly unobserved.
"""
p = HERE / 'REPORT.md'
assert not p.exists()
p.write_text(report)
for p, h in pins.items():
    assert sha(Path(p)) == h, p
evidence = {str(p.relative_to(ROOT)): sha(p) for p in sorted(HERE.iterdir()) if p.is_file()}
put('evidence-manifest.json', {'schemaVersion': 1, 'reviewer': '/root/el_independent_review_03', 'verdict': 'clean-on-pinned-unchanged-hashes', 'cycle': 3, 'locale': 'el', 'sourceInventorySha256': manifest['sourceInventorySha256'], 'sourceStaticSha256': manifest['sourceStaticSha256'], 'approvedGlossarySha256': manifest['approvedGlossarySha256'], 'closureManifestSha256': sha(EL / 'correction-cycle-003-closure-manifest.json'), 'closureIdsSha256': manifest['closure']['sha256'], 'deltaIdsSha256': manifest['deltaReview']['sha256'], 'deltaReviewRowsSha256': manifest['deltaReviewRows']['sha256'], 'freshReadAndAccepted': 138, 'reusedCurrentClosure': 1566, 'objectiveFindings': 0, 'selectorDefects': 0, 'mandatoryFresh': 39, 'mandatoryReused': 1230, 'evidencePins': evidence, 'selfHashConvention': 'Manifest excludes itself; coordinator pins its SHA-256 externally.'})
print(json.dumps({'verdict': 'clean', 'read': 138, 'reused': 1566, 'manifestSha256': sha(HERE / 'evidence-manifest.json')}))
