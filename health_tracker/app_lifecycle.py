from __future__ import annotations

from pathlib import Path
from time import perf_counter, time
from typing import Callable

from flask import Flask, Response, abort, g, redirect, request, session, url_for

from health_tracker.constants import (
    ACCOUNT_SEEN_TOUCH_INTERVAL_SECONDS,
    BODY_PART_CLASSES,
    MEAL_TYPE_CLASSES,
)
from health_tracker.meta import get_app_updated_at, get_app_version
from health_tracker.security import (
    ADMIN_GET_ENDPOINTS,
    ADMIN_ONLY_ENDPOINTS,
    AUTHENTICATED_SHARED_ENDPOINTS,
    PUBLIC_GET_ENDPOINTS,
    PUBLIC_POST_ENDPOINTS,
    ensure_csrf_token,
    validate_csrf_token,
)
from health_tracker.services.accounts import touch_account_seen
from health_tracker.services.pagination import query_url
from health_tracker.utils import parse_int


def configure_lifecycle_hooks(
    app: Flask,
    *,
    database: Path,
    current_account: Callable[[], object],
    get_app_preferences: Callable[[], dict[str, object]],
    is_admin_account: Callable[[], bool],
    settings_unlocked: Callable[[], bool],
) -> None:
    @app.before_request
    def before_request() -> None:
        g.request_started_at = perf_counter()
        g.db_query_count = 0
        endpoint = request.endpoint or ""
        if request.method == "GET" and endpoint in {"static", "root_favicon", "root_service_worker"}:
            return None
        if request.endpoint != "static":
            account_id = parse_int(str(session.get("account_id") or ""))
            last_seen_touch = parse_int(str(session.get("last_seen_touch_at") or "")) or 0
            now_seconds = int(time())
            if account_id and now_seconds - last_seen_touch >= ACCOUNT_SEEN_TOUCH_INTERVAL_SECONDS:
                touch_account_seen(database, account_id)
                session["last_seen_touch_at"] = now_seconds
        ensure_csrf_token()
        if request.method == "POST":
            json_payload = request.get_json(silent=True) if request.is_json else None
            json_token = json_payload.get("csrf_token") if isinstance(json_payload, dict) else None
            if not validate_csrf_token(request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or json_token):
                abort(400)
        account = current_account()
        if session.get("account_id") and not account:
            session.pop("account_id", None)
            session.pop("settings_unlocked", None)
        logged_in = bool(account and session.get("settings_unlocked"))
        if not logged_in:
            if request.method == "GET" and endpoint not in PUBLIC_GET_ENDPOINTS:
                next_url = request.full_path.rstrip("?")
                return redirect(url_for("login_page", mode="user", next=next_url))
            if request.method == "POST" and endpoint not in PUBLIC_POST_ENDPOINTS:
                abort(403)
            return None
        if request.method == "GET" and endpoint in {"login_page", "legacy_login_page"}:
            return redirect(url_for("admin_dashboard_page" if account["role"] == "admin" else "index"))
        admin_endpoint = endpoint.startswith("admin_") or endpoint in ADMIN_ONLY_ENDPOINTS
        if account["role"] == "admin":
            if endpoint not in AUTHENTICATED_SHARED_ENDPOINTS and not admin_endpoint:
                if request.method == "GET":
                    return redirect(url_for("admin_dashboard_page"))
                abort(403)
        elif admin_endpoint:
            if request.method == "GET":
                return redirect(url_for("login_page", mode="admin", error="admin_required"))
            abort(403)
        if request.method == "GET" and request.endpoint in ADMIN_GET_ENDPOINTS and not settings_unlocked():
            return redirect(url_for("settings_page"))

    @app.after_request
    def add_diagnostics_headers(response: Response) -> Response:
        elapsed_ms = (perf_counter() - float(getattr(g, "request_started_at", perf_counter()))) * 1000
        response.headers["X-Request-Duration-ms"] = f"{elapsed_ms:.1f}"
        response.headers["X-DB-Query-Count"] = str(int(getattr(g, "db_query_count", 0)))
        response.headers["Server-Timing"] = f"app;dur={elapsed_ms:.1f}"
        return response

    @app.teardown_appcontext
    def close_db(error: Exception | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.context_processor
    def inject_app_meta() -> dict[str, object]:
        preferences = get_app_preferences()
        account = current_account()
        return {
            "app_version": get_app_version(),
            "app_updated_at": get_app_updated_at(),
            "is_admin": is_admin_account(),
            "can_write": settings_unlocked(),
            "current_account": account,
            "csrf_token": ensure_csrf_token,
            "per_page_options": preferences["per_page_options"],
            "app_preferences": preferences,
            "body_part_class_map": BODY_PART_CLASSES,
            "meal_type_class_map": MEAL_TYPE_CLASSES,
            "query_url": lambda **updates: query_url(request.path, request.args, **updates),
        }
