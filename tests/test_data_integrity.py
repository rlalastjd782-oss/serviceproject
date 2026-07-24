from __future__ import annotations

from datetime import date, timedelta

import app as app_module

from tests.flow_base import FlowTestBase

FUTURE_DATE = (date.today() + timedelta(days=5)).isoformat()
FUTURE_WEEK_START = (date.today() + timedelta(days=7)).isoformat()


class NoWriteOnReadTest(FlowTestBase):
    """Regression tests: viewing a page (GET) must never create workout_sessions rows.

    A real bug shipped where opening /plans/weekly for a week the user had never
    touched silently created 7 empty workout_sessions rows (one per day), because a
    read-only summary calculation called get_or_create_session. The same pattern
    existed on GET /app for whatever date was being viewed.
    """

    def _session_count(self) -> int:
        with self.app.app_context():
            return app_module.get_db().execute("SELECT COUNT(*) FROM workout_sessions").fetchone()[0]

    def test_viewing_today_page_creates_no_session(self) -> None:
        before = self._session_count()
        self.client.get("/app")
        self.client.get("/app?mode=workout")
        self.client.get("/app?mode=meal")
        self.client.get(f"/app?date={FUTURE_DATE}")
        self.client.get(f"/app?date={FUTURE_DATE}&mode=workout")
        self.assertEqual(before, self._session_count())

    def test_viewing_weekly_plan_creates_no_sessions(self) -> None:
        before = self._session_count()
        self.client.get(f"/plans/weekly?week={FUTURE_WEEK_START}")
        self.assertEqual(before, self._session_count())

    def test_saving_a_set_still_creates_exactly_one_session(self) -> None:
        before = self._session_count()
        response = self.client.post(
            "/sets",
            data={
                "workout_date": FUTURE_DATE,
                "mode": "workout",
                "location_id": "",
                "body_part": "가슴",
                "exercise_name": "벤치프레스",
                "equipment": "",
                "set_weight": "60",
                "set_weight_unit": "kg",
                "set_reps": "8",
                "set_type": "본세트",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(before + 1, self._session_count())

        # Revisiting the now-real session's day must still render (completion
        # toggle / workout clock keep working once a real session exists).
        response = self.client.get("/app?mode=workout")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Internal Server Error", response.data.decode("utf-8"))
