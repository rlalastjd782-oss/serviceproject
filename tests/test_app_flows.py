from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import app as app_module


class HealthTrackerFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_database = app_module.DATABASE
        app_module.DATABASE = Path(self.tmpdir.name) / "test-workout.db"
        self.app = app_module.app
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        app_module.DATABASE = self.original_database
        self.tmpdir.cleanup()

    def test_main_pages_render(self) -> None:
        paths = [
            "/",
            "/summaries/daily",
            "/summaries/weekly",
            "/summaries/monthly",
            "/summaries/exercises",
            "/summaries/equipment",
            "/summaries/pr",
            "/calendar",
            "/meals/weekly",
            "/meals/monthly",
            "/settings",
            "/api/sessions",
            "/records/search",
        ]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

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


if __name__ == "__main__":
    unittest.main()
