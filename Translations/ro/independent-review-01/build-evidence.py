"""Read-only independent Romanian review evidence; all writes stay beside this file."""
import hashlib, importlib.util, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT)); from compiled_context import load
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data):
 p=OUT/name; assert not p.exists(),p
 p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('recipe',ROOT/'Translations/ro/correction-cycle-001-recipe-v3.py')
recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)
progress=json.loads(recipe.PROGRESS.read_text()); rows=[]
for x in progress['reviewSegments']:rows.extend(json.loads(l) for l in (ROOT/x['path']).read_text().splitlines())
rows.sort(key=lambda r:r['ordinal']); assert [r['ordinal'] for r in rows]==list(range(16538))
_,values,locations=recipe.authored(); bykey={r['key']:r for r in rows if r['key']}; byid={r['stableId']:r for r in rows}
closure=[json.loads(l) for l in (ROOT/'Translations/ro/correction-cycle-001-closure-v3/review-rows.jsonl').read_text().splitlines()]
closureids={r['stableId'] for r in closure}; nodes,programsha=load()
placements={k:[] for k in bykey}; relevant={}; callbacks=[]
for name,ins in nodes.items():
 matched=[]
 for i in ins:
  for arg in i['operands']:
   if isinstance(arg,str) and arg in bykey:
    placements[arg].append({'node':name,'instruction':i['index'],'opcode':i['opcode']})
    if bykey[arg]['stableId'] in closureids:matched.append(bykey[arg]['stableId'])
 if matched:
  relevant[name]={'instructions':ins,'orderedTextUnits':[{'instruction':i['index'],'opcode':i['opcode'],'ordinal':bykey[a]['ordinal'],'stableId':bykey[a]['stableId'],'key':a,'source':bykey[a]['source'],'target':values[bykey[a]['stableId']]} for i in ins for a in i['operands'] if isinstance(a,str) and a in bykey]}
  if any(i['opcode']==12 for i in ins):callbacks.append({'node':name,'calls':[i for i in ins if i['opcode']==12]})
write('compiled-context.json',{'programSha256':programsha,'nodes':relevant,'limit':'Instruction order and branch operands preserved from pinned source. This is not a VM execution/reachability check.'})
write('compiled-placements.json',{'programSha256':programsha,'rows':[{'ordinal':r['ordinal'],'stableId':r['stableId'],'key':r['key'],'placements':placements.get(r['key'],[])} for r in closure],'callbackNodes':callbacks})
checks=json.loads((ROOT/'Source/preserve-exactly-v4.json').read_text());rules={r['stableId']:r for r in checks['tableRows']+checks['staticRows']}
from preserve_exact import check_value
for r in rows:check_value(rules[r['stableId']],values[r['stableId']])
write('preserve-exact-result.json',{'checkedUnits':len(rows),'errors':0,'boundary':'Current authored strings against pinned token rules; this does not verify semantics or rendering.'})
scope=json.loads((ROOT/'Documentation/static-text-scope-v2.json').read_text())
write('static-role-evidence.json',{'rows':[r for r in scope['rows'] if r['source'] in ['Super speed','В желаемое']],'limit':'Serialized role and binding evidence only; no live control reachability or layout claim.'})
enum=json.loads((OUT/'character-type-enum.json').read_text()); domain=json.loads((OUT/'admissible-character-inputs.json').read_text())
domains=[]
for c in domain['characters']:
 if c['room']==0:
  k='characterName_'+enum[str(c['type'])]; row=bykey.get(k)
  domains.append({**c,'enumName':enum[str(c['type'])],'key':k,'stableId':row['stableId'] if row else None,'target':values[row['stableId']] if row else None,'assembled':('BigLebowski: Fir-ar, nu. Ai deja '+values[row['stableId']]+' în locul ăla mișto, deci.') if row else None})
write('occupied-room-inputs.json',{'callback':'GetCharacterOnPlace(BigLebowski)','samePlaceSourceDomain':domains,'sourceDomainCount':len(domains),'assemblyEvidence':'managed-consumers.json','limit':'Provider/type/room domain is a conservative source domain. Empty/self and spawn feasibility need live save-state checks; no reachability claimed. All nonempty substitutions fit the same uninflected name slot.'})
# Independent risk surfaces: exact manifests include all source witnesses, even
# when a witness is outside the original closure. Discovery is not semantic acceptance.
risks={
 'dog-branch-context':lambda r:(r['key'] or '').startswith(('line:Buddy_Asking_3','line:Buddy_Armpit','line:Buddy_Hands','line:Buddy_Photo')),
 'body-check-context':lambda r:bool(re.search(r'^line:.*_(?:Teeth|Eyes|Hands|Ears|Armpit|Photo)(?:_|$)',r['key'] or '')),
 'violent-actions-unrestricted':lambda r:bool(re.search(r'зарез|прирез|выбил|выбили|перебил|убил|убить|убили',r['source'],re.I)),
 'kinship-and-referents':lambda r:bool(re.search(r'матер|\bмать\b|\bмама|родител|\bбрат|сестр|\bотец\b|отца|доч|девоч|дет[еи]|реб[её]н|вдов|\bмуж|\bжен',r['source'],re.I)),
 'hidden-role-ui':lambda r:(r['key'] or '').startswith('characterName_'),
 'placeholder-callback-context':lambda r:bool(re.search(r'\{\d+\}',r['source'])),
}
write('catalog-completeness-witnesses.json',{'definition':'Independent project source-risk surfaces; lexical surfaces require semantic adjudication, not automatic defect labels. Full compiled dependency edges retained separately.','surfaces':{name:{'count':len(hit:=[r for r in rows if select(r)]),'outsideClosureCount':sum(r['stableId'] not in closureids for r in hit),'outsideClosure':[{'ordinal':r['ordinal'],'stableId':r['stableId'],'key':r['key'],'source':r['source'],'target':values[r['stableId']]} for r in hit if r['stableId'] not in closureids]} for name,select in risks.items()}})
pins=[ROOT/'Translations/ro/correction-cycle-001-closure-v3/manifest.json',recipe.PROGRESS,recipe.PLAN,recipe.MANIFEST,ROOT/'Translations/ro/correction-cycle-001-recipe-v3.py',ROOT/'Documentation/glossary-translations/ro/layer.json',ROOT/'Source/localization-inventory-v3/strings.jsonl',ROOT/'Source/localization-inventory-v3/static-text.jsonl']
write('input-pins.json',{'files':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in pins],'authoredFiles':[{'path':p,'sha256':sha(ROOT/p)} for p in sorted({p for p,i in locations.values()})],'authoredValuesSha256':hashlib.sha256(json.dumps(values,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'programSha256':programsha})
print('closure',len(closure),'compiledNodes',len(relevant),'callbacks',len(callbacks),'room0',len(domains),'preserve16538 pass')
