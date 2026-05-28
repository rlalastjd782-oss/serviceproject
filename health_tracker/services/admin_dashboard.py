from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from health_tracker.services.accounts import account_db_path


NEEDS_ACTION_STATUSES = {"empty", "low", "db_missing", "disabled"}


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


def _sort_user_summaries(users: list[dict[str, object]], sort_key: str) -> list[dict[str, object]]:
    if sort_key == "last_record":
        return sorted(users, key=lambda item: str(item["last_record_date"] or ""), reverse=True)
    if sort_key == "last_login":
        return sorted(users, key=lambda item: str(item["account"]["last_login_at"] or ""), reverse=True)
    if sort_key == "sets":
        return sorted(users, key=lambda item: int(item["set_count"] or 0), reverse=True)
    if sort_key == "name":
        return sorted(
            users,
            key=lambda item: str(item["account"]["display_name"] or item["account"]["username"]).casefold(),
        )
    return sorted(users, key=lambda item: int(item["account"]["id"]))


def _filter_user_summaries(
    users: list[dict[str, object]],
    query: str = "",
    status: str = "all",
) -> list[dict[str, object]]:
    query = query.strip().casefold()
    filtered = []
    for item in users:
        account = item["account"]
        haystack = " ".join(
            [
                str(account["username"] or ""),
                str(account["display_name"] or ""),
                str(account["memo"] or ""),
                str(item["status_label"] or ""),
            ]
        ).casefold()
        if query and query not in haystack:
            continue
        if status == "active" and not int(account["is_active"] or 0):
            continue
        if status == "disabled" and int(account["is_active"] or 0):
            continue
        if status == "needs_action" and item["status"] not in NEEDS_ACTION_STATUSES:
            continue
        if status not in {"all", "active", "disabled", "needs_action"} and item["status"] != status:
            continue
        filtered.append(item)
    return filtered


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
        base.update(
            {
                "workout_days": workout_days,
                "set_count": set_count,
                "meal_count": meal_count,
                "meal_days": meal_days,
                "last_record_date": max(last_workout, last_meal),
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


def build_admin_dashboard(
    main_database: Path,
    accounts: list[sqlite3.Row],
    query: str = "",
    status: str = "all",
    sort_key: str = "id",
) -> dict[str, object]:
    user_accounts = [account for account in accounts if account["role"] == "user"]
    admin_accounts = [account for account in accounts if account["role"] == "admin"]
    all_users = [account_usage_summary(main_database, account) for account in user_accounts]
    users = _sort_user_summaries(_filter_user_summaries(all_users, query, status), sort_key)
    needs_action_users = _sort_user_summaries(
        [item for item in all_users if item["status"] in NEEDS_ACTION_STATUSES],
        "last_login",
    )[:6]
    disabled_users = sum(1 for account in user_accounts if int(account["is_active"] or 0) == 0)
    low_activity_users = sum(1 for item in all_users if item["status"] in {"empty", "low", "db_missing"})
    total_sets = sum(int(item["set_count"]) for item in all_users)
    total_meals = sum(int(item["meal_count"]) for item in all_users)
    recording_users = sum(1 for item in all_users if int(item["workout_days"]) or int(item["meal_count"]))
    dormant_users = sum(1 for item in all_users if not item["last_record_date"])
    active_rate = round(recording_users / len(user_accounts) * 100) if user_accounts else 0
    return {
        "users": users,
        "all_users": all_users,
        "needs_action_users": needs_action_users,
        "filters": {"q": query, "status": status, "sort": sort_key},
        "filtered_users": len(users),
        "admin_count": len(admin_accounts),
        "total_users": len(user_accounts),
        "active_users": sum(1 for account in user_accounts if int(account["is_active"] or 0) == 1),
        "disabled_users": disabled_users,
        "total_workout_days": sum(int(item["workout_days"]) for item in all_users),
        "total_sets": total_sets,
        "total_meals": total_meals,
        "recording_users": recording_users,
        "active_rate": active_rate,
        "dormant_users": dormant_users,
        "low_activity_users": low_activity_users,
        "contact_points": [
            {
                "label": "??? ??",
                "value": f"{active_rate}%",
                "detail": f"?? ??? {recording_users}? / ?? {len(user_accounts)}?",
            },
            {
                "label": "?? ??",
                "value": f"{low_activity_users}?",
                "detail": f"???/???/DB ?? ??, ??? {disabled_users}?",
            },
            {
                "label": "??? ??",
                "value": f"{total_sets}??",
                "detail": f"?? {total_meals}?, ?? ?? ?? {dormant_users}?",
            },
        ],
    }
