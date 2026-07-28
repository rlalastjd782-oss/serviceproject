from __future__ import annotations

import app as app_module

from tests.flow_base import FlowTestBase


class InputBoundsTest(FlowTestBase):
    """Regression: weight/reps/rpe/cardio/meal inputs were saved with no
    range check, so an absurd value (or a mistyped extra digit) would be
    stored as-is and silently corrupt PR/1RM/volume calculations downstream."""

    def test_absurd_weight_and_reps_are_clamped_on_create(self) -> None:
        self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-20",
                "mode": "workout",
                "body_part": "가슴",
                "exercise_name": "__TEST__ Bounds Bench",
                "set_weight": "999999",
                "set_reps": "99999",
                "set_rpe": "55",
                "set_type": "본세트",
            },
        )
        with self.app.app_context():
            row = app_module.get_db().execute(
                """
                SELECT ws.weight, ws.reps, ws.rpe
                FROM workout_sets ws
                JOIN exercises e ON e.id = ws.exercise_id
                WHERE e.name = ?
                """,
                ("__TEST__ Bounds Bench",),
            ).fetchone()
        self.assertEqual(row["weight"], 500)
        self.assertEqual(row["reps"], 100)
        self.assertEqual(row["rpe"], 10)

    def test_negative_cardio_values_are_clamped_on_create(self) -> None:
        self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-20",
                "mode": "workout",
                "body_part": "유산소",
                "exercise_name": "__TEST__ Bounds Cardio",
                "cardio_incline": "-5",
                "cardio_speed": "999",
                "cardio_minutes": "-10",
            },
        )
        with self.app.app_context():
            row = app_module.get_db().execute(
                """
                SELECT ws.cardio_incline, ws.cardio_speed, ws.cardio_minutes
                FROM workout_sets ws
                JOIN exercises e ON e.id = ws.exercise_id
                WHERE e.name = ?
                """,
                ("__TEST__ Bounds Cardio",),
            ).fetchone()
        self.assertEqual(row["cardio_incline"], 0)
        self.assertEqual(row["cardio_speed"], 60)
        self.assertEqual(row["cardio_minutes"], 0)

    def test_absurd_meal_values_are_clamped_on_create(self) -> None:
        self.client.post(
            "/meals",
            data={
                "meal_date": "2026-05-20",
                "mode": "meal",
                "meal_type": "아침",
                "food_name": "__TEST__ Bounds Food",
                "amount": "9999",
                "grams": "999999",
                "calories": "9999999",
            },
        )
        with self.app.app_context():
            row = app_module.get_db().execute(
                "SELECT quantity, grams, calories FROM meal_entries WHERE food_name = ?",
                ("__TEST__ Bounds Food",),
            ).fetchone()
        self.assertEqual(row["quantity"], 100)
        self.assertEqual(row["grams"], 5000)
        self.assertEqual(row["calories"], 20000)

    def test_weight_update_is_clamped(self) -> None:
        self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-20",
                "mode": "workout",
                "body_part": "가슴",
                "exercise_name": "__TEST__ Bounds Update",
                "set_weight": "50",
                "set_reps": "5",
                "set_type": "본세트",
            },
        )
        with self.app.app_context():
            set_id = app_module.get_db().execute(
                """
                SELECT ws.id FROM workout_sets ws
                JOIN exercises e ON e.id = ws.exercise_id
                WHERE e.name = ?
                """,
                ("__TEST__ Bounds Update",),
            ).fetchone()["id"]

        self.client.post(
            f"/sets/{set_id}/update",
            data={
                "mode": "workout",
                "body_part": "가슴",
                "exercise_name": "__TEST__ Bounds Update",
                "weight": "-999",
                "weight_unit": "kg",
                "reps": "-50",
                "rpe": "0",
                "set_type": "본세트",
            },
        )
        with self.app.app_context():
            row = app_module.get_db().execute(
                "SELECT weight, reps, rpe FROM workout_sets WHERE id = ?",
                (set_id,),
            ).fetchone()
        self.assertEqual(row["weight"], 0)
        self.assertEqual(row["reps"], 0)
        self.assertEqual(row["rpe"], 1)
