from __future__ import annotations

import sqlite3

from health_tracker.app_activity_facade import recalculate_exercise_calories_for_date
from health_tracker.app_database import get_db
from health_tracker.config import PHOTO_DIR
from health_tracker.date_utils import shift_month
from health_tracker.services.body import (
    build_body_monthly_report_from_rows,
    get_body_metric_from_db,
    list_body_metric_trend_from_rows,
    list_all_body_photos_from_db,
    list_body_metrics_from_db,
    list_body_photos_from_db,
    save_body_metric_to_db,
    save_body_photo_to_db,
)
from health_tracker.services.meal import (
    apply_meal_template_to_db,
    copy_meal_type_from_day_in_db,
    copy_meals_from_day_in_db,
    create_meal_template_from_day_in_db,
    delete_meal_template_from_db,
    list_frequent_meal_combos_from_db,
    list_meal_templates_from_db,
    list_recent_meal_days_from_db,
)


def get_body_metric(metric_date: str) -> sqlite3.Row | None:
    return get_body_metric_from_db(get_db(), metric_date)


def save_body_metric(
    metric_date: str,
    body_weight: float | None,
    muscle_mass: float | None,
    body_fat: float | None,
    waist: float | None,
) -> None:
    save_body_metric_to_db(
        get_db(),
        metric_date,
        body_weight,
        muscle_mass,
        body_fat,
        waist,
        recalculate_exercise_calories_for_date,
    )


def list_body_metrics(month_start: str) -> list[sqlite3.Row]:
    return list_body_metrics_from_db(get_db(), month_start, shift_month)


def build_body_monthly_report(month_start: str) -> dict[str, object]:
    return build_body_monthly_report_from_rows(list_body_metrics(month_start))


def list_body_metric_trend(month_start: str) -> list[dict[str, object]]:
    return list_body_metric_trend_from_rows(list_body_metrics(month_start))


def save_body_photo(photo_date: str, file) -> None:
    save_body_photo_to_db(get_db(), PHOTO_DIR, photo_date, file)


def list_body_photos(photo_date: str, limit: int = 3) -> list[sqlite3.Row]:
    return list_body_photos_from_db(get_db(), photo_date, limit)


def list_all_body_photos(limit: int = 200) -> list[sqlite3.Row]:
    return list_all_body_photos_from_db(get_db(), limit)


def list_meal_templates() -> list[dict[str, object]]:
    return list_meal_templates_from_db(get_db())


def create_meal_template_from_day(name: str, meal_date: str) -> None:
    create_meal_template_from_day_in_db(get_db(), name, meal_date)


def apply_meal_template(template_id: int, meal_date: str) -> None:
    apply_meal_template_to_db(get_db(), template_id, meal_date)


def delete_meal_template(template_id: int) -> None:
    delete_meal_template_from_db(get_db(), template_id)


def list_recent_meal_days(target_date: str, limit: int = 3) -> list[sqlite3.Row]:
    return list_recent_meal_days_from_db(get_db(), target_date, limit)


def copy_meals_from_day(source_date: str, meal_date: str) -> None:
    copy_meals_from_day_in_db(get_db(), source_date, meal_date)


def copy_meal_type_from_day(source_date: str, meal_date: str, meal_type: str) -> None:
    copy_meal_type_from_day_in_db(get_db(), source_date, meal_date, meal_type)


def list_frequent_meal_combos(limit: int = 6) -> list[dict[str, object]]:
    return list_frequent_meal_combos_from_db(get_db(), limit)

