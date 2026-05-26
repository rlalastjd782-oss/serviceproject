from __future__ import annotations

import sqlite3


def list_exercise_notes_from_db(db: sqlite3.Connection) -> dict[str, str]:
    rows = db.execute("SELECT exercise_name, note FROM exercise_notes").fetchall()
    return {row["exercise_name"]: row["note"] for row in rows}


def save_exercise_note_to_db(db: sqlite3.Connection, exercise_name: str, note: str) -> None:
    db.execute(
        """
        INSERT INTO exercise_notes (exercise_name, note, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(exercise_name) DO UPDATE SET note = excluded.note, updated_at = CURRENT_TIMESTAMP
        """,
        (exercise_name, note),
    )
    db.commit()


def list_exercise_settings_from_db(
    db: sqlite3.Connection,
    default_rest_seconds: int,
) -> dict[str, dict[str, int | float | bool | str | None]]:
    rows = db.execute("SELECT * FROM exercise_settings").fetchall()
    return {
        row["exercise_name"]: {
            "rest_seconds": int(row["rest_seconds"] or default_rest_seconds),
            "is_favorite": bool(row["is_favorite"]),
            "equipment": row["equipment"] or "",
            "target_weight": row["target_weight"],
            "target_reps": row["target_reps"],
            "target_sets": row["target_sets"],
        }
        for row in rows
    }


def save_exercise_settings_to_db(
    db: sqlite3.Connection,
    exercise_name: str,
    rest_seconds: int,
    is_favorite: bool,
    default_rest_seconds: int,
    equipment: str = "",
    target_weight: float | None = None,
    target_reps: int | None = None,
    target_sets: int | None = None,
) -> None:
    db.execute(
        """
        INSERT INTO exercise_settings (
            exercise_name, rest_seconds, is_favorite, equipment,
            target_weight, target_reps, target_sets, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(exercise_name) DO UPDATE SET
            rest_seconds = excluded.rest_seconds,
            is_favorite = excluded.is_favorite,
            equipment = excluded.equipment,
            target_weight = excluded.target_weight,
            target_reps = excluded.target_reps,
            target_sets = excluded.target_sets,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            exercise_name,
            max(15, min(600, int(rest_seconds or default_rest_seconds))),
            1 if is_favorite else 0,
            equipment[:20],
            target_weight,
            target_reps,
            target_sets,
        ),
    )
    db.commit()


def save_exercise_equipment_to_db(db: sqlite3.Connection, exercise_name: str, equipment: str) -> None:
    if not exercise_name or not equipment:
        return
    db.execute(
        """
        INSERT INTO exercise_settings (exercise_name, equipment, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(exercise_name) DO UPDATE SET
            equipment = excluded.equipment,
            updated_at = CURRENT_TIMESTAMP
        """,
        (exercise_name, equipment[:20]),
    )


def get_exercise_rest_seconds_from_db(db: sqlite3.Connection, exercise_name: str, default_rest_seconds: int) -> int:
    row = db.execute(
        "SELECT rest_seconds FROM exercise_settings WHERE exercise_name = ?",
        (exercise_name,),
    ).fetchone()
    return int(row["rest_seconds"]) if row else default_rest_seconds
