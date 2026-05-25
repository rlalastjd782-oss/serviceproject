from __future__ import annotations

import hmac
import secrets

from flask import session


PUBLIC_POST_ENDPOINTS = {"unlock_settings_route", "save_settings_password_route"}

ADMIN_GET_ENDPOINTS = {
    "export_json",
    "export_csv",
    "export_meal_csv_route",
    "export_yearly_json_route",
    "export_yearly_workouts_csv_route",
    "export_yearly_meals_csv_route",
    "qa_report_page",
    "api_sessions",
}


def ensure_csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return str(token)


def validate_csrf_token(token: object) -> bool:
    expected = session.get("csrf_token")
    return bool(expected and token and hmac.compare_digest(str(expected), str(token)))
