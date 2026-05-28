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


def list_exercise_goal_progress_from_db(db: sqlite3.Connection) -> dict[str, dict[str, object]]:
    rows = db.execute(
        """
        WITH exercise_daily_sets AS (
            SELECT e.name AS exercise_name, s.workout_date, COUNT(ws.id) AS set_count
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            JOIN exercises e ON e.id = ws.exercise_id
            GROUP BY e.name, s.workout_date
        )
        SELECT
            es.exercise_name,
            es.target_weight,
            es.target_reps,
            es.target_sets,
            COALESCE(MAX(ws.weight), 0) AS best_weight,
            COALESCE(MAX(ws.reps), 0) AS best_reps,
            COALESCE((
                SELECT MAX(eds.set_count)
                FROM exercise_daily_sets eds
                WHERE eds.exercise_name = es.exercise_name
            ), 0) AS best_sets,
            MAX(s.workout_date) AS last_date
        FROM exercise_settings es
        LEFT JOIN exercises e ON e.name = es.exercise_name
        LEFT JOIN workout_sets ws ON ws.exercise_id = e.id
        LEFT JOIN workout_sessions s ON s.id = ws.session_id
        WHERE es.target_weight IS NOT NULL
           OR es.target_reps IS NOT NULL
           OR es.target_sets IS NOT NULL
        GROUP BY es.exercise_name, es.target_weight, es.target_reps, es.target_sets
        ORDER BY es.exercise_name
        """
    ).fetchall()
    progress: dict[str, dict[str, object]] = {}
    for row in rows:
        items: list[dict[str, object]] = []
        if row["target_weight"]:
            current = float(row["best_weight"] or 0)
            target = float(row["target_weight"] or 0)
            items.append({"label": "중량", "current": current, "target": target, "unit": "kg"})
        if row["target_reps"]:
            current = int(row["best_reps"] or 0)
            target = int(row["target_reps"] or 0)
            items.append({"label": "반복", "current": current, "target": target, "unit": "회"})
        if row["target_sets"]:
            current = int(row["best_sets"] or 0)
            target = int(row["target_sets"] or 0)
            items.append({"label": "세트", "current": current, "target": target, "unit": "세트"})

        scored = [
            min(100, round(float(item["current"] or 0) / float(item["target"] or 1) * 100))
            for item in items
            if float(item["target"] or 0) > 0
        ]
        percent = round(sum(scored) / len(scored)) if scored else 0
        progress[row["exercise_name"]] = {
            "percent": percent,
            "items": items,
            "last_date": row["last_date"],
            "is_done": percent >= 100,
        }
    return progress


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


def list_favorite_exercises_from_db(
    db: sqlite3.Connection,
    location_id: int | None = None,
) -> list[sqlite3.Row]:
    location_filter = (
        """
        AND EXISTS (
            SELECT 1
            FROM workout_sets lws
            JOIN workout_sessions ls ON ls.id = lws.session_id
            JOIN exercises le ON le.id = lws.exercise_id
            WHERE le.name = es.exercise_name AND ls.location_id = ?
        )
        """
        if location_id
        else ""
    )
    params = (location_id,) if location_id else ()
    return db.execute(
        f"""
        SELECT
            es.exercise_name,
            es.rest_seconds,
            es.equipment,
            COALESCE(
                (
                    SELECT ws.body_part
                    FROM workout_sets ws
                    JOIN exercises e ON e.id = ws.exercise_id
                    JOIN workout_sessions s ON s.id = ws.session_id
                    WHERE e.name = es.exercise_name
                    ORDER BY s.workout_date DESC, ws.sort_order DESC, ws.id DESC
                    LIMIT 1
                ),
                '기타'
            ) AS body_part
        FROM exercise_settings es
        WHERE es.is_favorite = 1
        {location_filter}
        ORDER BY es.updated_at DESC, es.exercise_name
        """,
        params,
    ).fetchall()
