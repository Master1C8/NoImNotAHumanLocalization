"""Seal review evidence without modifying historical or localization inputs."""
import json,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;C=ROOT/'Translations/fil/semantic-correction-cycle-003'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def write(n,d):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
for r in load(OUT/'input-verification.json')['pinChecks']:assert sha(ROOT/r['path'])==r['expected']
for r in load(OUT/'input-verification.json')['historicalChangedPins']:assert sha(ROOT/r['path'])==r['currentSha256']
for r in load(OUT/'full-corpus-validation.json')['authoredFiles']:assert sha(ROOT/r['path'])==r['sha256']
h=load(C/'handoff.json')
for n,v in h['cycleFilesSha256'].items():assert sha(C/n)==v
paths=[ROOT/'Source/glossary-corpus-v2/runtime-bindings.json',ROOT/'Source/preserve-exactly-v4.json',ROOT/'dynamic-producer-context.json',ROOT/'Scripts/validate_locale_corpus.py',ROOT/'Scripts/locale_text_inputs.py',C/'handoff.json']
paths += [Path('/Users/antonkrutov/.codex/instructions')/n for n in ['sitefor-mods.md','game-localization-prompt.md','game-localization-audit-workflow.md']]
paths += [Path('/Users/antonkrutov/.codex/skills/vn-game-localize')/'SKILL.md']
write('read-inputs.json',dict(inputs=[dict(path=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),sha256=sha(p)) for p in paths],cyclePins=h['cycleFilesSha256'],sourceAndGlossaryFingerprints=h['sourceAndGlossaryFingerprints'],priorReviewPins=h['priorReviewEvidenceSha256']))
write('final-command-verification.json',dict(commands=[dict(command='.venv/bin/python Translations/fil/semantic-correction-cycle-003/build_gate.py --verify',result='passed',checkedIds=16538,changedTargets=2,gateSha256=sha(C/'full-structural-validation.json')),dict(command='.venv/bin/python Translations/fil/semantic-correction-cycle-003/build_closure.py --verify',result='passed',closureSha256=sha(C/'closure.json'),closure=7604,delta=20)],guardReceiptSha256=sha(OUT/'full-corpus-validation.json'),guardCurrentAuthoredInputsRechecked=True))
cutoff=datetime.datetime.now(datetime.timezone.utc).isoformat()
write('evidence-manifest.json',dict(reviewer='/root/fil_independent_review_03',cutoffUtc=cutoff,status='one objective correction required',files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='evidence-manifest.json']))
write('completion-manifest.json',dict(reviewer='/root/fil_independent_review_03',cutoffUtc=cutoff,status='review sealed; one bounded correction required',sourceAndAuthoredPinsUnchanged=True,files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='completion-manifest.json'],reportingTailTelemetry='unknown; parent collects actual usage; current report cannot measure itself'))
print(json.dumps(dict(completionManifestSha256=sha(OUT/'completion-manifest.json'),reportSha256=sha(OUT/'REPORT.md'),findingsSha256=sha(OUT/'findings.json'),verificationSha256=sha(OUT/'verification.json'),cutoff=cutoff)))
