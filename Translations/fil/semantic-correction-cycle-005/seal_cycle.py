#!/usr/bin/env python3
"""Seal cycle005 correction evidence and exact mutable-checkpoint snapshot."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];CYCLE=Path(__file__).resolve().parent;FIL=ROOT/'Translations/fil'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
def main():
 out=CYCLE/'completion-manifest.json';require(not out.exists(),'Immutable cycle already sealed')
 handoff=load(CYCLE/'handoff.json')
 for name,h in handoff['cycleFilesSha256'].items():require(sha(CYCLE/name)==h,'Handoff file differs: '+name)
 for pin in handoff['sourceAndGlossaryFingerprints'].values():require(sha(ROOT/pin['path'])==pin['sha256'],'Source/glossary differs')
 gate=load(CYCLE/'full-structural-validation.json')
 for pin in gate['authoredFiles']:require(sha(ROOT/pin['path'])==pin['sha256'],'Current authored input differs')
 require(sha(ROOT/gate['affectedValidationPath'])==gate['affectedValidationSha256'],'Affected sidecar differs')
 v=load(CYCLE/'verification.json')
 for name,h in v['filesSha256'].items():require(sha(CYCLE/name)==h,'Applicability evidence differs')
 receipt=load(CYCLE/'full-corpus-validation.json')
 require(sha(ROOT/'Scripts/validate_locale_corpus.py')==receipt['validatorSha256'] and sha(ROOT/'Scripts/locale_text_inputs.py')==receipt['inputLoaderSha256'],'Owning guard code changed')
 for name,h in receipt['owningValidators'].items():require(sha(ROOT/'Scripts'/name)==h,'Owning validator changed')
 review=FIL/'independent-review-04'
 require(sha(review/'completion-manifest.json')==handoff['review04CompletionManifestSha256'],'Review04 seal changed')
 for pin in load(review/'completion-manifest.json')['files']:require(sha(ROOT/pin['path'])==pin['sha256'],'Immutable review04 artifact changed')
 checkpoint=load(FIL/'progress.json')['checkpointNotes']['semanticCorrectionCycle005']
 require(checkpoint['handoffSha256']==sha(CYCLE/'handoff.json') and checkpoint['closureSha256']==sha(CYCLE/'closure.json') and checkpoint['reportSha256']==sha(CYCLE/'REPORT.md'),'Checkpoint differs')
 require(not (CYCLE/'after-progress.json').exists(),'Checkpoint snapshot exists')
 (CYCLE/'after-progress.json').write_bytes((FIL/'progress.json').read_bytes())
 files=[p for p in CYCLE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
 manifest={'schemaVersion':1,'locale':'fil','status':'immutable author correction cycle005 sealed; exact141-pair distinct review pending','correctionOrdinal':9614,'draftUnits':16538,'editoriallyAcceptedUnits':0,'currentClosure':7678,'nextReviewDelta':141,'closureSha256':sha(CYCLE/'closure.json'),'handoffSha256':sha(CYCLE/'handoff.json'),'review04CompletionManifestSha256':sha(review/'completion-manifest.json'),'firstPassProgressPreservedSha256':sha(FIL/'semantic-review-progress.json'),'sourceAndGlossaryUnchanged':True,'currentProgressPath':'Translations/fil/progress.json','currentProgressSha256':sha(FIL/'progress.json'),'immutableAfterProgressPath':str((CYCLE/'after-progress.json').relative_to(ROOT)),'files':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in sorted(files)],'nextAction':checkpoint['nextAction'],'runtime':'not-run','telemetry':'unknown; no actual per-request token counters exposed; reporting tail unknown; no new agents'}
 out.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'completionManifestSha256':sha(out),'files':len(files),'handoffSha256':sha(CYCLE/'handoff.json'),'closureSha256':sha(CYCLE/'closure.json'),'nextReviewDelta':141,'firstPassProgressPreservedSha256':manifest['firstPassProgressPreservedSha256']}))
if __name__=='__main__':main()
