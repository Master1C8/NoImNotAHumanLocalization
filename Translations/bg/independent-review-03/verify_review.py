"""Read-only verification of sealed independent decisions and proposal safety."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent
BG=ROOT/'Translations/bg'
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tsha=lambda s:hashlib.sha256(s.encode()).hexdigest()
subprocess.run([sys.executable,str(OUT/'verify_inputs.py'),'verify'],check=True,stdout=subprocess.DEVNULL)
d=load(BG/'semantic-delta-cycle-003.json');c=load(BG/'semantic-closure-cycle-003.json')
rows=d['nextReviewRows'];current={r['stableId']:r for r in c['reviewRows']}
ledger=load(OUT/'per-id-read-verdicts.json');findings=load(OUT/'findings.json')['findings']
issues={f['stableId']:f for f in findings};assert len(issues)==len(findings)==3
assert len(ledger)==len(rows)==311
assert (OUT/'read.ids').read_bytes()==(BG/'semantic-cycle-003-review.ids').read_bytes()
for i,(r,v) in enumerate(zip(rows,ledger)):
    assert v['deltaIndex']==i and v['stableId']==r['stableId'] and v['fullPairRead']
    assert v['sourceSha256']==tsha(r['source']) and v['targetSha256']==tsha(r['target'])
    assert v['findingId']==issues.get(r['stableId'],{}).get('findingId')
corrected=load(OUT/'corrected-unit-verdicts.json');plan=load(BG/'correction-batch-003.json')
assert len(corrected)==41 and {r['stableId'] for r in corrected}=={r['stableId'] for r in plan['decisions']}
assert all(r['fullPairRead'] and r['stableId'] not in issues for r in corrected)
dismissed=load(OUT/'dismissed-proposals-verdicts.json');assert len(dismissed)==3
for r in dismissed: assert r['fullPairRead'] and r['currentFullTarget']==current[r['stableId']]['target']
supp=load(OUT/'supplementary-pair-verdicts.json');assert len(supp)==3
assert all(r['fullPairRead'] and r['stableId'] not in set(d['components']['review']['ids']) for r in supp)
fresh=set((OUT/'mandatory-fresh-read.ids').read_text().splitlines());reuse=set((OUT/'mandatory-prior-applicable.ids').read_text().splitlines())
mandatory=set(c['components']['mandatoryRegressions']['ids']);assert len(fresh)==4 and len(reuse)==904
assert fresh.isdisjoint(reuse) and fresh|reuse==mandatory and fresh.isdisjoint(issues)
sys.path.insert(0,str(ROOT/'Scripts'))
from preserve_exact import check_value
manifest=load(ROOT/'Source/preserve-exactly-v4.json')
rules={r['stableId']:r for r in manifest['tableRows']+manifest['staticRows']}
for f in findings:
    r=current[f['stableId']]
    assert f['source']==r['source'] and f['currentFullTarget']==r['target']
    assert f['sourceSha256']==tsha(r['source']) and f['targetSha256']==tsha(r['target'])
    assert f['proposedFullTarget']!=r['target'] and not f['applied']
    check_value(rules[f['stableId']],f['proposedFullTarget'])
fresh_corpus=load(OUT/'locale-corpus.json');assert fresh_corpus['rows']==16538
assert fresh_corpus['structuralResult']==fresh_corpus['exactResult']=='passed'
pins=load(OUT/'input-verification.json')['pins']
assert all(pins[f['path']]==f['sha256'] for f in fresh_corpus['authoredFiles'])
review=load(OUT/'review.json');assert review['coverage']['totalDistinctFreshIndependentPairs']==314
assert review['findings']['sha256']==sha(OUT/'findings.json') and not review['acceptance']['independentClean']
for p in ['Source/localization-inventory-v3/strings.jsonl','Documentation/glossary-translations/canonical-reviews/artifacts/bg/layer.json',
          'Translations/bg/correction-batch-003.json','Translations/bg/correction-batch-003-result.json',
          'Translations/bg/semantic-closure-cycle-003.json','Translations/bg/semantic-delta-cycle-003.json','Translations/bg/semantic-cycle-003-review.ids']:
    assert sha(ROOT/p) in (OUT/'REPORT.md').read_text(), 'Report hash mismatch: '+p
manifest_path=OUT/'evidence-sha256.json'
if manifest_path.exists():
    m=load(manifest_path)
    assert set(m['files'])=={p.name for p in OUT.iterdir() if p.is_file() and p.name!='evidence-sha256.json'}
    for name,h in m['files'].items():assert sha(OUT/name)==h,name
print(json.dumps({'verified':True,'deltaFullUnitDecisions':311,'supplementaryFullUnitDecisions':3,
                  'correctedAccepted':41,'dismissedProposalsUpheld':3,'mandatoryFresh':4,'mandatoryPriorExactApplicable':904,
                  'findings':3,'selectorDefects':0,'allProposedFullUnitsProtectedGrammar':'passed',
                  'freshCorpusRows':16538,'independentClean':False}))
