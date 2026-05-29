from __future__ import annotations

import sqlite3
from collections.abc import Callable


def save_goal_to_db(db: sqlite3.Connection, key: str, value: int) -> None:
    db.execute(
        """
        INSERT INTO user_goals (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """,
        (key, max(0, value)),
    )
    db.commit()


def get_goal_value_from_db(db: sqlite3.Connection, key: str, default: int) -> int:
    row = db.execute("SELECT value FROM user_goals WHERE key = ?", (key,)).fetchone()
    return int(row["value"]) if row else default


def goal_values_from_db(db: sqlite3.Connection, defaults: dict[str, int]) -> dict[str, int]:
    rows = db.execute(
        f"""
        SELECT key, value
        FROM user_goals
        WHERE key IN ({", ".join("?" for _ in defaults)})
        """,
        tuple(defaults),
    ).fetchall()
    values = dict(defaults)
    values.update({row["key"]: int(row["value"]) for row in rows})
    return values


def build_goal_progress_from_db(
    db: sqlite3.Connection,
    date_text: str,
    week_start_for_date: Callable[[str], str],
    shift_date: Callable[[str, int], str],
    normalize_month: Callable[[str], str],
    shift_month: Callable[[str, int], str],
) -> dict[str, dict[str, int | float | str]]:
    week_start = week_start_for_date(date_text)
    week_end = shift_date(week_start, 6)
    month_start = normalize_month(date_text[:7])
    next_month = shift_month(month_start, 1)
    weekly_workout_days = db.execute(
        """
        SELECT COUNT(DISTINCT s.workout_date) AS count
        FROM workout_sessions s
        JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date BETWEEN ? AND ?
        """,
        (week_start, week_end),
    ).fetchone()["count"]
    weekly_meal_days = db.execute(
        """
        SELECT COUNT(DISTINCT meal_date) AS count
        FROM meal_entries
        WHERE meal_date BETWEEN ? AND ?
        """,
        (week_start, week_end),
    ).fetchone()["count"]
    weekly_calories = db.execute(
        """
        SELECT COALESCE(SUM(calories), 0) AS calories
        FROM meal_entries
        WHERE meal_date BETWEEN ? AND ?
        """,
        (week_start, week_end),
    ).fetchone()["calories"]
    monthly_volume = db.execute(
        """
        SELECT COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        """,
        (month_start, next_month),
    ).fetchone()["volume"]
    monthly_workout_days = db.execute(
        """
        SELECT COUNT(DISTINCT s.workout_date) AS count
        FROM workout_sessions s
        JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        """,
        (month_start, next_month),
    ).fetchone()["count"]
    monthly_cardio_minutes = db.execute(
        """
        SELECT COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS minutes
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        """,
        (month_start, next_month),
    ).fetchone()["minutes"]
    goal_values = goal_values_from_db(
        db,
        {
            "weekly_workout_days": 3,
            "weekly_meal_days": 5,
            "weekly_calories": 14000,
            "monthly_volume": 10000,
            "monthly_workout_days": 12,
            "monthly_cardio_minutes": 300,
        },
    )
    return {
        "weekly_workout_days": goal_item(int(weekly_workout_days), goal_values["weekly_workout_days"], "주간 운동일"),
        "weekly_meal_days": goal_item(int(weekly_meal_days), goal_values["weekly_meal_days"], "주간 식단일"),
        "weekly_calories": goal_item(float(weekly_calories), goal_values["weekly_calories"], "주간 칼로리"),
        "monthly_volume": goal_item(float(monthly_volume), goal_values["monthly_volume"], "월간 볼륨"),
        "monthly_workout_days": goal_item(int(monthly_workout_days), goal_values["monthly_workout_days"], "월간 운동일"),
        "monthly_cardio_minutes": goal_item(
            float(monthly_cardio_minutes),
            goal_values["monthly_cardio_minutes"],
            "월간 유산소",
        ),
    }


def goal_item(current: int | float, target: int, label: str) -> dict[str, int | float | str]:
    percent = 0 if target <= 0 else min(100, round(float(current) / target * 100))
    return {"current": current, "target": target, "label": label, "percent": percent}
