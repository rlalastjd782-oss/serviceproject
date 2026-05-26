from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path


DELETE_ALL_TABLES = [
    "meal_template_items",
    "meal_templates",
    "routine_items",
    "routine_templates",
    "workout_plan_items",
    "pr_events",
    "workout_sets",
    "workout_sessions",
    "meal_entries",
    "body_photos",
    "body_metrics",
    "recovery_checkins",
    "exercise_notes",
    "exercise_settings",
    "food_favorites",
    "user_goals",
    "exercises",
]


def delete_empty_workout_sessions(db: sqlite3.Connection) -> None:
    db.execute(
        """
        DELETE FROM workout_sessions
        WHERE COALESCE(completed, 0) = 0
          AND id NOT IN (SELECT DISTINCT session_id FROM workout_sets)
          AND workout_date NOT IN (SELECT DISTINCT meal_date FROM meal_entries)
        """
    )


def delete_all_data(
    db: sqlite3.Connection,
    base_dir: Path,
    export_payload: Callable[[], dict[str, object]],
) -> None:
    backup_dir = base_dir / "instance" / "delete_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"before-delete-all-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    backup_path.write_text(json.dumps(export_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
    for table in DELETE_ALL_TABLES:
        db.execute(f"DELETE FROM {table}")
    db.commit()


def delete_internal_test_data(db: sqlite3.Connection) -> None:
    db.execute("DELETE FROM exercise_settings WHERE exercise_name LIKE '__%점검__'")
    db.execute("DELETE FROM workout_plan_items WHERE exercise_name LIKE '__%점검%'")
