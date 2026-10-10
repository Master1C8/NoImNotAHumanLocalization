#!/usr/bin/env python3
"""Verify archived full/neighbor caption controls with the current frozen matcher."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
import capture_six_scenes as scenes
from learn_intro_caption import CAPTIONS


def verify(output, upgrade=False):
    scenes.require(output.is_relative_to(scenes.ROOT/'outputs') and not output.exists(), 'Use a new canonical verification output')
    output.mkdir()
    source=Path(__file__).parent/'six_scenes.sikuli/six_scenes.py'
    frozen=output/'verifier.py';shutil.copy2(source,frozen)
    rows=[]
    for receipt in sorted(CAPTIONS.glob('*.json')):
        data=json.loads(receipt.read_text());locale=data['locale'];native=scenes.ROOT/data['native']
        scenes.require(scenes.sha(native)==data['nativeSha256'] and data['review']['status']=='pass', 'Reviewed caption source changed')
        marker=CAPTIONS/data['marker']['file'];scenes.require(scenes.sha(marker)==data['markerSha256'],'Caption marker changed')
        run=native.parents[2]
        control=run/'caption-training-controls.json'
        scenes.require(control.is_file(),'Original caption controls missing')
        recipe=json.loads(control.read_text());scene=recipe['scenes']['caption']
        scene['markers']=[dict(data['marker'],file=str(marker),whiteForegroundCoverage=.99)]
        inputs=[Path(scene['positive'])]+[Path(p) for p in scene['negative']]+[Path(p['file']) for p in scene.get('additionalPositive',[])]
        scenes.require(all(p.resolve().is_relative_to(scenes.ROOT/'outputs') and p.is_file() for p in inputs),'Caption controls escaped evidence')
        pins={str(p.relative_to(scenes.ROOT)):scenes.sha(p) for p in inputs}
        recipe_path=output/(locale+'-controls.json');scenes.write(recipe_path,recipe)
        result_path=output/(locale+'-verification.json')
        result=subprocess.run([str(scenes.JAVA),'-Djava.awt.headless=true','-cp',str(scenes.JAR),'org.python.util.jython',
                               str(frozen),'verify',str(recipe_path),str(result_path)],text=True,capture_output=True,timeout=120)
        (output/(locale+'.log')).write_text(result.stdout+result.stderr)
        scenes.require(result.returncode==0,'Caption coverage control failed: '+locale)
        row={'locale':locale,'verifierSha256':scenes.sha(frozen),'controlsSha256':scenes.sha(recipe_path),
             'inputHashes':pins,'verification':str(result_path.relative_to(scenes.ROOT)),
             'verificationSha256':scenes.sha(result_path),'result':'pass'}
        rows.append(row);scenes.write(output/'result.json',{'result':'in-progress','rows':rows})
        if upgrade:
            data['marker']['whiteForegroundCoverage']=.99;data['coverageVerification']=row
            scenes.write(receipt,data)
        print('CAPTION_VERIFIED '+locale,flush=True)
    scenes.write(output/'result.json',{'result':'pass','rows':rows,'upgraded':upgrade})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--upgrade',action='store_true');args=parser.parse_args();verify(args.output.resolve(),args.upgrade)
