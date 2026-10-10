#!/usr/bin/env python3
"""Read-only reproducibility check; does not replace recorded human pair reads."""
from pathlib import Path
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pins=load(OUT/'input-verification.json')['pins']
for p,h in pins.items():assert sha(ROOT/p)==h,p
c=load(ROOT/'Translations/bg/semantic-closure-cycle-002.json');d=load(ROOT/'Translations/bg/semantic-delta-cycle-002.json');rows=d['nextReviewRows'];ids=[r['stableId'] for r in rows]
for component in d['components'].values():
 assert component['count']==len(component['ids'])==len(set(component['ids']))
 assert sha(ROOT/component['path'])==component['sha256']
 assert (ROOT/component['path']).read_text().splitlines()==component['ids']
union=set().union(*(set(d['components'][k]['ids']) for k in ['corrected','newClosure','invalidatedPrior']))
assert union==set(ids)==set(d['components']['review']['ids']) and len(ids)==2110
assert [len(d['components'][k]['ids']) for k in ['corrected','newClosure','invalidatedPrior','retired']]==[147,1180,894,0]
assert (OUT/'read.ids').read_bytes()==(ROOT/'Translations/bg/semantic-cycle-002-review.ids').read_bytes()
ledger=load(OUT/'per-id-read-verdicts.json');assert len(ledger)==len(rows)
findings=load(OUT/'findings.json')['findings'];byId={f['stableId']:f for f in findings};assert len(byId)==len(findings)==43
for i,(row,item) in enumerate(zip(rows,ledger)):
 assert item['deltaIndex']==i and item['stableId']==row['stableId'] and item['fullPairRead']
 for field in ['source','target']:assert item[field+'Sha256']==hashlib.sha256(row[field].encode()).hexdigest()
 if row['stableId'] in byId:
  f=byId[row['stableId']];assert f['source']==row['source'] and f['currentFullTarget']==row['target'] and item['findingId']==f['findingId']
 else:assert item['findingId'] is None
mandatory=set(c['components']['mandatoryRegressions']['ids']);fresh=set((OUT/'mandatory-fresh-read.ids').read_text().splitlines());reuse=set((OUT/'mandatory-prior-applicable.ids').read_text().splitlines())
assert len(mandatory)==908 and len(fresh)==401 and len(reuse)==507 and fresh.isdisjoint(reuse) and fresh|reuse==mandatory
old={r['stableId']:r for r in load(ROOT/'Translations/bg/semantic-closure-cycle-001.json')['reviewRows']};now={r['stableId']:r for r in c['reviewRows']}
for sid in reuse:assert all(now[sid][k]==old[sid][k] for k in ['source','target','key','sceneNodes'])
s=load(ROOT/'Translations/bg/voice-risk-selector-v4.json');v=load(ROOT/'Translations/bg/voice-remedial-candidates-v4.json');prefixes=tuple(s['corePrefixes']+s['secondaryPrefixes']);words=lambda text:re.findall('[А-Яа-яЁё]+',text.lower())
source=[json.loads(line) for line in (ROOT/'Source/localization-inventory-v3/strings.jsonl').open()];dialogs=[r for r in source if r['collection']=='Dialogs'];assert len(dialogs)==16100
selected=[]
for row in dialogs:
 matched=sorted(set(w for w in words(row['source']) if w.startswith(prefixes)))
 if matched:selected.append((row['stableId'],matched))
assert selected==[(r['stableId'],r['matchedWords']) for r in v['candidates']] and len(selected)==735
assert set(x[0] for x in selected)<=set(ids)
sel=load(OUT/'selector-findings.json');extra=('посра','срал','теребоньк','смехуеч','ахуит');exact={'хз','хули'};selectedIds=set(x[0] for x in selected)
missed=[r['stableId'] for r in dialogs if r['stableId'] not in selectedIds and any(w.startswith(extra) or w in exact for w in words(r['source']))]
assert missed==sel['missingIds'] and len(missed)==6 and len(set(missed)-set(ids))==4
manifestPath=OUT/'evidence-sha256.json'
if manifestPath.exists():
 for name,h in load(manifestPath)['files'].items():assert sha(OUT/name)==h,name
print(json.dumps({'verified':True,'deltaPairs':len(rows),'mandatoryFresh':len(fresh),'mandatoryPriorApplicable':len(reuse),'findings':len(findings),'voiceCandidates':len(selected),'selectorMisses':len(missed),'pins':len(pins)}))
