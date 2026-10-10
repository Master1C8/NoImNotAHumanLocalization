#!/usr/bin/env python3
"""Guarded Russian reference capture in the existing disposable Wine fixture.

Original game files/saves are read-only. The fixture's cloud-save directory is
moved intact aside; a disposable copied checkpoint is used, then retained as
evidence and the original directory moved back. No existing save is overwritten.
The source video is a navigation reference, never an uploadable game frame.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from probe_assets import ROOT, DEFAULT_GAME, digest, require
from fixture_preferences import FIXTURE, PREFERENCES, read_settings, replace_language
from install_th_text_draft import GAME
from run_locale_visual_qa import CLOUD_SAVE, SAVE, files
from run_saved_locale_probe import state, wait_menu

RUN = ROOT / 'outputs/russian-reference-live-v1'
REFERENCE = ROOT / 'outputs/renderer-final-runtime/ru/menu/native.png'


def write(value):
    (RUN / 'status.json').write_text(json.dumps(value, indent=2) + '\n')


def stopped():
    info = state(ROOT / 'outputs/visual-qa-tools/window-info')
    require(not info['applications'] and not info['windows'], 'Fixture already in use')
    rows = subprocess.check_output(['ps', '-axo', 'pid,command'], text=True).splitlines()
    require(not any(str(FIXTURE) in row for row in rows), 'Fixture child process remains')


def start():
    stopped()
    require(not RUN.exists(), 'Existing run must be reconciled, never relaunched')
    before = {n: r['sha256'] for n, r in json.loads((ROOT / 'outputs/th-only-package-v1/report.json').read_text())['artifacts'].items()}
    original = json.loads((ROOT / 'outputs/th-fresh-install-preflight-v3/report.json').read_text())['originalFileHashes']
    require(set(before) == set(original) and len(before) == 31, 'Payload scope changed')
    require(all(digest(GAME / n) == h for n, h in before.items()), 'Fixture checkpoint changed')
    require(all(digest(DEFAULT_GAME / n) == h for n, h in original.items()), 'Original game changed')
    for p in [GAME, CLOUD_SAVE, SAVE, PREFERENCES]:
        require(p.resolve().is_relative_to(FIXTURE.resolve()), 'Fixture path escaped')
    source_cloud = DEFAULT_GAME.parents[1] / 'users/Public/Documents/Steam/RUNE/3180070'
    source_files = files(source_cloud)
    old_cloud = files(CLOUD_SAVE)
    loader = GAME / 'winhttp.dll'
    require(loader.is_file(), 'Unexpected diagnostic loader state')
    RUN.mkdir(parents=True)
    frozen = RUN / 'helpers'
    shutil.copytree(ROOT / 'Scripts/visual-qa', frozen, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(Path(__file__), RUN / 'execution.py')
    shutil.copy2(PREFERENCES, RUN / 'before-user.reg')
    shutil.copy2(loader, RUN / 'winhttp.dll')
    record = dict(phase='prepared', locale='ru', runtimeLocale='ru', publishingLocale='ru',
                  gameVersion='1.3.19', payloadBefore=before, payloadInstalled=original,
                  preferencesBefore=digest(PREFERENCES), loaderBefore=digest(loader),
                  cloudBefore=old_cloud, sourceCloud=str(source_cloud), sourceCloudHashes=source_files,
                  saveBefore=files(SAVE), helperHashes=files(frozen),
                  captureMethod='native-window; guarded project adapter; Wine CUA attachment previously incompatible',
                  automatedResult='pending', visualReview={'status': 'pending'},
                  launchCount=0, originalGameWrites=False)
    write(record)
    for source, binary in [('window_info.swift', 'window-info'), ('reference_input.swift', 'target-input')]:
        subprocess.run(['/usr/bin/xcrun', 'swiftc', '-module-cache-path', '/private/tmp/no-human-swift-cache',
                        str(frozen / source), '-o', str(RUN / binary)], check=True)
    info = state(RUN / 'window-info')
    require(info['accessibilityAllowed'] and info['screenRecordingAllowed'], 'Input/capture unavailable')
    record['phase'] = 'installing'; write(record)
    for n, h in before.items():
        backup = RUN / 'payload-backup' / n
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(GAME / n, backup)
        require(digest(backup) == h, 'Payload backup differs')
        tmp = (GAME / n).with_name(Path(n).name + '.russian-reference-tmp')
        require(not tmp.exists(), 'Unreconciled temporary payload')
        shutil.copy2(DEFAULT_GAME / n, tmp)
        require(digest(tmp) == original[n], 'Temporary payload differs')
        tmp.replace(GAME / n)
    CLOUD_SAVE.rename(RUN / 'before-cloud-directory')
    shutil.copytree(source_cloud, CLOUD_SAVE)
    require(files(CLOUD_SAVE) == source_files and files(source_cloud) == source_files, 'Source checkpoint changed during copy')
    loader.unlink()
    text, _ = replace_language(PREFERENCES.read_text(), read_settings(PREFERENCES.read_text())[2]['TextSettingsData']['SelectedLanguage'], 'ru')
    # Match the owner's reference: complete dialogue text, no typing effect.
    import re
    match, raw, settings = read_settings(text)
    raw, count = re.subn(rb'("IsUseTypewriter"\s*:\s*)true', rb'\1false', raw)
    require(count in [0, 1], 'Ambiguous typewriter setting')
    encoded = ',\\\n  '.join(','.join(f'{b:02x}' for b in raw[i:i+32]) for i in range(0, len(raw), 32))
    text = text[:match.start(1)] + encoded + text[match.end(1):]
    tmp = PREFERENCES.with_name('user.reg.russian-reference-tmp')
    require(not tmp.exists(), 'Unreconciled preferences')
    tmp.write_text(text); tmp.replace(PREFERENCES)
    record.update(phase='launch-request', launchCount=1); write(record)
    subprocess.run(['/usr/bin/open', str(FIXTURE)], check=True)
    wait_menu(RUN / 'window-info', REFERENCE, RUN / 'readiness')
    record['phase'] = 'live'; write(record)
    capture('menu')


def live():
    record = json.loads((RUN / 'status.json').read_text())
    require(record['phase'] == 'live', 'Run is not live')
    require(files(RUN / 'helpers') == record['helperHashes'], 'Pinned helper changed')
    require(all(digest(GAME / n) == h for n, h in record['payloadInstalled'].items()), 'Installed source payload changed')
    require(read_settings(PREFERENCES.read_text())[2]['TextSettingsData']['SelectedLanguage'] == 'ru', 'Russian locale changed')
    info = state(RUN / 'window-info')
    windows = [w for w in info['windows'] if w.get('kCGWindowName') == 'NoImNotAHuman']
    require(len(windows) == 1 and info['screenRecordingAllowed'], 'Expected owned readable fixture window')
    require(windows[0]['kCGWindowBounds'] == {'Height': 900, 'Width': 1440, 'X': 0, 'Y': 0}, 'Capture geometry changed')
    return record, windows[0]


def capture(name):
    _, window = live()
    out = RUN / name
    out.mkdir(exist_ok=False)
    subprocess.run(['/usr/sbin/screencapture', '-x', '-o', '-l', str(window['kCGWindowNumber']), str(out / 'native.png')], check=True)
    (out / 'window.json').write_text(json.dumps(window, indent=2) + '\n')
    if (SAVE / 'Player.log').exists(): shutil.copy2(SAVE / 'Player.log', out / 'Player.log')
    print(json.dumps({'capture': name, 'sha256': digest(out / 'native.png')}), flush=True)


def action(name, kind, reference, region, values):
    _, window = live()
    require(reference.is_file(), 'Missing reviewed reference')
    out = RUN / name; out.mkdir(exist_ok=False)
    frame = out / 'before.png'
    subprocess.run(['/usr/sbin/screencapture', '-x', '-o', '-l', str(window['kCGWindowNumber']), str(frame)], check=True)
    geometry = f'[{region[2]}x{region[3]}+{region[0]}+{region[1]}]'
    result = subprocess.run(['/opt/homebrew/bin/magick', 'compare', '-metric', 'RMSE', str(reference) + geometry,
                             str(frame) + geometry, 'null:'], text=True, capture_output=True)
    metric = float(result.stderr.split('(')[1].split(')')[0]) if result.returncode in [0, 1] else None
    receipt = dict(action=kind, reference=str(reference), referenceSha256=digest(reference), region=region,
                   normalizedRmse=metric, values=values, window=window, inputSent=False)
    path = out / 'action.json'; path.write_text(json.dumps(receipt, indent=2) + '\n')
    require(metric is not None and metric < .06, 'Expected state changed; no input sent')
    args = [str(window['kCGWindowOwnerPID']), str(window['kCGWindowNumber'])]
    subprocess.run([str(RUN / 'target-input'), 'focus', *args], check=True)
    time.sleep(.25)
    subprocess.run([str(RUN / 'target-input'), kind, *args, *values], check=True)
    receipt['inputSent'] = True; path.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'action': kind, 'name': name, 'inputSent': True}), flush=True)


def finish():
    record = json.loads((RUN / 'status.json').read_text())
    info = state(RUN / 'window-info')
    # Terminate only exact fixture app PIDs and unchanged process identities.
    owned = []
    for app in info['applications']:
        require(app['path'].startswith(str(FIXTURE) + '/'), 'Unexpected app identity')
        identity = subprocess.check_output(['ps', '-p', str(app['pid']), '-o', 'lstart=', '-o', 'command='], text=True).strip()
        require(identity.endswith('C:\\windows\\system32\\explorer.exe /desktop') or
                identity.endswith('C:\\KS Games\\No Im not a Human\\NoImNotAHuman.exe'), 'Unexpected fixture process')
        owned.append((app['pid'], identity))
    import os, signal
    record.update(phase='stopping', stopProcessIdentities=owned)
    write(record)
    for pid, identity in reversed(owned):
        require(subprocess.check_output(['ps', '-p', str(pid), '-o', 'lstart=', '-o', 'command='], text=True).strip() == identity, 'PID identity changed')
        os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        info = state(RUN / 'window-info')
        rows = subprocess.check_output(['ps', '-axo', 'pid,command'], text=True).splitlines()
        if not info['applications'] and not info['windows'] and not any(str(FIXTURE) in row for row in rows): break
        time.sleep(.5)
    stopped()
    if (SAVE / 'Player.log').exists(): shutil.copy2(SAVE / 'Player.log', RUN / 'Player.log')
    record.update(phase='restoring', disposableCloudAfter=files(CLOUD_SAVE), unitySaveAfter=files(SAVE), stoppedProcesses=owned)
    write(record)
    for n, h in record['payloadBefore'].items():
        backup = RUN / 'payload-backup' / n
        require(digest(backup) == h and digest(GAME / n) in [h, record['payloadInstalled'][n]], 'Unknown payload during restore')
        tmp = (GAME / n).with_name(Path(n).name + '.russian-reference-restore-tmp')
        require(not tmp.exists(), 'Unreconciled restore temporary')
        shutil.copy2(backup, tmp); tmp.replace(GAME / n)
    CLOUD_SAVE.rename(RUN / 'disposable-cloud-after')
    (RUN / 'before-cloud-directory').rename(CLOUD_SAVE)
    require(not (GAME / 'winhttp.dll').exists(), 'Unexpected loader replacement')
    shutil.copy2(RUN / 'winhttp.dll', GAME / 'winhttp.dll')
    shutil.copy2(RUN / 'before-user.reg', PREFERENCES)
    require(files(CLOUD_SAVE) == record['cloudBefore'] and digest(PREFERENCES) == record['preferencesBefore'] and
            digest(GAME / 'winhttp.dll') == record['loaderBefore'] and
            all(digest(GAME / n) == h for n, h in record['payloadBefore'].items()) and
            all(digest(DEFAULT_GAME / n) == h for n, h in record['payloadInstalled'].items()), 'Restoration mismatch')
    record.update(phase='stopped-and-restored', fixtureStopped=True, fixturePayloadRestored=True,
                  preferencesRestoredByteForByte=True, fixtureCloudSavesRestoredByteForByte=True,
                  originalGameUnchanged=True, temporaryDiagnosticLoaderDisabled=True)
    write(record)
    print(json.dumps({'phase': record['phase']}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=['start', 'capture', 'action', 'finish'])
    p.add_argument('--name'); p.add_argument('--kind', choices=['click', 'move', 'scroll', 'tap-space', 'hold-space'])
    p.add_argument('--reference', type=Path); p.add_argument('--region', nargs=4, type=int); p.add_argument('--values', nargs='*', default=[])
    a = p.parse_args()
    if a.operation == 'start': start()
    elif a.operation == 'finish': finish()
    elif a.operation == 'capture': capture(a.name)
    else: action(a.name, a.kind, a.reference.resolve(), a.region, a.values)
