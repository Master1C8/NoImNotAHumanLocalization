"""Independent cycle003 verification; writes only new reviewer artifacts."""
import hashlib,json,struct,re,datetime
from pathlib import Path
import dnfile
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;C=ROOT/'Translations/fil/semantic-correction-cycle-003';P=ROOT/'Translations/fil/independent-review-02'
def load(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def th(s):return hashlib.sha256(s.encode()).hexdigest()
def ih(ids):return th(''.join(x+'\n' for x in ids))
checks=[]
def pin(p,h):
 a=sha(p);assert a==h,(str(p),h,a);checks.append(dict(path=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),expected=h,actual=a))
def write(name,d):
 p=OUT/name;assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
h=load(C/'handoff.json');plan=load(C/'plan.json');after=load(C/'after.json');cl=load(C/'closure.json');pv=load(P/'verification.json')
for row in h['sourceAndGlossaryFingerprints'].values():pin(ROOT/row['path'],row['sha256'])
for n,v in h['cycleFilesSha256'].items():pin(C/n,v)
for n,v in h['priorReviewEvidenceSha256'].items():pin(P/n,v)
for row in load(P/'completion-manifest.json')['files']:pin(ROOT/row['path'],row['sha256'])
# Historical pin records are reconciled against exact correction snapshots rather than rewritten.
exceptions={}
for f in after['files']:
 exceptions[f['authoredPath']]=f['beforeSha256'];exceptions[f['validationPath']]=None
historical_changed=[]
for row in pv['pinChecks']:
 p=ROOT/row['path'];expected=row['expected'];actual=sha(p)
 if actual!=expected:
  assert row['path'] in exceptions,(row['path'],expected,actual)
  if exceptions[row['path']] is not None:assert expected==exceptions[row['path']]
  historical_changed.append(dict(path=row['path'],historicalSha256=expected,currentSha256=actual,reason='cycle003 corrected authored input or owning validation sidecar; before snapshot separately pinned'))
 else:pin(p,expected)
current=jl(C/'closure-paired.jsonl');previous=jl(ROOT/'Translations/fil/semantic-correction-cycle-002/closure-paired.jsonl');fresh=jl(C/'next-delta-paired.jsonl');decisions=jl(P/'closure-decision-applicability.jsonl')
cm={r['stableId']:r for r in current};pm={r['stableId']:r for r in previous};dm={r['stableId']:r for r in decisions};fm={r['stableId']:r for r in fresh}
assert len(cm)==len(current)==7604 and len(pm)==len(previous)==len(dm)==7645 and len(fm)==len(fresh)==20
inv=jl(ROOT/'Source/localization-inventory-v3/strings.jsonl')+jl(ROOT/'Source/localization-inventory-v3/static-text.jsonl');sm={r['stableId']:r for r in inv}
for r in current:
 s=sm[r['stableId']];assert r['source']==s['source'] and r['key']==s.get('key') and r['nodeNames']==s.get('nodeNames',[]) and th(r['source'])==r['sourceSha256'] and th(r['target'])==r['targetSha256']
new=set(cm)-set(pm);retired=set(pm)-set(cm);corrected=set(cl['corrected']['ids']);invalid=set(cl['explicitlyInvalidatedPriorEvidence']['ids']);delta=corrected|new|invalid
assert len(new)==8 and len(retired)==49 and len(corrected)==2 and len(invalid)==10 and delta==set(fm)
for r in cl['components']+[cl[k] for k in ['currentClosure','newCurrentMinusPrevious','retiredPreviousMinusCurrent','corrected','explicitlyInvalidatedPriorEvidence','exactNextDelta']]:assert len(r['ids'])==r['count'] and ih(r['ids'])==r['idsSha256']
reused=set(cm)-delta;reuse=[]
for sid in cm:
 if sid in reused:
  a,b,d=cm[sid],pm[sid],dm[sid];assert all(a[k]==b[k] for k in ['source','target','key','nodeNames','sourceSha256','targetSha256']);assert a['sourceSha256']==d['sourceSha256'] and a['targetSha256']==d['targetSha256'] and d['findingId'] is None
  reuse.append(dict(stableId=sid,sourceSha256=a['sourceSha256'],targetSha256=a['targetSha256'],key=a['key'],nodeNames=a['nodeNames'],evidenceMode='exact-review02-reuse',decisionEvidence='Translations/fil/independent-review-02/closure-decision-applicability.jsonl'))
assert len(reuse)==7584
retirement=[]
for sid in cl['retiredPreviousMinusCurrent']['ids']:
 b=pm[sid];d=dm[sid];s=sm[sid];assert s['source']==b['source'] and s.get('key')==b['key'] and s.get('nodeNames',[])==b['nodeNames'];assert d['sourceSha256']==b['sourceSha256'] and d['targetSha256']==b['targetSha256'] and d['findingId'] is None
 assert sid not in cm and not any(sid in c['ids'] for c in cl['components'])
 retirement.append(dict(stableId=sid,sourceSha256=b['sourceSha256'],targetSha256=b['targetSha256'],priorComponents=b['components'],nodeNames=b['nodeNames'],reason='no current selector; prior scene-only context dependency retired; exact reviewed source/target retained'))
# Independently decode actual program with enum/field constants from shipped assembly.
assembly=Path(load(ROOT/'dynamic-producer-context.json')['assemblyPath']).parent/'YarnSpinner.dll';pe=dnfile.dnPE(str(assembly));owners={id(f.row):str(t.TypeName) for t in pe.net.mdtables.TypeDef for f in t.FieldList};constants={}
for c in pe.net.mdtables.Constant:
 owner=owners.get(id(c.Parent.row))
 if owner in ['Program','Node','Instruction','Operand','OpCode']:constants[owner+'.'+str(c.Parent.row.Name)]=int.from_bytes(bytes(c.Value.value),'little')
ops={v:k.split('.')[-1] for k,v in constants.items() if k.startswith('OpCode.')}
def vi(b,p):
 v=0;s=0
 while True:
  z=b[p];p+=1;v|=(z&127)<<s
  if not z&128:return v,p
  s+=7;assert s<=70

def wire(b):
 p=0;fs=[]
 while p<len(b):
  tag,p=vi(b,p);f,w=tag>>3,tag&7
  if w==0:v,p=vi(b,p)
  elif w==2:n,p=vi(b,p);v=b[p:p+n];p+=n
  elif w==5:v=b[p:p+4];p+=4
  elif w==1:v=b[p:p+8];p+=8
  else:raise AssertionError(w)
  fs.append((f,w,v))
 assert p==len(b);return fs

def operand(b):
 fs=wire(b);assert len(fs)==1;f,w,v=fs[0]
 if f==constants['Operand.StringValueFieldNumber']:return v.decode()
 if f==constants['Operand.BoolValueFieldNumber']:return bool(v)
 if f==constants['Operand.FloatValueFieldNumber']:return struct.unpack('<f',v)[0]
 raise AssertionError(f)
raw=bytes(load(ROOT/'Source/glossary-corpus-v2/runtime-bindings.json')['sharedassets0.assets:2743']['compiledYarnProgram']);assert hashlib.sha256(raw).hexdigest()==h['compiledProgramSha256'];actual={}
for f,w,entry in wire(raw):
 if f!=constants['Program.NodesFieldNumber']:continue
 fs=wire(entry);name=next(v.decode() for f,w,v in fs if f==1);node=next(v for f,w,v in fs if f==2);ins=[];labels={}
 for f,w,v in wire(node):
  if f==constants['Node.InstructionsFieldNumber']:
   ff=wire(v);op=next((v for f,w,v in ff if f==constants['Instruction.OpcodeFieldNumber']),0);args=[operand(v) for f,w,v in ff if f==constants['Instruction.OperandsFieldNumber']];ins.append(dict(index=len(ins),opcode=op,op=ops[op],operands=args))
  elif f==3:
   ff=wire(v);labels[next(v.decode() for f,w,v in ff if f==1)]=next((v for f,w,v in ff if f==2),0)
 actual[name]=dict(labels=labels,instructions=ins)
ctx=load(P/'additional-compiled-context.json');matched=0
for name,node in ctx['nodes'].items():
 assert node['labels']==actual[name]['labels']
 for a,b in zip(node['instructions'],actual[name]['instructions']):assert all(a[k]==b[k] for k in ['index','opcode','op','operands'])
 assert len(node['instructions'])==len(actual[name]['instructions']);matched+=len(node['instructions'])
bykey={r['key']:r for r in inv if r.get('key')};targets={r['stableId']:r['target'] for r in current}
# Whole-corpus guard independently pins all current targets; context outside closure uses current authored data.
G={'UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1'}
for r in load(C/'full-structural-validation.json')['batchReports']:
 for e in load(ROOT/r['path'])['entries']:targets[f"string:{G[load(ROOT/r['path'])['collection']]}:{e['id']}"]=e['target']
for r in retirement:assert th(targets[r['stableId']])==r['targetSha256']
names=set(n for r in fresh for n in r['nodeNames']);nodes={}
for name in sorted(names):
 n=actual[name];rows=[]
 for i in n['instructions']:
  s=bykey.get(i['operands'][0]) if i['op'] in ['RunLine','AddOption'] else None
  rows.append(dict(i,source=s['source'] if s else None,sourceStableId=s['stableId'] if s else None,target=targets.get(s['stableId']) if s else None))
 nodes[name]=dict(labels=n['labels'],instructions=rows)
dynamic=load(ROOT/'Translations/fil/semantic-correction-cycle-002/plan.json')['unchangedDynamicConsumers']
for r in dynamic:assert sm[r['stableId']]['sourceSha256']==r['sourceSha256'] and th(targets[r['stableId']])==r['targetSha256']
mandatory=set(next(r for r in cl['components'] if r['name']=='mandatoryRegression')['ids']);assert len(mandatory)==7234 and len(mandatory&delta)==12
write('input-verification.json',dict(reviewer='/root/fil_independent_review_03',cutoffUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pinChecks=checks,historicalChangedPins=historical_changed,closure=7604,delta=20,new=8,corrected=2,invalidated=10,retired=49,reused=7584,mandatoryTotal=7234,mandatoryFresh=12,mandatoryReused=len(mandatory-delta),compiledProgramSha256=h['compiledProgramSha256'],opcodeAssembly=dict(path=str(assembly),sha256=sha(assembly)),priorContextNodesVerified=len(ctx['nodes']),priorContextInstructionsVerified=matched,freshSceneNodes=len(nodes),freshSceneInstructions=sum(len(n['instructions']) for n in nodes.values()),dynamicConsumers=dynamic))
write('independent-compiled-context.json',dict(compiledProgramSha256=h['compiledProgramSha256'],nodes=nodes))
for name,rows in [('prior-decision-applicability.jsonl',reuse),('retired-dependencies.jsonl',retirement)]:
 p=OUT/name;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))
print(json.dumps(dict(pins=len(checks),historicalChangedPins=historical_changed,closure=7604,fresh=20,reuse=7584,retired=49,mandatory=7234,mandatoryFresh=12,sceneNodes=len(nodes),sceneInstructions=sum(len(n['instructions']) for n in nodes.values()),priorContextNodes=len(ctx['nodes']),priorContextInstructions=matched),indent=2))
