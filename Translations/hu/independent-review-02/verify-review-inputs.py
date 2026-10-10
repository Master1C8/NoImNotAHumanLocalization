#!/usr/bin/env python3
"""Read-only verification and immutable independent delta context capture."""
import hashlib, json, runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
CUR=ROOT/'Translations/hu/semantic-correction-cycle-03/evidence'
PREV=ROOT/'Translations/hu/semantic-correction-cycle-01/evidence'
OLD=ROOT/'Translations/hu/independent-review-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
rows=lambda p:[json.loads(x) for x in p.read_text().splitlines()]
ids=lambda p:p.read_text().splitlines()
def write(name,value):
    p=OUT/name
    assert not p.exists(),str(p)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

recipe=runpy.run_path(str(CUR.parent/'build-closure.py'))
payloads,manifest=recipe['generate']()
assert all((CUR/k).read_bytes()==v for k,v in payloads.items())
assert sha(CUR/'closure-manifest.json')=='86bd61ab9857dd7795cd6d3e9873c3f55909ec8abb7d5136ee5c2e243561cc16'
corpus=recipe['corpus']()
plan,spec,prior,verdict,preserve,order,rules,source,after,ownership,hashes,changed,remedial=corpus
previous=ids(PREV/'closure-ids.txt'); current=ids(CUR/'closure-ids.txt')
corrected=ids(CUR/'changed-ids.txt'); invalidated=ids(CUR/'explicitly-invalidated-prior-ids.txt')
delta=ids(CUR/'next-review-delta-ids.txt')
assert len(delta)==len(set(delta))==264
assert set(delta)==set(corrected)|(set(current)-set(previous))|set(invalidated)
assert delta==[k for k in order if k in set(delta)]
oldrows=rows(OLD/'full-pair-read-evidence.jsonl')
assert len(oldrows)==2902 and [r['stableId'] for r in oldrows]==previous
oldmap={r['stableId']:r for r in oldrows}
applicability=[]
for key in previous:
    r=oldmap[key]
    assert r['fullPairRead'] is True and r['reader']=='/root/hu_independent_review_01'
    assert r['source']==source[key]['source']
    assert hashlib.sha256(r['source'].encode()).hexdigest()==r['sourceSha256']
    assert hashlib.sha256(r['currentTarget'].encode()).hexdigest()==r['targetSha256']
    same=r['currentTarget']==after[key]
    assert same or key in corrected
    applicability.append({'stableId':key,'sourceHashVerified':True,'targetUnchanged':same,
        'priorDecision':r['verdict'],'priorReader':r['reader'],
        'disposition':'independent-recheck-in-delta' if key in set(delta) else 'applicable-unchanged-prior-independent-review',
        'currentAuthoredFileSha256':hashes[ownership[key]],
        'previousPairTargetSha256':r['targetSha256']})
catalog=ids(CUR/'mandatoryRegression-ids.txt')
assert len(catalog)==1697 and set(catalog)<=set(current)
assert set(catalog)<=set(oldmap)|set(delta)
assert {r['stableId'] for r in remedial['rows']}<=set(delta)
additional=load(CUR.parent/'additional-closure-read.json')['rows']
assert {r['stableId'] for r in additional}<=set(delta)
decoder=runpy.run_path(str(OLD/'read_compiled_context.py'))
nodes,programsha=decoder['load']()
bykey={r.get('key'):k for k,r in source.items() if r.get('key')}
occ={}
for node,instructions in nodes.items():
    for ins in instructions:
        if ins['opcode'] in (2,4):
            for arg in ins['operands']:
                if isinstance(arg,str) and arg.startswith('line:'):
                    occ.setdefault(arg,[]).append({'node':node,'instruction':ins['index'],'opcode':ins['opcode']})
context=[]
for key in delta:
    r=source[key]; entries=[]
    for hit in occ.get(r.get('key'),[]):
        window=[]
        for ins in nodes[hit['node']][max(0,hit['instruction']-3):hit['instruction']+4]:
            value={**ins}
            for arg in ins['operands']:
                if isinstance(arg,str) and arg in bykey:
                    ref=bykey[arg];value['stableId']=ref;value['source']=source[ref]['source'];value['target']=after[ref]
            window.append(value)
        entries.append({**hit,'window':window})
    context.append({'stableId':key,'key':r.get('key'),'sourceNodes':r.get('nodeNames',[]),'occurrences':entries})
write('compiled-delta-context.json',{'compiledProgramSha256':programsha,'wireDecoderSha256':sha(OLD/'read_compiled_context.py'),'rows':context,'limit':'Instruction windows establish order and branch operands, not runtime reachability.'})
write('prior-applicability.json',{'priorPairEvidenceSha256':sha(OLD/'full-pair-read-evidence.jsonl'),'rows':applicability})
write('input-verification.json',{'recipeSha256':sha(CUR.parent/'build-closure.py'),'selectorSpecSha256':sha(CUR.parent/'closure-selector-spec.json'),
    'reproducedOutputs':len(payloads),'allByteIdentical':True,'closureManifestSha256':sha(CUR/'closure-manifest.json'),
    'previousClosureManifestSha256':sha(PREV/'closure-manifest.json'),'previousCount':len(previous),'closureCount':len(current),
    'correctedCount':len(corrected),'newCount':len(set(current)-set(previous)),'invalidatedCount':len(invalidated),'deltaCount':len(delta),
    'unionOverlapCount':len(corrected)+len(set(current)-set(previous))+len(invalidated)-len(delta),
    'retiredClosureIds':[k for k in previous if k not in set(current)],'catalogCount':len(catalog),
    'catalogPriorReusableCount':len(set(catalog)-set(delta)), 'catalogDeltaReviewedCount':len(set(catalog)&set(delta)),
    'remedialReadCount':len(remedial['rows']),'additionalReadCount':len(additional),'authoredFiles':hashes,
    'sourceInventorySha256':sha(ROOT/'Source/localization-inventory-v3/strings.jsonl'),
    'staticInventorySha256':sha(ROOT/'Source/localization-inventory-v3/static-text.jsonl'),
    'glossaryLayerSha256':sha(ROOT/'Documentation/glossary-translations/hu/layer.json'),
    'canonicalGlossarySha256':sha(Path('/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json')),
    'preserveManifestSha256':sha(ROOT/'Source/preserve-exactly-v4.json'),
    'deltaIdsSha256':sha(CUR/'next-review-delta-ids.txt'),'deltaRowsSha256':sha(CUR/'next-review-delta.jsonl'),
    'compiledProgramSha256':programsha,'compiledDeltaRows':sum(bool(r['occurrences']) for r in context),
    'compiledMissingDeltaDialogueIds':[r['stableId'] for r in context if r['key'] and r['key'].startswith('line:') and not r['occurrences']]})
print(json.dumps({'delta':len(delta),'catalog':len(catalog),'catalogPriorReusable':len(set(catalog)-set(delta)),
    'catalogDeltaReviewed':len(set(catalog)&set(delta)),'compiledDeltaRows':sum(bool(r['occurrences']) for r in context)}))
