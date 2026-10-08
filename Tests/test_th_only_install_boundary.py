"""Exercise the Thai-only installer's real per-file interruption boundary."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from install_th_only_package import replace_files
from probe_assets import digest


class ThaiOnlyInstallBoundary(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir="/private/tmp")
        self.root = Path(self.temporary.name)
        self.game = self.root / "game"
        self.package = self.root / "package"
        self.output = self.root / "backups"
        self.output.mkdir()
        self.rows = []
        for name in ("first", "second"):
            relative = "NoImNotAHuman_Data/" + name
            installed = self.game / relative
            source = self.package / relative
            installed.parent.mkdir(parents=True, exist_ok=True)
            source.parent.mkdir(parents=True, exist_ok=True)
            installed.write_bytes((name + " old").encode())
            source.write_bytes((name + " new").encode())
            self.rows.append({"relativePath": relative, "before": digest(installed),
                              "after": digest(source), "installed": False})
        self.receipt = {"completed": False, "files": self.rows}
        self.receipt_path = self.output / "receipt.json"
        self.receipt_path.write_text(json.dumps(self.receipt))

    def tearDown(self):
        self.temporary.cleanup()

    def test_failure_between_writes_preserves_exact_partial_state(self):
        with self.assertRaisesRegex(RuntimeError, "Injected interruption"):
            replace_files(self.package, self.game, self.output, self.rows,
                          self.receipt, self.receipt_path, inject_failure_after=1)
        self.assertEqual(digest(self.game / self.rows[0]["relativePath"]),
                         self.rows[0]["after"])
        self.assertEqual(digest(self.game / self.rows[1]["relativePath"]),
                         self.rows[1]["before"])
        self.assertEqual(digest(self.output / self.rows[0]["relativePath"]),
                         self.rows[0]["before"])
        self.assertFalse((self.output / self.rows[1]["relativePath"]).exists())
        recorded = json.loads(self.receipt_path.read_text())
        self.assertFalse(recorded["completed"])
        self.assertEqual([row["installed"] for row in recorded["files"]], [True, False])
        self.assertNotEqual(digest(self.game / self.rows[0]["relativePath"]),
                            self.rows[0]["before"])

    def test_matching_complete_application(self):
        replace_files(self.package, self.game, self.output, self.rows,
                      self.receipt, self.receipt_path)
        self.assertTrue(all(digest(self.game / row["relativePath"]) == row["after"]
                            for row in self.rows))
        self.assertTrue(all(row["installed"] for row in
                            json.loads(self.receipt_path.read_text())["files"]))


if __name__ == "__main__":
    unittest.main()
