from __future__ import annotations

import unittest

from health_tracker.services.pr import classify_pr_tier


class ClassifyPrTierTest(unittest.TestCase):
    def test_empty_list_defaults_to_modest(self) -> None:
        self.assertEqual(classify_pr_tier([]), "modest")

    def test_zero_old_value_is_first(self) -> None:
        achieved = [{"record_type": "최고 중량", "value": 50.0, "old_value": 0.0}]
        self.assertEqual(classify_pr_tier(achieved), "first")

    def test_small_percent_gain_is_modest(self) -> None:
        achieved = [{"record_type": "최고 중량", "value": 102.0, "old_value": 100.0}]
        self.assertEqual(classify_pr_tier(achieved), "modest")

    def test_medium_percent_gain_is_solid(self) -> None:
        achieved = [{"record_type": "최고 중량", "value": 110.0, "old_value": 100.0}]
        self.assertEqual(classify_pr_tier(achieved), "solid")

    def test_large_percent_gain_is_big(self) -> None:
        achieved = [{"record_type": "최고 중량", "value": 120.0, "old_value": 100.0}]
        self.assertEqual(classify_pr_tier(achieved), "big")

    def test_mixed_achievements_take_highest_priority_tier(self) -> None:
        achieved = [
            {"record_type": "최고 반복", "value": 5.0, "old_value": 4.9},
            {"record_type": "최고 중량", "value": 50.0, "old_value": 0.0},
        ]
        self.assertEqual(classify_pr_tier(achieved), "first")

        achieved_with_big = achieved + [{"record_type": "최고 볼륨", "value": 250.0, "old_value": 200.0}]
        self.assertEqual(classify_pr_tier(achieved_with_big), "big")


if __name__ == "__main__":
    unittest.main()
