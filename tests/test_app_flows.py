from __future__ import annotations

import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

import app as app_module


TEST_TMP_DIR = Path(__file__).resolve().parents[1] / ".test-tmp"


class HealthTrackerFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        TEST_TMP_DIR.mkdir(exist_ok=True)
        self.tmpdir = tempfile.TemporaryDirectory(dir=TEST_TMP_DIR)
        self.original_database = app_module.DATABASE
        app_module.DATABASE = Path(self.tmpdir.name) / "test-workout.db"
        self.app = app_module.app
        self.client = self.app.test_client()
        self.raw_post = self.client.post
        self.client.post = self._post_with_csrf
        self.client.get("/auth/login?mode=user")
        response = self.client.post(
            "/signup",
            data={"username": "tester", "password": "1234", "password_confirm": "1234"},
        )
        self.assertEqual(response.status_code, 302)

    def tearDown(self) -> None:
        app_module.DATABASE = self.original_database
        self.tmpdir.cleanup()

    def _csrf_token(self, client=None) -> str:
        target_client = client or self.client
        with target_client.session_transaction() as sess:
            return str(sess.get("csrf_token", ""))

    def _post_with_csrf(self, *args, **kwargs):
        headers = dict(kwargs.pop("headers", {}) or {})
        token = self._csrf_token(self.client)
        if kwargs.get("json") is not None:
            headers["X-CSRF-Token"] = token
            kwargs["headers"] = headers
            return self.raw_post(*args, **kwargs)
        data = kwargs.pop("data", None)
        if data is None:
            data = {}
        if isinstance(data, dict):
            data = {**data, "csrf_token": token}
        kwargs["data"] = data
        kwargs["headers"] = headers
        return self.raw_post(*args, **kwargs)

    def _visitor_post(self, client, path: str, data: dict[str, object] | None = None):
        payload = dict(data or {})
        payload["csrf_token"] = self._csrf_token(client)
        return client.post(path, data=payload)

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
        ]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

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
        timer_source = Path("static/timers.js").read_text(encoding="utf-8")
        app_source = Path("static/app.js").read_text(encoding="utf-8")
        self.assertIn("resetWorkoutClockDisplayOnly", timer_source)
        self.assertIn("completedReset", timer_source)
        self.assertIn(r"/\/sessions\/\d+\/complete$/.test", app_source)
        self.assertIn("rest-start-button", workout_html)
        self.assertIn(">타이머 시작</button>", workout_html)
        self.assertNotIn("초 휴식</button>", workout_html)
        styles = (
            Path("static/styles.css").read_text(encoding="utf-8")
            + "\n"
            + Path("static/today.css").read_text(encoding="utf-8")
            + "\n"
            + Path("static/feature_pages.css").read_text(encoding="utf-8")
            + "\n"
            + Path("static/analysis.css").read_text(encoding="utf-8")
            + "\n"
            + Path("static/responsive.css").read_text(encoding="utf-8")
        )
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

    def test_locations_manage_equipment_and_filter_records(self) -> None:
        self.client.post(
            "/locations",
            data={"name": "DELETE-LOCATION", "address": "", "memo": ""},
        )
        db = sqlite3.connect(app_module.DATABASE)
        try:
            delete_location_id = db.execute(
                "SELECT id FROM workout_locations WHERE name = ?",
                ("DELETE-LOCATION",),
            ).fetchone()[0]
        finally:
            db.close()
        self.client.post(f"/locations/{delete_location_id}/remove")
        db = sqlite3.connect(app_module.DATABASE)
        try:
            deleted_location = db.execute(
                "SELECT id FROM workout_locations WHERE id = ?",
                (delete_location_id,),
            ).fetchone()
        finally:
            db.close()
        self.assertIsNone(deleted_location)

        response = self.client.post(
            "/locations",
            data={
                "name": "테스트 헬스장",
                "address": "강남",
                "memo": "스미스 머신 있음",
                "is_default": "1",
            },
        )
        self.assertEqual(response.status_code, 302)

        db = sqlite3.connect(app_module.DATABASE)
        try:
            db.row_factory = sqlite3.Row
            location = db.execute("SELECT * FROM workout_locations WHERE name = ?", ("테스트 헬스장",)).fetchone()
        finally:
            db.close()
        self.assertIsNotNone(location)
        location_id = int(location["id"])

        self.client.post(
            f"/locations/{location_id}/equipment",
            data={"equipment_name": "스미스 머신", "equipment_type": "플레이트로디드머신", "memo": "하체 가능"},
        )
        workout_html = self.client.get(f"/app?mode=workout&location_id={location_id}").data.decode("utf-8")
        self.assertIn("운동 장소", workout_html)
        self.assertIn('<option value="핀머신">핀머신</option>', workout_html)
        self.assertIn('<option value="플레이트로디드머신">플레이트로디드머신</option>', workout_html)
        self.assertIn('<option value="프리웨이트">프리웨이트</option>', workout_html)
        self.assertIn('<option value="덤벨">덤벨</option>', workout_html)
        self.assertIn('<option value="케이블">케이블</option>', workout_html)
        self.assertNotIn('<option value="스미스 머신">스미스 머신</option>', workout_html)

        self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-26",
                "mode": "workout",
                "location_id": str(location_id),
                "body_part": "하체",
                "exercise_name": "장소 테스트 스쿼트",
                "equipment": "스미스 머신",
                "set_weight": ["60"],
                "set_reps": ["8"],
                "set_type": ["본세트"],
            },
        )
        other_location_response = self.client.post(
            "/locations",
            data={"name": "다른장소", "address": "", "memo": ""},
        )
        self.assertEqual(other_location_response.status_code, 302)
        with self.app.app_context():
            other_location = app_module.get_db().execute(
                "SELECT id FROM workout_locations WHERE name = ?",
                ("다른장소",),
            ).fetchone()
            other_location_id = int(other_location["id"])
        self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-27",
                "mode": "workout",
                "location_id": str(other_location_id),
                "body_part": "가슴",
                "exercise_name": "다른장소 전용운동",
                "equipment": "덤벨",
                "set_weight": ["20"],
                "set_reps": ["10"],
                "set_type": ["본세트"],
            },
        )
        scoped_workout_html = self.client.get(f"/app?date=2026-05-26&mode=workout&location_id={location_id}").data.decode("utf-8")
        self.assertIn("장소 테스트 스쿼트", scoped_workout_html)
        self.assertNotIn('<option value="다른장소 전용운동">', scoped_workout_html)
        self.assertNotIn('data-exercise-name="다른장소 전용운동"', scoped_workout_html)

        search_html = self.client.get(
            "/records/search",
            query_string={
                "q": "장소 테스트",
                "location_id": str(location_id),
                "start": "2026-05-26",
                "end": "2026-05-26",
            },
        ).data.decode("utf-8")
        self.assertIn("테스트 헬스장", search_html)
        self.assertIn("플레이트로디드머신", search_html)

    def test_visitor_is_read_only_and_admin_routes_are_locked(self) -> None:
        visitor = self.app.test_client()
        response = visitor.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers.get("Location", ""))

        response = visitor.get("/app?mode=workout")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers.get("Location", ""))
        self.assertIn("next=", response.headers.get("Location", ""))

        visitor.get("/app")
        response = self._visitor_post(
            visitor,
            "/sets",
            {
                "workout_date": "2026-05-20",
                "body_part": "가슴",
                "exercise_name": "__TEST__ blocked",
                "set_weight": ["80"],
                "set_reps": ["10"],
            },
        )
        self.assertEqual(response.status_code, 403)

        response = visitor.get("/export.json")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers.get("Location", ""))

        response = self.raw_post(
            "/sets",
            data={
                "workout_date": "2026-05-20",
                "body_part": "가슴",
                "exercise_name": "__TEST__ csrf",
                "set_weight": ["80"],
                "set_reps": ["10"],
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_settings_password_lock_unlock_and_reset(self) -> None:
        response = self.client.get("/settings")
        self.assertEqual(response.status_code, 200)
        self.assertIn("settings-overview-section", response.data.decode("utf-8"))
        self.client.post("/logout")
        response = self.client.get("/settings")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers.get("Location", ""))
        self.client.get("/auth/login?mode=admin")
        response = self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        self.assertIn("/admin", response.headers.get("Location", ""))
        response = self.client.get("/settings")
        self.assertIn("/admin", response.headers.get("Location", ""))

    def test_two_accounts_use_separate_data_stores(self) -> None:
        response = self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-26",
                "mode": "workout",
                "body_part": "가슴",
                "exercise_name": "__TEST__ ADMIN ONLY",
                "equipment": "덤벨",
                "set_weight": ["30"],
                "set_reps": ["10"],
                "set_type": ["본세트"],
            },
        )
        self.assertEqual(response.status_code, 302)

        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        response = self.client.post(
            "/settings/accounts",
            data={
                "username": "partner",
                "display_name": "파트너",
                "password": "5678",
                "role": "user",
            },
        )
        self.assertEqual(response.status_code, 302)
        admin_html = self.client.get("/admin").data.decode("utf-8")
        self.assertIn("partner", admin_html)

        response = self.client.post("/logout")
        self.assertEqual(response.status_code, 302)
        self.client.get("/auth/login")
        response = self.client.post("/auth/login", data={"username": "partner", "password": "5678"})
        self.assertEqual(response.status_code, 302)

        partner_html = self.client.get("/app?mode=workout").data.decode("utf-8")
        self.assertIn("파트너", partner_html)
        self.assertNotIn("__TEST__ ADMIN ONLY", partner_html)

        response = self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-26",
                "mode": "workout",
                "body_part": "등",
                "exercise_name": "__TEST__ PARTNER ONLY",
                "equipment": "케이블",
                "set_weight": ["25"],
                "set_reps": ["12"],
                "set_type": ["본세트"],
            },
        )
        self.assertEqual(response.status_code, 302)
        partner_html = self.client.get("/app?date=2026-05-26&mode=workout").data.decode("utf-8")
        self.assertIn("__TEST__ PARTNER ONLY", partner_html)
        self.assertNotIn("__TEST__ ADMIN ONLY", partner_html)

        self.client.post("/logout")
        self.client.get("/auth/login")
        response = self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        self.assertEqual(response.status_code, 302)
        response = self.client.get("/app?date=2026-05-26&mode=workout")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin", response.headers.get("Location", ""))
        self.assertTrue((Path(self.tmpdir.name) / "accounts.db").exists())
        self.assertTrue((Path(self.tmpdir.name) / "accounts" / "user_3.db").exists())

    def test_login_tabs_signup_and_role_boundaries(self) -> None:
        self.client.post("/logout")
        html = self.client.get("/auth/login?mode=admin").data.decode("utf-8")
        self.assertIn("관리자 로그인", html)
        self.assertIn('name="csrf_token"', html)
        self.assertNotIn("<strong>회원가입</strong>", html)
        self.assertNotIn("href=\"/auth/signup", html)
        self.assertIn("서버 관리자에게 문의", html)
        html = self.client.get("/auth/login?mode=user").data.decode("utf-8")
        self.assertIn("사용자 로그인", html)
        self.assertIn("회원가입", html)
        self.assertIn("관리자에게 초기화", html)
        self.assertNotIn("사용자 회원가입</strong>", html)
        self.assertIn("미리보기", html)

        signup_html = self.client.get("/auth/signup").data.decode("utf-8")
        self.assertIn("사용자 회원가입", signup_html)
        self.assertIn("로그인으로 돌아가기", signup_html)
        self.assertIn("미리보기 보기", signup_html)

        response = self.client.post("/auth/signup", data={"username": "member_1", "password": "abcd", "password_confirm": "abcd"})
        self.assertEqual(response.status_code, 302)
        html = self.client.get("/app?mode=workout").data.decode("utf-8")
        self.assertIn("member_1", html)

        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "admin", "username": "member_1", "password": "abcd"},
        )
        self.assertIn("not_admin", response.headers.get("Location", ""))

        self.client.get("/auth/login?mode=user")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "user", "username": "admin", "password": "1234"},
        )
        self.assertIn("not_user", response.headers.get("Location", ""))

        self.client.get("/auth/login?mode=admin")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "admin", "username": "admin", "password": "1234"},
        )
        self.assertIn("/admin", response.headers.get("Location", ""))
        response = self.client.get("/app")
        self.assertIn("/admin", response.headers.get("Location", ""))

    def test_auth_preview_is_public_sample_only(self) -> None:
        self.client.post("/logout")
        response = self.client.get("/auth/preview")
        self.assertRegex(response.headers.get("X-Request-Duration-ms", ""), r"^\d+\.\d$")
        self.assertRegex(response.headers.get("X-DB-Query-Count", ""), r"^\d+$")
        self.assertIn("app;dur=", response.headers.get("Server-Timing", ""))
        html = response.data.decode("utf-8")
        self.assertIn("가입 전 미리보기", html)
        self.assertIn("운동 기록, 분석, 장소 관리를", html)
        self.assertIn("/auth/login", html)
        self.assertIn("/auth/signup", html)
        self.assertIn("랫풀다운", html)
        self.assertIn("아파트 헬스장", html)
        self.assertNotIn("<form", html)
        self.assertNotIn("__TEST__", html)
        self.assertNotIn("사용자 현황", html)

    def test_admin_can_change_own_password_and_settings_password_hash(self) -> None:
        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})

        dashboard_html = self.client.get("/admin").data.decode("utf-8")
        self.assertIn("관리자 비밀번호 변경", dashboard_html)

        response = self.client.post(
            "/admin/password",
            data={
                "current_password": "wrong",
                "new_password": "9999",
                "new_password_confirm": "9999",
            },
        )
        self.assertIn("error=password", response.headers.get("Location", ""))

        response = self.client.post(
            "/admin/password",
            data={
                "current_password": "1234",
                "new_password": "9999",
                "new_password_confirm": "9999",
            },
        )
        self.assertIn("updated=password", response.headers.get("Location", ""))

        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        response = self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        self.assertIn("invalid", response.headers.get("Location", ""))

        self.client.get("/auth/login?mode=admin")
        response = self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "9999"})
        self.assertIn("/admin", response.headers.get("Location", ""))
        with self.app.app_context():
            self.assertTrue(app_module.verify_settings_password("9999"))

    def test_admin_dashboard_reports_user_usage_and_blocks_users(self) -> None:
        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        self.client.post(
            "/settings/accounts",
            data={"username": "reportuser", "display_name": "리포트사용자", "password": "5678", "role": "user"},
        )
        self.client.post("/logout")
        self.client.get("/auth/login")
        self.client.post("/auth/login", data={"login_mode": "user", "username": "reportuser", "password": "5678"})
        response = self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-26",
                "mode": "workout",
                "body_part": "등",
                "exercise_name": "__TEST__ USER REPORT",
                "equipment": "케이블",
                "set_weight": ["25"],
                "set_reps": ["12"],
                "set_type": ["본세트"],
            },
        )
        self.assertEqual(response.status_code, 302)
        user_html = self.client.get("/app?mode=workout").data.decode("utf-8")
        self.assertIn("admin-mode", user_html)
        self.assertIn("header-meta", user_html)
        self.assertIn("account-greeting", user_html)
        self.assertIn("app-version", user_html)
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 302)
        self.assertIn("mode=admin", response.headers.get("Location", ""))

        self.client.post("/logout")
        self.client.get("/auth/login")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        admin_html = self.client.get("/admin").data.decode("utf-8")
        self.assertIn("관리자 대시보드", admin_html)
        self.assertIn("사용자 계정", admin_html)
        self.assertIn("운영 체크포인트", admin_html)
        self.assertIn("사용자 검색", admin_html)
        self.assertIn("조치 필요 사용자", admin_html)
        self.assertIn("관리자 활동 로그", admin_html)
        self.assertNotIn("admin · admin", admin_html)
        self.assertIn("리포트사용자", admin_html)
        self.assertIn("세트 1개", admin_html)
        filtered_html = self.client.get("/admin?q=reportuser&status=active&sort=sets").data.decode("utf-8")
        self.assertIn("reportuser", filtered_html)
        response = self.client.get("/admin/users/1")
        self.assertEqual(response.status_code, 302)
        self.assertIn("user_only", response.headers.get("Location", ""))
        detail_html = self.client.get("/admin/users/3").data.decode("utf-8")
        self.assertIn("__TEST__ USER REPORT", detail_html)
        self.assertIn("케이블", detail_html)
        self.assertIn("데이터 내보내기", detail_html)
        export_response = self.client.get("/admin/users/3/export")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("application/json", export_response.content_type)
        self.assertIn("__TEST__ USER REPORT", export_response.data.decode("utf-8"))

    def test_admin_can_manage_user_account_status_password_and_memo(self) -> None:
        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        self.client.post(
            "/settings/accounts",
            data={"username": "managed", "display_name": "관리대상", "password": "1111", "role": "user"},
        )
        detail_html = self.client.get("/admin/users/3").data.decode("utf-8")
        self.assertIn("계정 운영", detail_html)

        response = self.client.post(
            "/admin/users/3/memo",
            data={"display_name": "관리대상수정", "memo": "테스트 메모"},
        )
        self.assertEqual(response.status_code, 302)
        detail_html = self.client.get("/admin/users/3").data.decode("utf-8")
        self.assertIn("관리대상수정", detail_html)
        self.assertIn("테스트 메모", detail_html)
        self.assertIn("user_memo_update", detail_html)

        response = self.client.post("/admin/users/3/password", data={"password": "2222"})
        self.assertEqual(response.status_code, 302)
        self.client.post("/logout")
        self.client.get("/auth/login")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "user", "username": "managed", "password": "2222"},
        )
        self.assertEqual(response.status_code, 302)

        self.client.post("/logout")
        self.client.get("/auth/login")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        response = self.client.post(
            "/admin/users/3/status",
            data={"action": "disable", "confirm_status": "비활성화"},
        )
        self.assertEqual(response.status_code, 302)
        self.client.post("/logout")
        self.client.get("/auth/login")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "user", "username": "managed", "password": "2222"},
        )
        self.assertIn("invalid", response.headers.get("Location", ""))

        self.client.get("/auth/login")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        response = self.client.post("/admin/users/3/status", data={"action": "enable"})
        self.assertEqual(response.status_code, 302)
        self.client.post("/logout")
        self.client.get("/auth/login")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "user", "username": "managed", "password": "2222"},
        )
        self.assertEqual(response.status_code, 302)

    def test_yearly_qa_dummy_data_crosses_year_boundary(self) -> None:
        response = self.client.post("/qa-dummy/year")
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            status = app_module.get_qa_dummy_status()
            self.assertTrue(status["exists"])
            self.assertGreaterEqual(status["exercises"], 100)
            self.assertGreaterEqual(status["sets"], 3000)
            self.assertGreaterEqual(status["meals"], 1400)
            self.assertGreaterEqual(status["body_metrics"], 50)
            self.assertGreaterEqual(status["recovery"], 360)

        for path in [
            "/summaries/yearly?year=2025",
            "/summaries/yearly?year=2026",
            "/summaries/yearly/compare?base_year=2025&compare_year=2026",
            "/summaries/monthly?month=2025-12",
            "/summaries/monthly?month=2026-01",
            "/records/search?start=2025-12-31&end=2026-01-01&q=QA-",
        ]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn("QA-", response.data.decode("utf-8", errors="ignore"))

        response = self.client.get("/export/yearly.json?year=2026")
        self.assertEqual(response.status_code, 200)
        self.assertIn('"year": "2026"', response.data.decode("utf-8"))
        response = self.client.get("/export/yearly-workouts.csv?year=2026")
        self.assertEqual(response.status_code, 200)
        self.assertIn("QA-", response.data.decode("utf-8-sig"))

    def test_service_worker_precache_assets_are_valid(self) -> None:
        sw_path = Path(__file__).resolve().parents[1] / "static" / "sw.js"
        sw_source = sw_path.read_text(encoding="utf-8")
        assets_match = re.search(r"const ASSETS = \[(.*?)\];", sw_source, re.S)
        self.assertIsNotNone(assets_match)
        assets = re.findall(r'"([^"]+)"', assets_match.group(1))
        self.assertNotIn("/app", assets)
        self.assertNotIn("/app?mode=workout", assets)
        self.assertNotIn("/app?mode=meal", assets)
        self.assertIn("/calendar", assets)
        self.assertIn("/meals/weekly", assets)
        self.assertIn("/summaries/exercises", assets)
        self.assertIn("/summaries/yearly", assets)
        self.assertIn("/static/ui_rebuild.css", assets)
        self.assertIn("/sw.js", assets)
        self.assertIn("self.skipWaiting()", sw_source)
        self.assertIn("self.clients.claim()", sw_source)
        self.assertIn("offlineFallback", sw_source)

        for asset in assets:
            with self.subTest(asset=asset):
                response = self.client.get(asset)
                self.assertEqual(response.status_code, 200)
                response.close()

        response = self.client.get("/sw.js")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Service-Worker-Allowed"), "/")
        expected_version = Path("VERSION").read_text(encoding="utf-8").strip()
        self.assertIn(f"workout-pwa-v{expected_version}", response.data.decode("utf-8"))

    def test_lb_weights_are_saved_as_kg_and_set_builder_ui_exists(self) -> None:
        html = self.client.get("/app?mode=workout").data.decode("utf-8")
        self.assertIn("data-set-count-input", html)
        self.assertIn("data-set-count-preset=\"5\"", html)
        self.assertIn("name=\"set_weight_unit\"", html)
        self.assertIn("data-weight-preview", html)
        self.assertIn("set-row-number", html)

        response = self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-21",
                "mode": "workout",
                "body_part": "가슴",
                "exercise_name": "__TEST__ LB Bench",
                "set_weight": ["135", "155", "155"],
                "set_weight_unit": ["lb", "lb", "lb"],
                "set_reps": ["10", "8", "8"],
                "set_type": ["본세트", "본세트", "본세트"],
            },
        )
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            rows = app_module.get_db().execute(
                """
                SELECT ws.weight, ws.reps
                FROM workout_sets ws
                JOIN exercises e ON e.id = ws.exercise_id
                WHERE e.name = ?
                ORDER BY ws.id
                """,
                ("__TEST__ LB Bench",),
            ).fetchall()
            self.assertEqual(len(rows), 3)
            self.assertAlmostEqual(rows[0]["weight"], 61.23, places=2)
            self.assertAlmostEqual(rows[1]["weight"], 70.31, places=2)
            self.assertEqual(rows[2]["reps"], 8)

    def test_workout_cardio_meal_flow(self) -> None:
        default_workout_html = self.client.get("/app?mode=workout").data.decode("utf-8")
        self.assertIn('<option value="프리웨이트">프리웨이트</option>', default_workout_html)

        workout_date = "2026-05-26"
        strength_name = "__TEST__ 벤치"
        cardio_name = "__TEST__ 러닝"

        response = self.client.post(
            "/sets",
            data={
                "workout_date": workout_date,
                "mode": "workout",
                "body_part": "가슴",
                "exercise_name": strength_name,
                "equipment": "바벨",
                "set_weight": ["80", "85"],
                "set_reps": ["10", "8"],
                "set_type": ["본세트", "본세트"],
                "set_rpe": ["7", "8"],
            },
        )
        self.assertEqual(response.status_code, 302)

        response = self.client.post(
            "/sets",
            data={
                "workout_date": workout_date,
                "mode": "workout",
                "body_part": "유산소",
                "exercise_name": cardio_name,
                "equipment": "런닝머신",
                "cardio_incline": ["5"],
                "cardio_speed": ["6.2"],
                "cardio_minutes": ["30"],
                "set_rpe": ["6"],
            },
        )
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            db = app_module.get_db()
            rows = db.execute(
                """
                SELECT ws.*, e.name AS exercise_name
                FROM workout_sets ws
                JOIN exercises e ON e.id = ws.exercise_id
                ORDER BY ws.id
                """
            ).fetchall()
            strength = [row for row in rows if row["exercise_name"] == strength_name]
            cardio = [row for row in rows if row["exercise_name"] == cardio_name]
            self.assertEqual(len(strength), 2)
            self.assertEqual(strength[0]["weight"], 80)
            self.assertEqual(strength[0]["reps"], 10)
            self.assertEqual(len(cardio), 1)
            self.assertIsNone(cardio[0]["weight"])
            self.assertIsNone(cardio[0]["reps"])
            self.assertEqual(cardio[0]["cardio_minutes"], 30)
            set_id = strength[0]["id"]
            cardio_id = cardio[0]["id"]
            session_id = rows[0]["session_id"]

        response = self.client.post(
            f"/sets/{set_id}/update",
            data={
                "mode": "workout",
                "weight": "82.5",
                "reps": "11",
                "set_type": "본세트",
                "rpe": "8.5",
                "equipment": "바벨",
                "set_number": "2",
            },
        )
        self.assertEqual(response.status_code, 302)

        response = self.client.post(
            f"/sets/{cardio_id}/update",
            data={
                "mode": "workout",
                "cardio_incline": "6",
                "cardio_speed": "6.5",
                "cardio_minutes": "31",
                "rpe": "6.5",
                "equipment": "런닝머신",
            },
        )
        self.assertEqual(response.status_code, 302)

        response = self.client.post(f"/sessions/{session_id}/duration", json={"duration_seconds": 3661})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["duration_seconds"], 3661)

        response = self.client.post(
            "/meals",
            data={
                "meal_date": workout_date,
                "mode": "meal",
                "meal_type": "점심",
                "meal_food_name": ["__TEST__ 닭가슴살", "__TEST__ 고구마"],
                "meal_quantity": ["1", "2"],
                "meal_grams": ["150", "200"],
                "meal_calories": ["180", "260"],
            },
        )
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            db = app_module.get_db()
            changed = db.execute("SELECT * FROM workout_sets WHERE id = ?", (set_id,)).fetchone()
            changed_cardio = db.execute("SELECT * FROM workout_sets WHERE id = ?", (cardio_id,)).fetchone()
            meals = db.execute("SELECT * FROM meal_entries ORDER BY id").fetchall()
            favorite_count = db.execute("SELECT COUNT(*) FROM food_favorites").fetchone()[0]
            self.assertEqual(changed["weight"], 82.5)
            self.assertEqual(changed["reps"], 11)
            self.assertEqual(changed_cardio["cardio_minutes"], 31)
            self.assertEqual(len(meals), 2)
            self.assertEqual(meals[0]["calories"], 180)
            self.assertEqual(favorite_count, 0)

        response = self.client.get(f"/app?date={workout_date}&mode=meal")
        meal_html = response.data.decode("utf-8")
        self.assertIn("meal-record-card", meal_html)
        self.assertIn("meal-record-item", meal_html)
        self.assertIn("최근 입력 음식", meal_html)

        response = self.client.post(
            "/food-favorites",
            data={
                "meal_date": workout_date,
                "food_name": "__TEST__ 고정음식",
                "quantity": "1",
                "grams": "120",
                "calories": "220",
            },
        )
        self.assertEqual(response.status_code, 302)
        meal_html = self.client.get(f"/app?date={workout_date}&mode=meal").data.decode("utf-8")
        self.assertIn("고정 음식", meal_html)
        self.assertIn("meal-favorite-row", meal_html)
        self.assertIn("__TEST__ 고정음식", meal_html)

        response = self.client.get(f"/app?date={workout_date}&mode=workout")
        html = response.data.decode("utf-8")
        self.assertIn('list="exercise-list"', html)
        self.assertIn(f'value="{strength_name}"', html)
        self.assertIn(f'value="{cardio_name}"', html)
        self.assertIn('class="set-row-actions"', html)
        self.assertIn("finish-review-card", html)
        self.assertIn("운동 완료 리뷰", html)

        response = self.client.post(
            f"/sessions/{session_id}/complete",
            data={"mode": "workout", "completed": "1"},
        )
        self.assertEqual(response.status_code, 302)
        completed_html = self.client.get(f"/app?date={workout_date}&mode=workout").data.decode("utf-8")
        self.assertIn("완료된 기록 기준", completed_html)
        self.assertIn("다음 행동", completed_html)

        response = self.client.get("/summaries/exercises")
        self.assertIn('list="exercise-search-list"', response.data.decode("utf-8"))

        response = self.client.get("/summaries/pr")
        self.assertIn('list="pr-exercise-list"', response.data.decode("utf-8"))

        response = self.client.get("/summaries/pr", query_string={"q": strength_name})
        pr_html = response.data.decode("utf-8")
        self.assertIn(strength_name, pr_html)
        self.assertNotIn(cardio_name, pr_html)

        response = self.client.get("/records/search", query_string={"q": "벤치", "part": "가슴"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(strength_name, response.data.decode("utf-8"))

        response = self.client.get("/summaries/daily")
        self.assertIn("최근 7일", response.data.decode("utf-8"))

        response = self.client.get("/records/search")
        search_html = response.data.decode("utf-8")
        self.assertIn('name="start"', search_html)
        self.assertIn('name="end"', search_html)

        response = self.client.post(
            "/exercise-settings",
            data={
                "workout_date": workout_date,
                "exercise_name": strength_name,
                "rest_seconds": "120",
                "is_favorite": "1",
                "equipment": "諛붾꺼",
                "target_weight": "90",
                "target_reps": "8",
                "target_sets": "4",
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            setting = app_module.list_exercise_settings()[strength_name]
            self.assertEqual(setting["rest_seconds"], 120)
            self.assertEqual(setting["target_weight"], 90)
            self.assertEqual(setting["target_reps"], 8)
            self.assertEqual(setting["target_sets"], 4)
            goal_progress = app_module.list_exercise_goal_progress()[strength_name]
            self.assertGreater(goal_progress["percent"], 0)

        goal_html = self.client.get(f"/app?date={workout_date}&mode=workout").data.decode("utf-8")
        self.assertIn("exercise-goal-card", goal_html)
        self.assertIn("목표 진행률", goal_html)

        response = self.client.get("/export-meals.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("__TEST__", response.data.decode("utf-8-sig"))

        response = self.client.get("/export.csv")
        self.assertEqual(response.status_code, 200)
        workout_csv = response.data.decode("utf-8-sig")
        self.assertIn(strength_name, workout_csv)
        self.assertIn("82.5", workout_csv)

        response = self.client.get("/summaries/weekly", query_string={"week": workout_date})
        self.assertEqual(response.status_code, 200)
        self.assertIn("1시간 01분", response.data.decode("utf-8"))

        response = self.client.post(
            f"/sets/{set_id}/delete",
            data={"mode": "workout"},
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            deleted = app_module.get_db().execute("SELECT id FROM workout_sets WHERE id = ?", (set_id,)).fetchone()
            self.assertIsNone(deleted)

        response = self.client.post(
            "/rest-days",
            data={"rest_date": "2026-05-21", "rest_reason": "회복", "memo": "테스트 휴식"},
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            rest = app_module.get_db().execute(
                "SELECT * FROM recovery_checkins WHERE checkin_date = ?",
                ("2026-05-21",),
            ).fetchone()
            self.assertEqual(rest["is_rest_day"], 1)
            self.assertEqual(rest["rest_reason"], "회복")

    def test_sample_data_aggregates(self) -> None:
        with self.app.app_context():
            app_module.init_db()
            app_module.create_may_sample_data()
            monthly = app_module.build_monthly_report("2026-05-01")
            meal = app_module.build_monthly_meal_summary("2026-05-01")
            sample = app_module.get_sample_data_counts()
            self.assertEqual(monthly["workout_days"], 25)
            self.assertEqual(monthly["set_count"], 325)
            self.assertEqual(meal["meal_days"], 25)
            self.assertEqual(meal["meal_count"], 150)
            self.assertEqual(sample["sets"], 325)
            self.assertEqual(sample["meals"], 150)

        target_part = app_module.body_part_options()[0]
        all_html = self.client.get("/summaries/daily", query_string={"days": "90"}).data.decode("utf-8")
        self.assertIn("#body-part-analysis", all_html)
        visible_parts = [part for part in app_module.body_part_options() if f'data-body-part-summary="{part}"' in all_html]
        self.assertGreaterEqual(len(visible_parts), 4)

        html = self.client.get("/summaries/daily", query_string={"days": "90", "part": target_part}).data.decode("utf-8")
        self.assertIn("body-part-filter-list", html)
        self.assertIn("cat-stat-period", html)
        self.assertIn("cat-stat-detail", html)
        self.assertIn(f'data-body-part-summary="{target_part}"', html)
        for other_part in app_module.body_part_options()[1:]:
            self.assertNotIn(f'data-body-part-summary="{other_part}"', html)

        weekly_html = self.client.get("/summaries/weekly", query_string={"week": "2026-05-04"}).data.decode("utf-8")
        self.assertNotIn("body-part-filter-list", weekly_html)

    def test_update_set_can_rename_exercise_and_body_part(self) -> None:
        parts = app_module.body_part_options()
        first_part = parts[0]
        second_part = parts[1]
        workout_date = "2026-05-22"
        response = self.client.post(
            "/sets",
            data={
                "workout_date": workout_date,
                "mode": "workout",
                "body_part": first_part,
                "exercise_name": "__TEST__ original",
                "set_weight": ["50"],
                "set_reps": ["8"],
                "set_type": ["main"],
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            db = app_module.get_db()
            row = db.execute("SELECT id FROM workout_sets").fetchone()
            set_id = row["id"]

        response = self.client.post(
            f"/sets/{set_id}/update",
            data={
                "mode": "workout",
                "body_part": second_part,
                "exercise_name": "__TEST__ renamed",
                "weight": "55",
                "reps": "9",
                "set_type": "main",
                "equipment": "머신",
                "set_number": "1",
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            db = app_module.get_db()
            changed = db.execute(
                """
                SELECT ws.body_part, ws.weight, ws.reps, ws.equipment, e.name AS exercise_name
                FROM workout_sets ws
                JOIN exercises e ON e.id = ws.exercise_id
                WHERE ws.id = ?
                """,
                (set_id,),
            ).fetchone()
            self.assertEqual(changed["body_part"], second_part)
            self.assertEqual(changed["exercise_name"], "__TEST__ renamed")
            self.assertEqual(changed["weight"], 55)
            self.assertEqual(changed["reps"], 9)
            self.assertEqual(changed["equipment"], "핀머신")

    def test_session_exercise_rename_updates_group_and_shows_equipment(self) -> None:
        workout_date = "2026-05-22"
        body_part = app_module.body_part_options()[0]
        response = self.client.post(
            "/sets",
            data={
                "workout_date": workout_date,
                "mode": "workout",
                "body_part": body_part,
                "exercise_name": "__TEST__ 암풀다온",
                "equipment": "케이블",
                "set_weight": ["35", "37.5"],
                "set_reps": ["12", "10"],
                "set_type": ["본세트", "본세트"],
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            app_module.save_exercise_settings("__TEST__ 암풀다온", 75, True, "케이블", None, None, 3)
            db = app_module.get_db()
            session_id = db.execute(
                "SELECT id FROM workout_sessions WHERE workout_date = ?",
                (workout_date,),
            ).fetchone()["id"]

        html = self.client.get("/app", query_string={"date": workout_date, "mode": "workout"}).data.decode("utf-8")
        self.assertIn("운동명 일괄 수정", html)
        self.assertIn("__TEST__ 암풀다온", html)
        self.assertIn("케이블", html)

        response = self.client.post(
            f"/sessions/{session_id}/exercise-name/update",
            data={
                "mode": "workout",
                "old_exercise_name": "__TEST__ 암풀다온",
                "exercise_name": "__TEST__ 암풀다운",
                "body_part": body_part,
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            db = app_module.get_db()
            rows = db.execute(
                """
                SELECT e.name AS exercise_name, ws.equipment
                FROM workout_sets ws
                JOIN exercises e ON e.id = ws.exercise_id
                WHERE ws.session_id = ?
                ORDER BY ws.id
                """,
                (session_id,),
            ).fetchall()
            self.assertEqual([row["exercise_name"] for row in rows], ["__TEST__ 암풀다운", "__TEST__ 암풀다운"])
            copied_setting = app_module.list_exercise_settings()["__TEST__ 암풀다운"]
            self.assertEqual(copied_setting["equipment"], "케이블")

    def test_adaptive_recommendations_library_plan_and_reminders(self) -> None:
        workout_date = "2026-05-22"
        self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-18",
                "mode": "workout",
                "body_part": app_module.body_part_options()[0],
                "exercise_name": "__TEST__ adaptive",
                "set_weight": ["60", "62.5"],
                "set_reps": ["8", "8"],
                "set_type": ["main", "main"],
                "set_rpe": ["7", "7.5"],
            },
        )
        self.client.post(
            "/meals",
            data={
                "meal_date": "2026-05-18",
                "mode": "meal",
                "meal_type": "test",
                "meal_food_name": ["__TEST__ fuel"],
                "meal_quantity": ["1"],
                "meal_grams": ["100"],
                "meal_calories": ["500"],
            },
        )
        with self.app.app_context():
            recommendations = app_module.build_adaptive_training_recommendations(workout_date)
            self.assertTrue(any(item["exercise_name"] == "__TEST__ adaptive" for item in recommendations))
            link = app_module.build_nutrition_training_link("weekly", workout_date)
            self.assertGreaterEqual(link["workout_days"], 1)

        response = self.client.get("/exercises/library", query_string={"q": "__TEST__ adaptive"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("__TEST__ adaptive", response.data.decode("utf-8"))

        response = self.client.post("/plans/weekly/generate", data={"week_start": workout_date})
        self.assertEqual(response.status_code, 302)
        response = self.client.get("/plans/weekly", query_string={"week": workout_date})
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/reminders",
            data={
                "workout_enabled": "1",
                "workout_time": "18:30",
                "workout_message": "test workout reminder",
                "meal_time": "12:30",
                "meal_message": "test meal reminder",
                "weekly_time": "20:00",
                "weekly_message": "test weekly reminder",
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            reminders = app_module.list_reminder_settings()
            self.assertEqual(reminders["workout"]["enabled"], 1)
            self.assertEqual(reminders["workout"]["message"], "test workout reminder")

    def test_dangerous_delete_requires_confirmation(self) -> None:
        with self.app.app_context():
            app_module.init_db()
            app_module.create_may_sample_data()
            before = app_module.get_data_counts()
        response = self.client.post("/data/delete-all", data={"confirm_delete_all": "wrong"})
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            after = app_module.get_data_counts()
            self.assertEqual(after["sets"], before["sets"])
            self.assertEqual(after["meals"], before["meals"])


if __name__ == "__main__":
    unittest.main()
