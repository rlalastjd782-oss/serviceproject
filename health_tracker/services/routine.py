from __future__ import annotations

import sqlite3
from collections.abc import Callable


def list_routines_from_db(db: sqlite3.Connection, location_id: int | None = None) -> list[dict[str, object]]:
    location_where = "WHERE rt.location_id = ?" if location_id else ""
    params = (location_id,) if location_id else ()
    rows = db.execute(
        f"""
        SELECT
            rt.id,
            rt.name,
            COUNT(ri.id) AS item_count,
            GROUP_CONCAT(DISTINCT COALESCE(NULLIF(ri.body_part, ''), '기타')) AS body_parts,
            COALESCE(SUM(COALESCE(ri.cardio_minutes, 0)), 0) AS cardio_minutes
        FROM routine_templates rt
        LEFT JOIN routine_items ri ON ri.routine_id = rt.id
        {location_where}
        GROUP BY rt.id
        ORDER BY rt.created_at DESC, rt.id DESC
        """,
        params,
    ).fetchall()
    routines = []
    for row in rows:
        item_count = int(row["item_count"] or 0)
        cardio_minutes = float(row["cardio_minutes"] or 0)
        routines.append(
            {
                **dict(row),
                "body_parts": (row["body_parts"] or "").replace(",", " · "),
                "estimated_minutes": round(item_count * 3 + cardio_minutes),
            }
        )
    return routines


def rename_routine_template_in_db(db: sqlite3.Connection, routine_id: int, name: str) -> None:
    db.execute("UPDATE routine_templates SET name = ? WHERE id = ?", (name, routine_id))
    db.commit()


def delete_routine_template_from_db(db: sqlite3.Connection, routine_id: int) -> None:
    db.execute("DELETE FROM routine_items WHERE routine_id = ?", (routine_id,))
    db.execute("DELETE FROM routine_templates WHERE id = ?", (routine_id,))
    db.commit()


def create_routine_template_from_db(db: sqlite3.Connection, name: str, session_id: int) -> None:
    source_session = db.execute("SELECT location_id FROM workout_sessions WHERE id = ?", (session_id,)).fetchone()
    items = db.execute(
        """
        SELECT
            e.name AS exercise_name,
            ws.body_part,
            ws.set_type,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.equipment,
            ws.sort_order
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE ws.session_id = ?
        ORDER BY ws.sort_order, ws.id
        """,
        (session_id,),
    ).fetchall()
    if not items:
        return
    cursor = db.execute(
        "INSERT INTO routine_templates (name, location_id) VALUES (?, ?)",
        (name, source_session["location_id"] if source_session else None),
    )
    routine_id = int(cursor.lastrowid)
    for index, item in enumerate(items, start=1):
        db.execute(
            """
            INSERT INTO routine_items (
                routine_id, exercise_name, body_part, set_type, weight, reps,
                cardio_incline, cardio_speed, cardio_minutes, equipment, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                routine_id,
                item["exercise_name"],
                item["body_part"],
                item["set_type"],
                item["weight"],
                item["reps"],
                item["cardio_incline"],
                item["cardio_speed"],
                item["cardio_minutes"],
                item["equipment"],
                index,
            ),
        )
    db.commit()


def apply_routine_template_to_db(
    db: sqlite3.Connection,
    routine_id: int,
    workout_date: str,
    get_or_create_session: Callable[[str | None, int | None], sqlite3.Row],
    get_or_create_exercise: Callable[[str], int],
    estimate_exercise_calories: Callable[[str | None, float | None, float | None, float | None, str | None], float | None],
) -> None:
    items = db.execute(
        """
        SELECT id, routine_id, exercise_name, body_part, set_type, weight, reps,
               cardio_incline, cardio_speed, cardio_minutes, equipment, sort_order
        FROM routine_items
        WHERE routine_id = ?
        ORDER BY sort_order, id
        """,
        (routine_id,),
    ).fetchall()
    if not items:
        return
    session = get_or_create_session(workout_date, None)
    next_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workout_sets WHERE session_id = ?",
        (session["id"],),
    ).fetchone()[0]
    for offset, item in enumerate(items):
        exercise_id = get_or_create_exercise(item["exercise_name"])
        db.execute(
            """
            INSERT INTO workout_sets (
                session_id, exercise_id, body_part, set_type, weight, reps,
                cardio_incline, cardio_speed, cardio_minutes, estimated_calories, equipment, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["id"],
                exercise_id,
                item["body_part"],
                item["set_type"],
                item["weight"],
                item["reps"],
                item["cardio_incline"],
                item["cardio_speed"],
                item["cardio_minutes"],
                estimate_exercise_calories(
                    item["body_part"],
                    item["cardio_incline"],
                    item["cardio_speed"],
                    item["cardio_minutes"],
                    workout_date,
                ),
                item["equipment"],
                next_order + offset,
            ),
        )
    db.commit()


def apply_session_template_to_db(
    db: sqlite3.Connection,
    source_session_id: int,
    workout_date: str,
    get_or_create_session: Callable[[str | None, int | None], sqlite3.Row],
    get_or_create_exercise: Callable[[str], int],
    estimate_exercise_calories: Callable[[str | None, float | None, float | None, float | None, str | None], float | None],
) -> None:
    items = db.execute(
        """
        SELECT
            e.name AS exercise_name,
            ws.body_part,
            ws.set_type,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.equipment,
            ws.sort_order
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE ws.session_id = ?
        ORDER BY ws.sort_order, ws.id
        """,
        (source_session_id,),
    ).fetchall()
    if not items:
        return
    session = get_or_create_session(workout_date, None)
    next_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workout_sets WHERE session_id = ?",
        (session["id"],),
    ).fetchone()[0]
    for offset, item in enumerate(items):
        exercise_id = get_or_create_exercise(item["exercise_name"])
        db.execute(
            """
            INSERT INTO workout_sets (
                session_id, exercise_id, body_part, set_type, weight, reps,
                cardio_incline, cardio_speed, cardio_minutes, estimated_calories, equipment, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["id"],
                exercise_id,
                item["body_part"],
                item["set_type"],
                item["weight"],
                item["reps"],
                item["cardio_incline"],
                item["cardio_speed"],
                item["cardio_minutes"],
                estimate_exercise_calories(
                    item["body_part"],
                    item["cardio_incline"],
                    item["cardio_speed"],
                    item["cardio_minutes"],
                    workout_date,
                ),
                item["equipment"],
                next_order + offset,
            ),
        )
    db.commit()
