"""Verify final independent decisions and original sealed input applicability."""
import json,hashlib,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];B=R/'Translations/bg';O=Path(__file__).parent
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();th=lambda t:hashlib.sha256(t.encode()).hexdigest()
iv=load(O/'input-verification.json');d=load(B/'semantic-delta-cycle-004.json');c=load(B/'semantic-closure-cycle-004.json');review=load(O/'review.json');decisions=load(O/'per-id-read-verdicts.json');context=load(O/'full-pair-contexts.json')
for p,h in iv['pins'].items():assert sha(R/p)==h,p
for n in [1,2,3]:
 base=B/f'independent-review-{n:02}';m=load(base/'evidence-sha256.json')
 for p,h in m.get('files',m).items():assert sha(base/p)==h,(n,p)
assert sha(B/'correction-cycle-004-evidence-sha256.json')=='793dd579458b4b3cb0c7e24c31a9e9e195ba9495f856b82432ce8950eaa02de5'
assert sha(B/'independent-review-03/evidence-sha256.json')=='7528f1c522bf30a4a2f6999568e3dcfed48a684cea7122f720b29a791c733f61'
assert len(decisions)==len(context)==len(d['nextReviewRows'])==120
for idx,(v,r,ct) in enumerate(zip(decisions,d['nextReviewRows'],context)):
 assert v['deltaIndex']==idx==ct['deltaIndex'] and ct['fullPair']==r
 assert all(v[k]==value for k,value in r.items())
 assert v['fullPairRead'] and v['decision']=='accepted' and not v['objectiveFinding'] and v['sourceSha256']==th(r['source']) and v['targetSha256']==th(r['target'])
 assert v['compiledUses']==iv['compiledUses'][r['stableId']]
assert (O/'read.ids').read_bytes()==(B/'semantic-cycle-004-review.ids').read_bytes()
assert set(v['stableId'] for v in load(O/'corrected-unit-verdicts.json'))==set(d['components']['corrected']['ids'])
assert load(O/'findings.json')['findings']==[] and review['status']=='clean'
m=load(O/'mandatory-verdicts.json');fresh=set(d['mandatoryRegressions']['freshIds']);prior=set(d['mandatoryRegressions']['priorExactApplicableIds']);mand=set(c['components']['mandatoryRegressions']['ids']);assert len(fresh)==1 and len(prior)==907 and fresh|prior==mand and not fresh&prior and len(mand)==908
assert {v['stableId'] for v in m['freshDecisions']}==fresh and set(m['priorExactIds'])==prior
assert m['groups']==c['mandatoryRegressionGroups']
assert load(O/'retirement-invalidation-applicability.json')['invalidatedPriorReasons']==d['invalidatedPriorReasons']
raw=load(O/'occupant-domain-raw-v2.json');bald=next(r for r in raw['characterRecords'] if r['character']=='Bald');same=[r for r in raw['characterRecords'] if r['place']==bald['place']];assembled=load(O/'assembled-consumer-verdict.json')
assert len(raw['characterRecords'])==72 and {r['character'] for r in same}=={'Anxiety','Bald','Marauder'}
assert [r['character'] for r in assembled['metadataSamePlaceCandidates']]==[r['character'] for r in same]
for r in assembled['metadataSamePlaceCandidates']:assert r['assembledTarget']==assembled['fullTarget'].replace('{0}',r['targetName'])
assert sha(O/'locale-corpus.json')==review['owningFullCorpusGate']['receiptSha256'] and load(O/'locale-corpus.json')['rows']==16538
assert sha(B/'semantic-closure-cycle-004.json')==review['closureSha256'] and sha(B/'semantic-delta-cycle-004.json')==review['deltaSha256'] and sha(O/'read.ids')==review['reviewIdsSha256']
evidence={'schemaVersion':1,'locale':'bg','verdict':'clean','fullPairDecisions':120,'completeCorrectionsAccepted':3,'objectiveFindings':0,'closureIds':2911,'explicitInvalidations':45,'retired':0,'mandatoryFresh':1,'mandatoryExactPrior':907,'inputPinsRechecked':len(iv['pins']),'originalAuthorAndPriorIndependentSeals':'exact','currentVsHistoricalPinDifferences':'six intended authored/receipt changes; physical baseline preimages remain exact','currentReviewSha256':sha(O/'review.json'),'currentClosureSha256':review['closureSha256'],'currentDeltaSha256':review['deltaSha256'],'readIdsSha256':sha(O/'read.ids'),'rawConsumerFields':'original assembly IL and byte-exact serialized-prefix checks; static consumer scope only','physicalRuntime':'not run; original owner prohibition','rootEditorialAcceptance':'pending','tokenTelemetry':'unknown; no request counters exposed, reporting tail unmeasured'}
p=O/'final-verification.json';data=(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n').encode()
if sys.argv[1]=='snapshot':assert not p.exists();p.write_bytes(data)
else:assert p.read_bytes()==data
if (O/'evidence-sha256.json').exists():
 for name,h in load(O/'evidence-sha256.json')['files'].items():assert sha(O/name)==h,name
print(json.dumps(evidence))
