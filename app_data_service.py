from __future__ import annotations

import sqlite3
from pathlib import Path


def get_data_counts(db: sqlite3.Connection) -> dict[str, int]:
    return {
        "workouts": db.execute(
            """
            SELECT COUNT(DISTINCT s.workout_date)
            FROM workout_sessions s
            JOIN workout_sets ws ON ws.session_id = s.id
            """
        ).fetchone()[0],
        "sets": db.execute("SELECT COUNT(*) FROM workout_sets").fetchone()[0],
        "meals": db.execute("SELECT COUNT(*) FROM meal_entries").fetchone()[0],
        "routines": db.execute("SELECT COUNT(*) FROM routine_templates").fetchone()[0],
        "meal_templates": db.execute("SELECT COUNT(*) FROM meal_templates").fetchone()[0],
        "recovery": db.execute("SELECT COUNT(*) FROM recovery_checkins").fetchone()[0],
        "empty_workouts": db.execute(
            """
            SELECT COUNT(*)
            FROM workout_sessions
            WHERE COALESCE(completed, 0) = 0
              AND id NOT IN (SELECT DISTINCT session_id FROM workout_sets)
              AND workout_date NOT IN (SELECT DISTINCT meal_date FROM meal_entries)
            """
        ).fetchone()[0],
    }


def get_backup_status(base_dir: Path) -> dict[str, str]:
    backup_dirs = [base_dir / "instance" / "delete_backups", base_dir / "instance" / "restore_backups"]
    files = []
    for backup_dir in backup_dirs:
        if backup_dir.exists():
            files.extend(path for path in backup_dir.glob("*.json") if path.is_file())
    if not files:
        return {"last_backup": "없음", "count": "0"}
    latest = max(files, key=lambda path: path.stat().st_mtime)
    return {"last_backup": latest.name, "count": str(len(files))}


def get_sample_data_counts(db: sqlite3.Connection) -> dict[str, int]:
    return {
        "exercises": db.execute("SELECT COUNT(*) FROM exercises WHERE name LIKE '샘플%' OR name LIKE 'PR확인%'").fetchone()[0],
        "sets": db.execute(
            """
            SELECT COUNT(*)
            FROM workout_sets ws
            JOIN exercises e ON e.id = ws.exercise_id
            WHERE e.name LIKE '샘플%' OR e.name LIKE 'PR확인%'
            """
        ).fetchone()[0],
        "meals": db.execute("SELECT COUNT(*) FROM meal_entries WHERE food_name LIKE '샘플%'").fetchone()[0],
        "prs": db.execute("SELECT COUNT(*) FROM pr_events WHERE exercise_name LIKE '샘플%' OR exercise_name LIKE 'PR확인%'").fetchone()[0],
    }
