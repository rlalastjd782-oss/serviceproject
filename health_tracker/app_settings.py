from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable

from flask import g, has_request_context, session

from health_tracker.services.accounts import ensure_primary_account
from health_tracker.services.pagination import page_params
from health_tracker.services.preferences import app_preferences as build_app_preferences
from health_tracker.services.preferences import save_app_preferences as save_app_preferences_to_db
from health_tracker.services.settings import (
    get_app_setting as get_app_setting_from_db,
    has_settings_password as has_settings_password_in_db,
    reset_settings_password as reset_settings_password_in_db,
    save_app_setting as save_app_setting_to_db,
    set_settings_password as set_settings_password_in_db,
    verify_settings_password as verify_settings_password_in_db,
)
from health_tracker.utils import parse_int

_get_db: Callable[[], sqlite3.Connection] | None = None
_database: Path | None = None


def configure_settings_helpers(get_db_func: Callable[[], sqlite3.Connection], database: Path) -> None:
    global _get_db, _database
    _get_db = get_db_func
    _database = database


def _db() -> sqlite3.Connection:
    if _get_db is None:
        raise RuntimeError("Settings helpers are not configured.")
    return _get_db()


def _account_database() -> Path:
    if _database is None:
        raise RuntimeError("Settings helpers are not configured.")
    return _database


def clear_preference_caches() -> None:
    if has_request_context():
        g.pop("app_setting_cache", None)
        g.pop("app_preferences_cache", None)


def get_app_setting(key: str, default: str = "") -> str:
    if has_request_context():
        cache = getattr(g, "app_setting_cache", None)
        if cache is None:
            cache = {}
            g.app_setting_cache = cache
        cache_key = (key, default)
        if cache_key in cache:
            return cache[cache_key]
        value = get_app_setting_from_db(_db(), key, default)
        cache[cache_key] = value
        return value
    return get_app_setting_from_db(_db(), key, default)


def save_app_setting(key: str, value: str) -> None:
    save_app_setting_to_db(_db(), key, value)
    clear_preference_caches()


def get_app_preferences() -> dict[str, object]:
    if has_request_context() and hasattr(g, "app_preferences_cache"):
        return g.app_preferences_cache
    preferences = build_app_preferences(_db())
    if has_request_context():
        g.app_preferences_cache = preferences
    return preferences


def configured_page_params(args) -> tuple[int, int]:
    return page_params(args, int(get_app_preferences()["default_per_page"]))


def normalize_summary_days(value: str | None) -> int:
    options = [int(item) for item in get_app_preferences()["summary_day_options"]]
    parsed = parse_int(value) or options[0]
    return min(max(parsed, min(options)), max(options))


def save_app_preferences(form) -> None:
    save_app_preferences_to_db(_db(), form)
    clear_preference_caches()


def has_settings_password() -> bool:
    return has_settings_password_in_db(_db())


def set_settings_password(password: str) -> bool:
    if not set_settings_password_in_db(_db(), password):
        return False
    stored_hash = get_app_setting_from_db(_db(), "settings_password_hash", "")
    ensure_primary_account(_account_database(), stored_hash or None)
    session.setdefault("account_id", 1)
    session["settings_unlocked"] = True
    return True


def verify_settings_password(password: str) -> bool:
    return verify_settings_password_in_db(_db(), password)


def settings_unlocked() -> bool:
    if session.get("account_id") and session.get("settings_unlocked"):
        return True
    return has_settings_password() and bool(session.get("settings_unlocked"))


def reset_settings_password() -> None:
    reset_settings_password_in_db(_db())
    session.pop("settings_unlocked", None)
