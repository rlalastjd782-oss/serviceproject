from __future__ import annotations

import csv
import io
import sqlite3
from datetime import datetime


EXPORT_TABLES = [
    "exercises",
    "workout_sessions",
    "workout_sets",
    "meal_entries",
    "routine_templates",
    "routine_items",
    "meal_templates",
    "meal_template_items",
    "user_goals",
    "exercise_notes",
    "exercise_settings",
    "food_favorites",
    "workout_plan_items",
    "pr_events",
    "body_metrics",
    "body_photos",
    "recovery_checkins",
]


def export_all_data_from_db(db: sqlite3.Connection) -> dict[str, object]:
    return {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "tables": {table: [dict(row) for row in db.execute(f"SELECT * FROM {table}").fetchall()] for table in EXPORT_TABLES},
    }


def export_workout_csv_from_db(db: sqlite3.Connection) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "body_part", "exercise", "set_type", "weight", "reps", "incline", "speed", "minutes", "estimated_calories", "effort_score"])
    rows = db.execute(
        """
        SELECT
            s.workout_date,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.name AS exercise_name,
            ws.set_type,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.estimated_calories,
            ws.rpe
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        ORDER BY s.workout_date DESC, ws.sort_order ASC, ws.id ASC
        """
    ).fetchall()
    for row in rows:
        writer.writerow(
            [
                row["workout_date"],
                row["body_part"],
                row["exercise_name"],
                row["set_type"],
                row["weight"],
                row["reps"],
                row["cardio_incline"],
                row["cardio_speed"],
                row["cardio_minutes"],
                row["estimated_calories"],
                row["rpe"],
            ]
        )
    return "\ufeff" + output.getvalue()


def export_meal_csv_from_db(db: sqlite3.Connection) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "meal_type", "food", "quantity", "grams", "calories", "memo"])
    rows = db.execute(
        """
        SELECT meal_date, meal_type, food_name, quantity, grams, calories, memo
        FROM meal_entries
        ORDER BY meal_date DESC, meal_type, id
        """
    ).fetchall()
    for row in rows:
        writer.writerow(
            [
                row["meal_date"],
                row["meal_type"],
                row["food_name"],
                row["quantity"],
                row["grams"],
                row["calories"],
                row["memo"],
            ]
        )
    return "\ufeff" + output.getvalue()
