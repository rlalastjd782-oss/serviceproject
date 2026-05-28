from __future__ import annotations

import sqlite3
from collections.abc import Callable

MEAL_ENTRY_COLUMNS = "id, meal_date, meal_type, food_name, quantity, grams, calories, protein, carbs, fat, memo, created_at"
MEAL_TEMPLATE_ITEM_COLUMNS = "id, template_id, meal_type, food_name, quantity, grams, calories, sort_order"


def list_meals_for_date_from_db(db: sqlite3.Connection, meal_date: str) -> list[sqlite3.Row]:
    return db.execute(
        f"""
        SELECT {MEAL_ENTRY_COLUMNS}
        FROM meal_entries
        WHERE meal_date = ?
        ORDER BY created_at DESC, id DESC
        """,
        (meal_date,),
    ).fetchall()


def grouped_meals_for_date_from_db(db: sqlite3.Connection, meal_date: str) -> list[dict[str, object]]:
    rows = db.execute(
        f"""
        SELECT {MEAL_ENTRY_COLUMNS}
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
        f"""
        SELECT {MEAL_ENTRY_COLUMNS}
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


def list_meal_templates_from_db(db: sqlite3.Connection) -> list[dict[str, object]]:
    rows = db.execute(
        """
        SELECT mt.id, mt.name, COUNT(mti.id) AS item_count
        FROM meal_templates mt
        LEFT JOIN meal_template_items mti ON mti.template_id = mt.id
        GROUP BY mt.id
        ORDER BY mt.created_at DESC, mt.id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def create_meal_template_from_day_in_db(db: sqlite3.Connection, name: str, meal_date: str) -> None:
    rows = db.execute(
        f"""
        SELECT {MEAL_ENTRY_COLUMNS}
        FROM meal_entries
        WHERE meal_date = ?
        ORDER BY id
        """,
        (meal_date,),
    ).fetchall()
    if not rows:
        return
    cursor = db.execute("INSERT INTO meal_templates (name) VALUES (?)", (name,))
    template_id = int(cursor.lastrowid)
    for index, row in enumerate(rows, start=1):
        db.execute(
            """
            INSERT INTO meal_template_items
                (template_id, meal_type, food_name, quantity, grams, calories, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (template_id, row["meal_type"], row["food_name"], row["quantity"], row["grams"], row["calories"], index),
        )
    db.commit()


def apply_meal_template_to_db(db: sqlite3.Connection, template_id: int, meal_date: str) -> None:
    rows = db.execute(
        f"""
        SELECT {MEAL_TEMPLATE_ITEM_COLUMNS}
        FROM meal_template_items
        WHERE template_id = ?
        ORDER BY sort_order, id
        """,
        (template_id,),
    ).fetchall()
    for row in rows:
        db.execute(
            """
            INSERT INTO meal_entries (meal_date, meal_type, food_name, quantity, grams, calories)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (meal_date, row["meal_type"], row["food_name"], row["quantity"], row["grams"], row["calories"]),
        )
    db.commit()


def delete_meal_template_from_db(db: sqlite3.Connection, template_id: int) -> None:
    db.execute("DELETE FROM meal_template_items WHERE template_id = ?", (template_id,))
    db.execute("DELETE FROM meal_templates WHERE id = ?", (template_id,))
    db.commit()


def list_recent_meal_days_from_db(db: sqlite3.Connection, target_date: str, limit: int = 3) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT meal_date, COUNT(id) AS meal_count, COALESCE(SUM(calories), 0) AS calories
        FROM meal_entries
        WHERE meal_date < ?
        GROUP BY meal_date
        ORDER BY meal_date DESC
        LIMIT ?
        """,
        (target_date, limit),
    ).fetchall()


def copy_meals_from_day_in_db(db: sqlite3.Connection, source_date: str, meal_date: str) -> None:
    rows = db.execute(
        """
        SELECT meal_type, food_name, quantity, grams, calories, memo
        FROM meal_entries
        WHERE meal_date = ?
        ORDER BY id
        """,
        (source_date,),
    ).fetchall()
    for row in rows:
        db.execute(
            """
            INSERT INTO meal_entries (meal_date, meal_type, food_name, quantity, grams, calories, memo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (meal_date, row["meal_type"], row["food_name"], row["quantity"], row["grams"], row["calories"], row["memo"]),
        )
    db.commit()


def copy_meal_type_from_day_in_db(db: sqlite3.Connection, source_date: str, meal_date: str, meal_type: str) -> None:
    rows = db.execute(
        """
        SELECT meal_type, food_name, quantity, grams, calories, memo
        FROM meal_entries
        WHERE meal_date = ? AND meal_type = ?
        ORDER BY id
        """,
        (source_date, meal_type),
    ).fetchall()
    for row in rows:
        db.execute(
            """
            INSERT INTO meal_entries (meal_date, meal_type, food_name, quantity, grams, calories, memo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (meal_date, row["meal_type"], row["food_name"], row["quantity"], row["grams"], row["calories"], row["memo"]),
        )
    db.commit()


def list_frequent_meal_combos_from_db(db: sqlite3.Connection, limit: int = 6) -> list[dict[str, object]]:
    rows = db.execute(
        """
        SELECT
            meal_date,
            meal_type,
            COUNT(id) AS item_count,
            GROUP_CONCAT(food_name, ', ') AS foods,
            COALESCE(SUM(calories), 0) AS calories
        FROM meal_entries
        GROUP BY meal_date, meal_type
        HAVING COUNT(id) >= 2
        ORDER BY meal_date DESC, item_count DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]
