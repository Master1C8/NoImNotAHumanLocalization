#!/usr/bin/env python3
"""Reproduce exact cycle004 delta and per-row applicability from sealed independent reads."""
import argparse,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];BG=ROOT/'Translations/bg'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text());th=lambda t:hashlib.sha256(t.encode()).hexdigest()
idbytes=lambda ids:('\n'.join(ids)+ ('\n' if ids else '')).encode()
same=lambda a,b:all(a.get(k)==b.get(k) for k in ['source','target','key','sceneNodes','collection'])
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['preview','build','verify']);args=parser.parse_args()
 old=load(BG/'semantic-closure-cycle-003.json');new=load(BG/'semantic-closure-cycle-004.json');result=load(BG/'correction-batch-004-result.json')
 assert new['correctionResultSha256']==sha(BG/'correction-batch-004-result.json')
 oldrows={r['stableId']:r for r in old['reviewRows']};newrows={r['stableId']:r for r in new['reviewRows']}
 current=set(newrows);assert len(oldrows)==2839 and len(current)==2911
 corrected=set(result['changedIds']);assert len(corrected)==3
 catalog=defaultdict(list);reviewpins={};readsets={}
 closures={n:load(BG/f'semantic-closure-cycle-{n:03}.json') for n in [1,2,3]}
 # All seals include actual final verifier evidence; never replace the failed Review02 diagnostic.
 for n in [1,2,3]:
  base=BG/f'independent-review-{n:02}';manifest=load(base/'evidence-sha256.json')
  for name,h in manifest.get('files',manifest).items():assert sha(base/name)==h,(n,name)
  reviewpins[str((base/'evidence-sha256.json').relative_to(ROOT))]=sha(base/'evidence-sha256.json')
  review=load(base/'review.json');assert review['closureSha256']==sha(BG/f'semantic-closure-cycle-{n:03}.json')
  rows={r['stableId']:r for r in closures[n]['reviewRows']};ids=set((base/'read.ids').read_text().splitlines());readsets[n]=ids
  assert len(ids)=={1:1506,2:2110,3:311}[n] and ids<=set(rows)
  if n in [2,3]:
   verdictpath=base/'per-id-read-verdicts.json';verdicts=load(verdictpath);assert len(verdicts)==len(ids) and {v['stableId'] for v in verdicts}==ids
   reviewpins[str(verdictpath.relative_to(ROOT))]=sha(verdictpath)
   for v in verdicts:
    r=rows[v['stableId']];assert v['fullPairRead'] and v['sourceSha256']==th(r['source']) and v['targetSha256']==th(r['target'])
  for i in ids:catalog[i].append({'origin':f'Review{n:02} full read','row':rows[i]})
 # Supplementary Review02: exact source/target/key, with unchanged compiled topology
 # established in sealed Review03 input verification. Its three unchanged pair credits
 # remain usable only at the same complete target, never at a modified target.
 supp02=[r for r in load(BG/'independent-review-02/selector-supplementary-rows.json') if not r['inDelta']];assert len(supp02)==4
 for r in supp02:
  i=r['stableId'];reference=oldrows[i];assert r['source']==reference['source'] and r['key']==reference['key']
  pair=dict(reference,target=r['target']);catalog[i].append({'origin':'Review02 supplementary exact pair + Review03 verified unchanged compiled consumer','row':pair})
 supp03=load(BG/'independent-review-03/supplementary-pair-verdicts.json');assert len(supp03)==3
 for r in supp03:
  assert r['fullPairRead'];i=r['stableId'];assert same(r,oldrows[i]);catalog[i].append({'origin':'Review03 supplementary full read','row':r})
 previous=load(BG/'semantic-delta-cycle-003.json')
 assert set(previous['components']['priorApplicable']['ids'])|readsets[3]==set(oldrows)
 for i,r in oldrows.items():assert any(same(e['row'],r) for e in catalog[i]),'Prior closure lacks exact independently read pair: '+i
 assert sha(BG/'independent-review-03/evidence-sha256.json')=='7528f1c522bf30a4a2f6999568e3dcfed48a684cea7122f720b29a791c733f61'
 applicable={i for i in current if any(same(e['row'],newrows[i]) for e in catalog[i])}
 assert len(applicable)==2836 and not corrected & applicable
 applicable_catalog=[];origins=Counter()
 for r in new['reviewRows']:
  i=r['stableId']
  if i not in applicable:continue
  matching=[e for e in catalog[i] if same(e['row'],r)];origin=matching[-1]['origin'];origins[origin]+=1
  applicable_catalog.append({'stableId':i,'sourceSha256':th(r['source']),'targetSha256':th(r['target']),'key':r['key'],'sceneNodes':r['sceneNodes'],'collection':r['collection'],'creditedOrigin':origin,'allExactApplicableOrigins':[e['origin'] for e in matching]})
 corrected_nodes={n for i in corrected for n in newrows[i]['sceneNodes']};corrected_sources={newrows[i]['source'] for i in corrected}
 groups={g:set(new['glossaryReferentGroups'][g]['ids']) for g in ['occasionVersusManner','answerResponsibilityVersusAssurance']}
 reasons={};retired=set(oldrows)-current
 for i in applicable:
  r=newrows[i];why=[]
  if set(r['sceneNodes'])&corrected_nodes:why.append('same compiled Yarn node as cycle004 complete replacement; chronology or assurance now repaired')
  if r['source'] in corrected_sources:why.append('exact Russian repetition of cycle004 corrected unit')
  for g,ids in groups.items():
   if i in ids and ids&corrected:why.append('bounded affected source idiom family: '+g+'; reinterpret against the repaired distinction, not register preference')
  if why:reasons[i]=why
 invalidated=set(reasons);new_without_applicable=current-applicable;review=corrected|new_without_applicable|invalidated
 assert not retired,'Retirement requires explicit predicate/consumer explanation'
 rank={r['stableId']:r['sourceIndex'] for r in new['reviewRows']};ordered=lambda ids:sorted(ids,key=rank.__getitem__)
 outputs={};components={}
 for name,ids in [('corrected',corrected),('newClosure',new_without_applicable),('invalidatedPrior',invalidated),('retired',retired),('review',review),('priorApplicable',applicable)]:
  ids=ordered(ids);raw=idbytes(ids);rel=f'Translations/bg/semantic-cycle-004-{name}.ids';outputs[rel]=raw
  components[name]={'path':rel,'count':len(ids),'sha256':hashlib.sha256(raw).hexdigest(),'ids':ids}
 mandatory=set(new['components']['mandatoryRegressions']['ids']);oldmandatory=set(old['components']['mandatoryRegressions']['ids']);assert mandatory==oldmandatory and len(mandatory)==908
 priorvalid=mandatory-review;fresh=mandatory&review;assert priorvalid<=applicable
 supplementary_applicability=[]
 for r in supp03:
  i=r['stableId'];exact=i in newrows and same(r,newrows[i]);supplementary_applicability.append({'stableId':i,'exactApplicable':exact,'reused':exact and i in applicable,'reason':'source/target/key/consumer unchanged' if exact else 'cycle004 target replacement; old full pair retained as preimage, no current read credit'})
 affectedpaths={r['path'] for r in result['changedFiles']};allowed=affectedpaths|{r['validationPath'] for r in result['changedFiles']}
 pins=load(BG/'independent-review-03/input-verification.json')['pins'];drift={p for p,h in pins.items() if sha(ROOT/p)!=h};assert drift==allowed
 for p,h in new['pinnedInputs'].items():assert sha(ROOT/p)==h,p
 evidence={'schemaVersion':1,'locale':'bg','gameVersion':'1.3.19','status':'cycle004 exact independent delta ready; no clean or editorial acceptance','acceptedUnits':16538,'firstPassReviewedUnits':16538,
  'priorClosurePath':'Translations/bg/semantic-closure-cycle-003.json','priorClosureSha256':sha(BG/'semantic-closure-cycle-003.json'),'currentClosurePath':'Translations/bg/semantic-closure-cycle-004.json','currentClosureSha256':sha(BG/'semantic-closure-cycle-004.json'),
  'correctionResultPath':'Translations/bg/correction-batch-004-result.json','correctionResultSha256':sha(BG/'correction-batch-004-result.json'),
  'boundedAffectedReviewPath':'Translations/bg/correction-cycle-004-bounded-review.json','boundedAffectedReviewSha256':sha(BG/'correction-cycle-004-bounded-review.json'),
  'recipePath':'Translations/bg/build_semantic_delta_cycle_004.py','recipeSha256':sha(Path(__file__)),
  'reviewEvidencePins':reviewpins,'currentPins':new['pinnedInputs'],
  'formula':'corrected IDs union (current closure minus exact applicable prior independently read IDs) union explicitly invalidated prior IDs',
  'components':components,'priorReadingApplicability':{'priorClosureIds':2839,'priorClosureExactReadCoverage':2839,'currentExactApplicableIds':len(applicable),'originCounts':dict(sorted(origins.items())),'supplementary03':supplementary_applicability,'catalog':applicable_catalog},
  'invalidatedPriorReasons':[{'stableId':i,'reasons':reasons[i]} for i in ordered(invalidated)],
  'retiredDependencies':[], 'retiredDependencyExplanation':'None: all 2839 prior IDs remain selected by cumulative corrections, context, repetitions, active referents/voice, runtime and mandatory groups. New temporal/assurance predicates add current dependencies through normal generation.',
  'reasonCatalog':{'changedPair':'Three corrected complete targets invalidate old pair credit.','newSelection':'Current closure has no exact prior independent read.','sameConsumer':'Same actual compiled node as a chronology/assurance repair; neighboring meaning is checked again.','idiomFamily':'Direct temporal/assurance source family, irrespective of speaker; source sense repaired in this batch.','retired':'No retired IDs. A future retirement requires a rule/consumer applicability change and explicit justification.','unchangedMandatory':'Exact full pairs and topology retained; sealed Review03 mandatory credit includes 4 fresh and 904 inherited.'},
  'review03PinDrift':{'verifiedBaselinePins':len(pins),'intentionalChangedPins':sorted(drift),'unchangedPins':len(pins)-len(drift),'basis':'physical preimages + complete before/after sourcepairs; only three authored batches and three derived validation sidecars'},
  'mandatoryRegressions':{'currentCount':908,'freshInNextReview':len(fresh),'priorExactApplicableRetained':len(priorvalid),'freshIds':ordered(fresh),'priorExactApplicableIds':ordered(priorvalid),'groups':{g:{'count':v['count'],'idsSha256':v['idsSha256']} for g,v in new['mandatoryRegressionGroups'].items()}},
  'currentAuthoredFiles':result['allAuthoredFiles'],'nextReviewRows':[r for r in new['reviewRows'] if r['stableId'] in review],
  'semanticRestart':'none: exact source/glossary/character policy/accepted scope/compiled consumers unchanged; bounded source idioms only',
  'runtime':'not-run; owner prohibition'}
 outputs['Translations/bg/semantic-delta-cycle-004.json']=(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n').encode()
 if args.action=='preview':print(json.dumps({name:r['count'] for name,r in components.items()}|{'mandatoryFresh':len(fresh),'mandatoryReused':len(priorvalid),'originCounts':dict(origins)}));return
 for rel,raw in outputs.items():
  p=ROOT/rel
  if args.action=='build':
   if p.exists():assert p.read_bytes()==raw,'Immutable delta drift: '+rel
   else:p.write_bytes(raw)
  else:assert p.read_bytes()==raw,'Delta drift: '+rel
 print(json.dumps({'action':args.action,'closureIds':len(current),'reviewIds':len(review),'explicitInvalidations':len(invalidated),'newWithoutApplicableRead':len(new_without_applicable),'retired':len(retired),'mandatoryFresh':len(fresh),'deltaSha256':sha(BG/'semantic-delta-cycle-004.json')}))
if __name__=='__main__':main()
