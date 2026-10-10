#!/usr/bin/env python3
"""Verify exact cycle005 applicability and actual compiled scene binding, fil only."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
FIL=ROOT/'Translations/fil'; CYCLE=Path(__file__).resolve().parent; REVIEW=FIL/'independent-review-04'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
def jl(p):return [json.loads(s) for s in p.read_text().splitlines()]
def encode(d):return (json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()
def lines(d):return ''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in d).encode()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');parser.add_argument('--verify',action='store_true');args=parser.parse_args();require(args.write != args.verify,'Choose write or verify')
 plan=load(CYCLE/'plan.json');closure=load(CYCLE/'closure.json');gate=load(CYCLE/'full-structural-validation.json');changed={plan['row']['stableId']}
 require(sha(REVIEW/'completion-manifest.json')=='dea36a5b9f34c3b207fc97bcd88e29c03592fd21767ec3112918da6ad339915b','Review04 seal differs')
 for pin in load(REVIEW/'completion-manifest.json')['files']:require(sha(ROOT/pin['path'])==pin['sha256'],'Sealed evidence differs: '+pin['path'])
 allowed={plan['row']['authoredPath']:gate['affectedBatchSha256'],gate['affectedValidationPath']:gate['affectedValidationSha256']}
 # All historical pins remain exact except the two explicitly authorized current bytes.
 pins=load(REVIEW/'input-verification.json')['pinChecks']
 for pin in pins:require(sha(ROOT/pin['path'])==allowed.get(pin['path'],pin['sha256']),'Unexplained input change: '+pin['path'])
 family=load(CYCLE/'bounded-author-review.json')
 for name,h in family['files'].items():require(sha(CYCLE/name)==h,'Bounded preimage author evidence differs')
 for r in jl(CYCLE/'bounded-family-paired.jsonl'):
  expected=plan['beforeAuthoredSha256'] if r['authoredPath'] in allowed else r['authoredSha256']
  actual=sha(ROOT/plan['beforeAuthoredPath']) if r['authoredPath'] in allowed else sha(ROOT/r['authoredPath'])
  require(actual==expected==r['authoredSha256'],'Bounded read authored preimage differs')
 prior={r['stableId']:r for r in jl(REVIEW/'closure-decision-applicability.jsonl')}
 current=jl(CYCLE/'closure-paired.jsonl');delta=set(closure['exactNextDelta']['ids']);mandatory=set(next(r['ids'] for r in closure['components'] if r['name']=='mandatoryRegression'))
 applicability=[];mandatory_rows=[]
 for r in current:
  sid=r['stableId'];old=prior.get(sid)
  if sid in delta:
   status='pending-distinct-review';reason=r['deltaReason'];evidence=None
  else:
   require(old is not None and old['findingId'] is None and all(old[k]==r[k] for k in ['sourceSha256','targetSha256','key','nodeNames']),'Prior decision inapplicable: '+sid)
   status='exact-prior-independent-decision-reusable';reason=[];evidence=str((REVIEW/'closure-decision-applicability.jsonl').relative_to(ROOT))
  a={k:r[k] for k in ['acceptedOrdinal','stableId','sourceSha256','targetSha256','key','nodeNames']};a.update(status=status,deltaReason=reason,priorDecisionEvidence=evidence,priorDecisionFileSha256=sha(REVIEW/'closure-decision-applicability.jsonl') if evidence else None)
  applicability.append(a)
  if sid in mandatory:mandatory_rows.append(a)
 require(len(current)==7678 and len(delta)==141 and len(prior)==7612,'Closure counts differ')
 require(len(mandatory_rows)==7279 and len({r['stableId'] for r in applicability})==len(current),'Mandatory/closure catalog differs')
 # All54 prior retirements remain on exact hashes. One returns through the repaired ordinary source predicate and is in new delta.
 inventory={r['stableId']:r for r in jl(ROOT/'Source/localization-inventory-v3/strings.jsonl')}
 G={'UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1'};targets={}
 for pin in gate['authoredFiles']:
  p=ROOT/pin['path'];require(sha(p)==pin['sha256'],'Fresh gate input changed')
  d=load(p)
  if p.name=='static-text-draft.json':continue
  for e in d['entries']:targets[f"string:{G[d['collection']]}:{e['id']}"]=e['target']
 retired=[];reentered=set(closure['review04RetiredDependenciesReentered']['ids'])
 for r in jl(REVIEW/'retired-final-applicability.jsonl'):
  sid=r['stableId'];s=inventory[sid];require(hashlib.sha256(s['source'].encode()).hexdigest()==r['sourceSha256'] and hashlib.sha256(targets[sid].encode()).hexdigest()==r['targetSha256'] and s['key']==r['key'] and s['nodeNames']==r['nodeNames'],'Prior retired input differs')
  a=dict(r);a['currentStatus']='reentered ordinary source selector; fresh distinct review pending' if sid in reentered else 'still outside every current component; exact prior clean decision retained';a['currentComponents']=next((x['components'] for x in current if x['stableId']==sid),[]);retired.append(a)
 require(len(retired)==54 and len(reentered)==1 and reentered<=delta,'Retirement accounting differs')
 # Deterministic decode uses reviewed enum/field interpretation and actual unchanged program bytes.
 spec=importlib.util.spec_from_file_location('fil_reviewed_decoder',REVIEW/'bytecode_decoder.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 before_context=load(CYCLE/'bounded-compiled-context.json');ctx=json.loads(json.dumps(before_context));diffs=[]
 for name,node in ctx['nodes'].items():
  actual=m.actual[name];require(actual['labels']==node['labels'] and len(actual['instructions'])==len(node['instructions']),'Compiled branch differs')
  for ins,raw in zip(node['instructions'],actual['instructions']):
   require(all(ins[k]==raw[k] for k in ['index','opcode','op','operands']),'Compiled instruction differs')
   sid=ins['sourceStableId']
   if sid:
    r=inventory[sid];require(name in r['nodeNames'] and ins['op'] in ['RunLine','AddOption'] and ins['operands'][0]==r['key'] and ins['source']==r['source'],'Compiled source binding differs')
    if ins['target']!=targets[sid]:diffs.append((name,ins['index'],sid));ins['target']=targets[sid]
   else:require(ins['source'] is None and ins['target'] is None,'Nontext instruction received a target')
 require(diffs==[('Theorist_Asking_3',25,plan['row']['stableId'])],'Unexpected assembled context diff')
 require(hashlib.sha256(m.raw).hexdigest()==plan['compiledProgramSha256'],'Actual source bytecode changed')
 ctx.update(status='current source-bound compiled scenes; not runtime or independent acceptance',onlyChangedTextBinding=diffs)
 pendingmandatory=sum(r['status']=='pending-distinct-review' for r in mandatory_rows)
 report={'schemaVersion':1,'locale':'fil','status':'bounded author deterministic verification passed; independent delta pending','acceptedUnits':16538,'preCorrectionPinsVerified':1627,'sealedReviewFilesVerified':23,'historicalInputPinsChecked':len(pins),'authorizedChangedCurrentPaths':allowed,'unexplainedInputChanges':0,'wholeSourceAndGlossaryUnchanged':True,'closure':len(current),'exactNextDelta':len(delta),'corrected':1,'newCurrentMinusPrior':66,'explicitlyInvalidated':74,'priorIndependentDecisionsReusable':len(current)-len(delta),'mandatoryTotal':len(mandatory_rows),'mandatoryInDelta':pendingmandatory,'mandatoryPriorIndependentReusable':len(mandatory_rows)-pendingmandatory,'newRetirements':0,'priorRetirements':54,'priorRetirementsReentered':1,'priorRetirementsStillOutside':53,'compiledProgramSha256':plan['compiledProgramSha256'],'compiledNodesVerified':len(ctx['nodes']),'compiledInstructionsVerified':sum(len(n['instructions']) for n in ctx['nodes'].values()),'correctedCompiledInstruction':25,'dynamicConsumers':'six unchanged; all supplier/assembly/binding pins verified through review04 input pins','selectorRealRegressions':len(load(CYCLE/'selector-specification.json')['regressionExamples']),'selectorSyntheticRegressions':len(load(CYCLE/'selector-specification.json')['syntheticSelectorRegressions']),'unexplainedMissingIds':0,'unexplainedExtraIds':0,'fullRestartPredicateObserved':False,'independentReview':'pending; author reads cannot provide independent acceptance','runtime':'not-run','telemetry':'unknown; per-request input/cache/output/reasoning/total counters not exposed'}
 outputs={'current-compiled-context.json':encode(ctx),'prior-decision-applicability.jsonl':lines(applicability),'mandatory-regression-applicability.jsonl':lines(mandatory_rows),'retired-final-applicability.jsonl':lines(retired)}
 report['filesSha256']={k:hashlib.sha256(v).hexdigest() for k,v in outputs.items()};outputs['verification.json']=encode(report)
 for name,raw in outputs.items():
  p=CYCLE/name
  if args.write:require(not p.exists(),'Immutable output exists');p.write_bytes(raw)
  else:require(p.read_bytes()==raw,'Verification reproduction differs: '+name)
 print(json.dumps({k:report[k] for k in ['closure','exactNextDelta','mandatoryTotal','mandatoryInDelta','priorIndependentDecisionsReusable','compiledNodesVerified','compiledInstructionsVerified','unexplainedInputChanges']}))
if __name__=='__main__':main()
