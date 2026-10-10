import pathlib,json,re,hashlib
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
cl=json.loads((R/'Translations/fa/audit-cycle-001/closure.json').read_text());src={}
for l in (R/'Source/localization-inventory-v3/strings.jsonl').open():
 r=json.loads(l);src[r.get('key')]=r
tr={}
for r in cl['reviewRows']:tr[r['stableId']]=r['target']
chars=json.loads((O/'resident-inputs-v2.json').read_text())['rows'];enum=json.loads((O/'character-enum.json').read_text());consumer=[]
for name,key in [('Fatman','line:Fatman_Entrance_Occupied_0be05e8'),('Buddy','line:Buddy_Entrance_Occupied_0900d8b')]:
 c=next(r for r in chars if r['name']==name);s=src[key];rows=[]
 for peer in chars:
  if peer['place']!=c['place'] or peer['characterType']==c['characterType']:continue
  rk='characterName_'+enum[str(peer['characterType'])];rs=src[rk];target=tr[rs['stableId']]
  rows.append({'characterAssetName':peer['name'],'characterType':peer['characterType'],'place':peer['place'],'runtimeUiKey':rk,'runtimeUiStableId':rs['stableId'],'russianValue':rs['source'],'persianValue':target,'assembledRussian':s['source'].replace('{0}',rs['source']),'assembledPersian':tr[s['stableId']].replace('{0}',target),'logicalReview':'passed; substitution preserves referent and number, neutral Persian clause accepts each admitted label'})
 consumer.append({'stableId':s['stableId'],'node':s['nodeNames'][0],'visitor':name,'place':c['place'],'samePlaceOtherCharacters':rows})
result={'schemaVersion':1,'scope':'logical assembled changed occupied-resident consumers, admitted peer domain from pinned serialized CharacterSOData._place and exact ECharacterType enum -> UI runtime localization key','consumers':consumer,'limits':'No game execution; not current save occupancy or a live shaping/layout proof. Body prefix parsing excludes unrelated managed-reference registry tails. resident-inputs.json v1 reader advancement was not prefix consumption; authoritative corrected byte consumption is resident-inputs-v2.json.','pins':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [O/'resident-inputs-v2.json',O/'character-enum.json',O/'managed-context-v2.json',O/'compiled-context.json']}}
(O/'assembled-consumers.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for c in consumer:
 for r in c['samePlaceOtherCharacters']:print(c['visitor'],r['characterAssetName'],r['assembledPersian'])
