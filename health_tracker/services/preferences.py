from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping

from health_tracker.constants import (
    DEFAULT_BODY_WEIGHT_KG,
    DEFAULT_DAILY_CALORIES,
    DEFAULT_REPS_PLACEHOLDER,
    DEFAULT_REST_SECONDS,
    DEFAULT_SET_COUNT,
    DEFAULT_WEIGHT_PLACEHOLDER,
    REST_TIMER_PRESETS,
    SET_TYPE_OPTIONS,
    SUMMARY_DAY_OPTIONS,
)
from health_tracker.services.pagination import DEFAULT_PER_PAGE, PER_PAGE_OPTIONS


DEFAULT_APP_PREFERENCES = {
    "default_rest_seconds": DEFAULT_REST_SECONDS,
    "rest_timer_presets": REST_TIMER_PRESETS,
    "default_set_count": DEFAULT_SET_COUNT,
    "default_weight_placeholder": DEFAULT_WEIGHT_PLACEHOLDER,
    "default_reps_placeholder": DEFAULT_REPS_PLACEHOLDER,
    "default_daily_calories": DEFAULT_DAILY_CALORIES,
    "default_body_weight_kg": DEFAULT_BODY_WEIGHT_KG,
    "default_per_page": DEFAULT_PER_PAGE,
    "summary_day_options": SUMMARY_DAY_OPTIONS,
    "set_type_options": SET_TYPE_OPTIONS,
}


def _setting(db: sqlite3.Connection, key: str) -> str:
    row = db.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row and row["value"] is not None else ""


def _setting_from_values(values: Mapping[str, str], key: str) -> str:
    return str(values.get(key) or "")


def _save(db: sqlite3.Connection, key: str, value: object) -> None:
    stored = json.dumps(value, ensure_ascii=False) if isinstance(value, list) else str(value)
    db.execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """,
        (key, stored),
    )


def _int_setting(values: Mapping[str, str], key: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(_setting_from_values(values, key) or default)
    except ValueError:
        value = default
    return min(maximum, max(minimum, value))


def _float_setting(values: Mapping[str, str], key: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(_setting_from_values(values, key) or default)
    except ValueError:
        value = default
    return min(maximum, max(minimum, value))


def _int_list_setting(values: Mapping[str, str], key: str, default: list[int], minimum: int, maximum: int) -> list[int]:
    raw = _setting_from_values(values, key)
    values: list[int] = []
    if raw:
        try:
            source = json.loads(raw)
        except json.JSONDecodeError:
            source = raw.replace(",", " ").split()
        for item in source:
            try:
                parsed = int(str(item).strip())
            except ValueError:
                continue
            if minimum <= parsed <= maximum and parsed not in values:
                values.append(parsed)
    return values or list(default)


def _string_list_setting(values: Mapping[str, str], key: str, default: list[str], limit: int = 12) -> list[str]:
    raw = _setting_from_values(values, key)
    values: list[str] = []
    if raw:
        try:
            source = json.loads(raw)
        except json.JSONDecodeError:
            source = raw.splitlines()
        for item in source:
            value = str(item).strip()
            if value and value not in values:
                values.append(value[:20])
    return values[:limit] or list(default)


def app_preferences(db: sqlite3.Connection) -> dict[str, object]:
    keys = tuple(DEFAULT_APP_PREFERENCES)
    rows = db.execute(
        f"""
        SELECT key, value
        FROM app_settings
        WHERE key IN ({", ".join("?" for _ in keys)})
        """,
        keys,
    ).fetchall()
    values = {row["key"]: str(row["value"] or "") for row in rows}
    default_per_page = _int_setting(values, "default_per_page", DEFAULT_PER_PAGE, 1, 100)
    if default_per_page not in PER_PAGE_OPTIONS:
        default_per_page = DEFAULT_PER_PAGE
    return {
        "default_rest_seconds": _int_setting(values, "default_rest_seconds", DEFAULT_REST_SECONDS, 15, 600),
        "rest_timer_presets": _int_list_setting(values, "rest_timer_presets", REST_TIMER_PRESETS, 15, 600)[:6],
        "default_set_count": _int_setting(values, "default_set_count", DEFAULT_SET_COUNT, 1, 20),
        "default_weight_placeholder": _float_setting(
            values, "default_weight_placeholder", DEFAULT_WEIGHT_PLACEHOLDER, 0, 500
        ),
        "default_reps_placeholder": _int_setting(values, "default_reps_placeholder", DEFAULT_REPS_PLACEHOLDER, 0, 200),
        "default_daily_calories": _int_setting(values, "default_daily_calories", DEFAULT_DAILY_CALORIES, 0, 10000),
        "default_body_weight_kg": _float_setting(values, "default_body_weight_kg", DEFAULT_BODY_WEIGHT_KG, 20, 300),
        "default_per_page": default_per_page,
        "per_page_options": list(PER_PAGE_OPTIONS),
        "summary_day_options": _int_list_setting(values, "summary_day_options", SUMMARY_DAY_OPTIONS, 1, 365)[:8],
        "set_type_options": _string_list_setting(values, "set_type_options", SET_TYPE_OPTIONS),
    }


def save_app_preferences(db: sqlite3.Connection, form: Mapping[str, object]) -> None:
    current = app_preferences(db)
    int_keys = {
        "default_rest_seconds",
        "default_set_count",
        "default_reps_placeholder",
        "default_daily_calories",
        "default_per_page",
    }
    float_keys = {"default_weight_placeholder", "default_body_weight_kg"}
    list_keys = {"rest_timer_presets", "summary_day_options", "set_type_options"}
    for key in int_keys:
        if key in form:
            _save(db, key, form.get(key) or current[key])
    for key in float_keys:
        if key in form:
            _save(db, key, form.get(key) or current[key])
    for key in list_keys:
        if key in form:
            raw = str(form.get(key) or "").replace(",", "\n").splitlines()
            _save(db, key, [item.strip() for item in raw if item.strip()])
    db.commit()
