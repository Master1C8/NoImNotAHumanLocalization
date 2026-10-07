#!/usr/bin/env python3
"""Prepare an isolated Hindi dynamic font with stable glyph-ID PUA mapping.

Never changes the source game. Cloned atlas, material and font belong to this probe.
The original font is retained for HarfBuzz; TMP's clone omits shaping/positioning tables.
"""
import argparse,copy,io,json,subprocess,zipfile
from pathlib import Path
import UnityPy
from fontTools.ttLib import TTFont
from probe_assets import ROOT,EXPECTED_UNITY,digest,require
from fixture_preferences import FIXTURE
from install_locale_probe import GAME
from unity_types import CheckedTypeTreeGenerator,generated_tree
from build_locale_probe import clone,save_verified


def prepare(output):
    require(output.is_relative_to(ROOT/'outputs'),'Output outside canonical project')
    processes=subprocess.check_output(['ps','-axo','pid,command'],text=True)
    require(not any(str(FIXTURE) in line or 'NoImNotAHuman.exe' in line or 'wineserver' in line for line in processes.splitlines()),'Fixture must be stopped')
    expected=json.loads((ROOT/'outputs/native-locale-probe-v6/report.json').read_text())
    paths=['NoImNotAHuman_Data/sharedassets0.assets','NoImNotAHuman_Data/resources.assets']
    for name in paths:require(digest(GAME/name)==expected['artifacts'][name]['sha256'],'Unexpected fixture font assets: '+name)
    output.mkdir(parents=True,exist_ok=False)
    backups=output/'before';backups.mkdir()
    receipt={'completed':False,'files':[],'commitBoundary':'Per-file replace only; not a transaction. Keep game stopped on failure.'}
    def record():(output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    record()
    generator=CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed'))
    for name in paths:
        source=GAME/name;(backups/Path(name).name).write_bytes(source.read_bytes())
        env=UnityPy.load(str(source));env.typetree_generator=generator
        original={o.path_id:o.get_raw_data() for o in env.objects};generated={};allowed=set()
        if name.endswith('sharedassets0.assets'):
            original_font=env.file.objects[1165];font_tree=original_font.read_typetree();font_bytes=bytes(font_tree['m_FontData'])
            (output/'hi-source.ttf').write_bytes(font_bytes)
            font=TTFont(io.BytesIO(font_bytes));order=font.getGlyphOrder()
            require(len(order)<6400,'Font exceeds BMP private-use mapping')
            cmaps=[c for c in font['cmap'].tables if c.isUnicode() and c.format in (4,12)]
            require(not any(0xe001<=c<0xe000+len(order) for m in cmaps for c in m.cmap),'Source already uses reserved PUA')
            for cmap in cmaps:
                cmap.cmap.update({0xe000+i:n for i,n in enumerate(order) if i})
            for table in ['GSUB','GPOS','kern']:
                if table in font:del font[table]
            data=io.BytesIO();font.save(data);prepared=data.getvalue()
            restored=TTFont(io.BytesIO(prepared));cmap=restored.getBestCmap()
            require(all(cmap[0xe000+i]==n for i,n in enumerate(order) if i),'PUA read-back mismatch')
            font_tree['m_Name']='VN Probe Hindi Glyph Source';font_tree['m_FontData']=list(prepared)
            clone(original_font,900013,font_tree)
            base=env.file.objects[2614];tree,schema=generated_tree(base)
            tree['m_Name']='VN Probe Hindi Shaped Dynamic';tree['m_SourceFontFile']={'m_FileID':0,'m_PathID':900013}
            tree['m_FontFeatureTable']={k:[] for k in tree['m_FontFeatureTable']}
            tree['m_GlyphTable']=[];tree['m_CharacterTable']=[]
            material_obj=env.file.objects[tree['m_Material']['m_PathID']];material=material_obj.read_typetree()
            tex_obj=env.file.objects[tree['m_AtlasTextures'][0]['m_PathID']];tex=tex_obj.read_typetree()
            tex['m_Name']='VN Probe Hindi Atlas';clone(tex_obj,900012,tex)
            material['m_Name']='VN Probe Hindi Material'
            for _,value in material['m_SavedProperties']['m_TexEnvs']:
                if value['m_Texture']=={'m_FileID':0,'m_PathID':tex_obj.path_id}:value['m_Texture']['m_PathID']=900012
            clone(material_obj,900011,material)
            tree['m_Material']['m_PathID']=900011;tree['m_AtlasTextures'][0]['m_PathID']=900012
            # Empty lookup tables need the complete free atlas; original clone may contain prior glyphs.
            size=tree['m_AtlasWidth'];height=tree['m_AtlasHeight'];tree['m_UsedGlyphRects']=[]
            tree['m_FreeGlyphRects']=[{'m_X':0,'m_Y':0,'m_Width':size-1,'m_Height':height-1}]
            clone(base,900010,tree,schema);generated[900010]=(schema,tree)
            receipt['font']={'sourceSha256':digest(output/'hi-source.ttf'),'glyphCount':len(order),'mapping':'U+E000 + original glyph ID; .notdef rejected','preparedFontSha256':__import__('hashlib').sha256(prepared).hexdigest(),'originalFontRetained':True}
        roles=[2601] if name.endswith('sharedassets0.assets') else [1453,1454]
        for role in roles:
            obj=env.file.objects[role];tree,schema=generated_tree(obj)
            rows=[r for r in tree['<Fonts>k__BackingField']['_serializedList'] if r['Key']=='hi'];require(len(rows)==1,'Ambiguous Hindi role')
            require(rows[0]['Value']['m_PathID']==2614,'Hindi role changed')
            rows[0]['Value']['m_PathID']=900010;obj.save_typetree(tree,nodes=schema);allowed.add(role);generated[role]=(schema,tree)
        dest=output/Path(name).name;save_verified(env,dest,{'original':original,'allowed':allowed},generated)
        receipt['files'].append({'path':name,'beforeSha256':digest(source),'afterSha256':digest(dest)})
    record()
    for row in receipt['files']:
        target=GAME/row['path'];require(digest(target)==row['beforeSha256'],'Fixture changed before installation')
        temp=target.with_name(target.name+'.renderer-tmp');require(not temp.exists(),'Unexpected pending replacement')
        temp.write_bytes((output/target.name).read_bytes());temp.replace(target)
    receipt['completed']=True;record();print(json.dumps({'completed':True,'receipt':str(output/'receipt.json')}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a.output.resolve())
