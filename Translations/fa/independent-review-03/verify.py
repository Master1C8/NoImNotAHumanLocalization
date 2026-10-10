"""Read-only independent cycle003 verification; writes new reviewer evidence only."""
import contextlib, hashlib, importlib.util, io, json, pathlib, re, subprocess, sys
R=pathlib.Path(__file__).resolve().parents[3]; O=pathlib.Path(__file__).parent
FA=R/'Translations/fa'; C=FA/'audit-cycle-003'; P=FA/'audit-cycle-002'; Q=FA/'independent-review-02'; A=FA/'independent-review-01'
def read(p): return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def pair(r,sorted_keys=False):return hashlib.sha256(json.dumps({k:r[k] for k in ['stableId','source','target']},ensure_ascii=False,sort_keys=sorted_keys,separators=(',',':')).encode()).hexdigest()
def put(name,obj):
 data=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode();p=O/name
 if p.exists():assert p.read_bytes()==data,str(p)
 else:p.write_bytes(data)
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
pins={}
for base in [C,Q,A]:
 index=read(base/'evidence-index.json')
 for n,h in index['files'].items():
  p=R/n if n.startswith('Translations/') else base/n
  assert sha(p)==h,(base,n)
  pins[str(p.relative_to(R))]=h
 pins[str((base/'evidence-index.json').relative_to(R))]=sha(base/'evidence-index.json')
oldpins=read(Q/'review-verdict.json')['pins'];before=C/'before/dialogue-batch-348.json'
for n,h in oldpins.items():
 p=before if n=='Translations/fa/dialogue-batch-348.json' else R/n
 assert sha(p)==h,n
 pins[str(p.relative_to(R))]=h
for n,h in read(C/'deterministic-gate.json')['authoredFileHashes'].items():assert sha(R/n)==h; pins[n]=h
m=load('cycle003',C/'cycle.py')
def readonly(path,data):assert path.exists() and path.read_bytes()==data,str(path)
m.write_once=readonly
original_corpus=m.corpus
verified_corpus=[]
def capture_corpus():
 result=original_corpus();verified_corpus.append(result);return result
m.corpus=capture_corpus
buf=io.StringIO()
with contextlib.redirect_stdout(buf):m.closure()
reproduced=json.loads(buf.getvalue())
assert len(verified_corpus)==1
order,source,target,location,files,rules=verified_corpus[0]
cl=read(C/'closure.json');delta=read(C/'next-review-delta.json');prev=read(P/'closure.json')
def ids(base,n):
 p=base/(n+'-ids.txt');data=p.read_bytes();vals=data.decode().splitlines()
 assert data==''.join(x+'\n' for x in vals).encode() and len(vals)==len(set(vals))
 assert vals==[s for s in order if s in set(vals)]
 return set(vals)
components={n:ids(C,n) for n in cl['componentHashes']}
for n,v in components.items():assert cl['componentHashes'][n]=={'count':len(v),'sha256':sha(C/(n+'-ids.txt'))}
old=ids(P,'closure');current=components['closure'];changed=components['changed'];new=components['newlySelected'];invalid=components['invalidatedPrior'];retired=components['retiredPrior'];D=components['nextReviewDelta']
assert current==set().union(*(components[n] for n in ['changed','context','repetition','glossaryReferent','runtimeBinding','mandatoryRegression','contextWatchlist']))
assert new==current-old and retired==old-current and D==changed|new|invalid
assert invalid=={s for s in old if location[s]=='Translations/fa/dialogue-batch-348.json'}
assert len(old)==2701 and len(current)==946 and len(new)==2 and len(retired)==1757 and len(invalid)==16 and len(D)==18
beforedata=read(before);afterdata=read(C/'after/dialogue-batch-348.json');live=FA/'dialogue-batch-348.json'
assert live.read_bytes()==(C/'after/dialogue-batch-348.json').read_bytes()
assert {k:v for k,v in beforedata.items() if k!='entries'}=={k:v for k,v in afterdata.items() if k!='entries'}
diffs=[]
for a,b in zip(beforedata['entries'],afterdata['entries']):
 assert {k:v for k,v in a.items() if k!='target'}=={k:v for k,v in b.items() if k!='target'}
 if a!=b:diffs.append((a,b))
assert len(beforedata['entries'])==len(afterdata['entries'])==21 and len(diffs)==1
plan=read(C/'correction-plan.json')['rows'][0]
assert diffs[0][0]['target']==plan['before'] and diffs[0][1]['target']==plan['acceptedTarget']
assert plan['before'].replace('خاله‌ام','عمه یا خاله‌ام')==plan['acceptedTarget']
top=load('topology002',P/'verify-photo-topology.py');raw=bytes(read(R/'Source/glossary-corpus-v1/sharedassets0.assets-2743.json')['compiledYarnProgram']);nodes={}
for n,_,v in top.fields(raw):
 if n!=2:continue
 e=list(top.fields(v));name=next(x.decode() for k,_,x in e if k==1);node=next(x for k,_,x in e if k==2);instructions=[];labels={}
 for k,_,x in top.fields(node):
  if k==2:
   f=list(top.fields(x));ops=[]
   for a,_,b in f:
    if a==2:ops.append({str(aa):bb.decode() if isinstance(bb,bytes) else bb for aa,_,bb in top.fields(b)})
   instructions.append({'index':len(instructions),'opcode':next((b for a,_,b in f if a==1),0),'operands':ops})
  elif k==3:
   f=list(top.fields(x));labels[next(b.decode() for a,_,b in f if a==1)]=next((b for a,_,b in f if a==2),0)
 nodes[name]={'instructions':instructions,'labels':labels,'rawSha256':hashlib.sha256(node).hexdigest()}
assert hashlib.sha256(raw).hexdigest()==cl['compiledYarnProgramSha256']
priornodes=read(Q/'compiled-context.json')['nodes'];assert all(nodes[n]==v for n,v in priornodes.items())
delta_by={r['stableId']:r for r in delta['rows']}; assert set(delta_by)==D
context_names=set(read(C/'selector-spec.json')['contextNodeNames'])|{n for s in D for n in source[s].get('nodeNames',[])}
keys={r.get('key'):s for s,r in source.items() if r.get('key')};sites={};sequence=[]
for n in sorted(context_names):
 for ins in nodes[n]['instructions']:
  if ins['opcode'] in [2,4] and ins['operands']:
   key=ins['operands'][0].get('1')
   if key in keys:
    s=keys[key];site={'node':n,'instruction':ins['index'],'opcode':ins['opcode']};sites.setdefault(s,[]).append(site)
    sequence.append({**site,'stableId':s,'key':key,'source':source[s]['source'],'target':target[s]})
reg=components['mandatoryRegression'];old1={r['stableId']:r for r in read(A/'per-id-review.json')['reviewRows']};old2={r['stableId']:r for r in read(Q/'per-id-review.json')['reviewRows']}
reuse=[]; retiredrows=[]
for s in sorted(reg|retired|components['contextWatchlist'],key=order.index):
 prior=old2.get(s,old1.get(s)); assert prior is not None,s
 assert prior['source']==source[s]['source'] and prior['target']==target[s],s
 assert prior['fullPairSha256']==pair(prior,sorted_keys=s not in old2) and prior.get('findingId') is None,s
 if prior.get('nodeNames') is not None:assert prior['nodeNames']==source[s].get('nodeNames',[]),s
 row={'stableId':s,'fullPairSha256':pair(prior),'priorFullPairSha256':prior['fullPairSha256'],'priorPairEncoding':'stableId,source,target order' if s in old2 else 'sorted keys: source,stableId,target','priorReview':str((Q if s in old2 else A).relative_to(R))+'/per-id-review.json','priorOutcome':prior['outcome'],'sourceTargetSceneUnchanged':True,'consumerEvidence':'compiled program, managed/static fixtures and assembly/substitution pins verified unchanged'}
 if s in reg:reuse.append(row)
 if s in retired:retiredrows.append(row)
fixture={}
for name in ['managed-context-v2.json','static-context.json','static-buttons.json','resident-inputs-v2.json']:
 e=read(A/name);key='assemblyPath' if 'assemblyPath' in e else 'sourceAsset';pin='assemblySha256' if 'assemblySha256' in e else 'sourceSha256';p=pathlib.Path(e[key]);assert sha(p)==e[pin];fixture[e[key]]=e[pin]
assembled=read(A/'assembled-consumers.json');assert all(sha(A/n)==h for n,h in assembled['pins'].items())
outputs=0
for consumer in assembled['consumers']:
 for row in consumer['samePlaceOtherCharacters']:
  assert target[row['runtimeUiStableId']]==row['persianValue']
  assert target[consumer['stableId']].replace('{0}',row['persianValue'])==row['assembledPersian'];outputs+=1
assert len(reg)==len(reuse)==544 and len(retiredrows)==1757
put('compiled-context.json',{'compiledSha256':hashlib.sha256(raw).hexdigest(),'nodes':{n:nodes[n] for n in sorted(context_names)},'displaySequence':sequence,'limits':'Static compiled order and branch facts only; no live reachability or rendering claim.'})
put('full-read-inputs.json',{'rows':[{**r,'nodeNames':source[r['stableId']].get('nodeNames',[]),'compiledInstructionSites':sites.get(r['stableId'],[])} for r in delta['rows']]})
put('catalog-reuse.json',{'count':544,'idSha256':sha(C/'mandatoryRegression-ids.txt'),'freshDeltaCatalogReads':len(reg&D),'exactUnchangedPriorDecisionReuse':len(reg-D),'rows':reuse,'sceneProgramSha256':cl['compiledYarnProgramSha256'],'fixtureSourceHashes':fixture,'assembledConsumerTemplates':len(assembled['consumers']),'admittedDynamicOutputs':outputs,'logicalResult':'clean exact applicable independent decisions retained','renderedResult':'not-run'})
put('retired-accounting.json',{'count':1757,'idSha256':sha(C/'retiredPrior-ids.txt'),'allRetiredRowsVerifiedUnchangedAndIndependentlyReviewed':True,'reason':cl['retiredReason'],'rows':retiredrows})
spec=read(C/'selector-spec.json');sourcehits={s for s in order if re.search(spec['sourceAuntPattern'],source[s]['source'],re.I)};targethits={s for s in order if any(t in target[s] for t in spec['targetAuntFragments'])}
assert sourcehits==targethits==changed
assert not re.search(spec['sourceAuntPattern'],'лететь',re.I)
assert all(re.search(spec['sourceAuntPattern'],s,re.I) for s in ['тётка','тетки','тётки','тёткой','тётке','тётку','тёток','тётя','тётю','тётей','тётями','тетя'])
table=0;batches=0
for f in files:
 if f.name=='static-text-draft.json':continue
 b=read(f);v=read(f.with_suffix('.validation.json'));assert v['batchSha256']==sha(f) and v['structuralResult']=='passed' and v['authoredRows']==len(b['entries']);table+=len(b['entries']);batches+=1
static=read(FA/'static-text-draft.json')['entries'];phrase=read(FA/'static-phrase-map.json')['phrases'];mapping={r['source']:r['target'] for r in phrase};assert len(mapping)==len(phrase)
mapped=[e for e in static if source[e['stableId']]['source'] in mapping];assert len(mapped)==177 and all(e['target']==mapping[source[e['stableId']]['source']] for e in mapped)
credits=read(FA/'credits-role-map.json')['replacements'];cm={r['source']:r['target'] for r in credits};assert len(cm)==len(credits)==81
pattern=re.compile('|'.join(re.escape(s) for s in sorted(cm,key=len,reverse=True)));credit='tmp:level5:59:m_text';assert pattern.sub(lambda x:cm[x[0]],source[credit]['source'])==target[credit]
common=read(FA/'common-options-001.authored.json')['phrases'];selected=[]
for r in common:
 selectedids=[s for s in order if source[s].get('collection')=='Dialogs' and source[s]['source']==r['source']];assert len(selectedids)==r['expectedRows'] and all(target[s]==r['target'] for s in selectedids);selected+=selectedids
assert len(selected)==len(set(selected))==2841
for n in ['Source/glossary-corpus-v1/sharedassets0.assets-2743.json','Documentation/glossary-research/final-v1/glossary.json','Documentation/glossary-translations/fa/layer.json','Scripts/report_locale_readiness.py','Scripts/expand_exact_text_batch.py','Scripts/preserve_exact.py']:
 pins[n]=sha(R/n)
checks={}
for name,args in [('full-exact-readiness',['Scripts/report_locale_readiness.py','--exact','--compact']),('repeat-expansion',['Scripts/expand_exact_text_batch.py','--verify','Translations/fa/common-options-001.authored.json','Translations/fa/dialogue-batch-001.json'])]:
 cp=subprocess.run([str(R/'.venv/bin/python'),*args],cwd=R,capture_output=True,text=True);assert cp.returncode==0,(name,cp.stderr)
 checks[name]={'command':'.venv/bin/python '+' '.join(args),'returnCode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr}
 if name=='full-exact-readiness':assert 'fa  16538/16538' in cp.stdout and next(l for l in cp.stdout.splitlines() if l.startswith('fa ')).endswith('problems=0')
assert all(sha(R/n)==h for n,h in pins.items())
put('verification.json',{'cycleReproduction':reproduced,'reproductionWritePolicy':'cycle.write_once replaced by assertion of existing exact bytes; normal closure function and all selectors executed unchanged','componentArithmetic':{'previous':2701,'current':946,'intersection':len(old&current),'new':2,'retired':1757,'corrected':1,'explicitInvalidated':16,'correctedInvalidatedOverlap':len(changed&invalid),'exactDelta':18},'fullAcceptedStructuralAndPreserveExact':16538,'authoredSidecars':batches,'tableRows':table,'staticRows':len(static),'staticRecipeMatchedRows':len(mapped),'creditsRoles':81,'commonExpansionRows':2841,'auntSourceIds':list(sourcehits),'auntTargetIds':list(targethits),'sourceInflectionTests':12,'letetFalsePositiveExcluded':True,'oneAuthoredFullReplacementVerified':True,'managedStaticConsumerPinsUnchanged':True,'checks':checks,'pins':pins,'inputsUnchangedAtFinish':True})
print(json.dumps({'closure':len(current),'delta':len(D),'mandatory':len(reg),'retired':len(retired),'contextNodes':len(context_names),'contextDisplayUnits':len(sequence),'structure':len(order),'sidecars':batches,'regressionFreshDelta':len(reg&D)},ensure_ascii=False))
