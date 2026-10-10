"""Read-only independent cycle002 verification; writes only new reviewer evidence."""
import hashlib,json,struct,re,datetime
from pathlib import Path
import dnfile
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
C=ROOT/'Translations/fil/semantic-correction-cycle-002'; P=ROOT/'Translations/fil/independent-review-01'
def load(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def th(s):return hashlib.sha256(s.encode()).hexdigest()
def ih(ids):return th(''.join(x+'\n' for x in ids))
checks=[]
def pin(p,h):
 a=sha(p);assert a==h,(str(p),h,a); checks.append(dict(path=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),expected=h,actual=a))
plan=load(C/'plan.json');after=load(C/'after.json'); gate=load(C/'full-structural-validation.json');closure=load(C/'closure.json');handoff=load(C/'handoff.json'); pv=load(P/'verification.json')
for p in plan['sourceAndGlossaryFingerprints'].values():pin(ROOT/p['path'],p['sha256'])
for k,v in handoff.items():
 if isinstance(v,dict):
  for field,val in v.items():
   if field.endswith('Path') and field[:-4]+'Sha256' in v:pin(ROOT/val,v[field[:-4]+'Sha256'])
pin(ROOT/plan['previousClosurePath'],plan['previousClosureSha256'])
pin(ROOT/'Translations/fil/semantic-correction-cycle-001.paired.jsonl',plan['previousPairedSha256'])
for name,h in plan['reviewEvidenceSha256'].items():pin(P/name,h)
for p in pv['pinChecks']:pin(ROOT/p['path'],p['expected'])
pin(P/'decisions.jsonl',pv['decisionsSha256']);pin(P/'findings.json',pv['findingsSha256']);pin(P/'recipe-findings.json',pv['recipeFindingsSha256'])
for row in pv['readInputs']:pin(ROOT/row['path'],row['sha256'])
for r in gate['batchReports']:
 pin(ROOT/r['path'],r['sha256']);pin(ROOT/r['sidecarPath'],r['sidecarSha256'])
manifest=load(C/'before-authored-files-manifest.json')
for f in manifest['files']:pin(ROOT/f['snapshotPath'],f['sha256'])
changed=[]
for f in after['files']:
 pin(ROOT/f['beforeSnapshotPath'],f['beforeSha256']);pin(ROOT/f['afterSnapshotPath'],f['afterSha256']);pin(ROOT/f['authoredPath'],f['afterSha256'])
 b=load(ROOT/f['beforeSnapshotPath']);a=load(ROOT/f['afterSnapshotPath']); assert set(b)==set(a);assert len(b['entries'])==len(a['entries'])
 for old,new in zip(b['entries'],a['entries']):
  assert old['id']==new['id'];o=dict(old);n=dict(new);ot=o.pop('target');nt=n.pop('target');assert o==n
  if ot!=nt:
   sid='string:444ff14f1967f5a4c8eb9e4cf4c913f1:'+str(new['id']);pr=next(x for x in plan['rows'] if x['stableId']==sid);assert ot==pr['currentTarget'] and nt==pr['acceptedFullTarget']; changed.append(sid)
 bb=dict(b);aa=dict(a);bb.pop('entries');aa.pop('entries');assert bb==aa
assert set(changed)=={r['stableId'] for r in plan['rows']} and len(changed)==19
current=jl(C/'closure-paired.jsonl');prior=jl(ROOT/'Translations/fil/semantic-correction-cycle-001.paired.jsonl');pending=jl(C/'pending-delta-paired.jsonl'); decisions=jl(P/'decisions.jsonl')
cm={r['stableId']:r for r in current};pm={r['stableId']:r for r in prior};dm={r['stableId']:r for r in decisions}
assert len(cm)==len(current)==7645 and len(pm)==len(prior)==len(dm)==7956
inv=jl(ROOT/'Source/localization-inventory-v3/strings.jsonl')+jl(ROOT/'Source/localization-inventory-v3/static-text.jsonl');sm={r['stableId']:r for r in inv}
G={'UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1'};tm={}
for r in gate['batchReports']:
 d=load(ROOT/r['path'])
 for e in d['entries']:
  sid=f"string:{G[d['collection']]}:{e['id']}";assert sid not in tm;tm[sid]=e['target']
for e in load(ROOT/'Translations/fil/static-text-draft.json')['entries']:assert e['stableId'] not in tm;tm[e['stableId']]=e['target']
assert len(tm)==16538
for r in current:
 s=sm[r['stableId']];assert r['source']==s['source'] and r['target']==tm[r['stableId']] and th(r['source'])==r['sourceSha256'] and th(r['target'])==r['targetSha256'];assert r['nodeNames']==s.get('nodeNames',[])
new=set(cm)-set(pm); retired=set(pm)-set(cm); invalid=set(closure['explicitlyInvalidatedPriorEvidence']['ids']);corrected=set(changed);delta=corrected|new|invalid;supp={r['stableId'] for r in plan['verifiedSupplementalIndependentReads']};fresh={r['stableId'] for r in pending}
assert len(new)==207 and len(retired)==518 and len(invalid)==60 and len(delta)==286 and len(supp)==20 and len(fresh)==266 and fresh==delta-supp
for r in closure['components']+[closure[x] for x in ['currentClosure','newCurrentMinusPrevious','retiredPreviousMinusCurrent','corrected','explicitlyInvalidatedPriorEvidence','exactNextDelta','supplementalIndependentReadsReused','pendingDistinctReviewerDelta']]:assert len(r['ids'])==r['count'] and ih(r['ids'])==r['idsSha256']
reused=set(cm)-delta
for sid in reused:
 a=cm[sid];b=pm[sid];d=dm[sid];assert a['source']==b['source'] and a['target']==b['target'] and a['nodeNames']==b['nodeNames'] and a['key']==b['key'];assert a['sourceSha256']==d['sourceSha256'] and a['targetSha256']==d['targetSha256'];assert d['findingId'] is None
sp={x['stableId']:x for x in load(P/'recipe-findings.json')['supplementalPairs']};suppchecks=[]
for r in plan['verifiedSupplementalIndependentReads']:
 sid=r['stableId'];a=cm[sid];b=sp[sid];assert r['sourceSha256']==a['sourceSha256'] and r['targetSha256']==a['targetSha256'];assert a['source']==b['source'] and a['target']==b['target'] and a['nodeNames']==b['nodeNames'] and a['key']==b['key'];suppchecks.append(dict(stableId=sid,sourceSha256=a['sourceSha256'],targetSha256=a['targetSha256'],nodeNames=a['nodeNames'],priorEvidence='Translations/fil/independent-review-01/recipe-findings.json',decision='applicable exact prior independent read'))
# Decode current source program independently using constants from actual shipped DLL.
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
raw=bytes(load(ROOT/'Source/glossary-corpus-v2/runtime-bindings.json')['sharedassets0.assets:2743']['compiledYarnProgram']);actual={}
for f,w,entry in wire(raw):
 if f!=constants['Program.NodesFieldNumber']:continue
 fs=wire(entry);name=next(v.decode() for f,w,v in fs if f==1);node=next(v for f,w,v in fs if f==2);ins=[];labels={}
 for f,w,v in wire(node):
  if f==constants['Node.InstructionsFieldNumber']:
   ff=wire(v);opcode=next((v for f,w,v in ff if f==constants['Instruction.OpcodeFieldNumber']),0);args=[operand(v) for f,w,v in ff if f==constants['Instruction.OperandsFieldNumber']];ins.append(dict(index=len(ins),opcode=opcode,op=ops[opcode],operands=args))
  elif f==3:
   ff=wire(v);labels[next(v.decode() for f,w,v in ff if f==1)]=next((v for f,w,v in ff if f==2),0)
 actual[name]=dict(labels=labels,instructions=ins)
ctx=load(C/'compiled-context-corrected.json');old=load(C/'compiled-context.json');err=load(C/'compiled-context-erratum.json');assert th(raw.hex())!=ctx['compiledProgramSha256'];assert hashlib.sha256(raw).hexdigest()==ctx['compiledProgramSha256']==err['compiledProgramSha256'];assert set(ctx['nodes'])==set(old['nodes']) and len(ctx['nodes'])==17
bykey={r['key']:r for r in inv if r.get('key')};nodes={};changedops=0
for name,rows in ctx['nodes'].items():
 a=actual[name];assert len(rows)==len(a['instructions'])==len(old['nodes'][name]); result=[]
 for c,o,i in zip(rows,old['nodes'][name],a['instructions']):
  assert all(c[k]==i[k] for k in ['index','opcode','op','operands']);assert all(c[k]==o[k] for k in ['index','operands','source','sourceStableId']);changedops+=int(c['opcode']!=o['opcode'])
  line=bykey.get(i['operands'][0]) if i['op'] in ['RunLine','AddOption'] else None
  assert c['source']==(line['source'] if line else None) and c['sourceStableId']==(line['stableId'] if line else None)
  item=dict(c);item['target']=tm.get(c['sourceStableId']);result.append(item)
 nodes[name]=dict(labels=a['labels'],instructions=result)
assert changedops==err['correctedOpcodeFields']==221
# Verify all old independently read branches against actual bytecode, not erratum assertion.
for p in pv['compiledContext']['inputs']:
 pin(ROOT/p['path'],p['sha256']);d=load(ROOT/p['path'])
 for name,node in d.items():assert node==actual[name],name
mandatory=set(next(x for x in closure['components'] if x['name']=='mandatoryRegression')['ids'])
result=dict(schemaVersion=1,reviewer='/root/fil_independent_review_02',cutoffUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pinChecks=checks,authoredUnits=16538,changedTargets=19,changedFiles=16,unexpectedAuthoredFieldChanges=0,closureUnits=7645,new=207,retired=518,corrected=19,explicitlyInvalidated=60,exactDelta=286,freshPairs=266,supplementalReused=20,priorUnchangedDecisionsReused=len(reused),mandatoryRegression=dict(total=len(mandatory),fresh=len(mandatory&fresh),supplemental=len(mandatory&supp),priorUnchanged=len(mandatory&reused)),compiledProgramSha256=hashlib.sha256(raw).hexdigest(),opcodeAssembly=dict(path=str(assembly),sha256=sha(assembly),constants=constants),compiledContext=dict(nodes=17,instructions=sum(len(x['instructions']) for x in nodes.values()),correctedOpcodeFields=changedops,priorReadNodesVerified=82,priorReadInstructionsVerified=1194),supplementalChecks=suppchecks,limits=['Static admissibility is not live scheduling','No game, layout, glyph, package or runtime execution','Inventory-only repeats have no proven compiled reachability'])
for name,data in [('input-verification.json',result),('independent-compiled-context.json',dict(compiledProgramSha256=hashlib.sha256(raw).hexdigest(),nodes=nodes))]:
 path=OUT/name;assert not path.exists();path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['pinChecks','opcodeAssembly','supplementalChecks']},ensure_ascii=False,indent=2))
