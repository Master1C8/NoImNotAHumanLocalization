"""Read-only independent review adapter; writes only this evidence directory."""
import json, hashlib, importlib.util, struct, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
CYCLE=ROOT/'Translations/sw/semantic-correction-cycle-02'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p): return [json.loads(x) for x in p.read_text().splitlines()]
def save(name,obj): (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
delta=rows(CYCLE/'review-delta-v3.jsonl')
allrows=rows(CYCLE/'after-targets.jsonl')
targets={r['stableId']:r['target'] for r in allrows}
source={r['stableId']:r for p in ('strings.jsonl','static-text.jsonl') for r in rows(ROOT/'Source/localization-inventory-v3'/p)}
keyrows={r['key']:dict(r,target=targets.get(r['stableId'])) for r in source.values() if r.get('collection')=='Dialogs'}
spec=importlib.util.spec_from_file_location('decoder',ROOT/'Translations/sw/independent-review-01/read_compiled_context.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
def operand(data):
    fields=list(d.fields(data));assert len(fields)==1
    f,w,v=fields[0]
    if (f,w)==(1,2):return v.decode('utf-8')
    if (f,w)==(2,0):return bool(v)
    if (f,w)==(3,5):return struct.unpack('<f',v)[0]
    raise ValueError(fields)
d.operand=operand
nodes,program_hash=d.load()
consumers={}
for n,ins in nodes.items():
    for i in ins:
        if i['opcode'] in (2,4) and i['operands'] and i['operands'][0] in keyrows:
            consumers.setdefault(i['operands'][0],[]).append((n,i['index'],i['operands'][1:]))

if __name__=='__main__':
    if sys.argv[1]=='context-rest':
        extra=[(n['nodeName'],s) for n in rows(HERE/'compiled-context-reviewed-02.jsonl') for s in n['orderedVisibleSlots'] if s['readMode'].startswith('not independently')]
        a,b=map(int,sys.argv[2:4])
        for j,(name,s) in enumerate(extra[a:b],a):
            print(j,name,s['instructionIndex'],s['key'])
            print('RU',s['source']);print('SW',s['assembledCurrentTarget'])
    elif sys.argv[1]=='context':
        names=list(dict.fromkeys(n for row in delta for n,_,_ in consumers.get(row['key'],[])))
        a,b=map(int,sys.argv[2:4]); selectedkeys={x['key'] for x in delta}
        for n in names[a:b]:
            ins=nodes[n];visible=[i for i in ins if i['opcode'] in (2,4) and i['operands'] and i['operands'][0] in keyrows]
            pos=[j for j,i in enumerate(visible) if i['operands'][0] in selectedkeys]
            needed={j for p in pos for j in range(max(0,p-1),min(len(visible),p+2))}
            print('NODE',n,'visible-order',[(i['index'],next((j for j,x in enumerate(delta) if x['key']==i['operands'][0]),'context')) for i in visible])
            for j in sorted(needed):
                i=visible[j];key=i['operands'][0]
                if key not in selectedkeys:
                    r=keyrows[key];print('CONTEXT',i['index'],key);print('RU',r['source']);print('SW',r['target'])
            control=[]
            for i in ins:
                args=i['operands'];op=i['opcode']
                if op in (13,14) and args and str(args[0]).startswith('$Yarn.Internal.Visiting.'):continue
                if op==12 and args and args[0] in ('visited','Number.Add'):continue
                if op in (3,6,10,12,13,14,16) or op==4:control.append([i['index'],op,args])
            print('CONTROL',json.dumps(control,ensure_ascii=False,separators=(',',':')))
    elif sys.argv[1]=='read':
        a,b=map(int,sys.argv[2:4])
        for x,r in enumerate(delta[a:b],a):
            print(f"{x} {r['stableId'].rsplit(':',1)[-1]} {r['key']} [{','.join(r['reasons'])}] {consumers.get(r['key'],[])}")
            print('RU '+r['source']);print('SW '+r['target'])
    elif sys.argv[1]=='node':
        for n in sys.argv[2:]:
            print('NODE',n)
            for i in nodes[n]:
                args=i['operands'];op=i['opcode']
                if op in (2,4) and args and args[0] in keyrows:
                    r=keyrows[args[0]];print(i['index'], 'OPTION' if op==4 else 'LINE', r['key'], args[1:]);print('RU',r['source']);print('SW',r['target'])
                elif not(op in (13,14) and args and str(args[0]).startswith('$Yarn.Internal.Visiting.')) and not(op==12 and args and args[0] in ('visited','Number.Add')):
                    print(i['index'],'OP',op,args)
    elif sys.argv[1]=='verify':
        checks=[]
        def checkref(ref):
            if isinstance(ref,dict):
                if 'path' in ref and 'sha256' in ref:
                    p=Path(ref['path']);p=p if p.is_absolute() else ROOT/p
                    assert sha(p)==ref['sha256'],str(p)
                    checks.append({'path':str(p),'sha256':sha(p)})
                for k,v in ref.items():
                    if k!='priorCorrectionProgress':checkref(v)
            elif isinstance(ref,list):
                for v in ref:checkref(v)
        closure=json.loads((CYCLE/'dependency-closure-v3.json').read_text());checkref(closure)
        checkref(json.loads((CYCLE/'inputs.json').read_text()))
        previous=json.loads((ROOT/'Translations/sw/independent-review-01/evidence-manifest-01.json').read_text());checkref(previous)
        applicability=json.loads((ROOT/'outputs/yarn-operand-applicability-v1.json').read_text())
        for p,h in applicability['recipeHashes'].items():assert sha(ROOT/p)==h
        assert applicability['compiledProgramSha256']==program_hash
        explicit=nodes
        def wireoperand(data):
            f,w,v=list(d.fields(data))[0]
            if w==2:return v.decode()
            if w==0:return bool(v)
            if w==5:return struct.unpack('<f',v)[0]
            raise ValueError(w)
        d.operand=wireoperand
        patched,_=d.load();assert explicit==patched
        def ids(name):return {r['stableId'] for r in rows(CYCLE/name)}
        old={r['stableId'] for r in rows(ROOT/closure['priorClosure']['path'])};current=ids('closure-ids-v3.jsonl');changed=ids('changed-ids-v3.jsonl');new=ids('new-ids-v3.jsonl');invalid=ids('invalidated-ids-v3.jsonl');retired=ids('retired-ids-v3.jsonl')
        assert new==current-old and retired==old-current and ids('review-delta-v3.jsonl')==changed|new|invalid
        manifest=json.loads((CYCLE/'final-payload-manifest.json').read_text())
        for r in manifest['artifacts']:
            for pk,hk in [('artifact','artifactSha256'),('sidecar','sidecarSha256')]:checkref({'path':r[pk],'sha256':r[hk]})
        for r in delta:assert r['source']==source[r['stableId']]['source'] and r['target']==targets[r['stableId']]
        save('input-verification-01.json',{'reviewer':'/root/sw_independent_review_02','hashChecks':checks,'sets':{'prior':len(old),'current':len(current),'corrected':len(changed),'new':len(new),'invalidated':len(invalid),'retired':len(retired),'delta':len(delta),'overlapCount':len(changed)+len(new)+len(invalid)-len(delta)},'selectorReproduction':'authoritative v3 recipe passed against existing immutable outputs','explicitOperandSchema':{'1:2':'string','2:0':'bool','3:5':'float'},'decodedEquality':{'nodes':len(nodes),'instructions':sum(map(len,nodes.values())),'result':'passed'},'applicabilityReport':{'path':'outputs/yarn-operand-applicability-v1.json','sha256':sha(ROOT/'outputs/yarn-operand-applicability-v1.json')},'programSha256':program_hash})
        print('Verified',len(checks),'pins; exact sets',len(delta),'nodes',len(nodes),'instructions',sum(map(len,nodes.values())))
