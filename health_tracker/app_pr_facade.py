from __future__ import annotations

import sqlite3

from health_tracker.app_database import get_db
from health_tracker.services.pr import (
    build_pr_cards_from_rows,
    build_pr_dashboard_from_rows,
    list_exercise_pr_history_from_db,
    list_exercise_pr_summary_from_db,
    list_pr_events_from_db,
    list_pr_exercise_choices_from_db,
    list_recent_pr_events_filtered_from_db,
    list_recent_pr_events_from_db,
)


def get_exercise_record_values(exercise_id: int) -> dict[str, float]:
    row = get_db().execute(
        """
        SELECT
            COALESCE(MAX(weight), 0) AS max_weight,
            COALESCE(MAX(reps), 0) AS max_reps,
            COALESCE(MAX(COALESCE(weight, 0) * COALESCE(reps, 0)), 0) AS max_volume
        FROM workout_sets
        WHERE exercise_id = ?
        """,
        (exercise_id,),
    ).fetchone()
    return {
        "max_weight": float(row["max_weight"] or 0),
        "max_reps": float(row["max_reps"] or 0),
        "max_volume": float(row["max_volume"] or 0),
    }


def update_record_values(records: dict[str, float], weight: float | None, reps: int | None) -> dict[str, float]:
    volume = float(weight or 0) * float(reps or 0)
    return {
        "max_weight": max(records["max_weight"], float(weight or 0)),
        "max_reps": max(records["max_reps"], float(reps or 0)),
        "max_volume": max(records["max_volume"], volume),
    }


def record_pr_events(
    set_id: int,
    workout_date: str,
    exercise_id: int,
    exercise_name: str,
    weight: float | None,
    reps: int | None,
    previous: dict[str, float],
) -> None:
    candidates = [
        ("최고 중량", float(weight or 0), previous["max_weight"]),
        ("최고 반복", float(reps or 0), previous["max_reps"]),
        ("최고 볼륨", float(weight or 0) * float(reps or 0), previous["max_volume"]),
    ]
    for record_type, value, old_value in candidates:
        if value > 0 and value > old_value:
            get_db().execute(
                """
                INSERT INTO pr_events (workout_date, set_id, exercise_id, exercise_name, record_type, record_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (workout_date, set_id, exercise_id, exercise_name, record_type, value),
            )


def list_pr_events(workout_date: str) -> list[sqlite3.Row]:
    return list_pr_events_from_db(get_db(), workout_date)


def build_pr_cards(workout_date: str) -> list[dict[str, object]]:
    return build_pr_cards_from_rows(list_pr_events(workout_date))


def list_recent_pr_events(limit: int = 12) -> list[sqlite3.Row]:
    return list_recent_pr_events_from_db(get_db(), limit)


def list_recent_pr_events_filtered(body_part: str = "", query: str = "", limit: int = 30) -> list[sqlite3.Row]:
    return list_recent_pr_events_filtered_from_db(get_db(), body_part, query, limit)


def list_exercise_pr_history(exercise_id: int | None, limit: int = 12) -> list[sqlite3.Row]:
    return list_exercise_pr_history_from_db(get_db(), exercise_id, limit)


def list_exercise_pr_summary(body_part: str = "", query: str = "", limit: int = 80) -> list[sqlite3.Row]:
    return list_exercise_pr_summary_from_db(get_db(), body_part, query, limit)


def list_pr_exercise_choices(body_part: str = "", query: str = "") -> list[sqlite3.Row]:
    return list_pr_exercise_choices_from_db(get_db(), body_part, query)


def build_pr_dashboard(pr_rows: list[sqlite3.Row], recent_events: list[sqlite3.Row]) -> dict[str, object]:
    return build_pr_dashboard_from_rows(pr_rows, recent_events)


def list_exercise_best_sets(exercise_id: int | None) -> list[dict[str, object]]:
    if not exercise_id:
        return []
    rows = get_db().execute(
        """
        WITH base AS (
            SELECT
                ws.id,
                s.workout_date,
                e.name AS exercise_name,
                COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
                ws.weight,
                ws.reps,
                COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0) AS volume,
                COALESCE(ws.weight, 0) * (1 + COALESCE(ws.reps, 0) / 30.0) AS estimated_1rm,
                ws.cardio_incline,
                ws.cardio_speed,
                ws.cardio_minutes,
                ws.estimated_calories
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            JOIN exercises e ON e.id = ws.exercise_id
            WHERE ws.exercise_id = ?
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (ORDER BY weight DESC, workout_date DESC, id DESC) AS rn_weight,
                ROW_NUMBER() OVER (ORDER BY reps DESC, workout_date DESC, id DESC) AS rn_reps,
                ROW_NUMBER() OVER (ORDER BY volume DESC, workout_date DESC, id DESC) AS rn_volume,
                ROW_NUMBER() OVER (ORDER BY estimated_1rm DESC, workout_date DESC, id DESC) AS rn_1rm,
                ROW_NUMBER() OVER (ORDER BY cardio_minutes DESC, workout_date DESC, id DESC) AS rn_cardio_minutes,
                ROW_NUMBER() OVER (ORDER BY cardio_speed DESC, workout_date DESC, id DESC) AS rn_cardio_speed
            FROM base
        )
        SELECT * FROM ranked
        WHERE rn_weight = 1
           OR rn_reps = 1
           OR rn_volume = 1
           OR rn_1rm = 1
           OR rn_cardio_minutes = 1
           OR rn_cardio_speed = 1
        ORDER BY workout_date DESC, id DESC
        """,
        (exercise_id,),
    ).fetchall()
    best_items: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in rows:
        candidates = [
            ("최고 중량", row["weight"], "kg", row["rn_weight"]),
            ("최고 반복", row["reps"], "회", row["rn_reps"]),
            ("최고 볼륨", row["volume"], "kg", row["rn_volume"]),
            ("예상 1RM", row["estimated_1rm"], "kg", row["rn_1rm"]),
            ("최장 유산소", row["cardio_minutes"], "분", row["rn_cardio_minutes"]),
            ("최고 속도", row["cardio_speed"], "", row["rn_cardio_speed"]),
        ]
        for label, value, unit, rank in candidates:
            if rank == 1 and value and label not in seen:
                seen.add(label)
                best_items.append(
                    {
                        "label": label,
                        "value": float(value),
                        "unit": unit,
                        "workout_date": row["workout_date"],
                        "weight": row["weight"],
                        "reps": row["reps"],
                        "body_part": row["body_part"],
                        "cardio_incline": row["cardio_incline"],
                        "cardio_speed": row["cardio_speed"],
                        "cardio_minutes": row["cardio_minutes"],
                    }
                )
    return best_items

