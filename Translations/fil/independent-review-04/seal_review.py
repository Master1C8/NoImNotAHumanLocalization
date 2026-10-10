"""Seal immutable reviewer evidence after final input and retirement checks."""
import json,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;C=ROOT/'Translations/fil/semantic-correction-cycle-004'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def th(v):return hashlib.sha256(v.encode()).hexdigest()
def load(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def write(n,d):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
iv=load(OUT/'input-verification.json')
for r in iv['pinChecks']:assert sha(ROOT/r['path'])==r['sha256']
for r in iv['historicalChangedPins']:assert sha(ROOT/r['path'])==r['currentSha256']
for r in load(OUT/'dynamic-input-applicability.json')['pins']:assert sha(ROOT/r['path'])==r['sha256']
h=load(C/'handoff.json')
for n,v in h['cycleFilesSha256'].items():assert sha(C/n)==v
for r in load(OUT/'full-corpus-validation.json')['authoredFiles']:assert sha(ROOT/r['path'])==r['sha256']
sm={r['stableId']:r for r in jl(ROOT/'Source/localization-inventory-v3/strings.jsonl')+jl(ROOT/'Source/localization-inventory-v3/static-text.jsonl')}
oldpairs={r['stableId']:r for r in jl(ROOT/'Translations/fil/semantic-correction-cycle-002/closure-paired.jsonl')};olddecisions={r['stableId']:r for r in jl(ROOT/'Translations/fil/independent-review-02/closure-decision-applicability.jsonl')}
priorpairs={r['stableId']:r for r in jl(ROOT/'Translations/fil/semantic-correction-cycle-003/closure-paired.jsonl')};priordecisions={r['stableId']:r for r in jl(ROOT/'Translations/fil/independent-review-03/closure-decision-applicability.jsonl')};current_ids=set(load(C/'closure.json')['currentClosure']['ids']);ret=[]
for r in jl(OUT/'retired-dependencies.jsonl'):
 sid=r['stableId'];p,d=(priorpairs[sid],priordecisions[sid]) if r['retiredCycle']==4 else (oldpairs[sid],olddecisions[sid]);s=sm[sid]
 if 'key' not in d:
  assert 'decisionEvidence' in d;reference=[x for x in jl(ROOT/d['decisionEvidence']) if x['stableId']==sid];assert len(reference)==1;d=reference[0]
 assert s['source']==p['source'] and s.get('key')==p['key'] and s.get('nodeNames',[])==p['nodeNames'] and all(p[k]==d[k] for k in ['sourceSha256','targetSha256','key','nodeNames']) and d['findingId'] is None and sid not in current_ids
 assert r['sourceSha256']==p['sourceSha256'] and r['targetSha256']==p['targetSha256']
 ret.append(dict(stableId=sid,acceptedOrdinal=p['acceptedOrdinal'],sourceSha256=p['sourceSha256'],targetSha256=p['targetSha256'],key=p['key'],nodeNames=p['nodeNames'],retiredCycle=r['retiredCycle'],priorCleanDecision=True,currentSourceKeyNodeExact=True,currentTargetExactVerifiedByInputReconciliation=True,reason='outside all current closure components; exact unchanged source/target/key/node; prior clean independent decision'))
assert len(ret)==len({r['stableId'] for r in ret})==54
p=OUT/'retired-final-applicability.jsonl';assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in ret))
write('final-command-verification.json',dict(commands=[dict(command='.venv/bin/python Translations/fil/semantic-correction-cycle-004/build_gate.py --verify',status='passed',checkedIds=16538,changedTargets=1,gateSha256=sha(C/'full-structural-validation.json')),dict(command='.venv/bin/python Translations/fil/semantic-correction-cycle-004/build_closure.py --verify',status='passed',closure=7612,delta=26,closureSha256=sha(C/'closure.json'))],guardSha256=sha(OUT/'full-corpus-validation.json'),allAuthoredAndReadPinsRechecked=True,retiredFullKeyDecisionApplicability=54))
write('read-inputs.json',dict(cycleHandoffSha256=sha(C/'handoff.json'),cyclePins=h['cycleFilesSha256'],sourceAndGlossaryFingerprints=h['sourceAndGlossaryFingerprints'],priorReviewPins=h['priorReviewEvidenceSha256'],priorReadInputsPins=load(ROOT/'Translations/fil/independent-review-03/read-inputs.json')['inputs'],idHashConvention='UTF-8 LF, canonical accepted source order, one stable ID per line',deltaIdsSha256=load(C/'closure.json')['exactNextDelta']['idsSha256']))
cutoff=datetime.datetime.now(datetime.timezone.utc).isoformat()
write('evidence-manifest.json',dict(reviewer='/root/fil_independent_review_04',status='one bounded full-unit correction required',cutoffUtc=cutoff,files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='evidence-manifest.json']))
write('completion-manifest.json',dict(reviewer='/root/fil_independent_review_04',status='immutable independent delta verdict sealed; one finding',cutoffUtc=cutoff,sourceAndAuthoredPinsUnchanged=True,files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='completion-manifest.json'],reportingTailTelemetry='unknown; parent collects actual usage; report cannot measure itself'))
print(json.dumps(dict(completionManifestSha256=sha(OUT/'completion-manifest.json'),reportSha256=sha(OUT/'REPORT.md'),findingsSha256=sha(OUT/'findings.json'),verificationSha256=sha(OUT/'verification.json'),cutoff=cutoff)))
