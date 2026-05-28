from __future__ import annotations

import sqlite3
from collections.abc import Callable

from flask import g, has_request_context, session

from health_tracker.services.accounts import (
    create_account as create_account_in_auth_db,
    ensure_primary_account,
    get_account as get_account_from_auth_db,
    get_account_any_status,
    list_admin_audit_logs as list_admin_audit_logs_from_auth_db,
    list_accounts as list_accounts_from_auth_db,
    log_admin_action as log_admin_action_to_auth_db,
    reset_account_password,
    update_account_login,
    update_account_memo,
    update_account_status,
    verify_account as verify_account_from_auth_db,
)
from health_tracker.services.admin_dashboard import (
    account_usage_summary,
    build_admin_dashboard as build_admin_dashboard_from_accounts,
)
from health_tracker.services.settings import get_app_setting as get_app_setting_from_db
from health_tracker.utils import parse_int

_get_db: Callable[[], sqlite3.Connection] | None = None
_get_database: Callable[[], object] | None = None


def configure_account_helpers(get_db_func: Callable[[], sqlite3.Connection], get_database_func: Callable[[], object]) -> None:
    global _get_db, _get_database
    _get_db = get_db_func
    _get_database = get_database_func


def _db() -> sqlite3.Connection:
    if _get_db is None:
        raise RuntimeError("account helpers are not configured")
    return _get_db()


def _database():
    if _get_database is None:
        raise RuntimeError("account helpers are not configured")
    return _get_database()


def current_account() -> sqlite3.Row | None:
    if not has_request_context():
        return None
    if hasattr(g, "current_account_cache"):
        return g.current_account_cache
    account_id = parse_int(str(session.get("account_id") or ""))
    account = get_account_from_auth_db(_database(), account_id)
    g.current_account_cache = account
    return account


def account_options() -> list[sqlite3.Row]:
    ensure_default_account()
    return list_accounts_from_auth_db(_database())


def account_by_id(account_id: int) -> sqlite3.Row | None:
    ensure_default_account()
    return get_account_any_status(_database(), account_id)


def ensure_default_account() -> None:
    stored_hash = get_app_setting_from_db(_db(), "settings_password_hash", "")
    ensure_primary_account(_database(), stored_hash or None)


def create_account(username: str, password: str, display_name: str = "", role: str = "user") -> tuple[bool, str]:
    ensure_default_account()
    return create_account_in_auth_db(_database(), username, password, display_name, role)


def verify_account(username: str, password: str) -> sqlite3.Row | None:
    ensure_default_account()
    return verify_account_from_auth_db(_database(), username, password)


def mark_account_login(account_id: int) -> None:
    update_account_login(_database(), account_id)
    if has_request_context():
        g.pop("current_account_cache", None)


def is_admin_account() -> bool:
    account = current_account()
    return bool(account and account["role"] == "admin" and session.get("settings_unlocked"))


def build_admin_dashboard(
    accounts: list[sqlite3.Row],
    query: str = "",
    status: str = "all",
    sort_key: str = "id",
) -> dict[str, object]:
    return build_admin_dashboard_from_accounts(_database(), accounts, query, status, sort_key)


def build_account_usage(account: sqlite3.Row) -> dict[str, object]:
    return account_usage_summary(_database(), account)


def reset_user_password(account_id: int, password: str) -> bool:
    return reset_account_password(_database(), account_id, password)


def set_user_active(account_id: int, is_active: bool) -> None:
    update_account_status(_database(), account_id, is_active)


def save_user_admin_note(account_id: int, memo: str, display_name: str = "") -> None:
    update_account_memo(_database(), account_id, memo, display_name)


def log_admin_action(action: str, target_account_id: int | None = None, detail: str = "") -> None:
    account = current_account()
    if not account:
        return
    log_admin_action_to_auth_db(_database(), int(account["id"]), action, target_account_id, detail)


def admin_audit_logs(limit: int = 20) -> list[sqlite3.Row]:
    return list_admin_audit_logs_from_auth_db(_database(), limit)
