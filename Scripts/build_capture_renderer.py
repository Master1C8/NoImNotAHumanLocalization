#!/usr/bin/env python3
"""Rebuild the pinned renderer with RTL routing restricted to dropdown owners.

The owner's active RuntimePlugin checkout is never read as executable input or
changed. Generated sources, compiler outputs and exact substitutions remain in
one immutable canonical output directory.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
from probe_assets import ROOT,digest,require


def build(descriptor,output,bind_hindi=False,bind_hebrew=False):
    require(output.is_relative_to(ROOT/'outputs') and not output.exists(), 'Use a new canonical build output')
    require(not (bind_hindi and bind_hebrew), 'Select one script-specific renderer')
    data=json.loads(descriptor.read_text());output.mkdir();source=output/'source';source.mkdir()
    snapshots=data['frozenSourceHashes']
    for name,expected in snapshots.items():
        path=ROOT/name;require(digest(path)==expected,'Frozen renderer source changed')
        (source/path.name).write_bytes(path.read_bytes())
    plugin=source/'Plugin.cs';text=plugin.read_text()
    changes=[('[BepInPlugin("fun.vnrevival.nohuman.renderer", "No Human Text Renderer Probe", "0.3.0")]',
              '[BepInPlugin("fun.vnrevival.nohuman.renderer", "No Human Text Renderer Probe", "0.3.1")]'),
             ('RENDERER_READY v0.3.0:', 'RENDERER_READY v0.3.1:'),
             ('if(Plugin.RtlSetterDepth==0 && __0.Any(',
              'if(Plugin.RtlSetterDepth==0 && __instance.GetComponentInParent<TMP_Dropdown>()!=null && __0.Any(')]
    for before,after in changes:
        require(text.count(before)==1 and after not in text,'Ambiguous renderer old/new source')
        text=text.replace(before,after)
    version='0.3.1'
    if bind_hindi:
        version='0.3.2'
        before='''            if(__instance.font?.name!="VN Probe Hindi Shaped Dynamic" || !__instance.richText) {'''
        after='''            if(__instance.font?.name!="VN Probe Hindi Shaped Dynamic") {
                // Some settings labels bypass the serialized locale font roles.
                // Bind the same verified loaded asset before processing Hindi input.
                var fonts=UnityEngine.Resources.FindObjectsOfTypeAll<TMP_FontAsset>()
                    .Where(f=>f.name=="VN Probe Hindi Shaped Dynamic").ToArray();
                if(fonts.Length!=1)throw new InvalidDataException("Expected one verified loaded Hindi font");
                __instance.font=fonts[0];
                Plugin.Report("HI_BOUND",__instance,original,original);
            }
            __instance.richText=true;
            if(__instance.font?.name!="VN Probe Hindi Shaped Dynamic" || !__instance.richText) {'''
        require(text.count(before)==1 and after not in text,'Ambiguous Hindi binding source')
        text=text.replace(before,after);changes.append((before,after))
        require(text.count('"0.3.1"')==1 and text.count('RENDERER_READY v0.3.1:')==1,'Renderer version ambiguous')
        text=text.replace('"0.3.1"','"0.3.2"').replace('RENDERER_READY v0.3.1:','RENDERER_READY v0.3.2:')
        changes.extend([('"0.3.1"','"0.3.2"'),('RENDERER_READY v0.3.1:','RENDERER_READY v0.3.2:')])
    if bind_hebrew:
        version='0.3.3'
        before='''        if(!HarfBuzz.ContainsHindi(original))return;'''
        after='''        if(!string.IsNullOrEmpty(original) && original.Any(c=>c>='\\u0590' && c<='\\u05ff')) {
            try {
                if(__instance.font?.name!="VN Probe LiberationSans Dynamic") {
                    var fonts=UnityEngine.Resources.FindObjectsOfTypeAll<TMP_FontAsset>()
                        .Where(f=>f.name=="VN Probe LiberationSans Dynamic").ToArray();
                    if(fonts.Length!=1)throw new InvalidDataException("Expected one verified loaded Hebrew font");
                    __instance.font=fonts[0];
                    Plugin.Report("HE_BOUND",__instance,original,original);
                }
                // TMP applies the imported pair advances incorrectly in this game's
                // RTL path. Keep glyph metrics and other OpenType features intact.
                bool removed=__instance.fontFeatures.Remove(UnityEngine.TextCore.OTL_FeatureTag.kern);
                Plugin.Report("HE_KERN",__instance,original,"removed="+removed);
            } catch(Exception ex) {Plugin.Instance.Log.LogError("RENDERER_FAILED: "+ex);}
        }
        if(!HarfBuzz.ContainsHindi(original))return;'''
        require(text.count(before)==1 and after not in text,'Ambiguous Hebrew binding source')
        text=text.replace(before,after);changes.append((before,after))
        text=text.replace('"0.3.1"','"0.3.3"').replace('RENDERER_READY v0.3.1:','RENDERER_READY v0.3.3:')
        changes.extend([('"0.3.1"','"0.3.3"'),('RENDERER_READY v0.3.1:','RENDERER_READY v0.3.3:')])
    plugin.write_text(text)
    project=source/'NoHuman.TextRenderer.csproj';text=project.read_text()
    before='<OutputPath>../outputs/renderer-build/bin/</OutputPath>'
    require(text.count(before)==1,'Compiler output path changed')
    text=text.replace(before,'<OutputPath>'+str(output/'bin')+'/</OutputPath>')
    if bind_hebrew:
        text=text.replace('  </ItemGroup>', '    <Reference Include="$(FixtureGame)/BepInEx/interop/UnityEngine.TextCoreFontEngineModule.dll" Private="false" />\n  </ItemGroup>')
    project.write_text(text)
    sdk=Path('/private/tmp/no-human-dotnet-sdk/dotnet');require(sdk.is_file(),'Verified local SDK missing')
    env=dict(os.environ,DOTNET_CLI_HOME='/private/tmp/no-human-dotnet-home',DOTNET_CLI_TELEMETRY_OPTOUT='1',
             DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
    from install_th_text_draft import GAME
    result=subprocess.run([str(sdk),'build',str(project),'-p:FixtureGame='+str(GAME),'--nologo'],
                          cwd=ROOT,env=env,text=True,capture_output=True,timeout=180)
    (output/'build.log').write_text(result.stdout+result.stderr)
    require(result.returncode==0,'Renderer build failed; inspect bounded build.log')
    binary=output/'bin/net6.0/NoHuman.TextRenderer.dll';require(binary.is_file(),'Renderer binary missing')
    if bind_hindi:data['locales']={'hi':data['locales']['hi']}
    if bind_hebrew:data['locales']={'he':data['locales']['he']}
    data.update(version=version,parentRendererDescriptor=str(descriptor.relative_to(ROOT)),
                parentRendererDescriptorSha256=digest(descriptor),
                pluginOverrides={'BepInEx/plugins/NoHuman.TextRenderer/NoHuman.TextRenderer.dll':
                                 {'file':str(binary.relative_to(ROOT)),'sha256':digest(binary)}},
                build={'recipeSha256':digest(Path(__file__)),'changes':changes,
                       'generatedSourceHashes':{str(p.relative_to(ROOT)):digest(p) for p in source.iterdir() if p.is_file()},
                       'buildLogSha256':digest(output/'build.log')})
    (output/'renderer.json').write_text(json.dumps(data,indent=2)+'\n')
    print(str(output/'renderer.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--descriptor',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--bind-hindi',action='store_true')
    p.add_argument('--bind-hebrew',action='store_true')
    a=p.parse_args();build(a.descriptor.resolve(),a.output.resolve(),a.bind_hindi,a.bind_hebrew)
