#!/usr/bin/env python3
"""Reproduce ordinary cycle006 closure and exact applicable-review delta."""
import argparse,hashlib,importlib.util,json,re,sys
from pathlib import Path
sys.dont_write_bytecode=True
from source_predicates import source_matches
from verify_application import gate,require,sha,load,ROOT,FIL,C,R
def jl(p):return [json.loads(s) for s in p.read_text().splitlines()]
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def rawjson(d):return (json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()
def build():
 require(rawjson(gate())==(C/'full-structural-validation.json').read_bytes(),'Application gate changed')
 plan=load(C/'plan.json');spec=load(C/'selector-specification.json');pre=load(C/'preimage-pins.json');fresh=load(C/'full-corpus-validation.json')
 previousPath=FIL/'semantic-correction-cycle-005/closure.json';previous=load(previousPath)
 require(sha(previousPath)==plan['previousClosureSha256']==spec['previousClosureSha256'],'Previous closure changed')
 require(sha(FIL/'semantic-correction-cycle-005/closure-paired.jsonl')==plan['previousPairedSha256'],'Previous pairs changed')
 G={'UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1'};targets={}
 for pin in fresh['authoredFiles']:
  p=ROOT/pin['path'];require(sha(p)==pin['sha256'],'Current input changed')
  doc=load(p)
  for e in doc['entries']:
   sid=e['stableId'] if p.name=='static-text-draft.json' else f"string:{G[doc['collection']]}:{e['id']}"
   require(sid not in targets,'Duplicate target');targets[sid]=e['target']
 inventory=jl(ROOT/'Source/localization-inventory-v3/strings.jsonl');source={r['stableId']:r for r in inventory if r['stableId'] in targets}
 source.update({r['stableId']:r for r in jl(ROOT/'Source/localization-inventory-v3/static-text.jsonl') if r['stableId'] in targets})
 order=[r['stableId'] for col in ['UI','ChecksDialogs','Dialogs'] for r in inventory if r['collection']==col and r['stableId'] in targets]+[e['stableId'] for e in load(FIL/'static-text-draft.json')['entries']]
 require(len(order)==len(set(order))==len(targets)==len(source)==16538 and digest(''.join(s+'\n' for s in order))==previous['acceptedOrderSha256'],'Canonical denominator/order differs');rank={s:i+1 for i,s in enumerate(order)}
 def ids(m):return [s for s in order if s in m]
 def pack(name,m):
  v=ids(m);return dict(name=name,count=len(v),idsSha256=digest(''.join(s+'\n' for s in v)),ids=v)
 def groups(patterns,field):
  return {name:{s for s in order if source_matches(name,p,source[s]['source'],spec) if field=='source'} if field=='source' else {s for s in order if re.search(p,targets[s])} for name,p in patterns.items()}
 # Selector evaluation is independent of the review worklist; reconcile after enumeration.
 referents=groups(spec['affectedReferentSourceRegex'],'source');coarse=referents['coarse-xren-xer']
 bounded=load(C/'bounded-author-inputs.json');require(coarse=={r['stableId'] for r in bounded['rows']} and len(coarse)==125,'Ordinary coarse selection differs')
 decoderPath=FIL/'independent-review-04/bytecode_decoder.py';topology=load(C/'actual-consumer-topology.json')
 require(sha(decoderPath)==topology['decoderSha256'],'Actual decoder changed')
 ds=importlib.util.spec_from_file_location('cycle006_decoder',decoderPath);m=importlib.util.module_from_spec(ds);ds.loader.exec_module(m)
 require(hashlib.sha256(m.raw).hexdigest()==plan['compiledProgramSha256']==topology['compiledProgramSha256'],'Actual compiled program changed')
 bykey={r['key']:r for r in source.values() if r.get('key') is not None};consumers={};context=set();nodes={};windows=[]
 for name,node in m.actual.items():
  texts=[i['index'] for i in node['instructions'] if i['op'] in ['RunLine','AddOption']]
  for i in node['instructions']:
   if i['op'] not in ['RunLine','AddOption']:continue
   row=bykey.get(i['operands'][0])
   if row is None:continue
   sid=row['stableId'];require(name in row.get('nodeNames',[]),'Actual consumer mapping differs')
   consumers.setdefault(sid,[]).append(dict(node=name,instruction=i['index'],opcode=i['op'],operands=i['operands']))
   if sid in coarse:
    pos=texts.index(i['index']);chosen=texts[max(0,pos-2):pos+3];start=min(chosen);end=max(chosen);nodes[name]=node
    window=[]
    for ins in node['instructions'][start:end+1]:
     key=ins['operands'][0] if ins['op'] in ['RunLine','AddOption'] else None;sr=bykey.get(key)
     if sr:context.add(sr['stableId'])
     window.append(dict(ins,sourceStableId=sr['stableId'] if sr else None,source=sr['source'] if sr else None,target=targets[sr['stableId']] if sr else None))
    windows.append(dict(stableId=sid,node=name,consumerInstruction=i['index'],windowInstructions=window))
 require(nodes==topology['nodes'] and ids(context)==topology['boundedContextStableIds'],'Reproduced ordinary context differs')
 for r in bounded['rows']:require(consumers.get(r['stableId'],[])==r['compiledConsumers'],'Candidate consumer identity differs')
 changed={r['stableId'] for r in plan['rows']};exactSources={r['source'] for r in plan['rows']};repeat={s for s in order if source[s]['source'] in exactSources}
 require(changed<=repeat and all(targets[r['stableId']]==r['acceptedFullTarget'] for r in plan['rows']),'Corrected full target differs')
 localized=groups({str(i):p for i,p in enumerate(spec['localizedWordingRegex'],1)},'target')
 for number,guard in spec['localizedWordingSourceGuards'].items():localized[number]&=referents[guard]
 exactTargets={r[k] for r in plan['rows'] for k in ['target','acceptedFullTarget']};localizedExact={s for s in order if targets[s] in exactTargets}
 optionSources={r['source'] for r in load(FIL/'common-options-001.authored.json')['phrases']}
 mandatory={'all-ui':{s for s in order if source[s].get('collection')=='UI'},'all-static':{s for s in order if s.startswith('tmp:')},'all-common-option-exact-sources':{s for s in order if source[s]['source'] in optionSources}}
 mandatory.update(groups(spec['mandatorySourceRegex'],'source'));require(len(mandatory['all-common-option-exact-sources'])==2675,'Exact common source selection differs')
 for t in spec['regressionExamples']:require(source[t['stableId']]['source']==t['source'] and t['stableId'] in mandatory[t['expectedSelector']],'Actual selector regression failed '+t['stableId'])
 for t in spec['syntheticSelectorRegressions']:require(source_matches(t['selector'],spec['mandatorySourceRegex'][t['selector']],t['source'],spec)==t['mustMatch'],'Synthetic control failed '+t['source'])
 dynamics=load(FIL/'semantic-correction-cycle-002/plan.json')['unchangedDynamicConsumers'];dynamic={r['stableId'] for r in dynamics};require(len(dynamic)==6,'Dynamic site count differs')
 for r in dynamics:require(digest(source[r['stableId']]['source'])==r['sourceSha256'] and digest(targets[r['stableId']])==r['targetSha256'],'Dynamic source/target changed')
 components={'changed':changed,'explicitContext':context,'exactSourceRepetition':repeat,'glossaryReferent':set().union(*referents.values()),'localizedWording':set().union(localizedExact,*localized.values()),'runtimeBinding':context|dynamic,'mandatoryRegression':set().union(*mandatory.values())}
 closure=set().union(*components.values());priorids=set(previous['currentClosure']['ids']);reviewed={r['stableId']:r for r in jl(R/'closure-decision-applicability.jsonl')};priorPairs={r['stableId']:r for r in jl(FIL/'semantic-correction-cycle-005/closure-paired.jsonl')}
 require(len(priorids)==len(reviewed)==7678 and priorids==set(reviewed)==set(priorPairs),'Prior review accounting differs')
 applicable=set();priorCatalog=[]
 def identity(s):
  # Full actual key/node/site/operand identity, tied to unchanged program and decoder/assembly pins.
  return dict(compiledProgramSha256=plan['compiledProgramSha256'],key=source[s].get('key'),nodeNames=source[s].get('nodeNames',[]),sites=consumers.get(s,[]))
 for s in ids(priorids):
  a,b=reviewed[s],priorPairs[s];require(a['sourceSha256']==b['sourceSha256']==digest(source[s]['source']) and a['targetSha256']==b['targetSha256'] and a['key']==b['key']==source[s].get('key') and a['nodeNames']==b['nodeNames']==source[s].get('nodeNames',[]),'Prior source/key/node differs')
  targetExact=a['targetSha256']==digest(targets[s]);clean=a['decision']!='objective-correction-required' and a['findingId'] is None
  require(targetExact or s in changed,'Unplanned target change invalidates prior review')
  if targetExact and clean:applicable.add(s)
  priorCatalog.append(dict(stableId=s,acceptedOrdinal=rank[s],priorDecision=a['decision'],priorFindingId=a['findingId'],sourceKeyNodesExact=True,targetExact=targetExact,consumerIdentityExact=True,consumerIdentity=identity(s),consumerIdentitySha256=digest(json.dumps(identity(s),sort_keys=True,ensure_ascii=False,separators=(',',':'))),cleanDecisionApplicable=targetExact and clean,reason='exact full pair and unchanged actual program/key/node/site/operands' if targetExact and clean else 'corrected target invalidates full-pair reuse; finding6555 has no clean credit'))
 # Invalidate the bounded mechanism even where bytes remain exact; not the unchanged full closure.
 invalidated=(applicable & closure & (coarse|context|repeat))-changed
 newraw=closure-priorids;minusApplicable=closure-applicable;delta=changed|minusApplicable|invalidated;reusable=closure-delta
 require(delta==changed|newraw|invalidated and reusable<=applicable and not (reusable&delta),'Exact next delta differs')
 priorMandatory=jl(R/'mandatory-regression-applicability.jsonl');priorMandatoryIds={r['stableId'] for r in priorMandatory};require(len(priorMandatory)==7279 and priorMandatoryIds==set(next(r['ids'] for r in previous['components'] if r['name']=='mandatoryRegression')),'Prior mandatory catalog differs')
 retirementReceipt=jl(R/'retired-final-applicability.jsonl');require(len(retirementReceipt)==len({r['stableId'] for r in retirementReceipt})==54,'Historical retirement receipt differs')
 retirees=[r for r in retirementReceipt if not r['currentComponents']];alreadyReentered=[r for r in retirementReceipt if r['currentComponents']]
 require(len(retirees)==53 and len(alreadyReentered)==1 and alreadyReentered[0]['stableId'] in priorids and reviewed[alreadyReentered[0]['stableId']]['decision']=='accepted-independent-reviewed-unit','Review05 historical retirement states differ')
 retirementRows=[]
 for r in retirees:
  s=r['stableId'];require(digest(source[s]['source'])==r['sourceSha256'] and source[s].get('key')==r['key'] and source[s].get('nodeNames',[])==r['nodeNames'],'Retired source identity changed')
  exact=digest(targets[s])==r['targetSha256'];inClosure=s in closure
  require(exact or s in changed,'Unplanned retired target change')
  if inClosure:require(s in delta,'Reentered retired unit missing from fresh delta')
  retirementRows.append(dict(r,currentTargetSha256=digest(targets[s]),currentTargetExact=exact,currentComponents=[n for n,v in components.items() if s in v],consumerIdentity=identity(s),currentStatus='reentered ordinary closure; requires fresh independent decision' if inClosure else 'still retired: no current component; exact unchanged clean prior decision',independentReuseInCurrentClosure=False))
 newlyRetired=priorids-closure
 for s in ids(newlyRetired):
  require(s in applicable,'Retired unit lacks exact clean prior decision')
  retirementRows.append(dict(stableId=s,acceptedOrdinal=rank[s],sourceSha256=digest(source[s]['source']),targetSha256=digest(targets[s]),key=source[s].get('key'),nodeNames=source[s].get('nodeNames',[]),retiredCycle=6,priorCleanDecision=True,currentTargetExact=True,currentComponents=[],consumerIdentity=identity(s),currentStatus='newly retired: outside every ordinary component; exact clean prior full pair',independentReuseInCurrentClosure=False))
 def pair(s):
  r=source[s];ci=identity(s)
  return dict(acceptedOrdinal=rank[s],stableId=s,collection=r.get('collection','static'),key=r.get('key'),nodeNames=r.get('nodeNames',[]),source=r['source'],sourceSha256=digest(r['source']),target=targets[s],targetSha256=digest(targets[s]),consumerIdentity=ci,consumerIdentitySha256=digest(json.dumps(ci,sort_keys=True,ensure_ascii=False,separators=(',',':'))),components=[n for n,v in components.items() if s in v],deltaReason=[n for n,v in [('corrected',changed),('currentMinusApplicablePrior',minusApplicable),('newClosure',newraw),('explicitlyInvalidated',invalidated)] if s in v])
 def jsonl(rows):return ''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows).encode()
 currentMandatory=components['mandatoryRegression'];mandatoryRows=[dict(pair(s),priorMandatory=s in priorMandatoryIds,priorFullPairApplicable=s in applicable,currentReviewStatus='pending distinct reviewer' if s in delta else 'exact prior clean decision reusable',priorReviewEvidenceSha256=sha(R/'closure-decision-applicability.jsonl')) for s in ids(currentMandatory)]
 files={'closure-paired.jsonl':jsonl(pair(s) for s in ids(closure)),'next-delta-paired.jsonl':jsonl(pair(s) for s in ids(delta)),'next-review-ids.txt':''.join(s+'\n' for s in ids(delta)).encode(),'prior-independent-applicability.jsonl':jsonl(priorCatalog),'retired-applicability.jsonl':jsonl(retirementRows),'mandatory-regression-catalog.jsonl':jsonl(mandatoryRows),'current-bounded-consumers.json':rawjson(dict(compiledProgramSha256=plan['compiledProgramSha256'],nodeCount=len(nodes),instructionCount=sum(len(n['instructions']) for n in nodes.values()),consumerSites=sum(len(consumers.get(s,[])) for s in coarse),textWindowRule=spec['runtimeBindingRule'],windows=windows,unchangedDynamicConsumerPins=dynamics))}
 oldComponents={r['name']:set(r['ids']) for r in previous['components']}
 result=dict(schemaVersion=6,locale='fil',gameVersion='1.3.19',status='cycle006 consolidated author correction; exact bounded distinct review pending',planSha256=sha(C/'plan.json'),applicationGateSha256=sha(C/'full-structural-validation.json'),selectorSpecificationSha256=sha(C/'selector-specification.json'),sourcePredicatesSha256=sha(C/'source_predicates.py'),previousClosureSha256=sha(previousPath),previousPairedSha256=sha(FIL/'semantic-correction-cycle-005/closure-paired.jsonl'),review05CompletionManifestSha256=pre['review05CompletionManifestSha256'],review05VerdictSha256=pre['review05VerdictSha256'],sourceAndGlossaryFingerprints=plan['sourceAndGlossaryFingerprints'],firstPassProgressSha256=plan['firstPassProgressSha256'],compiledProgramSha256=plan['compiledProgramSha256'],actualConsumerTopologySha256=sha(C/'actual-consumer-topology.json'),acceptedUnits=16538,acceptedOrderSha256=previous['acceptedOrderSha256'],components=[pack(n,v) for n,v in components.items()],componentDeltas=[dict(name=n,new=pack(n+':new',v-oldComponents[n]),retired=pack(n+':retired',oldComponents[n]-v)) for n,v in components.items()],referentSelectors=[dict(pack(n,v),sourceRegex=spec['affectedReferentSourceRegex'][n]) for n,v in referents.items()],localizedSelectors=[dict(pack(n,v),targetRegex=spec['localizedWordingRegex'][int(n)-1],sourceGuard=spec['localizedWordingSourceGuards'].get(n)) for n,v in localized.items()],mandatorySelectors=[dict(pack(n,v),sourceRegex=spec['mandatorySourceRegex'].get(n)) for n,v in mandatory.items()],previousClosureCount=len(priorids),currentClosure=pack('currentClosure',closure),corrected=pack('corrected',changed),newCurrentMinusPrevious=pack('newCurrentMinusPrevious',newraw),currentMinusExactApplicablePrior=pack('currentMinusExactApplicablePrior',minusApplicable),physicallyApplicablePriorCleanPairs=pack('physicallyApplicablePriorCleanPairs',applicable),explicitlyInvalidatedPriorEvidence=pack('explicitlyInvalidatedPriorEvidence',invalidated),reusableUnchangedIndependentPairs=pack('reusableUnchangedIndependentPairs',reusable),exactNextDelta=pack('exactNextDelta',delta),retiredPreviousMinusCurrent=pack('retiredPreviousMinusCurrent',newlyRetired),prior53RetireesReentered=pack('prior53RetireesReentered',{r['stableId'] for r in retirees}&closure),prior53RetireesStillRetired=pack('prior53RetireesStillRetired',{r['stableId'] for r in retirees}-closure),mandatoryCurrent=pack('mandatoryCurrent',currentMandatory),mandatoryFresh=pack('mandatoryFresh',currentMandatory&delta),mandatoryReusable=pack('mandatoryReusable',currentMandatory&reusable),actualSelectorRegressions=len(spec['regressionExamples']),syntheticSelectorControls=len(spec['syntheticSelectorRegressions']),invalidationRule='Exact prior clean full-pair decisions in current coarse-source family, actual nearest2 text consumer windows, or corrected full-source repetitions are explicitly invalidated for this mechanism; author reads confer no independent credit.',deltaFormula='corrected union(currentClosure minus exactApplicablePriorIndependentFullPairAndConsumerIDs) union explicitInvalidations; overlapping components counted once',priorConsumerReuseProof='All1157 old pins verified before application, unchanged compiled program/decoder/assembly/source/key/node pins, actual sites+opcodes+operands rederived; whole target unchanged and prior decision clean. Review05 finding6555 excluded.',retirementRule='No current ordinary component selects retired unit; exact clean source/target/key/node/consumer pins; all53 prior retirees individually reconciled, reentries pending fresh review.',files={n:dict(path=str((C/n).relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest()) for n,raw in files.items()},unexplainedMissingIds=[],unexplainedExtraIds=[],independentAcceptance=False,runtime='not-run')
 files['closure.json']=rawjson(result);return result,files
def main():
 p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');p.add_argument('--verify',action='store_true');a=p.parse_args();require(a.write!=a.verify,'Choose write or verify');d,files=build()
 for n,raw in files.items():
  out=C/n
  if a.write:require(not out.exists(),'Immutable closure artifact exists '+n);out.write_bytes(raw)
  else:require(out.read_bytes()==raw,'Stored closure artifact differs '+n)
 print(json.dumps({n:d[n]['count'] for n in ['currentClosure','corrected','newCurrentMinusPrevious','explicitlyInvalidatedPriorEvidence','exactNextDelta','reusableUnchangedIndependentPairs','mandatoryCurrent','mandatoryFresh','mandatoryReusable','retiredPreviousMinusCurrent','prior53RetireesReentered','prior53RetireesStillRetired']}))
if __name__=='__main__':main()
