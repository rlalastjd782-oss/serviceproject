from __future__ import annotations

from datetime import date, timedelta

import app as app_module

from health_tracker.services.streaks import build_logging_streak_from_db
from tests.flow_base import FlowTestBase

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TWO_DAYS_AGO = (date.today() - timedelta(days=2)).isoformat()
THREE_DAYS_AGO = (date.today() - timedelta(days=3)).isoformat()


class LoggingStreakTest(FlowTestBase):
    def _insert_workout_set(self, workout_date: str) -> None:
        with self.app.app_context():
            db = app_module.get_db()
            session_id = db.execute(
                "INSERT INTO workout_sessions (workout_date) VALUES (?)", (workout_date,)
            ).lastrowid
            exercise_id = db.execute(
                "INSERT INTO exercises (name) VALUES (?)", (f"__TEST__ 스트릭운동_{workout_date}",)
            ).lastrowid
            db.execute(
                "INSERT INTO workout_sets (session_id, exercise_id, weight, reps) VALUES (?, ?, ?, ?)",
                (session_id, exercise_id, 10, 5),
            )
            db.commit()

    def _streak(self) -> dict[str, object]:
        with self.app.app_context():
            return build_logging_streak_from_db(app_module.get_db(), TODAY)

    def test_no_history_returns_zero_streak(self) -> None:
        streak = self._streak()
        self.assertEqual(streak["current_streak"], 0)
        self.assertEqual(streak["status"], "새로 시작")
        self.assertIsNone(streak["last_active_date"])

    def test_consecutive_days_ending_today(self) -> None:
        self._insert_workout_set(TWO_DAYS_AGO)
        self._insert_workout_set(YESTERDAY)
        self._insert_workout_set(TODAY)
        streak = self._streak()
        self.assertEqual(streak["current_streak"], 3)
        self.assertEqual(streak["status"], "오늘 기록 중")

    def test_streak_continues_with_one_day_grace(self) -> None:
        self._insert_workout_set(TWO_DAYS_AGO)
        self._insert_workout_set(YESTERDAY)
        streak = self._streak()
        self.assertEqual(streak["current_streak"], 2)
        self.assertIn("이어가면", streak["status"])

    def test_streak_breaks_after_two_day_gap(self) -> None:
        self._insert_workout_set(THREE_DAYS_AGO)
        streak = self._streak()
        self.assertEqual(streak["current_streak"], 0)
        self.assertEqual(streak["status"], "끊김")
        self.assertEqual(streak["last_active_date"], THREE_DAYS_AGO)

    def test_ignores_activity_logged_after_the_viewed_date(self) -> None:
        # Regression: browsing to an old date must not pick up a streak from
        # activity logged on later dates (e.g. real "today").
        FAR_FUTURE = (date.today() + timedelta(days=30)).isoformat()
        self._insert_workout_set(FAR_FUTURE)
        streak = self._streak()
        self.assertEqual(streak["current_streak"], 0)
        self.assertEqual(streak["status"], "새로 시작")

    def test_meal_entry_also_counts_toward_streak(self) -> None:
        with self.app.app_context():
            db = app_module.get_db()
            db.execute(
                "INSERT INTO meal_entries (meal_date, meal_type, food_name) VALUES (?, ?, ?)",
                (TODAY, "아침", "__TEST__ 스트릭식단"),
            )
            db.commit()
        streak = self._streak()
        self.assertEqual(streak["current_streak"], 1)
        self.assertEqual(streak["status"], "오늘 기록 중")
