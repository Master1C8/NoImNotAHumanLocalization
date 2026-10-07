"""One-field saved-locale changes in the stopped, isolated Wine prefix only."""
import copy
import json
from pathlib import Path
import re
import subprocess

from probe_assets import ROOT, require, digest
from build_locale_probe import LANGUAGES

FIXTURE = ROOT/'runtime/No Human Probe.app'
PREFERENCES = FIXTURE/'Contents/SharedSupport/prefix/user.reg'
SETTING = '"SettingsPrefsData_h3770934882"=hex:'


def read_settings(text):
    section = '[Software\\\\Trioskaz\\\\NoImNotAHuman]'
    require(text.count(section)==1 and text.count(SETTING)==1, 'Missing/ambiguous game preferences')
    start=text.index(section)
    end=text.find('\n[',start+1)
    end=len(text) if end<0 else end
    match=re.search(re.escape(SETTING)+r'((?:[^\n]*\\\n)*[^\n]*)',text)
    require(match is not None and start<match.start()<end, 'Settings key outside game section')
    raw=bytes.fromhex(match.group(1).replace('\\\n','').replace(',',' '))
    require(raw.endswith(b'\0') and raw.count(b'"SelectedLanguage"')==1, 'Ambiguous saved language')
    settings=json.loads(raw[:-1])
    require(isinstance(settings['TextSettingsData']['SelectedLanguage'],str), 'Invalid saved locale')
    return match,raw,settings


def replace_language(text, expected, target):
    match,raw,before=read_settings(text)
    require(before['TextSettingsData']['SelectedLanguage']==expected, 'Saved locale changed before mutation')
    require(target in LANGUAGES or target in ['ru','en','ar'], 'Unsupported probe locale')
    if expected==target:
        return text,before
    old=json.dumps(expected).encode('ascii');new=json.dumps(target).encode('ascii')
    pattern=rb'("SelectedLanguage"\s*:\s*)'+re.escape(old)
    changed,count=re.subn(pattern,lambda m:m.group(1)+new,raw)
    require(count==1,'Ambiguous saved locale field')
    after=json.loads(changed[:-1]);wanted=copy.deepcopy(before)
    wanted['TextSettingsData']['SelectedLanguage']=target
    require(after==wanted,'Unrelated preferences changed')
    pieces=[','.join(f'{b:02x}' for b in changed[i:i+32]) for i in range(0,len(changed),32)]
    encoded=',\\\n  '.join(pieces)
    result=text[:match.start(1)]+encoded+text[match.end(1):]
    require(read_settings(result)[2]==wanted,'Preferences did not round-trip')
    return result,before


def set_language(expected,target,output):
    require(output.is_relative_to(ROOT/'outputs'),'Noncanonical output')
    require(PREFERENCES.resolve().is_relative_to(FIXTURE.resolve()),'Preferences escaped fixture')
    processes=subprocess.run(['ps','-axo','pid,command'],check=True,text=True,stdout=subprocess.PIPE).stdout
    require(not any(str(FIXTURE) in line or 'NoImNotAHuman.exe' in line or 'wineserver' in line
                    for line in processes.splitlines()),'Wine must be stopped before offline preferences edit')
    text=PREFERENCES.read_text();changed,before=replace_language(text,expected,target)
    output.mkdir(parents=True,exist_ok=False)
    backup=output/'before-user.reg';backup.write_bytes(PREFERENCES.read_bytes())
    temporary=PREFERENCES.with_name('user.reg.locale-probe-tmp')
    require(not temporary.exists(),'Unreconciled preferences temporary file')
    temporary.write_text(changed);temporary.replace(PREFERENCES)
    require(read_settings(PREFERENCES.read_text())[2]['TextSettingsData']['SelectedLanguage']==target,'Installed preference mismatch')
    receipt={'expectedLocale':expected,'targetLocale':target,'beforeSha256':digest(backup),
             'afterSha256':digest(PREFERENCES),'onlyLogicalFieldChanged':'TextSettingsData.SelectedLanguage',
             'unrelatedSettingsCompared':True,'runtimeRestoration':'not-yet-verified'}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt
