from __future__ import annotations

import sqlite3

from health_tracker.app_database import get_db
from health_tracker.app_settings import get_app_preferences
from health_tracker.date_utils import meal_week_label, normalize_month, shift_date, shift_month, week_start_for_date
from health_tracker.services.body_part_analysis import (
    list_body_part_summary_from_db,
    list_weekly_body_part_details_from_db,
)
from health_tracker.services.calendar import list_month_calendar_days_from_db
from health_tracker.services.exercise_calorie import estimate_exercise_calories_from_weight
from health_tracker.services.workout import grouped_sets_for_session_from_db, list_sets_for_session_from_db


def list_month_calendar_days(month_start: str) -> list[dict[str, object]]:
    return list_month_calendar_days_from_db(get_db(), month_start, shift_month)


def list_body_part_summary(scope: str, limit: int = 30, date_text: str | None = None) -> list[sqlite3.Row]:
    return list_body_part_summary_from_db(
        get_db(),
        scope,
        limit,
        date_text,
        week_start_for_date,
        meal_week_label,
        shift_date,
        normalize_month,
        shift_month,
    )


def list_weekly_body_part_details(date_text: str | None = None) -> dict[str, list[sqlite3.Row]]:
    return list_weekly_body_part_details_from_db(
        get_db(),
        date_text,
        week_start_for_date,
        meal_week_label,
        shift_date,
    )


def list_sets_for_session(session_id: int) -> list[sqlite3.Row]:
    return list_sets_for_session_from_db(get_db(), session_id)


def grouped_sets_for_session(session_id: int | None) -> list[dict[str, object]]:
    return grouped_sets_for_session_from_db(get_db(), session_id)


def get_body_weight_for_date(metric_date: str) -> float:
    row = get_db().execute(
        """
        SELECT body_weight
        FROM body_metrics
        WHERE metric_date <= ? AND body_weight IS NOT NULL
        ORDER BY metric_date DESC
        LIMIT 1
        """,
        (metric_date,),
    ).fetchone()
    if row and row["body_weight"]:
        return float(row["body_weight"])
    return float(get_app_preferences()["default_body_weight_kg"])


def estimate_exercise_calories(
    body_part: str,
    cardio_incline: float | None,
    cardio_speed: float | None,
    cardio_minutes: float | None,
    workout_date: str,
) -> float | None:
    return estimate_exercise_calories_from_weight(
        body_part,
        cardio_incline,
        cardio_speed,
        cardio_minutes,
        get_body_weight_for_date(workout_date),
    )


def recalculate_missing_exercise_calories() -> None:
    db = get_db()
    rows = db.execute(
        """
        SELECT ws.id, s.workout_date, ws.body_part, ws.cardio_incline, ws.cardio_speed, ws.cardio_minutes
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE COALESCE(NULLIF(ws.body_part, ''), '기타') = '유산소'
          AND ws.cardio_minutes IS NOT NULL
          AND ws.estimated_calories IS NULL
        """
    ).fetchall()
    for row in rows:
        db.execute(
            "UPDATE workout_sets SET estimated_calories = ? WHERE id = ?",
            (
                estimate_exercise_calories(
                    row["body_part"],
                    row["cardio_incline"],
                    row["cardio_speed"],
                    row["cardio_minutes"],
                    row["workout_date"],
                ),
                row["id"],
            ),
        )


def recalculate_exercise_calories_for_date(workout_date: str) -> None:
    db = get_db()
    rows = db.execute(
        """
        SELECT ws.id, ws.body_part, ws.cardio_incline, ws.cardio_speed, ws.cardio_minutes
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date = ?
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') = '유산소'
        """,
        (workout_date,),
    ).fetchall()
    for row in rows:
        db.execute(
            "UPDATE workout_sets SET estimated_calories = ? WHERE id = ?",
            (
                estimate_exercise_calories(
                    row["body_part"],
                    row["cardio_incline"],
                    row["cardio_speed"],
                    row["cardio_minutes"],
                    workout_date,
                ),
                row["id"],
            ),
        )
