from __future__ import annotations

import sqlite3

from health_tracker.app_database import get_db
from health_tracker.constants import BODY_PART_CLASSES, BODY_PARTS, MEAL_TYPE_CLASSES
from health_tracker.date_utils import current_local_date, meal_day_label, normalize_month, shift_date, shift_month, week_start_for_date
from health_tracker.services.meal import (
    build_monthly_meal_summary_from_db,
    build_weekly_meal_summary_from_db,
    grouped_meals_for_date_from_db,
    list_meals_for_date_from_db,
    list_monthly_meal_weeks_from_db,
    list_weekly_meal_days_from_db,
)
from health_tracker.services.records import (
    allowed_sort,
    list_exercise_summary_by_body_part_from_db,
    paged_equipment_daily_from_db,
    paged_equipment_detail_from_db,
    paged_equipment_summary_from_db,
    paged_exercise_summary_from_db,
    paged_rows_from_db,
    paged_search_workout_records_filtered_from_db,
)
from health_tracker.services.summary import (
    build_daily_chart_from_rows,
    build_period_chart_from_rows,
    get_day_summary_from_db,
    list_daily_summary_from_db,
    list_weekly_summary_from_db,
)
from health_tracker.services.workout import list_recent_sessions_from_db
from health_tracker.services.yearly import (
    build_yearly_export_payload,
    build_yearly_report as build_yearly_report_from_db,
    export_yearly_meal_csv as export_yearly_meal_csv_from_db,
    export_yearly_workout_csv as export_yearly_workout_csv_from_db,
    list_yearly_body_part_summary as list_yearly_body_part_summary_from_db,
    list_yearly_month_rows as list_yearly_month_rows_from_db,
    list_yearly_top_exercises as list_yearly_top_exercises_from_db,
)


def body_part_options() -> list[str]:
    return BODY_PARTS


def body_part_class(body_part: str | None) -> str:
    return BODY_PART_CLASSES.get((body_part or "기타").strip(), "body-part-other")


def meal_type_class(meal_type: str | None) -> str:
    return MEAL_TYPE_CLASSES.get((meal_type or "기타").strip(), "meal-type-other")


def list_recent_sessions(limit: int = 10) -> list[sqlite3.Row]:
    return list_recent_sessions_from_db(get_db(), limit)


def list_meals_for_date(meal_date: str) -> list[sqlite3.Row]:
    return list_meals_for_date_from_db(get_db(), meal_date)


def grouped_meals_for_date(meal_date: str) -> list[dict[str, object]]:
    return grouped_meals_for_date_from_db(get_db(), meal_date)


def list_weekly_meal_days(week_start: str) -> list[dict[str, object]]:
    return list_weekly_meal_days_from_db(get_db(), week_start, shift_date, meal_day_label)


def build_weekly_meal_summary(week_start: str) -> dict[str, object]:
    return build_weekly_meal_summary_from_db(get_db(), week_start, shift_date)


def build_monthly_meal_summary(month_start: str) -> dict[str, object]:
    return build_monthly_meal_summary_from_db(get_db(), month_start, normalize_month, shift_month)


def list_monthly_meal_weeks(month_start: str) -> list[dict[str, object]]:
    return list_monthly_meal_weeks_from_db(get_db(), month_start, normalize_month, shift_month)


def get_day_summary(day: str) -> dict[str, float]:
    return get_day_summary_from_db(get_db(), day)


def list_daily_summary(
    limit: int | None = None,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[sqlite3.Row]:
    return list_daily_summary_from_db(get_db(), limit, days, start_date, end_date)


def list_weekly_summary(limit: int = 12, month_start: str | None = None) -> list[sqlite3.Row]:
    return list_weekly_summary_from_db(get_db(), limit, month_start)


def build_period_chart(rows: list[sqlite3.Row]) -> list[dict[str, float | int | str]]:
    return build_period_chart_from_rows(rows)


def build_daily_chart(rows: list[sqlite3.Row]) -> list[dict[str, float | int | str]]:
    return build_daily_chart_from_rows(rows)


def build_yearly_report(year: str) -> dict[str, object]:
    return build_yearly_report_from_db(get_db(), year)


def list_yearly_month_rows(year: str) -> list[sqlite3.Row]:
    return list_yearly_month_rows_from_db(get_db(), year)


def list_yearly_body_part_summary(year: str) -> list[sqlite3.Row]:
    return list_yearly_body_part_summary_from_db(get_db(), year)


def list_yearly_top_exercises(year: str, limit: int = 10) -> list[sqlite3.Row]:
    return list_yearly_top_exercises_from_db(get_db(), year, limit)


def export_yearly_payload(year: str) -> dict[str, object]:
    return build_yearly_export_payload(get_db(), year)


def export_yearly_workout_csv(year: str) -> str:
    return export_yearly_workout_csv_from_db(get_db(), year)


def export_yearly_meal_csv(year: str) -> str:
    return export_yearly_meal_csv_from_db(get_db(), year)


def paged_rows(select_sql: str, count_sql: str, params: list[object], page: int, per_page: int) -> tuple[list[sqlite3.Row], object]:
    return paged_rows_from_db(get_db(), select_sql, count_sql, params, page, per_page)


def paged_search_workout_records_filtered(
    query: str = "",
    body_part: str = "",
    equipment: str = "",
    location_id: int | None = None,
    start_date: str = "",
    end_date: str = "",
    sort: str = "newest",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object, str]:
    return paged_search_workout_records_filtered_from_db(
        get_db(),
        query,
        body_part,
        equipment,
        location_id,
        start_date,
        end_date,
        sort,
        page,
        per_page,
    )


def paged_search_workout_records(
    query: str,
    sort: str = "newest",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object, str]:
    return paged_search_workout_records_filtered(
        query=query,
        sort=sort,
        page=page,
        per_page=per_page,
    )


def paged_exercise_summary(sort: str = "sets", page: int = 1, per_page: int = 20) -> tuple[list[sqlite3.Row], object, str]:
    return paged_exercise_summary_from_db(get_db(), sort, page, per_page)


def paged_exercise_pr_summary(
    body_part: str = "",
    query: str = "",
    sort: str = "weight",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object, str]:
    sort_options = {
        "1rm": "estimated_1rm DESC, best_weight DESC, last_date DESC, e.name",
        "weight": "best_weight DESC, best_volume DESC, last_date DESC, e.name",
        "volume": "best_volume DESC, best_weight DESC, last_date DESC, e.name",
        "recent": "last_date DESC, best_weight DESC, e.name",
    }
    selected_sort = allowed_sort(sort, sort_options, "weight")
    filters = ["ws.weight IS NOT NULL", "ws.reps IS NOT NULL", "COALESCE(NULLIF(ws.body_part, ''), '기타') != '유산소'"]
    params: list[object] = []
    if body_part:
        filters.append("COALESCE(NULLIF(ws.body_part, ''), '기타') = ?")
        params.append(body_part)
    if query:
        filters.append("e.name LIKE ?")
        params.append(f"%{query}%")
    where_clause = " AND ".join(filters)
    from_sql = f"""
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE {where_clause}
        GROUP BY e.id, e.name
    """
    rows, pagination = paged_rows(
        f"""
        SELECT
            e.id,
            e.name,
            COALESCE(NULLIF(MAX(ws.body_part), ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COUNT(DISTINCT s.workout_date) AS workout_days,
            MAX(s.workout_date) AS last_date,
            COALESCE(MAX(ws.weight), 0) AS best_weight,
            COALESCE(MAX(ws.reps), 0) AS best_reps,
            COALESCE(MAX(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS best_volume,
            COALESCE(MAX(ws.weight * (1 + ws.reps / 30.0)), 0) AS estimated_1rm
        {from_sql}
        ORDER BY {sort_options[selected_sort]}
        """,
        f"SELECT COUNT(*) FROM (SELECT e.id {from_sql})",
        params,
        page,
        per_page,
    )
    return rows, pagination, selected_sort


def list_exercise_summary_by_body_part() -> dict[str, list[sqlite3.Row]]:
    return list_exercise_summary_by_body_part_from_db(get_db(), body_part_options)


def equipment_scope_clause(scope: str) -> tuple[str, tuple[str, ...]]:
    from health_tracker.services.records import equipment_scope_clause as build_equipment_scope_clause

    return build_equipment_scope_clause(scope, current_local_date(), week_start_for_date, shift_month)


def paged_equipment_summary(
    scope: str = "month",
    sort: str = "sets",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object, str]:
    return paged_equipment_summary_from_db(
        get_db(),
        scope,
        sort,
        page,
        per_page,
        current_local_date(),
        week_start_for_date,
        shift_month,
    )


def paged_equipment_detail(
    equipment: str,
    scope: str = "month",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object]:
    return paged_equipment_detail_from_db(
        get_db(),
        equipment,
        scope,
        page,
        per_page,
        current_local_date(),
        week_start_for_date,
        shift_month,
    )


def paged_equipment_daily(
    equipment: str,
    scope: str = "month",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object]:
    return paged_equipment_daily_from_db(
        get_db(),
        equipment,
        scope,
        page,
        per_page,
        current_local_date(),
        week_start_for_date,
        shift_month,
    )

