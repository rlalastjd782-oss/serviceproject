from __future__ import annotations

import sqlite3

from health_tracker.constants import MEAL_TYPE_CLASSES


def list_foods_by_meal_type_from_db(db: sqlite3.Connection, limit: int = 6) -> dict[str, list[dict[str, float | str | None]]]:
    rows = db.execute(
        """
        SELECT
            COALESCE(NULLIF(meal_type, ''), '기타') AS meal_type,
            food_name,
            quantity,
            grams,
            calories,
            COUNT(id) AS use_count,
            MAX(meal_date) AS last_date
        FROM meal_entries
        GROUP BY meal_type, food_name
        ORDER BY meal_type, last_date DESC, use_count DESC, food_name
        """
    ).fetchall()
    grouped: dict[str, list[dict[str, float | str | None]]] = {meal_type: [] for meal_type in MEAL_TYPE_CLASSES}
    for row in rows:
        meal_type = row["meal_type"] or "기타"
        if len(grouped.setdefault(meal_type, [])) >= limit:
            continue
        grouped[meal_type].append(
            {
                "food_name": row["food_name"],
                "quantity": row["quantity"],
                "grams": row["grams"],
                "calories": row["calories"],
            }
        )
    return grouped


def list_favorite_foods_from_db(db: sqlite3.Connection, limit: int = 6) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT food_name, quantity, grams, calories
        FROM food_favorites
        WHERE is_favorite = 1
        ORDER BY updated_at DESC, food_name
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def list_frequent_foods_from_db(db: sqlite3.Connection, limit: int = 6) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT
            food_name,
            quantity,
            grams,
            calories,
            COUNT(id) AS use_count,
            MAX(meal_date) AS last_date
        FROM meal_entries
        WHERE meal_date >= date('now', 'localtime', '-30 day')
        GROUP BY food_name
        HAVING COUNT(id) >= 3
        ORDER BY use_count DESC, last_date DESC, food_name
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def save_food_favorite_to_db(
    db: sqlite3.Connection,
    food_name: str,
    quantity: float | None,
    grams: float | None,
    calories: float | None,
) -> None:
    db.execute(
        """
        INSERT INTO food_favorites (food_name, quantity, grams, calories, is_favorite, updated_at)
        VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(food_name) DO UPDATE SET
            quantity = excluded.quantity,
            grams = excluded.grams,
            calories = excluded.calories,
            is_favorite = 1,
            updated_at = CURRENT_TIMESTAMP
        """,
        (food_name, quantity, grams, calories),
    )
    db.commit()


def delete_food_favorite_from_db(db: sqlite3.Connection, food_name: str) -> None:
    db.execute("DELETE FROM food_favorites WHERE food_name = ?", (food_name,))
    db.commit()
