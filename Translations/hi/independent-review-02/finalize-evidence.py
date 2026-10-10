"""One-shot immutable consolidation of Review 02; no translation mutation."""
import collections, hashlib, importlib.util, json
from pathlib import Path

R = Path.cwd()
H = R / 'Translations/hi'
P = Path(__file__).parent
def j(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ih(ids): return hashlib.sha256(('\n'.join(ids) + '\n').encode()).hexdigest()
def emit(name, data):
    with (P / name).open('x') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
def lines(name, data):
    with (P / name).open('x') as f:
        for row in data: f.write(json.dumps(row, ensure_ascii=False) + '\n')

start = j(P / 'start-pins.json')
end = {p: sha(R / p) for p in start}
assert start == end, [p for p in start if start[p] != end[p]]
c = j(H / 'semantic-cycle-002-closure.json')
d = j(H / 'semantic-cycle-002-review-delta.json')
old = j(H / 'semantic-cycle-001-closure.json')
findings = j(P / 'consolidated-full-unit-findings.json')['items']
fmap = collections.defaultdict(list)
for item in findings: fmap[item['stableId']].append(item['findingId'])
rows = {r['stableId']: r for r in c['reviewRows']}
cid = list(rows)
did = d['deltaIds']
prior = {r['stableId']: r for r in j(P / 'applicable-prior-mandatory-decisions.json')}
fresh = {}
part_counts = {}
for part in ['001', '002', '003', '004b', '005', '006']:
    data = [json.loads(s) for s in (P / f'per-id-read-part-{part}.jsonl').read_text().splitlines()]
    part_counts[part] = len(data)
    for r in data:
        sid = r['stableId']; row = rows[sid]
        assert r['fullRussianAndCurrentHindiRead'] is True
        assert r['sourceSha256'] == row['sourceSha256']
        assert r['currentTargetSha256'] == row['targetSha256']
        assert r['glossaryVersionSha256'] == c['glossaryLayerSha256']
        assert sid in did
        fresh[sid] = r
assert set(fresh) == set(did) and len(fresh) == 4429
assert len(prior) == 704 and set(prior) == set(cid) - set(did)
ledger = []
for ordinal, sid in enumerate(cid):
    row = rows[sid]
    if sid in fresh:
        r = dict(fresh[sid]); r['provenance'] = 'fresh independent full-pair delta read'
    else:
        r = dict(prior[sid]['priorDecision'])
        assert r['sourceSha256'] == row['sourceSha256']
        assert r['currentTargetSha256'] == row['targetSha256']
        assert r['glossaryVersionSha256'] == c['glossaryLayerSha256']
        assert r['fullRussianAndCurrentHindiRead'] and not r['findingIds']
        r['provenance'] = 'exact applicable independent Review 01 decision; no fresh-read credit'
        r['priorDecisionArtifact'] = 'Translations/hi/independent-review-01/per-id-read-evidence.jsonl'
    r['closureOrdinal0'] = ordinal
    r['components'] = row['components']
    r['findingIds'] = fmap[sid]
    r['result'] = 'objective-full-unit-finding' if fmap[sid] else 'no-objective-finding-in-static-read'
    r['contextStatus'] = 'adjudicated with approved glossary and compiled/source context where applicable'
    ledger.append(r)
lines('per-id-final-decisions.jsonl', ledger)
decision = {r['stableId']: r for r in ledger}
catalog = j(R / c['catalogPath'])
catalog_groups = collections.defaultdict(list)
for group in catalog['groups']:
    assert len(group['ids']) == group['count']
    assert ih(group['ids']) == group['idsSha256']
    for sid in group['ids']: catalog_groups[sid].append(group['name'])
required = [sid for sid in cid if sid in catalog_groups]
assert len(required) == 4805
assert ih(required) == c['catalogRequiredIdListSha256LfFinalNewline']
catalog_decisions = [dict(decision[sid], catalogGroups=catalog_groups[sid]) for sid in required]
assert sum(r['stableId'] in fresh for r in catalog_decisions) == 4119
assert sum(r['stableId'] in prior for r in catalog_decisions) == 686
lines('mandatory-catalog-per-id-decisions.jsonl', catalog_decisions)
oldids = {r['stableId'] for r in old['reviewRows']}
changed = set(d['correctedIds'])
new = set(cid) - oldids
invalid = (set().union(*(set(c['components'][k]) for k in ['sceneContext','repetition','glossaryReferent','runtimeBinding'])) & oldids) - changed
retired = oldids - set(cid)
assert changed == set(c['components']['changed'])
assert new == set(d['newDependencyIds'])
assert invalid == set(d['explicitInvalidatedPriorIds'])
assert retired == set(d['retiredIds'])
assert changed | new | invalid == set(did)
assert not retired & set(did)
for key in ['correctedIds','newDependencyIds','explicitInvalidatedPriorIds','retiredIds']:
    assert ih(d[key]) == d[key + 'Sha256LfFinalNewline']
assert ih(cid) == c['closureIdListSha256LfFinalNewline']
assert ih(did) == d['deltaIdListSha256LfFinalNewline']
retirement = []
for sid in d['retiredIds']:
    retirement.append({'stableId':sid,'previousComponents':[k for k,v in old['components'].items() if sid in v], 'currentComponents':[], 'reason':'Absent from every current changed, scene, repetition, referent, binding and mandatory component; unchanged prior evidence is preserved, no delta credit.'})
emit('retired-per-id-reconciliation.json', retirement)
spec = importlib.util.spec_from_file_location('review02_cycle002', H / 'build-semantic-cycle-002-closure.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
rebuilt = m.build()
for path, text in zip([H / 'semantic-cycle-002-runtime-context.json',H / 'semantic-cycle-002-closure.json',H / 'semantic-cycle-002-review-delta.json'], rebuilt[:3]):
    assert path.read_text() == text
context = j(H / 'semantic-cycle-002-runtime-context.json')
assert context['technicalFragmentCount'] == 7
assert len(context['translatedSupplierIds']) == 17
assert all(s in decision for s in context['translatedSupplierIds'])
adjudication = j(H / 'semantic-cycle-002-adjudication.json')
corrections = []
for item in adjudication['items']:
    sid = item['stableId']; r = rows[sid]
    assert sid in fresh and r['source'] == item['source']
    assert r['target'] == item['acceptedFullTarget']
    assert not fmap[sid]
    corrections.append({'stableId':sid,'reviewIndex':r['reviewIndex'],'source':r['source'],'previousHindi':item['before'],'currentHindi':r['target'],'sourceSha256':r['sourceSha256'],'targetSha256':r['targetSha256'],'independentResult':'full current correction read; no objective finding','findingGroup':item['findingGroup']})
assert len(corrections) == 21
emit('applied-21-independent-decisions.json', corrections)
outside = [item for item in findings if item['stableId'] not in fresh]
assert len(outside) == 1
emit('outside-delta-context-finding-evidence.json', outside)
nodes = m.runtime_nodes(m.helper().fields)
node_names = ['Twins_Entrance_YesLet','Firefighter_Entrance_4','RageEnding_3','Esenin_Asking_SpecialEvent_1','BigLebowski_Entrance_3','BigLebowski_Entrance_1','BigLebowski_Entrance_2','Entrance_Prophet_3_5','Entrance_Prophet_3_4','Esenin_Asking_SpecialEvent','Anger_Asking_3','Anger_Asking_2','Rocker_Entrance_2','TaxiDriver_Entrance_1','Foreigner_Entrance_2','Foreigner_Entrance_NoLet','Tough_Ears_DontShoot','Wheelchair_Photo_DontShoot','Theorist_Ears_Gun','Alkonost_Teeth_Gun','Tough_Entrance_Occupied','Tough_Entrance_Occupied_YesLet','Leper_Asking_3_2','Leper_Asking_3','phone_psychics_8','FatalDame_Asking_4_4','FatalDame_Asking_4_3']
source = [json.loads(s) for s in (R / 'Source/localization-inventory-v3/strings.jsonl').read_text().splitlines()]
targets = {}
for file in j(H / 'semantic-cycle-002-structural-gate.json')['files']:
    data = j(R / file['path'])
    if 'collection' in data:
        for e in data['entries']: targets[data['collection'],str(e['id'])] = e['target']
node_context = []
for name in node_names:
    pairs = []
    for r in source:
        key = (r['collection'],r['stableId'].rsplit(':',1)[1])
        if name in r.get('nodeNames',[]) and key in targets:
            pairs.append({'stableId':r['stableId'],'key':r.get('key'),'source':r['source'],'target':targets[key]})
    node_context.append({'node':name,'compiled':name in nodes,'compiledInstructionOrder':nodes.get(name),'fullPairs':pairs})
emit('adjudicated-compiled-context-evidence.json', node_context)
placement_path = H / 'independent-review-01/character-placement-source-prefix.json'
emit('final-unchanged-input-pins.json', {'startPinnedPaths':len(start),'allStartPinsUnchanged':True,'pins':end,'characterPlacementAdditionalPin':{'path':str(placement_path.relative_to(R)),'sha256':sha(placement_path)}})
emit('final-coverage-and-closure-proof.json', {'status':'findings; exact assigned delta review complete, author correction/adjudication needed','freshFullPairs':4429,'freshOrdinalRange0BasedHalfOpen':[0,4429],'partialLedgerRows':part_counts,'emptyFailedPart004NotCredited':True,'currentClosureCount':5133,'exactPriorReused':704,'catalogRequired':4805,'catalogFresh':4119,'catalogExactPrior':686,'catalogMissing':[],'corrected':21,'new':4200,'invalidated':215,'retired':758,'delta':4429,'formulaVerified':True,'recipeByteReproductionVerified':True,'componentCounts':c['componentCounts'],'componentHashes':c['componentIdListSha256LfFinalNewline'],'closureHash':c['closureIdListSha256LfFinalNewline'],'deltaHash':d['deltaIdListSha256LfFinalNewline'],'catalogRequiredHash':c['catalogRequiredIdListSha256LfFinalNewline'],'technicalFragmentsNotTranslatedUnits':7,'rawUiLabelsTranslatedUnits':17,'prior82ContextReadsNotCredited':True,'firstFull16538PassPreserved':True,'findings':17,'deltaFindingUnits':16,'outsideDeltaFindingUnits':1,'authoredChanges':False,'runtimeVerified':False,'fontShapingWrappingVerified':False})
print('Final evidence: 4429 fresh + 704 exact prior = 5133; catalog 4119 + 686 = 4805; 17 findings.')
