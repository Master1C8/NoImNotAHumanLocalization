#!/usr/bin/env python3
"""One click after fresh native region, exact fixture/window and focus checks."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

from run_capture import ROOT, SCRIPT, MAGICK, sha


def run(reference, region, point, output):
    if not reference.is_file() or not output.is_relative_to(ROOT/'outputs'):
        raise ValueError('Missing reference or noncanonical output')
    output.mkdir(parents=True,exist_ok=False)
    worker=output/'worker';worker.mkdir()
    for name in ['window_info.swift','target_input.swift']:
        shutil.copy2(SCRIPT/name,worker/name)
    for name,binary in [('window_info','window-info'),('target_input','target-input')]:
        subprocess.run(['/usr/bin/xcrun','swiftc','-module-cache-path','/private/tmp/no-human-swift-cache',
                        str(worker/(name+'.swift')),'-o',str(worker/binary)],check=True)
    info=json.loads(subprocess.check_output([str(worker/'window-info')],text=True))
    windows=[w for w in info['windows'] if w.get('kCGWindowName')=='NoImNotAHuman']
    if len(windows)!=1 or not info['screenRecordingAllowed']:
        raise ValueError('Expected one readable fixture window')
    win=windows[0];pid=str(win['kCGWindowOwnerPID']);window=str(win['kCGWindowNumber'])
    frame=output/'before.png'
    subprocess.run(['/usr/sbin/screencapture','-x','-o','-l',window,str(frame)],check=True)
    geometry=f'[{region[2]}x{region[3]}+{region[0]}+{region[1]}]'
    compared=subprocess.run([str(MAGICK),'compare','-metric','RMSE',str(reference)+geometry,
                            str(frame)+geometry,'null:'],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    metric=float(compared.stderr.split('(')[1].split(')')[0]) if compared.returncode in [0,1] else None
    receipt={'reference':str(reference.relative_to(ROOT)),'referenceSha256':sha(reference),
             'region':region,'normalizedRmse':metric,'point':point,'window':win,'inputSent':False,
             'workerHashes':{p.name:sha(p) for p in worker.iterdir() if p.is_file()}}
    def record(): (output/'action.json').write_text(json.dumps(receipt,indent=2)+'\n')
    record()
    if metric is None or metric>.06:
        raise ValueError('Expected UI region changed; no input sent')
    subprocess.run([str(worker/'target-input'),'focus',pid,window],check=True)
    time.sleep(.2)
    receipt['afterFocus']=json.loads(subprocess.check_output([str(worker/'window-info')],text=True))
    record()
    result=subprocess.run([str(worker/'target-input'),'click',pid,window,*map(str,point)],text=True,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    receipt.update(inputSent=result.returncode==0,returnCode=result.returncode,message=result.stderr)
    record()
    print(json.dumps({'action':str(output/'action.json'),'inputSent':receipt['inputSent']}))
    if result.returncode: raise SystemExit('Guarded click refused')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--region',type=int,nargs=4,required=True,metavar=('X','Y','W','H'))
    p.add_argument('--point',type=float,nargs=2,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.reference.resolve(),a.region,a.point,a.output.resolve())
