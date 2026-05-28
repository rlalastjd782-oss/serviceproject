from __future__ import annotations

import re
import unittest
from pathlib import Path


class StaticAssetIntegrityTest(unittest.TestCase):
    def test_css_files_have_balanced_braces_and_no_known_broken_selectors(self) -> None:
        for path in [
            Path("static/styles.css"),
            Path("static/today.css"),
            Path("static/feature_pages.css"),
            Path("static/analysis.css"),
            Path("static/responsive.css"),
            Path("static/rules.css"),
            Path("static/ui_rebuild.css"),
        ]:
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8-sig")
                without_comments = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
                self.assertEqual(without_comments.count("{"), without_comments.count("}"))
                self.assertNotIn(".next-set-advice-row {.next-set-advice-row", source)
                if path.name == "ui_rebuild.css":
                    self.assertIn(":not(.meal-record-card)", source)
                    self.assertIn(".record-list > .meal-record-card", source)
