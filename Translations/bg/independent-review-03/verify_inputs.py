"""Independent cycle003 input and dependency reconciliation; writes only this review."""
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
BG = ROOT / 'Translations/bg'
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
textsha = lambda t: hashlib.sha256(t.encode()).hexdigest()
idbytes = lambda ids: ('\n'.join(ids) + ('\n' if ids else '')).encode()

c = load(BG / 'semantic-closure-cycle-003.json')
d = load(BG / 'semantic-delta-cycle-003.json')
plan = load(BG / 'correction-batch-003.json')
result = load(BG / 'correction-batch-003-result.json')
rows = d['nextReviewRows']
assert sha(BG / 'semantic-delta-cycle-003.json') == '423dcb03e4ddb29e4394e58aac4f24f072e3759b227c3f471d872271b042cd3e'
pins = dict(c['pinnedInputs'])
for name in ['semantic-delta-cycle-003.json', 'semantic-closure-cycle-003.json',
             'build_semantic_closure_cycle_003.py', 'build_semantic_delta_cycle_003.py',
             'build_voice_remedial_candidates.py', 'build_correction_result_003.py',
             'independent-review-02-author-adjudication.json',
             'independent-review-handoff-cycle-003.md', 'correction-cycle-003-handoff-checkpoint.json',
             'independent-review-01/compiled-context.json', 'independent-review-01/compiled-nodes.json',
             'independent-review-01/managed-context.json', 'independent-review-01/inspect_context.py',
             'independent-review-01/evidence-sha256.json', 'independent-review-02/evidence-sha256.json']:
    p = BG / name
    pins[str(p.relative_to(ROOT))] = sha(p)
for item in d['currentAuthoredFiles']:
    pins[item['path']] = item['sha256']
    pins[item['validationPath']] = item['validationSha256']
for name in ['validate_locale_corpus.py', 'locale_text_inputs.py', 'preserve_exact.py',
             'validate_game_text_batch.py', 'validate_static_text_draft.py']:
    pins['Scripts/' + name] = sha(ROOT / 'Scripts' / name)
for p, h in pins.items():
    assert sha(ROOT / p) == h, p
for cycle in ['01', '02']:
    base = BG / ('independent-review-' + cycle)
    manifest = load(base / 'evidence-sha256.json')
    for name, h in manifest.get('files', manifest).items():
        assert sha(base / name) == h, (cycle, name)

guid = {'Dialogs': '444ff14f1967f5a4c8eb9e4cf4c913f1', 'UI': '0cbd8a7a4f543344bb95659de87f67a5',
        'ChecksDialogs': '389c6d80595013c41b85a7197838c4b6'}
targets = {}
for f in result['allAuthoredFiles']:
    for e in load(ROOT / f['path'])['entries']:
        sid = e.get('stableId') or 'string:' + guid[f['collection']] + ':' + str(e['id'])
        assert sid not in targets
        targets[sid] = e['target']
assert len(targets) == 16538
source = [json.loads(l) for l in (ROOT / 'Source/localization-inventory-v3/strings.jsonl').open()]
source += [json.loads(l) for l in (ROOT / 'Source/localization-inventory-v3/static-text.jsonl').open()]
sourceby = {r['stableId']: r for r in source}
current = {r['stableId']: r for r in c['reviewRows']}
for r in c['reviewRows']:
    assert r['source'] == sourceby[r['stableId']]['source'] and r['target'] == targets[r['stableId']]
    assert r['key'] == sourceby[r['stableId']].get('key')
assert load(ROOT / '/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary-translations.json')['bg'] == load(ROOT / 'Documentation/glossary-translations/canonical-reviews/artifacts/bg/layer.json')

old = {r['stableId']: r for r in load(BG / 'semantic-closure-cycle-002.json')['reviewRows']}
first = {r['stableId']: r for r in load(BG / 'semantic-closure-cycle-001.json')['reviewRows']}
read01 = set((BG / 'independent-review-01/read.ids').read_text().splitlines())
read02 = set((BG / 'independent-review-02/read.ids').read_text().splitlines())
assert read01 | read02 == set(old)
same = lambda a,b: all(a.get(k) == b.get(k) for k in ['source','target','key','sceneNodes','collection'])
prior = {sid for sid in read02 if sid in current and same(old[sid], current[sid])}
prior01 = {sid for sid in read01-read02 if sid in current and same(first[sid], current[sid])}
assert len(prior) == 2070 and len(prior01) == 576
prior |= prior01
supp = {r['stableId']:r for r in load(BG / 'independent-review-02/selector-supplementary-rows.json') if not r['inDelta']}
assert len(supp) == 4
for sid,r in supp.items():
    if all(current[sid][k] == r[k] for k in ['source','target','key']): prior.add(sid)
assert len(prior) == 2649
corrected = {r['stableId'] for r in plan['decisions']}
for r in plan['decisions']:
    previous = old.get(r['stableId'], supp.get(r['stableId']))
    assert previous['source'] == r['source'] and previous['target'] == r['currentFullTarget']
    assert current[r['stableId']]['target'] == r['acceptedFullTarget']
assert len(corrected) == 41
baseline = {f['path']:f for f in plan['baselineAuthoredFiles']}
affected = {r['batchPath'] for r in plan['decisions']}
assert len(affected) == 35
historic = load(BG / 'independent-review-02/input-verification.json')['pins']
historical_drift = []
for p,h in historic.items():
    if sha(ROOT / p) != h: historical_drift.append(p)
allowed_drift = affected | {str(Path(p).with_suffix('.validation.json')) for p in affected}
assert set(historical_drift) == allowed_drift
for f in result['allAuthoredFiles']:
    b = baseline[f['path']]
    if f['path'] not in affected: assert f == b
    assert historic[f['path']] == b['sha256'] and historic[f['validationPath']] == b['validationSha256']

changed_nodes = {n for sid in corrected for n in current[sid]['sceneNodes']}
changed_sources = {current[sid]['source'] for sid in corrected}
groups = defaultdict(set)
for r in load(BG / 'correction-cycle-003-bounded-review.json')['rows']:
    for group in r['groupMembership']: groups[group].add(r['stableId'])
direct = ['baldFamilyReferents','wheelchairEarSignConsumer','leperLightExclamation','colorVerbReferents','rockImperativeAndMusic']
reasons = {}
for sid in prior:
    r=current[sid]; why=[]
    if set(r['sceneNodes']) & changed_nodes: why.append('same compiled Yarn node as a correction003 full-unit replacement')
    if r['source'] in changed_sources: why.append('exact Russian repetition of a correction003 unit')
    for g in direct:
        if sid in groups[g] and groups[g] & corrected: why.append('direct affected referent or consumer: '+g)
    if why: reasons[sid]=why
assert len(reasons)==121
assert reasons == {r['stableId']:r['reasons'] for r in d['invalidatedPriorReasons']}
new = set(current)-prior
assert len(new)==190 and not set(old)-set(current)
assert corrected | new | set(reasons) == {r['stableId'] for r in rows}
assert len(rows)==311
for component in list(c['components'].values())+list(d['components'].values()):
    assert component['count']==len(component['ids'])==len(set(component['ids']))
    assert (ROOT/component['path']).read_bytes()==idbytes(component['ids'])
    assert sha(ROOT/component['path'])==component['sha256']
mandatory=set(c['components']['mandatoryRegressions']['ids'])
delta={r['stableId'] for r in rows}
fresh=mandatory & delta; reuse=mandatory-delta
assert len(mandatory)==908 and len(fresh)==4 and len(reuse)==904 and reuse<=prior

spec=load(BG/'voice-risk-selector-v6.json'); candidates=load(BG/'voice-remedial-candidates-v6.json')
prefixes=tuple(spec['corePrefixes']+spec['secondaryPrefixes']); exact=set(spec['additionalExactWords']); excluded=set(spec['excludeExactWords'])
match=lambda t:[w for w in re.findall('[А-Яа-яЁё]+',t.lower()) if w not in excluded and (w in exact or w.startswith(prefixes))]
for w in spec['regressionCases']['include']: assert match(w)==[w]
for w in spec['regressionCases']['exclude']: assert not match(w)
selected=[(r['stableId'],match(r['source'])) for r in source if r.get('collection')=='Dialogs' and match(r['source'])]
assert selected==[(r['stableId'],r['matchedWords']) for r in candidates['candidates']] and len(selected)==741
misses=load(BG/'independent-review-02/selector-findings.json')['missingIds']
assert len(misses)==6 and set(misses)<={sid for sid,hits in selected} and set(misses)<=set(current)

# Read the raw current protobuf independently using the preserved wire decoder.
decodepath=BG/'independent-review-01/inspect_context.py'
module_spec=importlib.util.spec_from_file_location('wire_context',decodepath)
decoder=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(decoder)
bindings=load(ROOT/'Source/glossary-corpus-v2/runtime-bindings.json')
program=bytes(bindings['sharedassets0.assets:2743']['compiledYarnProgram']); nodes={}
for f,w,v in decoder.fields(program):
    if f!=2: continue
    entry=decoder.fields(v);name=next(x[2].decode() for x in entry if x[0]==1)
    nf=decoder.fields(next(x[2] for x in entry if x[0]==2));ins=[];labels={}
    for nn,ww,vv in nf:
        if nn==2:
            opcode=0;operands=[]
            for k,wire,val in decoder.fields(vv):
                if k==1:opcode=val
                elif k==2:operands.append([(a,wt,decoder.strings(av) if wt==2 else av) for a,wt,av in decoder.fields(val)])
            ins.append({'index':len(ins),'opcode':opcode,'operands':operands})
        elif nn==3:
            ll=decoder.fields(vv);labels[next(x[2].decode() for x in ll if x[0]==1)]=next((x[2] for x in ll if x[0]==2),0)
    nodes[name]={'instructions':ins,'labels':labels}
assert json.loads(json.dumps(nodes))==load(BG/'independent-review-01/compiled-nodes.json') and len(nodes)==3255
uses=defaultdict(list)
producers=Counter()
for name,node in nodes.items():
    for ins in node['instructions']:
        vals=[f[2] for op in ins['operands'] for f in op if len(f)>2]
        for val in vals:
            if isinstance(val,str) and val.startswith('line:'):uses[val].append({'node':name,'instruction':ins['index'],'opcode':ins['opcode']})
        if ins['opcode']==12:
            for val in vals:
                if isinstance(val,str) and val in ['GetCharacterOnPlace','GetCharacterName','GetConsumableName','GetPhoneNumber']: producers[val]+=1
managed=load(BG/'independent-review-01/managed-context.json')
base=Path('/Volumes/KINGSTONMAC/Applications/No Im not a Human.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human/NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed')
for filename,record in managed.items(): assert sha(base/filename)==record['sha256']
assert bindings['level1:4471']['runSelectedOptionAsLine']==0
record={'pins':pins,'currentAuthoredFiles':411,'currentValidationSidecars':411,'uniqueCurrentTargetIds':16538,
        'correctedFullUnitsMatchingCurrentAndHistoricalPairs':41,'affectedBatches':35,
        'historicReview02ChangedPins':historical_drift,'historicPinsMeaning':'70 authored/sidecar preimages intentionally changed; all other Review02 pins remain exact. All 41 old full pairs verified against sealed independent rows; no historic authored bytes reconstructed.',
        'priorApplicableIds':d['components']['priorApplicable']['ids'],'priorApplicableCounts':{'review02':2070,'review01Only':576,'review02Supplemental':3},
        'invalidatedReasons':d['invalidatedPriorReasons'],'invalidatedCount':121,'newWithoutApplicableReadCount':190,'reviewIds':311,'retired':0,
        'mandatoryFreshIds':[sid for sid in c['components']['mandatoryRegressions']['ids'] if sid in fresh],
        'mandatoryPriorApplicableIds':[sid for sid in c['components']['mandatoryRegressions']['ids'] if sid in reuse],
        'voiceCandidates':741,'voiceSpeakerCategories':len({r['speaker'] for r in candidates['candidates']}),'normalLexicalControls':spec['regressionCases'],'normalSelectedMisses':misses,
        'compiledProgramSha256':hashlib.sha256(program).hexdigest(),'compiledNodes':3255,
        'compiledUses':[{'stableId':r['stableId'],'key':r['key'],'uses':uses[r['key']]} for r in rows],
        'deltaRowsWithCompiledUses':sum(bool(uses[r['key']]) for r in rows),'deltaWithoutCompiledUses':[r['stableId'] for r in rows if not uses[r['key']]],
        'deltaFormatSlotRows':sum(bool(re.search(r'\{[0-9]+\}',r['source'])) for r in rows),
        'closureFormatSlotRows':sum(bool(re.search(r'\{[0-9]+\}',r['source'])) for r in c['reviewRows']),
        'measuredCompiledDynamicProducerCalls':dict(producers),'managedSourceSha256':{f:r['sha256'] for f,r in managed.items()},
        'dynamicApplicability':'Current assemblies, runner, compiled program, table bindings and source rows exactly match prior independent pins. Current delta contains no format slots. Dynamic output and mandatory slot evidence retain unchanged prior independent decisions; no arbitrary six-output count is asserted.',
        'physicalRuntime':'not run; owner prohibited launch','allSourceOrGlossaryChanged':False}
path=OUT/'input-verification.json'
payload=(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode()
if sys.argv[1]=='snapshot':
    assert not path.exists();path.write_bytes(payload)
else:
    assert path.read_bytes()==payload, 'Independent input verification drift'
print(json.dumps({k:v for k,v in record.items() if k in ['currentAuthoredFiles','uniqueCurrentTargetIds','correctedFullUnitsMatchingCurrentAndHistoricalPairs','invalidatedCount','reviewIds','voiceCandidates','voiceSpeakerCategories','deltaRowsWithCompiledUses','deltaFormatSlotRows','closureFormatSlotRows','measuredCompiledDynamicProducerCalls']}))
