"""Real-catalog regressions for matching and integrity updates, not renderer tests."""
import sys
import unittest
import struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from probe_assets import DEFAULT_GAME
from addressables_catalog import Catalog, bundle_crc, update_bundle


class CatalogIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aa = DEFAULT_GAME / 'NoImNotAHuman_Data/StreamingAssets/aa'
        cls.raw = (cls.aa / 'catalog.bin').read_bytes()
        cls.source = cls.aa / 'StandaloneWindows64/localization-string-tables-russian(ru)_assets_all.bundle'
        cls.replacement = Path(__file__).resolve().parents[1] / 'outputs/early-probe-verified-20261007/no-op.bundle'

    def test_all_original_bundle_sizes_match_catalog(self):
        entries = Catalog(self.raw).bundles()
        self.assertEqual(len(entries), 26)
        for entry in entries.values():
            path = self.aa / 'StandaloneWindows64' / entry['internalId'].replace('\\', '/').split('/')[-1]
            self.assertEqual(path.stat().st_size, entry['size'], str(path))

    def test_crc_matches_runtime_failure_evidence(self):
        self.assertEqual(bundle_crc(self.source), 0x93218230)
        self.assertEqual(bundle_crc(self.replacement), 0x2B91D6F2)

    def test_positive_only_integrity_span_changes(self):
        patched, report = update_bundle(self.raw, self.source, self.replacement)
        start, end = report['changedFieldSpan']
        self.assertEqual(patched[:start], self.raw[:start])
        self.assertEqual(patched[end:], self.raw[end:])
        self.assertEqual(report['newCrc'], bundle_crc(self.replacement))
        self.assertNotEqual(report['newCrc'], 0)

    def test_wrong_original_crc_rejected_at_integrity_guard(self):
        patched, report = update_bundle(self.raw, self.source, self.replacement)
        damaged = bytearray(self.raw)
        struct.pack_into('<I', damaged, report['optionsOffset']+8, 1)
        with self.assertRaisesRegex(ValueError, 'Original bundle/catalog integrity mismatch'):
            update_bundle(bytes(damaged), self.source, self.replacement)

    def test_wrong_header_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported binary catalog'):
            Catalog(bytes(4)+self.raw[4:])
