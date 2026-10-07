#!/usr/bin/env python3
"""Capture an already-running isolated game window; no input or launch side effects."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).resolve().parent
JAVA = Path('/opt/homebrew/opt/openjdk@17/bin/java')
JAR = Path('/Users/antonkrutov/Applications/Oculix/oculixide-4.0.0-macos.jar')
MAGICK = Path('/opt/homebrew/bin/magick')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(output, marker):
    for path in [JAVA, JAR, MAGICK]:
        if not path.is_file():
            raise ValueError('Missing capture dependency: ' + str(path))
    if not output.is_relative_to(ROOT / 'outputs'):
        raise ValueError('Capture output must be below the canonical outputs directory')
    if marker and not marker.is_file():
        raise ValueError('Missing recognition marker')
    output.mkdir(parents=True, exist_ok=False)
    worker = output / 'worker'
    worker.mkdir()
    # Pin every helper read by this run, including code loaded later by Jython.
    shutil.copytree(SCRIPT / 'probe_capture.sikuli', worker / 'probe_capture.sikuli')
    shutil.copy2(SCRIPT / 'window_info.swift', worker / 'window_info.swift')
    helper = worker / 'window-info'
    subprocess.run(['/usr/bin/xcrun', 'swiftc', '-module-cache-path', '/private/tmp/no-human-swift-cache',
                    str(worker / 'window_info.swift'), '-o', str(helper)], check=True)
    info = json.loads(subprocess.check_output([str(helper)], text=True))
    (output / 'window-info.json').write_text(json.dumps(info, indent=2) + '\n')
    windows = [w for w in info['windows'] if w.get('kCGWindowName') == 'NoImNotAHuman' and w.get('kCGWindowLayer') == 0]
    if not info['screenRecordingAllowed'] or len(windows) != 1:
        raise ValueError('Expected one readable isolated game window; no game action performed')
    win = windows[0]
    mode = 'guard' if marker else 'smoke'
    copied_marker = worker / 'marker.png'
    if marker:
        shutil.copy2(marker, copied_marker)
    command = [str(JAVA), '-jar', str(JAR), '-c', '-r', str(worker / 'probe_capture.sikuli'),
               '--', mode, str(output), str(win['kCGWindowNumber']), str(copied_marker), str(helper)]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    (output / 'oculix.log').write_text(result.stdout)
    frame = output / 'native.png'
    size = subprocess.check_output([str(MAGICK), 'identify', '-format', '%wx%h', str(frame)], text=True) if frame.is_file() else None
    evidence = {'schemaVersion': 1, 'recordedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'gameVersion': '1.3.19', 'purpose': 'technical-window-capture', 'runtimeLocale': None,
                'window': win, 'sourceFingerprints': {str(p.relative_to(output)): sha(p) for p in worker.rglob('*') if p.is_file()},
                'jarSha256': sha(JAR), 'javaVersion': subprocess.check_output([str(JAVA), '-version'], stderr=subprocess.STDOUT, text=True),
                'magickVersion': subprocess.check_output([str(MAGICK), '-version'], text=True).splitlines()[0],
                'nativeCapture': {'path': str(frame.relative_to(ROOT)), 'sha256': sha(frame) if frame.is_file() else None, 'dimensions': size},
                'automatedResult': 'pass' if result.returncode == 0 and 'VN_HUMAN_CAPTURE_OK:' in result.stdout else 'fail',
                'visualReview': {'status': 'pending'}, 'inputActions': 0, 'localeOrSaveActions': 0,
                'cleanup': 'capture-only; already-running authorized fixture retained'}
    (output / 'evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'evidence': str(output / 'evidence.json'), 'automatedResult': evidence['automatedResult']}))
    if evidence['automatedResult'] != 'pass':
        raise SystemExit('Native capture or expected-state recognition failed; see oculix.log')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--marker', type=Path)
    args = parser.parse_args()
    run(args.output.resolve(), args.marker.resolve() if args.marker else None)
