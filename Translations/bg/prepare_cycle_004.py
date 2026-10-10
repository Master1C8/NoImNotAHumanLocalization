#!/usr/bin/env python3
"""Pin, adjudicate and snapshot the bounded Review03 Bulgarian correction cycle."""
import hashlib, json, re, sys
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]; BG=ROOT/'Translations/bg'
sys.path.insert(0,str(ROOT/'Scripts'))
from preserve_exact import check_value
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
th=lambda t:hashlib.sha256(t.encode()).hexdigest()
load=lambda p:json.loads(p.read_text())
def freeze(p,obj):
 raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
 if p.exists(): assert p.read_bytes()==raw,str(p)+' drift'
 else:p.write_bytes(raw)
def sid(c,e):
 return e.get('stableId') or 'string:'+{'UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1'}[c]+':'+str(e['id'])

def main():
 manifest=BG/'independent-review-03/evidence-sha256.json'
 assert sha(manifest)=='7528f1c522bf30a4a2f6999568e3dcfed48a684cea7122f720b29a791c733f61'
 for n,h in load(manifest)['files'].items():assert sha(manifest.parent/n)==h,n
 baseline=load(BG/'correction-batch-003-result.json')
 pins=load(BG/'semantic-closure-selector-cycle-003.json')['pinnedInputs'].copy()
 for n in ['correction-batch-003-result.json','semantic-closure-cycle-003.json','semantic-delta-cycle-003.json','independent-review-03/evidence-sha256.json','independent-review-03/input-verification.json','independent-review-03/final-verification.json','independent-review-03/findings.json','independent-review-03/per-id-read-verdicts.json','independent-review-03/supplementary-pair-verdicts.json','independent-review-01/compiled-nodes.json']:
  pins['Translations/bg/'+n]=sha(BG/n)
 for n in ['validate_locale_corpus.py','locale_text_inputs.py','preserve_exact.py','validate_game_text_batch.py','validate_static_text_draft.py']:
  pins['Scripts/'+n]=sha(ROOT/'Scripts'/n)
 for p,h in pins.items():assert sha(ROOT/p)==h,p
 # Verify every current review input before any correction; save this result.
 reviewpins=load(BG/'independent-review-03/input-verification.json')['pins']
 for p,h in reviewpins.items():assert sha(ROOT/p)==h,p
 target={};paths={}
 for f in baseline['allAuthoredFiles']:
  assert sha(ROOT/f['path'])==f['sha256'] and sha(ROOT/f['validationPath'])==f['validationSha256'],f['path']
  for e in load(ROOT/f['path'])['entries']:
   identity=sid(f['collection'],e);assert identity not in target
   target[identity]=e['target'];paths[identity]=f['path']
 assert len(target)==16538
 source={}
 for p in ['strings.jsonl','static-text.jsonl']:
  for line in (ROOT/'Source/localization-inventory-v3'/p).open():
   r=json.loads(line)
   if r['stableId'] in target:source[r['stableId']]=r
 assert set(source)==set(target)
 exact=load(ROOT/'Source/preserve-exactly-v4.json'); rules={r['stableId']:r for r in exact['tableRows']+exact['staticRows']}
 nodes=load(BG/'independent-review-01/compiled-nodes.json'); uses=defaultdict(list)
 keys={r.get('key'):i for i,r in source.items() if r.get('key')}
 for name,node in nodes.items():
  for ins in node['instructions']:
   for op in ins['operands']:
    for f in op:
     if isinstance(f[2],str) and f[2] in keys: uses[keys[f[2]]].append({'node':name,'instruction':ins['index'],'opcode':ins['opcode']})
 temporal_pattern=r'(?iu)\bкак[-‐‑\s]+то\b'; assurance_pattern=r'(?iu)\bотвечаю\b'
 standalone=r'(?iu)(?:^|[.!?]\s+)Отвечаю[.!?](?:\s|$)'
 temporal={i for i,r in source.items() if re.search(temporal_pattern,r['source'])}
 assurance={i for i,r in source.items() if re.search(assurance_pattern,r['source'])}
 narrow={i for i in assurance if re.search(standalone,source[i]['source'])}
 assert len(temporal)==76 and len(assurance)==5 and len(narrow)==2
 # Controls change only the semantic construction. Never replace a matched token mechanically.
 spec={'schemaVersion':1,'locale':'bg','status':'canonical bounded temporal/assurance source-family rule for cycle004',
       'sourceSha256':sha(ROOT/'Source/localization-inventory-v3/strings.jsonl'),
       'rules':[{'name':'occasionVersusManner','sourceRegex':temporal_pattern,'expectedInventoryMatches':76,
                 'interpretation':'Read complete unit and scene: past anecdote -> occasion; means/degree/current uncertainty -> manner or downtoner. No automatic replacement.'},
                {'name':'answerResponsibilityVersusAssurance','sourceRegex':assurance_pattern,'expectedInventoryMatches':5,
                 'standaloneAssuranceRegex':standalone,'expectedStandaloneMatches':2,
                 'interpretation':'Standalone Scammer Отвечаю vouches for his claim. Answering a question and being responsible for something are different constructions.'}],
       'regressionCases':{'temporalPositive':'Bald: Я как-то вернулся домой. Дверь открыта.',
         'temporalNegativeSense':'Unstable: Как-то я их перекрутил.',
         'temporalNegativeLexical':'Bald: Я вернулся домой.',
         'assurancePositive':['Scammer: Это выигрышная стратегия. Отвечаю.','Scammer: Мутить темки было как нехер делать, ёпта. Отвечаю.'],
         'assuranceNegativeStandalone':['Miner: Я тут за всё отвечаю.','Scammer: За базар отвечаю.','Experienced: Я тебе отвечаю!'],
         'responsibilityTarget':'Miner: ...отговарям за всичко.',
         'occasionRepair':'Веднъж се прибрах вкъщи.', 'rejectedOccasionCalque':'Прибрах се някак.',
         'assuranceRepair':'Гарантирам.', 'rejectedAssuranceCalque':'Отговарям.'},
       'glossaryRules':['theater-man: male; mother and grandmother; coarse familiar voice; distinguish Wolfhound.','player: male; retain revelation order.','Scammer service prefix preserved; actual compiled betting/KIS scene controls assurance; no invented name or speaker attribution.'],
       'bounds':'All accepted source matches, not a speaker whitelist or generated-ID append. Exact target controls checked separately. Voice v6 unchanged; Review03 found no voice selector defect.'}
 freeze(BG/'idiom-dependency-spec-cycle-004.json',spec)
 for t in spec['regressionCases']['assurancePositive']:assert re.search(standalone,t)
 for t in spec['regressionCases']['assuranceNegativeStandalone']:assert not re.search(standalone,t)
 assert re.search(temporal_pattern,spec['regressionCases']['temporalPositive']) and re.search(temporal_pattern,spec['regressionCases']['temporalNegativeSense'])
 assert not re.search(temporal_pattern,spec['regressionCases']['temporalNegativeLexical'])
 findings=load(BG/'independent-review-03/findings.json')['findings'];assert len(findings)==3
 decisions=[];adjud=[]
 reasons=[
  'Compiled Bald_Asking_4:25 describes one past arrival, before injured family, approaching thugs and flight. Keep mother AND grandmother, open door, chaos, broken fingers/legs, coarse hesitation and unfinished speech; change only temporal opening, restoring explicit home.',
  'Compiled Scammer_Asking_2_3_2:3 vouches for a winning strategy before KIS advice. Keep actor, strategy and affiliation statement; Гарантирам is a natural unqualified assurance, not an answer.',
  'Compiled Scammer_Asking_1_2:3 vouches for betting schemes after earnings, before bookmaker scam methods. Keep past action, ease comparison and coarse oath; replace only the assurance calque.']
 for f,reason in zip(findings,reasons):
  i=f['stableId'];assert source[i]['source']==f['source'] and target[i]==f['currentFullTarget'] and paths[i]==f['authoredPath']
  assert th(f['source'])==f['sourceSha256'] and th(target[i])==f['targetSha256']
  assert uses[i] and {u['node'] for u in uses[i]}==set(f['sceneNodes'])
  check_value(rules[i],f['proposedFullTarget'])
  d={'stableId':i,'collection':'Dialogs','batchPath':paths[i],'source':f['source'],'currentFullTarget':target[i],'acceptedFullTarget':f['proposedFullTarget'],'basis':f['findingId'],'compiledUses':uses[i]}
  decisions.append(d);adjud.append(dict(d,disposition='accepted',reason=reason,reviewerProposedFullTarget=f['proposedFullTarget']))
 assert {d['stableId'] for d in decisions if 'Scammer:' in d['source']}==narrow
 snapshot=BG/'correction-cycle-004-baseline';snapshot.mkdir(exist_ok=True)
 copies=[]
 for f in baseline['allAuthoredFiles']:
  if f['path'] not in {d['batchPath'] for d in decisions}:continue
  for field,hfield in [('path','sha256'),('validationPath','validationSha256')]:
   original=ROOT/f[field];copy=snapshot/original.name;raw=original.read_bytes()
   if copy.exists():assert copy.read_bytes()==raw
   else:copy.write_bytes(raw)
   copies.append({'path':f[field],'snapshotPath':str(copy.relative_to(ROOT)),'sha256':f[hfield]})
 # Freeze mutable progress as historical exact evidence before later summary update.
 progress=BG/'semantic-review-progress.json';saved=snapshot/'semantic-review-progress.json'
 if saved.exists():assert saved.read_bytes()==progress.read_bytes()
 else:saved.write_bytes(progress.read_bytes())
 manifestobj={'schemaVersion':1,'locale':'bg','acceptedUnits':16538,'review03ManifestSha256':sha(manifest),'review03CurrentInputsVerified':len(reviewpins),
              'sourceAndConfigurationPins':pins,'allAuthoredFiles':baseline['allAuthoredFiles'],'physicalSnapshots':copies,'progressSnapshotSha256':sha(saved),
              'immutableReviewEvidenceVerified':True,'boundary':'exact preimage snapshot; no game/Git/source/glossary mutation'}
 freeze(snapshot/'manifest.json',manifestobj)
 pins['Translations/bg/correction-cycle-004-baseline/manifest.json']=sha(snapshot/'manifest.json')
 pins['Translations/bg/idiom-dependency-spec-cycle-004.json']=sha(BG/'idiom-dependency-spec-cycle-004.json')
 plan={'schemaVersion':1,'locale':'bg','gameVersion':'1.3.19','acceptedUnits':16538,'status':'all three Review03 proposals accepted in one bounded preflighted batch',
       'decisionCount':3,'reviewerProposalCount':3,'reviewerAcceptedCount':3,'reviewerDismissedCount':0,'additionalDependencyCount':0,
       'pinnedInputs':[{'path':p,'sha256':h} for p,h in pins.items()], 'baselineAuthoredFiles':baseline['allAuthoredFiles'],'decisions':decisions}
 freeze(BG/'correction-batch-004.json',plan)
 freeze(BG/'independent-review-03-author-adjudication.json',{'schemaVersion':1,'locale':'bg','proposalCount':3,'acceptedCount':3,'dismissedCount':0,'additionalCorrectionCount':0,
         'adjudications':adjud,'upheldPriorDismissals':'Review03 upheld Review02 -010, -014 and -029; no new contradictory evidence, preserved unchanged.',
         'planSha256':sha(BG/'correction-batch-004.json'),'baselineManifestSha256':sha(snapshot/'manifest.json'),'independence':'author adjudication only; no clean independent review or acceptance'})
 # Complete full pairs in the bounded lexical families, with actual compiled uses,
 # nearest line instructions and branch operands. Selection is over the whole accepted inventory.
 temporal_events=set('110504455038902285 110504454569140228 110504454418145291 110504453981937669 110504453835137025 110504453570895873 110504453558312966 110504453541535746 110504453516369923 110504452941750273 110504452790755329 110504452471988226 110504452459405319 110504452438433796 110504452434239494 110504452358742020 110504452354547717 110504451817676809 110504455814848520'.split())
 rows=[]
 for i in source:
  if i not in temporal|assurance:continue
  r=source[i];context=[]
  for u in uses[i]:
   node=nodes[u['node']];lineins=[]
   for ins in node['instructions']:
    hits=[keys[f[2]] for op in ins['operands'] for f in op if isinstance(f[2],str) and f[2] in keys]
    if hits:lineins.append((ins['index'],hits))
   positions=[k for k,(idx,ids) in enumerate(lineins) if idx==u['instruction']]
   nearby=[]
   for pos in positions:
    for idx,ids in lineins[max(0,pos-2):pos+3]:
     for si in ids:nearby.append({'instruction':idx,'stableId':si,'source':source[si]['source'],'target':target[si]})
   branches=[ins for ins in node['instructions'] if ins['opcode'] in (0,1,3,4,7,8,9,10,11,12,13)]
   context.append({'use':u,'labels':node['labels'],'nearbyFullPairs':nearby,'controlAndCommands':branches})
  finding=next((d for d in adjud if d['stableId']==i),None)
  sense=('past occasion/anecdote' if i.rsplit(':',1)[1] in temporal_events else 'manner/degree/current uncertainty') if i in temporal else ('standalone pledge' if i in narrow else 'responsibility or contextual vouching, not standalone answer')
  rows.append({'stableId':i,'key':r.get('key'),'source':r['source'],'currentFullTarget':target[i],'authoredPath':paths[i],'sourceSha256':th(r['source']),'targetSha256':th(target[i]),
               'family':'occasionVersusManner' if i in temporal else 'answerResponsibilityVersusAssurance','contextualSense':sense,'actualCompiledContext':context,
               'fullPairRead':True,'authorVerdict':'accept complete finding' if finding else 'retain; no objective meaning/grammar repair identified',
               'acceptedFullTarget':finding['acceptedFullTarget'] if finding else None})
 assert len(rows)==81
 controls=[{'stableId':i,'source':source[i]['source'],'target':t,'key':source[i].get('key'),'compiledUses':uses[i],'fullPairRead':True,'verdict':'covered proposed calque' if i in {d['stableId'] for d in decisions} else 'retain valid responsibility/applicability/assurance construction'} for i,t in target.items() if re.search(r'(?iu)\bотговарям\b|прибрах се някак|гарантирам',t)]
 freeze(BG/'correction-cycle-004-bounded-review.json',{'schemaVersion':1,'locale':'bg','status':'bounded author full-pair review; not independent','acceptedInventoryUnits':16538,
       'specPath':'Translations/bg/idiom-dependency-spec-cycle-004.json','specSha256':sha(BG/'idiom-dependency-spec-cycle-004.json'),'sourcePins':pins,
       'temporalMatches':76,'assuranceMatches':5,'standaloneAssuranceMatches':2,'fullPairCount':81,'temporalPastOccasionUnits':len(temporal_events),'rows':rows,'targetControls':controls,
       'objectiveCorrections':3,'additionalCorrections':0,'readBoundary':'Every selected complete Russian/Bulgarian pair read. Three corrections and ambiguous sense controls checked in full compiled scenes; other clear manner/degree or anecdote pairs read with their line context. Branch metadata is admissible source consumer evidence, not runtime testing.',
       'restart':'No changed source, glossary, character policy, scope, consumer or workflow; first complete semantic pass reusable.'})
 print(json.dumps({'changedIds':3,'affectedBatches':3,'fullPairFamilies':81,'targetControls':len(controls),'review03InputPinsVerified':len(reviewpins),'planSha256':sha(BG/'correction-batch-004.json')}))
if __name__=='__main__':main()
