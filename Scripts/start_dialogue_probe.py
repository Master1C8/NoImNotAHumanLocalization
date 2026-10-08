#!/usr/bin/env python3
"""Start one bounded dialogue observation in the stopped, isolated fixture."""
import argparse,copy,json,re,shutil,subprocess,sys,time
from pathlib import Path
from probe_assets import ROOT,require,digest
from fixture_preferences import FIXTURE,PREFERENCES,read_settings,replace_language
from run_saved_locale_probe import state,wait_menu,run_capture,guarded_click

GAME=FIXTURE/'Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human'
CONFIG=GAME/'BepInEx/config/nohuman-dialogue-probe.json'
SAVE=FIXTURE/'Contents/SharedSupport/prefix/drive_c/users/Sikarugir/AppData/LocalLow/Trioskaz/NoImNotAHuman'

def enable_typewriter(text):
    match,raw,before=read_settings(text)
    require(isinstance(before['TextSettingsData']['IsUseTypewriter'],bool),'Unexpected typewriter preference')
    changed,count=re.subn(rb'("IsUseTypewriter"\s*:\s*)(?:false|true)',lambda m:m.group(1)+b'true',raw)
    require(count==1,'Ambiguous typewriter field')
    wanted=copy.deepcopy(before);wanted['TextSettingsData']['IsUseTypewriter']=True
    require(json.loads(changed[:-1])==wanted,'Unrelated preferences changed')
    pieces=[','.join(f'{b:02x}' for b in changed[i:i+32]) for i in range(0,len(changed),32)]
    result=text[:match.start(1)]+',\\\n  '.join(pieces)+text[match.end(1):]
    require(read_settings(result)[2]==wanted,'Typewriter preference round-trip failed')
    return result

def run(locale,sample,output):
    require(output.is_relative_to(ROOT/'outputs'),'Noncanonical output')
    output.mkdir(parents=True,exist_ok=False)
    frozen=output/'frozen-helpers';frozen.mkdir()
    for source in (ROOT/'Scripts').rglob('*'):
        if source.is_file() and source.suffix in ['.py','.swift']:
            target=frozen/source.relative_to(ROOT/'Scripts');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    run_capture.SCRIPT=frozen/'visual-qa';guarded_click.SCRIPT=run_capture.SCRIPT
    helper=output/'window-info'
    subprocess.run(['/usr/bin/xcrun','swiftc','-module-cache-path','/private/tmp/no-human-swift-cache',
                    str(run_capture.SCRIPT/'window_info.swift'),'-o',str(helper)],check=True)
    info=state(helper)
    require(not info['applications'] and not info['windows'],
            'The copied game is in use; preserve its window and preferences')
    processes=subprocess.run(['ps','-axo','pid,command'],check=True,text=True,
                             stdout=subprocess.PIPE).stdout.splitlines()
    require(not any(str(FIXTURE) in line or 'NoImNotAHuman.exe' in line or
                    'wineserver' in line for line in processes),
            'Game or Wine is running; preserve the fixture')
    (output/'initial-state.json').write_text(json.dumps(info,indent=2)+'\n')
    require(not CONFIG.exists(),'Existing probe config requires reconciliation')
    shutil.copy2(PREFERENCES,output/'before-user.reg')
    shutil.copytree(SAVE,output/'before-save-directory')
    initial=PREFERENCES.read_text();before=read_settings(initial)[2]
    changed,_=replace_language(initial,before['TextSettingsData']['SelectedLanguage'],locale)
    changed=enable_typewriter(changed)
    tmp=PREFERENCES.with_name('user.reg.dialogue-probe-tmp');require(not tmp.exists(),'Unreconciled preference temporary')
    tmp.write_text(changed);tmp.replace(PREFERENCES)
    CONFIG.write_text(json.dumps({'enabled':True,'sample':sample},ensure_ascii=False)+'\n')
    receipt={'phase':'launch-request','locale':locale,'initialSettings':before,
             'probeSettings':read_settings(changed)[2],'preferencesBackupSha256':digest(output/'before-user.reg'),
             'moduleSha256':digest(GAME/'BepInEx/plugins/NoHuman.TextRenderer/NoHuman.TextRenderer.dll'),
             'configSha256':digest(CONFIG),'sample':sample,
             'sourceHashes':{str(p.relative_to(frozen)):digest(p) for p in frozen.rglob('*') if p.is_file()}}
    def record():(output/'status.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    record();subprocess.run(['/usr/bin/open',str(FIXTURE)],check=True)
    wait_menu(helper,ROOT/'outputs/renderer-final-runtime/ru/menu/native.png',output/'readiness')
    run_capture.run(output/'menu',None)
    guarded_click.run(output/'menu/native.png',[580,1580,324,100],[372,818],output/'new-game',
                      extra_guards=[(ROOT/'outputs/renderer-final-runtime/ru/menu/native.png',
                                     [0,100,500,450],.12)])
    time.sleep(2)
    run_capture.run(output/'after-new-game',None)
    receipt['phase']='new-game-input-sent; next-frame-review-required';record()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--locale',required=True);p.add_argument('--sample');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.locale,a.sample,a.output.resolve())
