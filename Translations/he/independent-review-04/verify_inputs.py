#!/usr/bin/env python3
"""Independent cycle-04 verification; all new output stays in this review."""
import hashlib, json, pathlib, re, runpy, struct, sys
sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
C = ROOT/'Translations/he/semantic-correction-cycle-04'
P = ROOT/'Translations/he/semantic-correction-cycle-03'
IR3 = ROOT/'Translations/he/independent-review-03'
sys.path.insert(0, str(ROOT/'Scripts'))
from preserve_exact import check_value
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def shat(s): return hashlib.sha256(s.encode()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(n,d):
    p=OUT/n; b=(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()
    assert not p.exists() or p.read_bytes()==b,p
    if not p.exists():p.write_bytes(b)
checks=[]
def pin(p,h,kind):
    p=pathlib.Path(p);p=p if p.is_absolute() else ROOT/p
    a=sha(p);checks.append(dict(path=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),expectedSha256=h,actualSha256=a,kind=kind,passed=a==h))
    assert a==h,(p,h,a)
def refs(d,kind):
    if isinstance(d,dict):
        if 'path' in d and 'sha256' in d:pin(d['path'],d['sha256'],kind)
        for v in d.values():refs(v,kind)
    elif isinstance(d,list):
        for v in d:refs(v,kind)
H=read(C/'independent-review-handoff.json');M=read(C/'closure-manifest.json');T=read(C/'full-structural-diff.json')
for d,k in [(read(C/'review-handoff-index.json'),'index'),(H,'handoff'),(M,'closure'),(T,'structural'),(read(C/'final-gate.json'),'final-gate'),(read(C/'final-evidence-manifest.json'),'author-manifest'),(read(IR3/'final-evidence-manifest.json'),'prior-independent-manifest')]:refs(d,k)
pin(C/'close.py',M['selectorScriptSha256'],'recipe');pin(C/'workflow.py',M['workflowScriptSha256'],'recipe');pin(C/'input-pins.json',M['inputPinsSha256'],'recipe-input')
pin(ROOT/'Translations/he/semantic-review-progress.json',sha(ROOT/'Translations/he/semantic-review-progress.json'),'checkpoint')
previous=read(IR3/'final-input-verification.json')
refs(previous['approvedGlossaryAcceptanceChecks'],'approved-glossary-acceptance')
refs(previous['sourceGlossary'],'source-glossary')
pin(previous['sourceGlossary']['masterPath'],previous['sourceGlossary']['masterSha256'],'canonical-source-glossary')
pin(ROOT/'Documentation/glossary-translations/canonical-reviews/he.json',sha(ROOT/'Documentation/glossary-translations/canonical-reviews/he.json'),'approved-glossary-evidence')
R=read(ROOT/'Source/preserve-exactly-v4.json');order=[r['stableId'] for r in R['tableRows']+R['staticRows']];rules={r['stableId']:r for r in R['tableRows']+R['staticRows']}
assert len(order)==len(rules)==16538
S={r['stableId']:r for n in ['strings','static-text'] for r in map(json.loads,(ROOT/f'Source/localization-inventory-v3/{n}.jsonl').open())}
A={};loc={};guid={'UI':'0cbd8a7a4f543344bb95659de87f67a5','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'}
for f in T['authoredFiles']:
    d=read(ROOT/f['path'])
    for i,r in enumerate(d['entries']):
        sid=r.get('stableId') or f"string:{guid[d['collection']]}:{r['id']}"
        assert sid not in A;A[sid]=r['target'];loc[sid]=dict(path=f['path'],offset=i,authoredFileSha256=f['sha256'])
assert set(A)==set(rules)
for sid in A:check_value(rules[sid],A[sid])
assert shat(''.join(x['path']+'\t'+x['sha256']+'\n' for x in T['authoredFiles']))==T['authoredFileSetSha256']
assert shat(''.join(x['path']+'\t'+x['sha256']+'\n' for x in T['sidecars']))==T['sidecarFileSetSha256']
rows=list(map(json.loads,(C/'review-rows.jsonl').open()));delta=list(map(json.loads,(C/'delta-review-rows.jsonl').open()))
names=['changedIds','previousClosureIds','closureIds','newClosureIds','explicitlyInvalidatedIds','retiredIds','deltaIds']
lists={n:(ROOT/M[n]['path']).read_text().splitlines() for n in names}
for n,ids in lists.items():
    ss=set(ids);assert len(ids)==len(ss)==M[n]['count'];assert ids==[sid for sid in order if sid in ss]
    assert (ROOT/M[n]['path']).read_bytes()==(('\n'.join(ids)+'\n').encode() if ids else b'')
changed,old,current,new,invalid,retired,ds=(set(lists[n]) for n in names)
assert new==current-old and retired==old-current and not retired and ds==changed|new|invalid and invalid<=old
assert len(changed&new)==4 and not changed&invalid and not new&invalid
assert [r['stableId'] for r in rows]==lists['closureIds'] and [r['stableId'] for r in delta]==lists['deltaIds']
assert delta==[r for r in rows if r['reviewDelta']]
for r in rows:assert r['source']==S[r['stableId']]['source'] and r['after']==A[r['stableId']] and r['nodeNames']==S[r['stableId']].get('nodeNames',[])
components={n:set((ROOT/d['path']).read_text().splitlines()) for n,d in M['components'].items()}
assert set.union(*components.values())==current and old<=current and len(current)==2407
for r in rows:assert r['components']==sorted(n for n,ids in components.items() if r['stableId'] in ids)
prior={r['stableId']:r for r in map(json.loads,(P/'review-rows.jsonl').open())}
assert {sid for sid in old if prior[sid]['after']!=A[sid]}==changed&old
decisions={};origins={}
for i in [1,2,3]:
    p=ROOT/f'Translations/he/independent-review-{i:02d}/complete-review-decisions.json'
    pin(p,sha(p),'prior-independent-decisions')
    for d in read(p)['decisions']:decisions[d['stableId']]=d;origins[d['stableId']]=str(p.relative_to(ROOT))
reg=components['mandatory-regressions'];assert len(reg)==549
reuse=[]
for sid in [sid for sid in order if sid in reg-ds]:
    d=decisions[sid];assert d['findingId'] is None and d['sourceValueSha256']==shat(S[sid]['source']) and d['currentTargetValueSha256']==shat(A[sid])
    assert d['nodeNames']==S[sid].get('nodeNames',[])
    reuse.append(dict(stableId=sid,priorDecisionPath=origins[sid],priorDecisionFileSha256=sha(ROOT/origins[sid]),sourceValueSha256=shat(S[sid]['source']),currentTargetValueSha256=shat(A[sid]),decision=d['decision'],applicability='Exact source/target, glossary, compiled program and actual consumer assembly pins unchanged; independent prior decision, no author-read credit.'))
outputs=[];recipe=runpy.run_path(str(C/'close.py'))
def compare_only(p,data):
    assert p.is_file() and p.read_bytes()==data,p
    outputs.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=len(data)))
recipe['main'].__globals__['once']=compare_only;recipe['main']()
def var(b,i):
    n=shift=0
    while True:
        c=b[i];i+=1;n|=(c&127)<<shift
        if c<128:return n,i
        shift+=7
def wire(b):
    i=0;out=[]
    while i<len(b):
        key,i=var(b,i);f,w=key>>3,key&7
        if w==0:v,i=var(b,i)
        elif w==2:l,i=var(b,i);v=b[i:i+l];i+=l
        elif w==5:v=struct.unpack('<f',b[i:i+4])[0];i+=4
        elif w==1:v=b[i:i+8];i+=8
        else:raise ValueError(w)
        out.append((f,w,v))
    return out
fmt=read(IR3/'compiled-scene-context.json');binding=ROOT/'Source/glossary-corpus-v2/runtime-bindings.json';pin(binding,fmt['runtimeBindingsSha256'],'actual-runtime-bindings')
program=bytes(read(binding)['sharedassets0.assets:2743']['compiledYarnProgram']);assert hashlib.sha256(program).hexdigest()==fmt['compiledProgramSha256']
nodes={}
for f,w,v in wire(program):
    if f!=2:continue
    ent=wire(v);key=[v.decode() for f,w,v in ent if f==1][0];node=[v for f,w,v in ent if f==2][0];ins=[]
    for f,w,v in wire(node):
        if f!=2:continue
        op=0;args=[]
        for a,z,b in wire(v):
            if a==1:op=b
            elif a==2:args.append(next((q.decode() if t==2 else q for a,t,q in wire(b) if a in [1,2,3]),None))
        ins.append(dict(opcode=op,operands=args))
    nodes[key]=ins
wanted={n for r in delta for n in r['nodeNames']};assert wanted<=set(nodes)
for name in ['compiled-scene-context.json','additional-compiled-scene-context.json']:
    for n,ins in read(IR3/name)['nodes'].items():assert ins==nodes[n]
save('compiled-scene-context.json',dict(compiledProgramSha256=fmt['compiledProgramSha256'],runtimeBindingsSha256=fmt['runtimeBindingsSha256'],nodes={n:nodes[n] for n in sorted(wanted)},opcodes='2 RunLine, 3 RunCommand, 4 AddOption; complete branches retained',runtime='not-run'))
bykey={r.get('key'):r['stableId'] for r in S.values() if r.get('key')}
for r in read(C/'compiled-consumer-preflight.json')['nodes']:
    assert r['afterDisplayed']==A[r['stableId']]
    for n in r['nodes']:
        ins=nodes[n['node']][n['operationIndex']]
        assert ins['opcode']==n['opcode'] and ins['operands'][0]==n['key']
IR1=ROOT/'Translations/he/independent-review-01'
domain=read(IR1/'character-consumer-domain.json');pin(domain['sourcePath'],domain['sourceSha256'],'resident-asset')
for n in ['item-binding-verified.json','dynamic-consumer-il-02.json','place-and-item-binding-il.json']:
    j=read(IR1/n);pin(j.get('sourcePath',j.get('assemblyPath')),j.get('sourceSha256',j.get('assemblySha256')),'consumer-assembly')
characters={x['name']:x for x in domain['characters']}
branches=read(IR3/'consumer-verification.json')['branches']
for b in branches:
    ids=[bykey[x['operands'][0]] for x in nodes[b['node']] if x['opcode']==2 and x['operands'][0] in bykey]
    assert ids==b['sourceLineIdsInCompiledOrder']
    place=characters[b['caller']]['place'];residents=[n for n in domain['placeDomains'][str(place)] if n!=b['caller']]
    assert place==b['place'] and residents==b['residentAlternatives']
    for v in b['assembled']:
        labelid=bykey['characterName_'+v['resident']];label=A[labelid]
        assert v['labelId']==labelid and v['label']==label
        assert v['displayInCompiledOrder']==[A[sid].replace('{0}',label) for sid in ids]
assert not any(s.get('key')=='characterName_Twins' for s in S.values())
ledger=read(C/'bald-voice-roster-ledger.json')['rows']
roster=[sid for sid in order if S[sid]['source'].startswith('Bald: ')]
assert [r['stableId'] for r in ledger]==roster and len(roster)==132
for r in ledger:
    assert r['source']==S[r['stableId']]['source'] and r['sourceSha256']==shat(r['source']) and r['targetBeforeSha256']==shat(r['targetBefore'])
assert {r['stableId'] for r in ledger if r['dependencySelected']}==components['bald-source-voice-risk']
assert len(components['bald-source-voice-risk'])==39 and len(components['selector-regression-controls'])==8
assert components['selector-regression-controls']<=components['bald-source-voice-risk'] and components['selector-regression-controls']<=ds
save('consumer-verification.json',dict(schemaVersion=1,status='passed static compiled/domain/assembly verification',branches=branches,assembledVariants=sum(len(b['assembled']) for b in branches),deltaCompiledNodes=len(wanted),closureRecipeReproducedOutputs=outputs,unresolved='characterName_Twins exact accepted UI key absent; runtime fallback unverified',runtime='not-run',bidi='logical authored Hebrew only; display unverified'))
save('regression-reuse.json',dict(schemaVersion=1,catalogSha256=M['components']['mandatory-regressions']['sha256'],catalogCount=len(reg),newReads=[sid for sid in order if sid in reg&ds],reusedDecisions=reuse,reusedCount=len(reuse),runtime='not-run',visual='not-run'))
save('current-row-locations.json',{r['stableId']:loc[r['stableId']] for r in delta})
save('input-verification.json',dict(schemaVersion=1,status='passed',hashChecks=checks,hashChecksCount=len(checks),acceptedAuthoredUnits=len(A),sourceCurrentAlignmentRows=len(rows),componentUnionVerified=True,canonicalOrderVerified=True,counts={n:len(v) for n,v in lists.items()},intersections=dict(correctedAndNew=len(changed&new),correctedAndInvalidated=len(changed&invalid),newAndInvalidated=len(new&invalid)),deltaArithmetic='14 + 25 + 37 - 4 = 72',compiledNodes=len(wanted),mandatoryRegressions=len(reg),regressionNewReads=len(reg&ds),regressionReusedUnchanged=len(reg-ds),protectedRowsChecked=len(A),closureRecipeReproducedOutputs=len(outputs),authoredFileSetSha256=T['authoredFileSetSha256']))
print(json.dumps(dict(hashChecks=len(checks),delta=len(delta),regressionRead=len(reg&ds),regressionReused=len(reg-ds),compiledNodes=len(wanted),recipeOutputs=len(outputs))))
