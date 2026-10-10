from pathlib import Path
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def v(p,h):
 p=ROOT/p if not Path(p).is_absolute() else Path(p)
 a=sha(p);assert a==h,(str(p),h,a);checks.append({'path':str(p),'sha256':a})
handoff=(ROOT/'Translations/nl/semantic-cycle-2/independent-delta-handoff.md').read_text()
for p,h in re.findall(r'`([^`]+)` \| `([0-9a-f]{64})`',handoff):v(p,h)
m=json.loads((ROOT/'Translations/nl/semantic-cycle-2/closure/closure-manifest.json').read_text())
for q in m['pins'].values():v(q['path'],q['sha256'])
for k in ['recipe','adjudication','selectorGroups','reviewRows','consumerContext','deltaReviewRows','previousClosure']:v(m[k+'Path'],m[k+'Sha256'])
for f,k in [('complete-batch-preflight-v2.json','preflightSha256'),('before-rows.jsonl','beforeRowsSha256'),('after-rows.jsonl','afterRowsSha256')]:v('Translations/nl/semantic-cycle-2/'+f,m[k])
v('Translations/nl/semantic-review-rows-pass1.jsonl',m['pass1ReviewRowsSha256'])
v('Translations/nl/independent-review-01/evidence-manifest.json',m['previousIndependentReviewEvidenceSha256'])
prevreceipt=json.loads((ROOT/'Translations/nl/independent-review-01/evidence-manifest.json').read_text())
for q in prevreceipt['artifacts']:v(q['path'],q['sha256'])
for q in [*m['components'].values(),m['nontranslatableContext']]:
 v(q['path'],q['sha256']);assert len((ROOT/q['path']).read_text().splitlines())==q['count']
for q in m['manual']['authoredBatches']:v(q['path'],q['sha256'])
assert hashlib.sha256(''.join(q['path']+' '+q['sha256']+'\n' for q in m['manual']['authoredBatches']).encode()).hexdigest()==m['manual']['authoredSetSha256']
for p,k in [('Translations/nl/static-text-map.json','staticMapSha256'),('Translations/nl/credits-role-map.json','creditsRoleMapSha256')]:v(p,m['manual'][k])
for p,k in [('Translations/nl/static-text-draft.json','staticDraftSha256'),('Translations/nl/semantic-cycle-2/preserve-exact-v4-after.json','preserveExactAfterSha256'),('Translations/nl/semantic-cycle-2/structural-validation.json','structuralValidationSha256')]:v(p,m['derived'][k])
readrows=lambda p:[json.loads(l) for l in p.read_text().splitlines()]
full=readrows(ROOT/m['reviewRowsPath']);delta=readrows(ROOT/m['deltaReviewRowsPath'])
sets={k:set((ROOT/q['path']).read_text().splitlines()) for k,q in m['components'].items()}
prev=set((ROOT/m['previousClosurePath']).read_text().splitlines())
assert sets['new-dependencies']==sets['closure']-prev
assert sets['retired-dependencies']==prev-sets['closure']
assert sets['delta']==sets['changed']|sets['new-dependencies']|sets['explicit-invalidated']
assert len(delta)==367 and len(full)==921
assert [r['stableId'] for r in delta]==(ROOT/m['components']['delta']['path']).read_text().splitlines()
assert [r['stableId'] for r in full]==(ROOT/m['components']['closure']['path']).read_text().splitlines()
rules=json.loads((ROOT/'Source/preserve-exactly-v4.json').read_text());rules={r['stableId']:(i,r) for i,r in enumerate(rules['tableRows']+rules['staticRows'])}
prior={r['stableId']:r for r in readrows(ROOT/'Translations/nl/independent-review-01/review-decisions.jsonl')}
retained=[];order=[]
for r in full:
 i,rule=rules[r['stableId']];order.append(i);assert r['sourceSha256']==rule['sourceSha256']
 for f in ['source','target']:assert hashlib.sha256(r[f].encode()).hexdigest()==r[f+'Sha256']
 p=json.loads((ROOT/r['authoredPath']).read_text())
 es=[e for e in p['entries'] if e.get('stableId')==r['stableId'] or str(e.get('id'))==r['stableId'].rsplit(':',1)[-1]]
 assert len(es)==1 and es[0]['target']==r['target']
 if r['stableId'] not in sets['delta']:
  p=prior[r['stableId']];assert p['sourceSha256']==r['sourceSha256'] and p['targetSha256']==r['targetSha256'];assert p['decision']=='no-objective-text-finding-in-independent-read';retained.append(r['stableId'])
assert order==sorted(order)
out={'status':'passed','verifiedHashes':checks,'fullClosureRowsMechanicallyVerified':921,'deltaRowsToRead':367,'correctedIds':38,'newDependencyIds':329,'explicitInvalidatedIds':0,'retiredIds':848,'reusedReview01UnchangedDecisions':len(retained),'retainedIds':retained,'authoredSetSha256':m['manual']['authoredSetSha256'],'reviewScope':'exact 367 delta; no renewed semantic reads of retained or retired prior rows'}
p=OUT/'preflight.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n')
print('Verified',len(checks),'hashes; exact 367-ID delta; reused',len(retained),'unchanged current-closure decisions.')
