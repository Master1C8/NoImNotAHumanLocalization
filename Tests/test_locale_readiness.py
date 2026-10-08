"""Keep the integration denominator tied to the accepted source selection."""

import sys
import json
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from report_locale_readiness import selected_ids  # noqa: E402


class LocaleReadinessTest(unittest.TestCase):
    def test_checks_collection_uses_only_the_accepted_shared_id(self):
        selected, _, _ = selected_ids()
        self.assertEqual(selected["ChecksDialogs"], {21377524158749})
        self.assertEqual(sum(map(len, selected.values())), 16538)

    def test_language_selector_label_preserves_its_exact_source_value(self):
        try:
            from preserve_exact import MANIFEST, check_value
        except ModuleNotFoundError as exc:
            self.skipTest(str(exc))
        manifest = json.loads(MANIFEST.read_text())
        rule = next(row for row in manifest["tableRows"]
                    if row["stableId"].endswith(":66450728108675072"))
        self.assertTrue(rule["wholeTextExact"])
        check_value(rule, "Русский")
        with self.assertRaisesRegex(ValueError, "Whole-text exact value mismatch"):
            check_value(rule, "Română")


if __name__ == "__main__":
    unittest.main()
