#!/usr/bin/env python3
"""Operate the existing exact fixture; never relaunch it or infer a dialogue ID."""
import argparse,json,shutil,subprocess,sys,time
from pathlib import Path
from probe_assets import ROOT,require,digest
from start_dialogue_probe import GAME,CONFIG,PREFERENCES,SAVE
from run_saved_locale_probe import state,stop_fixture

def run(run_dir,action,name):
    require(run_dir.is_relative_to(ROOT/'outputs') and (run_dir/'status.json').is_file(),'Missing run identity')
    out=run_dir/name;out.mkdir(exist_ok=False)
    info=state(run_dir/'window-info');windows=[w for w in info['windows'] if w.get('kCGWindowName')=='NoImNotAHuman']
    require(len(windows)==1 and info['screenRecordingAllowed'],'Expected one readable fixture window')
    win=windows[0];pid=str(win['kCGWindowOwnerPID']);number=str(win['kCGWindowNumber'])
    (out/'before-state.json').write_text(json.dumps(info,indent=2)+'\n')
    evidence=GAME/'BepInEx/config/nohuman-dialogue-evidence.jsonl'
    receipt={'action':action,'window':win,'inputSent':False,'commandSent':False}
    def record():(out/'action.json').write_text(json.dumps(receipt,indent=2)+'\n')
    record()
    status=json.loads((run_dir/'status.json').read_text())
    require(digest(GAME/'BepInEx/plugins/NoHuman.TextRenderer/NoHuman.TextRenderer.dll')==status['moduleSha256'],
            'Installed module differs from the observed run')
    require(digest(CONFIG)==status['configSha256'],'Probe configuration changed')
    if action in ['focus','skip']:
        helper=run_dir/'new-game/worker/target-input'
        subprocess.run([str(helper),'focus',pid,number],check=True)
        receipt['focusRequested']=True;record()
        time.sleep(2)
    if action in ['tap-space','hold-space']:
        # Caller must review the recorded current frame before issuing a new action.
        subprocess.run(['/usr/sbin/screencapture','-x','-o','-l',number,str(out/'before.png')],check=True)
        source=run_dir/'frozen-helpers/visual-qa/target_input.swift';helper=out/'target-input'
        shutil.copy2(source,out/source.name)
        subprocess.run(['/usr/bin/xcrun','swiftc','-module-cache-path','/private/tmp/no-human-swift-cache',str(out/source.name),'-o',str(helper)],check=True)
        subprocess.run([str(helper),'focus',pid,number],check=True);time.sleep(.2)
        subprocess.run([str(helper),action,pid,number],check=True)
        receipt.update(inputSent=True,helperSha256=digest(helper));record()
    elif action=='skip':
        rows=[json.loads(s) for s in evidence.read_text().splitlines()]
        lines=[r['data'] for r in rows if r['kind']=='line'];require(lines,'No observed dialogue')
        line=lines[-1];command={'action':'skip','sequence':line['sequence'],'lineId':line['lineId'],'nonce':name}
        target=GAME/'BepInEx/config/nohuman-dialogue-command.json'
        tmp=target.with_suffix('.tmp');require(not tmp.exists(),'Unreconciled command')
        tmp.write_text(json.dumps(command)+'\n');tmp.replace(target)
        receipt.update(commandSent=True,command=command);record();time.sleep(.8)
    elif action not in ['capture','finish','focus']:raise ValueError('Unsupported action')
    subprocess.run(['/usr/sbin/screencapture','-x','-o','-l',number,str(out/'native.png')],check=True)
    for source in [evidence,GAME/'BepInEx/LogOutput.log',SAVE/'Player.log']:
        shutil.copy2(source,out/source.name)
    receipt['nativeSha256']=digest(out/'native.png');record()
    if action=='finish':
        stop_fixture(run_dir/'window-info',out/'stop.json')
        for source in [evidence,GAME/'BepInEx/LogOutput.log',SAVE/'Player.log']:shutil.copy2(source,out/source.name)
        CONFIG.unlink()
        command=GAME/'BepInEx/config/nohuman-dialogue-command.json'
        if command.exists():command.unlink()
        shutil.copy2(run_dir/'before-user.reg',PREFERENCES)
        require(digest(PREFERENCES)==digest(run_dir/'before-user.reg'),'Preference restoration mismatch')
        receipt.update(fixtureStopped=True,preferencesRestored=True);record()
    print(json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--action',required=True);p.add_argument('--name',required=True)
    a=p.parse_args();run(a.run.resolve(),a.action,a.name)
