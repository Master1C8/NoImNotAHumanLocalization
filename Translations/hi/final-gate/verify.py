#!/usr/bin/env python3
"""Read-only Hindi final-gate reconciliation. No acceptance or output writes.

Historical cycle004 recipe hashes are evaluated against the archived batch080
sidecar preimage only. Current acceptance contracts always use the live sidecar.
Run with PYTHONDONTWRITEBYTECODE=1 and the canonical .venv/bin/python.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
HI = ROOT / 'Translations/hi'
GATE = HI / 'final-gate'
REVIEW = HI / 'independent-review-04'
sys.path.insert(0, str(ROOT / 'Scripts'))
from locale_text_inputs import accepted_inputs, checked_files, current_text
from preserve_exact import MANIFEST


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def id_sha(ids):
    return text_sha('\n'.join(ids) + '\n')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def reconcile():
    transition = read(GATE / 'administrative-transition.json')
    preimage = transition['before']
    live_sidecar = ROOT / preimage['path']
    archived_sidecar = ROOT / preimage['archivePath']
    assert sha(archived_sidecar) == preimage['sha256'] == preimage['archiveSha256']
    assert sha(live_sidecar) == transition['after']['sha256']
    assert sha(ROOT / transition['validator']['path']) == transition['validator']['sha256']
    assert transition['semanticInputsChanged'] == 0 and transition['administrativePinsChanged'] == 1
    assert read(live_sidecar)['batchSha256'] == sha(HI / 'dialogue-batch-080.json')

    manifest = REVIEW / 'final-artifact-manifest.json'
    assert sha(manifest) == 'd2d683071f97e6cf91acb1ed8f6c26798deb70e05ef3a62546038c87e2ccae76'
    sealed = read(manifest)
    assert len(checked_files(sealed['artifacts'])) == sealed['artifactCount'] == 22
    assert sealed['reviewer'] == '/root/hi_independent_review_04'
    pins = read(REVIEW / 'final-unchanged-input-pins.json')['pins']
    changed = [p for p, h in pins.items() if sha(ROOT / p) != h]
    assert len(pins) == 806 and changed == [preimage['path']]
    assert pins[preimage['path']] == sha(archived_sidecar)

    values, authored = current_text('hi')  # live mutable sidecars, exact spans, selected scope, credits
    current_hashes = checked_files(authored)
    assert len(authored) == 335 and len(values) == 16538
    source = lines(ROOT / 'Source/localization-inventory-v3/strings.jsonl')
    static = lines(ROOT / 'Source/localization-inventory-v3/static-text.jsonl')
    identities = {(r['collection'], int(r['stableId'].rsplit(':', 1)[1])): r for r in source}
    identities.update({('static', r['stableId']): r for r in static})
    targets = {identities[k]['stableId']: value for k, value in values.items()}
    accepted = [r for r in source + static if r['stableId'] in targets]
    ids = [r['stableId'] for r in accepted]
    by_id = {r['stableId']: r for r in accepted}
    assert len(ids) == len(set(ids)) == 16538

    first = read(HI / 'semantic-pass-001-progress-immutable.json')
    assert first['acceptedUnits'] == first['reviewedUnits'] == 16538
    assert first['remainingUnits'] == 0 and first['nextId'] is None
    assert id_sha(ids) == first['reviewOrderIdListSha256LfFinalNewline'] == first['reviewedPrefixIdListSha256LfFinalNewline']
    baseline = first['reviewedTargetFileHashes']
    assert len(baseline) == 335 and sum(r['reviewedUnits'] for r in baseline.values()) == 16538
    evolved = {p: r['sha256'] for p, r in baseline.items()}
    phrase_hash = first['reviewedInputHashes']['Translations/hi/static-phrases-authored.json']
    applied_ids = set()
    cycles = []
    for number in range(1, 5):
        stem = f'semantic-cycle-{number:03}'
        plan = read(HI / (stem + '-application-plan.json'))
        adjudication = read(HI / (stem + '-adjudication.json'))
        application = read(HI / (stem + '-applied-evidence.json'))
        assert application['applicationPlanSha256'] == sha(HI / (stem + '-application-plan.json'))
        assert plan['adjudicationSha256'] == application['adjudicationSha256'] == sha(HI / (stem + '-adjudication.json'))
        if 'preflightSha256' in plan:
            assert plan['preflightSha256'] == sha(HI / (stem + '-preflight.json'))
        items = adjudication.get('items', [adjudication.get('item')])
        proposals = {r['stableId']: r for r in items if 'acceptedFullTarget' in r}
        assert len(proposals) == plan['changedCount']
        records = plan.get('files', [plan.get('file')])
        changed_ids = set()
        for record in records:
            path = record['path']
            before_path = HI / (stem + '-before-files') / Path(path).name
            after_path = HI / (stem + '-after-files') / Path(path).name
            assert sha(before_path) == record['beforeSha256'] == evolved[path]
            assert sha(after_path) == record['afterSha256']
            before, after = read(before_path), read(after_path)
            assert {k: v for k, v in before.items() if k != 'entries'} == {k: v for k, v in after.items() if k != 'entries'}
            assert len(before['entries']) == len(after['entries']) == baseline[path]['reviewedUnits']
            observed = set()
            for old, new in zip(before['entries'], after['entries']):
                assert {k: v for k, v in old.items() if k != 'target'} == {k: v for k, v in new.items() if k != 'target'}
                if old['target'] == new['target']:
                    continue
                identity = ('static', old['stableId']) if 'stableId' in old else (before['collection'], old['id'])
                sid = identities[identity]['stableId']
                proposed = proposals[sid]
                assert proposed['source'] == by_id[sid]['source']
                assert old['target'] == proposed['before'] and new['target'] == proposed['acceptedFullTarget']
                observed.add(sid)
            expected = set(record.get('changedIds', plan.get('changedIds', [])))
            assert observed == expected
            changed_ids.update(observed)
            evolved[path] = record['afterSha256']
        assert changed_ids == set(proposals) and len(changed_ids) == plan['changedCount']
        applied_ids.update(changed_ids)
        if plan.get('phraseMap'):
            mapping = plan['phraseMap']
            assert sha(HI / (stem + '-before-files') / Path(mapping['path']).name) == mapping['beforeSha256'] == phrase_hash
            assert sha(HI / (stem + '-after-files') / Path(mapping['path']).name) == mapping['afterSha256']
            phrase_hash = mapping['afterSha256']
        cycles.append({'cycle': number, 'correctedUnits': len(changed_ids), 'authoredFiles': len(records),
                       'applicationPlanSha256': sha(HI / (stem + '-application-plan.json'))})
    assert evolved == current_hashes
    assert sha(HI / 'static-phrases-authored.json') == phrase_hash
    for path, h in first['reviewedInputHashes'].items():
        if path not in evolved and path != 'Translations/hi/static-phrases-authored.json':
            assert sha(ROOT / path) == h, path

    checkpoint = read(ROOT / 'Documentation/hi-text-checkpoint.json')
    master = Path('/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human')
    assert sha(master / 'glossary.json') == checkpoint['glossary']['sourceRawSha256']
    layer = read(ROOT / checkpoint['glossary']['localeLayer'])
    assert read(master / 'glossary-translations.json')['hi'] == layer and len(layer) == 201
    assert [r['id'] for r in read(master / 'glossary.json')['entries']] == list(layer)
    assert sha(ROOT / checkpoint['glossary']['localeLayer']) == checkpoint['glossary']['localeLayerSha256']
    glossary_acceptance = read(ROOT / 'Documentation/glossary-translations/acceptance-manifest.json')
    glossary_hi = glossary_acceptance['accepted']['hi']
    assert glossary_hi['layerRawSha256'] == sha(ROOT / checkpoint['glossary']['localeLayer'])
    for path, h in glossary_hi['evidenceSha256'].items():
        assert sha(ROOT / 'Documentation/glossary-translations' / path) == h
    approved = read(ROOT / checkpoint['glossary']['acceptedReview'])
    assert approved['status'] == 'editorially-accepted-canonical' and approved['entryCount'] == 201
    assert approved['sourceRawSha256'] == sha(master / 'glossary.json')
    assert approved['layerRawSha256'] == glossary_hi['layerRawSha256']

    full = read(HI / 'semantic-cycle-004-full-corpus.json')
    assert full['rows'] == 16538 and full['structuralResult'] == full['exactResult'] == 'passed'
    assert checked_files(full['authoredFiles']) == current_hashes
    for field, path in [('validatorSha256', 'Scripts/validate_locale_corpus.py'),
                        ('inputLoaderSha256', 'Scripts/locale_text_inputs.py'),
                        ('sourceInventorySha256', 'Source/localization-inventory-v3/strings.jsonl'),
                        ('staticInventorySha256', 'Source/localization-inventory-v3/static-text.jsonl')]:
        assert full[field] == sha(ROOT / path)
    for name, h in full['owningValidators'].items():
        assert sha(ROOT / 'Scripts' / name) == h

    # Reproduce immutable historic recipe without overwriting it or restoring live state.
    # The one changed administrative pin resolves to its exact archived preimage;
    # all semantic inputs and live acceptance sidecars were verified above.
    recipe = HI / 'build-semantic-cycle-004-closure.py'
    spec = importlib.util.spec_from_file_location('hi_historic_cycle004', recipe)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_sha = module.sha
    module.sha = lambda path: sha(archived_sidecar) if Path(path).resolve() == live_sidecar.resolve() else original_sha(path)
    outputs, closure, delta = module.build()  # pure build; options invoke --verify only
    for name, content in outputs.items():
        assert (HI / name).read_text(encoding='utf-8') == content, name
    assert sha(recipe) == closure['selectorSha256']
    closure_ids = [r['stableId'] for r in closure['reviewRows']]
    assert len(closure_ids) == 5216 and id_sha(closure_ids) == closure['closureIdListSha256LfFinalNewline']
    assert len(delta['deltaIds']) == 9 and id_sha(delta['deltaIds']) == delta['deltaIdListSha256LfFinalNewline']
    for r in closure['reviewRows']:
        assert r['source'] == by_id[r['stableId']]['source'] and r['target'] == targets[r['stableId']]
    catalog = read(ROOT / closure['catalogPath'])
    required = set()
    for group in catalog['groups']:
        assert len(group['ids']) == len(set(group['ids'])) == group['count']
        assert id_sha(group['ids']) == group['idsSha256']
        required.update(group['ids'])
    assert len(required) == 4805 and required <= set(ids)
    assert required <= set(closure['components']['mandatoryRegression'])
    assert id_sha([sid for sid in ids if sid in required]) == closure['catalogRequiredIdListSha256LfFinalNewline']

    def decisions(path, expected):
        rows = lines(path)
        assert len(rows) == len({r['stableId'] for r in rows}) == len(expected)
        assert [r['stableId'] for r in rows] == [sid for sid in ids if sid in set(expected)]
        for r in rows:
            sid = r['stableId']
            assert r['sourceSha256'] == text_sha(by_id[sid]['source'])
            assert r.get('currentTargetSha256', r.get('targetSha256')) == text_sha(targets[sid])
            assert not r['findingIds'] and r['result'] in ('no-objective-finding-in-static-read', 'clean-no-objective-finding')
            assert r['glossarySha256'] == closure['glossaryLayerSha256']
            assert r['compiledBindingSha256'] == closure['compiledRuntimeBindingsSha256']
            if r.get('priorDecisionArtifact'):
                prior = lines(ROOT / r['priorDecisionArtifact'])
                previous = next(x for x in prior if x['stableId'] == sid)
                assert previous['sourceSha256'] == r['sourceSha256']
                assert previous.get('currentTargetSha256', previous.get('targetSha256')) == text_sha(targets[sid])
        return rows

    # Cache ledgers: reused decisions must not repeatedly parse large JSONL files.
    original_lines = lines
    ledger_cache = {}
    def cached_lines(path):
        key = str(Path(path).resolve())
        if key not in ledger_cache:
            ledger_cache[key] = original_lines(path)
        return ledger_cache[key]
    globals()['lines'] = cached_lines
    closure_decisions = decisions(REVIEW / 'per-id-current-closure-decisions.jsonl', closure_ids)
    catalog_decisions = decisions(REVIEW / 'mandatory-catalog-per-id-decisions.jsonl', required)
    fresh = decisions(REVIEW / 'per-id-fresh-decisions.jsonl', delta['deltaIds'])
    assert len([r for r in closure_decisions if r.get('priorDecisionArtifact')]) == 5207
    assert all(r.get('priorDecisionArtifact') for r in catalog_decisions)
    findings = read(REVIEW / 'consolidated-full-unit-findings.json')
    assert findings['status'] == 'clean' and not findings['textFindings'] and not findings['recipeFindings']
    assert findings['closureSha256'] == sha(HI / 'semantic-cycle-004-closure.json')
    assert findings['deltaSha256'] == sha(HI / 'semantic-cycle-004-review-delta.json')
    coverage = read(REVIEW / 'final-coverage-and-regression-proof.json')
    assert coverage['fullSemanticCorpusCoveragePreserved'] == 16538 and coverage['cleanIndependentAcceptance'] is True
    assert coverage['mandatoryFreshThisDelta'] == 0 and coverage['mandatoryExactPriorApplicable'] == 4805
    assert coverage['consolidatedTextFindings'] == coverage['consolidatedRecipeFindings'] == 0
    exact = read(GATE / 'preserve-exact.json')
    assert exact['checkedRows'] == 16538 and exact['exactResult'] == 'passed' and exact['locale'] == 'hi'
    assert exact['manifestSha256'] == sha(MANIFEST) and checked_files(exact['inputFiles']) == current_hashes
    technical = read(ROOT / closure['technicalContextPath'])
    assert technical['technicalFragmentCount'] == len(technical['technicalFragments']) == 7
    assert len(set(technical['translatedSupplierIds'])) == 17
    for fragment in technical['technicalFragments']:
        payload = {k: v for k, v in fragment.items() if k != 'fragmentSha256'}
        assert fragment['fragmentSha256'] == text_sha(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
    assert id_sha(technical['translatedSupplierIds']) == technical['translatedSupplierIdListSha256LfFinalNewline']
    return {'schemaVersion': 1, 'locale': 'hi', 'result': 'passed', 'acceptedUnits': 16538,
            'firstSemanticPassUnits': 16538, 'authoredFiles': 335, 'currentSidecars': 335,
            'authoredSemanticHashesUnchanged': True, 'administrativePinsChanged': 1,
            'firstPassCorrectionChain': cycles, 'correctionApplications': sum(r['correctedUnits'] for r in cycles),
            'uniqueCorrectedIds': len(applied_ids), 'independentReviewer': sealed['reviewer'],
            'independentCurrentClosure': 5216, 'independentFreshDelta': len(fresh), 'exactPriorClosure': 5207,
            'mandatoryCatalogUniqueIds': 4805, 'mandatoryFreshReadsReview04': 0, 'mandatoryExactPriorDecisions': 4805,
            'mandatoryComponentIds': len(closure['components']['mandatoryRegression']),
            'myceliumActualSourceInflections': 22, 'derivedStaticRows': 178,
            'commonOptionExpansionRows': [2593, 245, 45], 'technicalSupplierFragmentsSeparate': 7,
            'translatedUiSupplierLabels': 17, 'wholeCorpusGuard': 'cycle004 reused on exact unchanged authored/source/code pins',
            'preserveExactCheckedRows': 16538, 'unresolvedObjectiveFindings': 0,
            'missingAcceptedIds': [], 'extraAcceptedIds': [], 'rootAcceptance': 'pending', 'runtime': 'not-run'}


def expected_acceptance(handoff):
    """Reproduce exact output bytes of the pinned acceptance tool, without writes."""
    evidence, authored = checked_files(handoff['evidenceFiles']), checked_files(handoff['authoredFiles'])
    ref = handoff['preserveExactReport']
    inputs = {'Translations/hi/final-gate/root-handoff.json': sha(GATE / 'root-handoff.json'),
              **evidence, **authored, ref['path']: sha(ROOT / ref['path'])}
    result = {'schemaVersion': 1, 'gameVersion': '1.3.19', 'sourceLocale': 'ru', 'locale': 'hi',
              'status': 'text editorially accepted offline', 'acceptedUnits': 16538,
              'firstSemanticPassUnits': 16538, 'unresolvedObjectiveFindings': 0,
              'independentClean': True, 'independentReviewer': handoff['independentReviewer'],
              'mandatoryRegression': handoff['mandatoryRegression'], 'structuralRows': 16538,
              'derivedStaticRows': 178, 'inputSha256': inputs,
              'acceptanceToolSha256': sha(ROOT / 'Scripts/accept_locale_text.py'),
              'runtime': 'not-run', 'fontRenderingLayout': 'not-run', 'imagesTextures': 'excluded',
              'remainingLimits': handoff['remainingLimits']}
    return json.dumps(result, ensure_ascii=False, indent=2) + '\n'


def verify_handoff():
    handoff = read(GATE / 'root-handoff.json')
    assert handoff['locale'] == 'hi' and handoff['acceptedUnits'] == handoff['firstSemanticPassUnits'] == 16538
    assert handoff['unresolvedObjectiveFindings'] == 0 and handoff['independentClean'] is True
    assert handoff['independentReviewer'] == '/root/hi_independent_review_04' and handoff['currentHashesUnchanged'] is True
    assert handoff['structural'] == {'rows': 16538, 'result': 'passed'}
    assert handoff['derivedStatic'] == {'rows': 178, 'result': 'passed'}
    r = handoff['mandatoryRegression']
    assert r == {'count': 4805, 'freshReads': 0, 'reusedUnchangedIndependentDecisions': 4805, 'result': 'passed'}
    checked_files(handoff['evidenceFiles'])
    authored = checked_files(handoff['authoredFiles'])
    _, current = current_text('hi')
    assert authored == {r['path']: r['sha256'] for r in current}
    exact_ref = handoff['preserveExactReport']
    assert sha(ROOT / exact_ref['path']) == exact_ref['sha256']
    exact = read(ROOT / exact_ref['path'])
    assert exact['checkedRows'] == 16538 and exact['exactResult'] == 'passed' and checked_files(exact['inputFiles']) == authored
    assert exact['manifestSha256'] == sha(MANIFEST)
    proposal = read(GATE / 'integration-proposal.json')
    proposed = ROOT / proposal['proposedAcceptanceOutput']
    assert proposed.is_relative_to(ROOT / 'Documentation') and not proposed.with_suffix('.pending.json').exists()
    expected = expected_acceptance(handoff)
    assert text_sha(expected) == proposal['expectedAcceptanceSha256']
    assert proposal['acceptanceToolSha256'] == sha(ROOT / 'Scripts/accept_locale_text.py')
    if proposed.exists():
        assert proposed.read_text(encoding='utf-8') == expected
        accepted_inputs('hi', proposed, ROOT / exact_ref['path'])  # read-only post-integration check
    checked_files(proposal['integrationFiles'])
    assert all(r['path'].startswith('Translations/hi/') for r in proposal['integrationFiles'])
    special = {'Translations/hi/final-gate/integration-proposal.json',
               'Translations/hi/final-gate/integration-proposal.sha256.json'}
    actual_paths = {str(p.relative_to(ROOT)) for p in HI.rglob('*') if p.is_file()}
    assert actual_paths == {r['path'] for r in proposal['integrationFiles']} | special
    assert proposal['handoffSha256'] == sha(GATE / 'root-handoff.json')
    assert sha(GATE / 'integration-proposal.json') == read(GATE / 'integration-proposal.sha256.json')['sha256']


if __name__ == '__main__':
    result = reconcile()
    assert result == read(GATE / 'reconciliation.json')
    verify_handoff()
    print(json.dumps(result, ensure_ascii=False))
