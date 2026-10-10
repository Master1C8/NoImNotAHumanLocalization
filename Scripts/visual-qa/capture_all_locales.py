#!/usr/bin/env python3
"""Capture six genuine in-game scenes sequentially for the canonical locale roster.

Completed runs are retained; resume revalidates code, archive, checkpoint and frame
pins. Automated recognition and independent visual review are separate gates.
"""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import re
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import capture_six_scenes as scenes
import select_intro_caption as captions

ROOT = scenes.ROOT
TRAINING = ROOT / 'Resources/VisualQA/six-scenes-neutral-v1'
ROSTER = ROOT / 'Documentation/localization-state.json'
RENDERER = ROOT / 'Resources/VisualQA/capture-renderer-v1.json'
HINDI_RENDERER = ROOT / 'Resources/VisualQA/capture-renderer-hi-v1.json'
HEBREW_RENDERER = ROOT / 'Resources/VisualQA/capture-renderer-he-v1.json'


def locales():
    rows = json.loads(ROSTER.read_text())['targetLocales']
    scenes.require(len(rows) == len(set(rows)) == 14, 'Canonical locale roster changed')
    return rows


def archive_for(locale):
    pattern = 'NoImNotAHuman-' + locale + '-runtime-preview-v*.zip'
    candidates = [(int(re.fullmatch('NoImNotAHuman-' + re.escape(locale) + r'-runtime-preview-v(\d+)\.zip',p.name).group(1)),p)
                  for p in (ROOT/'dist').glob(pattern) if re.fullmatch('NoImNotAHuman-' + re.escape(locale) + r'-runtime-preview-v(\d+)\.zip',p.name)]
    runtime = max(candidates)[1] if candidates else None
    archive = runtime if runtime is not None else ROOT / ('dist/NoImNotAHuman-' + locale + '-preview-v1.zip')
    proof = json.loads(archive.with_suffix('.zip.json').read_text())
    scenes.require(proof.get('locale') == locale or proof.get('newLocales') == [locale], 'Archive identity differs')
    scenes.require(scenes.sha(archive) == proof['sha256'], 'Archive receipt changed')
    from unity_bundle_writer import block_crcs
    with ZipFile(archive) as zipped:
        report = json.loads(zipped.read('report.json'))
        scenes.require(report['locale'] == locale and report['translatedTextValues'] == 16538 and
                       report['gameVersion'] == '1.3.19' and zipped.testzip() is None, 'Package invalid')
        for name in report['artifacts']:
            data = zipped.read(name)
            if data.startswith(b'UnityFS\0'):
                checks = block_crcs(data)
                scenes.require(not checks['ambiguousBlocks'] and checks['logicalCrc'] == checks['runtimeBoundaryCrc'],
                               'Unity-incompatible compressed block: ' + locale + ' / ' + name)
    return archive


def expected_text(locale):
    keys = {('Dialogs', 110504455986814984): 'introCaption',
            ('Dialogs', 110504456292999176): 'firstNeighborLine',
            ('Dialogs', 110504456292999177): 'firstAnswer'}
    result, pins = {}, {}
    for path in sorted((ROOT / 'Translations' / locale).glob('*-batch-*.json')):
        data = json.loads(path.read_text())
        for entry in data.get('entries', []):
            key = (data.get('collection'), entry.get('id'))
            if key in keys:
                label = keys[key]
                scenes.require(label not in result, 'Duplicate expected text')
                result[label] = entry['target']; pins[str(path.relative_to(ROOT))] = scenes.sha(path)
    scenes.require(set(result) == set(keys.values()), 'Expected caption/dialogue missing: ' + locale)
    return {'strings': result, 'sourceFileHashes': pins}


def plan(selected):
    scenes.validate_training(TRAINING / 'recipe.json')
    result = []
    for locale in selected:
        archive = archive_for(locale)
        row = {'locale': locale, 'archive': str(archive.relative_to(ROOT)),
               'archiveSha256': scenes.sha(archive), 'expectedText': expected_text(locale)}
        if locale in ['fa','hi','he']:
            descriptor = HINDI_RENDERER if locale=='hi' else HEBREW_RENDERER if locale=='he' else RENDERER
            renderer = json.loads(descriptor.read_text())
            scenes.require(renderer['locales'][locale].get('baseArchiveSha256',row['archiveSha256']) ==
                           row['archiveSha256'], 'Renderer archive binding changed')
            row['renderer'] = renderer
            row['rendererRecipeSha256'] = scenes.sha(descriptor)
        result.append(row)
    return result


def ensure_ocr():
    import subprocess
    source = ROOT / 'Scripts/visual-qa/caption_ocr.swift'
    binary = ROOT / 'outputs/visual-qa-tools/caption-ocr'
    receipt = binary.with_suffix('.json')
    if receipt.is_file() and binary.is_file():
        pin = json.loads(receipt.read_text())
        if pin == {'sourceSha256':scenes.sha(source),'binarySha256':scenes.sha(binary)}:
            return
    binary.parent.mkdir(parents=True,exist_ok=True)
    temporary=binary.with_name(binary.name+'.build')
    scenes.require(not temporary.exists(),'Unreconciled OCR build')
    subprocess.run(['/usr/bin/xcrun','swiftc','-module-cache-path','/private/tmp/no-human-swift-cache',
                    str(source),'-o',str(temporary)],check=True)
    temporary.replace(binary)
    scenes.write(receipt,{'sourceSha256':scenes.sha(source),'binarySha256':scenes.sha(binary)})


def batch(output, selected, resume=False):
    scenes.require(output.is_relative_to(ROOT / 'outputs'), 'Output escaped canonical project')
    ensure_ocr()
    planned = plan(selected)  # Check every archive before changing the fixture.
    pins = {str(p.relative_to(ROOT)): scenes.sha(p) for p in [
        Path(__file__), ROOT / 'Scripts/visual-qa/capture_six_scenes.py',
        ROOT / 'Scripts/capture_russian_reference.py', ROOT / 'Scripts/visual-qa/select_intro_caption.py',
        ROOT / 'Scripts/visual-qa/caption_ocr.swift', ROOT / 'Scripts/visual-qa/learn_intro_caption.py',
        ROOT / 'Scripts/visual-qa/six_scenes.sikuli/six_scenes.py', TRAINING / 'recipe.json', RENDERER, HINDI_RENDERER, HEBREW_RENDERER]}
    if resume:
        receipt = json.loads((output / 'batch.json').read_text())
        scenes.require(receipt['plan'] == planned and receipt['executionPins'] == pins, 'Resume inputs changed')
        scenes.require(receipt['phase'] != 'complete', 'Batch already complete')
    else:
        scenes.require(not output.exists(), 'Existing batch requires --resume')
        output.mkdir(parents=True)
        receipt = {'schemaVersion': 1, 'plan': planned, 'executionPins': pins,
                   'createdAtUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'phase': 'capturing', 'completed': [], 'visualReview': {'status': 'pending'}}
    scenes.write(output / 'batch.json', receipt)
    try:
        for row in planned:
            locale = row['locale']; run = output / locale
            scenes.require(all(scenes.sha(ROOT / p) == h for p, h in pins.items()), 'Batch code changed')
            if run.exists():
                proof = json.loads((run / 'scenario.json').read_text())
                scenes.require(proof['automatedResult'] in ['pass', 'navigation-pass-caption-pending'] and proof['phase'] == 'stopped-and-restored' and
                               len(proof['frames']) in [5, 6] and all(proof['cleanup'].values()),
                               'Existing failed/live locale needs reconciliation before resume: ' + locale)
                status = json.loads((run / 'status.json').read_text())
                scenes.require(status['locale'] == locale and status['archiveSha256'] == row['archiveSha256'], 'Reused locale package differs')
                scenes.require(status.get('runtimeRenderer') == row.get('renderer'), 'Reused renderer differs')
                for frame in proof['frames']:
                    scenes.require(scenes.sha(ROOT / frame['file']) == frame['sha256'] and
                                   scenes.sha(ROOT / frame['native']) == frame['nativeSha256'], 'Completed frame changed')
            else:
                print('LOCALE_START ' + locale, flush=True)
                scenes.replay(run, locale, TRAINING, ROOT / row['archive'], row.get('renderer'))
                scenes.write(run / 'expected-text.json', row['expectedText'])
                captions.select(run, row['expectedText']['strings']['introCaption'])
            if locale not in receipt['completed']:
                receipt['completed'].append(locale)
            scenes.write(output / 'batch.json', receipt)
            print('LOCALE_COMPLETE ' + locale, flush=True)
        receipt['phase'] = 'captured-awaiting-review'
        receipt['pendingCaptions'] = [r['locale'] for r in planned if len(json.loads((output/r['locale']/'scenario.json').read_text())['frames']) != 6]
    except BaseException as error:
        receipt['phase'] = 'stopped-on-first-failure'; receipt['error'] = str(error)
        raise
    finally:
        scenes.write(output / 'batch.json', receipt)


def package(output, destination):
    receipt = json.loads((output / 'batch.json').read_text())
    scenes.require(receipt['visualReview']['status'] == 'pass' and
                   set(receipt['completed']) == {r['locale'] for r in receipt['plan']}, 'Batch review incomplete')
    scenes.require(destination.is_relative_to(ROOT / 'dist') and not destination.exists(), 'Use a new release folder')
    temporary = destination.with_name(destination.name + '.staging')
    scenes.require(not temporary.exists(), 'Unreconciled staged delivery')
    (temporary / 'jpeg').mkdir(parents=True)
    manifest = {'schemaVersion': 1, 'batch': str(output.relative_to(ROOT)), 'locales': receipt['completed'],
                'jpeg': {'dimensions': [960, 600], 'quality': 60, 'subsampling': 2}, 'frames': []}
    for row in receipt['plan']:
        proof = json.loads((output / row['locale'] / 'scenario.json').read_text())
        scenes.require(proof['visualReview']['status'] == 'pass' and all(proof['cleanup'].values()) and
                       len(proof['frames']) == 6 and {f['scene'] for f in proof['frames']} == set(scenes.DELIVERABLES),
                       'Locale review or exact six-scene set missing')
        for frame in proof['frames']:
            source = ROOT / frame['file']
            scenes.require(scenes.sha(source) == frame['sha256'] and
                           scenes.sha(ROOT / frame['native']) == frame['nativeSha256'], 'Reviewed frame changed')
            shutil.copy2(source, temporary / 'jpeg' / source.name)
            manifest['frames'].append(dict(frame, locale=row['locale'], file='jpeg/' + source.name,
                                          archiveSha256=row['archiveSha256'],
                                          runtimeRendererVersion=row.get('renderer',{}).get('version'),
                                          rendererRecipeSha256=row.get('rendererRecipeSha256')))
    with ZipFile(temporary / 'screenshots.zip', 'w', ZIP_DEFLATED) as zipped:
        for path in sorted((temporary / 'jpeg').glob('*.jpg')):
            zipped.write(path, path.name)
    with ZipFile(temporary / 'screenshots.zip') as zipped:
        scenes.require(zipped.testzip() is None and len(zipped.namelist()) == len(receipt['plan']) * 6, 'ZIP incomplete')
        import hashlib
        for frame in manifest['frames']:
            scenes.require(hashlib.sha256(zipped.read(Path(frame['file']).name)).hexdigest() == frame['sha256'], 'ZIP frame differs')
    scenes.write(temporary / 'manifest.json', manifest)
    temporary.rename(destination)
    receipt.update(phase='complete', delivery=str(destination.relative_to(ROOT)))
    scenes.write(output / 'batch.json', receipt)
    print(str(destination), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'capture', 'package'])
    parser.add_argument('--locales', nargs='+')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    selected = args.locales or locales()
    scenes.require(selected and len(set(selected)) == len(selected) and set(selected) <= set(locales()), 'Unsupported locale selection')
    if args.action == 'plan':
        print(json.dumps(plan(selected), ensure_ascii=False, indent=2))
    elif args.action == 'capture':
        scenes.require(args.output is not None, '--output is required')
        batch(args.output.resolve(), selected, args.resume)
    else:
        scenes.require(args.output is not None and args.destination is not None, 'Output and destination are required')
        package(args.output.resolve(), args.destination.resolve())
