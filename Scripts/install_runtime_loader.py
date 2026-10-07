#!/usr/bin/env python3
"""Install the pinned official IL2CPP loader only in the stopped isolated fixture."""
import argparse
import json
from pathlib import Path
import subprocess
import zipfile
from probe_assets import ROOT,require,digest
from fixture_preferences import FIXTURE,PREFERENCES
from install_locale_probe import GAME

EXPECTED='f4cc496bd098a0df4164b81e3737297707f13a47c2478dba2f60eefab784817a'
URL='https://builds.bepinex.dev/projects/bepinex_be/788/BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.788%2B5b766a3.zip'

def install(archive,output):
    require(output.is_relative_to(ROOT/'outputs'),'Noncanonical output')
    require(digest(archive)==EXPECTED,'Loader archive changed')
    processes=subprocess.check_output(['ps','-axo','pid,command'],text=True)
    require(not any(str(FIXTURE) in l or 'NoImNotAHuman.exe' in l or 'wineserver' in l for l in processes.splitlines()),'Fixture must be stopped')
    require(GAME.resolve().is_relative_to(FIXTURE.resolve()) and PREFERENCES.resolve().is_relative_to(FIXTURE.resolve()),'Fixture escaped scope')
    z=zipfile.ZipFile(archive);names=[n for n in z.namelist() if not n.endswith('/')]
    require(len(names)==len(set(names)),'Duplicate archive entries')
    for name in names:
        target=GAME/name
        require(not Path(name).is_absolute() and target.resolve().is_relative_to(GAME.resolve()),'Archive path escaped fixture')
        require(not target.exists(),'Existing loader file; reconcile before install: '+name)
    preferences=PREFERENCES.read_text()
    section='[Software\\\\Wine\\\\AppDefaults\\\\NoImNotAHuman.exe\\\\DllOverrides]'
    require(section not in preferences,'Existing game-specific DLL override; preserve it')
    output.mkdir(parents=True,exist_ok=False)
    (output/'before-user.reg').write_bytes(PREFERENCES.read_bytes())
    receipt={'sourceUrl':URL,'archiveSha256':EXPECTED,'fixture':str(FIXTURE),'completed':False,'files':[],
             'registryScope':'Only NoImNotAHuman.exe winhttp=native,builtin in copied prefix',
             'commitBoundary':'Files then one registry replacement, no transaction; do not launch until completed.'}
    def record():(output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    record()
    for name in names:
        dest=GAME/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(name))
        receipt['files'].append({'relativePath':name,'sha256':digest(dest)})
    record()
    temporary=PREFERENCES.with_name('user.reg.loader-tmp');require(not temporary.exists(),'Unreconciled registry temporary file')
    changed=preferences+'\n'+section+'\n"winhttp"="native,builtin"\n'
    temporary.write_text(changed);temporary.replace(PREFERENCES)
    require(PREFERENCES.read_text()==changed,'Registry differs')
    receipt.update(completed=True,beforeRegistrySha256=digest(output/'before-user.reg'),afterRegistrySha256=digest(PREFERENCES));record()
    print(json.dumps({'receipt':str(output/'receipt.json'),'files':len(names),'completed':True}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();install(a.archive.resolve(),a.output.resolve())
