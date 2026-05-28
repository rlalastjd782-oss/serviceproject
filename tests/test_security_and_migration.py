from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

import app as app_module
from health_tracker.security import make_password_hash, verify_password_hash


TEST_TMP_DIR = Path(__file__).resolve().parents[1] / ".test-tmp"


class SecurityHelperTest(unittest.TestCase):
    def test_password_hash_uses_pbkdf2_and_rejects_wrong_password(self) -> None:
        stored_hash = make_password_hash("1234")

        self.assertTrue(stored_hash.startswith("pbkdf2_sha256$"))
        self.assertTrue(verify_password_hash("1234", stored_hash))
        self.assertFalse(verify_password_hash("wrong", stored_hash))
        self.assertFalse(verify_password_hash("1234", "legacy-or-broken-hash"))


class LegacyMigrationTest(unittest.TestCase):
    def test_legacy_workout_sessions_without_location_id_migrates_before_index(self) -> None:
        TEST_TMP_DIR.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP_DIR) as tmpdir:
            original_database = app_module.DATABASE
            app_module.DATABASE = Path(tmpdir) / "legacy-workout.db"
            try:
                db = sqlite3.connect(app_module.DATABASE)
                try:
                    db.execute(
                        """
                        CREATE TABLE workout_sessions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            workout_date TEXT NOT NULL UNIQUE,
                            note TEXT NOT NULL DEFAULT '',
                            completed INTEGER NOT NULL DEFAULT 0,
                            duration_seconds INTEGER NOT NULL DEFAULT 0,
                            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                    db.commit()
                finally:
                    db.close()

                with app_module.app.app_context():
                    app_module.init_db()
                db = sqlite3.connect(app_module.DATABASE)
                try:
                    columns = [row[1] for row in db.execute("PRAGMA table_info(workout_sessions)").fetchall()]
                    indexes = [row[1] for row in db.execute("PRAGMA index_list(workout_sessions)").fetchall()]
                finally:
                    db.close()
                self.assertIn("location_id", columns)
                self.assertIn("idx_workout_sessions_location", indexes)
            finally:
                app_module.DATABASE = original_database

    def test_database_pragmas_and_performance_indexes_are_enabled(self) -> None:
        TEST_TMP_DIR.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP_DIR) as tmpdir:
            original_database = app_module.DATABASE
            app_module.DATABASE = Path(tmpdir) / "pragmas.db"
            try:
                with app_module.app.app_context():
                    app_module.init_db()
                    db = app_module.get_db()
                    self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
                    self.assertGreaterEqual(db.execute("PRAGMA busy_timeout").fetchone()[0], 5000)
                db = sqlite3.connect(app_module.DATABASE)
                try:
                    indexes = {
                        row[1]
                        for table in ("workout_sessions", "workout_sets", "meal_entries", "pr_events", "location_equipment")
                        for row in db.execute(f"PRAGMA index_list({table})").fetchall()
                    }
                finally:
                    db.close()
                self.assertIn("idx_workout_sessions_date_location", indexes)
                self.assertIn("idx_workout_sets_session_sort", indexes)
                self.assertIn("idx_workout_sets_exercise_body", indexes)
                self.assertIn("idx_workout_sets_body_part_session", indexes)
                self.assertIn("idx_meal_entries_type_date", indexes)
                self.assertIn("idx_meal_entries_food_date", indexes)
                self.assertIn("idx_meal_entries_date_type_food", indexes)
                self.assertIn("idx_pr_events_exercise_date", indexes)
                self.assertIn("idx_location_equipment_location_active", indexes)
            finally:
                app_module.DATABASE = original_database
