from __future__ import annotations

import re
import unittest
from pathlib import Path


class StaticAssetIntegrityTest(unittest.TestCase):
    def test_user_facing_text_has_no_broken_encoding_markers(self) -> None:
        broken_tokens = [
            chr(0xFFFD),
            chr(0x00C3),
            chr(0x00C2),
            chr(0x00EC),
            chr(0x00EB),
            chr(0x00ED),
            chr(0x00EA),
            chr(0xF9E4),
            chr(0x7B4C),
            chr(0x6E72),
            chr(0xAC2E),
            chr(0xB2EF),
            chr(0xBB3E),
        ]
        paths = [
            *Path("health_tracker/templates").rglob("*.html"),
            *Path("health_tracker/services").rglob("*.py"),
            *Path("static/js").rglob("*.js"),
            *Path("static/css").rglob("*.css"),
        ]
        repeated_question_mark = re.compile(r"\?{3,}")
        repeated_user_text_question_mark = re.compile(r"\?{2,}")
        broken_question_hangul = re.compile(r"\?[가-힣]")
        cjk_ideograph = re.compile(r"[\u4E00-\u9FFF]")

        for path in sorted(paths):
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8-sig")
                self.assertIsNone(repeated_question_mark.search(source))
                if path.suffix != ".js":
                    self.assertIsNone(repeated_user_text_question_mark.search(source))
                self.assertIsNone(broken_question_hangul.search(source))
                self.assertIsNone(cjk_ideograph.search(source))
                for token in broken_tokens:
                    self.assertNotIn(token, source)

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
