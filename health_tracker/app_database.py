from __future__ import annotations

import secrets
import sqlite3
from pathlib import Path
from typing import Callable

from flask import g, has_request_context, session

from health_tracker.config import BASE_DIR, DATABASE
from health_tracker.constants import SQLITE_BUSY_TIMEOUT_MS
from health_tracker.database.schema import init_database
from health_tracker.services.accounts import account_db_path
from health_tracker.utils import parse_int

_initialized_workout_databases: set[Path] = set()
_initializing_workout_databases: set[Path] = set()
_recalculate_missing_exercise_calories: Callable[[], None] | None = None
_bootstrap_locations: Callable[[sqlite3.Connection], sqlite3.Row] | None = None
_delete_internal_test_data: Callable[[], int] | None = None
_get_database: Callable[[], Path] = lambda: DATABASE


def configure_database_helpers(
    *,
    get_database: Callable[[], Path],
    recalculate_missing_exercise_calories: Callable[[], None],
    bootstrap_locations: Callable[[sqlite3.Connection], sqlite3.Row],
    delete_internal_test_data: Callable[[], int],
) -> None:
    global _get_database, _recalculate_missing_exercise_calories, _bootstrap_locations, _delete_internal_test_data
    _get_database = get_database
    _recalculate_missing_exercise_calories = recalculate_missing_exercise_calories
    _bootstrap_locations = bootstrap_locations
    _delete_internal_test_data = delete_internal_test_data


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        account_id = parse_int(str(session.get("account_id") or "")) if has_request_context() else None
        database_path = account_db_path(_get_database(), account_id or 1)
        database_path.parent.mkdir(exist_ok=True)
        g.db = sqlite3.connect(database_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
        g.db.execute("PRAGMA journal_mode = WAL")
        g.db.execute("PRAGMA synchronous = NORMAL")
        g.db.set_trace_callback(lambda _sql: setattr(g, "db_query_count", int(getattr(g, "db_query_count", 0)) + 1))
        ensure_workout_database_initialized(database_path)
    return g.db


def init_db() -> None:
    account_id = parse_int(str(session.get("account_id") or "")) if has_request_context() else None
    database_path = account_db_path(_get_database(), account_id or 1)
    database_path.parent.mkdir(exist_ok=True)
    ensure_workout_database_initialized(database_path, force=True)


def ensure_workout_database_initialized(database_path: Path, force: bool = False) -> None:
    if not force and database_path in _initialized_workout_databases and database_path.exists():
        return
    if database_path in _initializing_workout_databases:
        return
    if not _recalculate_missing_exercise_calories or not _bootstrap_locations or not _delete_internal_test_data:
        raise RuntimeError("Database helpers are not configured.")
    _initializing_workout_databases.add(database_path)
    try:
        db = get_db()
        init_database(
            db,
            _recalculate_missing_exercise_calories,
            _bootstrap_locations,
            _delete_internal_test_data,
        )
        db.commit()
        _initialized_workout_databases.add(database_path)
    finally:
        _initializing_workout_databases.discard(database_path)


def get_or_create_secret_key() -> str:
    secret_path = BASE_DIR / "instance" / "secret_key.txt"
    secret_path.parent.mkdir(exist_ok=True)
    if secret_path.exists():
        secret = secret_path.read_text(encoding="utf-8").strip()
        if secret:
            return secret
    secret = secrets.token_urlsafe(32)
    secret_path.write_text(secret, encoding="utf-8")
    return secret
