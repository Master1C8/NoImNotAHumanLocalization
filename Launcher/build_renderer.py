#!/usr/bin/env python3
"""Combine the two exact reviewed script-specific bindings into one renderer."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(out):
    assert out.is_relative_to(ROOT/'outputs') and not out.exists();out.mkdir(parents=True)
    plan=json.loads((ROOT/'outputs/six-scenes-all-locales-v8/batch.json').read_text())['plan']
    hi=next(r['renderer'] for r in plan if r['locale']=='hi');he=next(r['renderer'] for r in plan if r['locale']=='he')
    source=out/'source';source.mkdir()
    for name,expected in hi['build']['generatedSourceHashes'].items():
        p=ROOT/name;assert sha(p)==expected;(source/p.name).write_bytes(p.read_bytes())
    plugin=source/'Plugin.cs';text=plugin.read_text()
    before,after=next((a,b) for a,b in he['build']['changes'] if 'HE_KERN' in b)
    assert text.count(before)==1 and after not in text;text=text.replace(before,after)
    assert text.count('"0.3.2"')==1 and text.count('RENDERER_READY v0.3.2:')==1
    text=text.replace('"0.3.2"','"0.3.4"').replace('RENDERER_READY v0.3.2:','RENDERER_READY v0.3.4:');plugin.write_text(text)
    project=source/'NoHuman.TextRenderer.csproj';text=project.read_text()
    old='<OutputPath>'+str(ROOT/'outputs/capture-renderer-build-hi-v1/bin')+'/</OutputPath>'
    assert text.count(old)==1;text=text.replace(old,'<OutputPath>'+str(out/'bin')+'/</OutputPath>')
    text=text.replace('  </ItemGroup>','    <Reference Include="$(FixtureGame)/BepInEx/interop/UnityEngine.TextCoreFontEngineModule.dll" Private="false" />\n  </ItemGroup>');project.write_text(text)
    game=ROOT/'runtime/No Human Probe.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human'
    env=dict(os.environ,DOTNET_CLI_HOME='/private/tmp/no-human-dotnet-home',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
    subprocess.run(['/private/tmp/no-human-dotnet-sdk/dotnet','build',str(project),'-p:FixtureGame='+str(game),'--nologo','-v:q'],check=True,env=env)
    binary=out/'bin/net6.0/NoHuman.TextRenderer.dll'
    receipt={'version':'0.3.4','hindiSourcePins':hi['build']['generatedSourceHashes'],'hebrewBinding':{'before':before,'after':after},'binarySha256':sha(binary),'generatedSourceHashes':{str(p.relative_to(ROOT)):sha(p) for p in source.iterdir() if p.is_file()},'runtime':'pending'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.out.resolve())
