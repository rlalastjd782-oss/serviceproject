from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterable


CRITICAL_INDEXES = {
    "idx_workout_sessions_date",
    "idx_workout_sessions_date_location",
    "idx_workout_sets_session",
    "idx_workout_sets_session_sort",
    "idx_workout_sets_exercise",
    "idx_workout_sets_exercise_body",
    "idx_workout_sets_body_part",
    "idx_workout_sets_body_part_session",
    "idx_meal_entries_date",
    "idx_meal_entries_type_date",
    "idx_meal_entries_food_date",
    "idx_meal_entries_date_type_food",
    "idx_pr_events_date",
    "idx_pr_events_exercise",
    "idx_pr_events_exercise_date",
    "idx_location_equipment_location_active",
}


def run_database_analyze(db: sqlite3.Connection) -> None:
    db.execute("ANALYZE")
    db.commit()


def list_database_indexes(db: sqlite3.Connection, tables: Iterable[str]) -> set[str]:
    indexes: set[str] = set()
    for table in tables:
        indexes.update(row["name"] for row in db.execute(f"PRAGMA index_list({table})").fetchall())
    return indexes


def explain_query_plan(db: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()) -> list[str]:
    rows = db.execute(f"EXPLAIN QUERY PLAN {sql}", params).fetchall()
    return [str(row["detail"]) for row in rows]


def build_performance_snapshot(db: sqlite3.Connection) -> dict[str, object]:
    tables = ("workout_sessions", "workout_sets", "meal_entries", "pr_events", "location_equipment")
    indexes = list_database_indexes(db, tables)
    missing_indexes = sorted(CRITICAL_INDEXES - indexes)
    return {
        "critical_index_count": len(CRITICAL_INDEXES),
        "present_index_count": len(CRITICAL_INDEXES) - len(missing_indexes),
        "missing_indexes": missing_indexes,
        "query_plans": {
            "recent_workout_sets": explain_query_plan(
                db,
                """
                SELECT ws.id
                FROM workout_sets ws
                JOIN workout_sessions s ON s.id = ws.session_id
                WHERE s.workout_date BETWEEN ? AND ?
                ORDER BY s.workout_date DESC, ws.sort_order
                LIMIT 20
                """,
                ("2026-01-01", "2026-12-31"),
            ),
            "meal_search": explain_query_plan(
                db,
                """
                SELECT id
                FROM meal_entries
                WHERE meal_date BETWEEN ? AND ?
                  AND meal_type = ?
                ORDER BY meal_date DESC
                LIMIT 20
                """,
                ("2026-01-01", "2026-12-31", "아침"),
            ),
            "pr_history": explain_query_plan(
                db,
                """
                SELECT id
                FROM pr_events
                WHERE exercise_id = ?
                ORDER BY workout_date DESC
                LIMIT 20
                """,
                (1,),
            ),
        },
    }


def build_page_timing_snapshot(app, account_id: int | None, paths: list[tuple[str, str]]) -> list[dict[str, object]]:
    timings: list[dict[str, object]] = []
    with app.test_client() as client:
        if account_id:
            with client.session_transaction() as test_session:
                test_session["account_id"] = account_id
                test_session["settings_unlocked"] = True
        for label, path in paths:
            started_at = time.perf_counter()
            response = client.get(path)
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 1)
            timings.append(
                {
                    "label": label,
                    "path": path,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                    "size_kb": round(len(response.get_data()) / 1024, 1),
                    "tone": "slow" if elapsed_ms >= 700 else "warn" if elapsed_ms >= 300 else "ok",
                }
            )
    return timings
