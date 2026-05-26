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
