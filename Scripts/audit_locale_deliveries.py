"""Audit the complete thirteen-locale offline delivery without launching a game.

Reuse serialized readback evidence only on unchanged source, code, acceptance,
report and artifact hashes. Reopen every ZIP member. Write one new audit receipt.
"""
import argparse
import datetime
import hashlib
import json
import subprocess
from pathlib import Path
from zipfile import ZipFile

from locale_text_inputs import accepted_inputs, project_path, read
from probe_assets import DEFAULT_GAME, ROOT, digest, require

LOCALES = ('id', 'cs', 'hu', 'nl', 'fa', 'ro', 'hi', 'fil', 'el', 'bg', 'sr', 'sw', 'he')
THAI_ZIP_SHA256 = '300a409c6e0f6eae576bda12b20cb40e81f52d3998988ad23aa3f7d242cef24a'


def tracked_blobs(records):
    paths = sorted(records)
    raw = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=ROOT,
                                  input=''.join('HEAD:' + p + '\n' for p in paths).encode())
    cursor = 0
    for path in paths:
        end = raw.index(b'\n', cursor)
        header = raw[cursor:end].split()
        require(len(header) == 3 and header[1] == b'blob', 'Missing canonical committed input: ' + path)
        size = int(header[2])
        cursor = end + 1
        require(hashlib.sha256(raw[cursor:cursor + size]).hexdigest() == records[path],
                'Canonical committed input differs: ' + path)
        cursor += size
        require(raw[cursor:cursor + 1] == b'\n', 'Malformed Git batch output')
        cursor += 1
    require(cursor == len(raw), 'Unexpected Git batch tail')


def audit(output):
    require(output.is_relative_to(ROOT / 'Documentation') and not output.exists(), 'Use a new audit receipt')
    require(subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT) == b'main\n',
            'Canonical branch is not main')
    require(not subprocess.check_output(['git', 'diff', '--cached', '--name-only', '-z'], cwd=ROOT),
            'Pending index work must be reconciled before final audit')
    original_inputs, committed, rows = {}, {}, []
    for locale in LOCALES:
        acceptance_path = ROOT / f'Documentation/{locale}-semantic-acceptance-v1.json'
        package = ROOT / f'outputs/{locale}-only-package-v1'
        report_path, verification_path = package / 'report.json', package / 'verification.json'
        report, verification = read(report_path), read(verification_path)
        text_path = project_path(report['textReportPath'])
        base_path = project_path(report['baseReportPath'])
        text, base = read(text_path), read(base_path)
        acceptance, exact, authored = accepted_inputs(locale, acceptance_path, project_path(text['exactReportPath']))
        require(acceptance['acceptanceToolSha256'] == digest(ROOT / 'Scripts/accept_locale_text.py') and
                acceptance['unresolvedObjectiveFindings'] == 0, 'Acceptance tool/decision changed')
        committed[str(acceptance_path.relative_to(ROOT))] = digest(acceptance_path)
        committed.update({p: h for p, h in acceptance['inputSha256'].items() if p.startswith('Translations/')})
        committed.update(authored)
        require(report['locale'] == locale and report['gameVersion'] == '1.3.19' and
                report['newLocaleCount'] == 1 and report['translatedTextValues'] == 16538 and
                report['rtlOriginalTextValues'] == 165 and not report['texturesAndImagesTranslated'] and
                report['originalGameUnchanged'] and not report['installerIncluded'], 'Package scope differs')
        require(digest(base_path) == report['baseReportSha256'] == text['baseReportSha256'] and
                digest(text_path) == report['textReportSha256'] == verification['deliveredTextObjects']['reportSha256'] and
                digest(text_path.parent / 'verification.json') == report['textVerificationSha256'] and
                digest(acceptance_path) == text['semanticAcceptanceSha256'] and
                digest(project_path(text['exactReportPath'])) == text['exactReportSha256'], 'Layer pins changed')
        require(text['builderSha256'] == digest(ROOT / 'Scripts/build_locale_text.py') and
                verification['verifierSha256'] == digest(ROOT / 'Scripts/package_locale_text.py') and
                verification['nativeVerifierSha256'] == digest(ROOT / 'Scripts/verify_locale_native.py') and
                verification['textVerifierSha256'] == digest(ROOT / 'Scripts/verify_locale_text.py'), 'Readback code changed')
        require(verification['result'] == 'passed' and verification['reportSha256'] == digest(report_path) and
                verification['newLocales'] == [locale] and verification['newUiKeys'] == ['language_' + locale] and
                verification['artifactHashesCompared'] == 31 and verification['translatedTextValuesCompared'] == 16538 and
                verification['rtlOriginalTextValuesCompared'] == 165 and verification['fontRolesCompared'] == 3,
                'Delivered readback scope differs')
        native, delivered = verification['nativeObjects'], verification['deliveredTextObjects']
        require(native['result'] == 'passed' and native['originalNativeObjectsCompared'] == 5017 and
                native['newLocale'] == locale and native['newUiKey'] == 'language_' + locale and
                delivered['tableRowsCompared'] == 16360 and delivered['staticRowsCompared'] == 178 and
                delivered['rtlOriginalTextRowsCompared'] == 165 and delivered['selectedObjectsAllOtherFieldsCompared'] == 181 and
                delivered['unchangedObjectsCompared'] == (12752 if locale == 'he' else 12749) and
                delivered['serializedValuesResult'] == delivered['allOtherOverlayFieldsResult'] == 'passed',
                'Native/serialized field evidence incomplete')
        require(set(base['languages']) == {locale} and text['baseLanguages'] == [locale] and
                len(base['artifacts']) == 24 and len(text['artifacts']) == 10 and
                set(report['artifacts']) == set(base['artifacts']) | set(text['artifacts']), 'Locale/layer union differs')
        expected = {p: v['sha256'] for p, v in report['artifacts'].items()}
        require(len(expected) == 31, 'Artifact count differs')
        for path, sha in expected.items():
            require((package / path).resolve().is_relative_to(package) and digest(package / path) == sha,
                    'Actual delivered artifact changed: ' + path)
        for path, sha in {**base['inputs'], **text['sourceGameInputs']}.items():
            require(path not in original_inputs or original_inputs[path] == sha, 'Original source pins conflict')
            original_inputs[path] = sha
        expected.update({'report.json': digest(report_path), 'verification.json': digest(verification_path)})
        archive = ROOT / f'dist/NoImNotAHuman-{locale}-preview-v1.zip'
        receipt_path = archive.with_suffix('.zip.json')
        receipt = read(receipt_path)
        require(receipt['locale'] == locale and receipt['archivedArtifacts'] == 31 and
                receipt['allMembersReadBack'] == 33 and receipt['sha256'] == digest(archive), 'Archive receipt differs')
        with ZipFile(archive) as zipped:
            require(zipped.namelist() == sorted(expected) and zipped.testzip() is None, 'ZIP member set/CRC differs')
            for name, sha in expected.items():
                require(hashlib.sha256(zipped.read(name)).hexdigest() == sha, 'Actual ZIP member differs: ' + name)
        proof = ROOT / ('Documentation/locale-delivery-proof-v1' if locale == 'nl' else
                        f'Documentation/{locale}-delivery-proof-v1')
        prefix = 'nl-' if locale == 'nl' else ''
        for name, live in [('package', report_path), ('package-verification', verification_path), ('archive', receipt_path)]:
            pin = proof / f'{prefix}{name}.json'
            require(digest(pin) == digest(live), 'Canonical delivery proof differs')
            committed[str(pin.relative_to(ROOT))] = digest(pin)
        require(all(verification[k] == 'not-run' for k in ('runtime', 'installation', 'fontRenderingLayout')),
                'Unsupported runtime claim')
        rows.append({'locale': locale, 'acceptedUnits': 16538, 'mandatory': acceptance['mandatoryRegression'],
                     'archive': str(archive.relative_to(ROOT)), 'archiveSha256': receipt['sha256'],
                     'actualZipMembersRead': len(expected), 'reusedSerializedReadbackOnExactPins': True})
    for path, sha in original_inputs.items():
        require(digest(DEFAULT_GAME / path) == sha, 'Original game build input changed: ' + path)
    require(digest(ROOT / 'dist/NoImNotAHuman-th-preview-v1.zip') == THAI_ZIP_SHA256, 'Original Thai ZIP changed')
    gates_path = ROOT / 'Documentation/locale-delivery-proof-v1/negative-gates-canonical.json'
    gates = read(gates_path)
    for field, script in [('checkerSha256', 'check_locale_build_gates.py'),
                          ('inputModuleSha256', 'locale_text_inputs.py'),
                          ('builderSha256', 'build_locale_text.py')]:
        require(gates[field] == digest(ROOT / 'Scripts' / script), 'Cached regression code changed')
    require(len(gates['results']) == 4 and sum(r['result'].startswith('rejected') for r in gates['results']) == 3 and
            gates['results'][-1]['case'] == 'matching positive control' and
            gates['results'][-1]['result'] == 'passed real acceptance preflight', 'Negative/positive gate evidence incomplete')
    parity_path = ROOT / 'Documentation/locale-delivery-proof-v1/thai-payload-parity.json'
    parity = read(parity_path)
    require(parity['result'] == 'passed' and parity['artifactsByteIdentical'] == 10 and
            parity['originalThaiZipSha256'] == THAI_ZIP_SHA256 and
            parity['builderSha256'] == digest(ROOT / 'Scripts/build_locale_text.py') and
            parity['inputModuleSha256'] == digest(ROOT / 'Scripts/locale_text_inputs.py'), 'Thai parity evidence changed')
    for path in (gates_path, parity_path):
        committed[str(path.relative_to(ROOT))] = digest(path)
    for name in ('build_locale_text.py', 'locale_text_inputs.py', 'verify_locale_text.py', 'verify_locale_native.py'):
        committed['Scripts/' + name] = digest(ROOT / 'Scripts' / name)
    tracked_blobs(committed)
    result = {'schemaVersion': 1, 'result': 'passed', 'capturedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'capturedCanonicalHead': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'auditCodeSha256': digest(Path(__file__)), 'requestedLocales': list(LOCALES), 'verifiedLocales': rows,
              'cachedRegressionEvidenceSha256': digest(gates_path), 'cachedThaiParityEvidenceSha256': digest(parity_path),
              'committedInputBlobsCompared': len(committed), 'originalBuildInputsChecked': original_inputs,
              'thaiZipSha256': THAI_ZIP_SHA256, 'runtime': 'not-run', 'installation': 'not-run',
              'fontRenderingLayout': 'not-run', 'imagesTextures': 'excluded', 'publicationPushDeployment': 'not-performed',
              'boundary': 'Final hash/ZIP/source/committed-input reconciliation. Serialized field readbacks are reused only on exact code/source/acceptance/artifact pins; no fresh gameplay or linguistic reread is claimed.'}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'result': 'passed', 'locales': len(rows), 'receipt': str(output.relative_to(ROOT)),
                      'committedBlobs': len(committed), 'zipMembersRead': sum(r['actualZipMembersRead'] for r in rows)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    audit(args.output.resolve())
