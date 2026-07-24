from __future__ import annotations

import sqlite3

from health_tracker.app_activity_facade import estimate_exercise_calories
from health_tracker.app_database import get_db
from health_tracker.app_exercise_settings_facade import get_exercise_rest_seconds
from health_tracker.app_settings import get_app_preferences
from health_tracker.app_summary_facade import body_part_class, body_part_options
from health_tracker.constants import DEFAULT_PROGRAMS
from health_tracker.date_utils import normalize_date, normalize_month, shift_date, shift_month, week_start_for_date
from health_tracker.services.coaching import (
    build_adaptive_training_recommendations_from_db,
    build_readiness_profile_from_db,
    list_recommended_sessions_from_db,
    list_workout_focus_recommendations_from_db,
)
from health_tracker.services.data_quality import build_data_quality_profile_from_db, list_record_gaps_from_db
from health_tracker.services.food_shortcuts import (
    delete_food_favorite_from_db,
    list_favorite_foods_from_db,
    list_foods_by_meal_type_from_db,
    list_frequent_foods_from_db,
    save_food_favorite_to_db,
)
from health_tracker.services.goals import (
    build_goal_progress_from_db,
    get_goal_value_from_db,
    goal_item as build_goal_item,
    save_goal_to_db,
)
from health_tracker.services.location import (
    get_location as get_location_from_db,
    get_recent_or_default_location as get_recent_or_default_location_from_db,
)
from health_tracker.services.muscle_balance import build_muscle_balance as build_muscle_balance_from_db
from health_tracker.services.progressive_overload import (
    build_next_set_suggestions as build_next_set_suggestions_from_db,
    list_progressive_overload_rows as list_progressive_overload_rows_from_db,
)
from health_tracker.services.reminders import list_reminder_settings_from_db, save_reminder_settings_to_db
from health_tracker.services.routine import (
    apply_routine_template_to_db,
    apply_session_template_to_db,
    create_routine_template_from_db,
    delete_routine_template_from_db,
    list_routines_from_db,
    rename_routine_template_in_db,
)
from health_tracker.services.workout import (
    get_or_create_exercise_in_db,
    get_or_create_session_from_db,
    get_session_by_date_from_db,
    get_session_by_id_from_db,
    get_session_or_placeholder_from_db,
    list_exercise_stats_by_name_from_db,
    list_exercises_by_body_part_from_db,
    list_exercises_from_db,
    list_recent_sets_by_exercise_from_db,
    mark_session_completed_in_db,
    reorder_set_within_exercise_in_db,
    update_session_duration_in_db,
)
from health_tracker.services.workout_plan import (
    apply_default_program_to_db,
    build_workout_completion_summary_from_db,
    build_workout_finish_review_from_db,
    build_workout_session_flow_from_db,
    create_workout_plan_item_in_db,
    delete_workout_plan_item_from_db,
    list_workout_plan_from_db,
)


def get_or_create_session(workout_date: str | None = None, location_id: int | None = None) -> sqlite3.Row:
    return get_or_create_session_from_db(
        get_db(),
        workout_date,
        location_id,
        normalize_date,
        get_location_from_db,
        get_recent_or_default_location_from_db,
        get_session_by_date,
    )


def get_session_or_placeholder(workout_date: str | None = None, location_id: int | None = None) -> dict[str, object]:
    return get_session_or_placeholder_from_db(
        get_db(),
        workout_date,
        location_id,
        normalize_date,
        get_location_from_db,
        get_recent_or_default_location_from_db,
    )


def get_session_by_date(workout_date: str) -> sqlite3.Row | None:
    return get_session_by_date_from_db(get_db(), workout_date)


def get_session_by_id(session_id: int) -> sqlite3.Row | None:
    return get_session_by_id_from_db(get_db(), session_id)


def mark_session_completed(session_id: int, completed: bool) -> None:
    mark_session_completed_in_db(get_db(), session_id, completed)


def update_session_duration(session_id: int, duration_seconds: int) -> None:
    update_session_duration_in_db(get_db(), session_id, duration_seconds)


def reorder_set_within_exercise(db: sqlite3.Connection, set_id: int, requested_set_number: int) -> None:
    reorder_set_within_exercise_in_db(db, set_id, requested_set_number)


def get_or_create_exercise(name: str) -> int:
    return get_or_create_exercise_in_db(get_db(), name)


def list_exercises(location_id: int | None = None) -> list[sqlite3.Row]:
    return list_exercises_from_db(get_db(), location_id)


def list_exercises_by_body_part(location_id: int | None = None) -> dict[str, list[str]]:
    return list_exercises_by_body_part_from_db(get_db(), body_part_options(), location_id)


def list_recent_sets_by_exercise(
    limit: int = 6,
    location_id: int | None = None,
) -> dict[str, list[dict[str, float | int | None]]]:
    return list_recent_sets_by_exercise_from_db(get_db(), limit, location_id)


def list_exercise_stats_by_name(location_id: int | None = None) -> dict[str, dict[str, object]]:
    return list_exercise_stats_by_name_from_db(get_db(), location_id)


def list_foods_by_meal_type(limit: int = 6) -> dict[str, list[dict[str, float | str | None]]]:
    return list_foods_by_meal_type_from_db(get_db(), limit)


def list_favorite_foods(limit: int = 6) -> list[sqlite3.Row]:
    return list_favorite_foods_from_db(get_db(), limit)


def list_frequent_foods(limit: int = 6) -> list[sqlite3.Row]:
    return list_frequent_foods_from_db(get_db(), limit)


def save_food_favorite(food_name: str, quantity: float | None, grams: float | None, calories: float | None) -> None:
    save_food_favorite_to_db(get_db(), food_name, quantity, grams, calories)


def delete_food_favorite(food_name: str) -> None:
    delete_food_favorite_from_db(get_db(), food_name)


def list_routines(location_id: int | None = None) -> list[dict[str, object]]:
    return list_routines_from_db(get_db(), location_id)


def rename_routine_template(routine_id: int, name: str) -> None:
    rename_routine_template_in_db(get_db(), routine_id, name)


def delete_routine_template(routine_id: int) -> None:
    delete_routine_template_from_db(get_db(), routine_id)


def create_routine_template(name: str, session_id: int) -> None:
    create_routine_template_from_db(get_db(), name, session_id)


def apply_routine_template(routine_id: int, workout_date: str) -> None:
    apply_routine_template_to_db(
        get_db(),
        routine_id,
        workout_date,
        get_or_create_session,
        get_or_create_exercise,
        estimate_exercise_calories,
    )


def apply_session_template(source_session_id: int, workout_date: str) -> None:
    apply_session_template_to_db(
        get_db(),
        source_session_id,
        workout_date,
        get_or_create_session,
        get_or_create_exercise,
        estimate_exercise_calories,
    )


def list_workout_plan(workout_date: str) -> list[sqlite3.Row]:
    return list_workout_plan_from_db(get_db(), workout_date)


def build_workout_completion_summary(workout_date: str) -> dict[str, object]:
    return build_workout_completion_summary_from_db(get_db(), workout_date, get_session_by_date)


def build_workout_finish_review(workout_date: str) -> dict[str, object]:
    return build_workout_finish_review_from_db(get_db(), workout_date, get_session_by_date)


def build_workout_session_flow(workout_date: str) -> dict[str, object]:
    return build_workout_session_flow_from_db(
        get_db(),
        workout_date,
        get_exercise_rest_seconds,
        int(get_app_preferences()["default_rest_seconds"]),
    )


def list_record_gaps(date_text: str, days: int = 7) -> list[dict[str, object]]:
    return list_record_gaps_from_db(get_db(), date_text, days)


def build_data_quality_profile(date_text: str, days: int = 14) -> dict[str, object]:
    return build_data_quality_profile_from_db(get_db(), normalize_date(date_text), days)


def create_workout_plan_item(workout_date: str, body_part: str, exercise_name: str, target_sets: int) -> None:
    create_workout_plan_item_in_db(get_db(), workout_date, body_part, exercise_name, target_sets)


def delete_workout_plan_item(item_id: int) -> None:
    delete_workout_plan_item_from_db(get_db(), item_id)


def apply_default_program(program_name: str, workout_date: str) -> None:
    apply_default_program_to_db(get_db(), DEFAULT_PROGRAMS.get(program_name), workout_date, get_or_create_session, get_or_create_exercise)


def list_recommended_sessions(workout_date: str, limit: int = 3) -> list[dict[str, object]]:
    return list_recommended_sessions_from_db(get_db(), workout_date, limit)


def list_workout_focus_recommendations(workout_date: str, limit: int = 5) -> list[dict[str, object]]:
    return list_workout_focus_recommendations_from_db(get_db(), workout_date, body_part_options, limit)


def build_adaptive_training_recommendations(workout_date: str, limit: int = 6) -> list[dict[str, object]]:
    return build_adaptive_training_recommendations_from_db(get_db(), workout_date, shift_date, limit)


def build_next_set_suggestions(exercise_names: list[str], workout_date: str, limit: int = 8) -> dict[str, dict[str, object]]:
    readiness = build_readiness_profile_from_db(get_db(), workout_date)
    return build_next_set_suggestions_from_db(get_db(), exercise_names, int(readiness["percent"] or 60), limit)


def list_progressive_overload_rows(limit: int = 30) -> list[dict[str, object]]:
    return list_progressive_overload_rows_from_db(get_db(), limit)


def build_muscle_balance(start_date: str, end_date: str) -> dict[str, object]:
    return build_muscle_balance_from_db(get_db(), start_date, end_date, body_part_class)


def generate_weekly_plan(week_start: str) -> int:
    created = 0
    for offset in range(7):
        workout_date = shift_date(week_start, offset)
        if list_workout_plan(workout_date):
            continue
        recommendations = build_adaptive_training_recommendations(workout_date, limit=3)
        if not recommendations:
            recommendations = list_workout_focus_recommendations(workout_date, limit=3)
        for item in recommendations[:3]:
            create_workout_plan_item(
                workout_date,
                str(item["body_part"]),
                str(item["exercise_name"]),
                int(item.get("target_sets") or 3),
            )
            created += 1
    return created


def list_reminder_settings() -> dict[str, dict[str, object]]:
    return list_reminder_settings_from_db(get_db())


def save_reminder_settings(key: str, enabled: bool, time_text: str, message: str) -> None:
    save_reminder_settings_to_db(get_db(), key, enabled, time_text, message)


def save_goal(key: str, value: int) -> None:
    save_goal_to_db(get_db(), key, value)


def get_goal_value(key: str, default: int) -> int:
    return get_goal_value_from_db(get_db(), key, default)


def get_goal_progress(date_text: str) -> dict[str, dict[str, int | float | str]]:
    return build_goal_progress_from_db(get_db(), date_text, week_start_for_date, shift_date, normalize_month, shift_month)


def goal_item(current: int | float, target: int, label: str) -> dict[str, int | float | str]:
    return build_goal_item(current, target, label)


def build_weekly_plan_board(week_start: str) -> list[dict[str, object]]:
    return [
        {
            "date": shift_date(week_start, offset),
            "plan_items": list_workout_plan(shift_date(week_start, offset)),
            "summary": build_workout_completion_summary(shift_date(week_start, offset)),
            "recommendations": build_adaptive_training_recommendations(shift_date(week_start, offset), limit=3),
        }
        for offset in range(7)
    ]


