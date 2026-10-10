#!/usr/bin/env python3
"""Reproduce the Indonesian 1.3.19 final offline text gate on unchanged inputs.

Run with --write once to freeze receipts, then --verify to rerun all owning
validators and compare every deterministic output. No game, build or Git action.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOCALE = ROOT / 'Translations/id'
OUT = LOCALE / 'final-gate'
CYCLE = LOCALE / 'semantic-correction-cycle-03'
REVIEW = LOCALE / 'independent-review-03'
PENDING = {}
GUIDS = {'Dialogs':'444ff14f1967f5a4c8eb9e4cf4c913f1',
         'UI':'0cbd8a7a4f543344bb95659de87f67a5',
         'ChecksDialogs':'389c6d80595013c41b85a7197838c4b6'}

def raw(path):
    return (ROOT / path).read_bytes()
def sha(data):
    return hashlib.sha256(data).hexdigest()
def pin(path, expected):
    actual = sha(raw(path))
    assert actual == expected, (path, expected, actual)
    return actual
def load(path):
    return json.loads(raw(path))
def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
def output(name, value, mode):
    data = json_bytes(value)
    path = OUT / name
    if mode == 'write':
        assert not path.exists() and name not in PENDING, path
        PENDING[name] = data
    else:
        assert path.read_bytes() == data, name
    return {'path': 'Translations/id/final-gate/' + name, 'sha256': sha(data)}
def id_list(path):
    data = raw(path).decode('utf-8')
    assert not data or data.endswith('\n')
    result = data.splitlines()
    assert len(result) == len(set(result))
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--write', action='store_true')
    g.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    mode = 'write' if args.write else 'verify'
    artifact = load('Translations/id/semantic-correction-cycle-03/artifact-manifest.json')
    review = load('Translations/id/independent-review-03/review.json')
    review_manifest = load('Translations/id/independent-review-03/evidence-manifest.json')
    assert artifact['targetInputCount'] == 332 and len(artifact['targetInputs']) == 332
    assert review['cleanIndependentVerdict'] is True and review['textFindings'] == review['selectorFindings'] == 0
    assert review['deltaRowsRead'] == 21 and review['unreadRows'] == 0 and review['unchangedPinsAtReviewEnd']
    assert load('Translations/id/independent-review-03/findings.json')['rows'] == []
    for e in review_manifest['files']:
        pin(e['path'], e['sha256'])
    for key in ('sourceAndGlossary','manuals','authoredMapsAndSelectorRecipe','targetInputs','validationSidecars','previousFirstPassParts','previousIndependentReviews'):
        for e in artifact[key]:
            pin(e['path'], e['sha256'])
    pin('Translations/id/semantic-correction-cycle-03/artifact-manifest.json',
        '71ac6a9e0de12b586f1bf6b610ee0f9aeab79c6604e5af1afb5143123482d153')
    pin('Translations/id/semantic-correction-cycle-03/closure.ids.txt', review['closureSha256'])
    pin('Translations/id/semantic-correction-cycle-03/delta-review.ids.txt', review['deltaSha256'])
    state_before = sha(raw('Documentation/localization-state.json'))

    # Reconcile the accepted source/glossary contract and the complete first pass.
    acceptance = load('Documentation/text-source-acceptance-v1.json')
    rules = load('Source/preserve-exactly-v4.json')
    ordered = [r['stableId'] for r in rules['tableRows'] + rules['staticRows']]
    assert len(ordered) == len(set(ordered)) == acceptance['selectedTotalRows'] == 16538
    valid = set(ordered)
    sources = {}
    for name in ('strings','static-text'):
        for line in (ROOT / 'Source/localization-inventory-v3' / (name + '.jsonl')).open(encoding='utf-8'):
            row = json.loads(line)
            if row['stableId'] in valid:
                assert row['stableId'] not in sources
                sources[row['stableId']] = row
    assert set(sources) == valid
    layer = load('Documentation/glossary-translations/id/layer.json')
    master_source = load('/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json')
    master_layers = load('/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary-translations.json')
    source_ids = [e['id'] for e in master_source['entries']]
    assert len(source_ids) == len(set(source_ids)) == 201
    assert list(layer) == source_ids and master_layers['id'] == layer
    source_proof = {
        'schemaVersion':1,'locale':'id','acceptedUnits':16538,
        'sourceAndGlossary':artifact['sourceAndGlossary'],
        'glossaryEntries':201,'sourceIdsAndOrderMatchLocale':True,
        'siteLocaleLayerEqualsApprovedSnapshot':True,
        'siteLocaleLayerCanonicalSha256':sha(json_bytes(layer)),
        'acceptedScopeUnchanged':True,
        'review03ManifestSha256':sha(raw('Translations/id/independent-review-03/evidence-manifest.json')),
        'review03CurrentSourceAndTargetPinsUnchanged':True,
    }
    source_proof_pin = output('source-glossary-applicability.json', source_proof, mode)
    part_rows = []
    last = 0
    for e in artifact['previousFirstPassParts']:
        part = load(e['path'])
        assert part['sourceOrderStart'] == last + 1
        assert part['sourceOrderEnd'] == part['sourceOrderStart'] + part['reviewedRows'] - 1
        assert len(part['rows']) == part['reviewedRows']
        part_rows.extend(part['rows']); last = part['sourceOrderEnd']
    assert last == len(part_rows) == 16538
    assert [r['stableId'] for r in part_rows] == ordered
    assert all(r['source'] == sources[r['stableId']]['source'] for r in part_rows)
    progress = load('Translations/id/semantic-review-progress.json')
    assert progress['reviewedUnits'] == 16538 and progress['semanticPassComplete']
    assert progress['nextSourceOrderIndex'] == 16539 and progress['nextStableId'] is None
    decisions = []
    for cycle, accepted in ((1,83),(2,9),(3,3)):
        base = f'Translations/id/semantic-correction-cycle-{cycle:02d}/'
        a = load(base + 'adjudication.json')
        n = sum(r['decision'] == 'accepted' for r in a['rows'])
        assert n == accepted
        decisions.append({'cycle':cycle,'acceptedCorrections':n,
                          'adjudicationSha256':sha(raw(base+'adjudication.json'))})
    assert sum(d['acceptedCorrections'] for d in decisions) == 95
    r1 = load('Translations/id/independent-review-01/review.json')
    r2 = load('Translations/id/independent-review-02/review.json')
    assert r1['verdict'] == r2['verdict'] == 'corrections required'
    assert r2['deltaRowsRead'] == 324 and r2['supplementalRowsRead'] == 3
    semantic_proof = {'schemaVersion':1,'locale':'id','acceptedUnits':16538,
                      'firstSemanticPassUnits':16538,'firstPassEvidenceParts':35,
                      'firstPassContiguousAndSourceAligned':True,
                      'correctionChain':decisions,'cumulativeAcceptedCorrections':95,
                      'independentReview01':'2182 closure rows; nine findings',
                      'independentReview02':'324 delta rows plus three supplemental dependencies; three findings and selector repair',
                      'independentReview03':'21 delta rows; zero text and selector findings',
                      'unresolvedObjectiveFindings':0,'fullSemanticRestartCondition':'none on unchanged source, glossary, inventory and stable-ID mapping'}
    semantic_proof_pin = output('semantic-chain-proof.json', semantic_proof, mode)

    # Run every owning validator and confirm every sidecar remains byte-identical.
    sidecars = {e['inputPath']: e for e in artifact['validationSidecars']}
    assert len(sidecars) == 332
    targets = {}
    owners = {}
    counts = {'UI':0,'Dialogs':0,'ChecksDialogs':0,'Static':0}
    def validate_entry(entry):
        path = entry['path']
        is_static = path.endswith('static-text-draft.json')
        script = 'Scripts/validate_static_text_draft.py' if is_static else 'Scripts/validate_game_text_batch.py'
        run = subprocess.run([str(ROOT/'.venv/bin/python'),script,path], cwd=ROOT,
                             text=True,capture_output=True)
        assert run.returncode == 0, (path,run.stderr,run.stdout)
        report = json.loads(run.stdout)
        assert report['structuralResult'] == 'passed'
        side = sidecars[path]
        pin(side['path'],side['sha256'])
        assert report.get('batchSha256',report.get('draftSha256')) == entry['sha256']
        return path
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(validate_entry, entry):entry['path'] for entry in artifact['targetInputs']}
        finished = set()
        for future in as_completed(futures):
            finished.add(future.result())
            if len(finished) % 50 == 0:
                print(f'validated {len(finished)}/332 authored inputs', flush=True)
    assert len(finished) == 332
    for entry in artifact['targetInputs']:
        path = entry['path']
        is_static = path.endswith('static-text-draft.json')
        batch = load(path)
        for item in batch['entries']:
            sid = item['stableId'] if is_static else 'string:'+GUIDS[batch['collection']]+':'+str(item['id'])
            assert sid not in targets and sid in valid, sid
            targets[sid] = item['target']; owners[sid] = path
            counts['Static' if is_static else batch['collection']] += 1
    assert set(targets) == valid and sum(counts.values()) == 16538
    assert counts == {'UI':259,'Dialogs':16100,'ChecksDialogs':1,'Static':178}
    assert state_before == sha(raw('Documentation/localization-state.json'))
    structural = {'schemaVersion':1,'locale':'id','rows':16538,'result':'passed',
                  'authoredInputFiles':332,'stringBatches':331,'staticDraftFiles':1,
                  'matchingValidatorSidecars':332,'sidecarBytesUnchanged':True,
                  'acceptedStableIdSetExact':True,'uniqueAndNoExtraIds':True,
                  'byCollection':counts,'sharedValidationStateSha256':state_before}
    structural_pin = output('structural-proof.json',structural,mode)

    # Reproduce all 178 static cells directly from their authored phrase and credits maps.
    draft = load('Translations/id/static-text-draft.json')
    phrases = load('Translations/id/static-phrases.authored.json')
    credits = load('Translations/id/credits-role-map.json')
    assert draft['authoredPhraseMapSha256'] == sha(raw('Translations/id/static-phrases.authored.json'))
    assert draft['creditsRoleMapSha256'] == sha(raw('Translations/id/credits-role-map.json'))
    phrase_map = {p['source']:p['target'] for p in phrases['phrases']}
    assert len(phrase_map) == len(phrases['phrases']) == 75
    repl = {p['source']:p['target'] for p in credits['replacements']}
    assert len(repl) == len(credits['replacements']) == 81
    pattern = re.compile('|'.join(re.escape(s) for s in sorted(repl,key=len,reverse=True)))
    credits_sid = credits['stableId']
    assert credits_sid == 'tmp:level5:59:m_text'
    assert len(draft['entries']) == 178
    assert [x['stableId'] for x in draft['entries']] == [sid for sid in ordered if sid.startswith('tmp:')]
    for item in draft['entries']:
        sid = item['stableId'];source = sources[sid]['source']
        expected = pattern.sub(lambda m:repl[m.group()], source) if sid == credits_sid else phrase_map[source]
        assert item['target'] == expected, sid
    derived = {'schemaVersion':1,'locale':'id','rows':178,'result':'passed',
               'phraseMapRows':75,'phraseDerivedRows':177,'creditsRoleMapRows':81,
               'creditsDerivedRows':1,'staticSourceAndDraftOrderExact':True,
               'authoredPhraseMapSha256':sha(raw('Translations/id/static-phrases.authored.json')),
               'creditsRoleMapSha256':sha(raw('Translations/id/credits-role-map.json')),
               'staticDraftSha256':sha(raw('Translations/id/static-text-draft.json'))}
    derived_pin = output('derived-static-proof.json',derived,mode)

    # Run the full owning preserve-exact validator on the final 16,538 cells.
    sys.path.insert(0,str(ROOT/'Scripts'))
    from preserve_exact import validate
    frozen = OUT / 'preserve-exact-report.json'
    with tempfile.TemporaryDirectory(prefix='.id-final-gate-', dir=OUT) as td:
        temp = Path(td)/'preserve-exact-report.json'
        validate('id', temp)
        data = temp.read_bytes()
    if mode == 'write':
        assert not frozen.exists()
        PENDING['preserve-exact-report.json'] = data
    else:
        assert frozen.read_bytes() == data
    preserve = json.loads(data)
    assert preserve['checkedRows'] == 16538 and preserve['exactResult'] == 'passed'
    preserve_pin = {'path':'Translations/id/final-gate/preserve-exact-report.json','sha256':sha(data)}

    # Reconcile the complete independent delta, unchanged reuse, and every mandatory row.
    selector = subprocess.run([str(ROOT/'.venv/bin/python'),
        'Translations/id/closure-selector-recipe-v3.py','--verify'],cwd=ROOT,
        text=True,capture_output=True,check=True)
    selection = json.loads(selector.stdout)
    assert selection['closureSha256'] == review['closureSha256']
    assert selection['deltaSha256'] == review['deltaSha256']
    closure = set(id_list('Translations/id/semantic-correction-cycle-03/closure.ids.txt'))
    delta = set(id_list('Translations/id/semantic-correction-cycle-03/delta-review.ids.txt'))
    assert len(closure) == 1414 and len(delta) == 21
    coverage = load('Translations/id/independent-review-03/coverage.json')
    reused = load('Translations/id/independent-review-03/reused-decisions.json')
    assert len(coverage) == 21 and len(reused) == 1393
    assert {r['stableId'] for r in coverage} == delta
    assert {r['stableId'] for r in reused} == closure-delta
    for row in coverage:
        sid = row['stableId']
        assert row['sourceTargetRead'] is True and row['findingId'] is None
        assert row['source'] == sources[sid]['source'] and row['target'] == targets[sid]
        assert row['sourceSha256'] == sha(row['source'].encode())
        assert row['targetSha256'] == sha(row['target'].encode())
        assert row['targetFile'] == owners[sid]
    for row in reused:
        sid = row['stableId']
        assert row['sourceSha256'] == sha(sources[sid]['source'].encode())
        assert row['targetSha256'] == sha(targets[sid].encode())
        assert row['status'] == 'no-objective-correction-found'
    closure_proof = {'schemaVersion':1,'locale':'id','result':'passed',
                     'currentClosureIds':1414,'exactDeltaIds':21,'cleanIndependentDeltaReads':21,
                     'reusedExactApplicablePriorIndependentDecisions':1393,
                     'closureSha256':review['closureSha256'],'deltaSha256':review['deltaSha256'],
                     'reviewer':review['reviewer'],'unresolvedObjectiveFindings':0,
                     'retiredPriorDependencies':38,'restoredCallbackSelectedNormally':True}
    closure_pin = output('closure-proof.json',closure_proof,mode)
    catalog = load('Translations/id/semantic-correction-cycle-03/mandatory-regression-catalog.json')
    groups = {name:set(id_list(e['path'])) for name,e in catalog['groups'].items()}
    mandatory = set().union(*groups.values())
    decisions = load('Translations/id/independent-review-03/mandatory-regression-decisions.json')
    assert len(mandatory) == len(decisions) == 845
    assert {r['stableId'] for r in decisions} == mandatory
    fresh = reused_mandatory = 0
    for row in decisions:
        sid = row['stableId']
        assert row['sourceSha256'] == sha(sources[sid]['source'].encode())
        assert row['targetSha256'] == sha(targets[sid].encode())
        assert set(row['groups']) == {name for name,group in groups.items() if sid in group}
        assert row['status'] == 'no-objective-correction-found'
        if sid in delta:
            assert row['mode'] == 'current independent full-unit delta read';fresh += 1
        else:
            assert row['mode'] == 'exact applicable prior independent decision'
            assert sid in closure-delta;reused_mandatory += 1
    assert (fresh,reused_mandatory) == (10,835)
    mandatory_proof = {'schemaVersion':1,'locale':'id','count':845,'freshReads':10,
                       'reusedUnchangedIndependentDecisions':835,'result':'passed',
                       'catalogSha256':sha(raw('Translations/id/semantic-correction-cycle-03/mandatory-regression-catalog.json')),
                       'decisionEvidenceSha256':sha(raw('Translations/id/independent-review-03/mandatory-regression-decisions.json')),
                       'everyIdPresentWithCurrentSourceAndTargetHash':True,
                       'everyGroupAndDecisionModeApplicable':True}
    mandatory_pin = output('mandatory-regression-proof.json',mandatory_proof,mode)
    assert review['closureSha256'] == sha(raw('Translations/id/semantic-correction-cycle-03/closure.ids.txt'))
    assert review['deltaSha256'] == sha(raw('Translations/id/semantic-correction-cycle-03/delta-review.ids.txt'))
    assert state_before == sha(raw('Documentation/localization-state.json'))
    receipt = {'schemaVersion':1,'locale':'id','gameVersion':'1.3.19',
               'status':'final offline author gate passed on unchanged reviewed text inputs',
               'acceptedUnits':16538,'firstSemanticPassUnits':16538,
               'unresolvedObjectiveFindings':0,'independentClean':True,
               'independentReviewer':review['reviewer'],
               'currentHashesUnchanged':True,
               'mandatoryRegression':{'count':845,'freshReads':10,
                   'reusedUnchangedIndependentDecisions':835,'result':'passed'},
               'structural':{'rows':16538,'result':'passed','batches':331,'sidecars':332},
               'derivedStatic':{'rows':178,'result':'passed'},
               'preserveExactReport':preserve_pin,
               'authoredFileCount':332,
               'sourceGlossaryProof':source_proof_pin,'semanticChainProof':semantic_proof_pin,
               'structuralProof':structural_pin,'derivedStaticProof':derived_pin,
               'closureProof':closure_pin,'mandatoryRegressionProof':mandatory_pin,
               'review03Sha256':sha(raw('Translations/id/independent-review-03/review.json')),
               'review03EvidenceManifestSha256':sha(raw('Translations/id/independent-review-03/evidence-manifest.json')),
               'cycle03ArtifactManifestSha256':sha(raw('Translations/id/semantic-correction-cycle-03/artifact-manifest.json')),
               'selectorRecipeSha256':sha(raw('Translations/id/closure-selector-recipe-v3.py')),
               'selectorConfigSha256':sha(raw('Translations/id/closure-selector-config-v3.json')),
               'sharedValidationStateSha256':state_before,
               'boundaries':{'runtime':'not run','dynamicSubstitution':'not executed',
                   'renderedLayoutAndFonts':'not tested','buildAndInstallation':'not run',
                   'imagesAndTextures':'excluded by owner','gitIntegration':'root pending'}}
    receipt_pin = output('gate-receipt.json',receipt,mode)
    if mode == 'write':
        assert all(not (OUT / name).exists() for name in PENDING)
        for name, data in PENDING.items():
            (OUT / name).write_bytes(data)
    print(json.dumps({'mode':mode,'result':'passed','acceptedUnits':16538,
                      'validatedBatches':331,'staticRows':178,'mandatoryFresh':10,
                      'mandatoryReused':835,'receiptSha256':receipt_pin['sha256']},ensure_ascii=False))

if __name__ == '__main__':
    main()
