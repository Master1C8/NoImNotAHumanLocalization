"""Keep the integration denominator tied to the accepted source selection."""

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from report_locale_readiness import selected_ids  # noqa: E402


class LocaleReadinessTest(unittest.TestCase):
    def test_checks_collection_uses_only_the_accepted_shared_id(self):
        selected, _, _ = selected_ids()
        self.assertEqual(selected["ChecksDialogs"], {21377524158749})
        self.assertEqual(sum(map(len, selected.values())), 16538)


if __name__ == "__main__":
    unittest.main()
