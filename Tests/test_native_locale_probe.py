"""Real-asset regressions for generated headers and native locale registration."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Scripts'))
import UnityPy
from addressables_catalog import Catalog
from build_locale_probe import LANGUAGES, identity
from probe_assets import DEFAULT_GAME, EXPECTED_UNITY, SAMPLES, UI_ID
from unity_types import CheckedTypeTreeGenerator, generated_tree, serialized_bytes


class NativeProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT/'outputs/native-locale-probe-v6'
        cls.report = json.loads((cls.output/'report.json').read_text())

    def test_all_locale_and_table_bindings(self):
        c = Catalog((self.output/'NoImNotAHuman_Data/StreamingAssets/aa/catalog.bin').read_bytes())
        keys = c.keys()
        self.assertEqual(len(keys['Locale']['locations']), 32)
        self.assertEqual(len(set(keys['Locale']['locations'])), 32)
        self.assertEqual(len(c.bundles()), 26)
        for code, (english, _) in LANGUAGES.items():
            self.assertIn(f'{english} ({code})', keys)
            self.assertEqual(len(keys['Locale-'+code]['locations']), 10)
            for table in ['Characters','ChecksDialogs','DayDialogs','Endings','NightDialogs',
                          'NotCharacterDialogs','DemoDialogs','Dialogs','TestDialogs','UI']:
                loc = keys[table+'_'+code]['locations'][0]
                self.assertIn(loc, keys['Locale-'+code]['locations'])
                _, internal, _, _, _, _, _ = c.values(loc, 7)
                self.assertTrue(c.string(internal,'/').endswith('/'+table+'_'+code+'.asset'))

    def test_samples_are_independent_native_tables(self):
        bundle = self.output/'NoImNotAHuman_Data/StreamingAssets/aa/StandaloneWindows64/localization-string-tables-russian(ru)_assets_all.bundle'
        env = UnityPy.load(str(bundle))
        for code in LANGUAGES:
            obj = next(o for o in env.objects if o.path_id == identity('UI_'+code))
            tree = obj.read_typetree()
            self.assertEqual(tree['m_LocaleId']['m_Code'], code)
            self.assertEqual(next(r['m_Localized'] for r in tree['m_TableData'] if r['m_Id']==UI_ID), SAMPLES[code])
            self.assertTrue(set(self.report['languageKeyIds'].values()).issubset(r['m_Id'] for r in tree['m_TableData']))
        russian = next(o for o in env.objects if o.type.name=='MonoBehaviour' and o.peek_name()=='UI_ru')
        self.assertEqual(next(r['m_Localized'] for r in russian.read_typetree()['m_TableData'] if r['m_Id']==UI_ID),'Новая игра')

    def test_every_appended_object_has_a_container_binding(self):
        folder=self.output/'NoImNotAHuman_Data/StreamingAssets/aa/StandaloneWindows64'
        for filename,expected in [('localization-locales_assets_all.bundle',32),
                                  ('localization-string-tables-russian(ru)_assets_all.bundle',135),
                                  ('localization-asset-tables-russian(ru)_assets_all.bundle',15)]:
            env=UnityPy.load(str(folder/filename))
            bundle=next(o for o in env.objects if o.type.name=='AssetBundle').read_typetree()
            self.assertEqual(len(bundle['m_Container']),expected)
            bound={row['asset']['m_PathID'] for _,row in bundle['m_Container']}
            assets={o.path_id for o in env.objects if o.type.name=='MonoBehaviour'}
            self.assertEqual(bound,assets)

    def test_generated_headers_and_noop_under_optimization(self):
        generator = CheckedTypeTreeGenerator(EXPECTED_UNITY)
        generator.load_local_dll_folder(str(DEFAULT_GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed'))
        for filename, ids in [('resources.assets',[1453,1454]), ('sharedassets0.assets',[2601,2604,2614])]:
            env=UnityPy.load(str(DEFAULT_GAME/'NoImNotAHuman_Data'/filename))
            env.typetree_generator=generator
            for path_id in ids:
                obj=env.file.objects[path_id]
                before=serialized_bytes(obj)
                tree,_=generated_tree(obj)
                self.assertEqual(before,serialized_bytes(obj))
                self.assertNotEqual(tree['m_Script']['m_PathID'],0)


if __name__=='__main__':
    unittest.main()
