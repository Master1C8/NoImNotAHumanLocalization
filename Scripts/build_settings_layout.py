#!/usr/bin/env python3
"""Enable bounded one-line fitting on localized volume labels, preserving text."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import UnityPy
from probe_assets import ROOT, DEFAULT_GAME, EXPECTED_UNITY, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree
from build_locale_probe import save_verified

LABELS={'level0':[2091,2170,2178],'level1':[3798,4048,4074,4129,4185,4267]}


def fit(tree):
    require(tree['m_fontSize']==36.0 and tree['m_enableAutoSizing']==0 and
            tree['m_fontSizeMin']==18.0 and tree['m_fontSizeMax']==72.0 and
            tree['m_TextWrappingMode']==1, 'Volume label differs from exact original state')
    result=copy.deepcopy(tree)
    result.update(m_enableAutoSizing=1,m_fontSizeMax=36.0,m_TextWrappingMode=0)
    return result


def build(archive,output,destination):
    require(archive.is_relative_to(ROOT/'dist') and output.is_relative_to(ROOT/'outputs') and
            destination.is_relative_to(ROOT/'dist') and not output.exists() and not destination.exists(),
            'Use a verified parent archive and new canonical outputs')
    identity=json.loads(archive.with_suffix('.zip.json').read_text())
    require(digest(archive)==identity['sha256'], 'Parent archive changed')
    output.mkdir();scope=json.loads((ROOT/'Documentation/static-text-scope-v2.json').read_text())['rows']
    with ZipFile(archive) as zipped:
        report=json.loads(zipped.read('report.json'))
        require(zipped.testzip() is None and len(zipped.namelist())==33 and
                report['locale']==identity['locale'] and report['translatedTextValues']==16538, 'Invalid parent package')
        for name,row in report['artifacts'].items():
            require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'Unsafe parent member')
            target=output/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(zipped.read(name))
            require(digest(target)==row['sha256'], 'Parent member changed')
    generator=CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed'))
    changes=[]
    for level,pids in LABELS.items():
        name='NoImNotAHuman_Data/'+level;path=output/name
        schema_source=UnityPy.load(str(DEFAULT_GAME/name));schema_source.typetree_generator=generator
        env=UnityPy.load(str(path));original={o.path_id:o.get_raw_data() for o in env.objects};generated={}
        for pid in pids:
            rows=[r for r in scope if r['stableId']==f'tmp:{level}:{pid}:m_text']
            require(len(rows)==1 and rows[0]['source'] in ['Music','Master','SFX'] and
                    any(x['name']=='SoundSettings' for x in rows[0]['sceneAncestry']) and
                    len(rows[0]['localizedStringBindings'])==1, 'Localized volume label ownership changed')
            _,schema=generated_tree(schema_source.file.objects[pid]);obj=env.file.objects[pid]
            before=obj.read_typetree(nodes=schema);after=fit(before)
            require(before['m_text']==after['m_text'], 'Authored label changed')
            obj.save_typetree(after,nodes=schema);generated[pid]=(schema,after)
        saved=save_verified(env,path,{'original':original,'allowed':set(pids)},generated)
        report['artifacts'][name]['sha256']=digest(path)
        changes.append({'path':name,'labels':pids,'saved':saved,'fields':{
            'm_enableAutoSizing':[0,1],'m_fontSizeMax':[72.0,36.0],'m_TextWrappingMode':[1,0]}})
    report['settingsLayoutRepair']={'parentArchive':str(archive.relative_to(ROOT)),
        'parentArchiveSha256':digest(archive),'recipeSha256':digest(Path(__file__)),
        'authoredTextChanged':False,'changes':changes,'runtime':'pending'}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with ZipFile(destination,'w',ZIP_DEFLATED) as zipped:
        for name in report['artifacts']:zipped.write(output/name,name)
        zipped.write(output/'report.json','report.json')
        zipped.writestr('README.txt','Verified localization with bounded one-line fitting for volume labels.\n')
    with ZipFile(destination) as zipped:require(zipped.testzip() is None and len(zipped.namelist())==33,'Final archive invalid')
    destination.with_suffix('.zip.json').write_text(json.dumps({'locale':report['locale'],'sha256':digest(destination),
        'parentArchiveSha256':digest(archive),'status':'Settings text-fit repair; runtime pending'},indent=2)+'\n')
    print(str(destination),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['archive','output','destination']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();build(a.archive.resolve(),a.output.resolve(),a.destination.resolve())
