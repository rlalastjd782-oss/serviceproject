from __future__ import annotations

import re
import unittest
from pathlib import Path


class StaticAssetIntegrityTest(unittest.TestCase):
    def test_css_files_have_balanced_braces_and_no_known_broken_selectors(self) -> None:
        for path in sorted(Path("static/css").rglob("*.css")):
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8-sig")
                without_comments = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
                self.assertEqual(without_comments.count("{"), without_comments.count("}"))
                self.assertNotIn(".next-set-advice-row {.next-set-advice-row", source)

        ui_source = "\n".join(path.read_text(encoding="utf-8-sig") for path in sorted(Path("static/css/overrides").glob("*.css")))
        self.assertIn(":not(.meal-record-card)", ui_source)
        self.assertIn(".record-list > .meal-record-card", ui_source)
        self.assertNotIn(".tab-btn,\n  .mode-button", ui_source)
        self.assertIn(".tabs .tab-btn", ui_source)
