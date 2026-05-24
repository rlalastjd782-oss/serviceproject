from __future__ import annotations

import sqlite3


def build_period_chart_from_rows(rows: list[sqlite3.Row]) -> list[dict[str, float | int | str]]:
    ordered_rows = list(reversed(rows))
    max_volume = max([float(row["volume"]) for row in ordered_rows] + [1.0])
    max_grams = max([float(row["grams"]) for row in ordered_rows] + [1.0])
    max_exercise_calories = max([float(row["exercise_calories"]) for row in ordered_rows] + [1.0])
    max_sets = max([int(row["set_count"]) for row in ordered_rows] + [1])
    max_duration = max([int(row["duration_seconds"]) for row in ordered_rows] + [1])
    return [
        {
            "period": row["period"],
            "volume": float(row["volume"]),
            "grams": float(row["grams"]),
            "exercise_calories": float(row["exercise_calories"]),
            "duration_seconds": int(row["duration_seconds"]),
            "set_count": int(row["set_count"]),
            "workout_days": int(row["workout_days"]),
            "meal_count": int(row["meal_count"]),
            "volume_height": max(3, round(float(row["volume"]) / max_volume * 100)),
            "volume_width": round(float(row["volume"]) / max_volume * 100),
            "grams_height": max(3, round(float(row["grams"]) / max_grams * 100)),
            "grams_width": round(float(row["grams"]) / max_grams * 100),
            "exercise_calorie_height": max(3, round(float(row["exercise_calories"]) / max_exercise_calories * 100)),
            "exercise_calorie_width": round(float(row["exercise_calories"]) / max_exercise_calories * 100),
            "set_height": max(3, round(int(row["set_count"]) / max_sets * 100)),
            "set_width": round(int(row["set_count"]) / max_sets * 100),
            "duration_width": round(int(row["duration_seconds"]) / max_duration * 100),
        }
        for row in ordered_rows
    ]


def build_daily_chart_from_rows(rows: list[sqlite3.Row]) -> list[dict[str, float | int | str]]:
    chart = build_period_chart_from_rows(rows)
    for item in chart:
        item["workout_days"] = 1 if int(item["set_count"]) > 0 else 0
    return chart
