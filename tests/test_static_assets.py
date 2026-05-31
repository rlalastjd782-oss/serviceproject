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

    def test_today_menu_stays_three_tabs_and_has_subtle_depth(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.22 today menu consistency and subtle depth pass", source)
        self.assertIn(".today-shell .today-mode-actions {\n  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;", source)
        self.assertIn(".today-shell .today-mode-actions .focus-mode-button", source)
        self.assertIn("display: none !important;", source)
        self.assertIn("0 5px 14px rgb(28 36 46 / 7%)", source)
        self.assertIn("0 4px 10px rgb(28 36 46 / 6%)", source)

    def test_workout_focus_action_is_visible_below_three_tabs(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.23 restore workout focus action", source)
        self.assertIn(".today-shell.workout-mode .today-mode-actions .focus-mode-button", source)
        self.assertIn("grid-column: 1 / -1 !important;", source)
        self.assertIn("display: inline-flex !important;", source)

    def test_today_depth_polish_uses_stronger_layered_surfaces(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.24 today depth polish", source)
        self.assertIn("0 10px 24px rgb(36 46 58 / 10%)", source)
        self.assertIn("0 7px 16px rgb(36 46 58 / 9%)", source)
        self.assertIn(".today-shell .today-focus-card:hover", source)
        self.assertIn("transform: translateY(-1px) !important;", source)
        self.assertIn(".today-shell input,\n.today-shell select,\n.today-shell textarea", source)

    def test_today_full_surface_pass_covers_remaining_panels(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.25 today full surface pass", source)
        self.assertIn(".today-shell .location-equipment-strip", source)
        self.assertIn(".today-shell .workout-clock-section", source)
        self.assertIn(".today-shell #rest-timer", source)
        self.assertIn(".today-shell .completion-card", source)
        self.assertIn(".today-shell:not(.workout-mode):not(.meal-mode) .today-focus-card", source)
        self.assertIn(".today-shell:not(.workout-mode):not(.meal-mode) .summary-card", source)

    def test_today_css_audit_pass_addresses_remaining_surfaces(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.26 today css audit pass", source)
        self.assertIn("--today-panel: #e9eef4;", source)
        self.assertIn(".today-shell .data-quality-ring", source)
        self.assertIn("conic-gradient(from 180deg", source)
        self.assertIn(".workout-mode #workout-input {\n  order: 13 !important;", source)
        self.assertIn(".today-shell .location-quick-panel > summary", source)
        self.assertIn(".today-shell .optional-workout-panel,\n.today-shell .optional-workout-panel[open]", source)
        self.assertIn(".today-shell .workout-clock-display,\n.today-shell .timer-display", source)

    def test_today_layout_correction_pass_flattens_inner_cards_and_orders_workout(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.27 today layout correction pass", source)
        self.assertIn(".workout-mode .next-action-section {\n  order: 16 !important;", source)
        self.assertIn(".workout-mode .rule-card-section {\n  order: 17 !important;", source)
        self.assertIn(".today-shell:not(.workout-mode):not(.meal-mode) .today-focus-card.is-analysis", source)
        self.assertIn(".today-shell .data-quality-card {\n  display: grid !important;", source)
        self.assertIn(".today-shell .today-focus-card,\n.today-shell .summary-card,\n.today-shell .quality-metric", source)
        self.assertIn("box-shadow: none !important;", source)
        self.assertIn(".today-shell .workout-clock-section .timer-actions", source)
        self.assertIn(".today-shell.workout-mode .overview-only:not(.workout-only)", source)
        self.assertIn(".today-shell.meal-mode .overview-only", source)
        self.assertIn("grid-template-columns: 1fr !important;\n    justify-items: center !important;", source)
        self.assertIn(".today-shell > .section,\n.today-shell > .summary-grid", source)
        self.assertIn("margin-bottom: 0 !important;", source)

    def test_today_visual_reset_returns_to_white_section_cards(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.28 today visual reset", source)
        self.assertIn("--today-surface: #ffffff;", source)
        self.assertIn(".today-shell .date-row,\n.today-shell .today-mode-actions,\n.today-shell .section", source)
        self.assertIn("background: var(--today-surface) !important;", source)
        self.assertIn(".today-shell .today-focus-card,\n.today-shell .summary-card,\n.today-shell .quality-metric", source)
        self.assertIn("background: var(--today-surface-soft) !important;", source)
        self.assertIn(".today-shell.workout-mode .overview-only:not(.workout-only)", source)
        self.assertIn(".today-shell .workout-action-dock {\n  position: static !important;", source)
        self.assertIn(".today-shell.workout-mode > .summary-grid.overview-only", source)
        self.assertIn(".today-shell > a,\n.today-shell > strong,\n.today-shell > small", source)

    def test_meal_mode_keeps_recording_flow_ahead_of_optional_panels(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.29 meal mode order pass", source)
        self.assertIn(".today-shell.meal-mode .meal-goal-section {\n  order: 10 !important;", source)
        self.assertIn(".today-shell.meal-mode .meal-input-section {\n  order: 20 !important;", source)
        self.assertIn(".today-shell.meal-mode .today-meal-section {\n  order: 30 !important;", source)
        self.assertIn(".today-shell.meal-mode .optional-section {\n  order: 50 !important;", source)

    def test_records_style_dimensional_ui_uses_shared_surface_tokens(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        self.assertIn("v2.8.30 records-style dimensional UI pass", source)
        self.assertIn("--surface-page: #edf3f8;", source)
        self.assertIn("--surface-card: #ffffff;", source)
        self.assertIn(".record-subnav ~ .section,\n.record-search-dashboard", source)
        self.assertIn(".record-search-dashboard,\n.record-result-section,\n.analysis-dashboard-section", source)
        self.assertIn(".daily-record-card,\n.record-result-card,\n.today-shell .today-focus-card", source)
        self.assertIn(".daily-metric,\n.record-result-value,\n.today-shell .detail-row", source)
        self.assertIn(".record-subnav a.active,\n.record-subnav a.is-active,\n.analysis-subnav a.active", source)

    def test_meal_tab_dimensional_ui_pass_updates_cache_version(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        weekly_template = Path("health_tracker/templates/meals/weekly.html").read_text(encoding="utf-8-sig")
        version = Path("VERSION").read_text(encoding="utf-8-sig").strip()
        sw_source = Path("static/sw.js").read_text(encoding="utf-8-sig")
        manifest_source = Path("static/manifest.webmanifest").read_text(encoding="utf-8-sig")

        self.assertEqual(version, "3.0.0")
        self.assertIn('CACHE_NAME = "workout-pwa-v3.0.0"', sw_source)
        self.assertIn('"version": "3.0.0"', manifest_source)
        self.assertIn('"background_color": "#edf3f8"', manifest_source)
        self.assertIn('class="meal-weekly-shell"', weekly_template)

        self.assertLess(source.index("v2.8.30 records-style dimensional UI pass"), source.index("v2.8.31 meal-tab dimensional UI pass"))
        self.assertIn(".meal-weekly-shell > .section,\n.today-shell .date-row", source)
        self.assertIn(".meal-weekly-shell .summary-card,\n.meal-weekly-shell .goal-card,\n.meal-weekly-shell .weekly-meal-day", source)
        self.assertIn(".meal-weekly-shell .week-control-row,\n.meal-weekly-shell .week-date-form", source)
        self.assertIn(".settings-panel,\n.settings-overview-section", source)

    def test_global_surface_enforcement_pass_covers_required_screens(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        version = Path("VERSION").read_text(encoding="utf-8-sig").strip()
        sw_source = Path("static/sw.js").read_text(encoding="utf-8-sig")
        manifest_source = Path("static/manifest.webmanifest").read_text(encoding="utf-8-sig")

        self.assertEqual(version, "3.0.0")
        self.assertIn('CACHE_NAME = "workout-pwa-v3.0.0"', sw_source)
        self.assertIn('"version": "3.0.0"', manifest_source)
        self.assertLess(source.index("v2.8.31 meal-tab dimensional UI pass"), source.index("v2.8.32 global surface enforcement pass"))

        required_tokens = [
            "--surface-page: #edf3f8;",
            "--surface-card: #ffffff;",
            "--surface-card-soft: #f8fafc;",
            "--surface-control: #eef4f9;",
            "--surface-shadow-active:",
        ]
        for token in required_tokens:
            self.assertIn(token, source)

        required_selectors = [
            ".meal-weekly-shell > .section",
            ".today-shell > .date-row",
            ".today-shell .workout-action-dock",
            ".today-shell .body-metric-form",
            ".today-shell .meal-entry-row",
            ".record-search-dashboard",
            ".record-result-section",
            ".analysis-dashboard-section",
            ".yearly-body-section",
            ".equipment-dashboard-section",
            ".record-body-part-section",
            ".more-group-section",
            ".more-tool-section",
            ".tool-card",
            ".settings-panel",
            ".settings-password-form",
        ]
        for selector in required_selectors:
            self.assertIn(selector, source)

        active_selectors = [
            ".body-part-filter-chip.is-active",
            ".body-part-toggle.is-active",
            ".pr-rank-card.is-selected",
            ".equipment-summary-card.is-selected",
            ".more-tool-section .btn-primary",
            ".settings-panel .btn-primary",
        ]
        for selector in active_selectors:
            self.assertIn(selector, source)

    def test_v3_ui_restructure_contract_is_present(self) -> None:
        source = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8-sig")
        base_template = Path("health_tracker/templates/layouts/base.html").read_text(encoding="utf-8-sig")
        overview_template = Path("health_tracker/templates/today/_overview_panels.html").read_text(encoding="utf-8-sig")
        weekly_template = Path("health_tracker/templates/summaries/_weekly_dashboard.html").read_text(encoding="utf-8-sig")
        more_template = Path("health_tracker/templates/more/index.html").read_text(encoding="utf-8-sig")
        settings_template = Path("health_tracker/templates/settings/index.html").read_text(encoding="utf-8-sig")

        self.assertIn("v3.0 final enforcement", source)
        self.assertIn('class="app-navigation-shell"', base_template)
        self.assertIn('class="account-actions"', base_template)
        self.assertNotIn("tab-logout-form", base_template[base_template.index('<nav class="tabs"') : base_template.index("</nav>")])

        for token in ["today-action-section", "quick-record-section", "recent-record-section"]:
            self.assertIn(token, overview_template)
            self.assertIn(token, source)
        self.assertIn("record-quality", overview_template)

        self.assertIn("analysis-conclusion-card", weekly_template)
        self.assertIn("analysis-conclusion-card", source)
        for label in ["기록 도구", "식단 도구", "운동/장소 도구", "관리 도구"]:
            self.assertIn(label, more_template)
        for selector in ["settings-account-panel", "settings-body-panel", "settings-management-panel", "danger-zone"]:
            self.assertIn(selector, settings_template)
            self.assertIn(selector, source)

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
