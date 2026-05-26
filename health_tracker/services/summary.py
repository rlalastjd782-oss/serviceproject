from __future__ import annotations

import sqlite3

from health_tracker.date_utils import current_local_date, normalize_month, shift_date, shift_month


def get_day_summary_from_db(db: sqlite3.Connection, day: str) -> dict[str, float]:
    workout = db.execute(
        """
        SELECT
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            COALESCE(MAX(s.duration_seconds), 0) AS duration_seconds
        FROM workout_sessions s
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date = ?
        """,
        (day,),
    ).fetchone()
    meal = db.execute(
        """
        SELECT
            COUNT(id) AS meal_count,
            COALESCE(SUM(quantity), 0) AS amount,
            COALESCE(SUM(grams), 0) AS grams,
            COALESCE(SUM(calories), 0) AS calories
        FROM meal_entries
        WHERE meal_date = ?
        """,
        (day,),
    ).fetchone()
    return {
        "set_count": workout["set_count"],
        "rep_count": workout["rep_count"],
        "volume": workout["volume"],
        "cardio_minutes": workout["cardio_minutes"],
        "exercise_calories": workout["exercise_calories"],
        "duration_seconds": workout["duration_seconds"],
        "meal_count": meal["meal_count"],
        "amount": meal["amount"],
        "grams": meal["grams"],
        "calories": meal["calories"],
    }


def list_daily_summary_from_db(
    db: sqlite3.Connection,
    limit: int | None = None,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[sqlite3.Row]:
    where_clause = ""
    limit_clause = ""
    params: list[object] = []
    if start_date and end_date:
        where_clause = "WHERE p.period BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    elif days is not None:
        start_date = shift_date(current_local_date(), -(max(1, days) - 1))
        where_clause = "WHERE p.period >= ?"
        params.append(start_date)
    elif limit is not None:
        limit_clause = "LIMIT ?"
        params.append(limit)
    return db.execute(
        f"""
        WITH workout AS (
            SELECT
                s.workout_date AS period,
                COUNT(ws.id) AS set_count,
                COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
                COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
                COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
                COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
                COALESCE(MAX(s.duration_seconds), 0) AS duration_seconds
            FROM workout_sessions s
            LEFT JOIN workout_sets ws ON ws.session_id = s.id
            GROUP BY s.workout_date
            HAVING COUNT(ws.id) > 0 OR COALESCE(MAX(s.completed), 0) = 1
        ),
        meal AS (
            SELECT
                meal_date AS period,
                COUNT(id) AS meal_count,
                COALESCE(SUM(quantity), 0) AS amount,
                COALESCE(SUM(grams), 0) AS grams,
                COALESCE(SUM(calories), 0) AS calories
            FROM meal_entries
            GROUP BY meal_date
        ),
        periods AS (
            SELECT period FROM workout
            UNION
            SELECT period FROM meal
        )
        SELECT
            p.period,
            COALESCE(w.set_count, 0) AS set_count,
            COALESCE(w.rep_count, 0) AS rep_count,
            COALESCE(w.volume, 0) AS volume,
            COALESCE(w.cardio_minutes, 0) AS cardio_minutes,
            COALESCE(w.exercise_calories, 0) AS exercise_calories,
            COALESCE(w.duration_seconds, 0) AS duration_seconds,
            COALESCE(m.meal_count, 0) AS meal_count,
            COALESCE(m.amount, 0) AS amount,
            COALESCE(m.grams, 0) AS grams,
            COALESCE(m.calories, 0) AS calories
        FROM periods p
        LEFT JOIN workout w ON w.period = p.period
        LEFT JOIN meal m ON m.period = p.period
        {where_clause}
        ORDER BY p.period DESC
        {limit_clause}
        """,
        params,
    ).fetchall()


def list_weekly_summary_from_db(
    db: sqlite3.Connection,
    limit: int = 12,
    month_start: str | None = None,
) -> list[sqlite3.Row]:
    workout_where = ""
    meal_where = ""
    params: list[object] = []
    if month_start:
        normalized_month = normalize_month(month_start)
        next_month = shift_month(normalized_month, 1)
        workout_where = "WHERE s.workout_date >= ? AND s.workout_date < ?"
        meal_where = "WHERE meal_date >= ? AND meal_date < ?"
        params.extend([normalized_month, next_month, normalized_month, next_month, normalized_month, next_month])
    params.append(limit)
    return db.execute(
        f"""
        WITH workout AS (
            SELECT
                strftime('%Y-%m', s.workout_date) AS month_key,
                CAST(strftime('%m', s.workout_date) AS INTEGER) AS month_number,
                ((CAST(strftime('%d', s.workout_date) AS INTEGER) - 1) / 7) + 1 AS week_of_month,
                COUNT(DISTINCT CASE WHEN ws.id IS NOT NULL THEN s.workout_date END) AS workout_days,
                COUNT(ws.id) AS set_count,
                COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
                COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
                COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
                COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories
            FROM workout_sessions s
            LEFT JOIN workout_sets ws ON ws.session_id = s.id
            {workout_where}
            GROUP BY month_key, week_of_month
            HAVING COUNT(ws.id) > 0
        ),
        workout_time AS (
            SELECT
                strftime('%Y-%m', workout_date) AS month_key,
                CAST(strftime('%m', workout_date) AS INTEGER) AS month_number,
                ((CAST(strftime('%d', workout_date) AS INTEGER) - 1) / 7) + 1 AS week_of_month,
                COALESCE(SUM(duration_seconds), 0) AS duration_seconds
            FROM workout_sessions s
            {workout_where.replace("s.workout_date", "workout_date")}
              {"AND" if workout_where else "WHERE"} EXISTS (SELECT 1 FROM workout_sets ws WHERE ws.session_id = s.id)
            GROUP BY month_key, week_of_month
        ),
        meal AS (
            SELECT
                strftime('%Y-%m', meal_date) AS month_key,
                CAST(strftime('%m', meal_date) AS INTEGER) AS month_number,
                ((CAST(strftime('%d', meal_date) AS INTEGER) - 1) / 7) + 1 AS week_of_month,
                COUNT(DISTINCT meal_date) AS meal_days,
                COUNT(id) AS meal_count,
                COALESCE(SUM(quantity), 0) AS amount,
                COALESCE(SUM(grams), 0) AS grams,
                COALESCE(SUM(calories), 0) AS calories
            FROM meal_entries
            {meal_where}
            GROUP BY month_key, week_of_month
        ),
        periods AS (
            SELECT month_key, month_number, week_of_month FROM workout
            UNION
            SELECT month_key, month_number, week_of_month FROM meal
        )
        SELECT
            p.month_key || '-' || p.week_of_month AS period_key,
            p.month_number || '월 ' || p.week_of_month || '주차' AS period,
            COALESCE(w.workout_days, 0) AS workout_days,
            COALESCE(w.set_count, 0) AS set_count,
            COALESCE(w.rep_count, 0) AS rep_count,
            COALESCE(w.volume, 0) AS volume,
            COALESCE(w.cardio_minutes, 0) AS cardio_minutes,
            COALESCE(w.exercise_calories, 0) AS exercise_calories,
            COALESCE(wt.duration_seconds, 0) AS duration_seconds,
            COALESCE(m.meal_days, 0) AS meal_days,
            COALESCE(m.meal_count, 0) AS meal_count,
            COALESCE(m.amount, 0) AS amount,
            COALESCE(m.grams, 0) AS grams,
            COALESCE(m.calories, 0) AS calories
        FROM periods p
        LEFT JOIN workout w
            ON w.month_key = p.month_key AND w.week_of_month = p.week_of_month
        LEFT JOIN workout_time wt
            ON wt.month_key = p.month_key AND wt.week_of_month = p.week_of_month
        LEFT JOIN meal m
            ON m.month_key = p.month_key AND m.week_of_month = p.week_of_month
        ORDER BY p.month_key DESC, p.week_of_month DESC
        LIMIT ?
        """,
        params,
    ).fetchall()


def build_period_chart_from_rows(rows: list[sqlite3.Row]) -> list[dict[str, float | int | str]]:
    ordered_rows = list(reversed(rows))
    max_volume = max([float(row["volume"]) for row in ordered_rows] + [1.0])
    max_grams = max([float(row["grams"]) for row in ordered_rows] + [1.0])
    max_exercise_calories = max([float(row["exercise_calories"]) for row in ordered_rows] + [1.0])
    max_sets = max([int(row["set_count"]) for row in ordered_rows] + [1])
    max_duration = max([int(row["duration_seconds"]) for row in ordered_rows] + [1])
    return [
        {
            "period": row["period"],
            "volume": float(row["volume"]),
            "grams": float(row["grams"]),
            "exercise_calories": float(row["exercise_calories"]),
            "duration_seconds": int(row["duration_seconds"]),
            "set_count": int(row["set_count"]),
            "workout_days": int(row["workout_days"]) if "workout_days" in row.keys() else (1 if int(row["set_count"]) > 0 else 0),
            "meal_count": int(row["meal_count"]),
            "volume_height": max(3, round(float(row["volume"]) / max_volume * 100)),
            "volume_width": round(float(row["volume"]) / max_volume * 100),
            "grams_height": max(3, round(float(row["grams"]) / max_grams * 100)),
            "grams_width": round(float(row["grams"]) / max_grams * 100),
            "exercise_calorie_height": max(3, round(float(row["exercise_calories"]) / max_exercise_calories * 100)),
            "exercise_calorie_width": round(float(row["exercise_calories"]) / max_exercise_calories * 100),
            "set_height": max(3, round(int(row["set_count"]) / max_sets * 100)),
            "set_width": round(int(row["set_count"]) / max_sets * 100),
            "duration_width": round(int(row["duration_seconds"]) / max_duration * 100),
        }
        for row in ordered_rows
    ]


def build_daily_chart_from_rows(rows: list[sqlite3.Row]) -> list[dict[str, float | int | str]]:
    chart = build_period_chart_from_rows(rows)
    for item in chart:
        item["workout_days"] = 1 if int(item["set_count"]) > 0 else 0
    return chart
