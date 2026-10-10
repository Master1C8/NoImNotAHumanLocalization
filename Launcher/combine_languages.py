#!/usr/bin/env python3
"""Combine frozen accepted text into the verified native 32-locale catalog.

Never translate or edit the owner's live translation/renderer checkout.
"""
import argparse, copy, hashlib, json, shutil, sys, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
import UnityPy
from probe_assets import DEFAULT_GAME, EXPECTED_UNITY, digest, require
from build_locale_probe import LANGUAGES, save_verified
from unity_types import CheckedTypeTreeGenerator, generated_tree
from addressables_catalog import Catalog, update_bundle

def build(out):
    require(out.is_relative_to(ROOT/'outputs') and not out.exists(),'Use a new canonical output directory')
    base=ROOT/'outputs/native-locale-probe-v6'
    baseline=json.loads((base/'report.json').read_text())
    require(set(baseline['languages'])==set(LANGUAGES),'Native catalog roster differs')
    require(all(digest(base/n)==v['sha256'] for n,v in baseline['artifacts'].items()),'Native base changed')
    plan=json.loads((ROOT/'outputs/six-scenes-all-locales-v8/batch.json').read_text())['plan']
    require({r['locale'] for r in plan}==set(LANGUAGES),'Frozen profile roster differs')
    require(all(digest(DEFAULT_GAME/n)==h for n,h in baseline['inputs'].items()),'Original game changed')
    fonts=ROOT/'outputs/renderer-font-v3';font_receipt=json.loads((fonts/'receipt.json').read_text())
    require(font_receipt['completed'],'Full native font checkpoint incomplete')
    for r in font_receipt['files']:require(digest(fonts/Path(r['path']).name)==r['afterSha256'],'Full native font checkpoint changed')
    generator=CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed'))
    out.mkdir(parents=True)
    for n in baseline['artifacts']:
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/n,p)
    for r in font_receipt['files']:shutil.copyfile(fonts/Path(r['path']).name,out/r['path'])
    aa='NoImNotAHuman_Data/StreamingAssets/aa/StandaloneWindows64/'
    string_name=aa+'localization-string-tables-russian(ru)_assets_all.bundle'
    asset_name=aa+'localization-asset-tables-russian(ru)_assets_all.bundle'
    string_env=UnityPy.load(str(out/string_name));asset_env=UnityPy.load(str(out/asset_name))
    string_original={o.path_id:o.get_raw_data() for o in string_env.objects};asset_original={o.path_id:o.get_raw_data() for o in asset_env.objects}
    string_objs={o.peek_name():o for o in string_env.objects if o.type.name=='MonoBehaviour'}
    asset_objs={o.peek_name():o for o in asset_env.objects if o.type.name=='MonoBehaviour'}
    static_rows=json.loads((ROOT/'Documentation/static-text-scope-v2.json').read_text())['rows']
    # Only the exact 178 unbound targets in the frozen delivery are transformed.
    reference=next(r for r in plan if r['locale']=='id')
    with zipfile.ZipFile(ROOT/reference['archive']) as z:reference_report=json.loads(z.read('report.json'))
    text_report=ROOT/reference_report['textReportPath']
    require(digest(text_report)==reference_report['textReportSha256'],'Frozen static scope report changed')
    static_file=ROOT/'Translations/id/static-text-draft.json'
    pinned=json.loads(text_report.read_text())['authoredFiles']
    require(any(r['path']==str(static_file.relative_to(ROOT)) and r['sha256']==digest(static_file) for r in pinned),'Static target inventory changed')
    frozen_static={r['stableId'] for r in json.loads(static_file.read_text())['entries']}
    static_ids={r['stableId'] for r in static_rows if r['stableId'] in frozen_static}
    require(len(static_ids)==178,'Frozen static target inventory differs')
    entries={};expected_tables={};provenance=[]
    for row in plan:
        loc=row['locale'];archive=ROOT/row['archive'];require(digest(archive)==row['archiveSha256'],'Frozen archive changed')
        with zipfile.ZipFile(archive) as z:
            report=json.loads(z.read('report.json'))
            require(report['locale']==loc and len(report['artifacts'])==31,'Frozen archive scope differs')
            for name,objects in [(string_name,string_objs),(asset_name,asset_objs)]:
                raw=z.read(name);require(hashlib.sha256(raw).hexdigest()==report['artifacts'][name]['sha256'],'Frozen bundle changed')
                env=UnityPy.load(raw)
                selected=[o for o in env.objects if o.type.name=='MonoBehaviour' and o.peek_name().endswith('_'+loc)]
                require(len(selected)==(9 if name==string_name else 1),'Frozen localized table count differs')
                for obj in selected:
                    title=obj.peek_name();target=objects[title];require(target.path_id==obj.path_id,'Stable table identity differs')
                    tree=obj.read_typetree()
                    if title=='UI_'+loc:
                        ids=set(baseline['languageKeyIds'].values())
                        tree['m_TableData']=[v for v in tree['m_TableData'] if v['m_Id'] not in ids]
                        tree['m_TableData'].extend({'m_Id':baseline['languageKeyIds'][c],'m_Localized':label,'m_Metadata':{'m_Items':[]}} for c,(_,label) in LANGUAGES.items())
                        target.save_typetree(tree)
                    else:target.set_raw_data(obj.get_raw_data())
                    expected_tables[title]=tree
            by_file={}
            for stable in static_ids:
                _,name,pid,field=stable.split(':');by_file.setdefault(name,[]).append((stable,int(pid)))
            for name,ids in by_file.items():
                relative='NoImNotAHuman_Data/'+name
                raw=z.read(relative);require(hashlib.sha256(raw).hexdigest()==report['artifacts'][relative]['sha256'],'Frozen scene changed')
                env=UnityPy.load(raw);source=UnityPy.load(str(DEFAULT_GAME/relative));source.typetree_generator=generator
                for stable,pid in ids:
                    original,schema=generated_tree(source.file.objects[pid]);tree=env.file.objects[pid].read_typetree(nodes=schema)
                    entry=entries.setdefault(stable,{'fallback':original['m_text'],'values':{}});entry['values'][loc]=tree['m_text']
                    if 'originalText' in tree:require(tree['originalText']==tree['m_text'],'Frozen RTL source and display disagree')
            provenance.append({'locale':loc,'archiveSha256':row['archiveSha256']})
        print('Combined exact tables/static values:',loc,flush=True)
    checks={};catalog=(out/'NoImNotAHuman_Data/StreamingAssets/aa/catalog.bin').read_bytes()
    for name,env,original in [(string_name,string_env,string_original),(asset_name,asset_env,asset_original)]:
        allowed={o.path_id for o in env.objects if o.type.name=='MonoBehaviour' and o.peek_name() in expected_tables}
        checks[name]=save_verified(env,out/name,{'original':original,'allowed':allowed})
        catalog,_=update_bundle(catalog,base/name,out/name)
        reopened=UnityPy.load(str(out/name))
        for obj in reopened.objects:
            if obj.type.name=='MonoBehaviour' and obj.peek_name() in expected_tables:require(obj.read_typetree()==expected_tables[obj.peek_name()],'Merged table did not round-trip')
    (out/'NoImNotAHuman_Data/StreamingAssets/aa/catalog.bin').write_bytes(catalog)
    require(len(Catalog(catalog).keys()['Locale']['locations'])==32,'Expected 18 original and 14 added locales')
    by_file={}
    for stable in static_ids:
        _,name,pid,field=stable.split(':');by_file.setdefault(name,[]).append((stable,int(pid)))
    for name,ids in sorted(by_file.items()):
        relative='NoImNotAHuman_Data/'+name
        source=UnityPy.load(str(DEFAULT_GAME/relative));source.typetree_generator=generator
        env=UnityPy.load(str(out/relative if (out/relative).exists() else DEFAULT_GAME/relative))
        original={o.path_id:o.get_raw_data() for o in env.objects};generated={};allowed=set()
        for stable,pid in ids:
            _,schema=generated_tree(source.file.objects[pid]);obj=env.file.objects[pid];tree=obj.read_typetree(nodes=schema)
            marker='VNREVIVAL_STATIC['+stable+']';tree['m_text']=marker
            if 'originalText' in tree:tree['originalText']=marker
            obj.save_typetree(tree,nodes=schema);generated[pid]=(schema,tree);allowed.add(pid)
        if name=='level0':
            for pid in [1958,2087,2108,2155,2181]:
                _,schema=generated_tree(source.file.objects[pid]);obj=env.file.objects[pid];tree=obj.read_typetree(nodes=schema)
                require(tree['m_fontSizeMin']==24.0 and tree['m_margin']['x']==20.0,'Menu source layout differs')
                tree['m_fontSizeMin']=16.0;tree['m_margin']['x']=tree['m_margin']['z']=8.0
                obj.save_typetree(tree,nodes=schema);generated[pid]=(schema,tree);allowed.add(pid)
        checks[relative]=save_verified(env,out/relative,{'original':original,'allowed':allowed},generated)
    require(len(entries)==178 and all(set(r['values'])==set(LANGUAGES) for r in entries.values()),'Static locale matrix incomplete')
    (out/'static-text.json').write_text(json.dumps(entries,ensure_ascii=False,separators=(',',':'))+'\n')
    # Verify every untouched original object and every merged table above; bind
    # all generated inputs and output bytes for packaging and runtime review.
    artifacts={str(p.relative_to(out)):{'sha256':digest(p)} for p in sorted((out/'NoImNotAHuman_Data').rglob('*')) if p.is_file()}
    require(len(artifacts)==31,'Combined game artifact scope differs')
    report={'schemaVersion':1,'mode':'all-native','locales':list(LANGUAGES),'nativeLocales':32,'artifacts':artifacts,'staticEntries':178,'staticValues':178*14,'tableObjects':len(expected_tables),'reviewedProfiles':provenance,'nativeBaseReportSha256':digest(base/'report.json'),'fullFontReceiptSha256':digest(fonts/'receipt.json'),'staticTextSha256':digest(out/'static-text.json'),'serializedChecks':checks,'authoredTranslationChanges':False,'runtime':'pending'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'nativeLocales':32,'artifacts':31,'staticValues':2492,'runtime':'pending'}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.out.resolve())
