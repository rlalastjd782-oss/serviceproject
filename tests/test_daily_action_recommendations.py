from __future__ import annotations

import unittest

from health_tracker.services.today_context import build_daily_action_recommendations


def base_context() -> dict[str, object]:
    return {
        "session": {"workout_date": "2026-06-02"},
        "current_date": "2026-06-02",
        "today_summary": {"set_count": 0, "meal_count": 0},
        "goals": {
            "weekly_workout_days": {"current": 1, "target": 3, "label": "주간 운동일", "percent": 33},
            "weekly_meal_days": {"current": 4, "target": 5, "label": "주간 식단일", "percent": 80},
        },
        "body_metric": None,
        "data_quality_profile": {"score": 20},
        "balance_score": {"missing": ["하체"]},
        "recovery_checkin": {"is_rest_day": 0},
    }


class DailyActionRecommendationTest(unittest.TestCase):
    def test_empty_day_limits_to_five_and_orders_primary_sources(self) -> None:
        result = build_daily_action_recommendations(base_context())

        self.assertEqual(result["badge"], "5개")
        sources = [item["source"] for item in result["items"]]
        self.assertEqual(sources, ["workout", "meal", "goal", "body", "quality"])
        self.assertEqual(result["items"][0]["href"], "/app?date=2026-06-02&mode=workout#workout-input")
        self.assertLessEqual(len(result["items"]), 5)

    def test_rest_day_does_not_force_workout_recommendation(self) -> None:
        context = base_context()
        context["recovery_checkin"] = {"is_rest_day": 1}

        result = build_daily_action_recommendations(context)

        self.assertNotIn("workout", [item["source"] for item in result["items"]])

    def test_complete_state_keeps_next_actions(self) -> None:
        context = base_context()
        context["today_summary"] = {"set_count": 4, "meal_count": 3}
        context["goals"] = {
            "weekly_workout_days": {"current": 3, "target": 3, "label": "주간 운동일", "percent": 100},
            "weekly_meal_days": {"current": 5, "target": 5, "label": "주간 식단일", "percent": 100},
        }
        context["body_metric"] = {"body_weight": 80}
        context["data_quality_profile"] = {"score": 90}
        context["balance_score"] = {"missing": []}

        result = build_daily_action_recommendations(context)

        self.assertTrue(result["is_complete"])
        self.assertEqual(result["badge"], "완료")
        self.assertGreaterEqual(len(result["complete_actions"]), 1)


if __name__ == "__main__":
    unittest.main()
