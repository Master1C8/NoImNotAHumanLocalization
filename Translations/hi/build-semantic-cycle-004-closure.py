#!/usr/bin/env python3
"""Rebuild/verify Hindi cycle004 closure and exact next independent delta."""
import argparse,hashlib,json,pathlib,re,subprocess,sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
HI=ROOT/'Translations/hi'
RV=HI/'independent-review-03'
PATTERN=r'(?i)\bмицели(?:й|я|ю|и|ем)\b'
OUTS=('semantic-cycle-004-applied-evidence.json','semantic-cycle-004-structural-gate.json',
      'semantic-cycle-004-closure.json','semantic-cycle-004-review-delta.json')
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def hs(text):return hashlib.sha256(text.encode()).hexdigest()
def ih(ids):return hs('\n'.join(ids)+'\n')
def read(path):return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
def lines(path):return [json.loads(x) for x in pathlib.Path(path).read_text().splitlines()]
def dump(obj):return json.dumps(obj,ensure_ascii=False,indent=2)+'\n'
def build():
 adj=read(HI/'semantic-cycle-004-adjudication.json');pre=read(HI/'semantic-cycle-004-preflight.json')
 plan=read(HI/'semantic-cycle-004-application-plan.json');snap=read(HI/'semantic-cycle-004-pre-edit-snapshot.json')
 old=read(HI/'semantic-cycle-003-closure.json');review=read(RV/'final-coverage-and-regression-proof.json')
 full=read(HI/'semantic-cycle-004-full-corpus.json');pins=read(RV/'final-unchanged-input-pins.json')
 assert pre['adjudicationSha256']==sha(HI/'semantic-cycle-004-adjudication.json')
 assert plan['preflightSha256']==sha(HI/'semantic-cycle-004-preflight.json')
 assert plan['snapshotSha256']==sha(HI/'semantic-cycle-004-pre-edit-snapshot.json')
 assert plan['previousClosureSha256']==sha(HI/'semantic-cycle-003-closure.json')==adj['previousClosureSha256']
 assert review['currentCycle003ClosureCount']==old['closureCount']==5207
 assert review['freshAssignedFullPairs']==141 and review['exactPriorApplicableCount']==5066
 assert full['locale']=='hi' and full['rows']==16538 and full['structuralResult']==full['exactResult']=='passed'
 assert full['selectedIdCoverage']=='16538 unique; no missing/extra'
 assert full['sourceInventorySha256']==adj['sourceInventorySha256'] and full['staticInventorySha256']==adj['staticInventorySha256']
 assert sha(ROOT/'Source/localization-inventory-v3/strings.jsonl')==adj['sourceInventorySha256']
 assert sha(ROOT/'Source/localization-inventory-v3/static-text.jsonl')==adj['staticInventorySha256']
 assert sha(ROOT/'Documentation/glossary-translations/hi/layer.json')==adj['glossaryLayerSha256']
 assert sha(ROOT/'Source/glossary-corpus-v2/runtime-bindings.json')==adj['compiledRuntimeBindingsSha256']
 assert sha(ROOT/'Source/preserve-exactly-v4.json')==adj['preserveExactManifestSha256']
 assert sha(ROOT/old['technicalContextPath'])==old['technicalContextSha256']
 assert sha(ROOT/old['catalogPath'])==old['catalogSha256']
 assert sha(RV/'final-artifact-manifest.json')==adj['review03FinalManifestSha256']
 old_pins=pins['pins'];new_path=plan['file']['path']
 assert len(old_pins)==705
 # The assigned operational checkpoint advances after this artifact is built.
 assert all(sha(ROOT/name)==digest for name,digest in old_pins.items()
            if name not in {new_path,'Documentation/hi-text-checkpoint.json'})
 assert sha(ROOT/new_path)==plan['file']['afterSha256'] and old_pins[new_path]==plan['file']['beforeSha256']
 assert all(sha(ROOT/name)==digest for name,digest in pins['additionalVerifiedInputs'].items())
 receipt_files={row['path']:row['sha256'] for row in full['authoredFiles']}
 assert len(receipt_files)==335
 assert all(sha(ROOT/name)==digest for name,digest in receipt_files.items())
 assert receipt_files[new_path]==plan['file']['afterSha256']
 source=lines(ROOT/'Source/localization-inventory-v3/strings.jsonl')
 static=lines(ROOT/'Source/localization-inventory-v3/static-text.jsonl')
 by_collection_id={(row['collection'],row['stableId'].rsplit(':',1)[1]):row for row in source}
 by_id={row['stableId']:row for row in source+static}
 targets={};authored={}
 for name in receipt_files:
  obj=read(ROOT/name)
  for e in obj['entries']:
   sid=e.get('stableId') or by_collection_id[(obj['collection'],str(e['id']))]['stableId']
   assert sid not in targets
   targets[sid]=e['target'];authored[sid]=name
 accepted=[row for row in source+static if row['stableId'] in targets]
 ids=[row['stableId'] for row in accepted];order={sid:i for i,sid in enumerate(ids)}
 assert len(ids)==len(set(ids))==len(targets)==16538
 assert ih(ids)==old['sourceOrderIdListSha256LfFinalNewline']
 prior_ids=[row['stableId'] for row in old['reviewRows']]
 assert len(prior_ids)==5207 and ih(prior_ids)==old['closureIdListSha256LfFinalNewline']
 prior=set(prior_ids)
 # All prior-closure full-unit source/current-target pairs retain their exact Review03 decision hashes.
 assert all(row['sourceSha256']==hs(by_id[row['stableId']]['source']) and
            row['targetSha256']==hs(targets[row['stableId']]) for row in old['reviewRows'])
 assert len(lines(RV/'per-id-current-closure-decisions.jsonl'))==5207
 item=adj['item'];sid=item['stableId'];file=plan['file'];p=ROOT/file['path']
 before=read(HI/'semantic-cycle-004-before-files'/p.name);after=read(p)
 assert sha(HI/'semantic-cycle-004-before-files'/p.name)==file['beforeSha256']
 assert sha(HI/'semantic-cycle-004-after-files'/p.name)==sha(p)==file['afterSha256']
 assert sha(ROOT/file['historicalSidecarPath'])==file['historicalSidecarSha256']
 old_entries={str(e['id']):e for e in before['entries']};new_entries={str(e['id']):e for e in after['entries']}
 assert old_entries.keys()==new_entries.keys()
 key=sid.rsplit(':',1)[1]
 assert {k for k in old_entries if old_entries[k]!=new_entries[k]}=={key}
 assert old_entries[key]['target']==item['before'] and new_entries[key]['target']==item['acceptedFullTarget']
 assert hs(targets[sid])==item['acceptedFullTargetSha256'] and hs(by_id[sid]['source'])==item['sourceSha256']
 assert sid not in prior
 family=[row['stableId'] for row in accepted if re.search(PATTERN,row['source'])]
 expected=read(RV/'mycelium-inflection-closure-finding-evidence.json')['completeSourceFamily']
 assert len(family)==22 and set(family)=={row['stableId'] for row in expected}
 assert family==[sid for sid in ids if sid in set(family)]
 assert set(family)-prior=={row['stableId'] for row in expected if not row['inCycle003Closure']}
 assert len(set(family)-prior)==6
 # Ordinary components retain prior regression dependencies, then add only source-selected current risks.
 components={name:set(members) for name,members in old['components'].items()}
 components['changed'].add(sid)
 current_scene={row['stableId'] for row in accepted if 'Mushroom_end_2' in row.get('nodeNames',[])}
 assert len(current_scene)==5 and sid in current_scene
 components['sceneContext'].update(current_scene)
 current_repeat={row['stableId'] for row in accepted if row['source']==item['source']}
 assert current_repeat=={sid}
 components['repetition'].update(current_repeat)
 components['glossaryReferent'].update(family)
 required=set()
 catalog=read(ROOT/old['catalogPath'])
 for group in catalog['groups']:
  assert len(group['ids'])==group['count'] and ih(group['ids'])==group['idsSha256']
  required.update(group['ids'])
 assert len(required)==4805 and required<=set(ids)
 components['mandatoryRegression'].update(required)
 assert required<=components['mandatoryRegression']
 assert set().union(*components.values())<=set(ids)
 ordered={name:[x for x in ids if x in members] for name,members in components.items()}
 current=set().union(*components.values())
 closure_ids=[x for x in ids if x in current]
 newly=current-prior;retired=prior-current
 # No prior independently read unit changes target or has this corrected node as scene context.
 current_invalidated=(current_scene|current_repeat)&prior-{sid}
 assert not current_invalidated
 invalidated=set()
 delta_set={sid}|newly|invalidated
 delta_ids=[x for x in ids if x in delta_set]
 assert len(closure_ids)==len(current) and len(delta_ids)==len(delta_set)
 assert delta_set=={sid}|(current-prior)|invalidated and not retired&delta_set
 supplemental=lines(RV/'outside-delta-six-independent-decisions.jsonl')
 assert len(supplemental)==6 and {row['stableId'] for row in supplemental}==set(family)-prior
 exact_supp=[];context_changed=[]
 for row in supplemental:
  ss=row['stableId']
  assert hs(by_id[ss]['source'])==row['sourceSha256'] and hs(targets[ss])==row['currentTargetSha256']
  assert row['glossarySha256']==adj['glossaryLayerSha256'] and row['compiledBindingSha256']==adj['compiledRuntimeBindingsSha256']
  exact_supp.append(ss)
  if ss in current_scene:context_changed.append(ss)
 assert len(exact_supp)==6 and len(context_changed)==2
 supplement={'exactFullUnitSourceTargetApplicableIds':[x for x in ids if x in exact_supp],
             'exactFullUnitApplicableCount':6,
             'sameNodeChangedContextIds':[x for x in ids if x in context_changed],
             'sameNodeChangedContextCount':2,
             'contextUnchangedSupplementalIds':[x for x in ids if x in set(exact_supp)-set(context_changed)],
             'contextUnchangedSupplementalCount':4,
             'interpretation':'All six clean supplemental complete-unit source/target decisions remain exact. Two Mushroom_end_2 neighbors require fresh scene-context judgment after the growth-size correction. The formal new-dependency delta includes all six because they were outside the previous independently reviewed closure.'}
 derived_names=['static-phrases-authored.json','credits-role-map.json','static-text-draft.json',
                'common-options-001.authored.json','common-options-002.authored.json','common-options-003.authored.json',
                'dialogue-batch-900.json','dialogue-batch-901.json','dialogue-batch-902.json']
 derived={name:sha(HI/name) for name in derived_names}
 assert all(pins['pins']['Translations/hi/'+name]==digest for name,digest in derived.items()
            if 'Translations/hi/'+name in pins['pins'])
 old_gate=read(HI/'semantic-cycle-002-structural-gate.json')
 assert derived['static-phrases-authored.json']==old_gate['phraseMapSha256']
 assert derived['credits-role-map.json']==old_gate['creditsRoleMapSha256']
 phrase_map={row['source']:row['target'] for row in read(HI/'static-phrases-authored.json')['entries']}
 assert len(phrase_map)==len(read(HI/'static-phrases-authored.json')['entries'])
 for row in static:
  if row['stableId'] in targets and row['stableId']!='tmp:level5:59:m_text':
   assert targets[row['stableId']]==phrase_map[row['source']]
 for number,output in (('001','900'),('002','901'),('003','902')):
  run=subprocess.run([sys.executable,str(ROOT/'Scripts/expand_exact_text_batch.py'),
                      str(HI/f'common-options-{number}.authored.json'),
                      str(HI/f'dialogue-batch-{output}.json'),'--verify'],
                     capture_output=True,text=True)
  assert run.returncode==0,(number,run.stdout,run.stderr)
  assert json.loads(run.stdout)['rows']=={'001':2593,'002':245,'003':45}[number]
 gate={'schemaVersion':1,'locale':'hi','gameVersion':'1.3.19',
       'status':'fresh locale-only whole-corpus and preserve-exact gate passed; distinct semantic review pending',
       'fullCorpusReceiptPath':'Translations/hi/semantic-cycle-004-full-corpus.json',
       'fullCorpusReceiptSha256':sha(HI/'semantic-cycle-004-full-corpus.json'),
       'fullCorpusValidatorSha256':full['validatorSha256'],'acceptedIds':16538,'duplicateIds':0,'missingIds':0,
       'extraIds':0,'exactSpanFailures':0,'owningStructuralGuards':'passed','historicalSidecars':'unchanged',
       'sourceInventorySha256':adj['sourceInventorySha256'],'staticInventorySha256':adj['staticInventorySha256'],
       'glossaryLayerSha256':adj['glossaryLayerSha256'],'compiledRuntimeBindingsSha256':adj['compiledRuntimeBindingsSha256'],
       'preserveExactManifestSha256':adj['preserveExactManifestSha256'],
       'derivedStaticRows':178,'commonOptionExpansionRows':[2593,245,45],
       'derivedInputOutputSha256':derived,'authoredFiles':full['authoredFiles']}
 application={'schemaVersion':1,'locale':'hi','status':'one full-unit target-only correction applied',
              'applicationPlanSha256':sha(HI/'semantic-cycle-004-application-plan.json'),
              'adjudicationSha256':sha(HI/'semantic-cycle-004-adjudication.json'),
              'preflightSha256':sha(HI/'semantic-cycle-004-preflight.json'),
              'beforeAuthoredSha256':file['beforeSha256'],'afterAuthoredSha256':file['afterSha256'],
              'historicalSidecarSha256':file['historicalSidecarSha256'],
              'changedStableIds':[sid],'changedCount':1,'unchangedOtherTargetCount':16537,
              'freshFullCorpusReceiptSha256':sha(HI/'semantic-cycle-004-full-corpus.json')}
 closure={'schemaVersion':1,'locale':'hi','gameVersion':'1.3.19','status':'reproducible cycle004 dependency closure; distinct delta review pending',
          'acceptedCount':16538,'sourceOrderIdListSha256LfFinalNewline':ih(ids),
          'sourceInventorySha256':adj['sourceInventorySha256'],'staticInventorySha256':adj['staticInventorySha256'],
          'glossaryLayerSha256':adj['glossaryLayerSha256'],'compiledRuntimeBindingsSha256':adj['compiledRuntimeBindingsSha256'],
          'authoredStructuralGateSha256':hs(dump(gate)),'adjudicationSha256':sha(HI/'semantic-cycle-004-adjudication.json'),
          'previousIndependentlyReviewedClosureSha256':sha(HI/'semantic-cycle-003-closure.json'),
          'review03FinalEvidenceManifestSha256':adj['review03FinalManifestSha256'],
          'catalogPath':old['catalogPath'],'catalogSha256':old['catalogSha256'],
          'catalogRequiredCount':len(required),'catalogRequiredIdListSha256LfFinalNewline':ih([x for x in ids if x in required]),
          'technicalContextPath':old['technicalContextPath'],'technicalContextSha256':old['technicalContextSha256'],
          'currentCorrectedCount':1,'cumulativeChangedComponentCount':len(components['changed']),
          'closureCount':len(closure_ids),'closureIdListSha256LfFinalNewline':ih(closure_ids),
          'componentCounts':{name:len(values) for name,values in ordered.items()},
          'componentIdListSha256LfFinalNewline':{name:ih(values) for name,values in ordered.items()},
          'components':ordered,'myceliumInflectionPattern':PATTERN,
          'myceliumAcceptedSourceUseCount':22,'myceliumAcceptedSourceIds':family,
          'myceliumAcceptedSourceIdListSha256LfFinalNewline':ih(family),
          'currentChangedSceneNode':'Mushroom_end_2','currentChangedSceneIds':[x for x in ids if x in current_scene],
          'supplementalReview03Applicability':supplement,'missingRequiredCatalogIds':[],'extraUnacceptedIds':[],
          'reviewRows':[{'stableId':x,'reviewIndex':order[x],'source':by_id[x]['source'],'target':targets[x],
                         'sourceSha256':hs(by_id[x]['source']),'targetSha256':hs(targets[x]),
                         'authoredPath':authored[x],
                         'components':[name for name,values in components.items() if x in values]} for x in closure_ids],
          'selectorMethod':'Canonical accepted source order; retained previous exact dependencies; one corrected full unit; actual compiled Mushroom_end_2 scene; exact source repetition; inflection-aware Russian mycelium predicate matching all 22 actual accepted uses; unchanged runtime supplier context; complete 4,805-ID mandatory source catalog.',
          'selectorSha256':sha(pathlib.Path(__file__))}
 delta={'schemaVersion':1,'locale':'hi','gameVersion':'1.3.19','status':'exact cycle004 next distinct-reviewer delta; not yet reviewed',
        'previousIndependentlyReviewedClosureSha256':sha(HI/'semantic-cycle-003-closure.json'),
        'previousIndependentlyReviewedCount':len(prior),'currentClosureCount':len(closure_ids),
        'currentClosureIdListSha256LfFinalNewline':ih(closure_ids),
        'correctedIds':[sid],'correctedCount':1,'newDependencyIds':[x for x in ids if x in newly],
        'newDependencyCount':len(newly),'explicitInvalidatedPriorIds':[x for x in ids if x in invalidated],
        'explicitInvalidatedPriorCount':len(invalidated),
        'invalidationReason':'No previous-closure target or same compiled scene changed. Selector expansion alone does not invalidate exact prior independent decisions.',
        'retiredIds':[x for x in ids if x in retired],'retiredCount':len(retired),
        'retirementReason':'No prior dependency was removed by this additive source predicate/scene correction.',
        'deltaIds':delta_ids,'deltaCount':len(delta_ids),'deltaIdListSha256LfFinalNewline':ih(delta_ids),
        'formula':'corrected union (current closure minus previous independently reviewed closure) union explicit invalidated prior',
        'supplementalExactApplicability':supplement,'missingAcceptedIds':[],'extraUnacceptedIds':[]}
 for key in ('correctedIds','newDependencyIds','explicitInvalidatedPriorIds','retiredIds'):
  delta[key+'Sha256LfFinalNewline']=ih(delta[key])
 outputs=dict(zip(OUTS,map(dump,(application,gate,closure,delta))))
 return outputs,closure,delta

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
 outputs,c,d=build()
 for name,text in outputs.items():
  path=HI/name
  if args.verify:assert path.read_text(encoding='utf-8')==text,name
  else:
   assert not path.exists(),name
   path.write_text(text,encoding='utf-8')
 print('verified' if args.verify else 'wrote',c['closureCount'],'closure;',d['deltaCount'],'delta;',d['newDependencyCount'],'new;',d['explicitInvalidatedPriorCount'],'invalidated;',d['retiredCount'],'retired')
if __name__=='__main__':main()
