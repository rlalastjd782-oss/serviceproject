from __future__ import annotations

import sqlite3


def list_exercise_smart_defaults_from_db(db: sqlite3.Connection, location_id: int | None = None) -> dict[str, dict[str, object]]:
    params: list[object] = []
    location_clause = ""
    if location_id is not None:
        location_clause = "AND (s.location_id = ? OR s.location_id IS NULL)"
        params.append(location_id)

    rows = db.execute(
        f"""
        WITH ranked AS (
            SELECT
                e.name AS exercise_name,
                ws.body_part,
                ws.equipment,
                ws.weight,
                ws.reps,
                ws.cardio_incline,
                ws.cardio_speed,
                ws.cardio_minutes,
                ws.set_type,
                s.workout_date,
                ROW_NUMBER() OVER (
                    PARTITION BY e.name
                    ORDER BY s.workout_date DESC, ws.sort_order DESC, ws.id DESC
                ) AS rn
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            JOIN exercises e ON e.id = ws.exercise_id
            WHERE 1 = 1 {location_clause}
        )
        SELECT
            r.*,
            (
                SELECT COUNT(*)
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                JOIN exercises e2 ON e2.id = ws2.exercise_id
                WHERE e2.name = r.exercise_name
                  AND s2.workout_date = r.workout_date
                  {location_clause.replace("s.location_id", "s2.location_id")}
            ) AS set_count,
            COALESCE(es.rest_seconds, 0) AS rest_seconds,
            COALESCE(es.target_sets, 0) AS target_sets,
            COALESCE(es.target_weight, 0) AS target_weight,
            COALESCE(es.target_reps, 0) AS target_reps
        FROM ranked r
        LEFT JOIN exercise_settings es
          ON es.exercise_name = r.exercise_name
         AND (es.location_id = ? OR es.location_id IS NULL)
        WHERE r.rn = 1
        ORDER BY r.workout_date DESC, r.exercise_name ASC
        """,
        [*params, *params, location_id or 0],
    ).fetchall()

    defaults: dict[str, dict[str, object]] = {}
    for row in rows:
        target_sets = int(row["target_sets"] or 0)
        target_weight = float(row["target_weight"] or 0)
        target_reps = int(row["target_reps"] or 0)
        defaults[row["exercise_name"]] = {
            "body_part": row["body_part"],
            "equipment": row["equipment"] or "",
            "weight": target_weight or row["weight"],
            "reps": target_reps or row["reps"],
            "cardio_incline": row["cardio_incline"],
            "cardio_speed": row["cardio_speed"],
            "cardio_minutes": row["cardio_minutes"],
            "set_type": row["set_type"] or "",
            "set_count": target_sets or max(1, min(20, int(row["set_count"] or 1))),
            "rest_seconds": int(row["rest_seconds"] or 0),
            "last_date": row["workout_date"],
        }
    return defaults
