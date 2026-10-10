#!/usr/bin/env python3
"""Inspect an exact shipped locale archive in the existing isolated fixture.

Run one locale at a time. Live actions require a reviewed native reference and
fresh state/focus guards. Finish restores the fixture payload and preferences.
No original game writes, synthetic dialogue, translation edits or publication.
"""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from zipfile import ZipFile

from probe_assets import ROOT, DEFAULT_GAME, digest, require
from fixture_preferences import FIXTURE, PREFERENCES, read_settings, replace_language
from install_th_text_draft import GAME, fixture_stopped
from rehearse_th_archive_install import apply_archive
from start_dialogue_probe import enable_typewriter
from run_saved_locale_probe import state, stop_fixture, wait_menu

sys.path.insert(0, str(ROOT / 'Scripts/visual-qa'))
import run_capture
import guarded_click

SAVE = FIXTURE / 'Contents/SharedSupport/prefix/drive_c/users/Sikarugir/AppData/LocalLow/Trioskaz/NoImNotAHuman'
REFERENCE = ROOT / 'outputs/renderer-final-runtime/ru/menu/native.png'
LOADER_SHA = '8c6cdbc38836dee87e3368f5de1994d7c0ccebf29e4ce7aba3c0981f9375412c'
LOCALES = ['id', 'cs', 'hu', 'nl', 'fa', 'ro', 'hi', 'fil', 'el', 'bg', 'sr', 'sw', 'he']


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def files(directory):
    return {str(p.relative_to(directory)): digest(p) for p in directory.rglob('*') if p.is_file()}


def bind(run):
    frozen = run / 'frozen-helpers/visual-qa'
    run_capture.SCRIPT = frozen
    guarded_click.SCRIPT = frozen
    record = json.loads((run / 'status.json').read_text())
    require(all(digest(run / 'frozen-helpers' / name) == sha for name, sha in record['helperHashes'].items()),
            'Frozen helper changed; preserve live state')
    return record


def verify_live(run):
    record = bind(run)
    require(record['phase'] in ['launch-request', 'menu-captured', 'live'], 'Run is not live')
    require(not (GAME / 'winhttp.dll').exists(), 'Diagnostic loader unexpectedly enabled')
    require(all(digest(GAME / name) == sha for name, sha in record['installedHashes'].items()),
            'Live payload differs from the exact archive')
    require(read_settings(PREFERENCES.read_text())[2]['TextSettingsData']['SelectedLanguage'] == record['locale'],
            'Saved locale changed')
    info = state(run / 'window-info')
    windows = [w for w in info['windows'] if w.get('kCGWindowName') == 'NoImNotAHuman']
    require(len(windows) == 1 and info['screenRecordingAllowed'], 'Expected one readable owned fixture window')
    return record, windows[0]


def start(locale, run):
    require(locale in LOCALES and not run.exists() and run.is_relative_to(ROOT / 'outputs'),
            'Choose a supported locale and a new canonical run directory')
    fixture_stopped()
    require(GAME.resolve().is_relative_to(FIXTURE.resolve()) and PREFERENCES.resolve().is_relative_to(FIXTURE.resolve()),
            'Fixture symlink escaped')
    archive = ROOT / ('dist/NoImNotAHuman-' + locale + '-preview-v1.zip')
    proof = json.loads((ROOT / ('Documentation/' + locale + '-delivery-proof-v1/archive.json')).read_text())
    require(digest(archive) == proof['sha256'], 'Delivered archive changed')
    with ZipFile(archive) as zipped:
        require(zipped.testzip() is None and len(zipped.namelist()) == 33, 'Archive members or CRC differ')
        package = json.loads(zipped.read('report.json'))
    require(package['locale'] == locale and package['translatedTextValues'] == 16538, 'Wrong locale package')
    installed = {name: value['sha256'] for name, value in package['artifacts'].items()}
    thai = json.loads((ROOT / 'outputs/th-only-package-v1/report.json').read_text())
    previous = {name: value['sha256'] for name, value in thai['artifacts'].items()}
    require(set(installed) == set(previous) and len(installed) == 31, 'Unexpected payload paths')
    require(all(not Path(name).is_absolute() and '..' not in Path(name).parts and
                (GAME / name).resolve().is_relative_to(GAME.resolve()) for name in installed), 'Payload path escaped')
    require(all(digest(GAME / name) == sha for name, sha in previous.items()), 'Fixture is not the pinned Thai checkpoint')
    loader = GAME / 'winhttp.dll'
    require(loader.is_file() and digest(loader) == LOADER_SHA, 'Unexpected diagnostic loader state')
    require(not (GAME / 'BepInEx/config/nohuman-dialogue-probe.json').exists(), 'Diagnostic sample configured')
    require(REFERENCE.is_file(), 'Reviewed menu reference missing')
    run.mkdir(parents=True)
    frozen = run / 'frozen-helpers'
    frozen.mkdir()
    for source in (ROOT / 'Scripts').rglob('*'):
        if source.is_file() and source.suffix in ['.py', '.swift']:
            target = frozen / source.relative_to(ROOT / 'Scripts')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    record = {'schemaVersion': 1, 'startedAtUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'phase': 'prepared', 'locale': locale, 'runtimeLocale': locale, 'publishingLocale': locale,
              'localeMappingSource': str(archive.relative_to(ROOT)) + ':report.json.locale',
              'gameVersion': '1.3.19', 'archive': str(archive.relative_to(ROOT)), 'archiveSha256': digest(archive),
              'fixture': str(FIXTURE), 'installedHashes': installed, 'beforeHashes': previous,
              'originalHashes': {name: digest(DEFAULT_GAME / name) for name in installed},
              'helperHashes': files(frozen), 'diagnosticLoaderBeforeSha256': LOADER_SHA,
              'automatedResult': 'pending', 'visualReview': {'status': 'pending'},
              'scope': 'Exact archive without diagnostic loader; isolated fixture only; images/textures excluded'}
    shutil.copy2(PREFERENCES, run / 'before-user.reg')
    shutil.copytree(SAVE, run / 'before-save-directory')
    shutil.copy2(loader, run / 'winhttp.dll')
    record['preferencesBeforeSha256'] = digest(run / 'before-user.reg')
    record['saveFilesBefore'] = files(SAVE)
    write(run / 'status.json', record)
    bind(run)
    subprocess.run(['/usr/bin/xcrun', 'swiftc', '-module-cache-path', '/private/tmp/no-human-swift-cache',
                    str(frozen / 'visual-qa/window_info.swift'), '-o', str(run / 'window-info')], check=True)
    info = state(run / 'window-info')
    require(not info['applications'] and not info['windows'], 'Fixture is already in use')
    require(info['screenRecordingAllowed'] and info['accessibilityAllowed'], 'Native capture/input permission unavailable')
    write(run / 'initial-state.json', info)
    record['phase'] = 'installing'; write(run / 'status.json', record)
    apply_archive(archive, GAME, run / 'installation', previous, installed)
    fixture_stopped()
    loader.unlink()
    original = PREFERENCES.read_text()
    before_locale = read_settings(original)[2]['TextSettingsData']['SelectedLanguage']
    changed, _ = replace_language(original, before_locale, locale)
    changed = enable_typewriter(changed)
    temporary = PREFERENCES.with_name('user.reg.visual-qa-tmp')
    require(not temporary.exists(), 'Unreconciled preferences temporary')
    temporary.write_text(changed); temporary.replace(PREFERENCES)
    record['selectedSettings'] = read_settings(changed)[2]
    record['phase'] = 'launch-request'; write(run / 'status.json', record)
    subprocess.run(['/usr/bin/open', str(FIXTURE)], check=True)
    wait_menu(run / 'window-info', REFERENCE, run / 'readiness')
    run_capture.run(run / 'menu', None)
    record['phase'] = 'menu-captured'; write(run / 'status.json', record)
    print(json.dumps({'locale': locale, 'phase': record['phase'], 'run': str(run.relative_to(ROOT))}), flush=True)


def capture(run, name):
    verify_live(run)
    require(name and '/' not in name and name not in ['.', '..'], 'Invalid capture name')
    run_capture.run(run / name, None)
    if (SAVE / 'Player.log').exists():
        shutil.copy2(SAVE / 'Player.log', run / name / 'Player.log')


def click(run, reference, region, point, name, menu_guard=False):
    record, _ = verify_live(run)
    require(reference.is_relative_to(run) and reference.is_file(), 'Use a reviewed frame from this exact run')
    extra = [(REFERENCE, [600, 400, 300, 300], .12)] if menu_guard else []
    guarded_click.run(reference, region, point, run / name, extra_guards=extra)
    record['phase'] = 'live'; write(run / 'status.json', record)


def finish(run):
    record = bind(run)
    require(record['phase'] != 'stopped-and-restored', 'Run already restored')
    info = state(run / 'window-info')
    if info['applications'] or info['windows']:
        if info['windows']:
            run_capture.run(run / 'finish-frame', None)
        stop_fixture(run / 'window-info', run / 'stop.json')
    fixture_stopped()
    if (SAVE / 'Player.log').exists():
        shutil.copy2(SAVE / 'Player.log', run / 'Player.log')
    after = files(SAVE)
    record['isolatedSaveDirectoryChanges'] = sorted(name for name in set(after) | set(record['saveFilesBefore'])
                                                  if after.get(name) != record['saveFilesBefore'].get(name))
    record['phase'] = 'restoring'; write(run / 'status.json', record)
    for name, sha in record['beforeHashes'].items():
        destination = GAME / name
        current = digest(destination)
        require(current in [sha, record['installedHashes'][name]], 'Unrecognized partial payload; preserve it')
        if current != sha:
            backup = run / 'installation/backup' / name
            require(backup.is_file() and digest(backup) == sha, 'Missing verified payload backup')
            temporary = destination.with_name(destination.name + '.visual-qa-restore-tmp')
            require(not temporary.exists(), 'Unreconciled restore temporary')
            shutil.copy2(backup, temporary)
            require(digest(temporary) == sha, 'Restore copy differs')
            temporary.replace(destination)
    loader = GAME / 'winhttp.dll'
    require(not loader.exists() or digest(loader) == LOADER_SHA, 'Unexpected loader replacement')
    if not loader.exists():
        require(digest(run / 'winhttp.dll') == LOADER_SHA, 'Loader backup changed')
        shutil.copy2(run / 'winhttp.dll', loader)
    require(digest(run / 'before-user.reg') == record['preferencesBeforeSha256'], 'Preference backup changed')
    shutil.copy2(run / 'before-user.reg', PREFERENCES)
    require(digest(PREFERENCES) == record['preferencesBeforeSha256'] and
            all(digest(GAME / name) == sha for name, sha in record['beforeHashes'].items()) and
            all(digest(DEFAULT_GAME / name) == sha for name, sha in record['originalHashes'].items()),
            'Restoration or original-game identity mismatch')
    record.update(phase='stopped-and-restored', fixtureStopped=True, preferencesRestoredByteForByte=True,
                  originalGameUnchanged=True, fixturePayloadRestored=True, diagnosticLoaderRestored=True)
    write(run / 'status.json', record)
    print(json.dumps({'locale': record['locale'], 'phase': record['phase'],
                      'isolatedSaveDirectoryChanges': record['isolatedSaveDirectoryChanges']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=['start', 'capture', 'click', 'finish'], required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--locale', choices=LOCALES)
    parser.add_argument('--name')
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--region', type=int, nargs=4)
    parser.add_argument('--point', type=float, nargs=2)
    parser.add_argument('--menu-guard', action='store_true')
    args = parser.parse_args()
    directory = args.run.resolve()
    require(directory.is_relative_to(ROOT / 'outputs'), 'Noncanonical run directory')
    if args.action == 'start': start(args.locale, directory)
    elif args.action == 'capture': capture(directory, args.name)
    elif args.action == 'click':
        require(args.reference and args.region and args.point and args.name, 'Complete reviewed click contract required')
        click(directory, args.reference.resolve(), args.region, args.point, args.name, args.menu_guard)
    else: finish(directory)
