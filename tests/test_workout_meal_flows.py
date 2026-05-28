from __future__ import annotations

import app as app_module


from tests.flow_base import FlowTestBase


class WorkoutMealFlowTest(FlowTestBase):
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
