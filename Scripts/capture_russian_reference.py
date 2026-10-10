#!/usr/bin/env python3
"""Guarded locale reference capture in the existing disposable Wine fixture.

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


def start(locale="ru", archive=None, failure_after_install=None, renderer=None):
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
    installed = original
    package_identity = {}
    if archive is not None:
        from zipfile import ZipFile
        proof = json.loads(archive.with_suffix(archive.suffix + '.json').read_text())
        require(proof.get('locale') == locale or proof.get('newLocales') == [locale], 'Archive locale differs')
        require(digest(archive) == proof['sha256'], 'Archive changed')
        with ZipFile(archive) as zipped:
            require(zipped.testzip() is None and len(zipped.namelist()) == 33, 'Archive invalid')
            package = json.loads(zipped.read('report.json'))
            require(package['locale'] == locale and package['gameVersion'] == '1.3.19' and
                    package['translatedTextValues'] == 16538, 'Package identity differs')
            installed = {n: r['sha256'] for n, r in package['artifacts'].items()}
            require(set(installed) == set(original), 'Package scope differs')
            for n, wanted in installed.items():
                require(not Path(n).is_absolute() and '..' not in Path(n).parts and
                        (GAME / n).resolve().is_relative_to(GAME.resolve()), 'Package escaped fixture')
                import hashlib
                require(hashlib.sha256(zipped.read(n)).hexdigest() == wanted, 'Package member differs')
        package_identity = {'archive': str(archive), 'archiveSha256': digest(archive)}
    else:
        require(locale == 'ru', 'A translated locale requires its verified archive')
    overlay = {}
    if renderer is not None:
        require(locale in ['fa', 'hi', 'he'] and renderer['version'] in ['0.3.0','0.3.1','0.3.2','0.3.3'] and
                (renderer['version']!='0.3.2' or locale=='hi') and
                (renderer['version']!='0.3.3' or locale=='he'), 'Unexpected renderer scope')
        require(digest(ROOT / renderer['moduleReceipt']) == renderer['moduleReceiptSha256'] and
                all(digest(ROOT / n) == h for n, h in renderer['frozenSourceHashes'].items()) and
                all(digest(GAME / n) == h for n, h in renderer['pluginFiles'].items()) and
                digest(loader) == renderer['loaderSha256'], 'Renderer checkpoint changed')
        require(all(digest(ROOT / n) == h for n, h in renderer.get('build',{}).get('generatedSourceHashes',{}).items()),
                'Generated renderer source changed')
        require(set(renderer.get('pluginOverrides',{})) <= set(renderer['pluginFiles']), 'Module override escaped scope')
        for n,row in renderer.get('pluginOverrides',{}).items():
            require((ROOT/row['file']).resolve().is_relative_to(ROOT/'outputs') and
                    digest(ROOT/row['file'])==row['sha256'], 'Built renderer changed')
        config = GAME / 'BepInEx/config/nohuman-dialogue-probe.json'
        require(not config.exists() or json.loads(config.read_text()).get('enabled') is False,
                'Dialogue instrumentation must be disabled for genuine screenshots')
        locale_renderer = renderer['locales'][locale]
        require(locale_renderer.get('baseArchiveSha256', package_identity['archiveSha256']) ==
                package_identity['archiveSha256'], 'Renderer font parent package differs')
        overlay = locale_renderer['assets']
        require(set(overlay) <= set(installed), 'Renderer asset escaped payload scope')
        for n, row in overlay.items():
            source = ROOT / row['file']
            require(source.resolve().is_relative_to(ROOT / 'outputs') and digest(source) == row['sha256'],
                    'Renderer font asset changed')
            installed[n] = row['sha256']
    RUN.mkdir(parents=True)
    frozen = RUN / 'helpers'
    shutil.copytree(ROOT / 'Scripts/visual-qa', frozen, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(Path(__file__), RUN / 'execution.py')
    shutil.copy2(PREFERENCES, RUN / 'before-user.reg')
    shutil.copy2(loader, RUN / 'winhttp.dll')
    record = dict(phase='prepared', locale=locale, runtimeLocale=locale, publishingLocale=locale,
                  gameVersion='1.3.19', payloadBefore=before, payloadInstalled=installed, originalHashes=original,
                  preferencesBefore=digest(PREFERENCES), loaderBefore=digest(loader),
                  cloudBefore=old_cloud, sourceCloud=str(source_cloud), sourceCloudHashes=source_files,
                  saveBefore=files(SAVE), helperHashes=files(frozen),
                  captureMethod='native-window; guarded project adapter; Wine CUA attachment previously incompatible',
                  automatedResult='pending', visualReview={'status': 'pending'},
                  launchCount=0, originalGameWrites=False)
    record.update(package_identity)
    record['runtimeRenderer'] = renderer
    if renderer is not None:
        record['pluginInstalled'] = dict(renderer['pluginFiles'])
        record['pluginInstalled'].update({n:row['sha256'] for n,row in renderer.get('pluginOverrides',{}).items()})
    write(record)
    for source, binary in [('window_info.swift', 'window-info'), ('reference_input.swift', 'target-input')]:
        subprocess.run(['/usr/bin/xcrun', 'swiftc', '-module-cache-path', '/private/tmp/no-human-swift-cache',
                        str(frozen / source), '-o', str(RUN / binary)], check=True)
    info = state(RUN / 'window-info')
    require(info['accessibilityAllowed'] and info['screenRecordingAllowed'], 'Input/capture unavailable')
    if archive is not None:
        shutil.copy2(archive, RUN / 'installed-package.zip')
        require(digest(RUN / 'installed-package.zip') == package_identity['archiveSha256'], 'Frozen archive differs')
    for n, row in overlay.items():
        frozen_asset = RUN / 'renderer-assets' / n
        frozen_asset.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / row['file'], frozen_asset)
        require(digest(frozen_asset) == row['sha256'], 'Frozen renderer asset differs')
    if renderer is not None:
        for n,row in renderer.get('pluginOverrides',{}).items():
            backup=RUN/'plugin-backup'/n;backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(GAME/n,backup)
            require(digest(backup)==renderer['pluginFiles'][n], 'Module backup differs')
            frozen_plugin=RUN/'renderer-assets'/n;frozen_plugin.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/row['file'],frozen_plugin)
            require(digest(frozen_plugin)==row['sha256'], 'Frozen module differs')
    # Back up the complete set before the first replacement. Recovery therefore
    # works after any individual payload write, not only after a full install.
    for n, h in before.items():
        backup = RUN / 'payload-backup' / n
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(GAME / n, backup)
        require(digest(backup) == h, 'Payload backup differs')
    record['phase'] = 'installing'; write(record)
    if renderer is not None:
        for n,row in renderer.get('pluginOverrides',{}).items():
            target=GAME/n;tmp=target.with_name(target.name+'.capture-renderer-tmp')
            require(not tmp.exists() and digest(target)==renderer['pluginFiles'][n], 'Module changed before install')
            shutil.copy2(RUN/'renderer-assets'/n,tmp);require(digest(tmp)==row['sha256'],'Temporary module differs')
            tmp.replace(target)
    for index, (n, h) in enumerate(before.items(), 1):
        tmp = (GAME / n).with_name(Path(n).name + '.russian-reference-tmp')
        require(not tmp.exists(), 'Unreconciled temporary payload')
        if n in overlay:
            shutil.copy2(RUN / 'renderer-assets' / n, tmp)
        elif archive is None:
            shutil.copy2(DEFAULT_GAME / n, tmp)
        else:
            from zipfile import ZipFile
            with ZipFile(RUN / 'installed-package.zip') as zipped:
                tmp.write_bytes(zipped.read(n))
        require(digest(tmp) == installed[n], 'Temporary payload differs')
        tmp.replace(GAME / n)
        if failure_after_install == index:
            raise RuntimeError('Injected failure after payload replacement')
    CLOUD_SAVE.rename(RUN / 'before-cloud-directory')
    shutil.copytree(source_cloud, CLOUD_SAVE)
    require(files(CLOUD_SAVE) == source_files and files(source_cloud) == source_files, 'Source checkpoint changed during copy')
    if renderer is None:
        loader.unlink()
    text, _ = replace_language(PREFERENCES.read_text(), read_settings(PREFERENCES.read_text())[2]['TextSettingsData']['SelectedLanguage'], locale)
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
    record.update(phase='launch-request', launchCount=1, launchEpoch=time.time()); write(record)
    subprocess.run(['/usr/bin/open', str(FIXTURE)], check=True)
    wait_menu(RUN / 'window-info', REFERENCE, RUN / 'readiness')
    record['phase'] = 'live'; write(record)
    capture('menu')


def live():
    record = json.loads((RUN / 'status.json').read_text())
    require(record['phase'] == 'live', 'Run is not live')
    require(files(RUN / 'helpers') == record['helperHashes'], 'Pinned helper changed')
    require(all(digest(GAME / n) == h for n, h in record['payloadInstalled'].items()), 'Installed source payload changed')
    require(read_settings(PREFERENCES.read_text())[2]['TextSettingsData']['SelectedLanguage'] == record['locale'], 'Selected locale changed')
    renderer = record.get('runtimeRenderer')
    if renderer is not None:
        require(all(digest(GAME / n) == h for n, h in record['pluginInstalled'].items()), 'Live renderer changed')
        log = GAME / 'BepInEx/LogOutput.log'
        require(log.is_file() and log.stat().st_mtime >= record['launchEpoch'], 'Fresh renderer log missing')
        text = log.read_text(errors='replace')
        require('RENDERER_READY v'+renderer['version'] in text and 'RENDERER_FAILED' not in text and
                (record['locale'] != 'hi' or 'RENDERER_HI_UNBOUND' not in text), 'Renderer did not accept this locale')
    log = SAVE / 'Player.log'
    if log.exists():
        text = log.read_text(errors='replace')
        require('CRC Mismatch.' not in text and not ('LoadTableOperation' in text and 'OperationException' in text),
                'Localization tables failed to load; reject this screen before input')
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
    # A second Ctrl-C must not interrupt the checked restoration itself.
    import signal
    previous=signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT,signal.SIG_IGN)
    try:
        _finish()
    finally:
        signal.signal(signal.SIGINT,previous)


def stop_shutdown_applets(record, info):
    """Close only the fixture shutdown app spawned after this run's launch."""
    import datetime, os, signal
    path = str(FIXTURE / 'Contents/Resources/Scripts/ShutdownScript.app')
    if any(a['path'] != path for a in info['applications']):
        return
    for app in info['applications']:
        pid = app['pid']; command = path + '/Contents/MacOS/applet'
        observed = subprocess.run(['ps', '-p', str(pid), '-o', 'lstart=', '-o', 'command='], text=True, capture_output=True)
        if observed.returncode != 0 and not observed.stdout.strip():
            continue  # NSWorkspace can briefly retain an already exited app.
        require(observed.returncode == 0, 'Cannot verify shutdown app identity')
        identity = observed.stdout.strip()
        require(identity.endswith(command), 'Unknown shutdown app executable')
        started = datetime.datetime.strptime(identity[:-len(command)].strip(), '%a %b %d %H:%M:%S %Y').timestamp()
        require(record.get('stopProcessIdentities') and started >= record['launchEpoch'] - 2,
                'Shutdown app does not belong to this launched run')
        require(subprocess.check_output(['ps', '-p', str(pid), '-o', 'lstart=', '-o', 'command='], text=True).strip() == identity,
                'Shutdown app identity changed')
        record.setdefault('shutdownProcessIdentities', []).append([pid, identity])
        write(record)
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def _finish():
    record = json.loads((RUN / 'status.json').read_text())
    helper = RUN / 'window-info'
    if not helper.is_file():
        helper = ROOT / 'outputs/visual-qa-tools/window-info'
    info = state(helper)
    if record['phase'] == 'stopping':
        stop_shutdown_applets(record, info)
        info = state(helper)
    # Terminate only exact fixture app PIDs and unchanged process identities.
    owned = []
    for app in info['applications']:
        if record['phase'] == 'stopping' and app['path'] == str(FIXTURE / 'Contents/Resources/Scripts/ShutdownScript.app'):
            continue  # Verified above; wait for its actual exit below.
        require(app['path'].startswith(str(FIXTURE) + '/'), 'Unexpected app identity')
        identity = subprocess.check_output(['ps', '-p', str(app['pid']), '-o', 'lstart=', '-o', 'command='], text=True).strip()
        require(identity.endswith('C:\\windows\\system32\\explorer.exe /desktop') or
                identity.endswith('C:\\KS Games\\No Im not a Human\\NoImNotAHuman.exe'), 'Unexpected fixture process')
        owned.append((app['pid'], identity))
    import os, signal
    record.update(phase='stopping', stopProcessIdentities=owned or record.get('stopProcessIdentities', []))
    write(record)
    for pid, identity in reversed(owned):
        require(subprocess.check_output(['ps', '-p', str(pid), '-o', 'lstart=', '-o', 'command='], text=True).strip() == identity, 'PID identity changed')
        os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        info = state(helper)
        stop_shutdown_applets(record, info)
        rows = subprocess.check_output(['ps', '-axo', 'pid,command'], text=True).splitlines()
        if not info['applications'] and not info['windows'] and not any(str(FIXTURE) in row for row in rows): break
        time.sleep(.5)
    stopped()
    if (SAVE / 'Player.log').exists(): shutil.copy2(SAVE / 'Player.log', RUN / 'Player.log')
    if record.get('runtimeRenderer') is not None and record.get('launchCount'):
        renderer_log=GAME / 'BepInEx/LogOutput.log'
        if renderer_log.is_file():shutil.copy2(renderer_log, RUN / 'renderer.log')
        else:record['rendererLogMissing']=True
    record.update(phase='restoring', disposableCloudAfter=files(CLOUD_SAVE), unitySaveAfter=files(SAVE), stoppedProcesses=owned)
    write(record)
    for n, h in record['payloadBefore'].items():
        backup = RUN / 'payload-backup' / n
        if not backup.exists():
            require(digest(GAME / n) == h, 'Missing backup for changed payload')
            continue
        require(digest(backup) == h and digest(GAME / n) in [h, record['payloadInstalled'][n]], 'Unknown payload during restore')
        tmp = (GAME / n).with_name(Path(n).name + '.russian-reference-restore-tmp')
        require(not tmp.exists(), 'Unreconciled restore temporary')
        shutil.copy2(backup, tmp); tmp.replace(GAME / n)
    renderer=record.get('runtimeRenderer')
    if renderer is not None:
        for n,row in renderer.get('pluginOverrides',{}).items():
            before=renderer['pluginFiles'][n];target=GAME/n;backup=RUN/'plugin-backup'/n
            if not backup.exists():
                require(digest(target)==before,'Missing backup for changed module')
                continue
            require(digest(backup)==before and digest(target) in [before,row['sha256']], 'Unknown module during restore')
            tmp=target.with_name(target.name+'.capture-renderer-restore-tmp')
            require(not tmp.exists(),'Unreconciled module restore')
            shutil.copy2(backup,tmp);tmp.replace(target)
        require(all(digest(GAME/n)==h for n,h in renderer['pluginFiles'].items()), 'Module restoration differs')
    if (RUN / 'before-cloud-directory').exists():
        if CLOUD_SAVE.exists():
            CLOUD_SAVE.rename(RUN / 'disposable-cloud-after')
        (RUN / 'before-cloud-directory').rename(CLOUD_SAVE)
    loader = GAME / 'winhttp.dll'
    if loader.exists():
        require(digest(loader) == record['loaderBefore'], 'Unexpected loader replacement')
    else:
        shutil.copy2(RUN / 'winhttp.dll', loader)
    shutil.copy2(RUN / 'before-user.reg', PREFERENCES)
    require(files(CLOUD_SAVE) == record['cloudBefore'] and digest(PREFERENCES) == record['preferencesBefore'] and
            digest(GAME / 'winhttp.dll') == record['loaderBefore'] and
            all(digest(GAME / n) == h for n, h in record['payloadBefore'].items()) and
            all(digest(DEFAULT_GAME / n) == h for n, h in record.get('originalHashes', record['payloadInstalled']).items()), 'Restoration mismatch')
    record.update(phase='stopped-and-restored', fixtureStopped=True, fixturePayloadRestored=True,
                  preferencesRestoredByteForByte=True, fixtureCloudSavesRestoredByteForByte=True,
                  originalGameUnchanged=True, temporaryDiagnosticLoaderDisabled=record.get('runtimeRenderer') is None,
                  diagnosticLoaderRestoredByteForByte=True, rendererModuleRestoredByteForByte=True)
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
