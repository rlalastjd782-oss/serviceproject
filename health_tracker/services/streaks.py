from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta


def build_logging_streak_from_db(db: sqlite3.Connection, today_date: str) -> dict[str, object]:
    rows = db.execute(
        """
        SELECT DISTINCT s.workout_date AS active_date
        FROM workout_sessions s
        JOIN workout_sets ws ON ws.session_id = s.id
        UNION
        SELECT DISTINCT meal_date AS active_date
        FROM meal_entries
        """
    ).fetchall()
    active_dates = {row["active_date"] for row in rows if row["active_date"]}
    if not active_dates:
        return {"current_streak": 0, "last_active_date": None, "status": "새로 시작"}

    today = datetime.strptime(today_date, "%Y-%m-%d").date()
    last_active = max(datetime.strptime(value, "%Y-%m-%d").date() for value in active_dates)
    gap_days = (today - last_active).days

    if gap_days >= 2:
        return {"current_streak": 0, "last_active_date": last_active.isoformat(), "status": "끊김"}

    streak = 0
    cursor_date = last_active
    while cursor_date.isoformat() in active_dates:
        streak += 1
        cursor_date -= timedelta(days=1)

    status = "오늘 기록 중" if gap_days == 0 else "어제까지 기록 · 오늘 이어가면 계속됩니다"
    return {"current_streak": streak, "last_active_date": last_active.isoformat(), "status": status}
