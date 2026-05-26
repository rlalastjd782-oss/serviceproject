from __future__ import annotations

import sqlite3
from collections.abc import Callable


def list_body_part_summary_from_db(
    db: sqlite3.Connection,
    scope: str,
    limit: int,
    date_text: str | None,
    week_start_for_date: Callable[[str], str],
    meal_week_label: Callable[[str], str],
    shift_date: Callable[[str, int], str],
    normalize_month: Callable[[str], str],
    shift_month: Callable[[str, int], str],
) -> list[sqlite3.Row]:
    where_clause = ""
    params: list[object] = []
    if scope == "daily":
        period_expr = "s.workout_date"
        order_clause = "MAX(s.workout_date) DESC, body_part"
    elif scope == "weekly":
        period_expr = (
            "CAST(strftime('%m', s.workout_date) AS INTEGER) || '월 ' || "
            "(((CAST(strftime('%d', s.workout_date) AS INTEGER) - 1) / 7) + 1) || '주차'"
        )
        order_clause = "body_part, MAX(s.workout_date) DESC"
        if date_text:
            week_start = week_start_for_date(date_text)
            period_expr = f"'{meal_week_label(week_start)}'"
            where_clause = "WHERE s.workout_date BETWEEN ? AND ?"
            params.extend([week_start, shift_date(week_start, 6)])
    else:
        period_expr = "strftime('%Y-%m', s.workout_date)"
        order_clause = "body_part, MAX(s.workout_date) DESC"
        if date_text:
            month_start = normalize_month(date_text)
            where_clause = "WHERE s.workout_date >= ? AND s.workout_date < ?"
            params.extend([month_start, shift_month(month_start, 1)])
    params.append(limit)

    return db.execute(
        f"""
        SELECT
            {period_expr} AS period,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            COUNT(DISTINCT pe.id) AS pr_count,
            MAX(CASE WHEN pe.record_type = '최고 중량' THEN pe.record_value END) AS best_pr_weight,
            MAX(CASE WHEN pe.record_type = '최고 반복' THEN pe.record_value END) AS best_pr_reps,
            MAX(CASE WHEN pe.record_type = '최고 볼륨' THEN pe.record_value END) AS best_pr_volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        LEFT JOIN pr_events pe ON pe.set_id = ws.id
        {where_clause}
        GROUP BY period, body_part
        ORDER BY {order_clause}
        LIMIT ?
        """,
        params,
    ).fetchall()


def list_weekly_body_part_details_from_db(
    db: sqlite3.Connection,
    date_text: str | None,
    week_start_for_date: Callable[[str], str],
    meal_week_label: Callable[[str], str],
    shift_date: Callable[[str, int], str],
) -> dict[str, list[sqlite3.Row]]:
    where_clause = ""
    params: list[object] = []
    if date_text:
        week_start = week_start_for_date(date_text)
        where_clause = "WHERE s.workout_date BETWEEN ? AND ?"
        params.extend([week_start, shift_date(week_start, 6)])
        period_expr = f"'{meal_week_label(week_start)}'"
    else:
        period_expr = (
            "CAST(strftime('%m', s.workout_date) AS INTEGER) || '월 ' || "
            "(((CAST(strftime('%d', s.workout_date) AS INTEGER) - 1) / 7) + 1) || '주차'"
        )
    rows = db.execute(
        f"""
        SELECT
            {period_expr} AS period,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.name AS exercise_name,
            MIN(ws.weight) AS min_weight,
            MAX(ws.weight) AS max_weight,
            AVG(ws.cardio_incline) AS avg_cardio_incline,
            AVG(ws.cardio_speed) AS avg_cardio_speed,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COUNT(DISTINCT pe.id) AS pr_count,
            MAX(CASE WHEN pe.record_type = '최고 중량' THEN pe.record_value END) AS best_pr_weight,
            MAX(CASE WHEN pe.record_type = '최고 반복' THEN pe.record_value END) AS best_pr_reps,
            MAX(CASE WHEN pe.record_type = '최고 볼륨' THEN pe.record_value END) AS best_pr_volume,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN pr_events pe ON pe.set_id = ws.id
        {where_clause}
        GROUP BY period, body_part, e.name
        ORDER BY MAX(s.workout_date) DESC, body_part, e.name
        """,
        params,
    ).fetchall()

    details: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        details.setdefault(f"{row['period']}::{row['body_part']}", []).append(row)
    return details
