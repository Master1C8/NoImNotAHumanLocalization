import json,hashlib,struct
from pathlib import Path
R=Path(__file__).resolve().parents[3];H=R/'Translations/hi';D=Path(__file__).parent
def j(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,d):
 p=D/n;assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
ns={'__file__':str(H/'build-semantic-cycle-001-closure.py'),'__name__':'evidence_import'};exec(compile((H/'build-semantic-cycle-001-closure.py').read_text(),str(H/'build-semantic-cycle-001-closure.py'),'exec'),ns);f=ns['fields']
blob=bytes(j(R/'Source/glossary-corpus-v2/runtime-bindings.json')['sharedassets0.assets:2743']['compiledYarnProgram']);nodes={}
for num,wire,v in f(blob):
 if (num,wire)!=(2,2):continue
 parts=list(f(v));name=parts[0][2].decode();raw=parts[1][2];ins=[];labels=[]
 for n,w,v in f(raw):
  if (n,w)==(2,2):
   opcode=0;args=[]
   for nn,ww,vv in f(v):
    if (nn,ww)==(1,0):opcode=vv
    elif (nn,ww)==(2,2):
     vals=list(f(vv));args.append([{'field':a,'wire':b,'value':c if b==0 else struct.unpack('<f',c)[0] if (a,b)==(3,5) else c.decode('utf-8','backslashreplace')} for a,b,c in vals])
   ins.append({'index':len(ins),'opcode':opcode,'operands':args})
  elif (n,w)==(3,2):
   labels.append([{'field':a,'wire':b,'value':c if b==0 else c.decode('utf-8','backslashreplace')} for a,b,c in f(v)])
 nodes[name]={'instructions':ins,'labels':labels}
c=j(H/'semantic-cycle-001-closure.json');a=j(H/'semantic-cycle-001-adjudication.json');changedkeys={x['source'] for x in a['items']}
sources=[json.loads(l) for p in ['Source/localization-inventory-v3/strings.jsonl','Source/localization-inventory-v3/static-text.jsonl'] for l in (R/p).read_text().splitlines()];source={r['stableId']:r for r in sources};keys={source[x['stableId']].get('key') for x in a['items']}
selected={n:d for n,d in nodes.items() if any(v['value'] in keys for i in d['instructions'] for arg in i['operands'] for v in arg if isinstance(v['value'],str))}
write('compiled-changed-node-instructions.json',{'runtimeBindingSha256':sha(R/'Source/glossary-corpus-v2/runtime-bindings.json'),'nodes':selected,'note':'Actual protobuf instruction order, opcodes, operand fields and label targets. Static context, not reachability or execution proof.'})
catalog=j(R/'Documentation/th-semantic-regressions-v1.json');closure={r['stableId'] for r in c['reviewRows']};mandatory=set(c['components']['mandatoryRegression']);groups=[];union=set()
for g in catalog['groups']:
 ids=g['ids'];assert all(x in source for x in ids);assert hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest()==g['idsSha256'];union.update(ids)
 groups.append({'name':g['name'],'requiredCount':len(ids),'missingFromMandatory':[x for x in ids if x not in mandatory],'missingFromClosure':[x for x in ids if x not in closure]})
write('regression-catalog-reconciliation.json',{'catalogPath':'Documentation/th-semantic-regressions-v1.json','catalogSha256':sha(R/'Documentation/th-semantic-regressions-v1.json'),'selectorPath':'Scripts/build_th_semantic_regressions.py','selectorSha256':sha(R/'Scripts/build_th_semantic_regressions.py'),'use':'Existing project source-ID risk specification reused; no Thai translations or audit results used. Same accepted source universe.','requiredUnionCount':len(union),'hiMandatoryCount':len(mandatory),'missingRequiredFromMandatory':sorted(union-mandatory),'missingRequiredFromClosure':sorted(union-closure),'groups':groups,'verdict':'mandatory component incomplete; omitted semantic reads are not credited'})
print('COMPILED CHANGED NODES',len(selected))
for n,d in selected.items():
 vals=[v['value'] for i in d['instructions'] for arg in i['operands'] for v in arg if isinstance(v['value'],str)]
 print(n,' | '.join(x for x in vals if not x.startswith('line:') and not x.startswith('L')))
print('REGRESSION',len(union),len(union-mandatory),len(union-closure))
for g in groups:print(g['name'],g['requiredCount'],len(g['missingFromMandatory']),len(g['missingFromClosure']))
