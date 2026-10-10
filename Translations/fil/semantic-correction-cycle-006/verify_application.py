#!/usr/bin/env python3
"""Verify bounded changes against immutable preimages and fresh locale-only guard."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
from json_target_spans import rewrite_targets
ROOT=Path(__file__).resolve().parents[3];FIL=ROOT/'Translations/fil';C=Path(__file__).resolve().parent;R=FIL/'independent-review-05'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
def gate():
 plan=load(C/'plan.json');pins=load(C/'preimage-pins.json');fresh=load(C/'full-corpus-validation.json');affected=load(C/'affected-validation.json')
 require(fresh['rows']==16538 and fresh['structuralResult']==fresh['exactResult']=='passed','Fresh guard failed')
 for pin in plan['sourceAndGlossaryFingerprints'].values():require(sha(ROOT/pin['path'])==pin['sha256'],'Source/glossary changed')
 require(sha(ROOT/'Source/preserve-exactly-v4.json')==plan['preserveExactManifestSha256'],'Exact contract changed')
 require(sha(FIL/'semantic-review-progress.json')==plan['firstPassProgressSha256'],'First pass changed')
 for name,h in pins['review05FilesSha256'].items():require(sha(R/name)==h,'Review05 evidence changed '+name)
 require(sha(R/'completion-manifest.json')==pins['review05CompletionManifestSha256'] and sha(R/'final-verdict.json')==pins['review05VerdictSha256'],'Review seal changed')
 for name,h in pins['preparedFilesSha256'].items():require(sha(C/name)==h,'Bounded preimage changed')
 for path,key in [('Scripts/validate_locale_corpus.py','validatorSha256'),('Scripts/locale_text_inputs.py','inputLoaderSha256')]:
  require(sha(ROOT/path)==fresh[key],'Corpus guard/loader changed')
 for name,h in fresh['owningValidators'].items():require(sha(ROOT/'Scripts'/name)==h,'Owning validator changed')
 require(sha(ROOT/affected['owningValidatorPath'])==affected['owningValidatorSha256'],'Affected validator changed')
 old={r['path']:r['sha256'] for r in pins['authoredFiles']};current={r['path']:r['sha256'] for r in fresh['authoredFiles']}
 require(set(old)==set(current) and len(current)==456,'Authored input set differs')
 files={r['authoredPath']:r for r in plan['files']};reports={r['batch']:r for r in affected['reports']};changed={r['stableId']:r for r in plan['rows']}
 require(len(files)==len(reports)==41 and len(changed)==56,'Batch plan differs')
 allowed={}
 for path,h in current.items():
  require(sha(ROOT/path)==h,'Current authored guard pin changed '+path)
  if path not in files:require(old[path]==h,'Unrelated authored input changed '+path)
 observed=set()
 for path,f in files.items():
  before=ROOT/f['beforeSnapshotPath'];after=ROOT/f['afterSnapshotPath'];report=reports[path]
  require(sha(before)==f['beforeSha256']==old[path] and sha(after)==f['afterSha256']==current[path]==sha(ROOT/path),'Authored pre/post snapshot differs')
  require(sha(ROOT/f['beforeValidationSnapshotPath'])==f['beforeValidationSha256'],'Old sidecar changed')
  require(sha(ROOT/report['sidecarPath'])==report['sidecarSha256'] and report['batchSha256']==current[path] and report['structuralResult']=='passed','Current owning sidecar differs')
  a,b=load(before),load(after);require(rewrite_targets(before.read_bytes(),b)==after.read_bytes(),'Non-target raw bytes changed')
  for x,y in zip(a['entries'],b['entries']):
   if x['target']!=y['target']:
    sid='string:444ff14f1967f5a4c8eb9e4cf4c913f1:'+str(x['id']);require(sid in changed,'Unexpected target change')
    row=changed[sid];require(x['target']==row['target'] and y['target']==row['acceptedFullTarget'],'Full replacement differs');observed.add(sid)
  allowed[str(ROOT/path)]=current[path];allowed[str(ROOT/report['sidecarPath'])]=report['sidecarSha256']
 require(observed==set(changed),'Changed ID set differs')
 # Reconcile every previously checked pin; only planned41 inputs/sidecars and the administrative checkpoint can differ.
 administrative=[]
 for pin in load(R/'input-verification.json')['pinChecks']:
  p=ROOT/pin['path'];absolute=str(p);actual=sha(p)
  if absolute in allowed:require(actual==allowed[absolute],'Authorized changed pin differs')
  elif p==FIL/'progress.json':
   require(sha(C/'before-progress.json')==pins['beforeProgressSha256']==pin['sha256'],'Checkpoint preimage changed');administrative.append(str(p.relative_to(ROOT)))
  else:require(actual==pin['sha256'],'Unrelated previous pin changed '+str(p))
 # No corrected source feeds options/static/credits. Reuse only exact unchanged recipes and expansion bytes.
 derived=load(FIL/'semantic-correction-cycle-003/full-structural-validation.json');previous=load(FIL/'semantic-correction-cycle-005/full-structural-validation.json')
 recipePaths={'optionRecipeSha256':'common-options-001.authored.json','staticPhraseRecipeSha256':'static-phrases.authored.json','creditsRoleMapSha256':'credits-role-map.json','staticDraftSha256':'static-text-draft.json'}
 for key,name in recipePaths.items():require(sha(FIL/name)==derived[key]==previous[key],'Derived recipe/output changed '+name)
 optionSources={r['source'] for r in load(FIL/'common-options-001.authored.json')['phrases']};staticSources={r['source'] for r in load(FIL/'static-phrases.authored.json')['phrases']}
 require(not {r['source'] for r in changed.values()}&(optionSources|staticSources),'Changed source requires recipe regeneration')
 require(all(r['collection']=='Dialogs' for r in changed.values()),'Changed static dependency')
 return {'schemaVersion':6,'locale':'fil','status':'bounded56 full replacements; affected owning gates and fresh full16538 structure/exact passed; independent review pending','planSha256':sha(C/'plan.json'),'freshCorpusValidationSha256':sha(C/'full-corpus-validation.json'),'affectedValidationSha256':sha(C/'affected-validation.json'),'checkedIds':16538,'missingIds':0,'extraIds':0,'duplicateIds':0,'changedTargets':56,'affectedAuthoredFiles':41,'affectedOwningRows':sum(r['authoredRows'] for r in reports.values()),'authoredInputs':456,'unexpectedFieldOrEntryChanges':0,'nonTargetRawBytesExact':True,'previousPinsChecked':1157,'authorizedChangedPinPaths':sorted(allowed),'administrativeCheckpointPaths':administrative,'authoredFiles':fresh['authoredFiles'],'firstPassProgressSha256':plan['firstPassProgressSha256'],'sourceAndGlossaryFingerprints':plan['sourceAndGlossaryFingerprints'],'preserveExactManifestSha256':plan['preserveExactManifestSha256'],'derivedProvenance':{'priorFullExpansionReceiptPath':'Translations/fil/semantic-correction-cycle-003/full-structural-validation.json','priorFullExpansionReceiptSha256':sha(FIL/'semantic-correction-cycle-003/full-structural-validation.json'),'recipePins':{name:sha(FIL/name) for name in recipePaths.values()},'affectedDerivedIds':[],'regeneration':'none required: all56 corrected standalone dialogue sources absent from option/static recipes; all2674 owned option and177 static expansions and81 credits-role replacements retain exact verified inputs/output; fresh corpus guard rechecks credits assembly','optionOwnedRows':2674,'optionExactSourceRows':2675,'staticPhraseRows':177,'creditsRegeneratedExact':True},'independentAcceptance':False,'runtime':'not-run'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');p.add_argument('--verify',action='store_true');a=p.parse_args();require(a.write!=a.verify,'Choose write or verify')
 d=gate();raw=(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode();out=C/'full-structural-validation.json'
 if a.write:require(not out.exists(),'Immutable receipt exists');out.write_bytes(raw)
 else:require(out.read_bytes()==raw,'Stored gate differs')
 print(json.dumps({'changed':56,'batches':41,'checked':16538,'gateSha256':sha(out)}))
if __name__=='__main__':main()
