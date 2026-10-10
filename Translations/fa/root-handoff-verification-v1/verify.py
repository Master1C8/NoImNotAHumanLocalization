"""Read-only root handoff verification; output confined to this directory."""
import hashlib, json, pathlib, re, sys

R = pathlib.Path(__file__).resolve().parents[3]
O = pathlib.Path(__file__).parent
F = R / 'Translations/fa'
cache = {}
def read(p):
    p = pathlib.Path(p)
    if p not in cache: cache[p] = json.loads(p.read_text())
    return cache[p]
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ids_hash(ids): return hashlib.sha256(''.join(s+'\n' for s in ids).encode()).hexdigest()
def pair(row, sorted_keys=False):
    return hashlib.sha256(json.dumps({k:row[k] for k in ('stableId','source','target')}, ensure_ascii=False, sort_keys=sorted_keys, separators=(',',':')).encode()).hexdigest()
def verify_rows(rows):
    for row in rows: assert sha(R/row['path']) == row['sha256'], row['path']
def sid(batch, row):
    return row.get('stableId') or 'string:'+GUID[batch['collection']]+':'+str(row['id'])
GUID = {'UI':'0cbd8a7a4f543344bb95659de87f67a5','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'}
h = read(F/'final-gate/root-handoff.json')
assert sha(F/'final-gate/root-handoff.json') == '916680f97a5957b93a340d36faf072c37d00b405f601e8f2e479668524daf0d7'
verify_rows(h['authoredFiles']); verify_rows(h['evidenceFiles']); verify_rows(h['sharedRecipes'])
assert len(h['authoredFiles']) == 419 and len({r['path'] for r in h['authoredFiles']}) == 419
v = read(F/'independent-review-03/review-verdict.json')
assert sha(F/'independent-review-03/review-verdict.json') == '8d1210986d0847f163505ab94334c873060cf643ac4051af84d42a6a960f8e31'
indexed = 0
for base in ('independent-review-01','independent-review-02','independent-review-03','audit-cycle-003'):
    index=read(F/base/'evidence-index.json')
    for name, pin in index['files'].items():
        path=R/name if name.startswith('Translations/') else F/base/name
        assert sha(path)==pin,(base,name)
        indexed += 1
for name,pin in v['pins'].items(): assert sha(R/name)==pin,name

# Reconstruct each complete first-pass receipt on its actual before-correction bytes.
cycles=[F/f'audit-cycle-{n:03}' for n in (1,2,3)]
manifests=[read(c/'file-delta-manifest.json') for c in cycles]
first=read(cycles[0]/'first-pass.snapshot.json')
before={}
for c,fm in zip(cycles,manifests):
    for row in fm['files']:before.setdefault(row['path'],c/'before'/pathlib.Path(row['path']).name)
receipt=read(F/'independent-review-01/input-verification.json')
first_ids=[]; first_values={}; historical_files={}; reproduced_segments=[]
for seg in first['reviewedSegments']:
    p=before.get(seg['path'],R/seg['path'])
    assert sha(p)==seg['sha256'],seg['path']
    batch=read(p); entries=batch['entries']
    if 'entryStart' in seg: entries=entries[seg['entryStart']:seg['entryEndExclusive']]
    ids=[sid(batch,r) for r in entries]
    assert len(ids)==seg['units'] and ids_hash(ids)==seg['reviewedIdsSha256']
    first_ids.extend(ids)
    for stable,row in zip(ids,entries):
        assert stable not in first_values
        first_values[stable]=row['target']
    historical_files[seg['path']]=sha(p)
    reproduced_segments.append({'path':seg['path'],'units':len(ids),'inputSha256':sha(p),'idSha256':ids_hash(ids)})
assert reproduced_segments==receipt['firstPassReceiptSegments']
assert len(first_ids)==len(set(first_ids))==16538 and ids_hash(first_ids)==first['reviewedIdsSha256']
manifest=read(R/'Source/preserve-exactly-v4.json')
assert set(first_ids)=={r['stableId'] for r in manifest['tableRows']+manifest['staticRows']}
source={}
for name in ('strings.jsonl','static-text.jsonl'):
    for line in (R/'Source/localization-inventory-v3'/name).open():
        row=json.loads(line); assert row['stableId'] not in source; source[row['stableId']]=row
current={}; current_locations={}
for row in h['authoredFiles']:
    batch=read(R/row['path'])
    for entry in batch['entries']:
        stable=sid(batch,entry); assert stable not in current
        current[stable]=entry['target'];current_locations[stable]=row['path']
assert len(current)==16538 and set(current)==set(first_ids)

# Follow every authored correction, including per-file state boundaries and untouched fields.
expected=dict(first_values); file_heads=dict(historical_files); correction_counts=[]
for c, fm in zip(cycles,manifests):
    plan=read(c/'correction-plan.json'); planned={r['stableId']:r for r in plan['rows']}; changed={}
    assert sha(c/'correction-plan.json')==fm['correctionPlanSha256']
    for row in fm['files']:
        name=pathlib.Path(row['path']).name; bp=c/'before'/name;ap=c/'after'/name
        assert sha(bp)==row['beforeSha256'] and sha(ap)==row['afterSha256']
        if row['path'] in file_heads: assert file_heads[row['path']]==sha(bp),row['path']
        file_heads[row['path']]=sha(ap)
        a,b=read(bp),read(ap)
        if 'entries' not in a: continue # Authored static recipe; its derivation is checked below.
        assert {k:x for k,x in a.items() if k!='entries'}=={k:x for k,x in b.items() if k!='entries'}
        assert len(a['entries'])==len(b['entries'])
        for aa,bb in zip(a['entries'],b['entries']):
            stable=sid(a,aa)
            assert {k:x for k,x in aa.items() if k!='target'}=={k:x for k,x in bb.items() if k!='target'}
            if aa['target']!=bb['target']:
                pp=planned[stable]; assert aa['target']==pp['before'] and bb['target']==pp['acceptedTarget']
                assert expected[stable]==aa['target'];expected[stable]=bb['target'];changed[stable]=bb['target']
    assert set(changed)==set(planned),(c,len(changed),len(planned))
    correction_counts.append(len(changed))
assert correction_counts==[76,5,1] and expected==current
for name,pin in file_heads.items(): assert sha(R/name)==pin,name

def component(c,name):
    data=(c/(name+'-ids.txt')).read_bytes(); ids=data.decode().splitlines()
    assert data==''.join(s+'\n' for s in ids).encode() and len(ids)==len(set(ids))
    assert set(ids)<=set(current)
    return set(ids)
old=component(cycles[1],'closure');cl=read(cycles[2]/'closure.json')
comp={k:component(cycles[2],k) for k in cl['componentHashes']}
for name,ids in comp.items(): assert cl['componentHashes'][name]=={'count':len(ids),'sha256':sha(cycles[2]/(name+'-ids.txt'))}
union=set().union(*(comp[k] for k in ('changed','context','repetition','glossaryReferent','runtimeBinding','mandatoryRegression','contextWatchlist')))
assert comp['closure']==union and comp['newlySelected']==union-old and comp['retiredPrior']==old-union
assert comp['invalidatedPrior']=={s for s in old if current_locations[s]=='Translations/fa/dialogue-batch-348.json'}
assert comp['nextReviewDelta']==comp['changed']|comp['newlySelected']|comp['invalidatedPrior']
assert [len(old),len(union),len(comp['newlySelected']),len(comp['retiredPrior']),len(comp['invalidatedPrior']),len(comp['nextReviewDelta'])]==[2701,946,2,1757,16,18]
review=read(F/'independent-review-03/per-id-review.json')
delta=read(cycles[2]/'next-review-delta.json')
assert review['closureSha256']==sha(cycles[2]/'closure.json') and review['deltaSha256']==sha(cycles[2]/'next-review-delta.json')
assert [{k:r[k] for k in ('stableId','source','target')} for r in review['reviewRows']]==[{k:r[k] for k in ('stableId','source','target')} for r in delta['rows']]
assert {r['stableId'] for r in review['reviewRows']}==comp['nextReviewDelta']
for row in review['reviewRows']:
    assert row['source']==source[row['stableId']]['source'] and row['target']==current[row['stableId']]
    assert row['fullPairSha256']==pair(row) and row['findingId'] is None and row['reasonedDecision']
choices=read(F/'independent-review-03/additional-choice-review.json')
assert len(choices['rows'])==choices['fullUnitsRead']==4
for row in choices['rows']: assert row['source']==source[row['stableId']]['source'] and row['target']==current[row['stableId']]
aunt=next(r for r in review['reviewRows'] if r['stableId'] in comp['changed'])
assert 'عمه یا خاله‌ام' in aunt['target'] and 'дом своей тётки' in aunt['source']

# Recheck exact applicable prior decisions, not catalog count booleans.
prior={n:{r['stableId']:r for r in read(F/n/'per-id-review.json')['reviewRows']} for n in ('independent-review-01','independent-review-02')}
for filename,name,count in [('catalog-reuse.json','mandatoryRegression',544),('retired-accounting.json','retiredPrior',1757)]:
    evidence=read(F/'independent-review-03'/filename);assert len(evidence['rows'])==evidence['count']==count
    assert {r['stableId'] for r in evidence['rows']}==comp[name]
    for row in evidence['rows']:
        n=pathlib.Path(row['priorReview']).parent.name;p=prior[n][row['stableId']]
        assert p['source']==source[row['stableId']]['source'] and p['target']==current[row['stableId']]
        assert p['findingId'] is None and p['outcome']==row['priorOutcome']
        assert p['fullPairSha256']==pair(p,n=='independent-review-01')==row['priorFullPairSha256']
        assert pair(p)==row['fullPairSha256']
        if 'nodeNames' in p:assert p['nodeNames']==source[row['stableId']].get('nodeNames',[])
catalog=read(F/'independent-review-03/catalog-reuse.json')
for name,pin in catalog['fixtureSourceHashes'].items(): assert sha(name)==pin
assert len(comp['mandatoryRegression']&comp['nextReviewDelta'])==0
retired_overlap=comp['retiredPrior']&comp['nextReviewDelta']
assert len(retired_overlap)==5 and retired_overlap==set(read(F/'independent-review-03/retired-delta-overlap.json')['ids'])
assembled=read(F/'independent-review-01/assembled-consumers.json'); outputs=0
for name,pin in assembled['pins'].items():assert sha(F/'independent-review-01'/name)==pin
for consumer in assembled['consumers']:
    for row in consumer['samePlaceOtherCharacters']:
        assert current[row['runtimeUiStableId']]==row['persianValue']
        assert current[consumer['stableId']].replace('{0}',row['persianValue'])==row['assembledPersian'];outputs+=1
assert outputs==6

static=read(F/'static-text-draft.json')['entries'];phrases=read(F/'static-phrase-map.json')['phrases']
mapping={r['source']:r['target'] for r in phrases};assert len(mapping)==len(phrases)
mapped=[r for r in static if source[r['stableId']]['source'] in mapping]
assert len(static)==178 and len(mapped)==177 and all(r['target']==mapping[source[r['stableId']]['source']] for r in mapped)
credits=read(F/'credits-role-map.json')['replacements'];cm={r['source']:r['target'] for r in credits}
assert len(cm)==len(credits)==81
pat=re.compile('|'.join(re.escape(s) for s in sorted(cm,key=len,reverse=True)))
credit='tmp:level5:59:m_text';assert pat.sub(lambda m:cm[m[0]],source[credit]['source'])==current[credit]
selected=[]
for row in read(F/'common-options-001.authored.json')['phrases']:
    matches=[s for s,r in source.items() if r.get('collection')=='Dialogs' and r['source']==row['source']]
    assert len(matches)==row['expectedRows'] and all(current[s]==row['target'] for s in matches);selected.extend(matches)
assert len(selected)==len(set(selected))==2841

# Administrative edits are explicit; historical first-pass pins retain their own applicability.
oper=read(F/'final-gate/operational-change.json'); admin={}
for label,path in [('progress',F/'semantic-review-progress.json'),('documentation',R/'Documentation/fa-text-progress-v1.json')]:
    pre=F/'final-gate/preimages'/path.name;a,b=read(pre),read(path)
    assert sha(pre)==oper[label+'BeforeSha256'] and sha(path)==oper[label+'AfterSha256']
    changed=[k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)]
    allowed={'stage','independentReview03','finalOfflineGate','nextAction'} if label=='progress' else {'stage','authoredArtifacts','checks','nextAction'}
    assert set(changed)<=allowed
    if label=='progress':
        for key in ('pins','reviewedSegments','reviewedUnits','reviewedIdsSha256','cycle3Evidence'):assert a[key]==b[key]
        assert b['pinsScope'].startswith('The pins and reviewedSegments retain the historical first-pass')
    else:
        assert a['coverage']==b['coverage'] and a['inputs']==b['inputs']
        assert a['authoredArtifacts']['batchSetSha256']==b['authoredArtifacts']['batchSetSha256']
    admin[label]={'preimageSha256':sha(pre),'currentSha256':sha(path),'changedKeys':sorted(changed),'applicability':'Administrative final-stage/current evidence additions; historic semantic receipts remain explicitly scoped.'}

# Exercise the shared builder's exact current-text contract once, with no per-batch pools.
sys.dont_write_bytecode=True;sys.path.insert(0,str(R/'Scripts'))
from locale_text_inputs import current_text
values,files=current_text('fa')
assert len(values)==16538 and files==h['authoredFiles']
sidecars=[(R/r['path']).with_suffix('.validation.json') for r in files]
assert len(sidecars)==419 and all(p.exists() for p in sidecars)
fresh=read(F/'final-gate/fresh-full-corpus.json')
assert fresh['authoredFiles']==files and fresh['rows']==16538
for name,pin in fresh['owningValidators'].items():assert sha(R/'Scripts'/name)==pin
assert sha(R/'Scripts/validate_locale_corpus.py')==fresh['validatorSha256']
assert sha(R/'Scripts/locale_text_inputs.py')==fresh['inputLoaderSha256']
assert fresh['sourceInventorySha256']==sha(R/'Source/localization-inventory-v3/strings.jsonl')
assert fresh['staticInventorySha256']==sha(R/'Source/localization-inventory-v3/static-text.jsonl')
master=h['masterGlossaryParity']
assert read(master['masterSourcePath'])==read(R/master['localSourcePath'])
assert read(master['masterLayersPath'])['fa']==read(R/master['localLayerPath'])
assert sha(master['masterSourcePath'])==master['masterSourceSha256']
assert sha(R/master['localLayerPath'])==master['localLayerSha256']

report={'schemaVersion':1,'reviewer':'/root/fa_final_handoff_verification','result':'VERIFIED offline editorial evidence; coordinator acceptance adapter required','handoffSha256':sha(F/'final-gate/root-handoff.json'),'verdictSha256':sha(F/'independent-review-03/review-verdict.json'),'indexedFilesVerified':indexed,'reviewerPinsVerified':len(v['pins']),'firstPass':{'units':16538,'segments':447,'reviewedIdsSha256':ids_hash(first_ids),'receiptReconstructed':True,'limits':'Receipt reconstruction verifies complete pinned semantic-review evidence; no new full semantic reread claimed.'},'correctionChain':{'cycleTargetDeltas':correction_counts,'completeCurrentTargetsMatchReplayedChain':True,'fileCommitBoundary':'Per-file atomic changes; no cross-file transaction claim.'},'delta':{'previous':2701,'current':946,'new':2,'invalidated':16,'corrected':1,'exactDelta':18,'additionalChoiceReads':4,'retired':1757,'retiredDeltaOverlapFreshReads':5,'retiredOutsideDeltaReusable':1752},'mandatory':{'count':544,'exactPriorIndependentDecisions':544,'currentDeltaOverlap':0,'result':'passed'},'derived':{'static':178,'mapped':177,'creditsRoles':81,'commonOptions':2841,'admittedDynamicOutputs':6,'result':'passed'},'currentTextContract':{'units':16538,'authoredFiles':419,'tableValidationSidecars':418,'staticValidationSidecars':1,'exactProtectedGrammar':'passed by current_text','freshOwningStructuralReceiptReusable':'byte-identical inputs and validator pins verified'},'administrativeApplicability':admin,'integrationFindings':[{'id':'IF01','reason':'Author handoff carries extra structural/derived counts while accept_locale_text requires exact two-field dictionaries. Normalize a new adapter; keep this author handoff immutable.'},{'id':'IF02','reason':'Author full-corpus receipt uses rows/authoredFiles; accepted_inputs expects checkedRows/inputFiles/manifestSha256. Coordinator must create a compatible new preserve_exact receipt and pin it in the adapter.'}],'runtime':'not-run','visual':'not-run','build':'coordinator-owned; not run here','limits':h['unresolvedSourceContext'],'noFullAuditRestartJustified':True,'integrationPins':{'authorHandoff':h['evidenceFiles'],'authoredFiles':files,'sharedRecipes':h['sharedRecipes'],'review03IndexSha256':sha(F/'independent-review-03/evidence-index.json'),'exactManifestSha256':sha(R/'Source/preserve-exactly-v4.json')},'modelUsage':{'inputTokens':None,'cachedInputTokens':None,'outputTokens':None,'totalTokens':None,'status':'unknown in tool telemetry; coordinator collects session usage after completion; reporting tail unmeasured'},'writes':'Translations/fa/root-handoff-verification-v1 only; no Git/index/build/runtime/shared mutation'}
output=O/'verification.json';assert not output.exists();output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'result':report['result'],'reportSha256':sha(output),'correctionChain':correction_counts,'firstPassUnits':len(first_ids),'currentContractUnits':len(values),'indexedFiles':indexed,'reviewerPins':len(v['pins'])}))
