#!/usr/bin/env python3
"""Read-only reproduction of Indonesian cycle-01 review inputs and selectors."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
B=ROOT/'Translations/id/semantic-correction-cycle-01'
OUT=Path(__file__).resolve().parent
def read(p): return json.loads((ROOT/p).read_text())
def digest(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
h=read(str(B.relative_to(ROOT)/'independent-review-handoff.json'))
a=read(str(B.relative_to(ROOT)/'artifact-manifest.json'))
c=read(str(B.relative_to(ROOT)/'component-manifest.json'))
s=read(str(B.relative_to(ROOT)/'closure-selector-spec.json'))
records=h['evidence']+[r for k in ['sourceAndGlossary','manuals','authoredPhraseMaps','targetInputs','validationSidecars','semanticFirstPassParts'] for r in a[k]]+list(c['components'].values())+list(c['regressionGroups'].values())
checks=[dict(path=r['path'],expected=r['sha256'],actual=digest(r['path'])) for r in records]
assert all(r['expected']==r['actual'] for r in checks)
p=read('Source/preserve-exactly-v4.json'); ordered=p['tableRows']+p['staticRows']; ids=[r['stableId'] for r in ordered]; assert len(ids)==len(set(ids))==16538
protected={r['stableId']:r for r in ordered}
source={}
for path in ['Source/localization-inventory-v3/strings.jsonl','Source/localization-inventory-v3/static-text.jsonl']:
 for line in (ROOT/path).read_text().splitlines():
  r=json.loads(line); assert r['stableId'] not in source; source[r['stableId']]=r
targets={}; files={}
identity={(r['collection'],r['stableId'].rsplit(':',1)[1]):r['stableId'] for r in p['tableRows']}
for rec in a['targetInputs']:
 x=read(rec['path']); collection=x.get('collection'); guid={'UI':'0cbd8a7a4f543344bb95659de87f67a5','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','ChecksDialogs':'cba33ba290797ef44a2b58ea56366d6b4'}.get(collection)
 for e in x['entries']:
  sid=e.get('stableId')
  if sid is None:
   # Resolve accepted table identity against the canonical inventory, never infer GUID.
   matches=[identity[(collection,str(e['id']))]]
   assert len(matches)==1,(collection,e); sid=matches[0]
  assert sid not in targets; targets[sid]=e['target']; files[sid]=rec['path']
assert set(targets)==set(ids)
ad=read(str(B.relative_to(ROOT)/'adjudication.json'))
changed={r['stableId'] for r in ad['rows'] if r['decision']=='accepted'}
nodes={n for sid in changed for n in source[sid].get('nodeNames',[])}
context={sid for sid in ids if nodes.intersection(source[sid].get('nodeNames',[]))}
repeated={sid for sid in ids if source[sid]['source'] in {source[t]['source'] for t in changed}}
regex=[re.compile(v) for v in s['glossaryReferentsSourceRegex'].values()]
concept={sid for sid in ids if any(r.search(source[sid]['source']) for r in regex)}
special=lambda sid:any(protected[sid].get(k) for k in ['formatSlots','tmpTags','wholeTextExact','exactSubstrings','lineBreaks','trailingWhitespace'])
runtime={sid for sid in changed|context if special(sid) or source[sid].get('collection') in ['UI','ChecksDialogs']}
pronouns=re.compile(s['characterSourcePronounRegex'])
kinship=re.compile(s['glossaryReferentsSourceRegex']['kinshipAndChildAge'])
groups={
 'ui-menu-hud-locale-save-input':{sid for sid in ids if source[sid].get('collection')=='UI'},
 'static-tmp-credits-environment':{r['stableId'] for r in p['staticRows']},
 'accepted-checks':{sid for sid in ids if source[sid].get('collection')=='ChecksDialogs'},
 'protected-placeholders-markup-breaks-symbols':{sid for sid in ids if special(sid)},
 'gender-kinship-address':{sid for sid in ids if kinship.search(source[sid]['source']) or (sid in context and pronouns.search(source[sid]['source']))},
 'mixed-script-target':{sid for sid in ids if re.search('[А-Яа-яЁё]',targets[sid])}
}
components={'changed':changed,'context':context,'repetitions':repeated,'glossary-referents':concept,'runtime-bindings':runtime,'mandatory-regressions':set.union(*groups.values())}
components['closure']=set.union(*components.values())
results=[]
for name,sets,manifest in [('component',components,c['components']),('regression',groups,c['regressionGroups'])]:
 for key,selected in sets.items():
  got=''.join(sid+'\n' for sid in ids if sid in selected).encode(); m=manifest[key]; actual=(ROOT/m['path']).read_bytes()
  results.append(dict(kind=name,key=key,count=len(selected),expectedCount=m['count'],sha256=hashlib.sha256(got).hexdigest(),exactBytesEqual=got==actual,missing=list(set(actual.decode().splitlines())-selected),extra=list(selected-set(actual.decode().splitlines()))))
rows=[json.loads(line) for line in (B/'closure-review-rows.jsonl').read_text().splitlines()]
rowerrors=[]
assert [r['stableId'] for r in rows]==[sid for sid in ids if sid in set((B/'closure.ids.txt').read_text().splitlines())]
for r in rows:
 sid=r['stableId']
 if r['source']!=source[sid]['source'] or r['target']!=targets[sid] or r['targetFile']!=files[sid] or r['targetFileSha256']!=digest(files[sid]) or r['sourceOrderIndex']!=ids.index(sid)+1: rowerrors.append(sid)
report=dict(schemaVersion=1,handoffSha256=digest(str(B.relative_to(ROOT)/'independent-review-handoff.json')),hashChecks=len(checks),hashMismatches=[],targetInputs=len(a['targetInputs']),validationSidecars=len(a['validationSidecars']),canonicalIds=len(ids),closureRows=len(rows),rowErrors=rowerrors,selectorResults=results)
(OUT/'verification-final.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='selectorResults'})); print(json.dumps(results))
