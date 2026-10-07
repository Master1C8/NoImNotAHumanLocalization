import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Scripts'))
from start_dialogue_probe import enable_typewriter
from fixture_preferences import read_settings
from test_fixture_preferences import fixture

class DialoguePreferences(unittest.TestCase):
    def test_typewriter_preserves_locale_and_other_registry_values(self):
        source=fixture('hi')
        before=read_settings(source)[2]
        result=enable_typewriter(source)
        wanted=copy.deepcopy(before);wanted['TextSettingsData']['IsUseTypewriter']=True
        self.assertEqual(read_settings(result)[2],wanted)
        self.assertEqual(result[result.index('\n\n[Other]'):],source[source.index('\n\n[Other]'):])
        self.assertEqual(enable_typewriter(result),result)

    def test_typewriter_rejects_non_boolean_after_valid_registry_guards(self):
        source=fixture('hi')
        source=source.replace('66,61,6c,73,65','22,66,61,6c,73,65,22')
        self.assertEqual(read_settings(source)[2]['TextSettingsData']['IsUseTypewriter'],'false')
        with self.assertRaisesRegex(ValueError,'Unexpected typewriter preference'):
            enable_typewriter(source)
