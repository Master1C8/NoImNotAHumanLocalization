#!/usr/bin/env python3
"""Freeze a visually reviewed native caption and verify neighboring rejections."""
import json
from pathlib import Path
import subprocess
from PIL import Image
import capture_six_scenes as scenes

CAPTIONS = scenes.ROOT / 'Resources/VisualQA/locale-captions-v1'
REGION = [200,1530,2480,240]


def learn(run):
    proof = json.loads((run/'scenario.json').read_text())
    scenes.require(proof['visualReview']['status']=='pass', 'Independent visual review required')
    frame = next(f for f in proof['frames'] if f['scene']=='school-intro')
    native = scenes.ROOT / frame['native']; locale=proof['locale']
    CAPTIONS.mkdir(exist_ok=True)
    marker=run/(locale+'.png'); receipt=CAPTIONS/(locale+'.json')
    scenes.require(not receipt.exists(), 'Reviewed caption training exists')
    x,y,w,h=REGION
    with Image.open(native) as image:image.crop((x,y,x+w,y+h)).convert('RGB').save(marker)
    evidence=scenes.ROOT/proof['introEvidence']
    files=sorted(evidence.glob('*.png'));index=files.index(native) if native in files else None
    negatives=[]; positives=[]
    from select_intro_caption import normalize
    expected=json.loads((run/'expected-text.json').read_text())['strings']['introCaption']
    observed={r['file']:normalize(' '.join(r['lines'])) for r in json.loads((run/'ocr.json').read_text())['rows']} if (run/'ocr.json').exists() else {}
    if index is not None:
        for i in [index-1,index+1]:
            if 0<=i<len(files):
                if observed.get(str(files[i]))==normalize(expected):positives.append({'file':str(files[i])})
                else:negatives.append(str(files[i]))
    neighbor_review=run/'caption-neighbor-review.json'
    reviewed_controls=None
    if neighbor_review.exists():
        reviewed_controls=json.loads(neighbor_review.read_text())
        scenes.require(reviewed_controls['expected']==expected and reviewed_controls['nativeSha256']==scenes.sha(native),
                       'Neighbor review belongs to another caption')
        negatives=[];positives=[];seen=set()
        for row in reviewed_controls['controls']:
            path=Path(row['file'])
            scenes.require(path.resolve().is_relative_to(run.resolve()) and path in files and
                           scenes.sha(path)==row['sha256'] and path not in seen and row['review'], 'Neighbor control changed')
            seen.add(path)
            scenes.require(row['classification'] in ['complete','partial','different'], 'Unknown caption classification')
            if row['classification']=='complete':positives.append({'file':str(path),'sha256':row['sha256']})
            else:negatives.append(str(path))
        scenes.require(index is not None and (index==0 or files[index-1] in seen) and negatives,
                       'Review must include immediate previous frame and a partial/different negative')
    data={'locale':locale,'archiveSha256':json.loads((run/'status.json').read_text())['archiveSha256'],
          'runtimeRenderer':json.loads((run/'status.json').read_text()).get('runtimeRenderer'),
          'expected':json.loads((run/'expected-text.json').read_text())['strings']['introCaption'],
          'markerSha256':scenes.sha(marker),'native':str(native.relative_to(scenes.ROOT)),
          'nativeSha256':scenes.sha(native),'review':proof['visualReview'],
          'marker':{'file':marker.name,'region':REGION,'similarity':.97,'brightTextThreshold':220,'whiteForegroundCoverage':.99},
          'neighboringControls':negatives}
    if reviewed_controls is not None:data['neighborVisualReview']=reviewed_controls
    # The immediate preceding frame must be checked: some locales type across a video cut.
    recipe={'scenes':{'caption':{'positive':str(native),'negative':negatives,'additionalPositive':positives,'markers':[data['marker']]}}}
    control=run/'caption-training-controls.json';scenes.write(control,recipe)
    local_marker=run/marker.name
    import shutil
    if marker != local_marker:shutil.copy2(marker,local_marker)
    source=Path(__file__).parent/'six_scenes.sikuli/six_scenes.py'
    verifier=run/('caption-verifier-'+scenes.sha(source)[:12]+'.py')
    if verifier.exists():scenes.require(scenes.sha(verifier)==scenes.sha(source),'Frozen verifier changed')
    else:shutil.copy2(source,verifier)
    data['verifierSha256']=scenes.sha(verifier)
    result=subprocess.run([str(scenes.JAVA),'-Djava.awt.headless=true','-cp',str(scenes.JAR),'org.python.util.jython',
                           str(verifier),'verify',str(control),str(run/'caption-verification.json')],
                          text=True,capture_output=True,timeout=120)
    (run/'caption-training.log').write_text(result.stdout+result.stderr)
    scenes.require(result.returncode==0,'Caption control failed; inspect caption-training.log before accepting training')
    data['verificationSha256']=scenes.sha(run/'caption-verification.json')
    scenes.require(not (CAPTIONS/marker.name).exists(), 'Existing unreviewed canonical marker')
    shutil.copy2(marker,CAPTIONS/marker.name)
    scenes.write(receipt,data)
