from __future__ import annotations

import sqlite3


def reorder_set_within_exercise_in_db(db: sqlite3.Connection, set_id: int, requested_set_number: int) -> None:
    current = db.execute(
        """
        SELECT session_id, exercise_id, COALESCE(NULLIF(body_part, ''), '기타') AS body_part
        FROM workout_sets
        WHERE id = ?
        """,
        (set_id,),
    ).fetchone()
    if not current:
        return

    rows = db.execute(
        """
        SELECT id, sort_order
        FROM workout_sets
        WHERE session_id = ?
          AND exercise_id = ?
          AND COALESCE(NULLIF(body_part, ''), '기타') = ?
        ORDER BY sort_order, id
        """,
        (current["session_id"], current["exercise_id"], current["body_part"]),
    ).fetchall()
    if len(rows) <= 1:
        return

    ordered_ids = [int(row["id"]) for row in rows]
    if set_id not in ordered_ids:
        return
    ordered_ids.remove(set_id)
    target_index = min(max(requested_set_number, 1), len(rows)) - 1
    ordered_ids.insert(target_index, set_id)
    sort_orders = [int(row["sort_order"] or 0) for row in rows]
    for new_order, row_id in zip(sort_orders, ordered_ids):
        db.execute("UPDATE workout_sets SET sort_order = ? WHERE id = ?", (new_order, row_id))


def get_or_create_exercise_in_db(db: sqlite3.Connection, name: str) -> int:
    existing = db.execute("SELECT id FROM exercises WHERE name = ?", (name,)).fetchone()
    if existing:
        return int(existing["id"])
    cursor = db.execute("INSERT INTO exercises (name) VALUES (?)", (name,))
    db.commit()
    return int(cursor.lastrowid)


def get_or_create_session_from_db(
    db: sqlite3.Connection,
    workout_date: str | None,
    location_id: int | None,
    normalize_date,
    get_location,
    get_recent_or_default_location,
    get_session_by_date,
) -> sqlite3.Row:
    date_value = normalize_date(workout_date)
    location = get_location(db, location_id) if location_id else get_recent_or_default_location(db)
    existing = db.execute(
        "SELECT * FROM workout_sessions WHERE workout_date = ?",
        (date_value,),
    ).fetchone()
    if existing:
        if location_id and existing["location_id"] != location["id"]:
            db.execute(
                "UPDATE workout_sessions SET location_id = ? WHERE id = ?",
                (location["id"], existing["id"]),
            )
            db.commit()
            return get_session_by_date(date_value)
        return existing

    db.execute(
        "INSERT INTO workout_sessions (workout_date, location_id) VALUES (?, ?)",
        (date_value, location["id"]),
    )
    db.commit()
    return db.execute(
        "SELECT * FROM workout_sessions WHERE workout_date = ?",
        (date_value,),
    ).fetchone()


def get_session_by_date_from_db(db: sqlite3.Connection, workout_date: str) -> sqlite3.Row | None:
    return db.execute(
        "SELECT * FROM workout_sessions WHERE workout_date = ?",
        (workout_date,),
    ).fetchone()


def get_session_by_id_from_db(db: sqlite3.Connection, session_id: int) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM workout_sessions WHERE id = ?", (session_id,)).fetchone()


def mark_session_completed_in_db(db: sqlite3.Connection, session_id: int, completed: bool) -> None:
    db.execute("UPDATE workout_sessions SET completed = ? WHERE id = ?", (1 if completed else 0, session_id))
    db.commit()


def update_session_duration_in_db(db: sqlite3.Connection, session_id: int, duration_seconds: int) -> None:
    db.execute(
        "UPDATE workout_sessions SET duration_seconds = ? WHERE id = ?",
        (max(0, int(duration_seconds or 0)), session_id),
    )
    db.commit()


def list_exercises_from_db(db: sqlite3.Connection, location_id: int | None = None) -> list[sqlite3.Row]:
    if location_id:
        return db.execute(
            """
            SELECT DISTINCT e.id, e.name
            FROM exercises e
            JOIN workout_sets ws ON ws.exercise_id = e.id
            JOIN workout_sessions s ON s.id = ws.session_id
            WHERE s.location_id = ?
            ORDER BY e.name
            """,
            (location_id,),
        ).fetchall()
    return db.execute("SELECT id, name FROM exercises ORDER BY name").fetchall()


def list_exercises_by_body_part_from_db(
    db: sqlite3.Connection,
    body_parts: list[str],
    location_id: int | None = None,
) -> dict[str, list[str]]:
    location_where = "WHERE s.location_id = ?" if location_id else ""
    params = (location_id,) if location_id else ()
    rows = db.execute(
        f"""
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.name,
            COUNT(ws.id) AS use_count,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        {location_where}
        GROUP BY body_part, e.name
        ORDER BY body_part, last_date DESC, use_count DESC, e.name
        """,
        params,
    ).fetchall()
    exercises_by_part = {part: [] for part in body_parts}
    for row in rows:
        part = row["body_part"] or "기타"
        exercises_by_part.setdefault(part, []).append(row["name"])
    return exercises_by_part


def list_recent_sets_by_exercise_from_db(
    db: sqlite3.Connection,
    limit: int = 6,
    location_id: int | None = None,
) -> dict[str, list[dict[str, float | int | None]]]:
    location_filter = "AND s.location_id = ?" if location_id else ""
    params = (location_id,) if location_id else ()
    rows = db.execute(
        f"""
        SELECT e.name, ws.weight, ws.reps, s.workout_date, ws.sort_order
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.weight IS NOT NULL OR ws.reps IS NOT NULL
        {location_filter}
        ORDER BY s.workout_date DESC, ws.sort_order ASC, ws.id ASC
        """,
        params,
    ).fetchall()
    grouped: dict[str, list[dict[str, float | int | None]]] = {}
    seen_dates: set[str] = set()
    for row in rows:
        name = row["name"]
        if name in grouped and len(grouped[name]) >= limit:
            continue
        marker = f"{name}:{row['workout_date']}"
        if marker in seen_dates:
            grouped.setdefault(name, []).append({"weight": row["weight"], "reps": row["reps"]})
        elif name not in grouped:
            grouped[name] = [{"weight": row["weight"], "reps": row["reps"]}]
            seen_dates.add(marker)
    return grouped


def list_exercise_stats_by_name_from_db(
    db: sqlite3.Connection,
    location_id: int | None = None,
) -> dict[str, dict[str, object]]:
    location_filter = "AND s.location_id = ?" if location_id else ""
    recent_location_filter = "AND s2.location_id = ?" if location_id else ""
    params: tuple[object, ...] = (location_id, location_id) if location_id else ()
    rows = db.execute(
        f"""
        SELECT
            e.name,
            MAX(ws.weight) AS best_weight,
            MAX(ws.reps) AS best_reps,
            MAX(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)) AS best_volume,
            (
                SELECT s2.workout_date || ' · ' || COALESCE(ws2.weight, 0) || 'kg ' || COALESCE(ws2.reps, 0) || '회'
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id
                  AND (ws2.weight IS NOT NULL OR ws2.reps IS NOT NULL)
                  {recent_location_filter}
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS recent
        FROM exercises e
        JOIN workout_sets ws ON ws.exercise_id = e.id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.weight IS NOT NULL OR ws.reps IS NOT NULL
        {location_filter}
        GROUP BY e.id, e.name
        """,
        params,
    ).fetchall()
    return {
        row["name"]: {
            "recent": row["recent"],
            "best_weight": row["best_weight"],
            "best_reps": row["best_reps"],
            "best_volume": row["best_volume"],
        }
        for row in rows
    }


def list_sets_for_session_from_db(db: sqlite3.Connection, session_id: int) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT ws.*, e.name AS exercise_name
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE ws.session_id = ?
        ORDER BY ws.sort_order ASC, ws.id ASC
        """,
        (session_id,),
    ).fetchall()


def grouped_sets_for_session_from_db(db: sqlite3.Connection, session_id: int | None) -> list[dict[str, object]]:
    if session_id is None:
        return []
    groups: list[dict[str, object]] = []
    group_map: dict[tuple[str, str], dict[str, object]] = {}
    for row in list_sets_for_session_from_db(db, session_id):
        key = (row["exercise_name"], row["body_part"] or "기타")
        if key not in group_map:
            group = {"exercise_name": row["exercise_name"], "body_part": row["body_part"] or "기타", "sets": []}
            group_map[key] = group
            groups.append(group)
        group_map[key]["sets"].append(row)
    return groups


def list_recent_sessions_from_db(db: sqlite3.Connection, limit: int = 10) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT
            s.id,
            s.workout_date,
            COALESCE(s.duration_seconds, 0) AS duration_seconds,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories
        FROM workout_sessions s
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        GROUP BY s.id, s.duration_seconds
        HAVING COUNT(ws.id) > 0 OR COALESCE(s.completed, 0) = 1
        ORDER BY s.workout_date DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
