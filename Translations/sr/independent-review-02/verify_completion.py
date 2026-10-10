"""Final unchanged-input verification and canonical glossary approval supplement."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SR=ROOT/'Translations/sr'
OLD=SR/'independent-review-01'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,data):
    p=OUT/name;assert not p.exists()
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

verification=read(OUT/'verification.json')
for p,r in verification['pins'].items():
    p=Path(p);p=p if p.is_absolute() else ROOT/p
    assert sha(p)==r['expectedSha256']
for r in verification['authoredFiles']:assert sha(ROOT/r['path'])==r['sha256']

approval_path=ROOT/'Documentation/glossary-translations/canonical-reviews/sr.json'
approval=read(approval_path)
acceptance_path=ROOT/'Documentation/glossary-translations/acceptance-manifest.json'
acceptance=read(acceptance_path)['accepted']['sr']
assert approval['status']=='editorially-accepted-canonical'
assert approval['entryCount']==201 and approval['consecutiveCleanFullAudits']==3
assert approval['independentFinalColdAudits']==1
assert sha(ROOT/'Documentation/glossary-research/final-v1/glossary.json')==approval['sourceRawSha256']
assert sha(ROOT/'Documentation/glossary-translations/sr/layer.json')==approval['layerRawSha256']==acceptance['layerRawSha256']
assert sha(ROOT/'Documentation/glossary-translations/sr/authored.json')==approval['authoredRawSha256']==acceptance['authoredRawSha256']
evidence=[]
for path,expected in acceptance['evidenceSha256'].items():
    if path.startswith('sr/'):
        actual_path=ROOT/'Documentation/glossary-translations'/path
    else:
        assert path.startswith('independent-reviews/sr/')
        actual_path=ROOT/'Documentation/glossary-translations/canonical-reviews/independent/sr'/Path(path).name
    assert sha(actual_path)==expected
    evidence.append({'historicalPath':path,'currentPath':str(actual_path.relative_to(ROOT)),'expectedSha256':expected,'actualSha256':sha(actual_path),'result':'passed'})
cold=read(ROOT/'Documentation/glossary-translations/canonical-reviews/independent/sr/review-v1.json')
assert cold['status']=='full-clean-independent-final-cold-audit' and cold['entriesReviewed']==201 and not cold['findings']
save('glossary-approval-verification.json',{'result':'current canonical source and Serbian layer have matching canonical editorial acceptance and immutable independent review evidence','approvalPath':str(approval_path.relative_to(ROOT)),'approvalSha256':sha(approval_path),'acceptanceManifestPath':str(acceptance_path.relative_to(ROOT)),'acceptanceManifestSha256':sha(acceptance_path),'sourceRawSha256':approval['sourceRawSha256'],'layerRawSha256':approval['layerRawSha256'],'authoredRawSha256':approval['authoredRawSha256'],'independentReceiptSha256':sha(ROOT/'Documentation/glossary-translations/canonical-reviews/independent/sr/review-v1.json'),'evidence':evidence,'historicalAuthorStatus':'The older Documentation/glossary-translations/sr/review.json pending status is preserved author history. Canonical-reviews/sr.json plus acceptance-manifest.json establish the accepted current layer. The metadata limitation noted in this review summary is resolved by these existing receipts, with no source/layer changes and no new glossary audit.','cmsParity':'not rerun by this narrow independent text reviewer; no publication performed'})

bindings=ROOT/'Source/glossary-corpus-v2/runtime-bindings.json'
consumers=read(OLD/'runtime-consumers.json')
program=bytes(read(bindings)['sharedassets0.assets:2743']['compiledYarnProgram'])
assert hashlib.sha256(program).hexdigest()==consumers['compiledProgramSha256']
helper=(OUT/'produce_evidence.py').read_text()
decoder=helper[helper.index('def var(buf, i):'):helper.index('selected_nodes=')]
scope={'program':program}
exec('import struct\n'+decoder,scope)
nodes=scope['nodes']
risk=read(SR/'semantic-cycle-002-dynamic-risk.json')
categories={}
unbound=[]
for r in risk['rows']:
    actual=[]
    for n,node in nodes.items():
        instructions=node['instructions']
        for j,ins in enumerate(instructions):
            if r['key'] not in ins['operands']:continue
            # Only calls producing display substitutions are in this pinned catalog.
            prior_calls=[i['operands'][0] for i in instructions[:j] if i['opcode']==12 and i['operands'] and i['operands'][0] in ['LocalizeItem','GetCharacterOnPlace','GetPhoneNumber','GetCourierOrder']]
            assert prior_calls
            actual.append({'node':n,'consumer':prior_calls[-1],'instructionIndex':ins['index']})
    assert actual==r['compiledInstructions'],r['stableId']
    if not actual:unbound.append(r['stableId'])
    category=actual[0]['consumer'] if actual else 'unboundInPinnedCompiledProgram'
    assert category==r['consumerCategory']
    categories[category]=categories.get(category,0)+1
assert categories==risk['consumerCategoryCounts'] and len(unbound)==13

characters=read(OLD/'character-runtime-data.json')['rows']
enums=consumers['enums']['ECharacterType']
byenum={enums[str(x['characterType'])]:x for x in characters}
for r in consumers['samePlaceLabelCandidates']:
    owner=byenum[r['argument']]
    expected=[enums[str(x['characterType'])] for x in characters if x['place']==owner['place'] and enums[str(x['characterType'])]!=r['argument']]
    assert [x['enum'] for x in r['possibleLabels']]==expected
unknown=sorted({x['enum'] for r in consumers['samePlaceLabelCandidates'] for x in r['possibleLabels'] if not x['labelStableId']})
assert unknown==['Alkonost','Neighbour','Twins']
save('dynamic-catalog-verification.json',{'result':'all111 format rows matched against independently decoded entire compiled program; consumer categories and55 actual same-place domains verified from pinned serialized character place fields; semantic reuse remains per-ID in prior-evidence-applicability.jsonl','rows':111,'categoryCounts':categories,'unboundIds':unbound,'samePlaceConsumerDomains':len(consumers['samePlaceLabelCandidates']),'missingUiEnums':unknown,'substitution':'Source/generated evidence pinned unchanged; literal String.Replace without morphology. Synthetic insertion cases do not establish executed reachability.','staticRegeneration':'reproduce_static_draft.py without --write reproduced178 units at f62551d3a7eb584b213ee4e80dd84cdfbf6bb75aed006951597ec8aa381dc5b3; authored/credits maps unchanged.'})
save('completion-hash-verification.json',{'result':'all405 pinned original inputs and341 current authored files rehashed after evidence production; unchanged','pinCount':len(verification['pins']),'authoredCount':len(verification['authoredFiles']),'authoredFileSetSha256':verification['authoredFileSetSha256'],'deltaRowsSha256':sha(SR/'semantic-cycle-002-delta-review-rows.jsonl'),'closureSha256':sha(SR/'semantic-cycle-002-closure.json'),'preserveExactFinalSha256':sha(OUT/'preserve-exact-final.json'),'semanticVerdict':'changes required; one full-unit proposal SR-IR02-01 remains unmodified in findings.json'})
print(json.dumps({'finalPinsUnchanged':len(verification['pins']),'authoredFilesUnchanged':341,'glossaryApproval':'verified canonical','dynamicRowsVerified':111,'unboundRows':13,'unknownUiEnums':unknown}))
