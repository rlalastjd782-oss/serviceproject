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

    def test_ui_rebuild_uses_only_current_override_layers(self) -> None:
        rebuild_source = Path("static/css/ui_rebuild.css").read_text(encoding="utf-8-sig")
        sw_source = Path("static/sw.js").read_text(encoding="utf-8-sig")
        retired_layers = [
            "ui_rebuild_01.css",
            "ui_rebuild_02.css",
            "ui_rebuild_03.css",
        ]
        for layer in retired_layers:
            self.assertNotIn(layer, rebuild_source)
            self.assertNotIn(layer, sw_source)
        self.assertIn("ui_rebuild_04.css", rebuild_source)
        self.assertIn("ui_rebuild_05.css", rebuild_source)

    def test_final_ui_layer_flattens_nested_card_controls(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.15 anti-nesting pass", source)
        self.assertIn(".summary-card .summary-card", source)
        self.assertIn(".section .section", source)
        self.assertIn(".record-summary .badge", source)
        self.assertIn("box-shadow: none !important;", source)
        self.assertIn("--qa-flat", source)

    def test_today_quality_ui_uses_neutral_background_colors(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.17 lighter today summary", source)
        self.assertIn(".today-mode-actions .mode-button.btn-primary", source)
        self.assertIn(".overview-only.data-quality-section", source)
        self.assertIn("background: #f6f7f9 !important;", source)
        self.assertIn(".data-quality-card,\n.data-quality-card.state-high", source)
        self.assertIn("background: #ffffff !important;", source)
        self.assertNotIn("background:\n    linear-gradient(180deg, rgb(255 255 255 / 68%), rgb(235 241 247 / 36%)),\n    #edf2f7 !important;", source)
        self.assertNotIn(".today-mode-actions .mode-button.btn-primary {\n  background:\n    linear-gradient(180deg, rgb(255 255 255 / 18%)", source)

    def test_today_workout_ui_uses_record_neutral_surfaces(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.19 workout neutral pass", source)
        self.assertIn(".workout-mode .section.workout-only", source)
        self.assertIn(".workout-mode .workout-summary-card", source)
        self.assertIn(".workout-mode .exercise-quick-panel", source)
        self.assertIn(".workout-mode .set-entry-row", source)
        self.assertIn("background: #f6f7f9 !important;", source)

    def test_today_overview_summary_ui_uses_record_neutral_surfaces(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.20 today overview neutral pass", source)
        self.assertIn(".today-shell:not(.workout-mode):not(.meal-mode) .today-hero-section", source)
        self.assertIn(".today-shell:not(.workout-mode):not(.meal-mode) .summary-grid.overview-only", source)
        self.assertIn(".today-shell:not(.workout-mode):not(.meal-mode) .today-focus-card", source)
        self.assertIn(".today-shell:not(.workout-mode):not(.meal-mode) .summary-card", source)
        self.assertIn(".today-shell:not(.workout-mode):not(.meal-mode) .record-card", source)

    def test_today_page_uses_records_layout_spacing(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.21 today records-layout parity", source)
        self.assertIn(".today-shell {\n  display: grid !important;", source)
        self.assertIn(".today-shell > .date-row", source)
        self.assertIn(".today-shell .record-list {\n  grid-template-columns: 1fr !important;", source)
        self.assertIn(".today-shell .today-focus-panel", source)
        self.assertIn(".today-shell .summary-card", source)

    def test_light_theme_has_no_legacy_dark_surface_tokens(self) -> None:
        dark_surface_tokens = [
            "#101827",
            "#101b2e",
            "#121a29",
            "#0b1220",
            "#0d1420",
            "#0c111a",
            "#111823",
            "#102018",
            "#1f1115",
            "#0f1724",
            "#16131a",
            "#201a0c",
            "#271111",
            "rgb(15 23 42",
            "rgb(17 24 39",
            "rgb(8 13 22",
            "rgb(31 41 55",
            "rgb(127 29 29",
        ]
        legacy_light_text_tokens = [
            "#cbd5e1",
            "#d8e7ff",
            "#e5f0ff",
            "#bae6fd",
            "#fbbf24",
            "#4ade80",
            "#f87171",
        ]
        allowed_shadow_tokens = ("--shadow", "box-shadow")

        for path in sorted(Path("static/css").rglob("*.css")):
            source = path.read_text(encoding="utf-8-sig")
            for line_number, line in enumerate(source.splitlines(), start=1):
                stripped = line.strip()
                if any(token in stripped for token in dark_surface_tokens):
                    if not any(token in stripped for token in allowed_shadow_tokens):
                        self.fail(f"{path}:{line_number} has legacy dark surface token: {stripped}")
                for token in legacy_light_text_tokens:
                    self.assertNotIn(token, stripped, f"{path}:{line_number} has legacy light text token")

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
