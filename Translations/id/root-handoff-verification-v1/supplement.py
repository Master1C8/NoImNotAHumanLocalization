"""Additional read-only applicability checks, reusing the completed main verification."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
def read(p): return json.loads((ROOT/p).read_text())
def sha(b): return hashlib.sha256(b).hexdigest()
initial = read('Translations/id/independent-review-03/verification-initial.json')
pins = {}
for r in initial['pins']:
    assert sha((ROOT/r['path']).read_bytes()) == r['sha256']
    if r['path'] in pins: assert pins[r['path']] == r['sha256']
    pins[r['path']] = r['sha256']

spec = importlib.util.spec_from_file_location('compiled_ctx',ROOT/'Translations/id/independent-review-01/compiled_context.py')
m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
nodes,programsha = m.load()
saved = read('Translations/id/independent-review-03/compiled-context.json')
assert saved['programSha256'] == programsha == initial['compiledProgramSha256']
for name,rows in saved['nodes'].items():
    assert nodes[name] == [{k:r[k] for k in ('index','opcode','operands')} for r in rows]
phone = read('Translations/id/semantic-correction-cycle-02/source-only-context-manifest.json')
assert sha((ROOT/phone['selector']['inventoryPath']).read_bytes()) == phone['selector']['inventorySha256']
source = [json.loads(s) for s in (ROOT/phone['selector']['inventoryPath']).read_text().splitlines()]
expected = [r for r in source if r['collection'] == phone['selector']['collection'] and (r.get('key') or '').startswith(phone['selector']['keyPrefix'])]
actual = [json.loads(s) for s in (ROOT/phone['contextRowsPath']).read_text().splitlines()]
assert len(expected) == len(actual) == phone['selector']['expectedRows'] == 60
for e,a in zip(expected,actual):
    assert all(e[k] == a[k] for k in ('stableId','collection','key','nodeNames','source'))
    assert a['sourceSha256'] == sha(e['source'].encode())
manifest = read('Source/preserve-exactly-v4.json')
valid = {r['stableId'] for r in manifest['tableRows']+manifest['staticRows']}
assert not valid & {r['stableId'] for r in actual}

allow = {
 'Translations/id/correction-progress.json': {'stage','independentDeltaReview','editorialAcceptance','nextAction','independentDeltaReviewer03','independentDeltaReviewedUnits03','independentDeltaFindings03','unresolvedObjectiveFindings','finalGate','rootHandoffPath'},
 'Translations/id/semantic-review-progress.json': {'independentDiffReview','editorialAcceptance','correctionCycleProgressSha256','independentDeltaReviewer03','independentDeltaReviewedUnits03','independentDeltaFindings03','unresolvedObjectiveFindings','finalGateReceiptFile','finalGateReceiptSha256'},
}
for e in read('Translations/id/final-gate/administrative-update.json')['changedFiles']:
    assert sha((ROOT/e['beforeSnapshot']).read_bytes()) == e['beforeSha256']
    assert sha((ROOT/e['path']).read_bytes()) == e['afterSha256']
    if e['path'] in allow:
        a,b = read(e['beforeSnapshot']),read(e['path'])
        modified = {k for k in set(a)|set(b) if a.get(k)!=b.get(k)}
        assert modified == allow[e['path']]
    else:
        assert e['path'] == 'Translations/id/STATUS.md'

base = read('Translations/id/root-handoff-verification-v1/verification.json')
assert base['status'].startswith('VERIFIED') and not base['substantiveFindings']
result = {'status':'VERIFIED supplemental input/context applicability',
 'mainVerificationSha256':sha((OUT/'verification.json').read_bytes()),
 'review03InitialPins':{'checks':len(initial['pins']),'distinctPaths':len(pins),'mismatches':0},
 'sourceOnlyContext':{'exactProjectedRows':60,'acceptedOverlap':0},
 'compiledContext':{'programSha256':programsha,'savedNodesExactToCurrentWireDecodedProgram':len(saved['nodes']),'boundary':'Static wire decoding; no VM execution or global reachability proof'},
 'administrativeJsonFields':{'allowlistsExact':True,'beforeAndAfterHashesExact':True,'statusMarkdownDiff':'Reviewed directly: current final-gate narrative, historical cycle-03 heading and editorial stage row only'},
 'verifierAttempts':[{'attempt':1,'result':'Main verifier stopped before writing any result because local canonical-line test used tab delimiter; manifest digest verified with actual single-space path/hash convention'},
                      {'attempt':2,'result':'Main verifier passed all evidence reconstruction and finalizer checks; only designated verifier directory written'},
                      {'attempt':3,'result':'Supplement adds previously untested exact underlying review03 pin, source-only projection, decoded consumer and administrative allowlist checks; no repeat of full finalizer'}],
 'preservedAuthorHandoffSha256':sha((ROOT/'Translations/id/final-gate/root-handoff.json').read_bytes())}
(OUT/'supplement.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'reportSha256':sha((OUT/'supplement.json').read_bytes()),'sourceOnlyRows':60,'compiledNodes':len(saved['nodes'])}))
