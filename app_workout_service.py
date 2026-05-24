from __future__ import annotations

import sqlite3


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
