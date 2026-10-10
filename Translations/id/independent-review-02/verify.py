"""Read-only current-cycle verification; writes reviewer-owned evidence only."""
import json, hashlib, importlib.util
from pathlib import Path
R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
C = 'Translations/id/semantic-correction-cycle-02/'
P = 'Translations/id/semantic-correction-cycle-01/'
def sha(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads((R/p).read_text())
checks=[]
def walk(x):
    if isinstance(x,dict):
        if 'path' in x and 'sha256' in x:
            p=Path(x['path']);p=p if p.is_absolute() else R/p
            assert p.is_file(),p
            a=sha(p.read_bytes());checks.append({'path':str(p),'expected':x['sha256'],'actual':a})
            assert a==x['sha256'],p
        for v in x.values():walk(v)
    elif isinstance(x,list):
        for v in x:walk(v)
walk(load(C+'independent-delta-handoff-v2.json'))
for n in ['artifact-manifest.json','component-manifest.json','delta-manifest.json','source-only-context-manifest.json']:walk(load(C+n))
manifest=load(C+'artifact-manifest.json')
for x in manifest['validationSidecars']:
    assert sha((R/x['inputPath']).read_bytes())==x['inputSha256']
    s=load(x['path']);assert s.get('structuralResult')=='passed',s
    assert s.get('batchSha256',s.get('draftSha256',s.get('inputSha256')))==x['inputSha256'],s
spec=importlib.util.spec_from_file_location('ctx',R/'Translations/id/independent-review-01/compiled_context.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
nodes,programsha=m.load();saved=load('Translations/id/independent-review-01/compiled-nodes.json')
assert nodes==saved['nodes'];assert programsha==saved['programSha256']
def ids(p):return set((R/p).read_text().splitlines())
prev=ids(P+'closure.ids.txt');cur=ids(C+'closure.ids.txt');chg=ids(C+'changed.ids.txt');inv=ids(C+'invalidated-prior.ids.txt');delta=ids(C+'delta-review.ids.txt')
assert ids(C+'new-dependencies.ids.txt')==cur-prev
assert ids(C+'retired-dependencies.ids.txt')==prev-cur
assert delta==chg|(cur-prev)|inv
rules=load('Source/preserve-exactly-v4.json');order=[x['stableId'] for x in rules['tableRows']+rules['staticRows']]
src={x['stableId']:x for f in ['strings','static-text'] for x in map(json.loads,(R/f'Source/localization-inventory-v3/{f}.jsonl').read_text().splitlines())}
rows=list(map(json.loads,(R/(C+'delta-review-rows.jsonl')).read_text().splitlines()))
assert [x['stableId'] for x in rows]==[i for i in order if i in delta]
for x in rows:assert x['source']==src[x['stableId']]['source']
phone=list(map(json.loads,(R/(C+'source-only-phone-context.jsonl')).read_text().splitlines()))
selected=[x for x in src.values() if x.get('collection')=='NotCharacterDialogs' and (x.get('key') or '').startswith('line:phone_daughtersfriend_')]
assert len(selected)==len(phone)==60
for a,b in zip(phone,selected):assert all(a[k]==b[k] for k in a)
assert not set(x['stableId'] for x in phone)&set(order)
canonical=json.loads(Path('/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary-translations.json').read_text())
assert canonical['id']==load('Documentation/glossary-translations/id/layer.json')
out={'schemaVersion':1,'hashChecks':len(checks),'hashMismatches':[],'checks':checks,'targetInputs':len(manifest['targetInputs']),'matchingValidationSidecars':len(manifest['validationSidecars']),'compiledProgramSha256':programsha,'compiledNodes':len(nodes),'compiledInstructions':sum(map(len,nodes.values())),'deltaArithmetic':{'previous':len(prev),'current':len(cur),'corrected':len(chg),'new':len(cur-prev),'invalidated':len(inv),'retired':len(prev-cur),'delta':len(delta)},'exactSourceRows':True,'sourceOnlyPhoneContext':{'rows':60,'overlap':0,'projectionMatches':True},'canonicalLocaleLayerParity':True}
path=O/'verification-initial.json'
assert not path.exists()
path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print({k:v for k,v in out.items() if k!='checks'})
