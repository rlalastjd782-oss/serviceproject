from __future__ import annotations

import sqlite3

from health_tracker.security import make_password_hash, verify_password_hash


SETTINGS_PASSWORD_KEY = "settings_password_hash"


def get_app_setting(db: sqlite3.Connection, key: str, default: str = "") -> str:
    row = db.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else default


def save_app_setting(db: sqlite3.Connection, key: str, value: str) -> None:
    db.execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """,
        (key, value),
    )
    db.commit()


def has_settings_password(db: sqlite3.Connection) -> bool:
    return bool(get_app_setting(db, SETTINGS_PASSWORD_KEY))


def set_settings_password(db: sqlite3.Connection, password: str) -> bool:
    password = password.strip()
    if len(password) < 4:
        return False
    save_app_setting(db, SETTINGS_PASSWORD_KEY, make_password_hash(password))
    return True


def verify_settings_password(db: sqlite3.Connection, password: str) -> bool:
    stored_hash = get_app_setting(db, SETTINGS_PASSWORD_KEY)
    return bool(stored_hash and verify_password_hash(password, stored_hash))


def reset_settings_password(db: sqlite3.Connection) -> None:
    save_app_setting(db, SETTINGS_PASSWORD_KEY, "")
