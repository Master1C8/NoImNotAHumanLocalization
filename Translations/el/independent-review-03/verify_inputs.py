"""Read-only reconciliation for independent Greek cycle-003 review.

Outputs are new files under this review directory. This is a mechanical proof,
not a semantic reviewer or a translation generator.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EL = ROOT / 'Translations/el'
PINS = {}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def td(value):
    return hashlib.sha256(value.encode()).hexdigest()

def read(p):
    return json.loads(p.read_text())

def rows(p):
    return [json.loads(x) for x in p.read_text().splitlines()]

def pin(p, expected=None):
    p = Path(p)
    if not p.is_absolute():
        p = ROOT / p
    actual = sha(p)
    if expected is not None:
        assert actual == expected, str(p)
    PINS[str(p)] = actual
    return actual

def put(name, value):
    p = HERE / name
    content = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if p.exists():
        assert p.read_text() == content, str(p)
    else:
        p.write_text(content)

m = read(EL / 'correction-cycle-003-closure-manifest.json')
pin(EL / 'correction-cycle-003-closure-manifest.json', '656bdda477f04194de8a7e4e9989215b563c39d39db121ad5b3e062cc78469c5')
for group in list(m['components'].values()) + [m[k] for k in ('closure', 'new', 'invalidated', 'deltaReview', 'retired', 'closureReviewRows', 'deltaReviewRows', 'retiredEvidence', 'invalidationEvidence')]:
    pin(group['path'], group['sha256'])
for p, h in [('Source/localization-inventory-v3/strings.jsonl', m['sourceInventorySha256']), ('Source/localization-inventory-v3/static-text.jsonl', m['sourceStaticSha256']), ('Documentation/glossary-translations/el/layer.json', m['approvedGlossarySha256'])]:
    pin(p, h)
for f in m['currentTargetFiles']:
    pin(f['path'], f['sha256'])
for f in m['authoredAndGeneratedFiles']:
    pin(f['path'], f['afterSha256'])
previous = read(EL / 'independent-review-02/evidence-manifest-v2.json')
pin(EL / 'independent-review-02/evidence-manifest-v2.json', m['review02EvidenceManifestSha256'])
for p, h in previous['immutableEvidencePins'].items():
    pin(p, h)
original_pins = read(EL / 'independent-review-02/final-input-hashes.json')['pins']
changed_files = {str(ROOT / f['path']): f for f in m['authoredAndGeneratedFiles']}
for p, h in original_pins.items():
    if p in changed_files:
        assert h == changed_files[p]['beforeSha256']
        pin(p, changed_files[p]['afterSha256'])
    else:
        pin(p, h)
assert len(original_pins) == 1316 and len(changed_files) == 8

source = {r['stableId']: r for p in ('strings.jsonl', 'static-text.jsonl') for r in rows(ROOT / 'Source/localization-inventory-v3' / p)}
current = {r['stableId']: r for r in rows(EL / 'correction-cycle-003-closure-review.jsonl')}
delta = rows(EL / 'correction-cycle-003-delta-review.jsonl')
ds = {r['stableId'] for r in delta}
assert len(delta) == len(ds) == 138 and len(current) == 1704
proof = read(EL / 'independent-review-02/final-coverage-and-invalidation-proof.json')
old = rows(EL / 'independent-review-01/decisions.jsonl')
prior = {}
for r in proof['remainingReusedDecisions']:
    o = old[r['previousDecisionIndex']]
    assert o['stableId'] == r['stableId']
    assert o['fullSourceAndCurrentTargetRead'] and o['decision'] == 'accepted-current-wording'
    assert o['sourceSha256'] == r['sourceSha256'] == td(source[r['stableId']]['source'])
    assert o['currentTargetSha256'] == r['targetSha256']
    assert o['glossaryFingerprint'] == m['approvedGlossarySha256']
    prior[r['stableId']] = {'origin': 'review01-reused-by-review02', 'sourceSha256': r['sourceSha256'], 'targetSha256': r['targetSha256']}
fresh = rows(EL / 'independent-review-02/decisions.jsonl') + rows(EL / 'independent-review-02/bounded-additional-decisions.jsonl')
assert len(fresh) == 252 and len(prior) == 1505
for r in fresh:
    assert r['fullSourceAndCurrentTargetRead']
    assert r['sourceSha256'] == td(source[r['stableId']]['source'])
    assert r['glossaryFingerprint'] == m['approvedGlossarySha256']
    if r['decision'] == 'accepted-current-wording':
        assert r['stableId'] not in prior
        prior[r['stableId']] = {'origin': 'review02-fresh-accepted', 'sourceSha256': r['sourceSha256'], 'targetSha256': r['currentTargetSha256']}
assert len(prior) == 1751
changed = set((ROOT / m['components']['changed']['path']).read_text().splitlines())
invalidated = set((ROOT / m['invalidated']['path']).read_text().splitlines())
assert ds == changed | (set(current) - set(prior)) | invalidated
assert len(changed) == 6 and len(set(current) - set(prior)) == 24 and len(invalidated) == 114
reuse = []
for sid in current.keys() - ds:
    r, o = current[sid], prior[sid]
    assert not r['invalidationReasons']
    assert r['sourceSha256'] == o['sourceSha256'] == td(source[sid]['source'])
    assert r['currentTargetSha256'] == o['targetSha256']
    reuse.append({'stableId': sid, **o})
reuse.sort(key=lambda r: current[r['stableId']]['ordinal'])
assert len(reuse) == 1566
mandatory = set((ROOT / m['components']['mandatory-regression']['path']).read_text().splitlines())
assert len(mandatory) == 1269 and len(mandatory & ds) == 39 and len(mandatory - ds) == 1230
assert mandatory - ds <= {r['stableId'] for r in reuse}
retired = read(EL / 'correction-cycle-003-retired-evidence.json')
assert len(retired) == 71 and not {r['stableId'] for r in retired} & mandatory
for r in retired:
    assert r['targetSha256'] == prior[r['stableId']]['targetSha256']
    assert r['reason'] == 'No current-cycle dependency selector matches; source, glossary and target unchanged from the independently read prior value.'
assert set(proof['newlyInvalidatedPriorAcceptedIds']) <= changed and len(proof['newlyInvalidatedPriorAcceptedIds']) == 4

# Fresh parse of the pinned binary program; preserve all branch instructions.
reader = EL / 'independent-review-01/read_compiled.py'
pin(reader)
ns = {'__file__': str(reader)}
exec(reader.read_text().split('if sys.argv[1]')[0], ns)
cached = read(EL / 'independent-review-01/compiled-context.json')
assert ns['nodes'] == cached['nodes']
assert hashlib.sha256(ns['raw']).hexdigest() == cached['compiledSha256']
pin(cached['runtimeBindingPath'], cached['runtimeBindingSha256'])
occ, actual = {}, []
for name, node in ns['nodes'].items():
    ins = node['instructions']
    for i, instruction in enumerate(ins):
        if instruction['args'] and isinstance(instruction['args'][0], str) and instruction['args'][0].startswith('line:'):
            occ.setdefault(instruction['args'][0], []).append({'node': name, **instruction})
        if instruction['opcode'] == 12 and instruction['args'] == ['LocalizeItem']:
            assert ins[i-2]['opcode'] == 13 and ins[i-2]['args'] == ['$deficitItem']
            assert ins[i-1]['opcode'] == 7 and ins[i-1]['args'] == [1.0]
            assert ins[i+1]['opcode'] == 2 and ins[i+1]['args'][1] == 1.0
            actual.append((name, i+1, ins[i+1]['args'][0]))
topology = read(EL / 'independent-review-02/bounded-consumer-topology.json')
assert set(actual) == {(r['node'], r['pc'], r['row']['key']) for r in topology['consumerRows']}
assert len(actual) == 21
chosen = {o['node'] for r in delta for o in occ.get(r['key'], [])}
uncompiled = [r['stableId'] for r in delta if r['collection'] == 'Dialogs' and not occ.get(r['key'])]
put('compiled-delta-context.json', {'compiledSha256': cached['compiledSha256'], 'runtimeBindingSha256': cached['runtimeBindingSha256'], 'nodes': {n: ns['nodes'][n] for n in ns['nodes'] if n in chosen}, 'uncompiledDeltaIds': uncompiled, 'actualLocalizeItemProducerConsumers': actual})

# Reuse unchanged successful derivation evidence, with every current byte pinned.
derived = read(EL / 'correction-cycle-003-derived.validation.json')
pin(EL / 'correction-cycle-003-derived.validation.json', '7349c6f7a8417a627ed65e58719a57749f44f0eda5dfaadfde8058a8e22d5fe7')
for r in derived['orderedMaps']:
    pin(r['map'], r['mapSha256']); pin(r['batch'], r['batchSha256'])
pin(EL / 'static-lexicon-001.authored.json', derived['static']['lexiconSha256'])
pin(EL / 'static-text-draft.json', derived['static']['draftSha256'])
pin(EL / 'dialogue-repeats-001.authored.json', derived['repeated']['authoredMapSha256'])
pin(EL / 'dialogue-batch-006.json', derived['repeated']['batchSha256'])
assert derived['repeated']['rows'] == 2831 and derived['static']['rows'] == 178
receipt = read(HERE / 'corpus.validation.json')
assert receipt['authoredFiles'] == m['currentTargetFiles']
assert receipt['rows'] == 16538 and receipt['structuralResult'] == receipt['exactResult'] == 'passed'
assert sha(HERE / 'corpus.validation.json') == m['corpusValidationSha256']
for p in [EL / 'build_cycle3_closure.py', EL / 'verify_cycle3_consumers.py', EL / 'correction-cycle-003-selectors.json', EL / 'correction-cycle-003-adjudication.json', EL / 'correction-cycle-003-applied.json', ROOT / 'Scripts/validate_locale_corpus.py', ROOT / 'Scripts/locale_text_inputs.py', Path(__file__)]:
    pin(p)
for p, h in PINS.items():
    assert sha(Path(p)) == h, p
put('applicability-proof.json', {'freshDeltaIds': 138, 'reusedCurrentClosureDecisions': reuse, 'reusedCount': 1566, 'priorIndependentAcceptedCount': 1751, 'priorFreshRead': 252, 'priorFreshAccepted': 246, 'priorReused': 1505, 'priorNewlyInvalidatedAcceptedIds': proof['newlyInvalidatedPriorAcceptedIds'], 'closure': 1704, 'mandatoryFresh': 39, 'mandatoryReused': 1230, 'mandatoryTotal': 1269, 'retiredCount': 71, 'mandatoryRetiredCount': 0, 'retiredEvidenceSha256': sha(EL / 'correction-cycle-003-retired-evidence.json'), 'zeroMissingOrExtra': True, 'derivedEvidenceReused': derived, 'review02InternalPinsVerified': len(previous['immutableEvidencePins']), 'priorInputPinsReconciled': 1316, 'currentChangedAuthoredAndGeneratedFiles': 8, 'deltaCompiledNodes': len(chosen), 'uncompiledDeltaIds': uncompiled, 'actualProducerConsumersReproduced': 21, 'fullProgramReproduced': True})
put('input-pins.json', {'scope': 'SHA-256 exact original file bytes; final verification cutoff before report seal', 'pins': PINS})
print(json.dumps({'result': 'passed', 'inputPins': len(PINS), 'closureReuse': len(reuse), 'mandatoryFresh': 39, 'mandatoryReuse': 1230, 'compiledNodes': len(chosen), 'uncompiledDeltaIds': len(uncompiled), 'actualConsumers': 21}))
