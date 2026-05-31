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

    def test_css_imports_resolve_to_existing_files(self) -> None:
        import_pattern = re.compile(r"@import\s+url\([\"'](?P<path>[^\"']+)[\"']\)")

        for path in sorted(Path("static/css").rglob("*.css")):
            source = path.read_text(encoding="utf-8-sig")
            for match in import_pattern.finditer(source):
                imported = (path.parent / match.group("path")).resolve()
                with self.subTest(path=str(path), imported=str(imported)):
                    self.assertTrue(imported.is_file())

    def test_ui_rebuild_restores_v265_override_layers(self) -> None:
        rebuild_path = Path("static/css/ui_rebuild.css")
        rebuild_source = rebuild_path.read_text(encoding="utf-8-sig")
        sw_source = Path("static/sw.js").read_text(encoding="utf-8-sig")
        expected_imports = [
            '@import url("overrides/ui_rebuild_01.css");',
            '@import url("overrides/ui_rebuild_02.css");',
            '@import url("overrides/ui_rebuild_03.css");',
            '@import url("overrides/ui_rebuild_04.css");',
        ]

        self.assertEqual(expected_imports, rebuild_source.strip().splitlines())
        for layer in ["ui_rebuild_01.css", "ui_rebuild_02.css", "ui_rebuild_03.css", "ui_rebuild_04.css"]:
            self.assertTrue((Path("static/css/overrides") / layer).is_file())
            self.assertIn(f"/static/css/overrides/{layer}", sw_source)

        self.assertNotIn("ui_rebuild_05.css", rebuild_source)
        self.assertNotIn("/static/css/overrides/ui_rebuild_05.css", sw_source)

    def test_service_worker_precache_assets_exist(self) -> None:
        sw_source = Path("static/sw.js").read_text(encoding="utf-8-sig")
        asset_pattern = re.compile(r'"(?P<asset>/(?:static|sw\.js|favicon\.ico)[^"]*)"')

        for match in asset_pattern.finditer(sw_source):
            asset = match.group("asset")
            if asset == "/sw.js":
                path = Path("static/sw.js")
            elif asset == "/favicon.ico":
                path = Path("static/icon.svg")
            else:
                path = Path(asset.lstrip("/"))
            with self.subTest(asset=asset):
                self.assertTrue(path.is_file())

    def test_final_gray_theme_layer_avoids_black_text_and_border_stacking(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_04.css").read_text(encoding="utf-8-sig").lower()
        disallowed_tokens = [
            "#000",
            "#111827",
            "black",
            "border-color:",
            "background: #fff",
            "background: #ffffff",
            "background: #f9fafb",
            "background: #f8fafc",
        ]
        for token in disallowed_tokens:
            self.assertNotIn(token, source)
