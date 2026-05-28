from __future__ import annotations

from pathlib import Path


from tests.flow_base import FlowTestBase


class UiNavigationFlowTest(FlowTestBase):
    def test_main_pages_render(self) -> None:
        paths = [
            "/app",
            "/summaries/daily",
            "/summaries/weekly",
            "/summaries/monthly",
            "/summaries/yearly",
            "/summaries/yearly/compare",
            "/summaries/exercises",
            "/summaries/equipment",
            "/summaries/pr",
            "/calendar",
            "/meals/weekly",
            "/meals/monthly",
            "/settings",
            "/qa/report",
            "/api/sessions",
            "/records/search",
            "/records/check",
            "/data/center",
            "/locations/insights",
            "/insights/actions",
            "/exercises/library",
            "/meals/templates",
            "/plans/weekly",
            "/more",
            "/locations",
            "/sw.js",
            "/favicon.ico",
        ]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_rendered_pages_use_nested_static_assets(self) -> None:
        auth_pages = [
            "/auth/login?mode=user",
        ]
        app_pages = [
            "/app",
            "/summaries/daily",
            "/meals/weekly",
            "/more",
        ]
        legacy_assets = [
            "/static/styles.css",
            "/static/today.css",
            "/static/feature_pages.css",
            "/static/meal.css",
            "/static/analysis.css",
            "/static/responsive.css",
            "/static/rules.css",
            "/static/ui_rebuild.css",
            "/static/app.js",
            "/static/timers.js",
            "/static/offline_queue.js",
            "/static/workout_tools.js",
            "/static/ui_interactions.js",
            "/static/notifications.js",
            "/static/meal_entry.js",
            "/static/workout_entry.js",
        ]
        public_client = self.app.test_client()
        for page in auth_pages:
            with self.subTest(page=page):
                html = public_client.get(page).data.decode("utf-8")
                self.assertIn("/static/css/styles.css", html)
                self.assertIn("/static/icon.svg", html)
                self.assertIn("/favicon.ico", html)
                for asset in legacy_assets:
                    self.assertNotIn(asset, html)

        for page in app_pages:
            with self.subTest(page=page):
                html = self.client.get(page).data.decode("utf-8")
                self.assertIn("/static/css/styles.css", html)
                self.assertIn("/static/icon.svg", html)
                self.assertIn("/favicon.ico", html)
                for asset in legacy_assets:
                    self.assertNotIn(asset, html)

    def test_fold_ui_regression_markers_render(self) -> None:
        overview_html = self.client.get("/app").data.decode("utf-8")
        self.assertIn("data-quality-card", overview_html)
        self.assertIn("분석 신뢰도", overview_html)
        self.assertIn("quality-metric-list", overview_html)
        self.assertIn("today-hero-section", overview_html)
        self.assertIn("today-mode-actions", overview_html)

        workout_html = self.client.get("/app?mode=workout").data.decode("utf-8")
        self.assertIn("data-workout-quick-tab=\"recent\"", workout_html)
        self.assertIn("data-workout-quick-tab=\"favorite\"", workout_html)
        self.assertIn("data-workout-quick-tab=\"routine\"", workout_html)
        self.assertIn("set-advanced-options", workout_html)
        self.assertIn("data-readiness-coach", workout_html)
        self.assertIn("id=\"routine-library\"", workout_html)
        response = self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-26",
                "mode": "workout",
                "body_part": "가슴",
                "exercise_name": "__TEST__ timer",
                "set_weight": ["40"],
                "set_reps": ["8"],
                "set_type": ["본세트"],
            },
        )
        self.assertNotIn("rest=", response.headers.get("Location", ""))
        workout_html = self.client.get("/app?date=2026-05-26&mode=workout").data.decode("utf-8")
        self.assertLess(workout_html.index("workout-clock-section"), workout_html.index('id="rest-timer"'))
        self.assertLess(workout_html.index('id="rest-timer"'), workout_html.index("workout-action-dock"))
        self.assertIn("data-workout-complete-form", workout_html)
        focus_html = self.client.get("/app?date=2026-05-26&mode=workout&focus=1").data.decode("utf-8")
        self.assertIn("focus-mode", focus_html)
        self.assertIn("focus-mode-button", focus_html)
        self.assertIn('href="#workout-finish"', focus_html)
        timer_source = Path("static/js/timers.js").read_text(encoding="utf-8")
        form_submit_source = Path("static/js/form_submit.js").read_text(encoding="utf-8")
        self.assertIn("resetWorkoutClockDisplayOnly", timer_source)
        self.assertIn("completedReset", timer_source)
        self.assertIn(r"/\/sessions\/\d+\/complete$/.test", form_submit_source)
        self.assertIn("rest-start-button", workout_html)
        self.assertIn(">타이머 시작</button>", workout_html)
        self.assertNotIn("초 휴식</button>", workout_html)
        styles = "\n".join(path.read_text(encoding="utf-8") for path in sorted(Path("static/css").rglob("*.css")))
        self.assertIn(".workout-mode #rest-timer {\n  order: 11;", styles)
        self.assertIn(".workout-mode .workout-action-dock {\n  order: 12;", styles)
        self.assertIn(".focus-mode .workout-secondary-section", styles)
        self.assertIn(".focus-mode .workout-action-dock {\n  grid-template-columns: repeat(5", styles)
        self.assertIn(".workout-action-dock,\n  .mobile-action-dock {\n    top: 122px;", styles)
        self.assertIn("scroll-margin-top: 174px;", styles)

        search_html = self.client.get("/records/search").data.decode("utf-8")
        self.assertIn("record-filter-details", search_html)
        self.assertIn("<summary>상세 필터</summary>", search_html)
        self.assertIn("record-search-dashboard", search_html)
        self.assertIn("record-result-list", search_html)
        self.assertIn('<option value="10" selected>', search_html)

        weekly_html = self.client.get("/summaries/weekly").data.decode("utf-8")
        self.assertIn("analysis-dashboard-section", weekly_html)
        self.assertIn("주간 분석", weekly_html)
        monthly_html = self.client.get("/summaries/monthly").data.decode("utf-8")
        self.assertIn("analysis-dashboard-section", monthly_html)
        self.assertIn("월간 분석", monthly_html)
        pr_html = self.client.get("/summaries/pr").data.decode("utf-8")
        self.assertIn("PR 분석", pr_html)
        equipment_html = self.client.get("/summaries/equipment").data.decode("utf-8")
        self.assertIn("장비 분석", equipment_html)

        locations_html = self.client.get("/locations").data.decode("utf-8")
        self.assertIn("location-overview-grid", locations_html)
        self.assertIn("location-create-panel", locations_html)
        self.assertIn("location-form-actions", locations_html)
        self.assertIn("location-card-main", locations_html)
        self.assertIn("location-manage-details", locations_html)
        self.assertIn("location-equipment-chip-list", locations_html)
        self.assertIn("location-equipment-panel", locations_html)

        location_insights_html = self.client.get("/locations/insights").data.decode("utf-8")
        self.assertIn("location-insight-list", location_insights_html)

        record_check_html = self.client.get("/records/check").data.decode("utf-8")
        self.assertIn("기록 점검", record_check_html)
        self.assertIn("record-gap-list", record_check_html)
        self.assertIn("정리 후보", record_check_html)
        self.assertIn("data-cleanup-grid", record_check_html)

        qa_html = self.client.get("/qa/report").data.decode("utf-8")
        self.assertIn("2.0 준비 상태", qa_html)
        self.assertIn("readiness-grid", qa_html)

        meal_templates_html = self.client.get("/meals/templates").data.decode("utf-8")
        self.assertIn("식단 템플릿", meal_templates_html)
        self.assertIn("meal-template-grid", meal_templates_html)

        data_center_html = self.client.get("/data/center").data.decode("utf-8")
        self.assertIn("data-center-grid", data_center_html)
        self.assertIn("export-link-grid", data_center_html)

        action_insights_html = self.client.get("/insights/actions").data.decode("utf-8")
        self.assertIn("실행 인사이트", action_insights_html)
        self.assertIn("data-warning-list", action_insights_html)

    def test_app_preferences_drive_workout_defaults(self) -> None:
        response = self.client.post(
            "/settings/app-preferences",
            data={
                "default_rest_seconds": "150",
                "rest_timer_presets": "45, 75, 105",
                "default_set_count": "4",
                "default_weight_placeholder": "72.5",
                "default_reps_placeholder": "11",
                "default_daily_calories": "2550",
                "default_body_weight_kg": "82.5",
                "default_per_page": "20",
                "summary_day_options": "14, 28, 56",
                "set_type_options": "본세트\n탑세트\n백오프",
            },
        )
        self.assertEqual(response.status_code, 302)
        html = self.client.get("/app?mode=workout").data.decode("utf-8")
        self.assertIn('data-rest-seconds="45"', html)
        self.assertIn('data-rest-seconds="75"', html)
        self.assertIn('value="4" inputmode="numeric" data-set-count-input', html)
        self.assertIn('placeholder="72.5"', html)
        self.assertIn('placeholder="11"', html)
        self.assertIn('<option value="탑세트">탑세트</option>', html)
        self.assertIn('"default_daily_calories": 2550', html)
        daily_html = self.client.get("/summaries/daily").data.decode("utf-8")
        self.assertIn('name="days" value="28"', daily_html)
        self.assertIn('<option value="20" selected>', daily_html)
        check_html = self.client.get("/records/check").data.decode("utf-8")
        self.assertIn('<option value="28"', check_html)

    def test_record_and_analysis_submenus_are_separated(self) -> None:
        daily_html = self.client.get("/summaries/daily").data.decode("utf-8")
        self.assertIn("record-subnav", daily_html)
        self.assertNotIn("analysis-subnav", daily_html)
        search_html = self.client.get("/records/search").data.decode("utf-8")
        self.assertIn("record-subnav", search_html)
        self.assertNotIn("analysis-subnav", search_html)
        weekly_html = self.client.get("/summaries/weekly").data.decode("utf-8")
        self.assertIn("analysis-subnav", weekly_html)
        self.assertNotIn("record-subnav", weekly_html)
        pr_html = self.client.get("/summaries/pr").data.decode("utf-8")
        self.assertIn("analysis-subnav", pr_html)
        self.assertNotIn("record-subnav", pr_html)
        self.assertIn('href="/summaries/equipment"', pr_html)

    def test_more_page_does_not_duplicate_record_or_analysis_menu(self) -> None:
        html = self.client.get("/more").data.decode("utf-8")
        self.assertIn("운동 관리", html)
        self.assertIn("장소 인사이트", html)
        self.assertIn("데이터 센터", html)
        self.assertNotIn("기록 검색", html)
        self.assertNotIn("장비 분석", html)
        self.assertNotIn(">PR<", html)
