from __future__ import annotations

import sqlite3
from collections.abc import Callable


def ensure_column(db: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    columns = [row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def migrate_machine_equipment_categories(db: sqlite3.Connection) -> None:
    for table in ("workout_sets", "exercise_settings", "routine_items"):
        db.execute(f"UPDATE {table} SET equipment = '핀머신' WHERE equipment = '머신'")
    db.execute(
        """
        UPDATE location_equipment
        SET equipment_type = '핀머신'
        WHERE equipment_type = '머신'
        """
    )
    db.execute(
        """
        UPDATE location_equipment
        SET equipment_name = '핀머신'
        WHERE equipment_name = '머신'
          AND NOT EXISTS (
              SELECT 1
              FROM location_equipment sibling
              WHERE sibling.location_id = location_equipment.location_id
                AND sibling.equipment_name = '핀머신'
          )
        """
    )
    db.execute("UPDATE location_equipment SET is_active = 0 WHERE equipment_name = '머신'")


def init_database(
    db: sqlite3.Connection,
    recalculate_missing_exercise_calories: Callable[[], None],
    bootstrap_locations: Callable[[sqlite3.Connection], sqlite3.Row],
    delete_internal_test_data: Callable[[], None],
) -> None:
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_date TEXT NOT NULL UNIQUE,
            location_id INTEGER,
            note TEXT NOT NULL DEFAULT '',
            completed INTEGER NOT NULL DEFAULT 0,
            duration_seconds INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS workout_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            body_part TEXT NOT NULL DEFAULT '기타',
            set_type TEXT NOT NULL DEFAULT '본세트',
            weight REAL,
            reps INTEGER,
            equipment TEXT NOT NULL DEFAULT '',
            cardio_incline REAL,
            cardio_speed REAL,
            cardio_minutes REAL,
            estimated_calories REAL,
            memo TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES workout_sessions (id) ON DELETE CASCADE,
            FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS meal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_date TEXT NOT NULL,
            meal_type TEXT NOT NULL DEFAULT '',
            food_name TEXT NOT NULL,
            quantity REAL,
            grams REAL,
            calories REAL,
            protein REAL,
            carbs REAL,
            fat REAL,
            memo TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS routine_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS routine_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            routine_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            body_part TEXT NOT NULL DEFAULT '기타',
            set_type TEXT NOT NULL DEFAULT '본세트',
            weight REAL,
            reps INTEGER,
            cardio_incline REAL,
            cardio_speed REAL,
            cardio_minutes REAL,
            equipment TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (routine_id) REFERENCES routine_templates (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_goals (
            key TEXT PRIMARY KEY,
            value INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS exercise_notes (
            exercise_name TEXT PRIMARY KEY,
            note TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS exercise_settings (
            exercise_name TEXT PRIMARY KEY,
            location_id INTEGER,
            rest_seconds INTEGER NOT NULL DEFAULT 90,
            is_favorite INTEGER NOT NULL DEFAULT 0,
            equipment TEXT NOT NULL DEFAULT '',
            target_weight REAL,
            target_reps INTEGER,
            target_sets INTEGER,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS food_favorites (
            food_name TEXT PRIMARY KEY,
            quantity REAL,
            grams REAL,
            calories REAL,
            is_favorite INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS workout_plan_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_date TEXT NOT NULL,
            body_part TEXT NOT NULL DEFAULT '기타',
            exercise_name TEXT NOT NULL,
            target_sets INTEGER NOT NULL DEFAULT 3,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pr_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_date TEXT NOT NULL,
            set_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            record_type TEXT NOT NULL,
            record_value REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS body_metrics (
            metric_date TEXT PRIMARY KEY,
            body_weight REAL,
            muscle_mass REAL,
            body_fat REAL,
            waist REAL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS body_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_date TEXT NOT NULL,
            file_path TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS meal_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS meal_template_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            meal_type TEXT NOT NULL DEFAULT '',
            food_name TEXT NOT NULL,
            quantity REAL,
            grams REAL,
            calories REAL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (template_id) REFERENCES meal_templates (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS recovery_checkins (
            checkin_date TEXT PRIMARY KEY,
            condition_score INTEGER NOT NULL DEFAULT 3,
            sleep_score INTEGER NOT NULL DEFAULT 3,
            soreness_score INTEGER NOT NULL DEFAULT 3,
            fatigue_score INTEGER NOT NULL DEFAULT 3,
            is_rest_day INTEGER NOT NULL DEFAULT 0,
            rest_reason TEXT NOT NULL DEFAULT '',
            memo TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS reminder_settings (
            key TEXT PRIMARY KEY,
            enabled INTEGER NOT NULL DEFAULT 0,
            time_text TEXT NOT NULL DEFAULT '',
            message TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS workout_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            address TEXT NOT NULL DEFAULT '',
            memo TEXT NOT NULL DEFAULT '',
            is_default INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS location_equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,
            equipment_name TEXT NOT NULL,
            equipment_type TEXT NOT NULL DEFAULT '',
            memo TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(location_id, equipment_name),
            FOREIGN KEY (location_id) REFERENCES workout_locations (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_workout_sessions_date ON workout_sessions(workout_date);
        CREATE INDEX IF NOT EXISTS idx_workout_sets_session ON workout_sets(session_id);
        CREATE INDEX IF NOT EXISTS idx_workout_sets_exercise ON workout_sets(exercise_id);
        CREATE INDEX IF NOT EXISTS idx_workout_sets_body_part ON workout_sets(body_part);
        CREATE INDEX IF NOT EXISTS idx_workout_sets_equipment ON workout_sets(equipment);
        CREATE INDEX IF NOT EXISTS idx_meal_entries_date ON meal_entries(meal_date);
        CREATE INDEX IF NOT EXISTS idx_pr_events_exercise ON pr_events(exercise_id);
        CREATE INDEX IF NOT EXISTS idx_pr_events_date ON pr_events(workout_date);
        CREATE INDEX IF NOT EXISTS idx_location_equipment_location ON location_equipment(location_id);
        """
    )
    for table, column, column_type in [
        ("workout_sets", "body_part", "TEXT NOT NULL DEFAULT '기타'"),
        ("workout_sessions", "location_id", "INTEGER"),
        ("workout_sessions", "completed", "INTEGER NOT NULL DEFAULT 0"),
        ("workout_sessions", "duration_seconds", "INTEGER NOT NULL DEFAULT 0"),
        ("workout_sets", "set_type", "TEXT NOT NULL DEFAULT '본세트'"),
        ("workout_sets", "cardio_incline", "REAL"),
        ("workout_sets", "cardio_speed", "REAL"),
        ("workout_sets", "cardio_minutes", "REAL"),
        ("workout_sets", "estimated_calories", "REAL"),
        ("workout_sets", "rpe", "REAL"),
        ("workout_sets", "equipment", "TEXT NOT NULL DEFAULT ''"),
        ("exercise_settings", "equipment", "TEXT NOT NULL DEFAULT ''"),
        ("exercise_settings", "location_id", "INTEGER"),
        ("exercise_settings", "target_weight", "REAL"),
        ("exercise_settings", "target_reps", "INTEGER"),
        ("exercise_settings", "target_sets", "INTEGER"),
        ("routine_items", "set_type", "TEXT NOT NULL DEFAULT '본세트'"),
        ("routine_items", "cardio_incline", "REAL"),
        ("routine_items", "cardio_speed", "REAL"),
        ("routine_items", "cardio_minutes", "REAL"),
        ("routine_items", "equipment", "TEXT NOT NULL DEFAULT ''"),
        ("routine_templates", "location_id", "INTEGER"),
        ("meal_entries", "quantity", "REAL"),
        ("meal_entries", "grams", "REAL"),
        ("recovery_checkins", "is_rest_day", "INTEGER NOT NULL DEFAULT 0"),
        ("recovery_checkins", "rest_reason", "TEXT NOT NULL DEFAULT ''"),
        ("reminder_settings", "enabled", "INTEGER NOT NULL DEFAULT 0"),
        ("reminder_settings", "time_text", "TEXT NOT NULL DEFAULT ''"),
        ("reminder_settings", "message", "TEXT NOT NULL DEFAULT ''"),
        ("app_settings", "value", "TEXT NOT NULL DEFAULT ''"),
    ]:
        ensure_column(db, table, column, column_type)
    db.execute("CREATE INDEX IF NOT EXISTS idx_workout_sessions_location ON workout_sessions(location_id)")
    db.execute(
        """
        UPDATE meal_entries
        SET
            quantity = COALESCE(quantity, calories),
            grams = COALESCE(grams, protein),
            calories = NULL,
            protein = NULL
        WHERE quantity IS NULL
          AND grams IS NULL
          AND (calories IS NOT NULL OR protein IS NOT NULL)
          AND carbs IS NULL
          AND fat IS NULL
        """
    )
    migrate_machine_equipment_categories(db)
    recalculate_missing_exercise_calories()
    bootstrap_locations(db)
    delete_internal_test_data()
    db.commit()
