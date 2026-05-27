from __future__ import annotations

import hashlib
import hmac
import secrets

from flask import session


PUBLIC_GET_ENDPOINTS = {"root_route", "login_page", "signup_page", "preview_page", "legacy_login_page", "root_service_worker", "static"}

PUBLIC_POST_ENDPOINTS = {"login_route", "signup_route"}

AUTHENTICATED_SHARED_ENDPOINTS = {"logout_route", "root_service_worker", "static"}

ADMIN_ONLY_ENDPOINTS = {"create_account_route"}

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
