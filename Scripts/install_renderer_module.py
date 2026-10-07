#!/usr/bin/env python3
"""Install a built renderer module into the stopped, prepared fixture only."""
import argparse,json,shutil,subprocess,zipfile
from pathlib import Path
from fixture_preferences import FIXTURE
from install_locale_probe import GAME
from probe_assets import ROOT,digest,require
PACKAGE_SHA='526e22c0b773f57b5a0d202cb6135975ebfa74c8b2ece0681ceae8accacc632a'
FONT_SHA='e691fe27813ec6ed11d0a5be4c6c1f6739996ed682462eaa3244a6185217dd6c'


def install(build,font_build,package,previous,output):
    require(output.is_relative_to(ROOT/'outputs'),'Output escaped canonical scope')
    process_text=subprocess.check_output(['ps','-axo','pid,command'],text=True)
    require(not any(str(FIXTURE) in l or 'NoImNotAHuman.exe' in l or 'wineserver' in l for l in process_text.splitlines()),'Fixture must be stopped')
    require(digest(package)==PACKAGE_SHA,'Native package changed')
    require(digest(font_build/'hi-source.ttf')==FONT_SHA,'Shaping font changed')
    font_receipt=json.loads((font_build/'receipt.json').read_text());require(font_receipt['completed'],'Font build incomplete')
    for row in font_receipt['files']:
        require(digest(GAME/row['path'])==row['afterSha256'],'Installed font assets changed')
    target=GAME/'BepInEx/plugins/NoHuman.TextRenderer';require(target.resolve().is_relative_to(FIXTURE.resolve()),'Fixture escaped scope')
    prior=json.loads(previous.read_text());require(prior['completed'],'Previous module installation incomplete')
    old=prior['files'];require({p.name for p in target.iterdir()}==set(old),'Unexpected plugin files')
    for name,expected in old.items():require(digest(target/name)==expected,'Previous module changed: '+name)
    output.mkdir(parents=True,exist_ok=False);payload=output/'payload';payload.mkdir();backup=output/'before';backup.mkdir()
    shutil.copy2(build,payload/'NoHuman.TextRenderer.dll');shutil.copy2(font_build/'hi-source.ttf',payload/'hi-source.ttf')
    with zipfile.ZipFile(package) as z:
        (payload/'libHarfBuzzSharp.dll').write_bytes(z.read('runtimes/win-x64/native/libHarfBuzzSharp.dll'))
        for name in ['LICENSE.txt','THIRD-PARTY-NOTICES.txt']:(output/name).write_bytes(z.read(name))
    sources={str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'RuntimePlugin').iterdir() if p.is_file()}
    receipt={'completed':False,'files':{p.name:digest(p) for p in payload.iterdir()},'beforeFiles':old,'sourceHashes':sources,
             'nativePackageSha256':PACKAGE_SHA,'fontReceiptSha256':digest(font_build/'receipt.json'),
             'commitBoundary':'Per-file atomic replace, not a transaction; fixture must stay stopped until completed.'}
    def record():(output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    record()
    for name in receipt['files']:
        shutil.copy2(target/name,backup/name)
        require(digest(target/name)==old[name],'Module changed before replacement')
        temp=target/(name+'.renderer-tmp');require(not temp.exists(),'Unreconciled replacement')
        shutil.copy2(payload/name,temp);temp.replace(target/name)
    for name,expected in receipt['files'].items():require(digest(target/name)==expected,'Installed module hash mismatch')
    receipt['completed']=True;record();print(json.dumps({'completed':True,'receipt':str(output/'receipt.json')}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['build','font-build','package','previous','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();install(a.build.resolve(),a.font_build.resolve(),a.package.resolve(),a.previous.resolve(),a.output.resolve())
