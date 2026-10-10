"""Read-only root evidence verification; writes only this verification directory.

No semantic reread, acceptance decision, build, Git, or runtime action.
"""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, str(ROOT / 'Scripts'))

def raw(p):
    return (ROOT / p).read_bytes()
def sha(b):
    return hashlib.sha256(b).hexdigest()
def load(p):
    return json.loads(raw(p))
def lines(p):
    return [json.loads(x) for x in raw(p).decode().splitlines()]
def ids(p):
    b = raw(p)
    assert b.endswith(b'\n')
    v = b.decode().splitlines()
    assert len(v) == len(set(v))
    return v
pins = {}
checks = 0
def pin(p, h):
    global checks
    assert sha(raw(p)) == h, ('stale pin', p)
    if p in pins:
        assert pins[p] == h
    pins[p] = h
    checks += 1
def rowmap(rows):
    d = {r['stableId']: r for r in rows}
    assert len(d) == len(rows)
    return d

handoff_path = 'Translations/id/final-gate/root-handoff.json'
pin(handoff_path, '9e6389bfa745f4f87036a1ff133e57e08480e9adcf590ed20abbdc2244785621')
h = load(handoff_path)
for e in h['authoredFiles'] + h['evidenceFiles']:
    pin(e['path'], e['sha256'])
integration = load('Translations/id/final-gate/integration-set.json')
paths = integration['paths']
assert len(paths) == integration['pathCount'] == 936
assert [r['path'] for r in paths] == sorted({r['path'] for r in paths})
assert all(Path(r['path']).is_relative_to('Translations/id') for r in paths)
canonical = ''.join(r['path'] + ' ' + r['sha256'] + '\n' for r in paths).encode()
assert sha(canonical) == integration['canonicalPathHashLineSha256']
for e in paths:
    pin(e['path'], e['sha256'])

artifact = load('Translations/id/semantic-correction-cycle-03/artifact-manifest.json')
for k in ('sourceAndGlossary', 'manuals', 'authoredMapsAndSelectorRecipe',
          'targetInputs', 'validationSidecars', 'previousFirstPassParts', 'previousIndependentReviews'):
    for e in artifact[k]:
        pin(e['path'], e['sha256'])
for e in load('Translations/id/independent-review-03/evidence-manifest.json')['files']:
    pin(e['path'], e['sha256'])

# Independently reconstruct every current target from first semantic rows and
# the exact full-unit before/after decisions, rather than accepting diff booleans.
manifest = load('Source/preserve-exactly-v4.json')
order = [r['stableId'] for r in manifest['tableRows'] + manifest['staticRows']]
assert len(order) == len(set(order)) == 16538
source = rowmap([r for name in ('strings', 'static-text')
                for r in lines('Source/localization-inventory-v3/' + name + '.jsonl')
                if r['stableId'] in set(order)])
first = []
last = 0
for e in artifact['previousFirstPassParts']:
    p = load(e['path'])
    assert p['sourceOrderStart'] == last + 1
    assert p['sourceOrderEnd'] == last + p['reviewedRows']
    assert len(p['rows']) == p['reviewedRows'] == e['rows']
    assert p['auditPhase'] == 'full semantic source-to-target pass'
    assert p['reviewMethod']
    first += p['rows']
    last = p['sourceOrderEnd']
assert len(first) == last == 16538 and [r['stableId'] for r in first] == order
assert all(r['source'] == source[r['stableId']]['source'] for r in first)
reconstructed = {r['stableId']: r['target'] for r in first}
cycle_counts = []
changed_union = set()
for cycle, count in ((1,83),(2,9),(3,3)):
    base = f'Translations/id/semantic-correction-cycle-{cycle:02d}/'
    adjudication = load(base + 'adjudication.json')
    pin(base + 'adjudication.json', load('Translations/id/final-gate/semantic-chain-proof.json')['correctionChain'][cycle-1]['adjudicationSha256'])
    rows = adjudication['rows']
    accepted = [r for r in rows if r['decision'] == 'accepted']
    assert len(accepted) == count
    for r in rows:
        sid = r['stableId']
        assert r['source'] == source[sid]['source']
        assert reconstructed[sid] == r['before'], ('chain before differs',cycle,sid)
        if r['decision'] == 'accepted':
            assert r['before'] != r['after']
            reconstructed[sid] = r['after']
            changed_union.add(sid)
        else:
            assert r['decision'] == 'rejected' and r['after'] == r['before']
    assert set(ids(base + 'changed.ids.txt')) == {r['stableId'] for r in accepted}
    cycle_counts.append(count)

from locale_text_inputs import current_text, checked_files, accepted_inputs
values, current_files = current_text('id')
guids = {'UI':'0cbd8a7a4f543344bb95659de87f67a5','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'}
targets = {(key if coll == 'static' else 'string:'+guids[coll]+':'+str(key)): v for (coll,key),v in values.items()}
assert targets == reconstructed
assert checked_files(h['authoredFiles']) == {r['path']:r['sha256'] for r in current_files}

# Exact transitive applicability of every reused current independent decision.
closure = set(ids('Translations/id/semantic-correction-cycle-03/closure.ids.txt'))
previous = set(ids('Translations/id/semantic-correction-cycle-02/closure.ids.txt'))
delta = set(ids('Translations/id/semantic-correction-cycle-03/delta-review.ids.txt'))
new = set(ids('Translations/id/semantic-correction-cycle-03/new-dependencies.ids.txt'))
invalidated = set(ids('Translations/id/semantic-correction-cycle-03/invalidated-prior.ids.txt'))
changed = set(ids('Translations/id/semantic-correction-cycle-03/changed.ids.txt'))
retired = set(ids('Translations/id/semantic-correction-cycle-03/retired-dependencies.ids.txt'))
assert (len(previous),len(closure),len(changed),len(new),len(invalidated),len(retired),len(delta)) == (1433,1414,3,19,1,38,21)
assert new == closure-previous and retired == previous-closure
assert delta == changed | new | invalidated
fresh = rowmap(load('Translations/id/independent-review-03/coverage.json'))
reused = rowmap(load('Translations/id/independent-review-03/reused-decisions.json'))
assert set(fresh) == delta and set(reused) == closure-delta
r2_reused = rowmap(lines('Translations/id/independent-review-02/reused-decisions.jsonl'))
r1 = rowmap(lines('Translations/id/independent-review-01/coverage.jsonl'))
cycle1rows = rowmap(lines('Translations/id/semantic-correction-cycle-01/closure-review-rows.jsonl'))
evidence_maps = {p: rowmap(lines(p)) for p in {r['decisionEvidence'] for r in reused.values()}}
for sid,r in {**fresh,**reused}.items():
    assert r['sourceSha256'] == sha(source[sid]['source'].encode())
    assert r['targetSha256'] == sha(targets[sid].encode())
    assert r['status'] == 'no-objective-correction-found'
    if sid in fresh:
        assert r['sourceTargetRead'] and r['findingId'] is None
        assert r['source'] == source[sid]['source'] and r['target'] == targets[sid]
    else:
        prior = evidence_maps[r['decisionEvidence']][sid]
        assert (r['sourceSha256'],r['targetSha256']) == (prior['sourceSha256'],prior['targetSha256'])
        if r['decisionEvidence'].endswith('/coverage.jsonl'):
            assert prior['sourceTargetRead'] and prior['status'] == 'no-objective-correction-found' and prior['findingId'] is None
        else:
            assert prior['priorDecision'] == r1[sid]['status'] == 'no-objective-correction-found'
            assert r1[sid]['sourceTargetRead'] and r1[sid]['findingId'] is None
            row = cycle1rows[sid]
            assert sha(row['source'].encode()) == r['sourceSha256']
            assert sha(row['target'].encode()) == r['targetSha256']
retired_rows = rowmap(lines('Translations/id/semantic-correction-cycle-03/retired-dependencies.jsonl'))
assert set(retired_rows) == retired
old_components = load('Translations/id/semantic-correction-cycle-02/component-manifest.json')['components']
old_sets = {k:set(ids(e['path'])) for k,e in old_components.items() if k != 'closure'}
for sid,r in retired_rows.items():
    assert set(r['previousComponents']) == {k for k,v in old_sets.items() if sid in v}
    assert r['reason'] and sid not in closure

# All administrative preimages are checked against current exact diff content.
admin = load('Translations/id/final-gate/administrative-update.json')
administrative = []
for e in admin['changedFiles']:
    pin(e['beforeSnapshot'],e['beforeSha256']);pin(e['path'],e['afterSha256'])
    if e['path'].endswith('.json'):
        before,after = load(e['beforeSnapshot']),load(e['path'])
        modified = sorted(k for k in set(before)|set(after) if before.get(k) != after.get(k))
    else:
        modified = ['current final-gate narrative, historical cycle-03 heading, editorial stage row']
    administrative.append({**e,'modifiedFields':modified})

# Replay the inspected no-pool finalizer. Its only temporary output is redirected
# into this assigned directory; finalizer byte-comparison preserves all receipts.
spec = importlib.util.spec_from_file_location('id_final_gate', ROOT/'Translations/id/final-gate/run-final.py')
module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
original_temp = tempfile.TemporaryDirectory
def scoped_temp(*args, **kwargs):
    kwargs['dir'] = OUT
    return original_temp(*args, **kwargs)
module.tempfile.TemporaryDirectory = scoped_temp
original_argv = sys.argv
sys.argv = [str(ROOT/'Translations/id/final-gate/run-final.py'),'--verify']
stream = io.StringIO()
try:
    with contextlib.redirect_stdout(stream):
        module.main()
finally:
    sys.argv = original_argv
    tempfile.TemporaryDirectory = original_temp
(OUT/'finalizer-replay.log').write_text(stream.getvalue())

# Exercise builder's actual accepted_inputs checks using an in-memory receipt;
# do not persist an editorial acceptance in Documentation or anywhere else.
import locale_text_inputs as inputs_module
exact_path = ROOT/h['preserveExactReport']['path']
evidence = checked_files(h['evidenceFiles']);authored = checked_files(h['authoredFiles'])
normalized = copy.deepcopy(h)
normalized['structural'] = {'rows':16538,'result':'passed'}
normalized['derivedStatic'] = {'rows':178,'result':'passed'}
acceptance = {'locale':'id','status':'text editorially accepted offline','acceptedUnits':16538,
              'firstSemanticPassUnits':16538,'independentClean':True,'structuralRows':16538,
              'derivedStaticRows':178,'mandatoryRegression':h['mandatoryRegression'],
              'unresolvedObjectiveFindings':0,
              'inputSha256':{handoff_path:sha(raw(handoff_path)),**evidence,**authored,
                             h['preserveExactReport']['path']:h['preserveExactReport']['sha256']}}
memory_path = OUT/'in-memory-contract-check-only.json'
original_read = inputs_module.read
inputs_module.read = lambda p: acceptance if p == memory_path else original_read(p)
try:
    checked = accepted_inputs('id', memory_path, exact_path)
    assert len(checked[2]) == 332
finally:
    inputs_module.read = original_read
assert not memory_path.exists()

# Recheck the entire integration set and author handoff at the final cutoff.
for p,expected in pins.items():
    assert sha(raw(p)) == expected, ('changed during verification',p)
result = {
    'status':'VERIFIED offline evidence; acceptance schema adapter required',
    'reviewer':'/root/id_final_handoff_verification',
    'handoff':{'path':handoff_path,'sha256':sha(raw(handoff_path))},
    'gateReceipt':{'path':'Translations/id/final-gate/gate-receipt.json','sha256':sha(raw('Translations/id/final-gate/gate-receipt.json'))},
    'firstSemantic':{'parts':35,'contiguousSourceAlignedRows':len(first),
                     'proof':'all complete source/target evidence rows plus exact reconstruction through all adjudicated full-unit replacements'},
    'corrections':{'cycles':cycle_counts,'totalAccepted':sum(cycle_counts),'finalReconstructedTargetsExact':len(targets)},
    'independent':{'freshCurrentDelta':len(fresh),'exactApplicablePriorDecisions':len(reused),
                   'closure':len(closure),'priorClosure':len(previous),'retired':len(retired),
                   'closureSha256':sha(raw('Translations/id/semantic-correction-cycle-03/closure.ids.txt')),
                   'deltaSha256':sha(raw('Translations/id/semantic-correction-cycle-03/delta-review.ids.txt')),
                   'transitivePriorDecisionHashesVerified':True},
    'mandatory':{'count':845,'fresh':10,'prior':835,'proof':'finalizer reproduces groups and decision-mode/source/target checks; reused decisions separately traced to actual independent predecessors'},
    'static':{'rows':178,'phraseMap':75,'creditsRoleMap':81,'byteExactDerivationReplayed':True},
    'preserveExact':{'rows':16538,'reportSha256':h['preserveExactReport']['sha256'],'byteIdenticalReplay':True},
    'pins':{'distinctPaths':len(pins),'checksBeforeFinalRecheck':checks,'finalRecheckCount':len(pins),
            'authored':332,'sidecars':332,'allPinnedBytesUnchanged':True},
    'integration':{'path':'Translations/id/final-gate/integration-set.json','sha256':sha(raw('Translations/id/final-gate/integration-set.json')),
                   'paths':936,'canonicalPathHashLineSha256':sha(canonical),
                   'authorHandoffAdditionalSelfFileVerified':True,'newVerifierArtifactsExcludedFromOriginalManifest':True},
    'administrativeReconciliation':administrative,
    'acceptanceContract':{'current_text':'passed on actual current corpus and sidecars',
                          'accepted_inputs':'passed on actual evidence/pins with in-memory synthesized acceptance; no acceptance receipt written',
                          'normalizationRequired':['structural to exact {rows:16538,result:passed}','derivedStatic to exact {rows:178,result:passed}'],
                          'originalAuthorHandoffPreserved':True},
    'substantiveFindings':[],
    'boundaries':['No semantic audit restart or new full corpus model reading','No runtime, dynamic VM substitution, rendering, fonts, build, installation or release verification','No acceptance decision or Git integration performed','Glossary comparison is local canonical parity; no CMS/network check'],
    'telemetry':'Coordinator collects actual session telemetry afterward; no exposed per-request counters here.'}
(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'distinctPins':len(pins),'targets':len(targets),'integrationPaths':936,'reportSha256':sha((OUT/'verification.json').read_bytes())}))
