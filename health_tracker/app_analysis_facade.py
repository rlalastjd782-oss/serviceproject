from __future__ import annotations

import sqlite3

from flask import url_for

from health_tracker.app_body_meal_facade import build_body_monthly_report
from health_tracker.app_coaching_reports_facade import build_weekly_report, list_balance_warnings, list_volume_warnings
from health_tracker.app_database import get_db
from health_tracker.app_settings import get_app_preferences
from health_tracker.app_summary_facade import paged_rows
from health_tracker.app_workout_facade import (
    build_adaptive_training_recommendations,
    build_data_quality_profile,
    get_goal_value,
    list_record_gaps,
)
from health_tracker.app_data import get_backup_status, get_data_counts
from health_tracker.date_utils import current_local_date, normalize_date, normalize_month, shift_date, shift_month, week_start_for_date
from health_tracker.services.location_insights import (
    list_location_quick_exercises_from_db,
    list_location_training_insights_from_db,
)
from health_tracker.services.personalization import build_next_workout_plan_from_db
from health_tracker.services.records import allowed_sort


def build_nutrition_training_link(scope: str = "weekly", date_text: str | None = None) -> dict[str, object]:
    base_date = date_text or current_local_date()
    if scope == "monthly":
        start = normalize_month(base_date[:7])
        end = shift_date(shift_month(start, 1), -1)
    else:
        start = week_start_for_date(base_date)
        end = shift_date(start, 6)
    rows = get_db().execute(
        """
        SELECT d.day,
               COALESCE(w.set_count, 0) AS set_count,
               COALESCE(w.volume, 0) AS volume,
               COALESCE(w.duration_seconds, 0) AS duration_seconds,
               COALESCE(m.calories, 0) AS calories,
               COALESCE(m.meal_count, 0) AS meal_count
        FROM (
            SELECT workout_date AS day FROM workout_sessions WHERE workout_date BETWEEN ? AND ?
            UNION
            SELECT meal_date AS day FROM meal_entries WHERE meal_date BETWEEN ? AND ?
        ) d
        LEFT JOIN (
            SELECT s.workout_date AS day,
                   COUNT(ws.id) AS set_count,
                   COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
                   MAX(COALESCE(s.duration_seconds, 0)) AS duration_seconds
            FROM workout_sessions s
            JOIN workout_sets ws ON ws.session_id = s.id
            WHERE s.workout_date BETWEEN ? AND ?
            GROUP BY s.workout_date
        ) w ON w.day = d.day
        LEFT JOIN (
            SELECT meal_date AS day,
                   COUNT(id) AS meal_count,
                   COALESCE(SUM(COALESCE(calories, 0)), 0) AS calories
            FROM meal_entries
            WHERE meal_date BETWEEN ? AND ?
            GROUP BY meal_date
        ) m ON m.day = d.day
        ORDER BY d.day
        """,
        (start, end, start, end, start, end, start, end),
    ).fetchall()
    workout_days = [row for row in rows if int(row["set_count"] or 0) > 0]
    rest_days = [row for row in rows if int(row["set_count"] or 0) == 0 and float(row["calories"] or 0) > 0]
    workout_avg = sum(float(row["calories"] or 0) for row in workout_days) / len(workout_days) if workout_days else 0
    rest_avg = sum(float(row["calories"] or 0) for row in rest_days) / len(rest_days) if rest_days else 0
    low_fuel_days = [
        row["day"]
        for row in workout_days
        if float(row["calories"] or 0) < float(get_goal_value("daily_calories", int(get_app_preferences()["default_daily_calories"]))) * 0.75
    ]
    message = "운동일 식단 데이터가 쌓이면 섭취량과 퍼포먼스 관계를 보여줍니다."
    if workout_days:
        if low_fuel_days:
            message = f"운동일 중 {len(low_fuel_days)}일은 칼로리 기록이 목표보다 낮습니다."
        elif workout_avg >= rest_avg and rest_avg > 0:
            message = "운동일 섭취 기록이 휴식일보다 높아 훈련 연료 흐름이 안정적입니다."
        else:
            message = "운동일 섭취량이 휴식일과 비슷하거나 낮습니다."
    return {
        "period": f"{start} ~ {end}",
        "workout_days": len(workout_days),
        "meal_days": sum(1 for row in rows if int(row["meal_count"] or 0) > 0),
        "workout_calorie_avg": round(workout_avg),
        "rest_calorie_avg": round(rest_avg),
        "low_fuel_days": low_fuel_days[:5],
        "message": message,
    }


def build_body_progress_insights(date_text: str) -> list[str]:
    month_start = normalize_month(date_text[:7])
    report = build_body_monthly_report(month_start)
    photos = get_db().execute(
        "SELECT COUNT(id) AS count FROM body_photos WHERE photo_date >= ? AND photo_date < ?",
        (month_start, shift_month(month_start, 1)),
    ).fetchone()["count"]
    messages = []
    if report.get("has_data"):
        messages.append(f"이번 달 체중 변화 {float(report['weight_delta'] or 0):+.1f}kg")
        messages.append(f"골격근 변화 {float(report['muscle_delta'] or 0):+.1f}kg")
        messages.append(f"체지방 변화 {float(report['fat_delta'] or 0):+.1f}%")
    else:
        messages.append("이번 달 체성분 기록이 아직 없습니다.")
    messages.append(f"이번 달 진행 사진 {int(photos or 0)}장")
    return messages[:4]


def list_exercise_library(
    body_part: str = "",
    query: str = "",
    favorite_only: bool = False,
    limit: int = 120,
) -> list[sqlite3.Row]:
    default_rest_seconds = int(get_app_preferences()["default_rest_seconds"])
    filters = ["1 = 1"]
    params: list[object] = []
    if body_part:
        filters.append("COALESCE(NULLIF(last_sets.body_part, ''), '기타') = ?")
        params.append(body_part)
    if query:
        filters.append("e.name LIKE ?")
        params.append(f"%{query}%")
    if favorite_only:
        filters.append("COALESCE(es.is_favorite, 0) = 1")
    params.append(limit)
    return get_db().execute(
        f"""
        SELECT
            e.id,
            e.name,
            COALESCE(NULLIF(last_sets.body_part, ''), '기타') AS body_part,
            COALESCE(es.is_favorite, 0) AS is_favorite,
            COALESCE(es.rest_seconds, {default_rest_seconds}) AS rest_seconds,
            COALESCE(es.equipment, last_sets.equipment, '') AS equipment,
            es.target_weight,
            es.target_reps,
            es.target_sets,
            en.note,
            COALESCE(last_sets.set_count, 0) AS set_count,
            last_sets.last_date,
            last_sets.best_weight,
            last_sets.best_volume
        FROM exercises e
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        LEFT JOIN exercise_notes en ON en.exercise_name = e.name
        LEFT JOIN (
            SELECT
                ws.exercise_id,
                COALESCE(NULLIF(MAX(ws.body_part), ''), '기타') AS body_part,
                COALESCE(NULLIF(MAX(ws.equipment), ''), '') AS equipment,
                COUNT(ws.id) AS set_count,
                MAX(s.workout_date) AS last_date,
                MAX(ws.weight) AS best_weight,
                MAX(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)) AS best_volume
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            GROUP BY ws.exercise_id
        ) last_sets ON last_sets.exercise_id = e.id
        WHERE {" AND ".join(filters)}
        ORDER BY COALESCE(es.is_favorite, 0) DESC, last_sets.last_date DESC, set_count DESC, e.name
        LIMIT ?
        """,
        params,
    ).fetchall()


def paged_exercise_library(
    body_part: str = "",
    query: str = "",
    favorite_only: bool = False,
    sort: str = "favorite",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object, str]:
    default_rest_seconds = int(get_app_preferences()["default_rest_seconds"])
    sort_options = {
        "favorite": "COALESCE(es.is_favorite, 0) DESC, last_sets.last_date DESC, set_count DESC, e.name",
        "recent": "last_sets.last_date DESC, set_count DESC, e.name",
        "name": "e.name ASC",
        "sets": "set_count DESC, last_sets.last_date DESC, e.name",
    }
    selected_sort = allowed_sort(sort, sort_options, "favorite")
    filters = ["1 = 1"]
    params: list[object] = []
    if body_part:
        filters.append("COALESCE(NULLIF(last_sets.body_part, ''), '기타') = ?")
        params.append(body_part)
    if query:
        filters.append("e.name LIKE ?")
        params.append(f"%{query}%")
    if favorite_only:
        filters.append("COALESCE(es.is_favorite, 0) = 1")
    from_sql = f"""
        FROM exercises e
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        LEFT JOIN exercise_notes en ON en.exercise_name = e.name
        LEFT JOIN (
            SELECT
                ws.exercise_id,
                COALESCE(NULLIF(MAX(ws.body_part), ''), '기타') AS body_part,
                COALESCE(NULLIF(MAX(ws.equipment), ''), '') AS equipment,
                COUNT(ws.id) AS set_count,
                MAX(s.workout_date) AS last_date,
                MAX(ws.weight) AS best_weight,
                MAX(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)) AS best_volume
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            GROUP BY ws.exercise_id
        ) last_sets ON last_sets.exercise_id = e.id
        WHERE {" AND ".join(filters)}
    """
    rows, pagination = paged_rows(
        f"""
        SELECT
            e.id,
            e.name,
            COALESCE(NULLIF(last_sets.body_part, ''), '기타') AS body_part,
            COALESCE(es.is_favorite, 0) AS is_favorite,
            COALESCE(es.rest_seconds, {default_rest_seconds}) AS rest_seconds,
            COALESCE(es.equipment, last_sets.equipment, '') AS equipment,
            es.target_weight,
            es.target_reps,
            es.target_sets,
            en.note,
            COALESCE(last_sets.set_count, 0) AS set_count,
            last_sets.last_date,
            last_sets.best_weight,
            last_sets.best_volume
        {from_sql}
        ORDER BY {sort_options[selected_sort]}
        """,
        f"SELECT COUNT(*) {from_sql}",
        params,
        page,
        per_page,
    )
    return rows, pagination, selected_sort





def build_data_center_status(date_text: str | None = None) -> dict[str, object]:
    date_value = normalize_date(date_text)
    counts = get_data_counts()
    backup_status = get_backup_status()
    quality = build_data_quality_profile(date_value, 30)
    gaps = list_record_gaps(date_value, 30)
    exports = [
        {"label": "전체 JSON", "href": url_for("export_json"), "note": "복원 가능한 전체 백업"},
        {"label": "운동 CSV", "href": url_for("export_csv"), "note": "운동 기록 표"},
        {"label": "식단 CSV", "href": url_for("export_meal_csv_route"), "note": "식단 기록 표"},
        {
            "label": f"{date_value[:4]} 운동 CSV",
            "href": url_for("export_yearly_workouts_csv_route", year=date_value[:4]),
            "note": "연간 운동 기록",
        },
        {
            "label": f"{date_value[:4]} 식단 CSV",
            "href": url_for("export_yearly_meals_csv_route", year=date_value[:4]),
            "note": "연간 식단 기록",
        },
    ]
    warnings = []
    if gaps:
        warnings.append(f"최근 30일 중 {len(gaps)}일은 운동/식단/휴식 기록이 없습니다.")
    if counts["empty_workouts"]:
        warnings.append(f"비어 있는 운동 세션 {counts['empty_workouts']}개를 정리할 수 있습니다.")
    if quality["score"] < 70:
        warnings.append("분석 신뢰도가 낮아 추천과 추세 해석이 제한될 수 있습니다.")
    if not warnings:
        warnings.append("백업과 기록 상태가 안정적입니다.")
    return {
        "date": date_value,
        "counts": counts,
        "backup_status": backup_status,
        "quality": quality,
        "gaps": gaps[:8],
        "exports": exports,
        "warnings": warnings,
    }


def list_location_training_insights(limit: int = 20) -> list[dict[str, object]]:
    return list_location_training_insights_from_db(get_db(), limit)


def list_location_quick_exercises(location_id: int | None, limit: int = 6) -> list[sqlite3.Row]:
    return list_location_quick_exercises_from_db(get_db(), location_id, limit)


def build_action_insights(date_text: str | None = None) -> dict[str, object]:
    date_value = normalize_date(date_text)
    weekly_report = build_weekly_report(date_value)
    quality = build_data_quality_profile(date_value, 30)
    recommendations = build_adaptive_training_recommendations(date_value, limit=8)
    balance_warnings = list_balance_warnings("weekly", date_value)
    volume_warnings = list_volume_warnings(date_value)
    nutrition_link = build_nutrition_training_link("weekly", date_value)
    alerts = [*balance_warnings[:3], *volume_warnings[:3]]
    if quality["score"] < 70:
        alerts.append("기록 점검에서 누락일을 먼저 채우면 분석 신뢰도가 올라갑니다.")
    if not alerts:
        alerts.append("이번 주 기록 흐름은 안정적입니다. PR 후보 운동을 중심으로 진행하면 됩니다.")
    return {
        "date": date_value,
        "weekly_report": weekly_report,
        "quality": quality,
        "recommendations": recommendations,
        "alerts": alerts[:6],
        "nutrition_link": nutrition_link,
        "location_insights": list_location_training_insights(limit=4),
        "next_workout_plan": build_next_workout_plan_from_db(get_db(), date_value),
    }

