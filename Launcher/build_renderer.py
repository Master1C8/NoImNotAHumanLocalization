#!/usr/bin/env python3
"""Combine the two exact reviewed script-specific bindings into one renderer."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(out):
    assert out.is_relative_to(ROOT/'outputs') and not out.exists();out.mkdir(parents=True)
    current=ROOT/'RuntimePlugin'
    pins={str(p.relative_to(ROOT)):sha(p) for p in sorted(current.glob('*')) if p.suffix in ('.cs','.csproj')}
    policy=ROOT/'Resources/Localization/mechanics-v1.json';pins[str(policy.relative_to(ROOT))]=sha(policy)
    source=out/'source';source.mkdir()
    for name in pins:
        p=ROOT/name;(source/p.name).write_bytes(p.read_bytes())
    plugin=source/'Plugin.cs';text=plugin.read_text()
    # Retain the exact already-rendered Hindi/Hebrew bindings while taking every
    # current shared radio/RTL hook. The two sources have the same shaping body.
    previous=ROOT/'outputs/launcher-renderer-v1/source/Plugin.cs'
    approved=json.loads((ROOT/'outputs/launcher-renderer-v1/receipt.json').read_text())
    assert sha(previous)==approved['generatedSourceHashes'][str(previous.relative_to(ROOT))]
    old=previous.read_text()
    start='        if(!HarfBuzz.ContainsHindi(original))return;'
    end='            var prepared=Plugin.Shaper.Shape(original);'
    before=text[text.index(start):text.index(end)]
    after=old[old.index('        if(!string.IsNullOrEmpty(original) && original.Any(c=>c>='):old.index(end)]
    assert text.count(before)==1 and 'HE_KERN' in after and 'HI_BOUND' in after
    text=text.replace(before,after).replace('"0.4.0"','"0.4.1"').replace('RENDERER_READY v0.4.0:','RENDERER_READY v0.4.1:')
    plugin.write_text(text)
    project=source/'NoHuman.TextRenderer.csproj';text=project.read_text()
    text=text.replace('../Resources/Localization/mechanics-v1.json','mechanics-v1.json')
    text=text.replace('<OutputPath>../outputs/renderer-build/bin/</OutputPath>','<OutputPath>'+str(out/'bin')+'/</OutputPath>')
    text=text.replace('  </ItemGroup>','    <Reference Include="$(FixtureGame)/BepInEx/interop/UnityEngine.TextCoreFontEngineModule.dll" Private="false" />\n  </ItemGroup>')
    project.write_text(text)
    game=ROOT/'runtime/No Human Probe.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human'
    env=dict(os.environ,DOTNET_CLI_HOME='/private/tmp/no-human-dotnet-home',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
    subprocess.run(['/private/tmp/no-human-dotnet-sdk/dotnet','build',str(project),'-p:FixtureGame='+str(game),'--nologo','-v:q'],check=True,env=env)
    binary=out/'bin/net6.0/NoHuman.TextRenderer.dll'
    receipt={'version':'0.4.1','currentSourceHashes':pins,'preservedBindingsSha256':sha(previous),'bindingMerge':{'before':before,'after':after},'binarySha256':sha(binary),'generatedSourceHashes':{str(p.relative_to(ROOT)):sha(p) for p in source.iterdir() if p.is_file()},'runtime':'pending'}
    assert all(sha(ROOT/name)==expected for name,expected in pins.items()), 'Renderer source changed during build'
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.out.resolve())
