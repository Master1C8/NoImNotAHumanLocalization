"""Static independent Czech review evidence; writes only this immutable run folder."""
import hashlib, importlib.util, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Scripts'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def txt(s): return hashlib.sha256(s.encode()).hexdigest()
def read(p): return json.loads((ROOT/p).read_text())
def write(name, data):
    p = OUT/name
    assert not p.exists(), p
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
c = read('Translations/cs/semantic-correction-cycle-002-closure.json')
a = read('Translations/cs/semantic-correction-cycle-002-application.json')
adj = read(a['adjudication'])
h = read('Translations/cs/semantic-correction-cycle-002-handoff.json')
refs = [r['path'] for r in h['refs'].values()]
refs += ['Source/localization-inventory-v3/strings.jsonl', 'Source/localization-inventory-v3/static-text.jsonl', 'Documentation/text-source-acceptance-v1.json', 'Source/preserve-exactly-v4.json', 'Documentation/glossary-translations/cs/layer.json', 'Documentation/glossary-research/final-v1/glossary.json', 'Source/glossary-corpus-v2/runtime-bindings.json', 'Source/glossary-corpus-v2/current-dialogs-scope.json']
files = sorted(p for p in (ROOT/'Translations/cs').iterdir() if re.fullmatch(r'(dialogue|ui|checks)-batch-\d{3}\.json|static-text-draft\.json', p.name))
hashes = {str(p.relative_to(ROOT)):sha(p) for p in files}
assert txt(''.join(k+'\t'+v+'\n' for k,v in hashes.items())) == a['authoredFileSetSha256After']
for ref in h['refs'].values(): assert sha(ROOT/ref['path']) == ref['sha256']
assert sha(ROOT/'Documentation/glossary-translations/cs/layer.json') == c['glossaryFingerprint']
source = {r['stableId']:r for p in ['Source/localization-inventory-v3/strings.jsonl','Source/localization-inventory-v3/static-text.jsonl'] for r in map(json.loads,(ROOT/p).read_text().splitlines())}
current = {}
guid = {'UI':'0cbd8a7a4f543344bb95659de87f67a5','Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1','ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'}
owners = {}
for p in files:
    batch=json.loads(p.read_text())
    for e in batch['entries']:
        sid=e.get('stableId') or f"string:{guid[batch['collection']]}:{e['id']}"
        assert sid not in current
        current[sid]=e['target']; owners[sid]=str(p.relative_to(ROOT))
assert len(current)==16538
for r in c['reviewRows']:
    assert r['source']==source[r['stableId']]['source']
    assert r['target']==current[r['stableId']]
    assert txt(r['source'])==r['sourceSha256'] and txt(r['target'])==r['targetSha256']
reconstruction=[]
for f in a['changedFiles']:
    p=ROOT/f['path']; assert sha(p)==f['sha256After']
    b=json.loads(p.read_text())
    for e in b['entries']:
        sid=f"string:{guid[b['collection']]}:{e['id']}"
        old=next((r for r in adj['candidateRows'] if r['stableId']==sid),None)
        if old:
            assert e['target']==old['acceptedFullReplacement']
            assert txt(old['before'])==old['beforeSha256'] and txt(e['target'])==old['acceptedSha256']
            e['target']=old['before']
    rebuilt=txt(json.dumps(b,ensure_ascii=False,indent=2)+'\n')
    assert rebuilt==f['sha256Before']
    reconstruction.append({'path':f['path'],'beforeSha256':rebuilt,'afterSha256':sha(p)})
write('input-pins.json', {'kind':'independent review baseline','authoredFiles':hashes,'refs':{p:sha(ROOT/p) for p in sorted(set(refs))},'authoredFileSetSha256':a['authoredFileSetSha256After'],'beforeReconstruction':reconstruction,'verifiedChangedRows':len(adj['candidateRows']),'allClosureRowsCurrent':True})
s=importlib.util.spec_from_file_location('selector',ROOT/'Translations/cs/semantic-closure-selector.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
nodes=m.compiled_nodes(bytes(read('Source/glossary-corpus-v2/runtime-bindings.json')['sharedassets0.assets:2743']['compiledYarnProgram']))
keymap={r['key']:r for r in source.values() if r.get('collection')=='Dialogs'}
sidset=set(c['closureIds']); node_subset={}
for name, instructions in nodes.items():
    if not any(x['operands'] and x['operands'][0] in keymap and keymap[x['operands'][0]]['stableId'] in sidset for x in instructions): continue
    enriched=[]
    for i,x in enumerate(instructions):
        item={'index':i,**x}
        row=keymap.get(x['operands'][0]) if x['operands'] else None
        if row and x['opcode'] in (2,4):
            sid=row['stableId']; item.update(stableId=sid,source=row['source'],target=current[sid],inClosure=sid in sidset)
        enriched.append(item)
    node_subset[name]=enriched
write('compiled-context.json', {'compiledYarnProgramSha256':c['compiledYarnProgramSha256'],'nodes':node_subset,'note':'All compiled string operands retained; numeric/bool operands are not included by the pinned selector decoder. Static scene order, commands and named branch labels; not reachability or runtime proof.'})
from preserve_exact import check_value
manifest=read('Source/preserve-exactly-v4.json')
rules={r['stableId']:r for r in manifest['tableRows']+manifest['staticRows']}
assert set(rules)==set(current)
for sid,value in current.items(): check_value(rules[sid],value)
write('deterministic-preflight.json', {'checkedRows':len(current),'result':'passed','sourceRowsMatchClosure':268,'targetRowsMatchClosure':268,'completePreserveExactlyRows':16538,'compiledNodeCount':len(node_subset),'beforeAfterReconstructionFiles':len(reconstruction),'sourceAcceptanceSha256':c['sourceAcceptanceSha256'],'authoredFileSetSha256':c['authoredFileSetSha256'],'closureIdsSha256':c['closureIdsSha256'],'runtime':'not run; prohibited'})
print(json.dumps({'closureRows':268,'beforeAfterReconstructionFiles':len(reconstruction),'preserveExactRows':16538,'contextNodes':len(node_subset)}))
