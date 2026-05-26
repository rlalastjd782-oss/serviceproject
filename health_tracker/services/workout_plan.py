from __future__ import annotations

import sqlite3
from collections.abc import Callable


def list_workout_plan_from_db(db: sqlite3.Connection, workout_date: str) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT
            wpi.*,
            COALESCE((
                SELECT COUNT(ws.id)
                FROM workout_sets ws
                JOIN workout_sessions s ON s.id = ws.session_id
                JOIN exercises e ON e.id = ws.exercise_id
                WHERE s.workout_date = wpi.workout_date
                  AND e.name = wpi.exercise_name
            ), 0) AS completed_sets
        FROM workout_plan_items wpi
        WHERE wpi.workout_date = ?
        ORDER BY wpi.sort_order, wpi.id
        """,
        (workout_date,),
    ).fetchall()


def build_workout_completion_summary_from_db(
    db: sqlite3.Connection,
    workout_date: str,
    get_or_create_session: Callable[[str | None, int | None], sqlite3.Row],
) -> dict[str, object]:
    session = get_or_create_session(workout_date, None)
    by_part = db.execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date = ?
        GROUP BY body_part
        ORDER BY set_count DESC, body_part
        """,
        (workout_date,),
    ).fetchall()
    top_exercise = db.execute(
        """
        SELECT e.name, COUNT(ws.id) AS set_count,
               COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.workout_date = ?
        GROUP BY e.name
        ORDER BY set_count DESC, volume DESC, e.name
        LIMIT 1
        """,
        (workout_date,),
    ).fetchone()
    plan_rows = list_workout_plan_from_db(db, workout_date)
    plan_total = len(plan_rows)
    plan_done = sum(1 for row in plan_rows if int(row["completed_sets"] or 0) >= int(row["target_sets"] or 1))
    return {
        "completed": bool(session["completed"]),
        "duration_seconds": int(session["duration_seconds"] or 0),
        "body_parts": [dict(row) for row in by_part],
        "top_exercise": dict(top_exercise) if top_exercise else None,
        "plan_total": plan_total,
        "plan_done": plan_done,
        "plan_percent": 0 if plan_total == 0 else round(plan_done / plan_total * 100),
    }


def build_workout_session_flow_from_db(
    db: sqlite3.Connection,
    workout_date: str,
    get_exercise_rest_seconds: Callable[[str], int],
    default_rest_seconds: int,
) -> dict[str, object]:
    plan_rows = list_workout_plan_from_db(db, workout_date)
    next_item = None
    for row in plan_rows:
        if int(row["completed_sets"] or 0) < int(row["target_sets"] or 1):
            next_item = dict(row)
            break
    if next_item is None and plan_rows:
        next_item = dict(plan_rows[-1])

    last_set = db.execute(
        """
        SELECT
            e.name AS exercise_name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.equipment,
            ws.set_type
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date = ?
        ORDER BY ws.sort_order DESC, ws.id DESC
        LIMIT 1
        """,
        (workout_date,),
    ).fetchone()
    rest_seconds = get_exercise_rest_seconds(last_set["exercise_name"]) if last_set else default_rest_seconds
    return {
        "next_item": next_item,
        "last_set": dict(last_set) if last_set else None,
        "rest_seconds": rest_seconds,
        "has_plan": bool(plan_rows),
    }


def create_workout_plan_item_in_db(db: sqlite3.Connection, workout_date: str, body_part: str, exercise_name: str, target_sets: int) -> None:
    next_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workout_plan_items WHERE workout_date = ?",
        (workout_date,),
    ).fetchone()[0]
    db.execute(
        """
        INSERT INTO workout_plan_items (workout_date, body_part, exercise_name, target_sets, sort_order)
        VALUES (?, ?, ?, ?, ?)
        """,
        (workout_date, body_part, exercise_name, max(1, target_sets), next_order),
    )
    db.commit()


def delete_workout_plan_item_from_db(db: sqlite3.Connection, item_id: int) -> None:
    db.execute("DELETE FROM workout_plan_items WHERE id = ?", (item_id,))
    db.commit()


def apply_default_program_to_db(
    db: sqlite3.Connection,
    program_rows: list[tuple[str, str, str, float | None, int | None]] | None,
    workout_date: str,
    get_or_create_session: Callable[[str | None, int | None], sqlite3.Row],
    get_or_create_exercise: Callable[[str], int],
) -> None:
    if not program_rows:
        return
    session = get_or_create_session(workout_date, None)
    next_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workout_sets WHERE session_id = ?",
        (session["id"],),
    ).fetchone()[0]
    for offset, (body_part, exercise_name, set_type, weight, reps) in enumerate(program_rows):
        exercise_id = get_or_create_exercise(exercise_name)
        db.execute(
            """
            INSERT INTO workout_sets (
                session_id, exercise_id, body_part, set_type, weight, reps, equipment, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session["id"], exercise_id, body_part, set_type, weight, reps, "", next_order + offset),
        )
    db.commit()
