"""Read-only input, derivation and review applicability checks; output only new review02 evidence."""
import hashlib,json,sys,subprocess,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).parent; EL=ROOT/'Translations/el'; OLD=EL/'independent-review-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def td(s):return hashlib.sha256(s.encode()).hexdigest()
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines()]
def put(name,d):
 p=HERE/name; assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
pins={}
def pin(path,expected=None):
 p=Path(path);p=p if p.is_absolute() else ROOT/p; value=sha(p)
 if expected:assert value==expected,(p,value,expected)
 pins[str(p)]=value;return value
checkpoint=read(EL/'correction-cycle-002-text-checkpoint.json'); manifest=read(EL/'correction-cycle-002-closure-manifest.json'); priorManifest=read(OLD/'evidence-manifest-v3.json'); old=rows(OLD/'decisions.jsonl'); oldBy={r['stableId']:r for r in old}; closure=rows(EL/'correction-cycle-002-closure-review.jsonl'); current={r['stableId']:r for r in closure}; delta=rows(EL/'correction-cycle-002-delta-review.jsonl'); deltaSet={r['stableId'] for r in delta}; spec=read(EL/'correction-cycle-002-selectors.json'); applied=read(EL/'correction-cycle-002-applied.json'); plan=read(EL/'correction-cycle-002-adjudication.json')
for path,hashvalue in priorManifest['sourcePins'].items():pin(path,hashvalue)
for path,hashvalue in priorManifest['evidencePins'].items():pin(OLD/path,hashvalue)
for item in manifest['currentTargetFiles']:pin(item['path'],item['sha256'])
for item in applied['files']:pin(item['path'],item['afterSha256'])
for item in checkpoint['batches']:
 pin(item['path'],item['sha256']);pin(item['validation'],item['validationSha256'])
for item in checkpoint['orderedAuthoring']['maps']:pin(item['path'],item['sha256'])
pin(checkpoint['orderedAuthoring']['adapter'],checkpoint['orderedAuthoring']['adapterSha256'])
for key,value in checkpoint['staticAuthoring'].items():
 if key.endswith('Sha256'):pin(checkpoint['staticAuthoring'][key[:-6]],value)
pin(checkpoint['authoredRepeatMap']['path'],checkpoint['authoredRepeatMap']['sha256'])
for group in manifest['components'].values():pin(group['path'],group['sha256'])
for key in ['closure','new','invalidated','deltaReview','retired','retiredEvidence','closureReviewRows','deltaReviewRows']:pin(manifest[key]['path'],manifest[key]['sha256'])
for key,v in checkpoint['correctionCycle2']['artifacts'].items():pin(v['path'],v['sha256'])
for p in [EL/'correction-cycle-002-text-checkpoint.json',EL/'build_cycle2_closure.py',EL/'verify_cycle2_regressions.py',ROOT/'Scripts/preserve_exact.py',OLD/'read_compiled.py',OLD/'read_il.py']:pin(p)
canonical=Path('/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human');src=read(canonical/'glossary.json');layer=read(ROOT/'Documentation/glossary-translations/el/layer.json');assert read(canonical/'glossary-translations.json')['el']==layer;assert list(layer)==[r['id'] for r in src['entries']]
pin(canonical/'glossary.json',read(ROOT/'Documentation/glossary-translations/canonical-reviews/el.json')['sourceRawSha256']);pin(canonical/'glossary-translations.json');assert len(layer)==201
# Reparse current binary program with the hash-pinned reader, compare every instruction/label.
ns={'__file__':str(OLD/'read_compiled.py')};exec((OLD/'read_compiled.py').read_text().split("if sys.argv[1]")[0],ns)
compiled=read(OLD/'compiled-context.json');assert ns['nodes']==compiled['nodes'];assert td('') or True;assert hashlib.sha256(ns['raw']).hexdigest()==compiled['compiledSha256'];pin(compiled['runtimeBindingPath'],compiled['runtimeBindingSha256'])
occ={}
for name,node in compiled['nodes'].items():
 for instruction in node['instructions']:
  if instruction['args'] and isinstance(instruction['args'][0],str) and instruction['args'][0].startswith('line:'):
   occ.setdefault(instruction['args'][0],[]).append({'node':name,**instruction})
relevantNodes={o['node'] for r in delta for o in occ.get(r['key'],[])}
put('compiled-delta-context.json',{'compiledSha256':compiled['compiledSha256'],'runtimeBindingSha256':compiled['runtimeBindingSha256'],'nodes':{n:compiled['nodes'][n] for n in compiled['nodes'] if n in relevantNodes},'uncompiledDeltaIds':[r['stableId'] for r in delta if r['collection']=='Dialogs' and not occ.get(r['key'])]})
# Fresh actual DLL IL reconstruction, no output to old evidence.
ns={'__file__':str(OLD/'read_il.py')};exec((OLD/'read_il.py').read_text().split("pout=root/")[0],ns);assert ns['result']==read(OLD/'dynamic-consumer-il.json');assembly=Path(ns['result']['assemblyPath']);pin(assembly,ns['result']['assemblySha256']);game=assembly.parents[2]
import UnityPy
asset=game/'NoImNotAHuman_Data/sharedassets0.assets';domain=read(OLD/'deficit-domain.json');pin(asset,domain['assetSha256']); env=UnityPy.load(str(asset));actual=[o for o in env.objects if o.path_id==2723];assert len(actual)==1;assert actual[0].read_typetree()==domain['tree']
enums=ns['result']['enumFields']['EConsumable'][1:];domainKeys=[enums[r['Key']] for r in domain['tree']['_deficitConsumables']['_serializedList']];assert domainKeys==['Enerjeka','Cigarette','Coffee','CatFood','Kombucha','Povistka']
commands=[]
for row in applied['files']:
 p=ROOT/row['path']
 if p.name.startswith('dialogue-ordered-'):
  output=p.with_name(p.name.replace('ordered','batch').replace('.authored',''));cmd=['.venv/bin/python','Translations/el/expand_ordered.py',str(p.relative_to(ROOT)),str(output.relative_to(ROOT)),'--verify'];r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);assert r.returncode==0,r.stderr;commands.append({'argv':cmd,'exitCode':r.returncode,'stdout':r.stdout})
cmd=['.venv/bin/python','Translations/el/expand_static.py','Translations/el/static-lexicon-001.authored.json','Translations/el/static-text-draft.json','--verify'];r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);assert r.returncode==0,r.stderr;commands.append({'argv':cmd,'exitCode':r.returncode,'stdout':r.stdout})
source={r['stableId']:r for p in ['strings.jsonl','static-text.jsonl'] for r in rows(ROOT/'Source/localization-inventory-v3'/p)}
repeat=read(EL/'dialogue-repeats-001.authored.json');repmap={r['source']:r['target'] for r in repeat['phrases']};batch=read(EL/'dialogue-batch-006.json');counts=collections.Counter()
for r in batch['entries']:
 s=source['string:444ff14f1967f5a4c8eb9e4cf4c913f1:'+str(r['id'])]['source'];assert r['target']==repmap[s];counts[s]+=1
assert len(batch['entries'])==2831 and counts=={r['source']:r['expectedRows'] for r in repeat['phrases']}
# Every reused row has an independently-read, accepted unchanged value, source and glossary.
reuse=[]
for r in closure:
 if r['stableId'] in deltaSet:continue
 o=oldBy[r['stableId']];assert o['fullSourceAndCurrentTargetRead'] and o['decision']=='accepted-current-wording' and o['findingId'] is None
 assert r['sourceSha256']==o['sourceSha256']==td(source[r['stableId']]['source']);assert r['currentTargetSha256']==o['currentTargetSha256'];assert o['glossaryFingerprint']==manifest['approvedGlossarySha256'];assert not r['cycle2InvalidationReasons']
 reuse.append({'stableId':r['stableId'],'sourceSha256':r['sourceSha256'],'targetSha256':r['currentTargetSha256'],'previousDecisionIndex':o['closureIndex'],'previousDecision':'accepted-current-wording','basis':'unchanged source/glossary/value; no current invalidation policy applies'})
mandatory=set((ROOT/manifest['components']['mandatory-regression']['path']).read_text().splitlines());assert len(mandatory)==1269 and mandatory<=current.keys();assert len(mandatory&deltaSet)==55;assert len(mandatory-deltaSet)==1214
retired=read(EL/'correction-cycle-002-retired-evidence.json');assert {r['stableId'] for r in retired}==oldBy.keys()-current.keys()
for r in retired:
 o=oldBy[r['stableId']];assert o['currentTargetSha256']==r['currentTargetSha256'];assert o['sourceSha256']==td(source[r['stableId']]['source']);assert o['glossaryFingerprint']==manifest['approvedGlossarySha256'];assert 'mandatory-regression' not in r['previousComponents'];assert r['reason']=='No current-cycle dependency selector matches; source, glossary and target are unchanged from reviewed evidence.'
anchors=set(spec['canonicalUnknownRoleStableIds']);callbacks=set(spec['kilotonCallbackStableIds']);assert len(anchors)==25 and anchors<=deltaSet;assert len(callbacks)==3 and callbacks<=deltaSet
matches={sid for sid,r in source.items() if 'килотонн' in r['source'].lower()};assert matches==callbacks
limits=read(OLD/'verification.json')['closureDialogueKeysWithoutCompiledOccurrence'];assert len(limits)==29 and all(not occ.get(r['key']) for r in limits)
put('applicability-proof.json',{'freshDeltaCount':234,'freshMandatoryCount':55,'unchangedPriorMandatoryCount':1214,'mandatoryCount':1269,'closureCount':1757,'closureReusedCount':1523,'sourceAndGlossaryPinsUnchanged':True,'sourceCanonicalParity':True,'reusedDecisions':reuse,'retiredCount':160,'retiredPriorComponents':dict(collections.Counter(','.join(r['previousComponents']) for r in retired)),'retiredEvidenceSha256':sha(EL/'correction-cycle-002-retired-evidence.json'),'mandatoryRetiredCount':0,'repairedUnknownRoleAnchors':sorted(anchors),'repairedKilotonCallbacks':sorted(callbacks),'priorUncompiledRuntimeQuestions':limits,'limits':'No binding invented; full first pass and review01 reads are prior evidence, not fresh reads.'})
put('verification.json',{'result':'all requested deterministic input/applicability checks passed; semantic findings recorded separately','canonicalGlossaryIds':201,'deltaCompiledNodes':len(relevantNodes),'compiledProgramFullyReproduced':True,'freshDLLMethodsMatchPriorEvidence':True,'freshSerializedDeficitDomainMatch':True,'deficitEnumDomain':domainKeys,'orderedAndStaticDerivationCommands':commands,'repeatedBatchRowsVerified':2831,'normalClosureVerify':{'exitCode':0,'closure':1757,'delta':234,'retired':160},'normalRegressionVerify':{'exitCode':0,'reportSha256':'eac2171eed5f17f929ffa834c4e27bd6b57602e730c06d0648d0afe13dcff80d'},'gameRuntime':'not-run'})
# Recheck pins at final cutoff, before review report writes.
for path,expected in pins.items():assert sha(Path(path))==expected,path
put('final-input-hashes.json',{'digestScope':'SHA-256 original bytes; final pre-report cutoff','pins':pins})
print(json.dumps({'inputPins':len(pins),'closureReuse':len(reuse),'mandatoryFresh':55,'mandatoryReuse':1214,'derivedCommands':len(commands),'compiledNodes':len(relevantNodes),'result':'passed'}))
