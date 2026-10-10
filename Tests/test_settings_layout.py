import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Scripts'))
from build_settings_layout import fit


class SettingsLayout(unittest.TestCase):
    def setUp(self):
        self.tree={'m_fontSize':36.0,'m_enableAutoSizing':0,'m_fontSizeMin':18.0,
                   'm_fontSizeMax':72.0,'m_TextWrappingMode':1,'m_text':'SFX',
                   'm_fontAsset':{'m_FileID':0,'m_PathID':12},'m_richText':True}

    def test_exact_three_fields_and_original_preserved(self):
        before=copy.deepcopy(self.tree);after=fit(self.tree)
        self.assertEqual(self.tree,before)
        self.assertEqual({k for k in before if before[k]!=after[k]},
                         {'m_enableAutoSizing','m_fontSizeMax','m_TextWrappingMode'})
        self.assertEqual(after['m_fontSizeMin'],18.0);self.assertEqual(after['m_fontSizeMax'],36.0)

    def test_changed_input_and_already_fitted_rejected(self):
        for key,value in [('m_fontSize',35.0),('m_enableAutoSizing',1),('m_TextWrappingMode',0)]:
            tree=copy.deepcopy(self.tree);tree[key]=value
            with self.assertRaisesRegex(ValueError,'exact original state'):fit(tree)
        with self.assertRaisesRegex(ValueError,'exact original state'):fit(fit(self.tree))


if __name__=='__main__':unittest.main()
