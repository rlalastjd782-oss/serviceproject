from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path


from tests.flow_base import FlowTestBase


class H1TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_h1 = False
        self._current: list[str] = []
        self.texts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "h1":
            self._in_h1 = True
            self._current = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "h1" and self._in_h1:
            text = " ".join("".join(self._current).split())
            self.texts.append(text)
            self._in_h1 = False
            self._current = []

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self._current.append(data)


class UiNavigationFlowTest(FlowTestBase):
    def h1_texts(self, html: str) -> list[str]:
        parser = H1TextParser()
        parser.feed(html)
        return parser.texts

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
            "/tools/plate-calculator",
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
                self.assertIn("/static/js/set_builder.js", html)
                self.assertIn("/static/icon.svg", html)
                self.assertIn("/favicon.ico", html)
                for asset in legacy_assets:
                    self.assertNotIn(asset, html)

    def test_mobile_fold_css_contracts_stay_intact(self) -> None:
        styles = "\n".join(path.read_text(encoding="utf-8") for path in sorted(Path("static/css").rglob("*.css")))
        self.assertIn("@media (max-width: 430px)", styles)
        self.assertIn(".tabs {\n    display: grid;", styles)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", styles)
        self.assertIn(".mobile-action-dock {\n    position: static;", styles)
        self.assertIn(".workout-mode .today-mode-actions", styles)
        self.assertIn(".weight-unit-control {\n    grid-template-columns: minmax(0, 1fr) 76px;", styles)
        self.assertIn(".set-row-actions {\n    grid-template-columns: minmax(0, 1fr) 44px;", styles)

    def test_fold_ui_regression_markers_render(self) -> None:
        overview_html = self.client.get("/app").data.decode("utf-8")
        self.assertIn("daily-action-section", overview_html)
        self.assertIn("daily-action-card", overview_html)
        self.assertIn("오늘 운동 기록이 없습니다.", overview_html)
        self.assertIn('href="/app?date=', overview_html)
        self.assertIn("data-quality-card", overview_html)
        self.assertIn("기록 품질", overview_html)
        self.assertIn(">요약</a>", overview_html)
        self.assertNotIn("분석 신뢰도", overview_html)
        self.assertIn("quality-metric-list", overview_html)
        self.assertIn("today-hero-section", overview_html)
        self.assertIn("today-mode-actions", overview_html)
        self.assertNotIn('id="workout-input"', overview_html)

        workout_html = self.client.get("/app?mode=workout").data.decode("utf-8")
        self.assertIn('id="workout-input"', workout_html)
        self.assertIn("오늘 운동 코치", workout_html)
        self.assertIn("운동 시작", workout_html)
        self.assertIn("data-copy-saved-set", workout_html)
        self.assertLess(workout_html.index("workout-coach-section"), workout_html.index("today-task-section"))
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
        self.assertIn(".meal-mode .today-meal-section {\n  order: 10;", styles)
        self.assertIn(".meal-mode .meal-input-section {\n  order: 20;", styles)
        self.assertIn(".meal-mode .meal-tool-section {\n  order: 30;", styles)
        self.assertIn(".meal-mode .meal-goal-section {\n  order: 70;", styles)
        self.assertIn(".meal-mode .optional-section {\n  order: 80;", styles)
        self.assertIn(".today-shell.meal-mode .today-meal-section {\n  order: 10 !important;", styles)
        self.assertIn(".today-shell.meal-mode .meal-tool-section {\n  order: 30 !important;", styles)
        self.assertIn(".today-shell.meal-mode .meal-goal-section {\n  order: 70 !important;", styles)
        self.assertNotIn(".today-shell.meal-mode .meal-goal-section {\n  order: 10 !important;", styles)
        self.assertNotIn(".today-shell.meal-mode .today-meal-section {\n  order: 30 !important;", styles)
        self.assertIn(".focus-mode .workout-secondary-section", styles)
        self.assertIn(".focus-mode .workout-action-dock {\n  grid-template-columns: repeat(5", styles)
        self.assertIn(".workout-action-dock,\n  .mobile-action-dock {\n    top: 122px;", styles)
        self.assertIn("scroll-margin-top: 174px;", styles)
        self.assertIn(".compact-select span {\n  white-space: nowrap;", styles)
        ui_rebuild_source = Path("static/css/overrides/ui_rebuild_04.css").read_text(encoding="utf-8")
        self.assertIn(".today-shell .meal-entry-card.meal-entry-row", ui_rebuild_source)
        self.assertIn("grid-template-columns: minmax(0, 1fr);", ui_rebuild_source)
        self.assertIn("grid-template-columns: minmax(0, 1fr) 42px;", ui_rebuild_source)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", ui_rebuild_source)
        self.assertIn("width: 42px;", ui_rebuild_source)
        self.assertIn("height: 42px;", ui_rebuild_source)

        meal_html = self.client.get("/app?mode=meal").data.decode("utf-8")
        self.assertIn('id="meal-input"', meal_html)
        self.assertIn("식단 상태", meal_html)
        self.assertNotIn("오늘 연료 상태", meal_html)
        self.assertNotIn("연료 상태", meal_html)
        self.assertNotIn("연료 코치", meal_html)
        self.assertIn('id="today-meal"', meal_html)
        self.assertIn("+ 식단 입력", meal_html)
        self.assertIn("식단 도구", meal_html)
        self.assertIn('role="tablist" aria-label="식단 도구"', meal_html)
        self.assertIn('data-meal-tool-tab="combo"', meal_html)
        self.assertIn('data-meal-tool-tab="copy"', meal_html)
        self.assertIn('data-meal-tool-tab="favorite"', meal_html)
        self.assertIn("meal-tool-empty", meal_html)
        self.assertIn("meal-summary-details", meal_html)
        self.assertIn("meal-summary-row", meal_html)
        self.assertIn("자주 먹는 조합 적용", meal_html)
        self.assertIn("템플릿에서 선택", meal_html)
        self.assertIn("아직 저장된 식단이 없습니다.", meal_html)
        self.assertIn("data-toggle-meal-form", meal_html)
        self.assertIn('data-meal-toggle-open-label="입력"', meal_html)
        self.assertIn(">입력</button>", meal_html)
        self.assertNotIn("입력 열기", meal_html)
        self.assertIn('name="meal_type"', meal_html)
        self.assertIn('aria-label="끼니 선택"', meal_html)
        self.assertNotIn('name="meal_input_basis"', meal_html)
        self.assertNotIn("data-meal-input-basis", meal_html)
        self.assertNotIn('aria-label="입력 기준"', meal_html)
        self.assertNotIn("kcal 기준", meal_html)
        self.assertNotIn("g 기준", meal_html)
        self.assertNotIn("개수 기준", meal_html)
        self.assertNotIn("자주 먹는 양", meal_html)
        self.assertIn("meal-entry-card", meal_html)
        self.assertIn("meal-card-head", meal_html)
        self.assertIn("meal-card-fields", meal_html)
        self.assertIn('placeholder="음식 이름"', meal_html)
        self.assertIn('name="meal_quantity"', meal_html)
        self.assertIn('name="meal_grams"', meal_html)
        self.assertIn('name="meal_calories"', meal_html)
        self.assertIn('data-remove-meal-row', meal_html)
        self.assertIn('data-add-meal-row', meal_html)
        self.assertIn('data-meal-quick-tab="recent"', meal_html)
        self.assertIn('data-meal-quick-tab="favorite"', meal_html)
        self.assertIn('data-meal-quick-tab="combo"', meal_html)
        self.assertIn("자주 먹는 음식", meal_html)
        self.assertLess(meal_html.index('id="meal-input"'), meal_html.index("fuel-coach-card"))
        self.assertLess(meal_html.index('name="meal_type"'), meal_html.index("meal-entry-card"))
        self.assertLess(meal_html.index("meal-entry-card"), meal_html.index("data-add-meal-row"))
        self.assertLess(meal_html.index("data-add-meal-row"), meal_html.index("data-food-quick-panel"))
        self.assertLess(meal_html.index("data-food-quick-panel"), meal_html.index("식단 저장"))
        self.assertLess(meal_html.index("meal-entry-card"), meal_html.index("fuel-coach-card"))
        self.assertLess(meal_html.index('data-meal-form'), meal_html.index("fuel-coach-card"))
        self.assertLess(meal_html.index('id="today-meal"'), meal_html.index('id="meal-input"'))
        self.assertLess(meal_html.index("meal-tool-section"), meal_html.index("fuel-coach-card"))
        self.assertLess(meal_html.index("meal-goal-section"), meal_html.index("optional-section"))
        app_boot_source = Path("static/js/app_boot.js").read_text(encoding="utf-8")
        meal_entry_source = Path("static/js/meal_entry.js").read_text(encoding="utf-8")
        meal_css_source = Path("static/css/meal.css").read_text(encoding="utf-8")
        self.assertIn("setMealQuickTab", meal_entry_source)
        self.assertIn("setMealToolTab", meal_entry_source)
        self.assertIn("expandMealToolRows", meal_entry_source)
        self.assertNotIn("입력 열기", app_boot_source)
        self.assertIn('setMealFormToggleLabels(isCollapsed ? "입력" : "입력 닫기")', app_boot_source)
        self.assertIn('setMealFormToggleLabels("입력")', app_boot_source)
        self.assertIn('.meal-form.is-collapsed > :not(input[type="hidden"])', meal_css_source)
        self.assertNotIn(':not(.meal-type-select)', meal_css_source)
        self.assertIn(".meal-tool-row {\n  display: grid;", meal_css_source)
        self.assertIn("grid-template-columns: minmax(0, 1fr) auto;", meal_css_source)
        self.assertIn(".meal-tool-row .meal-tool-action", meal_css_source)
        self.assertIn("meal-entry-card meal-entry-row", Path("static/js/set_builder.js").read_text(encoding="utf-8"))
        self.assertIn('querySelectorAll(".meal-entry-row").length > 1', app_boot_source)
        self.assertIn("renderFoodQuickList(mealTypeSelect.value)", app_boot_source)
        self.assertIn("data-meal-tool-more", app_boot_source)

        search_html = self.client.get("/records/search").data.decode("utf-8")
        self.assertIn("record-filter-details", search_html)
        self.assertIn("<summary>상세 필터</summary>", search_html)
        self.assertIn("record-search-dashboard", search_html)
        self.assertIn("record-result-list", search_html)
        self.assertIn('<option value="10" selected>', search_html)
        self.assertIn("v31-record-search-form", search_html)
        self.assertIn("list-control-row-selects", search_html)
        self.assertIn("list-control-row-actions", search_html)

        daily_html = self.client.get("/summaries/daily").data.decode("utf-8")
        self.assertIn("v31-period-filter-form", daily_html)
        self.assertIn("v31-record-list-toolbar", daily_html)
        self.assertIn("body-part-summary-status", daily_html)
        self.assertLessEqual(daily_html.count('data-body-part-summary="'), 6)
        rebuild_css = Path("static/css/overrides/ui_rebuild_05.css").read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 655px)", rebuild_css)
        self.assertIn(".section .period-filter-form.v31-period-filter-form", rebuild_css)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr)) !important;", rebuild_css)
        self.assertIn(".record-body-part-section .body-part-filter-list", rebuild_css)
        self.assertIn("flex-wrap: wrap !important;", rebuild_css)
        self.assertIn("overflow-x: hidden !important;", rebuild_css)

        weekly_html = self.client.get("/summaries/weekly").data.decode("utf-8")
        self.assertIn("analysis-dashboard-section", weekly_html)
        self.assertIn("주간 분석", weekly_html)
        monthly_html = self.client.get("/summaries/monthly").data.decode("utf-8")
        self.assertIn("analysis-dashboard-section", monthly_html)
        self.assertIn("월간 분석", monthly_html)
        exercises_html = self.client.get("/summaries/exercises").data.decode("utf-8")
        self.assertIn("상위 운동 목록", exercises_html)
        self.assertIn('<option value="5" selected>', exercises_html)
        self.assertLessEqual(exercises_html.count("ex-rank-item"), 5)
        self.assertNotIn("exercise-hero-card", exercises_html)
        pr_html = self.client.get("/summaries/pr").data.decode("utf-8")
        self.assertIn("PR 분석", pr_html)
        self.assertIn('<option value="5" selected>', pr_html)
        self.assertLessEqual(pr_html.count("pr-rank-card"), 5)
        self.assertNotIn("상세 PR", pr_html)
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

        self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-27",
                "mode": "workout",
                "body_part": "가슴",
                "exercise_name": "마법사테스트",
                "set_weight": ["40"],
                "set_reps": ["8"],
                "set_type": ["본세트"],
            },
        )
        self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-28",
                "mode": "workout",
                "body_part": "가슴",
                "exercise_name": "마법사 테스트",
                "set_weight": ["405"],
                "set_reps": ["8"],
                "set_type": ["본세트"],
            },
        )

        record_check_html = self.client.get("/records/check").data.decode("utf-8")
        self.assertIn("기록 점검", record_check_html)
        self.assertIn("정리 마법사 시작", record_check_html)
        self.assertIn("record-gap-list", record_check_html)
        self.assertIn("data-cleanup-grid", record_check_html)
        self.assertIn("cleanup-priority-grid", record_check_html)
        wizard_html = self.client.get("/records/check?wizard=1").data.decode("utf-8")
        self.assertIn("cleanup-wizard-card", wizard_html)
        self.assertIn("한 번에 하나의 문제만 처리합니다.", wizard_html)
        merge_confirm_html = self.client.get("/records/check?wizard=1&confirm=merge").data.decode("utf-8")
        self.assertIn("병합 확인", merge_confirm_html)
        outlier_confirm_html = self.client.get("/records/check?wizard=1&confirm=outlier").data.decode("utf-8")
        self.assertIn("삭제 확인", outlier_confirm_html)

        qa_html = self.client.get("/qa/report").data.decode("utf-8")
        self.assertIn("2.7 릴리스 준비 상태", qa_html)
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
        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "admin", "username": "admin", "password": "1234"},
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            "/settings/app-preferences",
            data={
                "next": "admin",
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
        self.assertIn("/admin", response.headers.get("Location", ""))
        self.client.post("/logout")
        self.client.get("/auth/login?mode=user")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "user", "username": "tester", "password": "1234"},
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

    def test_user_settings_only_keeps_password_and_admin_holds_operations(self) -> None:
        settings_html = self.client.get("/settings").data.decode("utf-8")
        self.assertIn("비밀번호 변경", settings_html)
        self.assertNotIn("앱 기본값", settings_html)
        self.assertNotIn("데이터 관리", settings_html)
        self.assertNotIn("QA 더미데이터", settings_html)
        self.assertNotIn("리마인더", settings_html)
        self.assertNotIn("전체 데이터 삭제", settings_html)

        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "admin", "username": "admin", "password": "1234"},
        )
        self.assertEqual(response.status_code, 302)
        admin_html = self.client.get("/admin").data.decode("utf-8")
        self.assertIn("앱 기본값", admin_html)
        self.assertIn("데이터 관리", admin_html)
        self.assertIn("QA 더미데이터", admin_html)
        self.assertIn("리마인더", admin_html)
        self.assertIn("전체 데이터 삭제", admin_html)

    def test_core_page_query_counts_stay_bounded(self) -> None:
        limits = {
            "/app": 50,
            "/app?mode=workout": 78,
            "/app?mode=meal": 45,
            "/records/search": 12,
            "/more": 30,
            "/locations": 30,
            "/summaries/daily": 45,
            "/summaries/weekly": 30,
            "/summaries/monthly": 50,
            "/summaries/pr": 35,
            "/summaries/equipment": 35,
            "/summaries/exercises": 35,
            "/meals/weekly": 35,
            "/meals/monthly": 45,
        }
        for path, limit in limits.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                query_count = int(response.headers.get("X-DB-Query-Count") or 0)
                self.assertLessEqual(query_count, limit)

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

    def test_analysis_pages_show_current_scope_marker(self) -> None:
        pages = {
            "/summaries/weekly": "주간",
            "/summaries/monthly": "월간",
            "/summaries/yearly": "연간",
            "/summaries/exercises": "운동별",
            "/summaries/pr": "PR",
            "/summaries/equipment": "장비별",
        }
        for path, label in pages.items():
            with self.subTest(path=path):
                html = self.client.get(path).data.decode("utf-8")
                self.assertIn("analysis-subnav", html)
                self.assertIn("analysis-period-strip", html)
                self.assertIn("현재 분석", html)
                self.assertIn(label, html)

    def test_screen_audit_release_blockers_stay_fixed(self) -> None:
        response = self.client.get("/summaries/annual?year=2026")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), "/summaries/yearly?year=2026")
        response = self.client.get("/summaries/annual/?year=2026")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), "/summaries/yearly?year=2026")

        pages = {
            "/app?mode=meal": "오늘 식단",
            "/summaries/daily": "날짜별 기록",
            "/summaries/weekly": "주간 기록",
            "/summaries/monthly": "월간 기록",
            "/summaries/yearly": "연간 기록",
            "/summaries/exercises": "운동별 기록",
            "/summaries/pr": "PR 분석",
            "/summaries/equipment": "장비별 기록",
            "/records/search": "기록 검색",
            "/records/check": "기록 점검",
            "/meals/templates": "식단 템플릿",
            "/calendar": "월간 캘린더",
            "/meals/weekly": "주간 식단",
            "/meals/monthly": "월간 식단",
            "/tools/plate-calculator": "원판 계산기",
            "/settings": "설정",
        }
        for path, title in pages.items():
            with self.subTest(path=path):
                html = self.client.get(path).data.decode("utf-8")
                self.assertEqual(self.h1_texts(html), [title])

    def test_more_page_does_not_duplicate_record_or_analysis_menu(self) -> None:
        html = self.client.get("/more").data.decode("utf-8")
        self.assertIn("운동 관리", html)
        self.assertIn("장소 인사이트", html)
        self.assertIn("데이터 센터", html)
        self.assertNotIn("기록 검색", html)
        self.assertNotIn("장비 분석", html)
        self.assertNotIn(">PR<", html)
