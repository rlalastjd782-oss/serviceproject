from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import app as app_module
from health_tracker.security import make_password_hash, verify_password_hash


TEST_TMP_DIR = Path(__file__).resolve().parents[1] / ".test-tmp"


class SecurityHelperTest(unittest.TestCase):
    def test_password_hash_uses_pbkdf2_and_rejects_wrong_password(self) -> None:
        stored_hash = make_password_hash("1234")

        self.assertTrue(stored_hash.startswith("pbkdf2_sha256$"))
        self.assertTrue(verify_password_hash("1234", stored_hash))
        self.assertFalse(verify_password_hash("wrong", stored_hash))
        self.assertFalse(verify_password_hash("1234", "legacy-or-broken-hash"))


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
        self.client.get("/settings")
        response = self.client.post(
            "/settings/password",
            data={"password": "1234", "password_confirm": "1234"},
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
            "/",
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
            "/exercises/library",
            "/plans/weekly",
            "/more",
            "/sw.js",
        ]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_fold_ui_regression_markers_render(self) -> None:
        overview_html = self.client.get("/").data.decode("utf-8")
        self.assertIn("data-quality-card", overview_html)
        self.assertIn("분석 신뢰도", overview_html)
        self.assertIn("quality-metric-list", overview_html)
        self.assertIn("today-hero-section", overview_html)
        self.assertIn("today-mode-actions", overview_html)

        workout_html = self.client.get("/?mode=workout").data.decode("utf-8")
        self.assertIn("data-workout-quick-tab=\"recent\"", workout_html)
        self.assertIn("data-workout-quick-tab=\"favorite\"", workout_html)
        self.assertIn("data-workout-quick-tab=\"routine\"", workout_html)
        self.assertIn("data-readiness-coach", workout_html)
        self.assertIn("id=\"routine-library\"", workout_html)
        self.client.post(
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
        workout_html = self.client.get("/?date=2026-05-26&mode=workout").data.decode("utf-8")
        self.assertIn("rest-start-button", workout_html)
        self.assertIn(">타이머 시작</button>", workout_html)
        self.assertNotIn("초 휴식</button>", workout_html)

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
        self.assertIn("운동 라이브러리", html)
        self.assertIn("주간 계획", html)
        self.assertIn("캘린더", html)
        self.assertNotIn("기록 검색", html)
        self.assertNotIn("장비 분석", html)
        self.assertNotIn(">PR<", html)

    def test_visitor_is_read_only_and_admin_routes_are_locked(self) -> None:
        visitor = self.app.test_client()
        html = visitor.get("/?mode=workout").data.decode("utf-8")
        self.assertIn("visitor-mode", html)
        self.assertIn("data-quality-card", html)

        visitor.get("/")
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
        self.assertIn("/settings", response.headers.get("Location", ""))

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

        response = self.client.post("/settings/lock")
        self.assertEqual(response.status_code, 302)
        html = self.client.get("/settings").data.decode("utf-8")
        self.assertIn("settings-lock-section", html)
        self.assertNotIn("settings-overview-section", html)

        response = self.client.post("/settings/unlock", data={"password": "wrong"})
        self.assertEqual(response.status_code, 302)
        html = self.client.get("/settings?error=invalid").data.decode("utf-8")
        self.assertIn("비밀번호가 맞지 않습니다", html)
        self.assertIn("settings-lock-section", html)

        response = self.client.post("/settings/unlock", data={"password": "1234"})
        self.assertEqual(response.status_code, 302)
        html = self.client.get("/settings").data.decode("utf-8")
        self.assertIn("settings-overview-section", html)

        response = self.client.post("/settings/password/reset", data={"confirm_reset": "RESET"})
        self.assertEqual(response.status_code, 302)
        html = self.client.get("/settings").data.decode("utf-8")
        self.assertIn("설정 잠금", html)
        self.assertIn("settings-lock-section", html)

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
        self.assertNotIn("/", assets)
        self.assertNotIn("/?mode=workout", assets)
        self.assertNotIn("/?mode=meal", assets)
        self.assertIn("/calendar", assets)
        self.assertIn("/meals/weekly", assets)
        self.assertIn("/summaries/exercises", assets)
        self.assertIn("/summaries/yearly", assets)
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
        self.assertIn("workout-pwa-v1.6.7", response.data.decode("utf-8"))

    def test_lb_weights_are_saved_as_kg_and_set_builder_ui_exists(self) -> None:
        html = self.client.get("/?mode=workout").data.decode("utf-8")
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
        workout_date = "2026-05-20"
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
            self.assertEqual(changed["weight"], 82.5)
            self.assertEqual(changed["reps"], 11)
            self.assertEqual(changed_cardio["cardio_minutes"], 31)
            self.assertEqual(len(meals), 2)
            self.assertEqual(meals[0]["calories"], 180)

        response = self.client.get(f"/?date={workout_date}&mode=workout")
        html = response.data.decode("utf-8")
        self.assertIn('list="exercise-list"', html)
        self.assertIn(f'value="{strength_name}"', html)
        self.assertIn(f'value="{cardio_name}"', html)
        self.assertIn('class="set-row-actions"', html)

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
                "equipment": "test-rack",
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
            self.assertEqual(changed["equipment"], "test-rack")

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
