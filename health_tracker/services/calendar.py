from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta


def list_month_calendar_days_from_db(
    db: sqlite3.Connection,
    month_start: str,
    shift_month: Callable[[str, int], str],
) -> list[dict[str, object]]:
    next_month = shift_month(month_start, 1)
    workout_rows = db.execute(
        """
        SELECT
            s.workout_date,
            COALESCE(s.duration_seconds, 0) AS duration_seconds,
            COALESCE(s.completed, 0) AS completed,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes
        FROM workout_sessions s
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        GROUP BY s.workout_date, s.duration_seconds, s.completed
        """,
        (month_start, next_month),
    ).fetchall()
    meal_rows = db.execute(
        """
        SELECT meal_date, COUNT(id) AS meal_count
        FROM meal_entries
        WHERE meal_date >= ? AND meal_date < ?
        GROUP BY meal_date
        """,
        (month_start, next_month),
    ).fetchall()
    workouts = {
        row["workout_date"]: {
            "set_count": int(row["set_count"]),
            "duration_seconds": int(row["duration_seconds"] or 0),
            "completed": bool(row["completed"]),
            "volume": float(row["volume"] or 0),
            "cardio_minutes": float(row["cardio_minutes"] or 0),
        }
        for row in workout_rows
    }
    meals = {row["meal_date"]: int(row["meal_count"]) for row in meal_rows}
    start = datetime.strptime(month_start, "%Y-%m-%d")
    next_start = datetime.strptime(next_month, "%Y-%m-%d")
    days = []
    current = start
    while current < next_start:
        key = current.strftime("%Y-%m-%d")
        days.append(
            {
                "date": key,
                "day": current.day,
                "weekday": current.weekday(),
                "set_count": workouts.get(key, {}).get("set_count", 0),
                "duration_seconds": workouts.get(key, {}).get("duration_seconds", 0),
                "completed": workouts.get(key, {}).get("completed", False),
                "volume": workouts.get(key, {}).get("volume", 0),
                "cardio_minutes": workouts.get(key, {}).get("cardio_minutes", 0),
                "meal_count": meals.get(key, 0),
            }
        )
        current += timedelta(days=1)
    return days
