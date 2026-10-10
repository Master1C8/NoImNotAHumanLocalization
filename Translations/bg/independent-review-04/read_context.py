"""Capture current full pairs and minimal raw compiled neighborhoods for review."""
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];B=R/'Translations/bg';O=Path(__file__).parent
load=lambda p:json.loads(p.read_text());d=load(B/'semantic-delta-cycle-004.json');nodes=load(B/'independent-review-01/compiled-nodes.json')
guid={'UI':'0cbd8a7a4f543344bb95659de87f67a5','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'};targets={}
for p in d['currentAuthoredFiles']:
 for e in load(R/p['path'])['entries']:
  i=e.get('stableId') or 'string:'+guid[p['collection']]+':'+str(e['id']);targets[i]=e['target']
source=[json.loads(l) for l in (R/'Source/localization-inventory-v3/strings.jsonl').open()];bykey={p['key']:p for p in source};byid={p['stableId']:p for p in source};uses={}
for name,node in nodes.items():
 for ins in node['instructions']:
  for op in ins['operands']:
   for f in op:
    if isinstance(f[2],str) and f[2] in bykey:uses.setdefault(f[2],[]).append({'node':name,'instruction':ins['index'],'opcode':ins['opcode']})
records=[]
for idx,row in enumerate(d['nextReviewRows']):
 contexts=[]
 for u in uses.get(row['key'],[]):
  node=nodes[u['node']];lines=[ins for ins in node['instructions'] if any(isinstance(f[2],str) and f[2] in bykey for op in ins['operands'] for f in op)];ix=next(i for i,ins in enumerate(lines) if ins['index']==u['instruction']);neighbors=[]
  for ins in lines[max(0,ix-1):ix+2]:
   for op in ins['operands']:
    for f in op:
     if isinstance(f[2],str) and f[2] in bykey:
      s=bykey[f[2]];neighbors.append({'instruction':ins['index'],'opcode':ins['opcode'],'stableId':s['stableId'],'key':s['key'],'source':s['source'],'target':targets.get(s['stableId'])})
  contexts.append({'use':u,'rawInstructions':node['instructions'],'labels':node['labels'],'neighbors':neighbors})
 records.append({'deltaIndex':idx,'stableId':row['stableId'],'fullPair':row,'compiledContexts':contexts,'runtimeReachability':'unproved' if not contexts else 'static compiled use only'})
if sys.argv[1]=='snapshot':
 p=O/'full-pair-contexts.json';assert not p.exists();p.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n');print(len(records))
else:
 a,b=map(int,sys.argv[1:3])
 for r in records[a:b]:
  print(r['deltaIndex'],r['fullPair']['key'])
  for c in r['compiledContexts']:
   print(c['use'])
   for n in c['neighbors']:
    if n['stableId']!=r['stableId']:print('CONTEXT R',n['source']);print('CONTEXT B',n['target'])
