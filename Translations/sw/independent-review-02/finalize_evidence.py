"""Materialize independently read review evidence; no authored payload writes."""
import json, hashlib, sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parent))
import review_reader as r

HERE=r.HERE; ROOT=r.ROOT; CYCLE=r.CYCLE
now=datetime.now(timezone.utc).isoformat()
def h(s):return hashlib.sha256(s.encode()).hexdigest()
def save(name,obj):r.save(name,obj)
def jsonl(name,rows):
 (HERE/name).write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in rows))
proposals={
61:('Vigilante: Yafungue zaidi, zaidi. Tumia mikono yako, haya!', 'The object is the player’s eyes (macho, class 6), confirmed by the immediately following ShowPlayerSign EYE. Ifungue uses class 9/4 object agreement instead of ya for these plural eyes. Preserve the hands instruction and impatient repetition.'),
100:('Twins: Asante. Kwa uangalifu, weka mkono chini ya mgongo wake… Hivyo.', 'The Russian instruction places a hand under her back to support the weakened sister. mgongoni places it on/at the back and omits under; mweke can also imply putting her rather than the hand. Preserve the complete thanks, caution and final guiding fragment.'),
220:('Foreigner: (Unatabasamu na kunyooshea kidole tabasamu lako, kisha kumnyooshea kidole mzungumzaji.)', 'The same pointing gesture targets the smile and then the interlocutor. kumwonyesha mzungumzaji means showing the interlocutor something, rather than pointing a finger at him. Preserve the full parenthetical action, actor and gesture order.'),
330:('Alt: Sina tatizo kukuonyesha makwapa yangu.', 'The named object is plural armpits. Approved glossary and prior adjudication use kwapa/makwapa, class 5/6; kwapa zangu gives it class 10 agreement. Use explicit plural makwapa with yangu; preserve the speaker’s lack of objection.'),
390:('Experienced: Naelewa kwamba si jambo la kupendeza kuona makwapa yangu…', 'The explicit plural armpits require makwapa yangu, following approved class 5/6 kwapa/makwapa usage, rather than kwapa zangu. Preserve the ellipsis and the full acknowledgment that the sight is unpleasant.'),
427:('Makwapa yana nywele.', 'The normal-player branch explicitly describes armpits with hair. Kwapa zina uses class 10 agreement with kwapa; the approved plural is makwapa, class 6, requiring yana. Preserve the positive hair finding and leave the adjacent normality statement unchanged.'),
477:('GraveDigger: Kama makwapa yangu yamekutisha, ni bora usiangalie kinachoendelea rohoni mwangu.', 'The subject explicitly names the speaker’s plural armpits, so makwapa yangu yamekutisha is required by the approved class 5/6 noun usage. kwapa zangu zimekutisha incorrectly gives them class 10 agreement. Preserve the whole conditional contrast with turmoil in his soul.'),
743:('Scammer: Fikiria mwenyewe; mtu wa kawaida hawezi kuwa na makwapa ya kutia shaka.', 'The named plural armpits require makwapa ya, not kwapa za, under the approved class 5/6 noun usage. Preserve the normal-person denial and suspicious-sign qualifier in the complete sentence.')
}
findings=[]
for num,(idx,(proposal,why)) in enumerate(proposals.items(),1):
 row=r.delta[idx]; sid=row['stableId'];src=r.source[sid]
 findings.append({'findingId':f'sw-independent-02-{num:04d}','reviewDeltaIndexZeroBased':idx,'stableId':sid,'key':row['key'],'sourceIndex':row.get('sourceIndex'),'authoredPath':row.get('authoredPath'),'source':row['source'],'currentTarget':row['target'],'proposedFullTarget':proposal,'objectiveReason':why,'sourceSha256':h(row['source']),'currentTargetSha256':h(row['target']),'proposedTargetSha256':h(proposal),'compiledConsumers':r.consumers.get(row['key'],[]),'scope':'proposal only; authored inputs unchanged','adjudication':'pending owner-workflow author/context adjudication'})
save('final-findings-02.json',{'schemaVersion':1,'reviewer':'/root/sw_independent_review_02','createdAtUtc':now,'completeAssignedPass':True,'findingGroups':len(findings),'findingUnits':len(findings),'findings':findings})
for key,proposal,why in [
 ('line:FunnyGuy_Ears_094c29c','FunnyGuy: Basi angalia, kwa nini usiangalie.', 'The speaker grants the player permission to look at his ears; ShowSign FunnyGuy EAR immediately follows. nisiangalie changes the rhetorical subject to the speaker (why should I not look), conflicting with the preceding player imperative. usiangalie preserves the player as the examiner.'),
 ('line:Fairytaller_Hands_DontShoot_099439d','Fairytaller: Kwa tahadhari, nitajaribu kuosha mikono yangu mara nyingi zaidi.', 'The scene concerns the speaker’s hands, with a scar on them and an optional dirty-nails branch. kuyaosha refers to class 6 objects, agreeing with neither mikono (class 4) nor kucha (class 10). Explicit kuosha mikono yangu preserves the washing intention in both branches without retaining an incorrect object prefix.')]:
 row=r.keyrows[key];sid=row['stableId'];a=next(x for x in r.allrows if x['stableId']==sid)
 findings.append({'findingId':f'sw-independent-02-{len(findings)+1:04d}','reviewDeltaIndexZeroBased':None,'discoverySurface':'additional full visible context unit in an affected compiled node','stableId':sid,'key':key,'sourceIndex':a['sourceIndex'],'authoredPath':a['artifact'],'source':row['source'],'currentTarget':row['target'],'proposedFullTarget':proposal,'objectiveReason':why,'sourceSha256':h(row['source']),'currentTargetSha256':h(row['target']),'proposedTargetSha256':h(proposal),'compiledConsumers':r.consumers.get(key,[]),'scope':'proposal only; authored inputs unchanged','adjudication':'pending owner-workflow author/context adjudication'})
save('final-findings-02.json',{'schemaVersion':1,'reviewer':'/root/sw_independent_review_02','createdAtUtc':now,'completeAssignedPass':True,'findingGroups':len(findings),'findingUnits':len(findings),'deltaFindingUnits':8,'additionalCompiledContextFindingUnits':2,'findings':findings})
findingids={x['stableId']:x['findingId'] for x in findings}
priorpath=ROOT/'Translations/sw/independent-review-01/final-reviewed-rows-01.jsonl'
prior={x['stableId']:x for x in r.rows(priorpath)}
selected={x['stableId']:x for x in r.delta}
reused=[]
for row in r.rows(CYCLE/'closure-ids-v3.jsonl'):
 sid=row['stableId']
 if sid in selected:continue
 assert sid in prior and prior[sid]['actuallyRead'] and prior[sid]['findingId'] is None
 assert prior[sid]['sourceSha256']==h(r.source[sid]['source']) and prior[sid]['targetSha256']==h(r.targets[sid])
 reused.append({'stableId':sid,'sourceSha256':prior[sid]['sourceSha256'],'targetSha256':prior[sid]['targetSha256'],'priorIndependentEvidence':'Translations/sw/independent-review-01/final-reviewed-rows-01.jsonl','decision':'unchanged applicable prior independent full-unit/context evidence retained'})
jsonl('unchanged-closure-reused-02.jsonl',reused)
selectedkeys={x['key'] for x in r.delta}
readranges=[[0,60],[60,140],[140,220],[220,300],[300,380],[380,470],[470,560],[560,650],[650,740],[740,834]]
contextranges=[[0,50],[50,90],[90,130],[130,165],[165,205],[205,245],[245,285],[285,325],[325,341]]
names=list(dict.fromkeys(n for row in r.delta for n,_,_ in r.consumers.get(row['key'],[])))
context=[];neighborids=set();visibleids=set();outside=[];extraRead=[]
for ni,n in enumerate(names):
 ins=r.nodes[n]; visible=[i for i in ins if i['opcode'] in (2,4) and i['operands'] and i['operands'][0] in r.keyrows]
 pos=[j for j,i in enumerate(visible) if i['operands'][0] in selectedkeys]
 needed={j for p in pos for j in range(max(0,p-1),min(len(visible),p+2))}
 slots=[]
 for j,i in enumerate(visible):
  row=r.keyrows[i['operands'][0]];sid=row['stableId']; visibleids.add(sid)
  if sid in selected:mode='fresh full delta unit read'
  elif j in needed:mode='fresh immediate neighboring full unit read';neighborids.add(sid)
  elif sid in prior and prior[sid]['sourceSha256']==h(row['source']) and prior[sid]['targetSha256']==h(row['target']):mode='unchanged prior independent full-unit/context evidence reused after exact unit and recipe pin verification'
  else:mode='fresh additional full visible context unit read in context-rest batches';extraRead.append({'nodeName':n,'stableId':sid,'key':row['key'],'source':row['source'],'currentTarget':row['target'],'sourceSha256':h(row['source']),'targetSha256':h(row['target']),'actuallyReadFullUnit':True,'findingId':findingids.get(sid),'decision':'changes requested' if sid in findingids else 'retain; no objective issue found in source-target/context comparison'})
  slots.append({'instructionIndex':i['index'],'opcode':i['opcode'],'stableId':sid,'key':row['key'],'source':row['source'],'assembledCurrentTarget':row['target'],'operands':i['operands'][1:],'sourceSha256':h(row['source']),'targetSha256':h(row['target']),'readMode':mode})
 context.append({'nodeIndexZeroBased':ni,'nodeName':n,'compiledProgramSha256':r.program_hash,'orderedVisibleSlots':slots,'completeSerializedInstructions':ins,'presentedControl': 'Commands, option destinations, state/function/branch operations read in context batches; internal visited counters omitted from presentation. Explicit-schema full instructions preserved here.','runtimeQualification':'serialized compiled consumers, not a VM execution or proof of reachability'})
jsonl('compiled-context-reviewed-02.jsonl',context)
jsonl('supplementary-context-reviewed-02.jsonl',extraRead)
reviewed=[]
for idx,row in enumerate(r.delta):
 sid=row['stableId'];reviewed.append({'reviewDeltaIndexZeroBased':idx,'stableId':sid,'key':row['key'],'sourceIndex':row.get('sourceIndex'),'authoredPath':row.get('authoredPath'),'source':row['source'],'currentTarget':row['target'],'sourceSha256':h(row['source']),'targetSha256':h(row['target']),'reasons':row['reasons'],'actuallyReadFullUnit':True,'readBatchHalfOpen':next(x for x in readranges if x[0]<=idx<x[1]),'compiledConsumers':r.consumers.get(row['key'],[]),'decision':'changes requested' if sid in findingids else 'retain; no objective issue found in the compared full unit and available context','findingId':findingids.get(sid),'checksApplied':['full factual meaning including unchanged sentences','voice and register','approved glossary and character facts','participant count, noun class and pronoun antecedents','repetition/concept dependencies','assembled serialized consumers and branch order where present','spoiler timing','protected syntax'],'consumerReachability':'not claimed','glossarySha256':'95fe1a773cf228dfabad22f97b085694a725bf5d3e2d83e0a07f8fda316beeb3'})
jsonl('final-reviewed-rows-02.jsonl',reviewed)
catpath=ROOT/'Translations/sw/semantic-correction-cycle-01/mandatory-regression-catalog-v2.json'
cat=json.loads(catpath.read_text());regrows=[];cats=[]
for category,ref in cat['categories'].items():
 assert r.sha(ROOT/ref['path'])==ref['sha256']
 ids=json.loads((ROOT/ref['path']).read_text())['stableIds'];fresh=0;reuse=0
 for sid in ids:
  src=r.source[sid];target=r.targets[sid]
  if sid in selected:mode='fresh delta full-unit review';fresh+=1
  else:
   assert sid in prior and prior[sid]['actuallyRead']
   assert prior[sid]['sourceSha256']==h(src['source']) and prior[sid]['targetSha256']==h(target)
   assert prior[sid]['findingId'] is None, sid
   mode='exact unchanged source/target and compiled/component/recipe pins; prior independent evidence reused';reuse+=1
  regrows.append({'stableId':sid,'category':category,'sourceSha256':h(src['source']),'targetSha256':h(target),'reviewMode':mode,'findingId':findingids.get(sid),'decision':'changes requested' if sid in findingids else 'retain; no objective issue found'})
 cats.append({'category':category,**ref,'freshFullUnitReview':fresh,'reusedExactPriorIndependentReview':reuse,'currentObjectiveFindingUnits':sum(x in findingids for x in ids),'result':'changes requested' if any(x in findingids for x in ids) else 'no objective issue found in compared/reused text evidence'})
jsonl('mandatory-regression-reviewed-02.jsonl',regrows)
save('mandatory-regression-result-02.json',{'catalogPath':str(catpath.relative_to(ROOT)),'catalogSha256':r.sha(catpath),'uniqueIdsCovered':len({x['stableId'] for x in regrows}),'missingIds':[],'categories':cats,'reusePriorFinalReviewedRows':{'path':str(priorpath.relative_to(ROOT)),'sha256':r.sha(priorpath)},'fullCorpusStructuralGate':'unchanged verified structural-validation.json and preserve-exact-validation.json covering 187 artifacts / 16538 units; applicability checked against actual final artifact and sidecar hashes','runtime':'not-run-per-owner','excluded':'images/textures; RTL not applicable to Swahili Latin','semanticScope':'mandatory categories checked as fresh affected full units plus exact applicable independently reviewed prior evidence; validator alone is not a semantic review'})
# Current serialized final consumers must equal planned assembled replacements.
preflight=r.rows(CYCLE/'assembled-consumer-preflight.jsonl');matched=0;dynamic=[]
for node in preflight:
 assert node['compiledProgramSha256']==r.program_hash
 for line in node['orderedVisibleLines']:
  assert r.targets[line['stableId']]==line['assembledTargetAfter']
  ins=r.nodes[node['nodeName']][line['instructionIndex']]
  assert ins['opcode']==line['opcode'] and ins['operands'][0]==line['key']
  if line['opcode']==4:assert ins['operands'][1:]==line['optionOperands']
  elif ins['operands'][1:]!=[0.0]:
   assert node['nodeName']=='FortuneTeller_Asking_2' and line['instructionIndex']==30
   assert ins['operands'][1:]==[1.0]
   producer=r.nodes[node['nodeName']][27:30]
   assert [(x['opcode'],x['operands']) for x in producer]==[(6,['Extrasens']),(7,[1.0]),(12,['GetPhoneNumber'])]
   token='⟦GetPhoneNumber("Extrasens")⟧'
   dynamic.append({'nodeName':node['nodeName'],'instructionIndex':30,'key':line['key'],'actualProducerInstructions':producer,'sourceAssembledSymbolically':line['source'].replace('{0}',token),'currentTargetAssembledSymbolically':line['assembledTargetAfter'].replace('{0}',token),'placeholderExact':'{0}','runtimeValue':'not executed; concrete number depends on live phone-number state, which is outside this owner-prohibited runtime review'})
  matched+=1
save('assembled-consumer-check-02.json',{'compiledProgramSha256':r.program_hash,'preflight':{'path':str((CYCLE/'assembled-consumer-preflight.jsonl').relative_to(ROOT)),'sha256':r.sha(CYCLE/'assembled-consumer-preflight.jsonl')},'nodes':len(preflight),'slotsCompared':matched,'actualFinalTargetsEqualPlannedAssembledTargets':True,'dynamicSlots':dynamic,'optionOperandEquality':True,'nonDialogueCorrectedUnit':'UI consumable_kombucha_narrativeDescription full unit reread; unchanged managed binding/dependency component and prior independent surface evidence verified','dynamicBindingScope':'zero-substitution dialogue lines/options compared against compiled slots; one actual GetPhoneNumber stack producer and symbolic assembled source/current target compared; unchanged other UI/title/input/dynamic/static consumers reuse verified component and prior independent surface evidence','runtime':'not-run-per-owner'})
save('read-evidence-02.json',{'reviewer':'/root/sw_independent_review_02','createdAtUtc':now,'deltaSha256':r.sha(CYCLE/'review-delta-v3.jsonl'),'freshFullDeltaUnitsRead':len(r.delta),'fullUnitReadBatchesHalfOpen':readranges,'contextNodeReadBatchesHalfOpen':contextranges,'affectedCompiledNodes':len(names),'visibleSlotOccurrences':sum(len(x['orderedVisibleSlots']) for x in context),'uniqueVisibleIds':len(visibleids),'freshImmediateNeighborUnits':len(neighborids),'serializedContextUnitsNotFreshlyReadOrPriorReusable':sorted(set(outside)),'dialogueUnitsWithoutCompiledConsumer':[x['stableId'] for x in r.delta if x['collection']=='Dialogs' and not r.consumers.get(x['key'])],'contextAdditionalFullNodesActuallyRead':['Vigilante_Entrance_2_Eyes','Twins_Entrance_Occupied_YesLet','Foreigner_Asking_5','Raskolnikov_Ears','Widow_Hands','Widow_Asking_1','Widow_Asking_4_3','Widow_Photo','Widow_Hands_DontShoot','Alt_Armpit','Experienced_Armpit_Gun','selfcheck_armpit','GraveDigger_Armpit_Gun','Scammer_Armpit_Gun'],'allApplied85CorrectionsFullUnitSemanticResult':'no objective issue found; unchanged sentences included','notClaimed':'fresh reread of all 5948 closure IDs or all 16538 corpus IDs; runtime reachability/layout/font/gameplay acceptance'})
read=json.loads((HERE/'read-evidence-02.json').read_text())
read.update({'additionalFreshVisibleContextUnits':len(extraRead),'additionalContextReadBatchesHalfOpen':[[0,140],[140,280],[280,420],[420,536]],'unchangedClosureUnitsIndividuallyPinnedAndReused':len(reused)})
read['contextAdditionalFullNodesActuallyRead']+=['FortuneTeller_Asking_2','Fairytaller_Hands_DontShoot','FunnyGuy_Ears','Bestson_Hands','Dude_Armpit']
save('read-evidence-02.json',read)
save('resolved-decisions-02.json',{'retained':[{'key':'line:Widow_Hands_02f2db4','decision':'retain walikataa','reason':'The omitted Russian plural subject can refer to the people who refused to save the husband; Widow_Asking_4_3 hospital/KHD account, Widow_Photo and Widow_Hands_DontShoot support that reading. Replacing with ilikataa would force unestablished personification of hands.'},{'scope':'Russian Вы to single player','decision':'retain respectful plural when already used','reason':'Exact prior independent final adjudication permits respectful plural; no singular-only approved policy.'},{'scope':'inanimate plural possessor e.g. galaksi','decision':'retain -ake where permissible','reason':'Exact prior adjudication establishes permitted singular possessive construction for inanimate possessors; not an objective agreement error.'},{'scope':'hair shaving ellipsis','decision':'retain implicit nywele antecedents where scene supports them','reason':'Do not force a named-body-part rewrite onto zi- forms that can refer to hair.'},{'key':'line:Raskolnikov_Ears_0a1ab58','decision':'retain','reason':'The fragment can naturally mean hearing even what is not supposed to be heard. A temporal expansion is a preference rather than an established factual correction.'}], 'standardKwapaUsage':'Prior final-adjudication-01.json established kwapa/makwapa li/ya and accepted Makwapa. Ya kawaida. Tu.; approved hairless-armpits/armpit-fungus glossary entries use makwapa. This batch fixes explicit erroneous z agreement only; it does not replace every colloquial standalone kwapa occurrence.'})
baseline=json.loads((HERE/'input-verification-01.json').read_text())
for ref in baseline['hashChecks']:assert r.sha(Path(ref['path']))==ref['sha256'],ref['path']
support=json.loads((HERE/'prior-support-applicability-02.json').read_text())
for ref in support['verifiedUnchangedSupportFiles']:
 p=Path(ref['path']);p=p if p.is_absolute() else ROOT/p
 assert r.sha(p)==ref['sha256'],str(p)
save('final-unchanged-hash-verification-02.json',{'checkedAtUtc':now,'baseline':{'path':'Translations/sw/independent-review-02/input-verification-01.json','sha256':r.sha(HERE/'input-verification-01.json')},'checkedReferences':len(baseline['hashChecks']),'additionalUnchangedPriorSupportReferences':len(support['verifiedUnchangedSupportFiles']),'allUnchanged':True,'finalPayloadManifestSha256':r.sha(CYCLE/'final-payload-manifest.json'),'sourceGlossaryAndRecipeApplicability':'unchanged','mutablePriorCorrectionProgress':'intentionally excluded historical mutable progress pin; not used for prior evidence applicability','authoredMutation':'none performed by reviewer'})
save('token-telemetry-02.json',{'reviewer':'/root/sw_independent_review_02','model':'GPT-6; exact runtime model identifier not exposed in this session','reasoning':'unknown','inputTokens':None,'cachedInputTokens':None,'outputTokens':None,'totalTokens':None,'telemetryStatus':'unknown; no per-request/session token telemetry tool exposed to reviewer. Parent coordinator may supplement actual session-record telemetry. No text-length estimate used.','measurementCutoff':now,'reportingTail':'not measured here','descendantAgents':'none'})
print(json.dumps({'findings':len(findings),'mandatoryCategories':cats,'context':{'nodes':len(names),'outside':len(set(outside))},'assembledSlots':matched},ensure_ascii=False,indent=2))
