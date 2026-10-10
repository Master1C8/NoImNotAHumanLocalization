import json,pathlib,importlib.util,hashlib
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
s=importlib.util.spec_from_file_location('topology',R/'Translations/fa/audit-cycle-002/verify-photo-topology.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
raw=bytes(json.loads((R/'Source/glossary-corpus-v1/sharedassets0.assets-2743.json').read_text())['compiledYarnProgram']);nodes={}
for n,_,v in m.fields(raw):
 if n!=2:continue
 e=list(m.fields(v));name=next(x.decode() for k,_,x in e if k==1);node=next(x for k,_,x in e if k==2);instructions=[];labels={}
 for k,_,x in m.fields(node):
  if k==2:
   f=list(m.fields(x));ops=[]
   for a,_,b in f:
    if a==2:ops.append({str(a):b.decode() if isinstance(b,bytes) else b for a,_,b in m.fields(b)})
   instructions.append({'index':len(instructions),'opcode':next((b for a,_,b in f if a==1),0),'operands':ops})
  elif k==3:
   f=list(m.fields(x));labels[next(b.decode() for a,_,b in f if a==1)]=next((b for a,_,b in f if a==2),0)
 nodes[name]={'instructions':instructions,'labels':labels,'rawSha256':hashlib.sha256(node).hexdigest()}
rows=[json.loads(x) for x in (O/'full-read-inputs.jsonl').read_text().splitlines()];names={n for r in rows for n in r['nodeNames']};names.add('MushroomEater_Entrance_3_6')
assert names<=set(nodes)
result={'compiledSha256':hashlib.sha256(raw).hexdigest(),'nodeCount':len(names),'nodes':{n:nodes[n] for n in sorted(names)}}
(O/'compiled-context.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('compiled delta node count',len(names))
