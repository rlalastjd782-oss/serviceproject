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
            '@import url("overrides/ui_rebuild_05.css");',
        ]

        self.assertEqual(expected_imports, rebuild_source.strip().splitlines())
        for layer in [
            "ui_rebuild_01.css",
            "ui_rebuild_02.css",
            "ui_rebuild_03.css",
            "ui_rebuild_04.css",
            "ui_rebuild_05.css",
        ]:
            self.assertTrue((Path("static/css/overrides") / layer).is_file())
            self.assertIn(f"/static/css/overrides/{layer}", sw_source)

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

    def test_v31_v30_ui_cascade_rollback_removes_broad_final_locks(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        marker = "/* v3.1 v3.0 UI cascade rollback: narrow guards only after legacy rebuild passes. */"
        self.assertIn(marker, source)
        lock_source = source.split(marker, 1)[1].lower()
        disallowed_backgrounds = [
            "background: #fff",
            "background: #ffffff",
            "background: #f6faf4",
            "background: #f6faf7",
            "background: #f9fcf7",
            "background: #edf3f8",
            "background: #f7fafc",
            "background: #eaf4ef",
            "background: #eef4f9",
            "linear-gradient(180deg, #ffffff 0%",
            "linear-gradient(180deg, #fff 0%",
        ]

        self.assertIn("background-color: #0f172a !important;", lock_source)
        self.assertIn("background-color: #1e293b !important;", lock_source)
        for selector in [
            ".content .cat-badge",
            ".content .record-result-value",
            ".content .analysis-action-plan",
            ".content .recent-meal-template-row",
            ".content .quality-bar",
            ".content .heat-track",
            ".content .btn-danger",
            ".content .row-remove-button",
        ]:
            self.assertIn(selector, lock_source)
        for selector in [
            ".header",
            ".tabs",
            "tab-btn",
            "date-picker-form",
            "arrow-btn",
            "pagination-nav",
            "body-part-pagination-nav",
            "daily-metric:nth-child",
            "analysis-metric-grid .yearly-metric-card:nth-child",
            "analysis-action-card.is-warning",
            "analysis-action-card.is-goal",
            "analysis-action-card.is-achievement",
            ".cat-stat-card",
        ]:
            self.assertNotIn(selector, lock_source)
        for token in disallowed_backgrounds:
            self.assertNotIn(token, lock_source)

    def test_v31_v30_ui_cascade_rollback_keeps_period_controls_compact(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        source_without_comments = re.sub(r"/\*.*?\*/", "", source, flags=re.S)

        for selector in [
            ".month-picker-form-wide",
            ".week-control-row",
            ".meal-weekly-shell .week-control-row",
            ".period-control-panel",
            ".month-picker-form-wide.period-control-panel",
            ".meal-weekly-shell .week-control-row.period-control-panel",
        ]:
            single_column_pattern = re.compile(
                rf"{re.escape(selector)}[^{{}}]*{{[^}}]*grid-template-columns:\s*1fr\s*!important;",
                re.S,
            )
            with self.subTest(selector=selector):
                self.assertIsNone(single_column_pattern.search(source_without_comments))

        overload_section_pattern = re.compile(
            r"\.overload-dashboard-section\s*{[^}]*border-radius:\s*8px\s*!important;",
            re.S,
        )
        self.assertIsNotNone(overload_section_pattern.search(source_without_comments))

        for selector in [
            ".meal-weekly-shell .week-control-row",
            ".meal-weekly-shell .week-control-row.period-control-panel",
            ".period-control-panel",
        ]:
            stretch_pattern = re.compile(
                rf"{re.escape(selector)}[^{{}}]*{{[^}}]*align-items:\s*stretch\s*!important;",
                re.S,
            )
            with self.subTest(selector=selector):
                self.assertIsNone(stretch_pattern.search(source_without_comments))

        feature_source = Path("static/css/features/feature_pages_01.css").read_text(encoding="utf-8-sig")
        compact_arrow_pattern = re.compile(
            r"\.week-control-row\s+\.arrow-btn,\s*\.month-picker-form-wide\s+\.arrow-btn\s*{[^}]*min-height:\s*44px",
            re.S,
        )
        self.assertIsNone(compact_arrow_pattern.search(feature_source))

    def test_v31_existing_ui_restore_removes_light_surface_pass_tokens(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        source_lower = source.lower()
        disallowed_tokens = [
            "--app-bg: #f6faf4",
            "--surface: #ffffff",
            "--surface-card: #ffffff",
            "--surface-card-soft: #f8fafc",
            "--surface-page: #edf3f8",
            "--surface-control: #eef4f9",
            "--surface-control-strong: #e2edf6",
            "--surface-warm: #f9fcf7",
            "--today-surface: #ffffff",
            "--today-surface-soft: #f7f9fb",
            "--surface-text: #142235",
            "--surface-text: #172536",
            "--surface-muted: #516476",
            "--surface-muted: #526576",
            "#e2e8f0",
            "#e4eaf1",
            "#dbe3ec",
            "#d5dee8",
            "#eceff3",
            "#eef4e7",
            "#f5ecef",
            "#edf0f8",
            "#eaf3f4",
            "#f3efe8",
            "#e8f3f8",
            "#f0f2f5",
            "#526476",
            "#eef3f8",
            "#e0eaf3",
            "rgb(228, 234, 241)",
            "#f9fbfd",
            "background: #ffffff !important",
            "background-color: #ffffff !important",
            "background: #fff7f7 !important",
            "#fff6f6",
            "#fff5f5",
            "rgb(255, 245, 245)",
            "linear-gradient(180deg, #ffffff 0%",
            "linear-gradient(135deg, #ffffff",
        ]
        high_alpha_white = re.compile(r"rgb\(255 255 255 / (?:5[0-9]|[6-9][0-9]|100)%\)")

        for token in disallowed_tokens:
            self.assertNotIn(token, source_lower)
        self.assertIsNone(high_alpha_white.search(source_lower))

    def test_v31_dark_theme_cache_busting_and_manifest_colors_are_dark(self) -> None:
        version = Path("VERSION").read_text(encoding="utf-8-sig").strip()
        sw_source = Path("static/sw.js").read_text(encoding="utf-8-sig")
        manifest_source = Path("static/manifest.webmanifest").read_text(encoding="utf-8-sig")

        self.assertEqual("3.1.12", version)
        self.assertIn(f'const CACHE_NAME = "workout-pwa-v{version}";', sw_source)
        self.assertIn('"version": "3.1.12"', manifest_source)
        self.assertIn('"background_color": "#0b0f17"', manifest_source)
        self.assertIn('"theme_color": "#0b0f17"', manifest_source)
        self.assertIn("/static/css/dark_theme_lock.css", sw_source)

    def test_v31_dark_theme_lock_is_last_linked_stylesheet(self) -> None:
        expected_link = "filename='css/dark_theme_lock.css'"
        for template in [
            Path("health_tracker/templates/layouts/base.html"),
            Path("health_tracker/templates/layouts/admin.html"),
        ]:
            source = template.read_text(encoding="utf-8-sig")
            with self.subTest(template=str(template)):
                self.assertIn("filename='css/ui_rebuild.css'", source)
                self.assertIn(expected_link, source)
                self.assertLess(source.index("filename='css/ui_rebuild.css'"), source.index(expected_link))

        lock_source = Path("static/css/dark_theme_lock.css").read_text(encoding="utf-8-sig").lower()
        self.assertIn("v3.1 v3.0 ui cascade rollback", lock_source)
        self.assertIn(".content .cat-badge", lock_source)
        self.assertIn(".content .record-result-value", lock_source)
        self.assertIn(".content .analysis-action-plan", lock_source)
        self.assertIn(".content .recent-meal-template-row", lock_source)
        self.assertIn(".content .quality-bar", lock_source)
        self.assertIn(".content .heat-track", lock_source)
        self.assertIn(".content .btn-danger", lock_source)
        self.assertIn(".content .row-remove-button", lock_source)
        for selector in [
            ".header",
            ".tabs",
            "tab-btn",
            ".content .section",
            ".content section",
            ".content article",
            ".content .summary-card",
            ".content .record-card",
            ".content .yearly-metric-card",
            ".content .date-picker-form",
            ".content .pagination-nav",
            ".content .body-part-pagination-nav",
            ".content .account-action-btn",
        ]:
            self.assertNotIn(selector, lock_source)
        self.assertIn("background-color: var(--surface-control) !important;", lock_source)
        self.assertIn("background-color: var(--surface-control-strong) !important;", lock_source)
