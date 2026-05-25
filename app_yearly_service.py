from __future__ import annotations

import sqlite3


def normalize_year(value: str | None, fallback: str) -> str:
    text = (value or fallback).strip()
    if len(text) >= 4 and text[:4].isdigit():
        return text[:4]
    return fallback[:4]


def year_bounds(year: str) -> tuple[str, str]:
    start = f"{year}-01-01"
    end = f"{int(year) + 1}-01-01"
    return start, end


def build_yearly_report(db: sqlite3.Connection, year: str) -> dict[str, object]:
    start, end = year_bounds(year)
    workout = db.execute(
        """
        SELECT
            COUNT(DISTINCT CASE WHEN ws.id IS NOT NULL THEN s.workout_date END) AS workout_days,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            COALESCE(SUM(CASE WHEN EXISTS (
                SELECT 1 FROM workout_sets ws2 WHERE ws2.session_id = s.id
            ) THEN s.duration_seconds ELSE 0 END), 0) AS duration_seconds
        FROM workout_sessions s
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        """,
        (start, end),
    ).fetchone()
    meal = db.execute(
        """
        SELECT
            COUNT(DISTINCT meal_date) AS meal_days,
            COUNT(id) AS meal_count,
            COALESCE(SUM(calories), 0) AS calories
        FROM meal_entries
        WHERE meal_date >= ? AND meal_date < ?
        """,
        (start, end),
    ).fetchone()
    pr = db.execute(
        """
        SELECT COUNT(id) AS pr_count
        FROM pr_events
        WHERE workout_date >= ? AND workout_date < ?
        """,
        (start, end),
    ).fetchone()
    return {
        "year": year,
        "period": f"{year}-01-01 ~ {year}-12-31",
        "workout_days": int(workout["workout_days"] or 0),
        "set_count": int(workout["set_count"] or 0),
        "rep_count": int(workout["rep_count"] or 0),
        "volume": float(workout["volume"] or 0),
        "cardio_minutes": float(workout["cardio_minutes"] or 0),
        "exercise_calories": float(workout["exercise_calories"] or 0),
        "duration_seconds": int(workout["duration_seconds"] or 0),
        "meal_days": int(meal["meal_days"] or 0),
        "meal_count": int(meal["meal_count"] or 0),
        "calories": float(meal["calories"] or 0),
        "pr_count": int(pr["pr_count"] or 0),
    }


def list_yearly_month_rows(db: sqlite3.Connection, year: str) -> list[sqlite3.Row]:
    start, end = year_bounds(year)
    return db.execute(
        """
        WITH months(month_key) AS (
            VALUES
              (? || '-01'), (? || '-02'), (? || '-03'), (? || '-04'),
              (? || '-05'), (? || '-06'), (? || '-07'), (? || '-08'),
              (? || '-09'), (? || '-10'), (? || '-11'), (? || '-12')
        ),
        workout AS (
            SELECT
                substr(s.workout_date, 1, 7) AS month_key,
                COUNT(DISTINCT CASE WHEN ws.id IS NOT NULL THEN s.workout_date END) AS workout_days,
                COUNT(ws.id) AS set_count,
                COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
                COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
                COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
                COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
                COALESCE(MAX(s.duration_seconds), 0) AS duration_seconds
            FROM workout_sessions s
            LEFT JOIN workout_sets ws ON ws.session_id = s.id
            WHERE s.workout_date >= ? AND s.workout_date < ?
            GROUP BY substr(s.workout_date, 1, 7)
        ),
        meal AS (
            SELECT
                substr(meal_date, 1, 7) AS month_key,
                COUNT(DISTINCT meal_date) AS meal_days,
                COUNT(id) AS meal_count,
                COALESCE(SUM(calories), 0) AS calories
            FROM meal_entries
            WHERE meal_date >= ? AND meal_date < ?
            GROUP BY substr(meal_date, 1, 7)
        ),
        pr AS (
            SELECT substr(workout_date, 1, 7) AS month_key, COUNT(id) AS pr_count
            FROM pr_events
            WHERE workout_date >= ? AND workout_date < ?
            GROUP BY substr(workout_date, 1, 7)
        )
        SELECT
            m.month_key AS period,
            COALESCE(w.workout_days, 0) AS workout_days,
            COALESCE(w.set_count, 0) AS set_count,
            COALESCE(w.rep_count, 0) AS rep_count,
            COALESCE(w.volume, 0) AS volume,
            COALESCE(w.cardio_minutes, 0) AS cardio_minutes,
            COALESCE(w.exercise_calories, 0) AS exercise_calories,
            COALESCE(w.duration_seconds, 0) AS duration_seconds,
            COALESCE(meal.meal_days, 0) AS meal_days,
            COALESCE(meal.meal_count, 0) AS meal_count,
            COALESCE(meal.calories, 0) AS calories,
            COALESCE(pr.pr_count, 0) AS pr_count
        FROM months m
        LEFT JOIN workout w ON w.month_key = m.month_key
        LEFT JOIN meal ON meal.month_key = m.month_key
        LEFT JOIN pr ON pr.month_key = m.month_key
        ORDER BY m.month_key ASC
        """,
        (year, year, year, year, year, year, year, year, year, year, year, year, start, end, start, end, start, end),
    ).fetchall()


def list_yearly_body_part_summary(db: sqlite3.Connection, year: str) -> list[sqlite3.Row]:
    start, end = year_bounds(year)
    return db.execute(
        """
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        GROUP BY body_part
        ORDER BY set_count DESC, volume DESC, body_part
        """,
        (start, end),
    ).fetchall()


def list_yearly_top_exercises(db: sqlite3.Connection, year: str, limit: int = 10) -> list[sqlite3.Row]:
    start, end = year_bounds(year)
    return db.execute(
        """
        SELECT
            e.name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        GROUP BY e.id, e.name, body_part
        ORDER BY set_count DESC, volume DESC, last_date DESC
        LIMIT ?
        """,
        (start, end, limit),
    ).fetchall()


def compare_yearly_reports(base: dict[str, object], compare: dict[str, object]) -> list[dict[str, object]]:
    items = [
        ("운동일", "workout_days", "일"),
        ("세트", "set_count", "세트"),
        ("볼륨", "volume", "kg"),
        ("운동 시간", "duration_seconds", "초"),
        ("유산소", "cardio_minutes", "분"),
        ("식단일", "meal_days", "일"),
        ("식단 kcal", "calories", "kcal"),
        ("PR", "pr_count", "개"),
    ]
    rows = []
    for label, key, unit in items:
        base_value = float(base.get(key) or 0)
        compare_value = float(compare.get(key) or 0)
        diff = compare_value - base_value
        percent = round(diff / base_value * 100, 1) if base_value else None
        rows.append(
            {
                "label": label,
                "key": key,
                "unit": unit,
                "base": base_value,
                "compare": compare_value,
                "diff": diff,
                "percent": percent,
            }
        )
    return rows


def export_yearly_workout_rows(db: sqlite3.Connection, year: str) -> list[sqlite3.Row]:
    start, end = year_bounds(year)
    return db.execute(
        """
        SELECT
            s.workout_date,
            e.name AS exercise_name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COALESCE(NULLIF(ws.equipment, ''), '미지정') AS equipment,
            ws.set_type,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.estimated_calories,
            ws.rpe,
            ws.memo
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        ORDER BY s.workout_date, ws.sort_order, ws.id
        """,
        (start, end),
    ).fetchall()


def export_yearly_meal_rows(db: sqlite3.Connection, year: str) -> list[sqlite3.Row]:
    start, end = year_bounds(year)
    return db.execute(
        """
        SELECT meal_date, meal_type, food_name, quantity, grams, calories, memo
        FROM meal_entries
        WHERE meal_date >= ? AND meal_date < ?
        ORDER BY meal_date, id
        """,
        (start, end),
    ).fetchall()
