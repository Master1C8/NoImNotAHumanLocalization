"""Immutable cycle 003 independent verification and manually adjudicated reads."""
import hashlib
import importlib.util
import json
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SR = ROOT / 'Translations/sr'
R01, R02 = SR / 'independent-review-01', SR / 'independent-review-02'

def read(p): return json.loads(Path(p).read_text())
def rows(p): return [json.loads(x) for x in Path(p).read_text().splitlines()]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ts(x): return hashlib.sha256(x.encode()).hexdigest()
def ids_sha(ids): return ts(''.join(i + '\n' for i in ids))
def save(name, value):
    p = OUT / name
    assert not p.exists(), p
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
def lines(name, values):
    p = OUT / name
    assert not p.exists(), p
    p.write_text(''.join(json.dumps(v, ensure_ascii=False) + '\n' for v in values))

pins = {}
def pin(p, expected):
    p = Path(p)
    actual = sha(p)
    assert actual == expected, str(p)
    key = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
    pins[key] = {'expectedSha256': expected, 'actualSha256': actual, 'result': 'passed'}

# This normal generation command has no --write flag and checks immutable bytes.
recipe = SR / 'build_delta_review_003.py'
run = subprocess.run([str(ROOT / '.venv/bin/python'), str(recipe)], cwd=ROOT,
                     capture_output=True, text=True, check=True)
recipe_result = json.loads(run.stdout)
assert recipe_result['result'] == 'verified'
c = read(SR / 'semantic-cycle-003-closure.json')
prior = read(SR / 'semantic-cycle-002-closure.json')
correction = read(SR / 'semantic-cycle-003-corrections.json')
plan = read(SR / 'semantic-cycle-003-adjudication.json')
catalog = read(SR / 'semantic-cycle-003-regressions.json')
manifest = read(ROOT / 'Source/preserve-exactly-v4.json')
canonical = [r['stableId'] for r in manifest['tableRows'] + manifest['staticRows']]
assert len(canonical) == len(set(canonical)) == 16538
source = {}
for name in ('strings.jsonl', 'static-text.jsonl'):
    for r in rows(ROOT / 'Source/localization-inventory-v3' / name):
        assert r['stableId'] not in source
        source[r['stableId']] = r
target, locations = {}, {}
guids = {'UI': '0cbd8a7a4f543344bb95659de87f67a5', 'Dialogs': '444ff14f1967f5a4c8eb9e4cf4c913f1', 'ChecksDialogs': '389c6d80595013c41b85a7197838c4b6'}
for f in correction['currentAuthoredFileHashes']:
    p = ROOT / f['path']; pin(p, f['sha256']); b = read(p)
    for e in b['entries']:
        i = e.get('stableId') or 'string:' + guids[b['collection']] + ':' + str(e['id'])
        assert i not in target
        target[i], locations[i] = e['target'], f['path']
    s = read(p.with_suffix('.validation.json'))
    assert s['structuralResult'] == 'passed'
    assert s.get('batchSha256', s.get('draftSha256')) == f['sha256']
assert len(correction['currentAuthoredFileHashes']) == 341 and set(target) == set(canonical)
fileset = ts(''.join(f['path'] + '\t' + f['sha256'] + '\n' for f in sorted(correction['currentAuthoredFileHashes'], key=lambda f:f['path'])))
assert fileset == c['currentAuthoredFileSetSha256'] == correction['currentAuthoredFileSetSha256']
for f in correction['currentStructuralSidecarHashes']: pin(ROOT / f['path'], f['sha256'])
for key in ('sourceInventorySha256', 'sourceStaticSha256', 'sourceAcceptanceSha256', 'glossaryFingerprint', 'canonicalGlossaryReviewSha256'):
    assert c[key] == correction[key]
for path, key in [('Source/localization-inventory-v3/strings.jsonl','sourceInventorySha256'),('Source/localization-inventory-v3/static-text.jsonl','sourceStaticSha256'),('Documentation/text-source-acceptance-v1.json','sourceAcceptanceSha256'),('Documentation/glossary-translations/sr/layer.json','glossaryFingerprint'),('Documentation/glossary-translations/canonical-reviews/sr.json','canonicalGlossaryReviewSha256')]:
    pin(ROOT / path, correction[key])
for path, key in [('Source/preserve-exactly-v4.json','preserveExactManifestSha256'),('Translations/sr/semantic-cycle-003-corrections.json','correctionEvidenceSha256'),('Translations/sr/semantic-cycle-002-closure.json','priorClosureSha256'),('Translations/sr/independent-review-02/summary.json','priorReviewerSummarySha256'),('Translations/sr/independent-review-02/artifact-manifest.json','priorReviewerManifestSha256')]:
    pin(ROOT / path, c[key])
for path, key in [('Translations/sr/static-authored-map.json','staticAuthoredRecipeSha256'),('Translations/sr/static-text-draft.json','staticDraftSha256'),('Translations/sr/dialogue-common-002.authored.json','dialogueCommonRecipeSha256')]:
    pin(ROOT / path, correction[key])
for f in read(R02 / 'artifact-manifest.json')['files']:
    pin(ROOT / f['path'], f['sha256']); assert (ROOT / f['path']).stat().st_size == f['bytes']
for path, v in read(R02 / 'verification.json')['pins'].items():
    if path != 'Translations/sr/dialogue-batch-251.validation.json': pin(ROOT / path, v['expectedSha256'])
prep = read(SR / 'semantic-review-progress.json')['independentReviewPreparation']
for pkey, hkey in [('correctionEvidence','correctionEvidenceSha256'),('closure','closureSha256'),('deltaRows','deltaRowsSha256'),('mandatoryRegressionCatalog','mandatoryRegressionCatalogSha256'),('fullPreserveExactReport','fullPreserveExactReportSha256'),('handoff','handoffSha256')]: pin(ROOT / prep[pkey], prep[hkey])
for p in [recipe, SR / 'semantic-cycle-003-adjudication.json', SR / 'semantic-cycle-003-application-verification.json', SR / 'semantic-cycle-003-retirement-reasons.json', SR / 'semantic-cycle-003-regression-evidence.json', SR / 'reproduce_static_draft.py', ROOT / 'Scripts/preserve_exact.py']:
    pin(p, sha(p))

# Exact isolated application: reversing the one target reconstructs prior bytes.
old_files = {f['path']: f['sha256'] for f in prior['currentAuthoredFileHashes']}
change = plan['entries'][0]; changed_path = ROOT / change['targetFile']
current_bytes = changed_path.read_bytes()
new_literal = json.dumps(change['acceptedTarget'], ensure_ascii=False).encode()
old_literal = json.dumps(change['currentTarget'], ensure_ascii=False).encode()
assert current_bytes.count(new_literal) == 1 and old_literal not in current_bytes
restored = current_bytes.replace(new_literal, old_literal)
assert hashlib.sha256(restored).hexdigest() == old_files[change['targetFile']]
old_obj = json.loads(restored); new_obj = read(changed_path)
found = 0
for old, new in zip(old_obj['entries'], new_obj['entries']):
    if old != new:
        found += 1
        assert old['target'] == change['currentTarget'] and new['target'] == change['acceptedTarget']
        assert {k:v for k,v in old.items() if k != 'target'} == {k:v for k,v in new.items() if k != 'target'}
assert found == 1
assert all(sha(ROOT / p) == h for p,h in old_files.items() if p != change['targetFile'])

current, previous = set(c['closureIds']['ids']), set(prior['closureIds']['ids'])
changed, invalidated = set(c['changedIds']['ids']), set(c['explicitlyInvalidatedPriorIds']['ids'])
new, retired = current - previous, previous - current
delta = changed | new | invalidated
assert (len(current),len(changed),len(invalidated),len(new),len(retired),len(delta)) == (548,1,3,0,56,4)
for name, values in [('closureIds',current),('changedIds',changed),('explicitlyInvalidatedPriorIds',invalidated),('newDependencyIds',new),('retiredDependencyIds',retired),('deltaReviewIds',delta)]:
    e = c[name]; assert e['ids'] == [i for i in canonical if i in values]
    assert e['count'] == len(values) and ids_sha(e['ids']) == e['idsSha256']
assert ids_sha(prior['closureIds']['ids']) == prior['closureIds']['idsSha256']
assert current == set().union(*(set(v['ids']) for v in c['componentLists'].values()))
for v in c['componentLists'].values():
    assert v['ids'] == [i for i in canonical if i in set(v['ids'])]
    assert len(v['ids']) == v['count'] and ids_sha(v['ids']) == v['idsSha256']
for pkey,hkey in [('fullClosureReviewRows','fullClosureReviewRowsSha256'),('deltaReviewRows','deltaReviewRowsSha256'),('regressionCatalog','regressionCatalogSha256')]: pin(ROOT / c[pkey],c[hkey])
delta_rows = rows(ROOT / c['deltaReviewRows'])
assert [r['stableId'] for r in delta_rows] == c['deltaReviewIds']['ids']
for r in rows(ROOT / c['fullClosureReviewRows']):
    i=r['stableId']; assert r['source']==source[i]['source'] and r['target']==target[i]
    assert r['sourceSha256']==ts(r['source']) and r['targetSha256']==ts(r['target'])

# Reuse prior decisions only with exact current full-unit and dependency identity.
evidence={}
for p in [R01/'read-evidence.jsonl',R01/'additional-context-read-evidence.jsonl',R02/'read-evidence.jsonl']:
    for e in rows(p): evidence[e['stableId']]=(e,p)
reuse=[]
for i in c['closureIds']['ids']:
    if i in delta: continue
    e,p=evidence[i]
    assert e['source']==source[i]['source'] and e['target']==target[i]
    assert e['sourceSha256']==ts(source[i]['source']) and e['targetSha256']==ts(target[i])
    assert e.get('decision',e.get('semanticVerdict'))=='passed within reviewed context' and not e.get('findingId')
    reuse.append({'stableId':i,'sourceSha256':e['sourceSha256'],'targetSha256':e['targetSha256'],'priorEvidencePath':str(p.relative_to(ROOT)),'priorEvidenceSha256':sha(p),'priorReadOrdinal':e['readOrdinal'],'result':'applicable unchanged independent full-unit decision; not reread in cycle003'})
assert len(reuse)==544
lines('prior-evidence-applicability.jsonl',reuse)
retirement=read(SR/'semantic-cycle-003-retirement-reasons.json')
assert [e['stableId'] for e in retirement['rows']]==c['retiredDependencyIds']['ids']
for r in retirement['rows']:
    i=r['stableId'];e,p=evidence[i]
    assert e['source']==source[i]['source'] and e['target']==target[i]
    assert e.get('decision',e.get('semanticVerdict'))=='passed within reviewed context' and r['reason'] and i not in current

# Verify current approved glossary, including immutable acceptance receipts.
G=ROOT/'Documentation/glossary-translations'
approval=read(G/'canonical-reviews/sr.json'); accept=read(G/'acceptance-manifest.json')
assert approval['status']=='editorially-accepted-canonical' and approval['mode']=='STANDARD'
assert approval['entryCount']==201 and not approval['unresolvedFindings']
assert approval['consecutiveCleanFullAudits']>=2 and approval['independentFinalColdAudits']>=1
layer=read(G/'sr/layer.json'); gs=read(ROOT/'Documentation/glossary-research/final-v1/glossary.json')
pin(ROOT/'Documentation/glossary-research/final-v1/glossary.json',approval['sourceRawSha256'])
pin(G/'sr/layer.json',approval['layerRawSha256']); pin(G/'sr/authored.json',approval['authoredRawSha256'])
assert accept['sourceRawSha256']==approval['sourceRawSha256'] and accept['accepted']['sr']['layerRawSha256']==approval['layerRawSha256']
old_approval=read(R02/'glossary-approval-verification.json')
pin(G/'acceptance-manifest.json',old_approval['acceptanceManifestSha256'])
for e in old_approval['evidence']: pin(ROOT/e['currentPath'],e['expectedSha256'])
master=Path('/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human')
pin(master/'glossary.json',approval['sourceRawSha256'])
assert read(master/'glossary-translations.json')['sr']==layer
pin(master/'glossary-translations.json',sha(master/'glossary-translations.json'))
save('glossary-approval-verification.json',{'result':'passed; current canonical standard approval and immutable full-review receipts match exact source/authored/layer pins','approvalSha256':sha(G/'canonical-reviews/sr.json'),'acceptanceManifestSha256':sha(G/'acceptance-manifest.json'),'sourceRawSha256':approval['sourceRawSha256'],'layerRawSha256':approval['layerRawSha256'],'authoredRawSha256':approval['authoredRawSha256'],'entryCount':201,'masterSourceRawParity':True,'masterSerbianLayerParsedParity':True,'cmsParity':'not rerun; narrow text-review scope; no publication','historicalStatus':'Older author pending metadata retained as history; current canonical approval owns acceptance.'})

# Decode the shipped compiled program independently, retaining actual branch order.
consumers=read(R01/'runtime-consumers.json'); characters=read(R01/'character-runtime-data.json')
pin(Path(consumers['sourceDll']),consumers['sourceDllSha256']);pin(Path(characters['sourcePath']),characters['sourceSha256'])
for s in consumers['generatedSourceEvidence']:
    p=Path(s['path']);pin(p,s['fileSha256'])
    assert ''.join(p.read_text().splitlines(keepends=True)[s['firstLine']-1:s['lastLine']])==s['exactText']
binding=ROOT/'Source/glossary-corpus-v2/runtime-bindings.json';pin(binding,consumers['bindingsSha256'])
program=bytes(read(binding)['sharedassets0.assets:2743']['compiledYarnProgram'])
assert hashlib.sha256(program).hexdigest()==consumers['compiledProgramSha256']
def var(buf,i):
    n=shift=0
    while True:
        v=buf[i];i+=1;n|=(v&127)<<shift;shift+=7
        if v<128:return n,i
def fields(buf):
    i=0;out=[]
    while i<len(buf):
        key,i=var(buf,i);f,w=key>>3,key&7
        if w==0:v,i=var(buf,i)
        elif w==2:n,i=var(buf,i);v=buf[i:i+n];i+=n
        elif w==5:v=struct.unpack('<f',buf[i:i+4])[0];i+=4
        else:raise ValueError(w)
        out.append((f,v))
    return out
def operand(buf):
    f,v=fields(buf)[0];return v.decode() if f==1 else v
nodes={}
for f,v in fields(program):
    if f!=2:continue
    pair=dict(fields(v));name=pair[1].decode();ins=[];labels={}
    for f,v in fields(pair[2]):
        if f==2:
            raw=fields(v);ins.append({'index':len(ins),'opcode':next((v for f,v in raw if f==1),0),'operands':[operand(v) for f,v in raw if f==2]})
        elif f==3:
            lab=dict(fields(v));labels[lab[1].decode()]=lab.get(2,0)
    nodes[name]={'instructions':ins,'labels':labels}
scene=nodes['Hunter_Entrance_Occupied'];prior_scene=read(R02/'compiled-delta-context.json')['nodes']['Hunter_Entrance_Occupied']
assert scene['instructions']==[{k:v for k,v in r.items() if k in ('index','opcode','operands')} for r in prior_scene['instructions']]
assert scene['labels']==prior_scene['labels']
keymap={r.get('key'):r for r in source.values() if r.get('collection')=='Dialogs'}
for ins in scene['instructions']:
    key=next((o for o in ins['operands'] if isinstance(o,str) and o.startswith('line:')),None)
    if key:
        r=keymap[key];i=r['stableId'];ins.update(stableId=i,source=r['source'],target=target[i])
assert {r['stableId'] for r in scene['instructions'] if 'stableId' in r}==delta
save('compiled-delta-context.json',{'compiledProgramSha256':consumers['compiledProgramSha256'],'bindingsSha256':consumers['bindingsSha256'],'nodes':{'Hunter_Entrance_Occupied':scene},'scope':'Independently decoded serialized instructions and actual branch order; no execution.'})
domain=next(r for r in consumers['samePlaceLabelCandidates'] if r['node']=='Hunter_Entrance_Occupied')
actual_place={r['name'] for r in characters['rows'] if r['place']==10 and r['name']!='Hunter'}
assert domain['argument']=='Hunter' and domain['place']==10 and actual_place=={r['enum'] for r in domain['possibleLabels']}=={'Blind','FortuneTeller','Leper','Neighbour'}
cases=[]
for r in domain['possibleLabels']:
    i=r['labelStableId']
    if i is None:
        assert r['enum']=='Neighbour' and not any(e.get('collection')=='UI' and e.get('key')==r['key'] for e in source.values())
        continue
    assert source[i]['source']==r['source'] and target[i]==r['target']
    cases.append(dict(r,sourceAssembly=change['source'].replace('{0}',r['source']),currentAssembly=change['acceptedTarget'].replace('{0}',target[i]),semanticDecision='passed: indefinite resident introduced; literal descriptor attached without case/gender coercion'))
assert len(cases)==3
save('raw-label-cases.json',{'cases':cases,'unknownUiLabels':['Neighbour'],'substitutionSemantics':consumers['substitutionSemantics'],'placeDataSha256':sha(R01/'character-runtime-data.json'),'sourceDefault':'Following Russian этого человека / его uses masculine generic/default wording even for the admitted FortuneTeller candidate; current Serbian тог човека / га preserves that source construction and adds no new fixed-gender claim.','limits':'Static possible inputs and literal insertion only; no executed reachability; original config extraction registry limitation retained.'})

# These reasons are the reviewer's full-unit semantic decisions, not generated wording.
decisions={
 '110504457169608704':'Supplies an indefinite already-present resident and separately identifies the unchanged raw descriptor. All three actual known place-10 labels assemble naturally; no added name or unsupported diagnosis. Уже, location, service speaker and slot retained.',
 '110504457169608705':'All three sentences retain Hunter sensing blood on the resident\'s hands, questioning why the male player admitted that resident, and the nervous-thrill accusation. Actor, possessor and addressee remain distinct. Source male-default этого человека / его maps to тог човека / га, with no new gender inflection induced by the opening. Player masculine пустио agrees with approved player canon.',
 '110504457169608706':'Player promises to drive out the resident, then tells Hunter to enter. Future agency, resident object and imperative destination agree with the compiled YesLet branch; source generic жильца maps to станара.',
 '110504457169608707':'Player advises Hunter to leave; Боље иди retains the imperative and better-to-leave meaning in the actual NoLet branch. No occupant eviction or invitation is introduced.'
}
reads=[]
for ordinal,r in enumerate(delta_rows,1):
    reads.append(dict(r,readOrdinal=ordinal,semanticRead='Complete exact Russian/current Serbian unit read independently with approved glossary, compiled branch order and three literal Hunter input assemblies.',decision='passed within reviewed context',findingId=None,reason=decisions[r['stableId'].rsplit(':',1)[1]],inputAuthoredFileSetSha256=fileset))
lines('read-evidence.jsonl',reads);save('findings.json',{'objectiveFindings':[],'readUnits':4,'passedUnits':4,'verdict':'clean on unchanged current cycle003 hashes','resolvedPriorFinding':'SR-IR02-01 is corrected in authored input and all three known actual slot assemblies pass.'})
regressions=[];union=set()
for name,v in catalog['catalog'].items():
    values=set(v['ids']);union|=values
    assert v['count']==len(values) and v['ids']==[i for i in canonical if i in values] and ids_sha(v['ids'])==v['idsSha256']
    assert values<=current
    regressions.append({'name':name,'count':len(values),'idsSha256':v['idsSha256'],'freshReads':len(values&delta),'unchangedPriorDecisions':len(values-delta),'result':'passed'})
assert union==current
save('mandatory-regressions.json',{'catalogSha256':sha(SR/'semantic-cycle-003-regressions.json'),'authoredFileSetSha256':fileset,'catalogUnionCount':548,'freshReadUnits':4,'exactUnchangedPriorDecisions':544,'regressions':regressions,'overlap':'Category counts overlap; unique coverage is 548.','runtimeVisualFontsLayout':'not run; semantic/structural evidence does not establish rendering.','unboundFormatRows':13,'unknownSamePlaceUiLabel':'Neighbour','sourceDefault':'Source male-default resident reference retained, as explicitly recorded in raw-label-cases.json.'})
sys.path.insert(0,str(ROOT/'Scripts'));import preserve_exact
preserve_exact.validate('sr',OUT/'preserve-exact-current.json')
assert sha(OUT/'preserve-exact-current.json')==correction['fullPreserveExactReportSha256']
spec=importlib.util.spec_from_file_location('sr_static',SR/'reproduce_static_draft.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert module.reproduce()==(SR/'static-text-draft.json').read_text()
save('verification.json',{'result':'passed','authoredFileSetSha256':fileset,'authoredFiles':341,'acceptedUnits':16538,'structuralSidecars':341,'pins':pins,'recipePath':str(recipe.relative_to(ROOT)),'recipeSha256':sha(recipe),'normalRecipeResult':recipe_result,'application':'Exact one target reverse reconstructs previous file bytes; 340 other authored files byte-identical.','closureCount':548,'deltaCount':4,'correctedIds':1,'invalidatedPriorIds':3,'newDependencyIds':0,'retiredDependencies':56,'reuseCount':544,'staticReproduction':'passed all178 current static units from unchanged authored maps','fullExactReportSha256':sha(OUT/'preserve-exact-current.json'),'finalDeterministicGate':'Coordinator-owned; this review records its own current structural/exact checks, not integration.'})
# Recheck all pins at the end before recording the clean verdict.
assert all(sha(Path(p) if Path(p).is_absolute() else ROOT/p)==v['actualSha256'] for p,v in pins.items())
telemetry={'servedModel':'GPT-6 family identity exposed; exact served model unknown','reasoningSetting':'unknown','inputTokens':'unknown','cachedInputTokens':'unknown','outputTokens':'unknown','reasoningTokens':'unknown','totalTokens':'unknown','cutoff':'evidence production; no exact per-request/session telemetry exposed by tools; reporting tail and platform overhead unmeasured','delegation':'none','coordinator':'Parent orchestration usage is separate and not included in this reviewer subtotal.'}
save('summary.json',{'status':'complete independent cycle003 delta review; clean unchanged-hash verdict','reviewerTask':'/root/sr_independent_review_03','locale':'sr','sourceLocale':'ru','gameVersion':'1.3.19','authoredFileSetSha256':fileset,'closureSha256':sha(SR/'semantic-cycle-003-closure.json'),'closureCount':548,'deltaRowsSha256':sha(ROOT/c['deltaReviewRows']),'deltaIdsSha256':c['deltaReviewIds']['idsSha256'],'deltaReviewed':4,'deltaPassed':4,'objectiveFindings':0,'mandatoryRegressions':'passed548 union via544 exact unchanged prior independent decisions plus4 fresh complete-unit reads','resolvedPriorFinding':'SR-IR02-01','editorialAcceptance':'Clean independent criterion satisfied; final gate/integration belongs to coordinator.','telemetry':telemetry,'writes':'New immutable evidence only under Translations/sr/independent-review-03; no authored/source/glossary/prior evidence/shared scripts/state or Git/index mutation.','runtimeVisualFontsLayoutPackagingRelease':'not run','imagesTextures':'excluded','remainingTechnicalLimits':['13 format-slot rows lack pinned compiled instruction binding.','Neighbour place-10 key lacks a pinned UI label; no assembly asserted.','Static source/config consumer evidence proves possible candidates and literal substitution, not executed reachability.','Pinned config extraction retains its registry limitation.','Runtime, font metrics/glyph coverage, layout, package/release and canonical integration are not certified by this review.']})
print(json.dumps({'result':'clean','deltaRead':4,'findings':0,'closure':548,'reuse':544,'exact':16538,'pins':len(pins),'authoredFileSetSha256':fileset}))
