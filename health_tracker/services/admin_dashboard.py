from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from health_tracker.services.accounts import account_db_path


def _connect(path: Path) -> sqlite3.Connection | None:
    if not path.exists():
        return None
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


def _scalar(db: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()) -> int:
    try:
        row = db.execute(sql, params).fetchone()
    except sqlite3.Error:
        return 0
    return int((row[0] if row else 0) or 0)


def _text(db: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()) -> str:
    try:
        row = db.execute(sql, params).fetchone()
    except sqlite3.Error:
        return ""
    return str((row[0] if row else "") or "")


def _rows(db: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()) -> list[sqlite3.Row]:
    try:
        return db.execute(sql, params).fetchall()
    except sqlite3.Error:
        return []


def account_usage_summary(main_database: Path, account: sqlite3.Row) -> dict[str, object]:
    db_path = account_db_path(main_database, int(account["id"]))
    base = {
        "account": account,
        "db_exists": db_path.exists(),
        "db_path": str(db_path),
        "workout_days": 0,
        "set_count": 0,
        "meal_count": 0,
        "meal_days": 0,
        "last_record_date": "",
        "top_body_parts": [],
        "top_equipment": [],
        "recent_workouts": [],
        "recent_meals": [],
        "status": "db_missing",
        "status_label": "DB 확인 필요",
    }
    db = _connect(db_path)
    if db is None:
        return base
    with closing(db):
        workout_days = _scalar(
            db,
            """
            SELECT COUNT(DISTINCT s.workout_date)
            FROM workout_sessions s
            WHERE EXISTS (SELECT 1 FROM workout_sets ws WHERE ws.session_id = s.id)
            """,
        )
        set_count = _scalar(db, "SELECT COUNT(*) FROM workout_sets")
        meal_count = _scalar(db, "SELECT COUNT(*) FROM meal_entries")
        meal_days = _scalar(db, "SELECT COUNT(DISTINCT meal_date) FROM meal_entries")
        last_workout = _text(db, "SELECT MAX(workout_date) FROM workout_sessions")
        last_meal = _text(db, "SELECT MAX(meal_date) FROM meal_entries")
        last_record_date = max(last_workout, last_meal)
        base.update(
            {
                "workout_days": workout_days,
                "set_count": set_count,
                "meal_count": meal_count,
                "meal_days": meal_days,
                "last_record_date": last_record_date,
                "top_body_parts": _rows(
                    db,
                    """
                    SELECT COALESCE(NULLIF(body_part, ''), '기타') AS label, COUNT(*) AS count
                    FROM workout_sets
                    GROUP BY label
                    ORDER BY count DESC, label
                    LIMIT 5
                    """,
                ),
                "top_equipment": _rows(
                    db,
                    """
                    SELECT COALESCE(NULLIF(equipment, ''), '미지정') AS label, COUNT(*) AS count
                    FROM workout_sets
                    GROUP BY label
                    ORDER BY count DESC, label
                    LIMIT 5
                    """,
                ),
                "recent_workouts": _rows(
                    db,
                    """
                    SELECT s.workout_date, COUNT(ws.id) AS set_count, GROUP_CONCAT(DISTINCT e.name) AS exercises
                    FROM workout_sessions s
                    JOIN workout_sets ws ON ws.session_id = s.id
                    JOIN exercises e ON e.id = ws.exercise_id
                    GROUP BY s.workout_date
                    ORDER BY s.workout_date DESC
                    LIMIT 7
                    """,
                ),
                "recent_meals": _rows(
                    db,
                    """
                    SELECT meal_date, COUNT(*) AS meal_count, COALESCE(SUM(calories), 0) AS calories
                    FROM meal_entries
                    GROUP BY meal_date
                    ORDER BY meal_date DESC
                    LIMIT 7
                    """,
                ),
            }
        )
    if not account["is_active"]:
        status, label = "disabled", "비활성"
    elif workout_days == 0 and meal_count == 0:
        status, label = "empty", "미사용"
    elif workout_days < 3 and meal_count < 3:
        status, label = "low", "기록 부족"
    else:
        status, label = "active", "정상"
    base.update({"status": status, "status_label": label})
    return base


def build_admin_dashboard(main_database: Path, accounts: list[sqlite3.Row]) -> dict[str, object]:
    users = [account_usage_summary(main_database, account) for account in accounts]
    return {
        "users": users,
        "total_users": len(accounts),
        "active_users": sum(1 for account in accounts if int(account["is_active"] or 0) == 1),
        "disabled_users": sum(1 for account in accounts if int(account["is_active"] or 0) == 0),
        "total_workout_days": sum(int(item["workout_days"]) for item in users),
        "total_sets": sum(int(item["set_count"]) for item in users),
        "total_meals": sum(int(item["meal_count"]) for item in users),
        "recording_users": sum(1 for item in users if int(item["workout_days"]) or int(item["meal_count"])),
    }
