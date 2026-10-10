"""Actual save-inventory guard: ordinary files versus an escaping nested link.

These tests exercise filesystem traversal and hashing. They do not replace
native game, Wine, capture, process ownership or restoration verification.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from run_locale_visual_qa import files
from probe_assets import digest


class SaveInventoryGuard(unittest.TestCase):
    def test_same_inventory_rejects_escaping_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            save = parent / 'save'
            nested = save / 'remote'
            nested.mkdir(parents=True)
            outside = parent / 'outside.sav'
            outside.write_bytes(b'owner save sentinel')
            local = nested / 'game.sav'
            local.write_bytes(outside.read_bytes())
            expected = digest(local)
            self.assertEqual(files(save), {'remote/game.sav': expected})
            local.unlink()
            local.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'Save directory contains an external link'):
                files(save)
            self.assertEqual(outside.read_bytes(), b'owner save sentinel')

    def test_escaping_directory_with_identical_contents_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            save = parent / 'save'
            nested = save / 'remote'
            nested.mkdir(parents=True)
            (nested / 'game.sav').write_bytes(b'checkpoint')
            self.assertEqual(set(files(save)), {'remote/game.sav'})
            (nested / 'game.sav').unlink()
            nested.rmdir()
            outside = parent / 'outside'
            outside.mkdir()
            (outside / 'game.sav').write_bytes(b'checkpoint')
            nested.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'Save directory contains an external link'):
                files(save)


if __name__ == '__main__':
    unittest.main()
