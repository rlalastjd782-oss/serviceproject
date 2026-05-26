from __future__ import annotations

import sqlite3


def list_pr_events_from_db(db: sqlite3.Connection, workout_date: str) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT *
        FROM pr_events
        WHERE workout_date = ?
        ORDER BY id DESC
        """,
        (workout_date,),
    ).fetchall()


def list_recent_pr_events_from_db(db: sqlite3.Connection, limit: int = 12) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT *
        FROM pr_events
        ORDER BY workout_date DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def list_recent_pr_events_filtered_from_db(
    db: sqlite3.Connection,
    body_part: str = "",
    query: str = "",
    limit: int = 30,
) -> list[sqlite3.Row]:
    filters = []
    params: list[object] = []
    if body_part:
        filters.append("COALESCE(NULLIF(ws.body_part, ''), '기타') = ?")
        params.append(body_part)
    if query:
        filters.append("pe.exercise_name LIKE ?")
        params.append(f"%{query}%")
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.append(limit)
    return db.execute(
        f"""
        SELECT pe.*
        FROM pr_events pe
        LEFT JOIN workout_sets ws ON ws.id = pe.set_id
        {where_clause}
        ORDER BY pe.workout_date DESC, pe.id DESC
        LIMIT ?
        """,
        params,
    ).fetchall()


def list_exercise_pr_history_from_db(db: sqlite3.Connection, exercise_id: int | None, limit: int = 12) -> list[sqlite3.Row]:
    if not exercise_id:
        return []
    return db.execute(
        """
        SELECT *
        FROM pr_events
        WHERE exercise_id = ?
        ORDER BY workout_date DESC, id DESC
        LIMIT ?
        """,
        (exercise_id, limit),
    ).fetchall()


def list_exercise_pr_summary_from_db(
    db: sqlite3.Connection,
    body_part: str = "",
    query: str = "",
    limit: int = 80,
) -> list[sqlite3.Row]:
    filters = ["ws.weight IS NOT NULL", "ws.reps IS NOT NULL"]
    params: list[object] = []
    if body_part:
        filters.append("COALESCE(NULLIF(ws.body_part, ''), '기타') = ?")
        params.append(body_part)
    if query:
        filters.append("e.name LIKE ?")
        params.append(f"%{query}%")
    where_clause = " AND ".join(filters)
    params.append(limit)
    return db.execute(
        f"""
        SELECT
            e.id,
            e.name,
            COALESCE(NULLIF(MAX(ws.body_part), ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COUNT(DISTINCT s.workout_date) AS workout_days,
            MAX(s.workout_date) AS last_date,
            COALESCE(MAX(ws.weight), 0) AS best_weight,
            COALESCE(MAX(ws.reps), 0) AS best_reps,
            COALESCE(MAX(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS best_volume,
            COALESCE(MAX(ws.weight * (1 + ws.reps / 30.0)), 0) AS estimated_1rm
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE {where_clause}
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') != '유산소'
        GROUP BY e.id, e.name
        ORDER BY best_weight DESC, best_volume DESC, last_date DESC, e.name
        LIMIT ?
        """,
        params,
    ).fetchall()


def list_pr_exercise_choices_from_db(db: sqlite3.Connection, body_part: str = "", query: str = "") -> list[sqlite3.Row]:
    filters = ["ws.weight IS NOT NULL", "ws.reps IS NOT NULL", "COALESCE(NULLIF(ws.body_part, ''), '기타') != '유산소'"]
    params: list[object] = []
    if body_part:
        filters.append("COALESCE(NULLIF(ws.body_part, ''), '기타') = ?")
        params.append(body_part)
    if query:
        filters.append("e.name LIKE ?")
        params.append(f"%{query}%")
    return db.execute(
        f"""
        SELECT DISTINCT e.id, e.name
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE {' AND '.join(filters)}
        ORDER BY e.name
        """,
        params,
    ).fetchall()


def build_pr_cards_from_rows(rows: list[sqlite3.Row]) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    for row in rows:
        unit = "kg" if row["record_type"] in {"최고 중량", "최고 볼륨"} else "회"
        cards.append(
            {
                "exercise_name": row["exercise_name"],
                "record_type": row["record_type"],
                "record_value": float(row["record_value"] or 0),
                "unit": unit,
            }
        )
    return cards


def build_pr_dashboard_from_rows(pr_rows: list[sqlite3.Row], recent_events: list[sqlite3.Row]) -> dict[str, object]:
    best_weight = max(pr_rows, key=lambda row: float(row["best_weight"] or 0), default=None)
    best_volume = max(pr_rows, key=lambda row: float(row["best_volume"] or 0), default=None)
    best_1rm = max(pr_rows, key=lambda row: float(row["estimated_1rm"] or 0), default=None)
    recent_30_dates = {row["workout_date"] for row in recent_events[:30]}
    return {
        "exercise_count": len(pr_rows),
        "recent_event_count": len(recent_events),
        "recent_day_count": len(recent_30_dates),
        "best_weight": best_weight,
        "best_volume": best_volume,
        "best_1rm": best_1rm,
    }
