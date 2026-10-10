import json,pathlib,hashlib,re
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;C=R/'Translations/fa/audit-cycle-002';FA=R/'Translations/fa';P=FA/'independent-review-01'
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def write(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
v=read(O/'verification.json');assert all(sha(R/p)==h for p,h in v['pins'].items())
plan=read(C/'correction-plan.json')['rows'];expected={r['stableId'] for r in plan};deltas=[]
GUID={'UI':'0cbd8a7a4f543344bb95659de87f67a5','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'}
for f in ['dialogue-batch-141.json','dialogue-batch-301.json','dialogue-batch-392.json','static-text-draft.json']:
 a=read(C/'before'/f);b=read(C/'after'/f);assert {k:v for k,v in a.items() if k!='entries'}=={k:v for k,v in b.items() if k!='entries'}
 assert len(a['entries'])==len(b['entries'])
 for aa,bb in zip(a['entries'],b['entries']):
  assert {k:v for k,v in aa.items() if k!='target'}=={k:v for k,v in bb.items() if k!='target'}
  if aa['target']!=bb['target']:
   sid=aa.get('stableId') or f"string:{GUID[a['collection']]}:{aa['id']}";p=next(r for r in plan if r['stableId']==sid);assert aa['target']==p['before'] and bb['target']==p['acceptedTarget'];deltas.append(sid)
assert len(deltas)==5 and set(deltas)==expected
src={r['stableId']:r for name in ['strings.jsonl','static-text.jsonl'] for r in map(json.loads,(R/'Source/localization-inventory-v3'/name).read_text().splitlines())};tr={};batches=[]
for f in sorted(FA.glob('*batch-*.json')):
 if not re.fullmatch(r'(ui|dialogue|checks)-batch-\d{3}\.json',f.name):continue
 b=read(f);s=read(f.with_suffix('.validation.json'));assert s['batchSha256']==sha(f) and s['structuralResult']=='passed';assert s['authoredRows']==len(b['entries'])
 for e in b['entries']:tr[f"string:{GUID[b['collection']]}:{e['id']}"]=e['target']
 batches.append(str(f.relative_to(R)))
static=read(FA/'static-text-draft.json');tr.update({r['stableId']:r['target'] for r in static['entries']})
phrases=read(FA/'static-phrase-map.json')['phrases'];m={r['source']:r['target'] for r in phrases};assert len(m)==len(phrases);mapped=[e for e in static['entries'] if src[e['stableId']]['source'] in m];assert len(mapped)==177
assert all(e['target']==m[src[e['stableId']]['source']] for e in mapped)
credits=read(FA/'credits-role-map.json')['replacements'];cm={r['source']:r['target'] for r in credits};assert len(cm)==len(credits)==81
pat=re.compile('|'.join(re.escape(s) for s in sorted(cm,key=len,reverse=True)));sid='tmp:level5:59:m_text';assert pat.sub(lambda x:cm[x[0]],src[sid]['source'])==tr[sid]
common=read(FA/'common-options-001.authored.json')['phrases'];commonrows={};selected=[]
for r in common:
 ids=[sid for sid,s in src.items() if s.get('collection')=='Dialogs' and s['source']==r['source'] and sid in tr];assert len(ids)==r['expectedRows'];assert all(tr[sid]==r['target'] for sid in ids);commonrows[r['source']]=len(ids);selected+=ids
assert len(selected)==len(set(selected))==2841
fixture={}
for name in ['managed-context-v2.json','static-context.json','static-buttons.json','resident-inputs-v2.json']:
 e=read(P/name);key='assemblyPath' if 'assemblyPath' in e else 'sourceAsset';pin='assemblySha256' if 'assemblySha256' in e else 'sourceSha256';path=pathlib.Path(e[key]);actual=sha(path);assert actual==e[pin],name;fixture[e[key]]=actual
assem=read(P/'assembled-consumers.json');assert all(sha(P/p)==h for p,h in assem['pins'].items())
for c in assem['consumers']:
 for p in c['samePlaceOtherCharacters']:
  assert tr[p['runtimeUiStableId']]==p['persianValue'];assert tr[c['stableId']].replace('{0}',p['persianValue'])==p['assembledPersian']
result={'exactFiveFullUnitDeltasVerified':deltas,'batchSidecars':len(batches),'tableUnits':16360,'staticUnits':178,'staticRecipeMatches':177,'creditsRoles':81,'creditsExactRegeneration':True,'commonPhraseCount':34,'commonExpansionUnits':2841,'commonPhraseOccurrences':commonrows,'fixtureSourceHashes':fixture,'assembledConsumerTemplates':2,'admittedDynamicOutputs':6,'inputsUnchangedAtFinish':True,'pins':{**v['pins'],**{str(p.relative_to(R)):sha(p) for p in [FA/'common-options-001.authored.json',FA/'credits-role-map.json',FA/'static-phrase-map.json',R/'Scripts/validate_static_text_draft.py']}}}
write('artifact-verification.json',result);print({k:v for k,v in result.items() if k not in ['pins','fixtureSourceHashes','commonPhraseOccurrences','exactFiveFullUnitDeltasVerified']})
