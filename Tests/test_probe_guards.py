"""Guard regressions using the actual pinned Russian table as the positive control.

The wrapper substitutes only object enumeration; these tests do not exercise
Unity serialization. The real no-op and 14 round trips exercise that boundary.
"""
import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
import UnityPy
from probe_assets import DEFAULT_GAME, select_ui, require, UI_ID


class ProbeGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = DEFAULT_GAME / "NoImNotAHuman_Data/StreamingAssets/aa/StandaloneWindows64/localization-string-tables-russian(ru)_assets_all.bundle"
        _, _, cls.original = select_ui(UnityPy.load(str(path)))

    def select(self, tree):
        obj = SimpleNamespace(assets_file=SimpleNamespace(name="control"), path_id=1,
                              type=SimpleNamespace(name="MonoBehaviour"),
                              read_typetree=lambda: tree)
        return select_ui(SimpleNamespace(objects=[obj]))

    def test_real_positive_control(self):
        self.select(copy.deepcopy(self.original))

    def test_rejects_wrong_source_language(self):
        tree = copy.deepcopy(self.original)
        tree["m_LocaleId"]["m_Code"] = "en"
        with self.assertRaisesRegex(ValueError, "Wrong source language"):
            self.select(tree)

    def test_rejects_duplicate_ids(self):
        tree = copy.deepcopy(self.original)
        tree["m_TableData"].append(copy.deepcopy(tree["m_TableData"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate Russian UI IDs"):
            self.select(tree)

    def test_rejects_changed_source_binding(self):
        tree = copy.deepcopy(self.original)
        next(e for e in tree["m_TableData"] if e["m_Id"] == UI_ID)["m_Localized"] = "New Game"
        with self.assertRaisesRegex(ValueError, "Unsupported original Common_NewGame"):
            self.select(tree)

    def test_require_survives_python_optimization(self):
        require(True, "control")
        with self.assertRaisesRegex(ValueError, "changed serialized value"):
            require(False, "changed serialized value")


if __name__ == "__main__":
    unittest.main()
