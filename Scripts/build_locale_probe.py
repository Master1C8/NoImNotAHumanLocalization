#!/usr/bin/env python3
"""Build isolated locale/font bindings, retaining Russian carrier text.

Not a translation release. Only Common_NewGame is a synthetic script sample.
All original objects are compared after serialization; source files stay read-only.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import UnityPy

from addressables_catalog import Catalog, CatalogExtension, update_bundle
from probe_assets import ROOT, DEFAULT_GAME, EXPECTED_UNITY, EXPECTED_BUILD_GUID, SAMPLES, UI_ID, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree, serialized_bytes, current_tree

LANGUAGES = {
    'th': ('Thai', 'ไทย'), 'id': ('Indonesian', 'Bahasa Indonesia'),
    'cs': ('Czech', 'Čeština'), 'hu': ('Hungarian', 'Magyar'),
    'nl': ('Dutch', 'Nederlands'), 'fa': ('Persian', 'فارسی'),
    'ro': ('Romanian', 'Română'), 'hi': ('Hindi', 'हिन्दी'),
    'fil': ('Filipino', 'Filipino'), 'el': ('Greek', 'Ελληνικά'),
    'bg': ('Bulgarian', 'Български'), 'sr': ('Serbian', 'Српски'),
    'sw': ('Swahili', 'Kiswahili'), 'he': ('Hebrew', 'עברית'),
}


def clone(obj, path_id, tree, schema=None):
    require(path_id not in obj.assets_file.objects, 'Duplicate new object identity')
    new = copy.copy(obj)
    new.path_id = path_id
    new.save_typetree(tree, nodes=schema)
    obj.assets_file.objects[path_id] = new
    return new


def identity(name):
    return int.from_bytes(hashlib.sha256(('vnrevival.probe.v1/'+name).encode()).digest()[:8], 'little') & 0x7FFFFFFFFFFFFFFF


def extend_bundle(env, obj, tree, name):
    new_id = identity(name)
    clone(obj, new_id, tree)
    bundle = next(o for o in env.objects if o.type.name == 'AssetBundle')
    bundle_tree = current_tree(bundle)
    originals = [(path, row) for path, row in bundle_tree['m_Container'] if row['asset']['m_PathID'] == obj.path_id]
    require(len(originals) == 1, 'Missing/ambiguous source bundle container')
    path, row = originals[0]
    new_path = path[:path.rfind('/')+1] + name + '.asset'
    require(not any(p == new_path for p, _ in bundle_tree['m_Container']), 'Duplicate new container path')
    preload = copy.deepcopy(bundle_tree['m_PreloadTable'][row['preloadIndex']:row['preloadIndex']+row['preloadSize']])
    require(sum(p == {'m_FileID': 0, 'm_PathID': obj.path_id} for p in preload) == 1, 'Unexpected source preload')
    for p in preload:
        if p == {'m_FileID': 0, 'm_PathID': obj.path_id}:
            p['m_PathID'] = new_id
    new_row = copy.deepcopy(row)
    new_row['asset']['m_PathID'] = new_id
    new_row['preloadIndex'] = len(bundle_tree['m_PreloadTable'])
    bundle_tree['m_PreloadTable'].extend(preload)
    bundle_tree['m_Container'].append((new_path, new_row))
    bundle_tree['m_Container'].sort(key=lambda item: item[0])
    bundle.save_typetree(bundle_tree)
    return new_path


def save_verified(env, path, expected_changes, generated=None):
    generated = generated or {}
    expected_raw = {o.path_id: serialized_bytes(o) for o in env.objects}
    before = expected_changes['original']
    allowed = expected_changes['allowed']
    require(all(expected_raw[k] == v for k, v in before.items() if k not in allowed), 'Unapproved original object changed')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(env.file.save(packer='lz4') if env.file.__class__.__name__ == 'BundleFile' else env.file.save())
    reopened = UnityPy.load(str(path))
    actual = {o.path_id: o.get_raw_data() for o in reopened.objects}
    require(actual == expected_raw, 'Saved object bytes differ from expected mutation')
    for path_id, (schema, tree) in generated.items():
        obj = reopened.file.objects[path_id]
        require(obj.read_typetree(nodes=schema) == tree, 'Generated fields did not round-trip')
    return {'sha256': digest(path), 'originalObjects': len(before), 'newObjects': len(actual)-len(before),
            'unchangedOriginalObjects': len(before)-len(allowed), 'changedOriginalObjects': sorted(allowed),
            'allSavedObjectBytesVerified': True}


def run(game, output, codes=None):
    codes = list(LANGUAGES) if codes is None else codes
    require(codes and len(codes) == len(set(codes)) and
            all(code in LANGUAGES for code in codes), 'Invalid selected locale set')
    active = {code: LANGUAGES[code] for code in codes}
    require(UnityPy.__version__ == '1.25.4', 'Pinned UnityPy required')
    data = game/'NoImNotAHuman_Data'
    require('build-guid='+EXPECTED_BUILD_GUID in (data/'boot.config').read_text().splitlines(), 'Source build changed')
    aa = data/'StreamingAssets/aa'
    source_bundles = aa/'StandaloneWindows64'
    inputs, artifacts = {}, {}
    output.mkdir(parents=True, exist_ok=False)
    catalog_bytes = (aa/'catalog.bin').read_bytes()
    extension = CatalogExtension(catalog_bytes)
    ui_ids = {}
    shared_path = source_bundles/'localization-assets-shared_assets_all.bundle'
    shared = UnityPy.load(str(shared_path))
    before = {o.path_id: o.get_raw_data() for o in shared.objects}
    ui = next(o for o in shared.objects if o.type.name == 'MonoBehaviour' and o.peek_name() == 'UI Shared Data')
    ui_tree = ui.read_typetree()
    used_ids = {r['m_Id'] for r in ui_tree['m_Entries']}
    used_keys = {r['m_Key'] for r in ui_tree['m_Entries']}
    for code in active:
        key = 'language_'+code
        require(key not in used_keys, 'Target language key already present')
        new_id = identity('ui-key/'+key)
        require(new_id not in used_ids, 'New shared key ID collision')
        ui_ids[code] = new_id
        ui_tree['m_Entries'].append({'m_Id': new_id, 'm_Key': key, 'm_Metadata': {'m_Items': []}})
    ui.save_typetree(ui_tree)

    def save_bundle(source, env, original, allowed):
        nonlocal catalog_bytes
        inputs[str(source.relative_to(game))] = digest(source)
        dest = output/'NoImNotAHuman_Data/StreamingAssets/aa/StandaloneWindows64'/source.name
        artifacts[str(dest.relative_to(output))] = save_verified(env, dest, {'original': original, 'allowed': allowed})
        catalog_bytes, integrity = update_bundle(catalog_bytes, source, dest)
        artifacts[str(dest.relative_to(output))]['catalogIntegrity'] = integrity

    save_bundle(shared_path, shared, before, {ui.path_id})
    locale_path = source_bundles/'localization-locales_assets_all.bundle'
    locales = UnityPy.load(str(locale_path))
    before = {o.path_id: o.get_raw_data() for o in locales.objects}
    russian = next(o for o in locales.objects if o.type.name == 'MonoBehaviour' and o.peek_name() == 'Russian (ru)')
    for index, (code, (english, _)) in enumerate(active.items()):
        name = f'{english} ({code})'
        tree = russian.read_typetree()
        tree.update(m_Name=name, m_LocaleName=name, m_SortOrder=100+index)
        tree['m_Identifier']['m_Code'] = code
        path = extend_bundle(locales, russian, tree, name)
        extension.clone_asset('Russian (ru)', name, path)
    save_bundle(locale_path, locales, before, {o.path_id for o in locales.objects if o.type.name == 'AssetBundle'})

    # Native language endonyms exist in every official UI table. Preserve existing strings.
    for source in sorted(source_bundles.glob('localization-string-tables-*_assets_all.bundle')):
        env = UnityPy.load(str(source))
        original = {o.path_id: o.get_raw_data() for o in env.objects}
        originals = list(env.objects)
        allowed = set()
        ui_obj = next(o for o in originals if o.type.name == 'MonoBehaviour' and o.peek_name().startswith('UI_'))
        tree = ui_obj.read_typetree()
        require(not set(ui_ids.values()).intersection(r['m_Id'] for r in tree['m_TableData']), 'Existing table ID collision')
        tree['m_TableData'].extend({'m_Id': ui_ids[c], 'm_Localized': label, 'm_Metadata': {'m_Items': []}}
                                  for c, (_, label) in active.items())
        ui_obj.save_typetree(tree)
        allowed.add(ui_obj.path_id)
        if tree['m_LocaleId']['m_Code'] == 'ru':
            for obj in originals:
                if obj.type.name != 'MonoBehaviour':
                    continue
                source_tree = current_tree(obj)
                require(source_tree['m_LocaleId']['m_Code'] == 'ru', 'Unexpected Russian bundle contents')
                source_name = source_tree['m_Name']
                for code in active:
                    new_tree = copy.deepcopy(source_tree)
                    name = source_name[:-2]+code
                    new_tree['m_Name'] = name
                    new_tree['m_LocaleId']['m_Code'] = code
                    if source_name == 'UI_ru':
                        next(r for r in new_tree['m_TableData'] if r['m_Id'] == UI_ID)['m_Localized'] = SAMPLES[code]
                    path = extend_bundle(env, obj, new_tree, name)
                    extension.clone_asset(source_name, name, path, code)
            allowed.update(o.path_id for o in originals if o.type.name == 'AssetBundle')
        save_bundle(source, env, original, allowed)
    # Keep Russian image references for technical progression; no texture localization claim.
    asset_source = source_bundles/'localization-asset-tables-russian(ru)_assets_all.bundle'
    env = UnityPy.load(str(asset_source))
    original = {o.path_id: o.get_raw_data() for o in env.objects}
    obj = next(o for o in env.objects if o.type.name == 'MonoBehaviour')
    for code in active:
        tree = obj.read_typetree()
        name = 'Characters_'+code
        tree['m_Name'] = name
        tree['m_LocaleId']['m_Code'] = code
        path = extend_bundle(env, obj, tree, name)
        extension.clone_asset('Characters_ru', name, path, code)
    save_bundle(asset_source, env, original, {o.path_id for o in env.objects if o.type.name == 'AssetBundle'})

    # Replace only bundle-integrity fields in the extended catalog's original storage.
    extension.data[:len(catalog_bytes)] = catalog_bytes
    final_catalog = extension.finish()
    dest = output/'NoImNotAHuman_Data/StreamingAssets/aa/catalog.bin'
    dest.write_bytes(final_catalog)
    inputs[str((aa/'catalog.bin').relative_to(game))] = digest(aa/'catalog.bin')
    artifacts[str(dest.relative_to(output))] = {'sha256': digest(dest), 'localeLocations': len(Catalog(final_catalog).keys()['Locale']['locations']),
                                             'catalogBundleLocationsCompared': len(Catalog(final_catalog).bundles())}

    generator = CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(game/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed'))
    for filename, roles in [('sharedassets0.assets', [2601]), ('resources.assets', [1453, 1454])]:
        source = data/filename
        inputs[str(source.relative_to(game))] = digest(source)
        env = UnityPy.load(str(source))
        original = {o.path_id: o.get_raw_data() for o in env.objects}
        env.typetree_generator = generator
        allowed, generated = set(), {}
        if filename == 'sharedassets0.assets' and 'he' in active:
            # A separate dynamic Hebrew font uses the game's embedded Liberation Sans.
            # Clone its atlas/material too; never mutate another font's shared atlas.
            base = env.file.objects[2614]
            font_tree, schema = generated_tree(base)
            liberation, _ = generated_tree(env.file.objects[2604])
            font_tree['m_Name'] = 'VN Probe LiberationSans Dynamic'
            font_tree['m_FaceInfo'] = liberation['m_FaceInfo']
            font_tree['m_SourceFontFile'] = {'m_FileID': 0, 'm_PathID': 1172}
            font_tree['m_SourceFontFileGUID'] = liberation['m_SourceFontFileGUID']
            font_tree['m_CreationSettings']['sourceFontFileGUID'] = liberation['m_SourceFontFileGUID']
            font_tree['m_CreationSettings']['pointSize'] = 86
            font_tree['m_FontFeatureTable'] = {key: [] for key in font_tree['m_FontFeatureTable']}
            material_obj = env.file.objects[font_tree['m_Material']['m_PathID']]
            material = material_obj.read_typetree()
            texture_obj = env.file.objects[font_tree['m_AtlasTextures'][0]['m_PathID']]
            texture = texture_obj.read_typetree()
            texture['m_Name'] = 'VN Probe Hebrew Atlas'
            clone(texture_obj, 900002, texture)
            material['m_Name'] = 'VN Probe Hebrew Material'
            for _, value in material['m_SavedProperties']['m_TexEnvs']:
                if value['m_Texture'] == {'m_FileID': 0, 'm_PathID': texture_obj.path_id}:
                    value['m_Texture']['m_PathID'] = 900002
            clone(material_obj, 900001, material)
            font_tree['m_Material']['m_PathID'] = 900001
            font_tree['m_AtlasTextures'][0]['m_PathID'] = 900002
            clone(base, 900000, font_tree, schema)
            generated[900000] = (schema, font_tree)
        for path_id in roles:
            obj = env.file.objects[path_id]
            tree, schema = generated_tree(obj)
            rows = tree['<Fonts>k__BackingField']['_serializedList']
            require(not set(active).intersection(row['Key'] for row in rows), 'Target font mapping already exists')
            for code in active:
                target = {'th': 2611, 'fa': 2605, 'hi': 2614, 'he': 900000}.get(code, 2614)
                rows.append({'Key': code, 'Value': {'m_FileID': 0 if filename == 'sharedassets0.assets' else 2, 'm_PathID': target}})
            obj.save_typetree(tree, nodes=schema)
            allowed.add(path_id)
            generated[path_id] = (schema, tree)
        dest = output/'NoImNotAHuman_Data'/filename
        artifacts[str(dest.relative_to(output))] = save_verified(env, dest, {'original': original, 'allowed': allowed}, generated)
    for relative, expected in inputs.items():
        require(digest(game/relative) == expected, 'Source changed during build')
    report = {'schemaVersion': 1, 'sourceRoot': str(game), 'buildGuid': EXPECTED_BUILD_GUID,
              'languages': active, 'samples': {code:SAMPLES[code] for code in active}, 'languageKeyIds': ui_ids,
              'inputs': inputs, 'artifacts': artifacts, 'sourceUnchanged': True,
              'coverage': f'{len(active)} native locale entries, {len(active) * 10} carrier tables, 3 font-role dictionaries, one synthetic menu binding per locale. Russian carrier text/images are untranslated. Font shaping, bidi, runtime selection, dialogue and progression remain unverified.'}
    (output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'report': str(output/'report.json'), 'locales': len(active), 'artifacts': len(artifacts), 'sourceUnchanged': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, default=DEFAULT_GAME)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--codes', nargs='+', choices=sorted(LANGUAGES))
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT/'outputs'):
        parser.error('Output must be below canonical outputs/')
    run(args.game.resolve(), output, args.codes)
