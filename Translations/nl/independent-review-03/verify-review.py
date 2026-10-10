"""Read-only input verification and isolated closure reproduction for review 03."""
from pathlib import Path
import json, hashlib, importlib.util, sys
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=lambda p:[json.loads(l) for l in p.read_text().splitlines()]
checks=[]
def verify(p,h):
    p=Path(p);p=p if p.is_absolute() else ROOT/p
    actual=sha(p);assert actual==h,(str(p),h,actual)
    checks.append({'path':str(p),'sha256':actual})
def load(p):return json.loads((ROOT/p).read_text())
def run(final=False):
    global checks
    checks=[]
    cp=load('Translations/nl/semantic-cycle-3/checkpoint-v2.json')
    m=load(cp['cycle3']['closureManifestPath'])
    verify(cp['cycle3']['closureManifestPath'],cp['cycle3']['closureManifestSha256'])
    verify(cp['handoffPath'],cp['handoffSha256'])
    verify(cp['currentProgressPath'],cp['currentProgressSha256'])
    for v in m['pins'].values():verify(v['path'],v['sha256'])
    for k in ['recipe','adjudication','selectorGroups','reviewRows','consumerContext','deltaReviewRows','previousClosure']:verify(m[k+'Path'],m[k+'Sha256'])
    for f,k in [('complete-batch-preflight-v3.json','preflightSha256'),('before-rows.jsonl','beforeRowsSha256'),('after-rows-v3.jsonl','afterRowsSha256')]:verify('Translations/nl/semantic-cycle-3/'+f,m[k])
    verify('Translations/nl/semantic-review-rows-pass1.jsonl',m['pass1ReviewRowsSha256'])
    for version in ['01','02']:
        path='Translations/nl/independent-review-'+version+'/evidence-manifest.json'
        receipt=load(path)
        if version=='02':verify(path,m['previousIndependentReviewEvidenceSha256'])
        else:
            old=load('Translations/nl/semantic-cycle-2/closure/closure-manifest.json')
            verify(path,old['previousIndependentReviewEvidenceSha256'])
        if 'files' in receipt:
            for p,h in receipt['files'].items():verify('Translations/nl/independent-review-'+version+'/'+p,h)
        else:
            for v in receipt['artifacts']:verify(v['path'],v['sha256'])
    for v in [*m['components'].values(),m['nontranslatableContext']]:
        verify(v['path'],v['sha256']);assert len((ROOT/v['path']).read_text().splitlines())==v['count']
    for v in m['manual']['authoredBatches']:verify(v['path'],v['sha256'])
    assert hashlib.sha256(''.join(v['path']+' '+v['sha256']+'\n' for v in m['manual']['authoredBatches']).encode()).hexdigest()==m['manual']['authoredSetSha256']==cp['currentAuthoredBatchSetSha256']
    for p,k in [('Translations/nl/static-text-map.json','staticMapSha256'),('Translations/nl/credits-role-map.json','creditsRoleMapSha256')]:verify(p,m['manual'][k])
    for p,k in [('Translations/nl/static-text-draft.json','staticDraftSha256'),('Translations/nl/semantic-cycle-3/preserve-exact-v4-after-v2.json','preserveExactAfterSha256'),('Translations/nl/semantic-cycle-3/structural-validation-v2.json','structuralValidationSha256')]:verify(p,m['derived'][k])
    consumer=load(m['consumerContextPath']);verify(consumer['bindingPath'],consumer['bindingSha256'])
    raw=bytes(load(consumer['bindingPath'])['sharedassets0.assets:2743']['compiledYarnProgram'])
    assert hashlib.sha256(raw).hexdigest()==consumer['compiledProgramSha256']
    priorconsumer=load(consumer['reusedGetterAndLocalizationEvidence']);verify(consumer['reusedGetterAndLocalizationEvidence'],consumer['reusedGetterAndLocalizationEvidenceSha256'])
    for k in ['getterCpp','localizationCpp']:verify(priorconsumer[k]['path'],priorconsumer[k]['sha256'])
    full=rows(ROOT/m['reviewRowsPath']);delta=rows(ROOT/m['deltaReviewRowsPath'])
    sets={k:set((ROOT/v['path']).read_text().splitlines()) for k,v in m['components'].items()}
    prev=set((ROOT/m['previousClosurePath']).read_text().splitlines())
    assert sets['new-dependencies']==sets['closure']-prev
    assert sets['retired-dependencies']==prev-sets['closure']
    assert sets['delta']==sets['changed']|sets['new-dependencies']|sets['explicit-invalidated']
    assert [len(sets[k]) for k in ['closure','changed','new-dependencies','explicit-invalidated','delta','retired-dependencies']]==[764,40,0,0,40,157]
    assert [r['stableId'] for r in full]==(ROOT/m['components']['closure']['path']).read_text().splitlines()
    assert [r['stableId'] for r in delta]==(ROOT/m['components']['delta']['path']).read_text().splitlines()
    earlier={}
    for version in ['01','02']:
        for r in rows(ROOT/f'Translations/nl/independent-review-{version}/review-decisions.jsonl'):earlier[r['stableId']]=dict(r,evidenceVersion=version)
    rules=load('Source/preserve-exactly-v4.json');rules={r['stableId']:r for r in rules['tableRows']+rules['staticRows']}
    retained=[]
    for r in full:
        assert r['sourceSha256']==rules[r['stableId']]['sourceSha256']
        for k in ['source','target']:assert hashlib.sha256(r[k].encode()).hexdigest()==r[k+'Sha256']
        doc=load(r['authoredPath']);entries=[e for e in doc['entries'] if e.get('stableId')==r['stableId'] or str(e.get('id'))==r['stableId'].rsplit(':',1)[-1]]
        assert len(entries)==1 and entries[0]['target']==r['target']
        if r['stableId'] not in sets['delta']:
            q=earlier[r['stableId']];assert q['sourceSha256']==r['sourceSha256'] and q['targetSha256']==r['targetSha256']
            assert q['decision']=='no-objective-text-finding-in-independent-read'
            retained.append({'stableId':r['stableId'],'evidenceVersion':q['evidenceVersion'],'sourceSha256':r['sourceSha256'],'targetSha256':r['targetSha256'],'mandatoryRegression':r['stableId'] in sets['mandatory-regressions']})
    result={'status':'passed','verifiedHashes':checks,'counts':{k:len(v) for k,v in sets.items()},'reusedUnchangedDecisions':retained,'authoredSetSha256':m['manual']['authoredSetSha256'],'closureSha256':sha(ROOT/cp['cycle3']['closureManifestPath']),'reproduction':None}
    if not final:
        spec=importlib.util.spec_from_file_location('pinned_recipe',ROOT/m['recipePath']);recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)
        recipe.HERE=OUT/'reproduced-closure';recipe.main()
        reproduced=[]
        for p in (ROOT/'Translations/nl/semantic-cycle-3/closure-v2').iterdir():
            if p.name=='closure-manifest.json':continue
            copy=recipe.HERE/p.name;assert p.read_bytes()==copy.read_bytes(),p.name
            reproduced.append({'filename':p.name,'sha256':sha(copy)})
        gen=json.loads((recipe.HERE/'closure-manifest.json').read_text())
        # Only evidence destination paths change in the isolated rerun.
        def normalize(v):
            if isinstance(v,str):return v.replace('Translations/nl/independent-review-03/reproduced-closure','Translations/nl/semantic-cycle-3/closure-v2')
            if isinstance(v,list):return [normalize(x) for x in v]
            if isinstance(v,dict):return {k:normalize(x) for k,x in v.items()}
            return v
        assert normalize(gen)==m
        result['reproduction']={'status':'exact byte parity for every list, rows and selector component; manifest equal after destination normalization','files':reproduced}
    else:
        initial=json.loads((OUT/'preflight.json').read_text());assert initial['verifiedHashes']==checks
        result['reproduction']='reused exact pinned recipe reproduction; inputs unchanged'
    output=OUT/('final-input-recheck.json' if final else 'preflight.json');assert not output.exists();output.write_text(json.dumps(result,indent=2)+'\n')
    print('Verified',len(checks),'hashes; retained',len(retained),'decisions; mandatory retained',sum(r['mandatoryRegression'] for r in retained))
if __name__=='__main__':run('--final' in sys.argv)
