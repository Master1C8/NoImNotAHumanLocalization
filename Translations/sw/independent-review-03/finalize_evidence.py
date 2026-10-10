"""Record actual cycle03 independent reads and deterministic applicability checks."""
import hashlib,importlib.util,json,struct,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;CYCLE=ROOT/'Translations/sw/semantic-correction-cycle-03'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def shat(t):return hashlib.sha256(t.encode()).hexdigest()
def rows(p):return [json.loads(x) for x in p.read_text().splitlines()]
def save(name,d):
 p=HERE/name;assert not p.exists(),p;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def save_rows(name,d):
 p=HERE/name;assert not p.exists(),p;p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in d))
spec=importlib.util.spec_from_file_location('review03',HERE/'review_reader.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
checks={}
def checkref(d):
 if isinstance(d,dict):
  if 'path' in d and 'sha256' in d:
   p=Path(d['path']);p=p if p.is_absolute() else ROOT/p
   assert sha(p)==d['sha256'],p;checks[str(p)]={'path':str(p),'sha256':sha(p)}
  for v in d.values():checkref(v)
 elif isinstance(d,list):
  for v in d:checkref(v)
manifest=json.loads((CYCLE/'dependency-closure.json').read_text());checkref(manifest)
inputs=json.loads((CYCLE/'inputs.json').read_text());checkref(inputs)
# Prior evidence itself is immutable. Old authored containing-file hashes are
# historical; current files are rebound below, and retained judgments use unit hashes.
for n in ['01','02']:
 m=json.loads((ROOT/f'Translations/sw/independent-review-{n}/evidence-manifest-{n}.json').read_text());checkref(m['files'])
support=json.loads((ROOT/'Translations/sw/independent-review-02/prior-support-applicability-02.json').read_text());checkref(support['verifiedUnchangedSupportFiles'])
app=json.loads((ROOT/'outputs/yarn-operand-applicability-v1.json').read_text())
for p,h in app['recipeHashes'].items():checkref({'path':p,'sha256':h})
assert app['compiledProgramSha256']==r.program_hash==manifest['compiledProgramSha256']
# Decode separately by the IL-proved field/wire pair; compare complete program.
d=r.p.d
def actual_operand(raw):
 fs=list(d.fields(raw));assert len(fs)==1
 f,w,v=fs[0]
 if (f,w)==(1,2):return v.decode()
 if (f,w)==(2,0):return bool(v)
 if (f,w)==(3,5):return struct.unpack('<f',v)[0]
 raise ValueError(fs)
d.operand=actual_operand;explicit,ph=d.load();assert explicit==r.nodes and ph==r.program_hash
payload=json.loads((CYCLE/'final-payload-manifest.json').read_text());actual={}
guids={'Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','UI':'0cbd8a7a4f543344bb95659de87f67a5','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'}
for a in payload['artifacts']:
 for pk,hk in [('artifact','artifactSha256'),('sidecar','sidecarSha256')]:checkref({'path':a[pk],'sha256':a[hk]})
 b=json.loads((ROOT/a['artifact']).read_text());assert b['locale']=='sw'
 for e in b['entries']:
  sid=e.get('stableId') or f"string:{guids[b['collection']]}:{e['id']}"
  assert sid not in actual;actual[sid]=e['target']
assert len(actual)==16538 and set(actual)==set(r.current)
assert all(actual[sid]==x['target'] for sid,x in r.current.items())
for x in r.delta:assert x['source']==r.source[x['stableId']]['source'] and x['target']==actual[x['stableId']]
# Deterministic full exact contract against actual current authored fields.
sys.path.insert(0,str(ROOT/'Scripts'));import preserve_exact
exact_out=HERE/'preserve-exact-current-03.json';preserve_exact.validate('sw',exact_out)
# Reuse prior independently read closure units only on exact per-unit hashes.
prior01={x['stableId']:x for x in rows(ROOT/'Translations/sw/independent-review-01/final-reviewed-rows-01.jsonl')}
prior02={x['stableId']:x for x in rows(ROOT/'Translations/sw/independent-review-02/final-reviewed-rows-02.jsonl')}
prior_reused={x['stableId']:x for x in rows(ROOT/'Translations/sw/independent-review-02/unchanged-closure-reused-02.jsonl')}
delta_ids={x['stableId'] for x in r.delta};reused=[]
for x in rows(CYCLE/'closure-ids.jsonl'):
 sid=x['stableId']
 if sid in delta_ids:continue
 e=prior02.get(sid) or prior_reused.get(sid);assert e is not None,sid
 assert e['sourceSha256']==shat(x['source']) and e['targetSha256']==shat(actual[sid]),sid
 if sid in prior_reused:
  old=prior01[sid];assert e['sourceSha256']==old['sourceSha256'] and e['targetSha256']==old['targetSha256'];assert not old.get('findingId')
 else:assert not e.get('findingId')
 reused.append({'stableId':sid,'sourceSha256':shat(x['source']),'targetSha256':shat(actual[sid]),'priorIndependentEvidence':f"Translations/sw/independent-review-{'02' if sid in prior02 else '01'}/final-reviewed-rows-{'02' if sid in prior02 else '01'}.jsonl",'decision':'unchanged applicable prior independent unit/context evidence retained'})
assert len(reused)==5935;save_rows('unchanged-closure-reused-03.jsonl',reused)
read=[]
for i,x in enumerate(r.delta):
 read.append(dict(x,reviewDeltaIndexZeroBased=i,currentTarget=x['target'],sourceSha256=shat(x['source']),targetSha256=shat(x['target']),actuallyReadFullUnit=True,readBatchHalfOpen=([0,25] if i<25 else [25,50] if i<50 else [50,69]),compiledConsumers=r.consumers[x['key']],decision='retain; no objective issue found in complete unit and assembled consumer context',findingId=None,checksApplied=['all facts and unchanged sentences','noun class and actual pronoun antecedents','character evidence and agency','voice/register','glossary inflection','branch order and option meaning','protected exact values','spoiler timing']))
save_rows('final-reviewed-rows-03.jsonl',read)
# All visible units and controls in these 26 nodes were displayed and read.
names=list(dict.fromkeys(n for x in r.delta for n,_,_,_ in r.consumers[x['key']]))
context=[];extra=set();slots=0;dynamic=[]
for n in names:
 visible=[]
 for ins in r.nodes[n]:
  a=ins['operands'];op=ins['opcode']
  if op in (2,4) and a and a[0] in r.keyrows:
   x=r.keyrows[a[0]];sid=x['stableId'];slots+=1
   if sid not in delta_ids:extra.add(sid)
   assembled_source=x['source'];assembled_target=actual[sid]
   if op==2 and a[1]!=0.0:
    assert n=='tv_11_necessary' and ins['index']==10 and a[1]==1.0
    symbol='⟦GetPhoneNumber("FEMA")⟧';assembled_source=assembled_source.replace('{0}',symbol);assembled_target=assembled_target.replace('{0}',symbol)
    dynamic.append({'node':n,'instructionIndex':10,'actualProducerInstructions':r.nodes[n][7:10],'symbolicSource':assembled_source,'symbolicCurrentTarget':assembled_target,'liveValue':'not executed'})
   visible.append({'stableId':sid,'key':x['key'],'instructionIndex':ins['index'],'opcode':op,'operands':a[1:],'source':x['source'],'currentTarget':actual[sid],'sourceSha256':shat(x['source']),'targetSha256':shat(actual[sid]),'assembledSource':assembled_source,'assembledCurrentTarget':assembled_target,'readMode':'fresh full unit in exact delta' if sid in delta_ids else 'fresh complete compiled-node support context','decision':'retain; no objective issue found'})
 context.append({'nodeName':n,'compiledProgramSha256':r.program_hash,'orderedVisibleSlots':visible,'allInstructions':r.nodes[n],'branchOrderInspected':True,'reachability':'not claimed'})
save_rows('compiled-context-reviewed-03.jsonl',context)
# Verify author's corrected-node planned assembly against actual compiled slots.
preflight=rows(CYCLE/'assembled-consumer-preflight.jsonl');preflight_slots=0
for node in preflight:
 for s in node['visible']:
  ins=r.nodes[node['node']][s['instructionIndex']];assert ins['opcode']==s['opcode'] and ins['operands'][0]==s['key']
  assert s['plannedTarget']==actual[s['stableId']] and s['source']==r.source[s['stableId']]['source']
  assert s['optionOperands']==(ins['operands'][1:] if ins['opcode']==4 else [])
  preflight_slots+=1
save('assembled-consumer-check-03.json',{'programSha256':r.program_hash,'deltaNodes':len(names),'freshVisibleSlots':slots,'additionalFreshContextUnits':len(extra),'correctedPreflightNodes':len(preflight),'correctedPreflightSlots':preflight_slots,'actualTargetsAndOptionOperandsEqualPreflight':True,'deltaSubstitutionSlots':0,'freshDynamicContext':dynamic,'unchangedDynamicSupport':'prior reviewed FortuneTeller GetPhoneNumber Extrasens slot source/target and complete compiled program unchanged','runtime':'not-run-per-owner'})
cat_path=ROOT/'Translations/sw/semantic-correction-cycle-01/mandatory-regression-catalog-v2.json';cat=json.loads(cat_path.read_text())
prior_reg={(x['category'],x['stableId']):x for x in rows(ROOT/'Translations/sw/independent-review-02/mandatory-regression-reviewed-02.jsonl')}
reg=[];categories=[];union=set()
for name,pin in cat['categories'].items():
 checkref(pin);ids=json.loads((ROOT/pin['path']).read_text())['stableIds'];fresh=0
 for sid in ids:
  union.add(sid);e=prior_reg[(name,sid)]
  if sid not in delta_ids:assert e['sourceSha256']==shat(r.source[sid]['source']) and e['targetSha256']==shat(actual[sid]) and not e.get('findingId'),sid
  else:fresh+=1
  reg.append({'stableId':sid,'category':name,'sourceSha256':shat(r.source[sid]['source']),'targetSha256':shat(actual[sid]),'reviewMode':'fresh exact delta unit/consumer read' if sid in delta_ids else 'exact unchanged prior independent category/consumer evidence reused','decision':'retain; no objective issue found','findingId':None})
 categories.append({'category':name,**pin,'freshDeltaRead':fresh,'exactPriorIndependentReuse':len(ids)-fresh,'result':'clean applicable text evidence'})
assert len(union)==1592;save_rows('mandatory-regression-reviewed-03.jsonl',reg)
save('mandatory-regression-result-03.json',{'catalogPath':str(cat_path.relative_to(ROOT)),'catalogSha256':sha(cat_path),'uniqueIdsCovered':1592,'missingIds':[],'categories':categories,'contextReadSeparateFromConservativeReuseCounts':True,'excluded':['images/textures per owner','RTL/bidi for Swahili Latin'],'runtime':'not-run-per-owner','layoutFontBuildPackaging':'unverified; no runtime or visual claim'})
save('resolved-decisions-03.json',{'miwani':'Retain class4 i agreement. Glasses-only 17 remedial support reads are not a correction dependency; no invalidated glossary evidence. Prior false-positive dismissal read and upheld.','kwapa':'Retain accepted standalone colloquial kwapa; explicitly plural corrected named armpits use makwapa and class6 ya agreement. No blind global replacement.','hairAntecedents':{'Dude_Armpit':'Zimenyolewa refers recoverably to nywele as the following explicit armpit-hair question and continuation establish; implicit hair forms are not forced into makwapa agreement.','Dude_Armpit_DontShoot':'Zinatusumbua and tunazo retain hair as subject/object, following the explicit nywele question.','Anger_Armpit':'ninazinyoa refers to hair, explicitly explained in the next unit; keep it.'},'Fairytaller':'Explicit kuosha mikono yangu preserves washing hands and nails across normal/imposter branches; no class6 object marker remains.','Couple':'Wanatoka chini ya ardhi refers to Guests, not nails; easy brain access restored as speculation in non-imposter branch only.','Foreigner':'Visible deliberate keyboard-layout literals remain exact under preservation contract; pointing smile then interlocutor is retained.','Vigilante':'Yafungue follows macho and actual ShowPlayerSign EYE; shared consumer evidence establishes correct eyes imperative.','Twins':'Hand under weakened sister back; parent loss, sister agency and dialogue order retained.','priorResolvedDecisions02Sha256':sha(ROOT/'Translations/sw/independent-review-02/resolved-decisions-02.json')})
save('read-evidence-03.json',{'reviewer':'/root/sw_independent_review_03','gameVersion':'1.3.19','source':'ru','target':'sw','deltaUnitsRead':69,'readRangesHalfOpen':[[0,25],[25,50],[50,69]],'compiledNodeRangesHalfOpen':[[0,6],[6,13],[13,20],[20,26]],'compiledNodesRead':26,'visibleSlotsRead':slots,'additionalContextUniqueUnitsRead':len(extra),'unchangedClosureUnitJudgmentsReused':len(reused),'fullCorpusNotAutomaticallyReread':True,'findings':0,'cleanCorrections':11})
save('input-verification-03.json',{'reviewer':'/root/sw_independent_review_03','hashChecks':list(checks.values()),'setCounts':{'priorClosure':5948,'currentClosure':6004,'changed':11,'new':56,'invalidated':4,'retired':0,'delta':69,'overlap':2},'allCurrentAuthoredValuesMatchProjectedTargets':16538,'explicitOperandSchema':{'1:2':'string','2:0':'bool','3:5':'float'},'completeDecodedProgramEquality':{'nodes':len(explicit),'instructions':sum(map(len,explicit.values())),'result':'passed'},'programSha256':r.program_hash,'authorRecipeReproduction':'passed under denied-write guard; no historical artifact mutation','priorEvidenceApplicability':'prior immutable evidence and support hashes checked, unchanged units rebound by unit hashes; current payload/sidecars checked against cycle03 manifest','priorMutableProgress':'pinned at start; not relied upon for per-unit semantic reuse'})
save('final-findings-03.json',{'schemaVersion':1,'reviewer':'/root/sw_independent_review_03','locale':'sw','gameVersion':'1.3.19','verdict':'clean','deltaUnits':69,'fullUnitFindingCount':0,'findings':[],'payloadManifestSha256':sha(CYCLE/'final-payload-manifest.json'),'closureManifestSha256':sha(CYCLE/'dependency-closure.json'),'reviewDeltaSha256':sha(CYCLE/'review-delta.jsonl'),'releaseAcceptance':'not conferred'})
# Actual exposed counters are unavailable in the reviewer API; parent may supplement.
save('token-telemetry-03.json',{'agent':'/root/sw_independent_review_03','model':'GPT-6','runtimeModelId':'not exposed','reasoningSetting':'not exposed','inputTokens':None,'cachedInputTokens':None,'outputTokens':None,'reasoningTokens':None,'totalTokens':None,'status':'unknown; no text-length or row-count estimate substituted','descendantAgents':0,'measurementCutoffUtc':datetime.now(timezone.utc).isoformat(),'reportingTail':'final report generation, final hash scan and final chat reply not measurable by this record','coordinatorAccounting':'parent coordinator responsibility; reviewer does not infer orchestration totals'})
print(json.dumps({'hashReferences':len(checks),'visibleSlots':slots,'extraContextUniqueUnits':len(extra),'preflightNodes':len(preflight),'preflightSlots':preflight_slots,'regressionCategories':categories,'verdict':'clean'},indent=2))
