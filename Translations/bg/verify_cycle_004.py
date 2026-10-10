#!/usr/bin/env python3
"""Verify current cycle004 exact bytes, idiom controls and preserved independent evidence."""
import argparse,hashlib,json,re
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2];BG=ROOT/'Translations/bg'
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();th=lambda t:hashlib.sha256(t.encode()).hexdigest()
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['snapshot','verify']);args=parser.parse_args()
 plan=load(BG/'correction-batch-004.json');result=load(BG/'correction-batch-004-result.json');corpus=load(BG/'locale-corpus-cycle-004.json');closure=load(BG/'semantic-closure-cycle-004.json');delta=load(BG/'semantic-delta-cycle-004.json');spec=load(BG/'idiom-dependency-spec-cycle-004.json');bounded=load(BG/'correction-cycle-004-bounded-review.json')
 for rec in plan['pinnedInputs']:assert sha(ROOT/rec['path'])==rec['sha256'],rec['path']
 targets={};sources={};guid={'UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1'}
 for rec in result['allAuthoredFiles']:
  p=ROOT/rec['path'];v=ROOT/rec['validationPath'];assert sha(p)==rec['sha256'] and sha(v)==rec['validationSha256']
  receipt=load(v);assert receipt.get('batchSha256',receipt.get('draftSha256'))==rec['sha256'] and receipt['structuralResult']=='passed' and receipt.get('authoredRows',receipt.get('rows'))==rec['entries']
  for row in load(p)['entries']:
   i=row.get('stableId') or 'string:'+guid[rec['collection']]+':'+str(row['id']);assert i not in targets;targets[i]=row['target']
 for name in ['strings.jsonl','static-text.jsonl']:
  for line in (ROOT/'Source/localization-inventory-v3'/name).open():
   r=json.loads(line)
   if r['stableId'] in targets:sources[r['stableId']]=r
 assert len(targets)==len(sources)==16538
 assert {f['path']:f['sha256'] for f in result['allAuthoredFiles']}=={f['path']:f['sha256'] for f in corpus['authoredFiles']}
 assert corpus['rows']==16538 and corpus['structuralResult']==corpus['exactResult']=='passed'
 assert sha(ROOT/'Scripts/validate_locale_corpus.py')==corpus['validatorSha256'] and sha(ROOT/'Scripts/locale_text_inputs.py')==corpus['inputLoaderSha256']
 for n,h in corpus['owningValidators'].items():assert sha(ROOT/'Scripts'/n)==h
 closure_rows={r['stableId']:r for r in closure['reviewRows']}
 for i,r in closure_rows.items():assert r['source']==sources[i]['source'] and r['target']==targets[i] and r['key']==sources[i].get('key')
 selected={}
 for rule in spec['rules']:
  ids={i for i,r in sources.items() if re.search(rule['sourceRegex'],r['source'])};assert len(ids)==rule['expectedInventoryMatches']
  assert ids==set(closure['glossaryReferentGroups'][rule['name']]['ids']);selected[rule['name']]=ids
 controls=spec['regressionCases'];pattern=spec['rules'][1]['standaloneAssuranceRegex']
 for s in controls['assurancePositive']:assert re.search(pattern,s)
 for s in controls['assuranceNegativeStandalone']:assert not re.search(pattern,s)
 assert re.search(spec['rules'][0]['sourceRegex'],controls['temporalPositive']) and re.search(spec['rules'][0]['sourceRegex'],controls['temporalNegativeSense'])
 assert not re.search(spec['rules'][0]['sourceRegex'],controls['temporalNegativeLexical'])
 actual_assurances={i for i in sources if re.search(pattern,sources[i]['source'])};decisions={d['stableId']:d for d in plan['decisions']}
 assert actual_assurances=={i for i,d in decisions.items() if d['source'].startswith('Scammer:')} and len(actual_assurances)==2
 for i,d in decisions.items():assert sources[i]['source']==d['source'] and targets[i]==d['acceptedFullTarget'] and targets[i]!=d['currentFullTarget']
 assert not any('Прибрах се някак' in t for t in targets.values())
 assert all(targets[i].endswith('Гарантирам.') and not targets[i].endswith('Отговарям.') for i in actual_assurances)
 # Preserve exact matching negative-control units; do not replace every отвечаю/отговарям.
 for r in bounded['rows']:
  i=r['stableId'];assert r['source']==sources[i]['source']
  if i not in decisions:assert targets[i]==r['currentFullTarget']
 responsibility={r['stableId']:r for r in bounded['rows'] if r['family']=='answerResponsibilityVersusAssurance' and r['stableId'] not in actual_assurances}
 assert len(responsibility)==3
 # The source-only voice mechanism is unchanged. Historical v6 targets are NOT
 # presented as current reads: closure004 supplies current full target pairs.
 voice=load(BG/'voice-risk-selector-v6.json');oldcandidates=load(BG/'voice-remedial-candidates-v6.json')
 prefixes=tuple(voice['corePrefixes']+voice['secondaryPrefixes']);excluded=set(voice['excludeExactWords']);exact=set(voice['additionalExactWords'])
 match=lambda t:[w for w in re.findall('[А-Яа-яЁё]+',t.lower()) if w not in excluded and (w in exact or w.startswith(prefixes))]
 for w in voice['regressionCases']['include']:assert match(w)==[w]
 for w in voice['regressionCases']['exclude']:assert not match(w)
 voice_hits=[(i,match(r['source'])) for i,r in sources.items() if r.get('collection')=='Dialogs' and match(r['source'])]
 assert voice_hits==[(r['stableId'],r['matchedWords']) for r in oldcandidates['candidates']] and len(voice_hits)==741
 snapshots=load(BG/'correction-cycle-004-baseline/manifest.json')
 for r in snapshots['physicalSnapshots']:assert sha(ROOT/r['snapshotPath'])==r['sha256']
 # Trace exact compiled consumer joins and order, not merely locale node-name metadata.
 nodes=load(BG/'independent-review-01/compiled-nodes.json');uses=defaultdict(list);bykey={r.get('key'):i for i,r in sources.items() if r.get('key')}
 for name,node in nodes.items():
  for ins in node['instructions']:
   for op in ins['operands']:
    for f in op:
     if isinstance(f[2],str) and f[2] in bykey:uses[bykey[f[2]]].append({'node':name,'instruction':ins['index'],'opcode':ins['opcode']})
 for i,d in decisions.items():assert uses[i]==d['compiledUses']
 readids={r['stableId'] for r in delta['nextReviewRows']};assert readids==set(delta['components']['review']['ids']) and len(readids)==120
 mandatory=set(closure['components']['mandatoryRegressions']['ids']);assert len(mandatory)==908
 assert set(delta['mandatoryRegressions']['freshIds'])==mandatory&readids
 fresh=delta['mandatoryRegressions']['freshIds'];assert len(fresh)==1
 freshpair=closure_rows[fresh[0]];assert freshpair['key']=='line:Bald_Entrance_Occupied_0b1927e' and '{0}' in freshpair['source']
 producer=nodes['Bald_Entrance_Occupied']['instructions'];assert producer[1]['operands'][0][0][2]=='Bald' and producer[3]['operands'][0][0][2]=='GetCharacterOnPlace' and uses[fresh[0]]==[{'node':'Bald_Entrance_Occupied','instruction':4,'opcode':2}]
 managed=load(BG/'independent-review-01/managed-context.json')
 # Reconcile actual assembly bytes at the exact read-only original source path.
 assemblybase=Path('/Volumes/KINGSTONMAC/Applications/No Im not a Human.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human/NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed')
 for n,r in managed.items():assert sha(assemblybase/n)==r['sha256'],n
 # Fresh raw compiled program identity was independently normalized in Review03;
 # unchanged current binding hash retains that proof for all 3255 nodes.
 bindings=load(ROOT/'Source/glossary-corpus-v2/runtime-bindings.json');program=bytes(bindings['sharedassets0.assets:2743']['compiledYarnProgram'])
 assert hashlib.sha256(program).hexdigest()=='33de1e80e55e4eb8ec2093078028aa83fc45ac8b77acc05c5a4f9477ebe92827' and len(nodes)==3255
 pins={}
 for n in ['correction-batch-004.json','correction-batch-004-result.json','correction-cycle-004-sourcepairs.json','correction-cycle-004-baseline/manifest.json','idiom-dependency-spec-cycle-004.json','correction-cycle-004-bounded-review.json','semantic-closure-selector-cycle-004.json','build_semantic_closure_cycle_004.py','semantic-closure-cycle-004.json','build_semantic_delta_cycle_004.py','semantic-delta-cycle-004.json','locale-corpus-cycle-004.json','preserve-exact-cycle-004.json','independent-review-03-author-adjudication.json','verify_cycle_004.py','credits-role-map.json']:
  pins['Translations/bg/'+n]=sha(BG/n)
 staticrec=next(r for r in result['allAuthoredFiles'] if r['collection']=='StaticTMP');assert staticrec==next(r for r in plan['baselineAuthoredFiles'] if r['collection']=='StaticTMP')
 sourcepairs=load(BG/'correction-cycle-004-sourcepairs.json');assert sourcepairs['unchangedRows']==16535 and sourcepairs['unchangedAuthoredFiles']==408
 evidence={'schemaVersion':1,'locale':'bg','status':'cycle004 author handoff verified; independent delta pending','acceptedUnits':16538,'draftCoveragePercent':100,'semanticFirstPassReviewedUnits':16538,
  'appliedFullUnits':3,'affectedAuthoredFiles':3,'unchangedAuthoredFiles':408,'unchangedFullUnits':16535,'allAuthoredFilesAndSidecars':411,
  'fullOwningLocaleGuard':{'rows':16538,'structural':'passed','preserveExact':'passed','derivedCredits':'passed','receiptSha256':sha(BG/'locale-corpus-cycle-004.json'),'sidecarRefresh':'three receipts derived from whole corpus guard; no per-batch pools'},
  'sourceFamilyRegressions':{'temporalMatches':76,'allOtvechayuMatches':5,'standaloneAssurancesSelectedBySource':2,'exactFullReplacementChecks':3,'unchangedAssuranceResponsibilityControls':3,'noMechanicalReplacement':True},
  'voiceMechanismRegressions':{'lexicon':'unchanged v6','sourceSelectionMatches':741,'speakerCategories':112,'positiveNegativeControls':'passed','historicalCandidateTargets':'v6 kept immutable; use cycle004 current closure targets','selectorDefect':'none found by Review03; no v6 rule change'},
  'independentEvidence':{'Review03ManifestSha256':sha(BG/'independent-review-03/evidence-sha256.json'),'priorCycle003CorrectionsAccepted':41,'priorDismissalsUpheld':3,'newCycle004IndependentReview':'pending; no self credit'},
  'closureIds':2911,'nextReviewIds':120,'correctedIds':3,'newUnreviewedDependencies':72,'withoutApplicablePriorRead':75,'explicitInvalidations':45,'exactPriorApplicable':2836,'retired':0,
  'mandatory':{'total':908,'fresh':1,'retainedExact':907},
  'compiledConsumer':{'programSha256':hashlib.sha256(program).hexdigest(),'nodes':3255,'managedAssemblies':'actual bytes unchanged','deltaRowsWithCompiledUses':sum(bool(uses[r['stableId']]) for r in delta['nextReviewRows']),
   'deltaWithoutCompiledUses':[r['stableId'] for r in delta['nextReviewRows'] if not uses[r['stableId']]],
   'freshMandatory':dict(freshpair,uses=uses[fresh[0]],producer='Bald argument -> GetCharacterOnPlace -> localized characterName_{occupant} -> slot0',admissibleContextLimit='Compiled producer and original managed IL reconciled. No assumed finite runtime output count. Fresh independent review must check admitted occupant names, agreement/referent of го, and assembled consumer context against source character/room domain; physical gameplay unrun.')},
  'inputPins':pins,'baselineProgressSnapshotSha256':snapshots['progressSnapshotSha256'],
  'restart':'none; accepted inventory/glossary/gender policies/consumer topology unchanged','limits':['independent delta not yet assigned in this chat','editorial acceptance pending root','integration/runtime/font/layout/build/release gates pending; no game launch','images/textures excluded'],
  'telemetry':{'actualTokenUsage':'unknown; no exposed counters','subagents':'none'}}
 p=BG/'correction-cycle-004-final-verification.json';raw=(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n').encode()
 if args.action=='snapshot':assert not p.exists();p.write_bytes(raw)
 else:assert p.read_bytes()==raw,'Verification evidence drift'
 print(json.dumps({'action':args.action,'appliedFullUnits':3,'fullGuardRows':16538,'closureIds':2911,'nextIndependentDelta':120,'mandatoryFresh':1,'verificationSha256':sha(p)}))
if __name__=='__main__':main()
