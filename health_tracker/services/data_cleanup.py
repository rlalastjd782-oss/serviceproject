from __future__ import annotations

import re
import sqlite3


def normalize_exercise_key(name: str) -> str:
    return re.sub(r"[\s\-_()/]+", "", name or "").casefold()


def list_duplicate_exercise_candidates(db: sqlite3.Connection, limit: int = 10) -> list[dict[str, object]]:
    rows = db.execute(
        """
        SELECT e.name,
               COUNT(ws.id) AS set_count,
               MAX(s.workout_date) AS last_date
        FROM exercises e
        LEFT JOIN workout_sets ws ON ws.exercise_id = e.id
        LEFT JOIN workout_sessions s ON s.id = ws.session_id
        GROUP BY e.id
        ORDER BY LOWER(e.name)
        """
    ).fetchall()
    grouped: dict[str, dict[str, object]] = {}
    for row in rows:
        key = normalize_exercise_key(row["name"])
        if not key:
            continue
        bucket = grouped.setdefault(key, {"variants": [], "set_count": 0, "last_date": ""})
        bucket["variants"].append(row["name"])
        bucket["set_count"] = int(bucket["set_count"]) + int(row["set_count"] or 0)
        if row["last_date"] and str(row["last_date"]) > str(bucket["last_date"]):
            bucket["last_date"] = row["last_date"]

    candidates = [
        {
            "variants": sorted(set(item["variants"])),
            "set_count": item["set_count"],
            "last_date": item["last_date"] or "-",
        }
        for item in grouped.values()
        if len(set(item["variants"])) > 1
    ]
    candidates.sort(key=lambda item: (int(item["set_count"]), item["last_date"]), reverse=True)
    return candidates[:limit]


def list_outlier_set_candidates(db: sqlite3.Connection, limit: int = 10) -> list[dict[str, object]]:
    rows = db.execute(
        """
        SELECT ws.id,
               s.workout_date,
               e.name AS exercise_name,
               ws.weight,
               ws.reps,
               ws.cardio_minutes,
               ws.rpe,
               ws.memo,
               COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0) AS volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE COALESCE(ws.weight, 0) > 350
           OR COALESCE(ws.reps, 0) > 100
           OR COALESCE(ws.cardio_minutes, 0) > 240
           OR COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0) > 10000
           OR COALESCE(ws.rpe, 0) > 10
        ORDER BY s.workout_date DESC, ws.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "date": row["workout_date"],
            "exercise_name": row["exercise_name"],
            "weight": row["weight"],
            "reps": row["reps"],
            "cardio_minutes": row["cardio_minutes"],
            "rpe": row["rpe"],
            "memo": row["memo"],
            "volume": row["volume"],
        }
        for row in rows
    ]
