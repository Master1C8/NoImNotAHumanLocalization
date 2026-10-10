"""Cycle004 independent evidence reconciliation; writes only this review directory."""
import json,hashlib,datetime
from pathlib import Path
from bytecode_decoder import actual,assembly
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;C=ROOT/'Translations/fil/semantic-correction-cycle-004';P=ROOT/'Translations/fil/independent-review-03'
def load(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def th(s):return hashlib.sha256(s.encode()).hexdigest()
def write(n,d):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def writejl(n,rows):
 p=OUT/n;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))
checks=[]
def pin(p,v):
 assert sha(p)==v,(str(p),v,sha(p));checks.append(dict(path=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),sha256=v))
h=load(C/'handoff.json');cl=load(C/'closure.json');after=load(C/'after.json')
for r in h['sourceAndGlossaryFingerprints'].values():pin(ROOT/r['path'],r['sha256'])
for n,v in h['cycleFilesSha256'].items():pin(C/n,v)
for n,v in h['priorReviewEvidenceSha256'].items():pin(P/n,v)
for r in load(P/'completion-manifest.json')['files']:pin(ROOT/r['path'],r['sha256'])
g=load(OUT/'full-corpus-validation.json')
for r in g['authoredFiles']:pin(ROOT/r['path'],r['sha256'])
for key,path in [('validatorSha256','Scripts/validate_locale_corpus.py'),('inputLoaderSha256','Scripts/locale_text_inputs.py')]:pin(ROOT/path,g[key])
for n,v in g['owningValidators'].items():pin(ROOT/'Scripts'/n,v)
assert g['rows']==16538 and g['structuralResult']==g['exactResult']=='passed'
# Reconcile historical input pins using the exact changed authored batch and sidecar.
f=after['file'];exceptions={f['authoredPath']:f['beforeSha256'],f['validationPath']:None};historical=[]
iv=load(P/'input-verification.json')
for r in iv['pinChecks']:
 p=ROOT/r['path'];v=r['expected']
 if sha(p)!=v:
  assert r['path'] in exceptions,(r['path'],v,sha(p))
  if exceptions[r['path']]:assert v==exceptions[r['path']]
  historical.append(dict(path=r['path'],historicalSha256=v,currentSha256=sha(p),reason='cycle004 single target correction or owning sidecar; exact before snapshot pinned'))
 else:pin(p,v)
for r in iv['historicalChangedPins']:pin(ROOT/r['path'],r['currentSha256'])
# Current full-corpus authored map, no historical sidecar interpretation.
G={'UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1'};targets={}
for r in g['authoredFiles']:
 d=load(ROOT/r['path'])
 for e in d['entries']:
  sid=e['stableId'] if r['path'].endswith('static-text-draft.json') else f"string:{G[d['collection']]}:{e['id']}"
  assert sid not in targets;targets[sid]=e['target']
assert len(targets)==16538
inv=jl(ROOT/'Source/localization-inventory-v3/strings.jsonl')+jl(ROOT/'Source/localization-inventory-v3/static-text.jsonl');sm={r['stableId']:r for r in inv};bykey={r['key']:r for r in inv if r.get('key')};bykey.update({r['key']:r for r in inv if r.get('key') and r['stableId'] in targets})
current=jl(C/'closure-paired.jsonl');prior=jl(ROOT/'Translations/fil/semantic-correction-cycle-003/closure-paired.jsonl');fresh=jl(C/'next-delta-paired.jsonl');decisions=jl(P/'closure-decision-applicability.jsonl')
cm={r['stableId']:r for r in current};pm={r['stableId']:r for r in prior};dm={r['stableId']:r for r in decisions};fm={r['stableId']:r for r in fresh}
assert len(cm)==len(current)==7612 and len(pm)==len(prior)==len(dm)==len(decisions)==7604 and len(fm)==len(fresh)==26 and set(pm)==set(dm)
for r in current:
 s=sm[r['stableId']];assert r['source']==s['source'] and r['key']==s.get('key') and r['nodeNames']==s.get('nodeNames',[]) and th(r['source'])==r['sourceSha256'] and targets[r['stableId']]==r['target'] and th(r['target'])==r['targetSha256']
new=set(cm)-set(pm);retired=set(pm)-set(cm);corrected=set(cl['corrected']['ids']);invalid=set(cl['explicitlyInvalidatedPriorEvidence']['ids']);delta=corrected|new|invalid
assert (len(new),len(retired),len(corrected),len(invalid),len(delta))==(13,5,1,12,26) and delta==set(fm)
for r in cl['components']+[cl[k] for k in ['currentClosure','newCurrentMinusPrevious','retiredPreviousMinusCurrent','corrected','explicitlyInvalidatedPriorEvidence','exactNextDelta','review03RetiredDependenciesStillRetired','review03RetiredDependenciesReentered']]:
 assert len(r['ids'])==len(set(r['ids']))==r['count'] and th(''.join(s+'\n' for s in r['ids']))==r['idsSha256']
reused=[]
for sid in cm:
 if sid not in delta:
  a,b,d=cm[sid],pm[sid],dm[sid];assert all(a[k]==b[k] for k in ['source','target','key','nodeNames','sourceSha256','targetSha256']) and d['findingId'] is None
  assert all(a[k]==d[k] for k in ['sourceSha256','targetSha256','key','nodeNames'])
  reused.append(dict(stableId=sid,acceptedOrdinal=a['acceptedOrdinal'],sourceSha256=a['sourceSha256'],targetSha256=a['targetSha256'],key=a['key'],nodeNames=a['nodeNames'],decision='applicable-independent-reviewed-unit',evidenceMode='exact-review03-reuse',findingId=None,decisionEvidence='Translations/fil/independent-review-03/closure-decision-applicability.jsonl'))
assert len(reused)==7586
retirement=[]
for sid in cl['retiredPreviousMinusCurrent']['ids']:
 b=pm[sid];d=dm[sid];s=sm[sid];assert s['source']==b['source'] and s.get('key')==b['key'] and s.get('nodeNames',[])==b['nodeNames'] and targets[sid]==b['target'] and all(b[k]==d[k] for k in ['sourceSha256','targetSha256','key','nodeNames']) and d['findingId'] is None
 assert sid not in cm and all(sid not in c['ids'] for c in cl['components']) and set(b['components'])<=set(['explicitContext','runtimeBinding'])
 retirement.append(dict(b,priorDecisionEvidence='Translations/fil/independent-review-03/closure-decision-applicability.jsonl',retiredCycle=4,reason='unchanged Esenin_Asking_3_1 scene-only peer outside every current selector'))
for r in jl(P/'retired-dependencies.jsonl'):
 sid=r['stableId'];s=sm[sid];assert th(s['source'])==r['sourceSha256'] and th(targets[sid])==r['targetSha256'] and s.get('nodeNames',[])==r['nodeNames'] and sid not in cm
 retirement.append(dict(r,retiredCycle=3,continuedApplicability='exact unchanged pins; remains outside all current components'))
assert len(retirement)==len({r['stableId'] for r in retirement})==54
# Recheck previous independently decoded compiled contexts against current actual bytecode.
ctxfiles=[P/'independent-compiled-context.json',ROOT/'Translations/fil/independent-review-02/additional-compiled-context.json'];prior_context=[]
for path in ctxfiles:
 ctx=load(path);matched=0
 for n,node in ctx['nodes'].items():
  assert node['labels']==actual[n]['labels'] and len(node['instructions'])==len(actual[n]['instructions'])
  for a,b in zip(node['instructions'],actual[n]['instructions']):assert all(a[k]==b[k] for k in ['index','opcode','op','operands'])
  matched+=len(node['instructions'])
 prior_context.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path),nodes=len(ctx['nodes']),instructions=matched))
names=set(n for r in fresh for n in r['nodeNames'])
# A legacy inventory row lacks nodeNames; discover its actual compiled consumer by stable key.
for r in fresh:
 if not r['nodeNames']:
  found=[n for n,node in actual.items() if any(i['op'] in ['RunLine','AddOption'] and i['operands'][0]==r['key'] for i in node['instructions'])]
  assert found or r['acceptedOrdinal']==5593;names.update(found)
nodes={}
for n in sorted(names):
 rows=[]
 for i in actual[n]['instructions']:
  s=bykey.get(i['operands'][0]) if i['op'] in ['RunLine','AddOption'] else None
  rows.append(dict(i,source=s['source'] if s else None,sourceStableId=s['stableId'] if s else None,target=targets.get(s['stableId']) if s else None))
 nodes[n]=dict(labels=actual[n]['labels'],instructions=rows)
dynamic=load(ROOT/'Translations/fil/semantic-correction-cycle-002/plan.json')['unchangedDynamicConsumers']
for r in dynamic:assert sm[r['stableId']]['sourceSha256']==r['sourceSha256'] and th(targets[r['stableId']])==r['targetSha256']
pin(ROOT/'Translations/fil/independent-review-01/dynamic-assembly-decisions.json',load(P/'recipe-regressions.json')['dynamicConsumers']['contextEvidenceSha256'])
mandatory=set(next(r for r in cl['components'] if r['name']=='mandatoryRegression')['ids']);prior_mandatory={r['stableId']:r for r in jl(P/'mandatory-regression-applicability.jsonl')}
assert len(mandatory)==7240 and len(mandatory&delta)==18 and len(mandatory-delta)==7222
for sid in mandatory-delta:assert sid in prior_mandatory and prior_mandatory[sid]['findingId'] is None and all(cm[sid][k]==prior_mandatory[sid][k] for k in ['sourceSha256','targetSha256','key','nodeNames'])
write('input-verification.json',dict(reviewer='/root/fil_independent_review_04',pinChecks=checks,historicalChangedPins=historical,closure=7612,delta=26,new=13,corrected=1,invalidated=12,reused=7586,retiredNew=5,retiredPrior=49,mandatoryTotal=7240,mandatoryFresh=18,mandatoryReused=7222,compiledProgramSha256=h['compiledProgramSha256'],opcodeAssembly=dict(path=str(assembly),sha256=sha(assembly)),priorCompiledContextApplicability=prior_context,freshSceneNodes=len(nodes),freshSceneInstructions=sum(len(n['instructions']) for n in nodes.values()),dynamicConsumers=dynamic,cutoffUtc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
write('independent-compiled-context.json',dict(compiledProgramSha256=h['compiledProgramSha256'],nodes=nodes))
writejl('prior-decision-applicability.jsonl',reused);writejl('retired-dependencies.jsonl',retirement)
print(json.dumps(dict(pins=len(checks),historicalChanged=len(historical),closure=7612,delta=26,reused=7586,retired=54,mandatory=7240,mandatoryFresh=18,sceneNodes=len(nodes),sceneInstructions=sum(len(n['instructions']) for n in nodes.values()),priorContext=prior_context)))
