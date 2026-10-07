#!/usr/bin/env python3
"""Verify saved-locale restoration in the exact fixture, one bounded case at a time.

Native capture readiness is not linguistic acceptance. Review each full frame.
No gameplay inputs, original-prefix writes or broad Wine termination.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from probe_assets import ROOT, digest, require
from fixture_preferences import FIXTURE, PREFERENCES, set_language, read_settings

sys.path.insert(0,str(ROOT/'Scripts/visual-qa'))
import run_capture
import guarded_click

LOG=FIXTURE/'Contents/SharedSupport/prefix/drive_c/users/Sikarugir/AppData/LocalLow/Trioskaz/NoImNotAHuman/Player.log'


def state(helper):
    return json.loads(subprocess.check_output([str(helper)],text=True))


def stop_fixture(helper,receipt):
    info=state(helper);owned=[]
    for app in info['applications']:
        require(app['path'].startswith(str(FIXTURE)+'/'),'Unexpected process path')
        pid=app['pid']
        identity=subprocess.check_output(['ps','-p',str(pid),'-o','lstart=','-o','command='],text=True).strip()
        require(identity.endswith('C:\\windows\\system32\\explorer.exe /desktop') or
                identity.endswith('C:\\KS Games\\No Im not a Human\\NoImNotAHuman.exe'),
                'Unrecognized fixture process; preserve it')
        owned.append({'pid':pid,'path':app['path'],'identity':identity})
    receipt.write_text(json.dumps({'ownedProcesses':owned,'completed':False},indent=2)+'\n')
    for app in reversed(owned):
        identity=subprocess.check_output(['ps','-p',str(app['pid']),'-o','lstart=','-o','command='],text=True).strip()
        require(identity==app['identity'],'Process identity changed before termination')
        os.kill(app['pid'],signal.SIGTERM)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        info=state(helper)
        processes=subprocess.run(['ps','-axo','pid,command'],check=True,text=True,stdout=subprocess.PIPE).stdout
        residual=[line for line in processes.splitlines() if str(FIXTURE) in line or 'NoImNotAHuman.exe' in line or 'wineserver' in line]
        if not info['applications'] and not info['windows'] and not residual:
            receipt.write_text(json.dumps({'ownedProcesses':owned,'completed':True,'remainingFixtureApps':0,
                                          'remainingGameOrWineServerProcesses':0},indent=2)+'\n')
            return
        time.sleep(.5)
    raise ValueError('Fixture processes did not stop; preserve live state')


def wait_menu(helper,reference,output):
    output.mkdir()
    deadline=time.monotonic()+60;attempts=[]
    while time.monotonic()<deadline:
        info=state(helper)
        windows=[w for w in info['windows'] if w.get('kCGWindowName')=='NoImNotAHuman']
        if len(windows)==1 and info['screenRecordingAllowed']:
            window=windows[0]
            if window['kCGWindowBounds']!={'Height':900,'Width':1440,'X':0,'Y':0}:
                attempts.append({'window':window['kCGWindowNumber'],'transientBounds':window['kCGWindowBounds']})
                (output/'readiness.json').write_text(json.dumps({'attempts':attempts,'passed':False},indent=2)+'\n')
                time.sleep(1)
                continue
            frame=output/'latest.png'
            subprocess.run(['/usr/sbin/screencapture','-x','-o','-l',str(window['kCGWindowNumber']),str(frame)],check=True)
            # Menu-specific button border, unaffected by changing sample or font.
            geometry='[320x18+1280+1574]'
            result=subprocess.run([str(run_capture.MAGICK),'compare','-metric','RMSE',str(reference)+geometry,
                                   str(frame)+geometry,'null:'],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            metric=float(result.stderr.split('(')[1].split(')')[0]) if result.returncode in [0,1] else None
            attempts.append({'window':window['kCGWindowNumber'],'normalizedBorderRmse':metric})
            (output/'readiness.json').write_text(json.dumps({'attempts':attempts,'passed':False},indent=2)+'\n')
            if metric is not None and metric<.06:
                (output/'readiness.json').write_text(json.dumps({'attempts':attempts,'passed':True},indent=2)+'\n')
                return
        time.sleep(1)
    raise ValueError('Menu readiness timeout; retain process/logs for diagnosis')


def run(codes,reference,output,resume_case=None):
    require(output.is_relative_to(ROOT/'outputs') and reference.is_file(),'Canonical output/reference required')
    output.mkdir(parents=True,exist_ok=False)
    frozen=output/'frozen-helpers';frozen.mkdir()
    # Python helpers are already loaded. Every later Swift read uses this snapshot.
    for source in (ROOT/'Scripts').rglob('*'):
        if source.is_file() and source.suffix in ['.py','.swift']:
            dest=frozen/source.relative_to(ROOT/'Scripts');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    run_capture.SCRIPT=frozen/'visual-qa';guarded_click.SCRIPT=run_capture.SCRIPT
    helper=output/'window-info'
    subprocess.run(['/usr/bin/xcrun','swiftc','-module-cache-path','/private/tmp/no-human-swift-cache',
                    str(run_capture.SCRIPT/'window_info.swift'),'-o',str(helper)],check=True)
    run_info={'expectedCodes':codes,'sourceHashes':{str(p.relative_to(frozen)):digest(p) for p in frozen.rglob('*') if p.is_file()},
              'initialSavedLocale':read_settings(PREFERENCES.read_text())[2]['TextSettingsData']['SelectedLanguage'],
              'coverage':'Saved locale restoration, menu sample loading and settings selector. No shaping/layout/dialogue/progression acceptance.'}
    (output/'run.json').write_text(json.dumps(run_info,indent=2)+'\n')
    if resume_case:
        status=json.loads((resume_case/'status.json').read_text())
        require(status=={'phase':'launch-request','expectedLocale':codes[0]},'Unsupported resume phase/code')
        require(run_info['initialSavedLocale']==codes[0],'Live resume locale changed')
        require(len([w for w in state(helper)['windows'] if w.get('kCGWindowName')=='NoImNotAHuman'])==1,
                'Expected existing fixture window for resume')
        (output/'resume.json').write_text(json.dumps({'case':str(resume_case.relative_to(ROOT)),
            'state':state(helper),'launchRepeated':False,'savedLocaleRewritten':False},indent=2)+'\n')
    else:
        stop_fixture(helper,output/'initial-stop.json')
    rows=[]
    for index,code in enumerate(codes):
        step=output/code;step.mkdir()
        previous=read_settings(PREFERENCES.read_text())[2]['TextSettingsData']['SelectedLanguage']
        if resume_case and index==0:
            shutil.copytree(resume_case/'preferences',step/'preferences')
            pref=json.loads((step/'preferences/receipt.json').read_text())
            require(pref['targetLocale']==code,'Prior preference receipt differs')
        else:
            pref=set_language(previous,code,step/'preferences')
        (step/'status.json').write_text(json.dumps({'phase':'launch-request','expectedLocale':code},indent=2)+'\n')
        if not (resume_case and index==0):
            subprocess.run(['/usr/bin/open',str(FIXTURE)],check=True)
        wait_menu(helper,reference,step/'readiness')
        run_capture.run(step/'menu',None)
        guarded_click.run(step/'menu/native.png',[1280,1580,320,100],[720,818],step/'open-settings')
        time.sleep(.5)
        run_capture.run(step/'settings',None)
        restored=read_settings(PREFERENCES.read_text())[2]['TextSettingsData']['SelectedLanguage']
        require(restored==code,'Runtime changed saved locale unexpectedly')
        pref.update(runtimeRestoration='passed-in-preferences; native-frame-review-pending')
        (step/'preferences/receipt.json').write_text(json.dumps(pref,indent=2)+'\n')
        shutil.copy2(LOG,step/'Player.log')
        text=(step/'Player.log').read_text()
        failures={key:text.count(key) for key in ['CRC Mismatch','Unable to load asset','No translation found','KeyNotFoundException','NullReferenceException']}
        row={'expectedLocale':code,'runtimeLocale':None,'savedLocaleAfterLaunch':restored,'resourceFailureCounts':failures,
             'menu':str((step/'menu/native.png').relative_to(ROOT)),'settings':str((step/'settings/native.png').relative_to(ROOT)),
             'visualReview':'pending','inputActions':1}
        rows.append(row);(output/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n')
        stop_fixture(helper,step/'stop.json')
        (step/'status.json').write_text(json.dumps({'phase':'stopped-and-captured','expectedLocale':code},indent=2)+'\n')
        print('CAPTURED_SAVED_LOCALE '+code,flush=True)
        require(not any(failures.values()),'Resource failure: stop subsequent cases for diagnosis')
    (output/'completion.json').write_text(json.dumps({'completedCases':len(rows),'fixtureStopped':True,'visualReview':'pending'},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--codes',nargs='+',required=True)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--resume-case',type=Path)
    a=p.parse_args();run(a.codes,a.reference.resolve(),a.output.resolve(),a.resume_case.resolve() if a.resume_case else None)
