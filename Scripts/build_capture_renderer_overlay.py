#!/usr/bin/env python3
"""Bind the verified fixture renderer to exact locale packages without changing text."""
import argparse
import copy
import json
import hashlib
import subprocess
from pathlib import Path
from zipfile import ZipFile
import UnityPy
from probe_assets import ROOT, DEFAULT_GAME, EXPECTED_UNITY, digest, require
from install_th_text_draft import GAME
from unity_types import CheckedTypeTreeGenerator, generated_tree
from build_locale_probe import save_verified


def build(archive, output):
    require(output.is_relative_to(ROOT/'outputs') and not output.exists(), 'Use a new canonical output')
    parent=json.loads(archive.with_suffix('.zip.json').read_text())
    require(parent['locale']=='hi' and digest(archive)==parent['sha256'], 'Hindi archive changed')
    font_root=ROOT/'outputs/renderer-font-v3'
    fonts=json.loads((font_root/'receipt.json').read_text())
    module_root=ROOT/'outputs/renderer-module-dialogue-v3'
    module=json.loads((module_root/'receipt.json').read_text())
    require(fonts['completed'] and module['completed'], 'Renderer checkpoint incomplete')
    source_commit='e72328e20a9b35c36d228ed20054723531373932'
    source_bytes={p:subprocess.check_output(['git','show',source_commit+':'+p],cwd=ROOT) for p in module['sourceHashes']}
    require(all(hashlib.sha256(source_bytes[p]).hexdigest()==h for p,h in module['sourceHashes'].items()),
            'Verified prebuilt renderer source differs from committed checkpoint')
    plugin=GAME/'BepInEx/plugins/NoHuman.TextRenderer'
    require({p.name:digest(p) for p in plugin.iterdir()}==module['files'], 'Installed renderer changed')
    descriptor={'version':'0.3.0','moduleReceipt':str((module_root/'receipt.json').relative_to(ROOT)),
                'moduleReceiptSha256':digest(module_root/'receipt.json'),
                'pluginFiles':{'BepInEx/plugins/NoHuman.TextRenderer/'+n:h for n,h in module['files'].items()},
                'loaderSha256':digest(GAME/'winhttp.dll'),'sourceHashes':module['sourceHashes'],
                'locales':{'fa':{'assets':{}},'he':{'assets':{}},'hi':{'baseArchiveSha256':digest(archive),'assets':{}}}}
    output.mkdir()
    descriptor['sourceCommit']=source_commit;descriptor['frozenSourceHashes']={}
    for p,data in source_bytes.items():
        frozen=output/'renderer-source'/p;frozen.parent.mkdir(parents=True,exist_ok=True);frozen.write_bytes(data)
        descriptor['frozenSourceHashes'][str(frozen.relative_to(ROOT))]=digest(frozen)
    generator=CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed'))
    checks=[]
    with ZipFile(archive) as zipped:
        report=json.loads(zipped.read('report.json'))
        require(zipped.testzip() is None and len(report['artifacts'])==31, 'Parent archive invalid')
        for name, artifact in report['artifacts'].items():
            require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'Unsafe parent member')
            target=output/'before'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(zipped.read(name))
            require(digest(target)==artifact['sha256'], 'Parent member changed')
        for row in fonts['files']:
            name=row['path'];prepared_path=font_root/Path(name).name
            require(digest(prepared_path)==row['afterSha256'], 'Prepared Hindi font changed')
            before=output/'before'/name
            require(digest(before)==report['artifacts'][name]['sha256'], 'Parent asset differs')
            env=UnityPy.load(str(before));env.typetree_generator=generator
            schema_source=UnityPy.load(str(DEFAULT_GAME/name));schema_source.typetree_generator=generator
            prepared=UnityPy.load(str(prepared_path));prepared.typetree_generator=generator
            raw={o.path_id:o.get_raw_data() for o in env.objects};generated={}
            added=[]
            if name.endswith('sharedassets0.assets'):
                for pid in [900010,900011,900012,900013]:
                    require(pid not in env.file.objects, 'Ambiguous existing Hindi clone')
                    source=prepared.file.objects[pid];new=copy.copy(source)
                    target_type=env.file.types[source.type_id]
                    require(target_type.class_id==source.serialized_type.class_id and
                            target_type.script_id==source.serialized_type.script_id, 'Clone serialized type differs')
                    new.assets_file=env.file;new.serialized_type=target_type;new.set_raw_data(source.get_raw_data())
                    env.file.objects[pid]=new;added.append(pid)
            roles=[2601] if name.endswith('sharedassets0.assets') else [1453,1454]
            for pid in roles:
                obj=env.file.objects[pid];_,schema=generated_tree(schema_source.file.objects[pid])
                tree=obj.read_typetree(nodes=schema)
                rows=[r for r in tree['<Fonts>k__BackingField']['_serializedList'] if r['Key']=='hi']
                require(len(rows)==1 and rows[0]['Value']['m_PathID']==2614, 'Hindi original role changed')
                rows[0]['Value']['m_PathID']=900010;obj.save_typetree(tree,nodes=schema);generated[pid]=(schema,tree)
            target=output/name
            saved=save_verified(env,target,{'original':raw,'allowed':set(roles)},generated)
            descriptor['locales']['hi']['assets'][name]={'file':str(target.relative_to(ROOT)),'sha256':digest(target)}
            checks.append({'path':name,'parentSha256':digest(before),'preparedFontSha256':digest(prepared_path),
                           'addedObjects':added,'changedRoles':roles,'allOtherOriginalObjectsUnchanged':True,'saved':saved})
    descriptor['hindiVerification']={'archiveSha256':digest(archive),'checks':checks,
                                    'authoredTextChanged':False,'recipeSha256':digest(Path(__file__))}
    (output/'renderer.json').write_text(json.dumps(descriptor,indent=2)+'\n')
    print(str(output/'renderer.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.archive.resolve(),a.output.resolve())
