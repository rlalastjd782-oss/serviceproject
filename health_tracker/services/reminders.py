from __future__ import annotations

import sqlite3


REMINDER_DEFAULTS = {
    "workout": {"enabled": 0, "time_text": "18:30", "message": "운동 기록 시간입니다."},
    "meal": {"enabled": 0, "time_text": "12:30", "message": "식단 기록을 확인하세요."},
    "weekly": {"enabled": 0, "time_text": "20:00", "message": "주간 기록을 점검하세요."},
}


def list_reminder_settings_from_db(db: sqlite3.Connection) -> dict[str, dict[str, object]]:
    rows = db.execute("SELECT key, enabled, time_text, message FROM reminder_settings").fetchall()
    settings = {key: value.copy() for key, value in REMINDER_DEFAULTS.items()}
    for row in rows:
        settings[row["key"]] = {
            "enabled": int(row["enabled"] or 0),
            "time_text": row["time_text"] or REMINDER_DEFAULTS.get(row["key"], {}).get("time_text", ""),
            "message": row["message"] or REMINDER_DEFAULTS.get(row["key"], {}).get("message", ""),
        }
    return settings


def save_reminder_settings_to_db(db: sqlite3.Connection, key: str, enabled: bool, time_text: str, message: str) -> None:
    if key not in REMINDER_DEFAULTS:
        return
    db.execute(
        """
        INSERT INTO reminder_settings (key, enabled, time_text, message, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            enabled = excluded.enabled,
            time_text = excluded.time_text,
            message = excluded.message,
            updated_at = CURRENT_TIMESTAMP
        """,
        (key, 1 if enabled else 0, time_text[:5], message[:120]),
    )
    db.commit()
