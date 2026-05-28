from __future__ import annotations

import hashlib
import hmac
import secrets

from flask import session


PUBLIC_GET_ENDPOINTS = {
    "root_route",
    "login_page",
    "signup_page",
    "preview_page",
    "legacy_login_page",
    "root_service_worker",
    "root_favicon",
    "static",
}

PUBLIC_POST_ENDPOINTS = {"login_route", "signup_route"}

AUTHENTICATED_SHARED_ENDPOINTS = {
    "export_csv",
    "export_json",
    "export_meal_csv_route",
    "logout_route",
    "qa_report_page",
    "root_favicon",
    "root_service_worker",
    "static",
}

ADMIN_ONLY_ENDPOINTS = {
    "cleanup_empty_data_route",
    "create_account_route",
    "create_may_sample_data_route",
    "delete_all_data_route",
    "delete_sample_data_route",
    "generate_year_qa_dummy_route",
    "import_json",
    "reset_settings_password_route",
    "save_app_preferences_route",
    "save_reminders_route",
}

ADMIN_GET_ENDPOINTS = {
    "export_json",
    "export_csv",
    "export_meal_csv_route",
    "export_yearly_json_route",
    "export_yearly_workouts_csv_route",
    "export_yearly_meals_csv_route",
    "qa_report_page",
    "api_sessions",
    "locations_page",
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


def make_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password_hash(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, digest_hex = stored_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 120_000)
    return hmac.compare_digest(digest.hex(), digest_hex)
