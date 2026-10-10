#!/usr/bin/env python3
"""Locate a complete translated intro caption in immutable native movie evidence.

OCR nominates a frame; human visual review remains required. Reviewed exact
caption templates can be reused by Oculix without relying on video timing.
"""
import json
from pathlib import Path
import subprocess
import unicodedata
from difflib import SequenceMatcher
from PIL import Image

import capture_six_scenes as scenes

LANGUAGES = {'th':'th-TH','id':'id-ID','cs':'cs-CZ','hu':'en-US','nl':'nl-NL',
             'fa':'ar-SA','ro':'ro-RO','hi':'hi-IN','fil':'en-US','el':'en-US',
             'bg':'ru-RU','sr':'ru-RU','sw':'en-US','he':'en-US'}


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if c.isalnum())


def accept_frame(run, frame, expected, method, observed=None):
    proof = json.loads((run / 'scenario.json').read_text())
    scenes.require(proof['phase'] == 'stopped-and-restored' and all(proof['cleanup'].values()), 'Fixture not restored')
    scenes.require(frame.resolve().is_relative_to(run.resolve()) and frame.is_file(), 'Caption frame escaped run')
    scenes.require(not any(f['scene'] == 'school-intro' for f in proof['frames']), 'Caption already selected')
    destination = run / 'jpeg' / (proof['locale'] + '-06-school-intro.jpg')
    scenes.require(not destination.exists(), 'Caption JPEG already exists')
    with Image.open(frame) as image:
        scenes.require(image.size == (2880,1800), 'Native frame dimensions changed')
        image.convert('RGB').resize((960,600), Image.Resampling.LANCZOS).save(destination, quality=60, subsampling=2, optimize=True)
    proof['frames'].append({'scene':'school-intro','file':str(destination.relative_to(scenes.ROOT)),
                            'sha256':scenes.sha(destination),'bytes':destination.stat().st_size,
                            'dimensions':[960,600],'native':str(frame.relative_to(scenes.ROOT)),
                            'nativeSha256':scenes.sha(frame),
                            'captionSelection':{'method':method,'expected':expected,'observed':observed,
                                                'visualReview':'pending'}})
    proof['automatedResult'] = 'pass'
    scenes.write(run / 'scenario.json',proof)
    return destination


def select(run, expected):
    proof = json.loads((run / 'scenario.json').read_text())
    existing = [f for f in proof['frames'] if f['scene']=='school-intro']
    if existing:
        return scenes.ROOT / existing[0]['file']
    folder = scenes.ROOT / proof['introEvidence']
    files = sorted(folder.glob('*.png'))
    scenes.require(files, 'Movie evidence is empty')
    learned = run / 'state-07-intro-to-door/caption.png'
    if learned.is_file():
        return accept_frame(run, learned, expected, 'Oculix reviewed locale-specific caption template')
    binary = scenes.ROOT / 'outputs/visual-qa-tools/caption-ocr'
    input_file = run / 'ocr-input.json'; output = run / 'ocr.json'
    scenes.write(input_file, {'language':LANGUAGES[proof['locale']], 'files':[str(p) for p in files]})
    if not output.exists():
        subprocess.run([str(binary),str(input_file),str(output)],check=True,timeout=180)
    wanted = normalize(expected)
    candidates = []
    for row in json.loads(output.read_text())['rows']:
        observed = ' '.join(row['lines']); actual = normalize(observed)
        score = SequenceMatcher(None,wanted,actual,autojunk=False).ratio()
        if score >= .96 and len(actual) >= len(wanted) * .97:
            candidates.append((score,row['file'],observed))
    scenes.write(run/'caption-candidates.json',{'expected':expected,'candidates':candidates,
                                               'result':'nominated' if candidates else 'manual-review-required'})
    if not candidates:
        print('CAPTION_REVIEW_REQUIRED '+proof['locale'],flush=True)
        return None
    # Prefer the most complete recognition; retain every observation for review.
    score,file,observed = max(candidates,key=lambda x:x[0])
    return accept_frame(run,Path(file),expected,'macOS Vision complete-caption nomination',observed)
