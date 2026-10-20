#!/usr/bin/env python3
"""Build the adapted native launchers; preserve previous build directories."""
import argparse, hashlib, json, os, plistlib, shutil, struct, subprocess, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=Path('/Users/antonkrutov/Desktop/StardewTranslationInstaller')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args, **kw): subprocess.run([str(x) for x in args],check=True,**kw)
def resource(kind, ident, data):
    header=struct.pack('<IIHHHHIHHII',len(data),32,65535,kind,65535,ident,0,0x30,0x409,0,0)
    return header+data+b'\0'*((-len(data))%4)
def windows_resources():
    result=struct.pack('<IIHHHHIHHII',0,32,65535,0,65535,0,0,0,0,0,0)
    result+=resource(24,1,(ROOT/'Launcher/Windows.manifest').read_bytes())
    ico=(ROOT/'Launcher/Icons/Game.ico').read_bytes()
    reserved,kind,count=struct.unpack_from('<HHH',ico)
    assert (reserved,kind)==(0,1) and count>0, 'Game icon must be a Windows ICO'
    group=struct.pack('<HHH',0,1,count)
    for i in range(count):
        w,h,colors,reserved,planes,bits,size,offset=struct.unpack_from('<BBBBHHII',ico,6+16*i)
        assert offset>=6+16*count and offset+size<=len(ico)
        result+=resource(3,i+1,ico[offset:offset+size])
        group+=struct.pack('<BBBBHHIH',w,h,colors,reserved,planes,bits,size,i+1)
    return result+resource(14,1,group)
def build(payload,out,zig):
    assert payload.is_relative_to(ROOT/'outputs') and out.is_relative_to(ROOT/'outputs')
    assert not out.exists(), 'Use a new versioned build directory'
    # Adaptation provenance is historical; the base checkout may legitimately advance.
    run(['git','-C',BASE,'cat-file','-e','d4154ff15c7c27c801d197750db36c39bc460aa8^{commit}'])
    expected='#pragma once\n#define NH_INVENTORY_SHA "'+sha(payload/'inventory.tsv')+'"\n'
    assert (ROOT/'Launcher/payload_pin.h').read_text()==expected, 'Update the reviewed payload pin before building'
    source_pins={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'Launcher').rglob('*')) if p.is_file()}
    out.mkdir(parents=True)
    env=os.environ.copy();env.update(ZIG_GLOBAL_CACHE_DIR='/private/tmp/nohuman-zig-global',ZIG_LOCAL_CACHE_DIR='/private/tmp/nohuman-zig-local')
    flags=['-O2']
    c=[ROOT/'Launcher/engine.c',ROOT/'Launcher/vendor/zstd/zstddeclib.c']
    win=out/'No Human Launcher Windows';(win/'Resources').mkdir(parents=True)
    # Standard Microsoft .res header avoids an extra host resource compiler.
    (out/'Windows.res').write_bytes(windows_resources())
    run([zig,'cc','-target','x86_64-windows-gnu',*flags,'-municode','-Wl,--subsystem,windows',ROOT/'Launcher/Windows.c',*c,out/'Windows.res','-lcomctl32','-lshell32','-lole32','-luuid','-lbcrypt','-ladvapi32','-lgdi32','-o',win/'No Human Launcher.exe'],env=env)
    pe=(win/'No Human Launcher.exe').read_bytes();header=struct.unpack_from('<I',pe,0x3c)[0]
    assert pe[header:header+4]==b'PE\0\0' and struct.unpack_from('<H',pe,header+24+68)[0]==2, 'Windows GUI subsystem required'
    shutil.copytree(payload,win/'Resources/Payload')
    app=out/'No Human Launcher.app';mac=app/'Contents/MacOS';res=app/'Contents/Resources';mac.mkdir(parents=True);res.mkdir()
    for arch in ['arm64','x86_64']:
        run(['clang','-target',arch+'-apple-macos14',*flags,'-DNOHUMAN_CLI','-Wno-deprecated-declarations',*c,'-o',out/('engine-'+arch)])
        run(['swiftc','-parse-as-library','-O','-target',arch+'-apple-macos14','-module-cache-path','/private/tmp/nohuman-swift-cache',ROOT/'Launcher/macOS.swift','-o',out/('ui-'+arch)])
    for name,prefix in [('nohuman-engine','engine-'),('No Human Launcher','ui-')]:run(['lipo','-create',out/(prefix+'arm64'),out/(prefix+'x86_64'),'-output',mac/name])
    shutil.copytree(payload,res/'Payload');shutil.copy(ROOT/'Launcher/Icons/Game.icns',res/'App.icns')
    info={'CFBundleName':'No Human Launcher','CFBundleDisplayName':'VN Revival — No, I’m not a Human','CFBundleExecutable':'No Human Launcher','CFBundleIdentifier':'fun.vnrevival.nohuman.launcher','CFBundleVersion':'3','CFBundleShortVersionString':'0.2.1','CFBundlePackageType':'APPL','LSMinimumSystemVersion':'14.0','NSHighResolutionCapable':True,'CFBundleIconFile':'App.icns'}
    (app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
    for destination in [res,win/'Resources']:
        shutil.copytree(ROOT/'Launcher/Licenses',destination/'Licenses')
        shutil.copy(ROOT/'Launcher/README.md',destination/'README.md')
        locales=[line.split('\t')[0] for line in (payload/'locales.tsv').read_text().splitlines()]
        provenance=json.loads((payload/'provenance.json').read_text())
        assert len(set(locales))==len(locales) and set(locales)=={p['locale'] for p in provenance['reviewedProfiles']}
        required=['Payload/'+line.split('\t')[0] for line in (payload/'inventory.tsv').read_text().splitlines()]+['Payload/inventory.tsv']
        manifest={'schemaVersion':1,'gameSlug':'no-im-not-a-human','platform':'macos' if destination==res else 'windows','releaseVersion':'0.2.1','locales':{locale:{'requiredPaths':required} for locale in locales}}
        (destination/'vnrevival-locales.json').write_text(json.dumps(manifest,indent=2)+'\n')
    run(['codesign','--force','--deep','--sign','-',app]);run(['codesign','--verify','--deep','--strict',app])
    # Delivery archives are generated only after compilation and signature validation.
    archives={}
    for platform,folder in [('macOS',app),('Windows',win)]:
        target=out/('NoHuman-Launcher-'+platform+'-0.2.1.zip')
        if platform=='macOS':run(['ditto','-c','-k','--norsrc','--noextattr','--noqtn','--keepParent',folder,target])
        else:
            with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
                for p in sorted(folder.rglob('*')):
                    if p.is_file():z.write(p,p.relative_to(out))
        assert target.stat().st_size<=100_000_000, 'Package exceeds the distribution limit'
        archives[platform]={'path':str(target.relative_to(ROOT)),'bytes':target.stat().st_size,'sha256':sha(target)}
    assert all(sha(ROOT/name)==expected for name,expected in source_pins.items()), 'Build source changed during compilation'
    (out/'build.json').write_text(json.dumps({'sourceHashes':source_pins,'baseRevision':'d4154ff15c7c27c801d197750db36c39bc460aa8','payloadInventorySha256':sha(payload/'inventory.tsv'),'archives':archives},indent=2)+'\n')
    print(json.dumps(archives))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--payload',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--zig',type=Path,required=True);a=p.parse_args();build(a.payload.resolve(),a.out.resolve(),a.zig.resolve())
