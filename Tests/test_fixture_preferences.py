import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Scripts'))
from fixture_preferences import replace_language,read_settings


def fixture(code):
    data={'TextSettingsData':{'SelectedLanguage':code,'IsUseTypewriter':False},
          'Other':{'Word':code+'-'+code+'script','Array':['id','hi']}}
    raw=json.dumps(data,separators=(',',':')).encode()+b'\0'
    return '[Software\\\\Trioskaz\\\\NoImNotAHuman]\n"SettingsPrefsData_h3770934882"=hex:'+','.join(f'{b:02x}' for b in raw)+'\n\n[Other]\n"Value"="id"\n'


class PreferenceTests(unittest.TestCase):
    def test_both_directions_preserve_overlapping_values(self):
        for old,new in [('id','hi'),('hi','id'),('id','fil'),('fil','id')]:
            source=fixture(old);result,before=replace_language(source,old,new)
            expected=copy.deepcopy(before);expected['TextSettingsData']['SelectedLanguage']=new
            self.assertEqual(read_settings(result)[2],expected)
            self.assertTrue(result.endswith('[Other]\n"Value"="id"\n'))

    def test_postcondition_then_idempotence(self):
        changed,_=replace_language(fixture('id'),'id','hi')
        self.assertEqual(read_settings(changed)[2]['TextSettingsData']['SelectedLanguage'],'hi')
        repeated,_=replace_language(changed,'hi','hi')
        self.assertEqual(repeated,changed)

    def test_wrong_prior_language_reason(self):
        with self.assertRaisesRegex(ValueError,'Saved locale changed before mutation'):
            replace_language(fixture('id'),'hi','fa')

    def test_duplicate_game_key_is_rejected(self):
        source=fixture('id')
        with self.assertRaisesRegex(ValueError,'Missing/ambiguous game preferences'):
            replace_language(source+source,'id','hi')


if __name__=='__main__':unittest.main()
