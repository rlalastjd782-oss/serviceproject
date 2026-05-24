from __future__ import annotations

import sqlite3
from collections.abc import Callable


def list_meals_for_date_from_db(db: sqlite3.Connection, meal_date: str) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT *
        FROM meal_entries
        WHERE meal_date = ?
        ORDER BY created_at DESC, id DESC
        """,
        (meal_date,),
    ).fetchall()


def grouped_meals_for_date_from_db(db: sqlite3.Connection, meal_date: str) -> list[dict[str, object]]:
    rows = db.execute(
        """
        SELECT *
        FROM meal_entries
        WHERE meal_date = ?
        ORDER BY
            CASE meal_type
                WHEN '아침' THEN 1
                WHEN '점심' THEN 2
                WHEN '저녁' THEN 3
                WHEN '간식' THEN 4
                ELSE 5
            END,
            id
        """,
        (meal_date,),
    ).fetchall()
    groups: list[dict[str, object]] = []
    group_by_type: dict[str, dict[str, object]] = {}
    for item in rows:
        meal_type = item["meal_type"] or "식사"
        if meal_type not in group_by_type:
            group = {"meal_type": meal_type, "entries": []}
            group_by_type[meal_type] = group
            groups.append(group)
        group_by_type[meal_type]["entries"].append(item)
    return groups


def list_weekly_meal_days_from_db(
    db: sqlite3.Connection,
    week_start: str,
    shift_date: Callable[[str, int], str],
    meal_day_label: Callable[[str], str],
) -> list[dict[str, object]]:
    week_end = shift_date(week_start, 6)
    rows = db.execute(
        """
        SELECT *
        FROM meal_entries
        WHERE meal_date BETWEEN ? AND ?
        ORDER BY meal_date ASC,
            CASE meal_type
                WHEN '아침' THEN 1
                WHEN '점심' THEN 2
                WHEN '저녁' THEN 3
                WHEN '간식' THEN 4
                ELSE 5
            END,
            created_at ASC,
            id ASC
        """,
        (week_start, week_end),
    ).fetchall()
    rows_by_date: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        rows_by_date.setdefault(row["meal_date"], []).append(row)

    days = []
    for offset in range(7):
        date_value = shift_date(week_start, offset)
        entries = rows_by_date.get(date_value, [])
        days.append(
            {
                "date": date_value,
                "label": meal_day_label(date_value),
                "entry_rows": entries,
                "meal_count": len(entries),
                "calories": sum(float(entry["calories"] or 0) for entry in entries),
            }
        )
    return days


def build_weekly_meal_summary_from_db(db: sqlite3.Connection, week_start: str, shift_date: Callable[[str, int], str]) -> dict[str, object]:
    week_end = shift_date(week_start, 6)
    totals = db.execute(
        """
        SELECT
            COUNT(DISTINCT meal_date) AS meal_days,
            COUNT(id) AS meal_count,
            COALESCE(SUM(calories), 0) AS calories,
            COALESCE(SUM(grams), 0) AS grams
        FROM meal_entries
        WHERE meal_date BETWEEN ? AND ?
        """,
        (week_start, week_end),
    ).fetchone()
    top_food = db.execute(
        """
        SELECT food_name, COUNT(id) AS count
        FROM meal_entries
        WHERE meal_date BETWEEN ? AND ?
        GROUP BY food_name
        ORDER BY count DESC, food_name
        LIMIT 1
        """,
        (week_start, week_end),
    ).fetchone()
    meal_days = int(totals["meal_days"] or 0)
    calories = float(totals["calories"] or 0)
    return {
        "meal_days": meal_days,
        "meal_count": int(totals["meal_count"] or 0),
        "calories": calories,
        "grams": float(totals["grams"] or 0),
        "avg_calories": round(calories / meal_days) if meal_days else 0,
        "top_food": top_food["food_name"] if top_food else "-",
        "top_food_count": int(top_food["count"] or 0) if top_food else 0,
    }


def build_monthly_meal_summary_from_db(
    db: sqlite3.Connection,
    month_start: str,
    normalize_month: Callable[[str], str],
    shift_month: Callable[[str, int], str],
) -> dict[str, object]:
    normalized_month = normalize_month(month_start)
    next_month = shift_month(normalized_month, 1)
    totals = db.execute(
        """
        SELECT
            COUNT(DISTINCT meal_date) AS meal_days,
            COUNT(id) AS meal_count,
            COALESCE(SUM(calories), 0) AS calories,
            COALESCE(SUM(grams), 0) AS grams
        FROM meal_entries
        WHERE meal_date >= ? AND meal_date < ?
        """,
        (normalized_month, next_month),
    ).fetchone()
    top_food = db.execute(
        """
        SELECT food_name, COUNT(id) AS count
        FROM meal_entries
        WHERE meal_date >= ? AND meal_date < ?
        GROUP BY food_name
        ORDER BY count DESC, food_name
        LIMIT 1
        """,
        (normalized_month, next_month),
    ).fetchone()
    meal_days = int(totals["meal_days"] or 0)
    calories = float(totals["calories"] or 0)
    return {
        "meal_days": meal_days,
        "meal_count": int(totals["meal_count"] or 0),
        "calories": calories,
        "grams": float(totals["grams"] or 0),
        "avg_calories": round(calories / meal_days) if meal_days else 0,
        "top_food": top_food["food_name"] if top_food else "-",
        "top_food_count": int(top_food["count"] or 0) if top_food else 0,
    }


def list_monthly_meal_weeks_from_db(
    db: sqlite3.Connection,
    month_start: str,
    normalize_month: Callable[[str], str],
    shift_month: Callable[[str, int], str],
) -> list[dict[str, object]]:
    normalized_month = normalize_month(month_start)
    next_month = shift_month(normalized_month, 1)
    rows = db.execute(
        """
        SELECT
            ((CAST(strftime('%d', meal_date) AS INTEGER) - 1) / 7) + 1 AS week_of_month,
            MIN(meal_date) AS start_date,
            MAX(meal_date) AS end_date,
            COUNT(DISTINCT meal_date) AS meal_days,
            COUNT(id) AS meal_count,
            COALESCE(SUM(calories), 0) AS calories,
            COALESCE(SUM(grams), 0) AS grams
        FROM meal_entries
        WHERE meal_date >= ? AND meal_date < ?
        GROUP BY week_of_month
        ORDER BY week_of_month ASC
        """,
        (normalized_month, next_month),
    ).fetchall()
    max_calories = max([float(row["calories"] or 0) for row in rows] + [1.0])
    max_meals = max([int(row["meal_count"] or 0) for row in rows] + [1])
    result = []
    month_number = int(normalized_month[5:7])
    for row in rows:
        calories = float(row["calories"] or 0)
        meal_days = int(row["meal_days"] or 0)
        result.append(
            {
                "label": f"{month_number}월 {int(row['week_of_month'])}주차",
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "meal_days": meal_days,
                "meal_count": int(row["meal_count"] or 0),
                "calories": calories,
                "grams": float(row["grams"] or 0),
                "avg_calories": round(calories / meal_days) if meal_days else 0,
                "calorie_width": round(calories / max_calories * 100),
                "meal_width": round(int(row["meal_count"] or 0) / max_meals * 100),
            }
        )
    return result
