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


def merge_exercise_names(db: sqlite3.Connection, source_names: list[str], target_name: str) -> dict[str, int | str]:
    clean_target = target_name.strip()
    clean_sources = [name.strip() for name in source_names if name.strip()]
    clean_sources = [name for name in dict.fromkeys(clean_sources) if name != clean_target]
    if not clean_target or not clean_sources:
        return {"target": clean_target, "sources": 0, "sets": 0, "prs": 0, "plans": 0, "routines": 0}

    db.execute("INSERT OR IGNORE INTO exercises (name) VALUES (?)", (clean_target,))
    target_id = db.execute("SELECT id FROM exercises WHERE name = ?", (clean_target,)).fetchone()["id"]
    source_rows = db.execute(
        f"SELECT id, name FROM exercises WHERE name IN ({', '.join('?' for _ in clean_sources)})",
        tuple(clean_sources),
    ).fetchall()
    source_ids = [int(row["id"]) for row in source_rows if int(row["id"]) != int(target_id)]
    if not source_ids:
        return {"target": clean_target, "sources": 0, "sets": 0, "prs": 0, "plans": 0, "routines": 0}

    id_placeholders = ", ".join("?" for _ in source_ids)
    name_placeholders = ", ".join("?" for _ in clean_sources)
    set_count = db.execute(
        f"SELECT COUNT(*) FROM workout_sets WHERE exercise_id IN ({id_placeholders})",
        tuple(source_ids),
    ).fetchone()[0]
    pr_count = db.execute(
        f"SELECT COUNT(*) FROM pr_events WHERE exercise_id IN ({id_placeholders}) OR exercise_name IN ({name_placeholders})",
        (*source_ids, *clean_sources),
    ).fetchone()[0]
    routine_count = db.execute(
        f"SELECT COUNT(*) FROM routine_items WHERE exercise_name IN ({name_placeholders})",
        tuple(clean_sources),
    ).fetchone()[0]
    plan_count = db.execute(
        f"SELECT COUNT(*) FROM workout_plan_items WHERE exercise_name IN ({name_placeholders})",
        tuple(clean_sources),
    ).fetchone()[0]

    db.execute(f"UPDATE workout_sets SET exercise_id = ? WHERE exercise_id IN ({id_placeholders})", (target_id, *source_ids))
    db.execute(
        f"UPDATE pr_events SET exercise_id = ?, exercise_name = ? WHERE exercise_id IN ({id_placeholders}) OR exercise_name IN ({name_placeholders})",
        (target_id, clean_target, *source_ids, *clean_sources),
    )
    db.execute(
        f"UPDATE routine_items SET exercise_name = ? WHERE exercise_name IN ({name_placeholders})",
        (clean_target, *clean_sources),
    )
    db.execute(
        f"UPDATE workout_plan_items SET exercise_name = ? WHERE exercise_name IN ({name_placeholders})",
        (clean_target, *clean_sources),
    )
    db.execute(
        f"""
        INSERT INTO exercise_settings (
            exercise_name, location_id, rest_seconds, is_favorite, equipment,
            target_weight, target_reps, target_sets, updated_at
        )
        SELECT ?, location_id, rest_seconds, is_favorite, equipment,
            target_weight, target_reps, target_sets, CURRENT_TIMESTAMP
        FROM exercise_settings
        WHERE exercise_name IN ({name_placeholders})
          AND NOT EXISTS (SELECT 1 FROM exercise_settings WHERE exercise_name = ?)
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (clean_target, *clean_sources, clean_target),
    )
    db.execute(
        f"""
        INSERT INTO exercise_notes (exercise_name, note, updated_at)
        SELECT ?, note, CURRENT_TIMESTAMP
        FROM exercise_notes
        WHERE exercise_name IN ({name_placeholders})
          AND NOT EXISTS (SELECT 1 FROM exercise_notes WHERE exercise_name = ?)
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (clean_target, *clean_sources, clean_target),
    )
    db.execute(f"DELETE FROM exercise_settings WHERE exercise_name IN ({name_placeholders})", tuple(clean_sources))
    db.execute(f"DELETE FROM exercise_notes WHERE exercise_name IN ({name_placeholders})", tuple(clean_sources))
    db.execute(f"DELETE FROM exercises WHERE id IN ({id_placeholders})", tuple(source_ids))
    db.commit()
    return {
        "target": clean_target,
        "sources": len(source_ids),
        "sets": int(set_count or 0),
        "prs": int(pr_count or 0),
        "plans": int(plan_count or 0),
        "routines": int(routine_count or 0),
    }
