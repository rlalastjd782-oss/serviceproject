from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from health_tracker.services.admin import build_app_health_status
from health_tracker.services.data import (
    get_backup_status as build_backup_status,
    get_data_counts as build_data_counts,
    get_sample_data_counts as build_sample_data_counts,
)
from health_tracker.services.data_cleanup import (
    list_duplicate_exercise_candidates as list_duplicate_exercise_candidates_from_db,
    list_outlier_set_candidates as list_outlier_set_candidates_from_db,
)
from health_tracker.services.data_maintenance import (
    delete_all_data as delete_all_data_from_db,
    delete_empty_workout_sessions as delete_empty_workout_sessions_from_db,
    delete_internal_test_data as delete_internal_test_data_from_db,
)
from health_tracker.services.dummy_data import generate_year_qa_dummy_data as generate_year_qa_dummy_data_in_db
from health_tracker.services.dummy_data import get_qa_dummy_status as get_qa_dummy_status_from_db
from health_tracker.services.export import (
    export_all_data_from_db,
    export_meal_csv_from_db,
    export_workout_csv_from_db,
    import_all_data_to_db,
)
from health_tracker.services.personal_coach import build_data_safety_status
from health_tracker.services.release_readiness import build_v2_readiness_report
from health_tracker.services.sample_data import create_may_sample_data_in_db, delete_sample_data_from_db

_get_db: Callable[[], sqlite3.Connection] | None = None
_get_database: Callable[[], object] | None = None
_get_base_dir: Callable[[], Path] | None = None
_has_settings_password: Callable[[], bool] | None = None
_settings_unlocked: Callable[[], bool] | None = None
_get_or_create_session: Callable[..., sqlite3.Row] | None = None
_get_or_create_exercise: Callable[[str], int] | None = None
_save_exercise_equipment: Callable[[str, str], None] | None = None
_estimate_exercise_calories: Callable[..., float | None] | None = None


def configure_data_helpers(
    *,
    get_db_func: Callable[[], sqlite3.Connection],
    get_database_func: Callable[[], object],
    get_base_dir_func: Callable[[], Path],
    has_settings_password_func: Callable[[], bool],
    settings_unlocked_func: Callable[[], bool],
    get_or_create_session_func: Callable[..., sqlite3.Row],
    get_or_create_exercise_func: Callable[[str], int],
    save_exercise_equipment_func: Callable[[str, str], None],
    estimate_exercise_calories_func: Callable[..., float | None],
) -> None:
    global _get_db, _get_database, _get_base_dir, _has_settings_password, _settings_unlocked
    global _get_or_create_session, _get_or_create_exercise, _save_exercise_equipment, _estimate_exercise_calories
    _get_db = get_db_func
    _get_database = get_database_func
    _get_base_dir = get_base_dir_func
    _has_settings_password = has_settings_password_func
    _settings_unlocked = settings_unlocked_func
    _get_or_create_session = get_or_create_session_func
    _get_or_create_exercise = get_or_create_exercise_func
    _save_exercise_equipment = save_exercise_equipment_func
    _estimate_exercise_calories = estimate_exercise_calories_func


def _db() -> sqlite3.Connection:
    if _get_db is None:
        raise RuntimeError("data helpers are not configured")
    return _get_db()


def _database():
    if _get_database is None:
        raise RuntimeError("data helpers are not configured")
    return _get_database()


def _base_dir() -> Path:
    if _get_base_dir is None:
        raise RuntimeError("data helpers are not configured")
    return _get_base_dir()


def _required(name: str, value):
    if value is None:
        raise RuntimeError(f"data helper dependency is not configured: {name}")
    return value


def get_qa_dummy_status() -> dict[str, object]:
    return get_qa_dummy_status_from_db(_db())


def generate_year_qa_dummy_data() -> dict[str, object]:
    return generate_year_qa_dummy_data_in_db(_db())


def get_data_counts() -> dict[str, int]:
    return build_data_counts(_db())


def get_backup_status() -> dict[str, str]:
    return build_backup_status(_base_dir())


def get_data_safety_status() -> list[dict[str, str]]:
    return build_data_safety_status(
        get_backup_status(),
        _required("has_settings_password", _has_settings_password)(),
        _required("settings_unlocked", _settings_unlocked)(),
    )


def get_sample_data_counts() -> dict[str, int]:
    return build_sample_data_counts(_db())


def get_app_health_status() -> list[dict[str, str]]:
    return build_app_health_status(_database(), get_data_counts(), get_sample_data_counts(), get_backup_status())


def list_duplicate_exercise_candidates(limit: int = 10) -> list[dict[str, object]]:
    return list_duplicate_exercise_candidates_from_db(_db(), limit)


def list_outlier_set_candidates(limit: int = 10) -> list[dict[str, object]]:
    return list_outlier_set_candidates_from_db(_db(), limit)


def build_v2_readiness() -> dict[str, object]:
    return build_v2_readiness_report(
        get_data_counts(),
        get_qa_dummy_status(),
        get_backup_status(),
        _required("has_settings_password", _has_settings_password)(),
    )


def delete_sample_data() -> None:
    delete_sample_data_from_db(_db(), delete_empty_workout_sessions)


def create_may_sample_data() -> None:
    create_may_sample_data_in_db(
        _db(),
        delete_sample_data,
        _required("get_or_create_session", _get_or_create_session),
        _required("get_or_create_exercise", _get_or_create_exercise),
        _required("save_exercise_equipment", _save_exercise_equipment),
        _required("estimate_exercise_calories", _estimate_exercise_calories),
    )


def delete_empty_workout_sessions() -> None:
    delete_empty_workout_sessions_from_db(_db())


def delete_all_data() -> None:
    delete_all_data_from_db(_db(), _base_dir(), export_all_data)


def delete_internal_test_data() -> None:
    delete_internal_test_data_from_db(_db())


def export_all_data() -> dict[str, object]:
    return export_all_data_from_db(_db())


def export_workout_csv() -> str:
    return export_workout_csv_from_db(_db())


def export_meal_csv() -> str:
    return export_meal_csv_from_db(_db())


def import_all_data(payload: dict[str, object]) -> None:
    import_all_data_to_db(_db(), _base_dir(), payload)
