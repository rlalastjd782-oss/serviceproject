from __future__ import annotations

import sqlite3

from health_tracker.app_database import get_db
from health_tracker.app_settings import get_app_preferences
from health_tracker.services.exercise_settings import (
    get_exercise_rest_seconds_from_db,
    list_exercise_goal_progress_from_db,
    list_exercise_notes_from_db,
    list_exercise_settings_from_db,
    list_favorite_exercises_from_db,
    save_exercise_equipment_to_db,
    save_exercise_note_to_db,
    save_exercise_settings_to_db,
)
from health_tracker.services.progressive_overload import list_overload_suggestions_from_db
from health_tracker.services.smart_workout import list_exercise_smart_defaults_from_db


def list_overload_suggestions() -> dict[str, str]:
    return list_overload_suggestions_from_db(get_db())


def list_exercise_notes() -> dict[str, str]:
    return list_exercise_notes_from_db(get_db())


def save_exercise_note(exercise_name: str, note: str) -> None:
    save_exercise_note_to_db(get_db(), exercise_name, note)


def list_exercise_settings() -> dict[str, dict[str, int | float | bool | str | None]]:
    return list_exercise_settings_from_db(get_db(), int(get_app_preferences()["default_rest_seconds"]))


def list_exercise_goal_progress() -> dict[str, dict[str, object]]:
    return list_exercise_goal_progress_from_db(get_db())


def list_exercise_smart_defaults(location_id: int | None = None) -> dict[str, dict[str, object]]:
    return list_exercise_smart_defaults_from_db(get_db(), location_id)


def save_exercise_settings(
    exercise_name: str,
    rest_seconds: int,
    is_favorite: bool,
    equipment: str = "",
    target_weight: float | None = None,
    target_reps: int | None = None,
    target_sets: int | None = None,
) -> None:
    save_exercise_settings_to_db(
        get_db(),
        exercise_name,
        rest_seconds,
        is_favorite,
        int(get_app_preferences()["default_rest_seconds"]),
        equipment,
        target_weight,
        target_reps,
        target_sets,
    )


def save_exercise_equipment(exercise_name: str, equipment: str) -> None:
    save_exercise_equipment_to_db(get_db(), exercise_name, equipment)


def get_exercise_rest_seconds(exercise_name: str) -> int:
    return get_exercise_rest_seconds_from_db(get_db(), exercise_name, int(get_app_preferences()["default_rest_seconds"]))


def list_favorite_exercises(location_id: int | None = None) -> list[sqlite3.Row]:
    return list_favorite_exercises_from_db(get_db(), location_id)

