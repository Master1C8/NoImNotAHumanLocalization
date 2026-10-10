#!/usr/bin/env python3
"""Train and replay the reviewed six-scene route in the isolated fixture.

Native evidence remains separate from the owner's JPEG 960x600 deliverables.
Translated runs require exact locale/archive checks and independent visual review.
No publication or original-save writes.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Scripts'))
import capture_russian_reference as adapter

JAVA = Path('/opt/homebrew/opt/openjdk@17/bin/java')
JAR = Path('/Users/antonkrutov/Applications/Oculix/oculixide-4.0.0-macos.jar')
TRAINING = ROOT / 'Resources/VisualQA/six-scenes-ru-v6'
RECIPE = TRAINING / 'recipe.json'
REFERENCE_RUN = ROOT / 'outputs/russian-reference-live-v1'

# Fixed backing-pixel regions; input coordinates are logical window coordinates.
SCENES = {
    'menu': ('menu/native.png', [(625, 1605, 240, 55)], ['settings', 'collection']),
    'settings': ('settings/native.png', [(90, 45, 570, 140)], ['menu', 'collection']),
    'collection-top': ('collection-top/native.png', [(1250, 1720, 350, 65)], ['menu', 'settings']),
    'collection': ('collection-bottom-check/native.png', [(1450, 1100, 1200, 240), (1250, 1720, 350, 65)],
                   ['collection-top', 'menu']),
    'school-intro': ('intro-observation/001.99.png', [(930, 1590, 1140, 90)], ['menu', 'door-far']),
    'door-far': ('gameplay-ready/native.png', [(1320, 1100, 70, 70), (1640, 975, 50, 70)], ['entrance', 'neighbor']),
    'entrance': ('door-close-check/native.png', [(1130, 730, 490, 180)], ['door-far', 'neighbor']),
    'neighbor-dialogue': ('neighbor-dialogue-check/native.png', [(1560, 520, 1100, 230)], ['entrance', 'menu']),
    'neighbor': ('neighbor-first-choices/native.png', [(1560, 520, 1100, 230), (1480, 1080, 650, 170)],
                 ['neighbor-dialogue', 'entrance']),
}
DELIVERABLES = {'menu': '01-main-menu', 'settings': '02-settings', 'collection': '03-collection',
                'entrance': '04-entrance', 'neighbor': '05-neighbor', 'school-intro': '06-school-intro'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return adapter.digest(path)


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def train():
    require(not TRAINING.exists(), 'Training already exists; do not overwrite reviewed markers')
    sources = {name: REFERENCE_RUN / spec[0] for name, spec in SCENES.items()}
    for path in sources.values():
        with Image.open(path) as image:
            require(image.size == (2880, 1800), 'Reference capture geometry changed')
    TRAINING.mkdir(parents=True)
    recipe = {'schemaVersion': 1, 'locale': 'ru', 'gameVersion': '1.3.19',
              'nativeDimensions': [2880, 1800],
              'logicalBounds': {'Height': 900, 'Width': 1440, 'X': 0, 'Y': 0},
              'jpeg': {'dimensions': [960, 600], 'quality': 60, 'subsampling': 2},
              'referenceRun': str(REFERENCE_RUN.relative_to(ROOT)),
              'scenes': {}, 'markerHashes': {}}
    for name, (_, regions, negatives) in SCENES.items():
        scene = {'positive': str(sources[name]), 'sourceSha256': sha(sources[name]),
                 'negative': [str(sources[n]) for n in negatives], 'markers': []}
        with Image.open(sources[name]) as source:
            for i, region in enumerate(regions):
                x, y, w, h = region
                filename = name + '-' + str(i) + '.png'
                source.crop((x, y, x + w, y + h)).convert('RGB').save(TRAINING / filename)
                scene['markers'].append({'file': filename, 'region': list(region), 'similarity': .90})
                recipe['markerHashes'][filename] = sha(TRAINING / filename)
        recipe['scenes'][name] = scene
    fresh_menu = ROOT / 'outputs/six-scenes-russian-replay-v1/state-01-menu/latest.png'
    if fresh_menu.is_file():
        recipe['scenes']['menu']['additionalPositive'] = [{'file': str(fresh_menu), 'sha256': sha(fresh_menu)}]
    school = recipe['scenes']['school-intro']
    school['markers'][0]['brightTextThreshold'] = 220
    first = REFERENCE_RUN / 'intro-observation/000.24.png'
    next_line = REFERENCE_RUN / 'intro-observation/003.69.png'
    school['additionalPositive'] = [{'file': str(first), 'sha256': sha(first)}]
    school['additionalNegative'] = [{'file': str(next_line), 'sha256': sha(next_line)}]
    door = recipe['scenes']['door-far']
    for marker in door['markers']:
        marker['searchRegion'] = [1000, 200, 750, 1400]
    fresh_door = ROOT / 'outputs/six-scenes-russian-replay-v4/state-08-door-far/latest.png'
    door['additionalPositive'] = [{'file': str(fresh_door), 'sha256': sha(fresh_door)}]
    entrance = recipe['scenes']['entrance']
    entrance['markers'][0]['searchRegion'] = [950, 600, 800, 550]
    fresh_entrance = ROOT / 'outputs/six-scenes-russian-replay-v5/state-10-entrance/latest.png'
    entrance['additionalPositive'] = [{'file': str(fresh_entrance), 'sha256': sha(fresh_entrance)}]
    # The title remains visible behind Settings: title-only recognition is unsafe.
    recipe['scenes']['menu']['markers'].append({
        **recipe['scenes']['settings']['markers'][0], 'present': False})
    # The first dialogue text remains unchanged when answers appear.
    recipe['scenes']['neighbor-dialogue']['markers'].append({
        **recipe['scenes']['neighbor']['markers'][1], 'present': False})
    recipe['scenes']['neighbor-dialogue']['negative'].append(str(sources['neighbor']))
    write(RECIPE, recipe)
    print(json.dumps({'training': str(RECIPE), 'scenes': len(SCENES)}), flush=True)


def validate_training(recipe_path=RECIPE):
    recipe = json.loads(recipe_path.read_text())
    require(recipe['locale'] in ['ru', 'neutral'] and set(recipe['scenes']) == set(SCENES), 'Unexpected trained route')
    for name, expected in recipe['markerHashes'].items():
        path = recipe_path.parent / name
        require(path.resolve().is_relative_to(recipe_path.parent.resolve()) and sha(path) == expected,
                'Trained marker changed: ' + name)
    return recipe


def verify(output):
    require(output.is_relative_to(ROOT / 'outputs') and not output.exists(), 'Use a new verification output')
    recipe = validate_training()
    for scene in recipe['scenes'].values():
        require(sha(Path(scene['positive'])) == scene['sourceSha256'], 'Reviewed source changed')
        for control in scene.get('additionalPositive', []) + scene.get('additionalNegative', []):
            require(sha(Path(control['file'])) == control['sha256'], 'Additional positive frame changed')
    output.mkdir(parents=True)
    script = output / 'six_scenes.sikuli'
    shutil.copytree(Path(__file__).parent / 'six_scenes.sikuli', script)
    result = subprocess.run([str(JAVA), '-cp', str(JAR), 'org.python.util.jython', str(script / 'six_scenes.py'),
                             'verify', str(RECIPE), str(output / 'verification.json')],
                            capture_output=True, text=True, timeout=120)
    (output / 'oculix.log').write_text(result.stdout + result.stderr)
    require(result.returncode == 0 and (output / 'verification.json').exists(), 'Oculix scene controls failed')
    print((output / 'verification.json').read_text(), flush=True)


def replay(run, locale="ru", training=TRAINING, archive=None, renderer=None):
    require(run.is_relative_to(ROOT / 'outputs') and not run.exists(), 'Use a new canonical run output')
    recipe_path = training / 'recipe.json'
    recipe = validate_training(recipe_path)
    for path in [JAVA, JAR, adapter.REFERENCE, ROOT / 'outputs/visual-qa-tools/window-info']:
        require(path.is_file(), 'Missing runtime prerequisite: ' + str(path))
    adapter.stopped()
    baseline = json.loads((REFERENCE_RUN / 'status.json').read_text())
    require(adapter.files(Path(baseline['sourceCloud'])) == baseline['sourceCloudHashes'],
            'Reviewed 3/11 source checkpoint changed; do not replay a different progress state')
    adapter.RUN = run
    source_hashes = {str(Path(module.__file__).resolve()): sha(Path(module.__file__))
                     for module in list(sys.modules.values()) if getattr(module, '__file__', None)
                     and Path(module.__file__).resolve().is_relative_to(ROOT / 'Scripts')
                     and Path(module.__file__).suffix == '.py'}
    source_hashes[str(Path(__file__).resolve())] = sha(Path(__file__))
    proof = {'schemaVersion': 1, 'locale': locale, 'phase': 'starting', 'sourceHashes': source_hashes,
             'recipeSha256': sha(recipe_path), 'frames': [], 'automatedResult': 'pending',
             'visualReview': {'status': 'pending'}, 'originalSaveWrites': False}

    def unchanged():
        require(all(sha(Path(p)) == h for p, h in source_hashes.items()), 'Loaded execution source changed')
        require(sha(run / 'training/recipe.json') == proof['recipeSha256'], 'Run recipe changed')
        validate_training(run / 'training/recipe.json')

    def focus():
        _, win = adapter.live()
        info = adapter.state(run / 'window-info')
        if info['frontmostApplication']['pid'] == win['kCGWindowOwnerPID']:
            return
        subprocess.run([str(run / 'target-input'), 'focus', str(win['kCGWindowOwnerPID']),
                        str(win['kCGWindowNumber'])], check=True)
        time.sleep(1.2)  # After the final activation, before screenshot recognition.

    counter = 0
    worker = None
    messages = None

    def worker_request(command, timeout):
        worker.stdin.write(json.dumps(command) + '\n'); worker.stdin.flush()
        deadline = time.monotonic() + timeout
        import queue
        while time.monotonic() < deadline:
            try:
                line = messages.get(timeout=max(.1, deadline - time.monotonic()))
            except queue.Empty:
                break
            if line is None:
                raise RuntimeError('Vision worker exited')
            if line.startswith('VN_WORKER_RESULT:'):
                result = json.loads(line.split(':', 1)[1])
                require(result['result'] == 'pass', result.get('error', 'Vision failed'))
                return
        raise TimeoutError('Vision worker response timeout')

    def wait_scene(name, timeout=35, deliver=False):
        nonlocal counter
        unchanged()
        focus()
        counter += 1
        folder = run / ('state-%02d-%s' % (counter, name))
        folder.mkdir()
        if worker is None:
            result = subprocess.run([str(JAVA), '-cp', str(JAR), 'org.python.util.jython',
                                     str(run / 'helpers/six_scenes.sikuli/six_scenes.py'), 'wait',
                                     str(run / 'training/recipe.json'), str(folder), name,
                                     str(run / 'window-info'), str(timeout), str(run / 'target-input')],
                                    capture_output=True, text=True, timeout=timeout + 45)
            (folder / 'oculix.log').write_text(result.stdout + result.stderr)
            require(result.returncode == 0, 'Scene not reached: ' + name)
        else:
            worker_request({'scene': name, 'output': str(folder), 'helper': str(run / 'window-info'),
                            'timeout': timeout, 'input': str(run / 'target-input')}, timeout + 45)
        require((folder / 'native.png').is_file(), 'Scene frame missing: ' + name)
        if deliver:
            delivered_scene = 'collection' if name == 'collection-scroll' else name
            frame = folder / 'native.png'
            destination = run / 'jpeg' / (locale + '-' + DELIVERABLES[delivered_scene] + '.jpg')
            with Image.open(frame) as image:
                require(image.size == tuple(recipe['nativeDimensions']), 'Native dimensions changed')
                image.convert('RGB').resize((960, 600), Image.Resampling.LANCZOS).save(
                    destination, quality=60, subsampling=2, optimize=True)
            with Image.open(destination) as image:
                require(image.size == (960, 600) and image.format == 'JPEG', 'JPEG output invalid')
                image.load()
            proof['frames'].append({'scene': delivered_scene, 'file': str(destination.relative_to(ROOT)),
                                    'sha256': sha(destination), 'bytes': destination.stat().st_size,
                                    'dimensions': [960, 600], 'native': str(frame.relative_to(ROOT)),
                                    'nativeSha256': sha(frame), 'recognition': str((folder / 'recognition.json').relative_to(ROOT))})
            write(run / 'scenario.json', proof)
            print('CAPTURED ' + destination.name, flush=True)
        return folder / 'native.png'

    def act(label, kind, reference, region, values=()):
        unchanged()
        # Fresh state check inside the adapter; the helper checks focus and PID again.
        adapter.action(label, kind, reference, region, list(map(str, values)))

    try:
        adapter.start(locale, archive, renderer=renderer)
        shutil.copytree(training, run / 'training')
        if locale != 'ru':
            learned_root = ROOT / 'Resources/VisualQA/locale-captions-v1'
            learned_receipt = learned_root / (locale + '.json')
            if learned_receipt.is_file():
                learned = json.loads(learned_receipt.read_text())
                marker = learned_root / learned['marker']['file']
                require(learned['archiveSha256'] == sha(archive) and sha(marker) == learned['markerSha256'], 'Learned caption changed')
                require(learned.get('runtimeRenderer') == renderer, 'Learned caption renderer differs')
                shutil.copy2(marker, run / 'training' / marker.name)
                recipe['learnedCaption'] = {'markers': [learned['marker']]}
                recipe['markerHashes'][marker.name] = sha(marker)
                write(run / 'training/recipe.json', recipe)
                proof['recipeSha256'] = sha(run / 'training/recipe.json')
        if locale != 'ru':
            import threading, queue
            messages = queue.Queue()
            worker = subprocess.Popen([str(JAVA), '-cp', str(JAR), 'org.python.util.jython',
                                       str(run / 'helpers/six_scenes.sikuli/six_scenes.py'), 'serve',
                                       str(run / 'training/recipe.json'), str(run / 'worker.json')],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, bufsize=1)
            def read_worker():
                with (run / 'vision-worker.log').open('w') as log:
                    for line in worker.stdout:
                        log.write(line); log.flush(); messages.put(line.rstrip())
                messages.put(None)
            threading.Thread(target=read_worker, daemon=True).start()
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                line = messages.get(timeout=max(.1, deadline - time.monotonic()))
                require(line is not None, 'Vision worker initialization failed')
                if line == 'VN_WORKER_READY':
                    break
            else:
                raise TimeoutError('Vision worker initialization timed out')
        (run / 'jpeg').mkdir()
        proof['phase'] = 'capturing'; write(run / 'scenario.json', proof)
        menu = wait_scene('menu', deliver=True)
        act('scenario-open-settings', 'click', menu, [1280, 1574, 320, 18], [720, 818])
        settings = wait_scene('settings', deliver=True)
        act('scenario-close-settings', 'click', settings, [60, 1660, 280, 90], [100, 850])
        menu = wait_scene('menu')
        act('scenario-open-collection', 'click', menu, [1630, 1574, 320, 18], [890, 818])
        collection = wait_scene('collection-top')
        act('scenario-position-scroll', 'move', collection, [1250, 1720, 350, 65], [750, 440])
        collection = wait_scene('collection-scroll', deliver=True)
        act('scenario-close-collection', 'click', collection, [60, 1660, 280, 90], [100, 850])
        menu = wait_scene('menu')
        act('scenario-new-game', 'click', menu, [600, 400, 300, 300], [372, 818])
        if locale == 'ru':
            wait_scene('school-intro', timeout=150, deliver=True)
            door = wait_scene('door-far', timeout=180)
        else:
            # Observe the whole intro and recognize the actual next state. A
            # missing caption must never strand the player in front of the door.
            door = wait_scene('intro-to-door', timeout=240)
            proof['introEvidence'] = str(door.parent.relative_to(ROOT) / 'movie-frames')
            write(run / 'scenario.json', proof)
        act('scenario-approach-door', 'click', door, [1100, 600, 300, 300], [710, 460])
        # Positioning the cursor changes this game's camera angle. Re-recognize
        # the doorway before W instead of comparing the pre-move camera frame.
        door = wait_scene('door-far')
        act('scenario-walk-to-door', 'hold-w', door, [1100, 600, 300, 300])
        entrance = wait_scene('entrance', deliver=True)
        act('scenario-open-door', 'tap-space', entrance, [1200, 300, 500, 300])
        dialogue = wait_scene('neighbor-dialogue', timeout=50)
        act('scenario-show-answers', 'tap-space', dialogue, [1550, 500, 950, 250])
        wait_scene('neighbor', deliver=True)
        require({f['scene'] for f in proof['frames']} == (set(DELIVERABLES) if locale == 'ru' else set(DELIVERABLES) - {'school-intro'}), 'Scene set incomplete')
        proof['automatedResult'] = 'pass' if locale == 'ru' else 'navigation-pass-caption-pending'
    except BaseException as error:
        proof['automatedResult'] = 'fail'
        proof['error'] = str(error)
        raise
    finally:
        if worker is not None:
            if worker.poll() is None:
                worker.stdin.write('{"mode":"quit"}\n'); worker.stdin.flush()
                try:
                    worker.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    worker.terminate(); worker.wait(timeout=5)
            worker.stdin.close()
        status = run / 'status.json'
        if status.exists():
            current = json.loads(status.read_text())
            if current['phase'] in ['prepared', 'installing', 'live', 'launch-request']:
                try:
                    adapter.finish()
                    proof['cleanup'] = {k: json.loads(status.read_text()).get(k) for k in [
                        'fixtureStopped', 'fixturePayloadRestored', 'preferencesRestoredByteForByte',
                        'fixtureCloudSavesRestoredByteForByte', 'originalGameUnchanged',
                        'diagnosticLoaderRestoredByteForByte','rendererModuleRestoredByteForByte']}
                    proof['phase'] = 'stopped-and-restored'
                except BaseException as cleanup_error:
                    proof['phase'] = 'cleanup-required'
                    proof['cleanupError'] = str(cleanup_error)
                    write(run / 'scenario.json', proof)
                    raise
            else:
                proof['phase'] = 'reconciliation-required'
            write(run / 'scenario.json', proof)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['train', 'verify', 'replay', 'restore'])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action == 'train':
        train()
    else:
        require(args.output is not None, 'A new --output directory is required')
        if args.action == 'restore':
            run = args.output.resolve()
            require(run.is_relative_to(ROOT / 'outputs') and (run / 'scenario.json').is_file(), 'Unknown scenario run')
            status = json.loads((run / 'status.json').read_text())
            require(status['phase'] in ['prepared', 'installing', 'live', 'launch-request', 'stopping', 'restoring'],
                    'Run is already restored or needs partial-install reconciliation')
            adapter.RUN = run
            adapter.finish()
            proof = json.loads((run / 'scenario.json').read_text())
            proof['phase'] = 'stopped-and-restored'
            proof['cleanup'] = {k: json.loads((run / 'status.json').read_text()).get(k) for k in [
                'fixtureStopped', 'fixturePayloadRestored', 'preferencesRestoredByteForByte',
                'fixtureCloudSavesRestoredByteForByte', 'originalGameUnchanged']}
            write(run / 'scenario.json', proof)
        else:
            (verify if args.action == 'verify' else replay)(args.output.resolve())
