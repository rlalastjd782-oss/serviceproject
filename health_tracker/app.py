from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Flask, Response, abort, g, jsonify, redirect, render_template, request, session, url_for

from health_tracker.config import APP_TIMEZONE, BASE_DIR, DATABASE, PHOTO_DIR
from health_tracker.constants import (
    BODY_PART_CLASSES,
    BODY_PARTS,
    DEFAULT_BODY_WEIGHT_KG,
    DEFAULT_PROGRAMS,
    EQUIPMENT_OPTIONS,
    MEAL_TYPE_CLASSES,
    RECOMMENDED_EXERCISE_MAP,
)
from health_tracker.meta import get_app_updated_at, get_app_version
from health_tracker.security import (
    ADMIN_GET_ENDPOINTS,
    PUBLIC_POST_ENDPOINTS,
    ensure_csrf_token,
    make_password_hash,
    validate_csrf_token,
    verify_password_hash,
)
from health_tracker.services.admin import build_app_health_status
from health_tracker.services.data import (
    get_backup_status as build_backup_status,
    get_data_counts as build_data_counts,
    get_sample_data_counts as build_sample_data_counts,
)
from health_tracker.services.data_quality import (
    build_data_quality_profile_from_db,
    list_record_gaps_from_db,
)
from health_tracker.services.dummy_data import generate_year_qa_dummy_data as generate_year_qa_dummy_data_in_db
from health_tracker.services.dummy_data import get_qa_dummy_status as get_qa_dummy_status_from_db
from health_tracker.services.export import (
    export_all_data_from_db,
    export_meal_csv_from_db,
    export_workout_csv_from_db,
)
from health_tracker.services.location import (
    bootstrap_locations,
    deactivate_location,
    deactivate_location_equipment,
    delete_location_if_unused,
    get_location as get_location_from_db,
    get_recent_or_default_location as get_recent_or_default_location_from_db,
    list_location_equipment as list_location_equipment_from_db,
    list_locations as list_locations_from_db,
    location_equipment_names as location_equipment_names_from_db,
    save_location as save_location_to_db,
    set_default_location as set_default_location_in_db,
    set_session_location as set_session_location_in_db,
    upsert_location_equipment,
)
from health_tracker.services.meal import (
    build_monthly_meal_summary_from_db,
    build_weekly_meal_summary_from_db,
    grouped_meals_for_date_from_db,
    list_meals_for_date_from_db,
    list_monthly_meal_weeks_from_db,
    list_weekly_meal_days_from_db,
)
from health_tracker.services.pagination import PER_PAGE_OPTIONS, build_pagination, page_params, query_url
from health_tracker.services.pr import build_pr_cards_from_rows, build_pr_dashboard_from_rows
from health_tracker.services.summary import build_daily_chart_from_rows, build_period_chart_from_rows
from health_tracker.services.workout import grouped_sets_for_session_from_db, list_sets_for_session_from_db
from health_tracker.services.yearly import (
    build_yearly_report as build_yearly_report_from_db,
    compare_yearly_reports,
    export_yearly_meal_rows,
    export_yearly_workout_rows,
    list_yearly_body_part_summary as list_yearly_body_part_summary_from_db,
    list_yearly_month_rows as list_yearly_month_rows_from_db,
    list_yearly_top_exercises as list_yearly_top_exercises_from_db,
    normalize_year,
)
from health_tracker.utils import (
    duration_hours,
    duration_minutes,
    format_duration,
    parse_duration_seconds,
    parse_float,
    parse_int,
    value_at,
)


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder=str(BASE_DIR / "static"), static_url_path="/static")
    app.config["DATABASE"] = DATABASE
    app.secret_key = get_or_create_secret_key()
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
    )

    @app.before_request
    def before_request() -> None:
        init_db()
        ensure_csrf_token()
        if request.method == "POST":
            json_payload = request.get_json(silent=True) if request.is_json else None
            json_token = json_payload.get("csrf_token") if isinstance(json_payload, dict) else None
            if not validate_csrf_token(request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or json_token):
                abort(400)
            if request.endpoint not in PUBLIC_POST_ENDPOINTS and not settings_unlocked():
                abort(403)
        if request.method == "GET" and request.endpoint in ADMIN_GET_ENDPOINTS and not settings_unlocked():
            return redirect(url_for("settings_page"))

    @app.teardown_appcontext
    def close_db(error: Exception | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.context_processor
    def inject_app_meta() -> dict[str, object]:
        return {
            "app_version": get_app_version(),
            "app_updated_at": get_app_updated_at(),
            "is_admin": settings_unlocked(),
            "csrf_token": ensure_csrf_token,
            "per_page_options": PER_PAGE_OPTIONS,
            "query_url": lambda **updates: query_url(request.path, request.args, **updates),
        }

    from health_tracker.routes.main import register_routes

    register_routes(app, globals())

    return app


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        DATABASE.parent.mkdir(exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db() -> None:
    db = get_db()
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
    ensure_column(db, "workout_sets", "body_part", "TEXT NOT NULL DEFAULT '기타'")
    ensure_column(db, "workout_sessions", "location_id", "INTEGER")
    ensure_column(db, "workout_sessions", "completed", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(db, "workout_sessions", "duration_seconds", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(db, "workout_sets", "set_type", "TEXT NOT NULL DEFAULT '본세트'")
    ensure_column(db, "workout_sets", "cardio_incline", "REAL")
    ensure_column(db, "workout_sets", "cardio_speed", "REAL")
    ensure_column(db, "workout_sets", "cardio_minutes", "REAL")
    ensure_column(db, "workout_sets", "estimated_calories", "REAL")
    ensure_column(db, "workout_sets", "rpe", "REAL")
    ensure_column(db, "workout_sets", "equipment", "TEXT NOT NULL DEFAULT ''")
    ensure_column(db, "exercise_settings", "equipment", "TEXT NOT NULL DEFAULT ''")
    ensure_column(db, "exercise_settings", "location_id", "INTEGER")
    ensure_column(db, "exercise_settings", "target_weight", "REAL")
    ensure_column(db, "exercise_settings", "target_reps", "INTEGER")
    ensure_column(db, "exercise_settings", "target_sets", "INTEGER")
    ensure_column(db, "routine_items", "set_type", "TEXT NOT NULL DEFAULT '본세트'")
    ensure_column(db, "routine_items", "cardio_incline", "REAL")
    ensure_column(db, "routine_items", "cardio_speed", "REAL")
    ensure_column(db, "routine_items", "cardio_minutes", "REAL")
    ensure_column(db, "routine_items", "equipment", "TEXT NOT NULL DEFAULT ''")
    ensure_column(db, "routine_templates", "location_id", "INTEGER")
    ensure_column(db, "meal_entries", "quantity", "REAL")
    ensure_column(db, "meal_entries", "grams", "REAL")
    ensure_column(db, "recovery_checkins", "is_rest_day", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(db, "recovery_checkins", "rest_reason", "TEXT NOT NULL DEFAULT ''")
    ensure_column(db, "reminder_settings", "enabled", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(db, "reminder_settings", "time_text", "TEXT NOT NULL DEFAULT ''")
    ensure_column(db, "reminder_settings", "message", "TEXT NOT NULL DEFAULT ''")
    ensure_column(db, "app_settings", "value", "TEXT NOT NULL DEFAULT ''")
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
    recalculate_missing_exercise_calories()
    bootstrap_locations(db)
    delete_internal_test_data()
    db.commit()


def ensure_column(db: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    columns = [row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def get_or_create_secret_key() -> str:
    secret_path = BASE_DIR / "instance" / "secret_key.txt"
    secret_path.parent.mkdir(exist_ok=True)
    if secret_path.exists():
        secret = secret_path.read_text(encoding="utf-8").strip()
        if secret:
            return secret
    secret = secrets.token_urlsafe(32)
    secret_path.write_text(secret, encoding="utf-8")
    return secret


def get_app_setting(key: str, default: str = "") -> str:
    row = get_db().execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else default


def save_app_setting(key: str, value: str) -> None:
    get_db().execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """,
        (key, value),
    )
    get_db().commit()


def has_settings_password() -> bool:
    return bool(get_app_setting("settings_password_hash"))


def set_settings_password(password: str) -> bool:
    password = password.strip()
    if len(password) < 4:
        return False
    save_app_setting("settings_password_hash", make_password_hash(password))
    session["settings_unlocked"] = True
    return True


def verify_settings_password(password: str) -> bool:
    stored_hash = get_app_setting("settings_password_hash")
    return bool(stored_hash and verify_password_hash(password, stored_hash))


def settings_unlocked() -> bool:
    return has_settings_password() and bool(session.get("settings_unlocked"))


def reset_settings_password() -> None:
    save_app_setting("settings_password_hash", "")
    session.pop("settings_unlocked", None)


def get_qa_dummy_status() -> dict[str, object]:
    return get_qa_dummy_status_from_db(get_db())


def generate_year_qa_dummy_data() -> dict[str, object]:
    return generate_year_qa_dummy_data_in_db(get_db())


def get_or_create_session(workout_date: str | None = None, location_id: int | None = None) -> sqlite3.Row:
    db = get_db()
    date_value = normalize_date(workout_date)
    location = get_location_from_db(db, location_id) if location_id else get_recent_or_default_location_from_db(db)
    existing = db.execute(
        "SELECT * FROM workout_sessions WHERE workout_date = ?",
        (date_value,),
    ).fetchone()
    if existing:
        if location_id and existing["location_id"] != location["id"]:
            db.execute(
                "UPDATE workout_sessions SET location_id = ? WHERE id = ?",
                (location["id"], existing["id"]),
            )
            db.commit()
            return get_session_by_date(date_value)
        return existing

    db.execute(
        "INSERT INTO workout_sessions (workout_date, location_id) VALUES (?, ?)",
        (date_value, location["id"]),
    )
    db.commit()
    return db.execute(
        "SELECT * FROM workout_sessions WHERE workout_date = ?",
        (date_value,),
    ).fetchone()


def get_session_by_date(workout_date: str) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM workout_sessions WHERE workout_date = ?",
        (workout_date,),
    ).fetchone()


def get_session_by_id(session_id: int) -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM workout_sessions WHERE id = ?", (session_id,)).fetchone()


def mark_session_completed(session_id: int, completed: bool) -> None:
    get_db().execute("UPDATE workout_sessions SET completed = ? WHERE id = ?", (1 if completed else 0, session_id))
    get_db().commit()


def update_session_duration(session_id: int, duration_seconds: int) -> None:
    get_db().execute(
        "UPDATE workout_sessions SET duration_seconds = ? WHERE id = ?",
        (max(0, int(duration_seconds or 0)), session_id),
    )
    get_db().commit()


def reorder_set_within_exercise(db: sqlite3.Connection, set_id: int, requested_set_number: int) -> None:
    current = db.execute(
        """
        SELECT session_id, exercise_id, COALESCE(NULLIF(body_part, ''), '기타') AS body_part
        FROM workout_sets
        WHERE id = ?
        """,
        (set_id,),
    ).fetchone()
    if not current:
        return

    rows = db.execute(
        """
        SELECT id, sort_order
        FROM workout_sets
        WHERE session_id = ?
          AND exercise_id = ?
          AND COALESCE(NULLIF(body_part, ''), '기타') = ?
        ORDER BY sort_order, id
        """,
        (current["session_id"], current["exercise_id"], current["body_part"]),
    ).fetchall()
    if len(rows) <= 1:
        return

    ordered_ids = [int(row["id"]) for row in rows]
    if set_id not in ordered_ids:
        return
    ordered_ids.remove(set_id)
    target_index = min(max(requested_set_number, 1), len(rows)) - 1
    ordered_ids.insert(target_index, set_id)
    sort_orders = [int(row["sort_order"] or 0) for row in rows]
    for new_order, row_id in zip(sort_orders, ordered_ids):
        db.execute("UPDATE workout_sets SET sort_order = ? WHERE id = ?", (new_order, row_id))


def get_or_create_exercise(name: str) -> int:
    db = get_db()
    existing = db.execute("SELECT id FROM exercises WHERE name = ?", (name,)).fetchone()
    if existing:
        return int(existing["id"])
    cursor = db.execute("INSERT INTO exercises (name) VALUES (?)", (name,))
    db.commit()
    return int(cursor.lastrowid)


def list_exercises() -> list[sqlite3.Row]:
    return get_db().execute("SELECT id, name FROM exercises ORDER BY name").fetchall()


def list_exercises_by_body_part() -> dict[str, list[str]]:
    rows = get_db().execute(
        """
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.name,
            COUNT(ws.id) AS use_count,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        GROUP BY body_part, e.name
        ORDER BY body_part, last_date DESC, use_count DESC, e.name
        """
    ).fetchall()
    exercises_by_part = {part: [] for part in body_part_options()}
    for row in rows:
        part = row["body_part"] or "기타"
        exercises_by_part.setdefault(part, []).append(row["name"])
    return exercises_by_part


def list_recent_sets_by_exercise(limit: int = 6) -> dict[str, list[dict[str, float | int | None]]]:
    rows = get_db().execute(
        """
        SELECT e.name, ws.weight, ws.reps, s.workout_date, ws.sort_order
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.weight IS NOT NULL OR ws.reps IS NOT NULL
        ORDER BY s.workout_date DESC, ws.sort_order ASC, ws.id ASC
        """
    ).fetchall()
    grouped: dict[str, list[dict[str, float | int | None]]] = {}
    seen_dates: set[str] = set()
    for row in rows:
        name = row["name"]
        if name in grouped and len(grouped[name]) >= limit:
            continue
        marker = f"{name}:{row['workout_date']}"
        if marker in seen_dates:
            grouped.setdefault(name, []).append({"weight": row["weight"], "reps": row["reps"]})
        elif name not in grouped:
            grouped[name] = [{"weight": row["weight"], "reps": row["reps"]}]
            seen_dates.add(marker)
    return grouped


def list_exercise_stats_by_name() -> dict[str, dict[str, object]]:
    rows = get_db().execute(
        """
        SELECT
            e.name,
            MAX(ws.weight) AS best_weight,
            MAX(ws.reps) AS best_reps,
            MAX(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)) AS best_volume,
            (
                SELECT s2.workout_date || ' · ' || COALESCE(ws2.weight, 0) || 'kg ' || COALESCE(ws2.reps, 0) || '회'
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id
                  AND (ws2.weight IS NOT NULL OR ws2.reps IS NOT NULL)
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS recent
        FROM exercises e
        JOIN workout_sets ws ON ws.exercise_id = e.id
        WHERE ws.weight IS NOT NULL OR ws.reps IS NOT NULL
        GROUP BY e.id, e.name
        """
    ).fetchall()
    return {
        row["name"]: {
            "recent": row["recent"],
            "best_weight": row["best_weight"],
            "best_reps": row["best_reps"],
            "best_volume": row["best_volume"],
        }
        for row in rows
    }


def list_foods_by_meal_type(limit: int = 12) -> dict[str, list[dict[str, float | str | None]]]:
    rows = get_db().execute(
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
    grouped = {meal_type: [] for meal_type in ["아침", "점심", "저녁", "간식", "기타"]}
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


def list_favorite_foods() -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT food_name, quantity, grams, calories
        FROM food_favorites
        WHERE is_favorite = 1
        ORDER BY updated_at DESC, food_name
        """
    ).fetchall()


def save_food_favorite(food_name: str, quantity: float | None, grams: float | None, calories: float | None) -> None:
    get_db().execute(
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
    get_db().commit()


def delete_food_favorite(food_name: str) -> None:
    get_db().execute("DELETE FROM food_favorites WHERE food_name = ?", (food_name,))
    get_db().commit()


def list_routines() -> list[dict[str, object]]:
    rows = get_db().execute(
        """
        SELECT
            rt.id,
            rt.name,
            COUNT(ri.id) AS item_count,
            GROUP_CONCAT(DISTINCT COALESCE(NULLIF(ri.body_part, ''), '기타')) AS body_parts,
            COALESCE(SUM(COALESCE(ri.cardio_minutes, 0)), 0) AS cardio_minutes
        FROM routine_templates rt
        LEFT JOIN routine_items ri ON ri.routine_id = rt.id
        GROUP BY rt.id
        ORDER BY rt.created_at DESC, rt.id DESC
        """
    ).fetchall()
    routines = []
    for row in rows:
        item_count = int(row["item_count"] or 0)
        cardio_minutes = float(row["cardio_minutes"] or 0)
        routines.append(
            {
                **dict(row),
                "body_parts": (row["body_parts"] or "").replace(",", " · "),
                "estimated_minutes": round(item_count * 3 + cardio_minutes),
            }
        )
    return routines


def rename_routine_template(routine_id: int, name: str) -> None:
    get_db().execute("UPDATE routine_templates SET name = ? WHERE id = ?", (name, routine_id))
    get_db().commit()


def delete_routine_template(routine_id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM routine_items WHERE routine_id = ?", (routine_id,))
    db.execute("DELETE FROM routine_templates WHERE id = ?", (routine_id,))
    db.commit()


def create_routine_template(name: str, session_id: int) -> None:
    db = get_db()
    items = db.execute(
        """
        SELECT
            e.name AS exercise_name,
            ws.body_part,
            ws.set_type,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.equipment,
            ws.sort_order
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE ws.session_id = ?
        ORDER BY ws.sort_order, ws.id
        """,
        (session_id,),
    ).fetchall()
    if not items:
        return
    cursor = db.execute("INSERT INTO routine_templates (name) VALUES (?)", (name,))
    routine_id = int(cursor.lastrowid)
    for index, item in enumerate(items, start=1):
        db.execute(
            """
            INSERT INTO routine_items (
                routine_id, exercise_name, body_part, set_type, weight, reps,
                cardio_incline, cardio_speed, cardio_minutes, equipment, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                routine_id,
                item["exercise_name"],
                item["body_part"],
                item["set_type"],
                item["weight"],
                item["reps"],
                item["cardio_incline"],
                item["cardio_speed"],
                item["cardio_minutes"],
                item["equipment"],
                index,
            ),
        )
    db.commit()


def apply_routine_template(routine_id: int, workout_date: str) -> None:
    db = get_db()
    items = db.execute(
        """
        SELECT *
        FROM routine_items
        WHERE routine_id = ?
        ORDER BY sort_order, id
        """,
        (routine_id,),
    ).fetchall()
    if not items:
        return
    session = get_or_create_session(workout_date)
    next_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workout_sets WHERE session_id = ?",
        (session["id"],),
    ).fetchone()[0]
    for offset, item in enumerate(items):
        exercise_id = get_or_create_exercise(item["exercise_name"])
        db.execute(
            """
            INSERT INTO workout_sets (
                session_id, exercise_id, body_part, set_type, weight, reps,
                cardio_incline, cardio_speed, cardio_minutes, estimated_calories, equipment, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["id"],
                exercise_id,
                item["body_part"],
                item["set_type"],
                item["weight"],
                item["reps"],
                item["cardio_incline"],
                item["cardio_speed"],
                item["cardio_minutes"],
                estimate_exercise_calories(
                    item["body_part"],
                    item["cardio_incline"],
                    item["cardio_speed"],
                    item["cardio_minutes"],
                    workout_date,
                ),
                item["equipment"],
                next_order + offset,
            ),
        )
    db.commit()


def apply_session_template(source_session_id: int, workout_date: str) -> None:
    db = get_db()
    items = db.execute(
        """
        SELECT
            e.name AS exercise_name,
            ws.body_part,
            ws.set_type,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.equipment,
            ws.sort_order
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE ws.session_id = ?
        ORDER BY ws.sort_order, ws.id
        """,
        (source_session_id,),
    ).fetchall()
    if not items:
        return
    session = get_or_create_session(workout_date)
    next_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workout_sets WHERE session_id = ?",
        (session["id"],),
    ).fetchone()[0]
    for offset, item in enumerate(items):
        exercise_id = get_or_create_exercise(item["exercise_name"])
        db.execute(
            """
            INSERT INTO workout_sets (
                session_id, exercise_id, body_part, set_type, weight, reps,
                cardio_incline, cardio_speed, cardio_minutes, estimated_calories, equipment, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["id"],
                exercise_id,
                item["body_part"],
                item["set_type"],
                item["weight"],
                item["reps"],
                item["cardio_incline"],
                item["cardio_speed"],
                item["cardio_minutes"],
                estimate_exercise_calories(
                    item["body_part"],
                    item["cardio_incline"],
                    item["cardio_speed"],
                    item["cardio_minutes"],
                    workout_date,
                ),
                item["equipment"],
                next_order + offset,
            ),
        )
    db.commit()


def list_workout_plan(workout_date: str) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT
            wpi.*,
            COALESCE((
                SELECT COUNT(ws.id)
                FROM workout_sets ws
                JOIN workout_sessions s ON s.id = ws.session_id
                JOIN exercises e ON e.id = ws.exercise_id
                WHERE s.workout_date = wpi.workout_date
                  AND e.name = wpi.exercise_name
            ), 0) AS completed_sets
        FROM workout_plan_items wpi
        WHERE wpi.workout_date = ?
        ORDER BY wpi.sort_order, wpi.id
        """,
        (workout_date,),
    ).fetchall()


def build_workout_completion_summary(workout_date: str) -> dict[str, object]:
    db = get_db()
    session = get_or_create_session(workout_date)
    by_part = db.execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date = ?
        GROUP BY body_part
        ORDER BY set_count DESC, body_part
        """,
        (workout_date,),
    ).fetchall()
    top_exercise = db.execute(
        """
        SELECT e.name, COUNT(ws.id) AS set_count,
               COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.workout_date = ?
        GROUP BY e.name
        ORDER BY set_count DESC, volume DESC, e.name
        LIMIT 1
        """,
        (workout_date,),
    ).fetchone()
    plan_rows = list_workout_plan(workout_date)
    plan_total = len(plan_rows)
    plan_done = sum(1 for row in plan_rows if int(row["completed_sets"] or 0) >= int(row["target_sets"] or 1))
    return {
        "completed": bool(session["completed"]),
        "duration_seconds": int(session["duration_seconds"] or 0),
        "body_parts": [dict(row) for row in by_part],
        "top_exercise": dict(top_exercise) if top_exercise else None,
        "plan_total": plan_total,
        "plan_done": plan_done,
        "plan_percent": 0 if plan_total == 0 else round(plan_done / plan_total * 100),
    }


def build_workout_session_flow(workout_date: str) -> dict[str, object]:
    plan_rows = list_workout_plan(workout_date)
    next_item = None
    for row in plan_rows:
        if int(row["completed_sets"] or 0) < int(row["target_sets"] or 1):
            next_item = dict(row)
            break
    if next_item is None and plan_rows:
        next_item = dict(plan_rows[-1])

    last_set = get_db().execute(
        """
        SELECT
            e.name AS exercise_name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.equipment,
            ws.set_type
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date = ?
        ORDER BY ws.sort_order DESC, ws.id DESC
        LIMIT 1
        """,
        (workout_date,),
    ).fetchone()
    rest_seconds = get_exercise_rest_seconds(last_set["exercise_name"]) if last_set else 90
    return {
        "next_item": next_item,
        "last_set": dict(last_set) if last_set else None,
        "rest_seconds": rest_seconds,
        "has_plan": bool(plan_rows),
    }


def list_record_gaps(date_text: str, days: int = 7) -> list[dict[str, object]]:
    return list_record_gaps_from_db(get_db(), date_text, days)


def build_data_quality_profile(date_text: str, days: int = 14) -> dict[str, object]:
    return build_data_quality_profile_from_db(get_db(), normalize_date(date_text), days)


def create_workout_plan_item(workout_date: str, body_part: str, exercise_name: str, target_sets: int) -> None:
    db = get_db()
    next_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workout_plan_items WHERE workout_date = ?",
        (workout_date,),
    ).fetchone()[0]
    db.execute(
        """
        INSERT INTO workout_plan_items (workout_date, body_part, exercise_name, target_sets, sort_order)
        VALUES (?, ?, ?, ?, ?)
        """,
        (workout_date, body_part, exercise_name, max(1, target_sets), next_order),
    )
    db.commit()


def delete_workout_plan_item(item_id: int) -> None:
    get_db().execute("DELETE FROM workout_plan_items WHERE id = ?", (item_id,))
    get_db().commit()


def apply_default_program(program_name: str, workout_date: str) -> None:
    rows = DEFAULT_PROGRAMS.get(program_name)
    if not rows:
        return
    session = get_or_create_session(workout_date)
    db = get_db()
    next_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workout_sets WHERE session_id = ?",
        (session["id"],),
    ).fetchone()[0]
    for offset, (body_part, exercise_name, set_type, weight, reps) in enumerate(rows):
        exercise_id = get_or_create_exercise(exercise_name)
        db.execute(
            """
            INSERT INTO workout_sets (
                session_id, exercise_id, body_part, set_type, weight, reps, equipment, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session["id"], exercise_id, body_part, set_type, weight, reps, "", next_order + offset),
        )
    db.commit()


def list_recommended_sessions(workout_date: str, limit: int = 3) -> list[dict[str, object]]:
    weekday = datetime.strptime(workout_date, "%Y-%m-%d").weekday()
    rows = get_db().execute(
        """
        SELECT
            s.id,
            s.workout_date,
            COALESCE(s.duration_seconds, 0) AS duration_seconds,
            COUNT(ws.id) AS set_count,
            GROUP_CONCAT(DISTINCT COALESCE(NULLIF(ws.body_part, ''), '기타')) AS body_parts
        FROM workout_sessions s
        JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date < ?
        GROUP BY s.id, s.workout_date, s.duration_seconds
        ORDER BY s.workout_date DESC
        LIMIT 30
        """,
        (workout_date,),
    ).fetchall()
    recommendations = []
    for row in rows:
        if datetime.strptime(row["workout_date"], "%Y-%m-%d").weekday() != weekday:
            continue
        recommendations.append(
            {
                "id": row["id"],
                "workout_date": row["workout_date"],
                "duration_seconds": int(row["duration_seconds"] or 0),
                "set_count": row["set_count"],
                "body_parts": (row["body_parts"] or "").replace(",", " · "),
            }
        )
        if len(recommendations) >= limit:
            break
    return recommendations


def list_workout_focus_recommendations(workout_date: str, limit: int = 5) -> list[dict[str, object]]:
    recent_part_rows = get_db().execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date < ?
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') NOT IN ('기타')
        GROUP BY body_part
        """,
        (workout_date,),
    ).fetchall()
    last_part_dates = {row["body_part"]: row["last_date"] for row in recent_part_rows}
    today_parts = {
        row["body_part"]
        for row in get_db()
        .execute(
            """
            SELECT DISTINCT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            WHERE s.workout_date = ?
            """,
            (workout_date,),
        )
        .fetchall()
    }
    rows = get_db().execute(
        """
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.id AS exercise_id,
            e.name AS exercise_name,
            COUNT(ws.id) AS set_count,
            MAX(s.workout_date) AS last_date,
            (
                SELECT ws2.weight
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id
                  AND s2.workout_date <= ?
                  AND ws2.weight IS NOT NULL
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_weight,
            (
                SELECT ws2.reps
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id
                  AND s2.workout_date <= ?
                  AND ws2.reps IS NOT NULL
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_reps,
            (
                SELECT ws2.cardio_incline
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id
                  AND s2.workout_date <= ?
                  AND ws2.cardio_incline IS NOT NULL
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_cardio_incline,
            (
                SELECT ws2.cardio_speed
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id
                  AND s2.workout_date <= ?
                  AND ws2.cardio_speed IS NOT NULL
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_cardio_speed,
            (
                SELECT ws2.cardio_minutes
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id
                  AND s2.workout_date <= ?
                  AND ws2.cardio_minutes IS NOT NULL
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_cardio_minutes
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date <= ?
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') NOT IN ('기타')
        GROUP BY body_part, e.id, e.name
        ORDER BY last_date DESC, set_count DESC, e.name
        """,
        (workout_date, workout_date, workout_date, workout_date, workout_date, workout_date),
    ).fetchall()
    if not rows:
        return []

    date_value = datetime.strptime(workout_date, "%Y-%m-%d")
    body_priority = {part: index for index, part in enumerate(body_part_options())}
    candidates = []
    for row in rows:
        body_part = row["body_part"] or "기타"
        last_date = last_part_dates.get(body_part) or row["last_date"]
        days_since = 99
        if last_date:
            days_since = max(0, (date_value - datetime.strptime(last_date, "%Y-%m-%d")).days)
        is_today = body_part in today_parts
        if is_today:
            reason = "오늘 이미 진행 중"
        elif days_since >= 3:
            reason = f"{days_since}일 쉬어서 우선 추천"
        elif days_since >= 1:
            reason = f"최근 {days_since}일 전 진행"
        else:
            reason = "최근 기록 기반 추천"
        candidates.append(
            {
                "body_part": body_part,
                "exercise_name": row["exercise_name"],
                "set_count": int(row["set_count"] or 0),
                "last_date": row["last_date"],
                "last_weight": row["last_weight"],
                "last_reps": row["last_reps"],
                "last_cardio_incline": row["last_cardio_incline"],
                "last_cardio_speed": row["last_cardio_speed"],
                "last_cardio_minutes": row["last_cardio_minutes"],
                "reason": reason,
                "_score": (
                    1 if is_today else 0,
                    -days_since,
                    body_priority.get(body_part, 99),
                    -int(row["set_count"] or 0),
                ),
            }
        )
    candidates.sort(key=lambda item: item["_score"])
    return [{key: value for key, value in item.items() if key != "_score"} for item in candidates[:limit]]


def build_adaptive_training_recommendations(workout_date: str, limit: int = 6) -> list[dict[str, object]]:
    db = get_db()
    recovery = get_recovery_checkin(workout_date)
    readiness = (
        int(recovery["condition_score"] or 3)
        + int(recovery["sleep_score"] or 3)
        + (6 - int(recovery["soreness_score"] or 3))
        + (6 - int(recovery["fatigue_score"] or 3))
    )
    readiness_ratio = readiness / 20
    recent_start = shift_date(workout_date, -10)
    recent_load_rows = db.execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
               COUNT(ws.id) AS set_count,
               AVG(ws.rpe) AS avg_rpe
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        GROUP BY body_part
        """,
        (recent_start, workout_date),
    ).fetchall()
    recent_load = {
        row["body_part"]: {
            "set_count": int(row["set_count"] or 0),
            "avg_rpe": float(row["avg_rpe"] or 0),
        }
        for row in recent_load_rows
    }
    rows = db.execute(
        """
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.name AS exercise_name,
            MAX(s.workout_date) AS last_date,
            COUNT(ws.id) AS history_sets,
            AVG(ws.rpe) AS avg_rpe,
            (
                SELECT ws2.weight
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id AND ws2.weight IS NOT NULL AND s2.workout_date < ?
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_weight,
            (
                SELECT ws2.reps
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id AND ws2.reps IS NOT NULL AND s2.workout_date < ?
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_reps,
            (
                SELECT ws2.cardio_minutes
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id AND ws2.cardio_minutes IS NOT NULL AND s2.workout_date < ?
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_cardio_minutes
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.workout_date < ?
        GROUP BY body_part, e.id, e.name
        ORDER BY last_date DESC, history_sets DESC
        LIMIT 80
        """,
        (workout_date, workout_date, workout_date, workout_date),
    ).fetchall()
    date_value = datetime.strptime(workout_date, "%Y-%m-%d")
    items = []
    for row in rows:
        body_part = row["body_part"] or "기타"
        if body_part == "기타":
            continue
        last_date = row["last_date"]
        days_since = (date_value - datetime.strptime(last_date, "%Y-%m-%d")).days if last_date else 99
        load = recent_load.get(body_part, {"set_count": 0, "avg_rpe": 0})
        avg_rpe = float(row["avg_rpe"] or load["avg_rpe"] or 0)
        load_penalty = int(load["set_count"]) * 2 + (8 if avg_rpe >= 8.5 else 0)
        readiness_bonus = round(readiness_ratio * 12)
        score = min(100, max(0, days_since * 8 + readiness_bonus + min(int(row["history_sets"] or 0), 15) - load_penalty))
        if readiness_ratio < 0.45 and body_part != "유산소":
            action = "가볍게 유지"
            target_sets = 2
        elif avg_rpe >= 8.5 or int(load["set_count"]) >= 12:
            action = "강도 낮춤"
            target_sets = 2
        elif days_since >= 3 and readiness_ratio >= 0.65:
            action = "증량 시도"
            target_sets = 4
        else:
            action = "기록 반복"
            target_sets = 3
        next_weight = row["last_weight"]
        next_reps = row["last_reps"]
        if next_weight is not None and action == "증량 시도":
            next_weight = round(float(next_weight) + 2.5, 1)
        items.append(
            {
                "body_part": body_part,
                "exercise_name": row["exercise_name"],
                "score": score,
                "action": action,
                "target_sets": target_sets,
                "last_date": last_date,
                "last_weight": next_weight,
                "last_reps": next_reps,
                "last_cardio_minutes": row["last_cardio_minutes"],
                "reason": f"회복 {round(readiness_ratio * 100)}% · 최근 {days_since}일 전",
            }
        )
    items.sort(key=lambda item: (-int(item["score"]), item["body_part"], item["exercise_name"]))
    return items[:limit]


def build_nutrition_training_link(scope: str = "weekly", date_text: str | None = None) -> dict[str, object]:
    base_date = date_text or current_local_date()
    if scope == "monthly":
        start = normalize_month(base_date[:7])
        end = shift_date(shift_month(start, 1), -1)
    else:
        start = week_start_for_date(base_date)
        end = shift_date(start, 6)
    rows = get_db().execute(
        """
        SELECT d.day,
               COALESCE(w.set_count, 0) AS set_count,
               COALESCE(w.volume, 0) AS volume,
               COALESCE(w.duration_seconds, 0) AS duration_seconds,
               COALESCE(m.calories, 0) AS calories,
               COALESCE(m.meal_count, 0) AS meal_count
        FROM (
            SELECT workout_date AS day FROM workout_sessions WHERE workout_date BETWEEN ? AND ?
            UNION
            SELECT meal_date AS day FROM meal_entries WHERE meal_date BETWEEN ? AND ?
        ) d
        LEFT JOIN (
            SELECT s.workout_date AS day,
                   COUNT(ws.id) AS set_count,
                   COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
                   MAX(COALESCE(s.duration_seconds, 0)) AS duration_seconds
            FROM workout_sessions s
            JOIN workout_sets ws ON ws.session_id = s.id
            WHERE s.workout_date BETWEEN ? AND ?
            GROUP BY s.workout_date
        ) w ON w.day = d.day
        LEFT JOIN (
            SELECT meal_date AS day,
                   COUNT(id) AS meal_count,
                   COALESCE(SUM(COALESCE(calories, 0)), 0) AS calories
            FROM meal_entries
            WHERE meal_date BETWEEN ? AND ?
            GROUP BY meal_date
        ) m ON m.day = d.day
        ORDER BY d.day
        """,
        (start, end, start, end, start, end, start, end),
    ).fetchall()
    workout_days = [row for row in rows if int(row["set_count"] or 0) > 0]
    rest_days = [row for row in rows if int(row["set_count"] or 0) == 0 and float(row["calories"] or 0) > 0]
    workout_avg = sum(float(row["calories"] or 0) for row in workout_days) / len(workout_days) if workout_days else 0
    rest_avg = sum(float(row["calories"] or 0) for row in rest_days) / len(rest_days) if rest_days else 0
    low_fuel_days = [
        row["day"]
        for row in workout_days
        if float(row["calories"] or 0) < float(get_goal_value("daily_calories", 2200)) * 0.75
    ]
    message = "운동일 식단 데이터가 쌓이면 섭취량과 퍼포먼스 관계를 보여줍니다."
    if workout_days:
        if low_fuel_days:
            message = f"운동일 중 {len(low_fuel_days)}일은 칼로리 기록이 목표보다 낮습니다."
        elif workout_avg >= rest_avg and rest_avg > 0:
            message = "운동일 섭취 기록이 휴식일보다 높아 훈련 연료 흐름이 안정적입니다."
        else:
            message = "운동일 섭취량이 휴식일과 비슷하거나 낮습니다."
    return {
        "period": f"{start} ~ {end}",
        "workout_days": len(workout_days),
        "meal_days": sum(1 for row in rows if int(row["meal_count"] or 0) > 0),
        "workout_calorie_avg": round(workout_avg),
        "rest_calorie_avg": round(rest_avg),
        "low_fuel_days": low_fuel_days[:5],
        "message": message,
    }


def build_body_progress_insights(date_text: str) -> list[str]:
    month_start = normalize_month(date_text[:7])
    report = build_body_monthly_report(month_start)
    photos = get_db().execute(
        "SELECT COUNT(id) AS count FROM body_photos WHERE photo_date >= ? AND photo_date < ?",
        (month_start, shift_month(month_start, 1)),
    ).fetchone()["count"]
    messages = []
    if report.get("has_data"):
        messages.append(f"이번 달 체중 변화 {float(report['weight_delta'] or 0):+.1f}kg")
        messages.append(f"골격근 변화 {float(report['muscle_delta'] or 0):+.1f}kg")
        messages.append(f"체지방 변화 {float(report['fat_delta'] or 0):+.1f}%")
    else:
        messages.append("이번 달 체성분 기록이 아직 없습니다.")
    messages.append(f"이번 달 진행 사진 {int(photos or 0)}장")
    return messages[:4]


def list_exercise_library(
    body_part: str = "",
    query: str = "",
    favorite_only: bool = False,
    limit: int = 120,
) -> list[sqlite3.Row]:
    filters = ["1 = 1"]
    params: list[object] = []
    if body_part:
        filters.append("COALESCE(NULLIF(last_sets.body_part, ''), '기타') = ?")
        params.append(body_part)
    if query:
        filters.append("e.name LIKE ?")
        params.append(f"%{query}%")
    if favorite_only:
        filters.append("COALESCE(es.is_favorite, 0) = 1")
    params.append(limit)
    return get_db().execute(
        f"""
        SELECT
            e.id,
            e.name,
            COALESCE(NULLIF(last_sets.body_part, ''), '기타') AS body_part,
            COALESCE(es.is_favorite, 0) AS is_favorite,
            COALESCE(es.rest_seconds, 90) AS rest_seconds,
            COALESCE(es.equipment, last_sets.equipment, '') AS equipment,
            es.target_weight,
            es.target_reps,
            es.target_sets,
            en.note,
            COALESCE(last_sets.set_count, 0) AS set_count,
            last_sets.last_date,
            last_sets.best_weight,
            last_sets.best_volume
        FROM exercises e
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        LEFT JOIN exercise_notes en ON en.exercise_name = e.name
        LEFT JOIN (
            SELECT
                ws.exercise_id,
                COALESCE(NULLIF(MAX(ws.body_part), ''), '기타') AS body_part,
                COALESCE(NULLIF(MAX(ws.equipment), ''), '') AS equipment,
                COUNT(ws.id) AS set_count,
                MAX(s.workout_date) AS last_date,
                MAX(ws.weight) AS best_weight,
                MAX(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)) AS best_volume
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            GROUP BY ws.exercise_id
        ) last_sets ON last_sets.exercise_id = e.id
        WHERE {" AND ".join(filters)}
        ORDER BY COALESCE(es.is_favorite, 0) DESC, last_sets.last_date DESC, set_count DESC, e.name
        LIMIT ?
        """,
        params,
    ).fetchall()


def paged_exercise_library(
    body_part: str = "",
    query: str = "",
    favorite_only: bool = False,
    sort: str = "favorite",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object, str]:
    sort_options = {
        "favorite": "COALESCE(es.is_favorite, 0) DESC, last_sets.last_date DESC, set_count DESC, e.name",
        "recent": "last_sets.last_date DESC, set_count DESC, e.name",
        "name": "e.name ASC",
        "sets": "set_count DESC, last_sets.last_date DESC, e.name",
    }
    selected_sort = allowed_sort(sort, sort_options, "favorite")
    filters = ["1 = 1"]
    params: list[object] = []
    if body_part:
        filters.append("COALESCE(NULLIF(last_sets.body_part, ''), '기타') = ?")
        params.append(body_part)
    if query:
        filters.append("e.name LIKE ?")
        params.append(f"%{query}%")
    if favorite_only:
        filters.append("COALESCE(es.is_favorite, 0) = 1")
    from_sql = f"""
        FROM exercises e
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        LEFT JOIN exercise_notes en ON en.exercise_name = e.name
        LEFT JOIN (
            SELECT
                ws.exercise_id,
                COALESCE(NULLIF(MAX(ws.body_part), ''), '기타') AS body_part,
                COALESCE(NULLIF(MAX(ws.equipment), ''), '') AS equipment,
                COUNT(ws.id) AS set_count,
                MAX(s.workout_date) AS last_date,
                MAX(ws.weight) AS best_weight,
                MAX(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)) AS best_volume
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            GROUP BY ws.exercise_id
        ) last_sets ON last_sets.exercise_id = e.id
        WHERE {" AND ".join(filters)}
    """
    rows, pagination = paged_rows(
        f"""
        SELECT
            e.id,
            e.name,
            COALESCE(NULLIF(last_sets.body_part, ''), '기타') AS body_part,
            COALESCE(es.is_favorite, 0) AS is_favorite,
            COALESCE(es.rest_seconds, 90) AS rest_seconds,
            COALESCE(es.equipment, last_sets.equipment, '') AS equipment,
            es.target_weight,
            es.target_reps,
            es.target_sets,
            en.note,
            COALESCE(last_sets.set_count, 0) AS set_count,
            last_sets.last_date,
            last_sets.best_weight,
            last_sets.best_volume
        {from_sql}
        ORDER BY {sort_options[selected_sort]}
        """,
        f"SELECT COUNT(*) {from_sql}",
        params,
        page,
        per_page,
    )
    return rows, pagination, selected_sort


def build_weekly_plan_board(week_start: str) -> list[dict[str, object]]:
    return [
        {
            "date": shift_date(week_start, offset),
            "plan_items": list_workout_plan(shift_date(week_start, offset)),
            "summary": build_workout_completion_summary(shift_date(week_start, offset)),
            "recommendations": build_adaptive_training_recommendations(shift_date(week_start, offset), limit=3),
        }
        for offset in range(7)
    ]


def generate_weekly_plan(week_start: str) -> int:
    created = 0
    for offset in range(7):
        workout_date = shift_date(week_start, offset)
        if list_workout_plan(workout_date):
            continue
        recommendations = build_adaptive_training_recommendations(workout_date, limit=3)
        if not recommendations:
            recommendations = list_workout_focus_recommendations(workout_date, limit=3)
        for item in recommendations[:3]:
            create_workout_plan_item(
                workout_date,
                str(item["body_part"]),
                str(item["exercise_name"]),
                int(item.get("target_sets") or 3),
            )
            created += 1
    return created


def list_reminder_settings() -> dict[str, dict[str, object]]:
    defaults = {
        "workout": {"enabled": 0, "time_text": "18:30", "message": "운동 기록 시간입니다."},
        "meal": {"enabled": 0, "time_text": "12:30", "message": "식단 기록을 확인하세요."},
        "weekly": {"enabled": 0, "time_text": "20:00", "message": "주간 기록을 점검하세요."},
    }
    rows = get_db().execute("SELECT * FROM reminder_settings").fetchall()
    settings = {key: value.copy() for key, value in defaults.items()}
    for row in rows:
        settings[row["key"]] = {
            "enabled": int(row["enabled"] or 0),
            "time_text": row["time_text"] or defaults.get(row["key"], {}).get("time_text", ""),
            "message": row["message"] or defaults.get(row["key"], {}).get("message", ""),
        }
    return settings


def save_reminder_settings(key: str, enabled: bool, time_text: str, message: str) -> None:
    if key not in {"workout", "meal", "weekly"}:
        return
    get_db().execute(
        """
        INSERT INTO reminder_settings (key, enabled, time_text, message, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            enabled = excluded.enabled,
            time_text = excluded.time_text,
            message = excluded.message,
            updated_at = CURRENT_TIMESTAMP
        """,
        (key, 1 if enabled else 0, time_text[:5], message[:120]),
    )
    get_db().commit()


def save_goal(key: str, value: int) -> None:
    get_db().execute(
        """
        INSERT INTO user_goals (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """,
        (key, max(0, value)),
    )
    get_db().commit()


def get_goal_value(key: str, default: int) -> int:
    row = get_db().execute("SELECT value FROM user_goals WHERE key = ?", (key,)).fetchone()
    return int(row["value"]) if row else default


def get_goal_progress(date_text: str) -> dict[str, dict[str, int | float | str]]:
    week_start = week_start_for_date(date_text)
    week_end = shift_date(week_start, 6)
    month_start = normalize_month(date_text[:7])
    next_month = shift_month(month_start, 1)
    db = get_db()
    weekly_workout_days = db.execute(
        """
        SELECT COUNT(DISTINCT s.workout_date) AS count
        FROM workout_sessions s
        JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date BETWEEN ? AND ?
        """,
        (week_start, week_end),
    ).fetchone()["count"]
    weekly_meal_days = db.execute(
        """
        SELECT COUNT(DISTINCT meal_date) AS count
        FROM meal_entries
        WHERE meal_date BETWEEN ? AND ?
        """,
        (week_start, week_end),
    ).fetchone()["count"]
    weekly_calories = db.execute(
        """
        SELECT COALESCE(SUM(calories), 0) AS calories
        FROM meal_entries
        WHERE meal_date BETWEEN ? AND ?
        """,
        (week_start, week_end),
    ).fetchone()["calories"]
    monthly_volume = db.execute(
        """
        SELECT COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        """,
        (month_start, next_month),
    ).fetchone()["volume"]
    monthly_workout_days = db.execute(
        """
        SELECT COUNT(DISTINCT s.workout_date) AS count
        FROM workout_sessions s
        JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        """,
        (month_start, next_month),
    ).fetchone()["count"]
    monthly_cardio_minutes = db.execute(
        """
        SELECT COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS minutes
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        """,
        (month_start, next_month),
    ).fetchone()["minutes"]
    return {
        "weekly_workout_days": goal_item(int(weekly_workout_days), get_goal_value("weekly_workout_days", 3), "주간 운동일"),
        "weekly_meal_days": goal_item(int(weekly_meal_days), get_goal_value("weekly_meal_days", 5), "주간 식단일"),
        "weekly_calories": goal_item(float(weekly_calories), get_goal_value("weekly_calories", 14000), "주간 칼로리"),
        "monthly_volume": goal_item(float(monthly_volume), get_goal_value("monthly_volume", 10000), "월간 볼륨"),
        "monthly_workout_days": goal_item(int(monthly_workout_days), get_goal_value("monthly_workout_days", 12), "월간 운동일"),
        "monthly_cardio_minutes": goal_item(float(monthly_cardio_minutes), get_goal_value("monthly_cardio_minutes", 300), "월간 유산소"),
    }


def goal_item(current: int | float, target: int, label: str) -> dict[str, int | float | str]:
    percent = 0 if target <= 0 else min(100, round(float(current) / target * 100))
    return {"current": current, "target": target, "label": label, "percent": percent}


def get_exercise_record_values(exercise_id: int) -> dict[str, float]:
    row = get_db().execute(
        """
        SELECT
            COALESCE(MAX(weight), 0) AS max_weight,
            COALESCE(MAX(reps), 0) AS max_reps,
            COALESCE(MAX(COALESCE(weight, 0) * COALESCE(reps, 0)), 0) AS max_volume
        FROM workout_sets
        WHERE exercise_id = ?
        """,
        (exercise_id,),
    ).fetchone()
    return {
        "max_weight": float(row["max_weight"] or 0),
        "max_reps": float(row["max_reps"] or 0),
        "max_volume": float(row["max_volume"] or 0),
    }


def update_record_values(records: dict[str, float], weight: float | None, reps: int | None) -> dict[str, float]:
    volume = float(weight or 0) * float(reps or 0)
    return {
        "max_weight": max(records["max_weight"], float(weight or 0)),
        "max_reps": max(records["max_reps"], float(reps or 0)),
        "max_volume": max(records["max_volume"], volume),
    }


def record_pr_events(
    set_id: int,
    workout_date: str,
    exercise_id: int,
    exercise_name: str,
    weight: float | None,
    reps: int | None,
    previous: dict[str, float],
) -> None:
    candidates = [
        ("최고 중량", float(weight or 0), previous["max_weight"]),
        ("최고 반복", float(reps or 0), previous["max_reps"]),
        ("최고 볼륨", float(weight or 0) * float(reps or 0), previous["max_volume"]),
    ]
    for record_type, value, old_value in candidates:
        if value > 0 and value > old_value:
            get_db().execute(
                """
                INSERT INTO pr_events (workout_date, set_id, exercise_id, exercise_name, record_type, record_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (workout_date, set_id, exercise_id, exercise_name, record_type, value),
            )


def list_pr_events(workout_date: str) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT *
        FROM pr_events
        WHERE workout_date = ?
        ORDER BY id DESC
        """,
        (workout_date,),
    ).fetchall()


def build_pr_cards(workout_date: str) -> list[dict[str, object]]:
    return build_pr_cards_from_rows(list_pr_events(workout_date))


def list_recent_pr_events(limit: int = 12) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT *
        FROM pr_events
        ORDER BY workout_date DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def list_recent_pr_events_filtered(body_part: str = "", query: str = "", limit: int = 30) -> list[sqlite3.Row]:
    filters = []
    params: list[object] = []
    if body_part:
        filters.append("COALESCE(NULLIF(ws.body_part, ''), '기타') = ?")
        params.append(body_part)
    if query:
        filters.append("pe.exercise_name LIKE ?")
        params.append(f"%{query}%")
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.append(limit)
    return get_db().execute(
        f"""
        SELECT pe.*
        FROM pr_events pe
        LEFT JOIN workout_sets ws ON ws.id = pe.set_id
        {where_clause}
        ORDER BY pe.workout_date DESC, pe.id DESC
        LIMIT ?
        """,
        params,
    ).fetchall()


def list_exercise_pr_history(exercise_id: int | None, limit: int = 12) -> list[sqlite3.Row]:
    if not exercise_id:
        return []
    return get_db().execute(
        """
        SELECT *
        FROM pr_events
        WHERE exercise_id = ?
        ORDER BY workout_date DESC, id DESC
        LIMIT ?
        """,
        (exercise_id, limit),
    ).fetchall()


def list_exercise_pr_summary(body_part: str = "", query: str = "", limit: int = 80) -> list[sqlite3.Row]:
    filters = ["ws.weight IS NOT NULL", "ws.reps IS NOT NULL"]
    params: list[object] = []
    if body_part:
        filters.append("COALESCE(NULLIF(ws.body_part, ''), '기타') = ?")
        params.append(body_part)
    if query:
        filters.append("e.name LIKE ?")
        params.append(f"%{query}%")
    where_clause = " AND ".join(filters)
    params.append(limit)
    return get_db().execute(
        f"""
        SELECT
            e.id,
            e.name,
            COALESCE(NULLIF(MAX(ws.body_part), ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COUNT(DISTINCT s.workout_date) AS workout_days,
            MAX(s.workout_date) AS last_date,
            COALESCE(MAX(ws.weight), 0) AS best_weight,
            COALESCE(MAX(ws.reps), 0) AS best_reps,
            COALESCE(MAX(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS best_volume,
            COALESCE(MAX(ws.weight * (1 + ws.reps / 30.0)), 0) AS estimated_1rm
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE {where_clause}
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') != '유산소'
        GROUP BY e.id, e.name
        ORDER BY best_weight DESC, best_volume DESC, last_date DESC, e.name
        LIMIT ?
        """,
        params,
    ).fetchall()


def list_pr_exercise_choices(body_part: str = "", query: str = "") -> list[sqlite3.Row]:
    filters = ["ws.weight IS NOT NULL", "ws.reps IS NOT NULL", "COALESCE(NULLIF(ws.body_part, ''), '기타') != '유산소'"]
    params: list[object] = []
    if body_part:
        filters.append("COALESCE(NULLIF(ws.body_part, ''), '기타') = ?")
        params.append(body_part)
    if query:
        filters.append("e.name LIKE ?")
        params.append(f"%{query}%")
    return get_db().execute(
        f"""
        SELECT DISTINCT e.id, e.name
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE {' AND '.join(filters)}
        ORDER BY e.name
        """,
        params,
    ).fetchall()


def build_pr_dashboard(pr_rows: list[sqlite3.Row], recent_events: list[sqlite3.Row]) -> dict[str, object]:
    return build_pr_dashboard_from_rows(pr_rows, recent_events)


def list_exercise_best_sets(exercise_id: int | None) -> list[dict[str, object]]:
    if not exercise_id:
        return []
    rows = get_db().execute(
        """
        WITH base AS (
            SELECT
                ws.id,
                s.workout_date,
                e.name AS exercise_name,
                COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
                ws.weight,
                ws.reps,
                COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0) AS volume,
                COALESCE(ws.weight, 0) * (1 + COALESCE(ws.reps, 0) / 30.0) AS estimated_1rm,
                ws.cardio_incline,
                ws.cardio_speed,
                ws.cardio_minutes,
                ws.estimated_calories
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            JOIN exercises e ON e.id = ws.exercise_id
            WHERE ws.exercise_id = ?
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (ORDER BY weight DESC, workout_date DESC, id DESC) AS rn_weight,
                ROW_NUMBER() OVER (ORDER BY reps DESC, workout_date DESC, id DESC) AS rn_reps,
                ROW_NUMBER() OVER (ORDER BY volume DESC, workout_date DESC, id DESC) AS rn_volume,
                ROW_NUMBER() OVER (ORDER BY estimated_1rm DESC, workout_date DESC, id DESC) AS rn_1rm,
                ROW_NUMBER() OVER (ORDER BY cardio_minutes DESC, workout_date DESC, id DESC) AS rn_cardio_minutes,
                ROW_NUMBER() OVER (ORDER BY cardio_speed DESC, workout_date DESC, id DESC) AS rn_cardio_speed
            FROM base
        )
        SELECT * FROM ranked
        WHERE rn_weight = 1
           OR rn_reps = 1
           OR rn_volume = 1
           OR rn_1rm = 1
           OR rn_cardio_minutes = 1
           OR rn_cardio_speed = 1
        ORDER BY workout_date DESC, id DESC
        """,
        (exercise_id,),
    ).fetchall()
    best_items: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in rows:
        candidates = [
            ("최고 중량", row["weight"], "kg", row["rn_weight"]),
            ("최고 반복", row["reps"], "회", row["rn_reps"]),
            ("최고 볼륨", row["volume"], "kg", row["rn_volume"]),
            ("예상 1RM", row["estimated_1rm"], "kg", row["rn_1rm"]),
            ("최장 유산소", row["cardio_minutes"], "분", row["rn_cardio_minutes"]),
            ("최고 속도", row["cardio_speed"], "", row["rn_cardio_speed"]),
        ]
        for label, value, unit, rank in candidates:
            if rank == 1 and value and label not in seen:
                seen.add(label)
                best_items.append(
                    {
                        "label": label,
                        "value": float(value),
                        "unit": unit,
                        "workout_date": row["workout_date"],
                        "weight": row["weight"],
                        "reps": row["reps"],
                        "body_part": row["body_part"],
                        "cardio_incline": row["cardio_incline"],
                        "cardio_speed": row["cardio_speed"],
                        "cardio_minutes": row["cardio_minutes"],
                    }
                )
    return best_items


def list_overload_suggestions() -> dict[str, str]:
    rows = get_db().execute(
        """
        SELECT e.name, ws.weight, ws.reps, s.workout_date
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.weight IS NOT NULL AND ws.reps IS NOT NULL
        ORDER BY s.workout_date DESC, ws.sort_order DESC, ws.id DESC
        """
    ).fetchall()
    suggestions: dict[str, str] = {}
    for row in rows:
        name = row["name"]
        if name in suggestions:
            continue
        next_weight = float(row["weight"]) + 2.5
        next_reps = int(row["reps"]) + 1
        suggestions[name] = f"지난 기록 기준: {float(row['weight']):.1f}kg {int(row['reps'])}회 → {next_weight:.1f}kg 또는 {next_reps}회 도전"
    return suggestions


def list_exercise_notes() -> dict[str, str]:
    rows = get_db().execute("SELECT exercise_name, note FROM exercise_notes").fetchall()
    return {row["exercise_name"]: row["note"] for row in rows}


def save_exercise_note(exercise_name: str, note: str) -> None:
    get_db().execute(
        """
        INSERT INTO exercise_notes (exercise_name, note, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(exercise_name) DO UPDATE SET note = excluded.note, updated_at = CURRENT_TIMESTAMP
        """,
        (exercise_name, note),
    )
    get_db().commit()


def list_exercise_settings() -> dict[str, dict[str, int | float | bool | str | None]]:
    rows = get_db().execute("SELECT * FROM exercise_settings").fetchall()
    return {
        row["exercise_name"]: {
            "rest_seconds": int(row["rest_seconds"] or 90),
            "is_favorite": bool(row["is_favorite"]),
            "equipment": row["equipment"] or "",
            "target_weight": row["target_weight"],
            "target_reps": row["target_reps"],
            "target_sets": row["target_sets"],
        }
        for row in rows
    }


def save_exercise_settings(
    exercise_name: str,
    rest_seconds: int,
    is_favorite: bool,
    equipment: str = "",
    target_weight: float | None = None,
    target_reps: int | None = None,
    target_sets: int | None = None,
) -> None:
    get_db().execute(
        """
        INSERT INTO exercise_settings (
            exercise_name, rest_seconds, is_favorite, equipment,
            target_weight, target_reps, target_sets, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(exercise_name) DO UPDATE SET
            rest_seconds = excluded.rest_seconds,
            is_favorite = excluded.is_favorite,
            equipment = excluded.equipment,
            target_weight = excluded.target_weight,
            target_reps = excluded.target_reps,
            target_sets = excluded.target_sets,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            exercise_name,
            max(15, min(600, int(rest_seconds or 90))),
            1 if is_favorite else 0,
            equipment[:20],
            target_weight,
            target_reps,
            target_sets,
        ),
    )
    get_db().commit()


def save_exercise_equipment(exercise_name: str, equipment: str) -> None:
    if not exercise_name or not equipment:
        return
    get_db().execute(
        """
        INSERT INTO exercise_settings (exercise_name, equipment, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(exercise_name) DO UPDATE SET
            equipment = excluded.equipment,
            updated_at = CURRENT_TIMESTAMP
        """,
        (exercise_name, equipment[:20]),
    )


def get_exercise_rest_seconds(exercise_name: str) -> int:
    row = get_db().execute(
        "SELECT rest_seconds FROM exercise_settings WHERE exercise_name = ?",
        (exercise_name,),
    ).fetchone()
    return int(row["rest_seconds"]) if row else 90


def list_favorite_exercises() -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT
            es.exercise_name,
            es.rest_seconds,
            COALESCE(
                (
                    SELECT ws.body_part
                    FROM workout_sets ws
                    JOIN exercises e ON e.id = ws.exercise_id
                    JOIN workout_sessions s ON s.id = ws.session_id
                    WHERE e.name = es.exercise_name
                    ORDER BY s.workout_date DESC, ws.sort_order DESC, ws.id DESC
                    LIMIT 1
                ),
                '기타'
            ) AS body_part
        FROM exercise_settings es
        WHERE es.is_favorite = 1
        ORDER BY es.updated_at DESC, es.exercise_name
        """
    ).fetchall()


def equipment_options() -> list[str]:
    return EQUIPMENT_OPTIONS


def list_workout_locations(include_inactive: bool = False) -> list[sqlite3.Row]:
    return list_locations_from_db(get_db(), include_inactive)


def get_workout_location(location_id: int | None = None) -> sqlite3.Row:
    return get_location_from_db(get_db(), location_id)


def get_recent_or_default_location() -> sqlite3.Row:
    return get_recent_or_default_location_from_db(get_db())


def save_workout_location(
    name: str,
    address: str = "",
    memo: str = "",
    location_id: int | None = None,
    is_default: bool = False,
) -> int:
    saved_id = save_location_to_db(get_db(), name, address, memo, location_id, is_default)
    get_db().commit()
    return saved_id


def set_default_workout_location(location_id: int) -> None:
    set_default_location_in_db(get_db(), location_id)
    get_db().commit()


def deactivate_workout_location(location_id: int) -> None:
    deactivate_location(get_db(), location_id)
    get_db().commit()


def delete_unused_workout_location(location_id: int) -> bool:
    deleted = delete_location_if_unused(get_db(), location_id)
    get_db().commit()
    return deleted


def set_workout_session_location(session_id: int, location_id: int | None) -> sqlite3.Row:
    location = set_session_location_in_db(get_db(), session_id, location_id)
    get_db().commit()
    return location


def list_location_equipment(location_id: int | None = None, include_inactive: bool = False) -> list[sqlite3.Row]:
    return list_location_equipment_from_db(get_db(), location_id, include_inactive)


def save_location_equipment(
    location_id: int,
    equipment_name: str,
    equipment_type: str = "",
    memo: str = "",
) -> None:
    upsert_location_equipment(get_db(), location_id, equipment_name, equipment_type, memo)
    get_db().commit()


def delete_location_equipment(equipment_id: int) -> None:
    deactivate_location_equipment(get_db(), equipment_id)
    get_db().commit()


def equipment_options_for_location(location_id: int | None = None) -> list[str]:
    names = location_equipment_names_from_db(get_db(), location_id)
    return list(dict.fromkeys([*names, *EQUIPMENT_OPTIONS]))


def get_body_metric(metric_date: str) -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM body_metrics WHERE metric_date = ?", (metric_date,)).fetchone()


def save_body_metric(
    metric_date: str,
    body_weight: float | None,
    muscle_mass: float | None,
    body_fat: float | None,
    waist: float | None,
) -> None:
    get_db().execute(
        """
        INSERT INTO body_metrics (metric_date, body_weight, muscle_mass, body_fat, waist, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(metric_date) DO UPDATE SET
            body_weight = excluded.body_weight,
            muscle_mass = excluded.muscle_mass,
            body_fat = excluded.body_fat,
            waist = excluded.waist,
            updated_at = CURRENT_TIMESTAMP
        """,
        (metric_date, body_weight, muscle_mass, body_fat, waist),
    )
    recalculate_exercise_calories_for_date(metric_date)
    get_db().commit()


def list_body_metrics(month_start: str) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT *
        FROM body_metrics
        WHERE metric_date >= ? AND metric_date < ?
        ORDER BY metric_date DESC
        """,
        (month_start, shift_month(month_start, 1)),
    ).fetchall()


def build_body_monthly_report(month_start: str) -> dict[str, object]:
    rows = list_body_metrics(month_start)
    if not rows:
        return {"has_data": False}
    first = rows[0]
    last = rows[-1]
    return {
        "has_data": True,
        "first_date": first["metric_date"],
        "last_date": last["metric_date"],
        "body_weight": last["body_weight"],
        "muscle_mass": last["muscle_mass"],
        "body_fat": last["body_fat"],
        "waist": last["waist"],
        "weight_delta": float(last["body_weight"] or 0) - float(first["body_weight"] or 0),
        "muscle_delta": float(last["muscle_mass"] or 0) - float(first["muscle_mass"] or 0),
        "fat_delta": float(last["body_fat"] or 0) - float(first["body_fat"] or 0),
        "waist_delta": float(last["waist"] or 0) - float(first["waist"] or 0),
    }


def list_body_metric_trend(month_start: str) -> list[dict[str, object]]:
    rows = list_body_metrics(month_start)
    max_weight = max([float(row["body_weight"] or 0) for row in rows] + [1.0])
    return [
        {
            "period": row["metric_date"][5:],
            "body_weight": float(row["body_weight"] or 0),
            "muscle_mass": float(row["muscle_mass"] or 0),
            "body_fat": float(row["body_fat"] or 0),
            "weight_width": round(float(row["body_weight"] or 0) / max_weight * 100),
        }
        for row in rows
    ]


def save_body_photo(photo_date: str, file) -> None:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    filename = f"{photo_date}-{datetime.now().strftime('%H%M%S')}{suffix}"
    target = PHOTO_DIR / filename
    file.save(target)
    relative_path = f"progress_photos/{filename}"
    get_db().execute(
        "INSERT INTO body_photos (photo_date, file_path) VALUES (?, ?)",
        (photo_date, relative_path),
    )
    get_db().commit()


def list_body_photos(photo_date: str, limit: int = 3) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT *
        FROM body_photos
        WHERE photo_date <= ?
        ORDER BY photo_date DESC, id DESC
        LIMIT ?
        """,
        (photo_date, limit),
    ).fetchall()


def list_meal_templates() -> list[dict[str, object]]:
    rows = get_db().execute(
        """
        SELECT mt.id, mt.name, COUNT(mti.id) AS item_count
        FROM meal_templates mt
        LEFT JOIN meal_template_items mti ON mti.template_id = mt.id
        GROUP BY mt.id
        ORDER BY mt.created_at DESC, mt.id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def create_meal_template_from_day(name: str, meal_date: str) -> None:
    rows = get_db().execute(
        """
        SELECT *
        FROM meal_entries
        WHERE meal_date = ?
        ORDER BY id
        """,
        (meal_date,),
    ).fetchall()
    if not rows:
        return
    cursor = get_db().execute("INSERT INTO meal_templates (name) VALUES (?)", (name,))
    template_id = int(cursor.lastrowid)
    for index, row in enumerate(rows, start=1):
        get_db().execute(
            """
            INSERT INTO meal_template_items
                (template_id, meal_type, food_name, quantity, grams, calories, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (template_id, row["meal_type"], row["food_name"], row["quantity"], row["grams"], row["calories"], index),
        )
    get_db().commit()


def apply_meal_template(template_id: int, meal_date: str) -> None:
    rows = get_db().execute(
        """
        SELECT *
        FROM meal_template_items
        WHERE template_id = ?
        ORDER BY sort_order, id
        """,
        (template_id,),
    ).fetchall()
    for row in rows:
        get_db().execute(
            """
            INSERT INTO meal_entries (meal_date, meal_type, food_name, quantity, grams, calories)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (meal_date, row["meal_type"], row["food_name"], row["quantity"], row["grams"], row["calories"]),
        )
    get_db().commit()


def list_recent_meal_days(target_date: str, limit: int = 3) -> list[sqlite3.Row]:
    return get_db().execute(
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


def copy_meals_from_day(source_date: str, meal_date: str) -> None:
    rows = get_db().execute(
        """
        SELECT meal_type, food_name, quantity, grams, calories, memo
        FROM meal_entries
        WHERE meal_date = ?
        ORDER BY id
        """,
        (source_date,),
    ).fetchall()
    for row in rows:
        get_db().execute(
            """
            INSERT INTO meal_entries (meal_date, meal_type, food_name, quantity, grams, calories, memo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (meal_date, row["meal_type"], row["food_name"], row["quantity"], row["grams"], row["calories"], row["memo"]),
        )
    get_db().commit()


def copy_meal_type_from_day(source_date: str, meal_date: str, meal_type: str) -> None:
    rows = get_db().execute(
        """
        SELECT meal_type, food_name, quantity, grams, calories, memo
        FROM meal_entries
        WHERE meal_date = ? AND meal_type = ?
        ORDER BY id
        """,
        (source_date, meal_type),
    ).fetchall()
    for row in rows:
        get_db().execute(
            """
            INSERT INTO meal_entries (meal_date, meal_type, food_name, quantity, grams, calories, memo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (meal_date, row["meal_type"], row["food_name"], row["quantity"], row["grams"], row["calories"], row["memo"]),
        )
    get_db().commit()


def list_frequent_meal_combos(limit: int = 6) -> list[dict[str, object]]:
    rows = get_db().execute(
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


def build_weekly_report(date_text: str | None = None) -> dict[str, object]:
    week_start = week_start_for_date(date_text or current_local_date())
    week_end = shift_date(week_start, 6)
    db = get_db()
    totals = db.execute(
        """
        SELECT
            COUNT(DISTINCT CASE WHEN ws.id IS NOT NULL THEN s.workout_date END) AS workout_days,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories
        FROM workout_sessions s
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date BETWEEN ? AND ?
        """,
        (week_start, week_end),
    ).fetchone()
    meal_days = db.execute(
        "SELECT COUNT(DISTINCT meal_date) AS meal_days FROM meal_entries WHERE meal_date BETWEEN ? AND ?",
        (week_start, week_end),
    ).fetchone()["meal_days"]
    duration_seconds = db.execute(
        """
        SELECT COALESCE(SUM(s.duration_seconds), 0) AS duration_seconds
        FROM workout_sessions s
        WHERE s.workout_date BETWEEN ? AND ?
          AND EXISTS (SELECT 1 FROM workout_sets ws WHERE ws.session_id = s.id)
        """,
        (week_start, week_end),
    ).fetchone()["duration_seconds"]
    top_part = db.execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date BETWEEN ? AND ?
        GROUP BY body_part
        ORDER BY set_count DESC
        LIMIT 1
        """,
        (week_start, week_end),
    ).fetchone()
    return {
        "period": f"{week_start} ~ {week_end}",
        "workout_days": int(totals["workout_days"] or 0),
        "set_count": int(totals["set_count"] or 0),
        "volume": float(totals["volume"] or 0),
        "cardio_minutes": float(totals["cardio_minutes"] or 0),
        "exercise_calories": float(totals["exercise_calories"] or 0),
        "duration_seconds": int(duration_seconds or 0),
        "meal_days": int(meal_days or 0),
        "top_part": top_part["body_part"] if top_part else "-",
    }


def build_monthly_report(date_text: str | None = None) -> dict[str, object]:
    base_date = date_text or current_local_date()
    month_start = normalize_month(base_date[:7])
    next_month = shift_month(month_start, 1)
    db = get_db()
    totals = db.execute(
        """
        SELECT
            COUNT(DISTINCT CASE WHEN ws.id IS NOT NULL THEN s.workout_date END) AS workout_days,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sessions s
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        """,
        (month_start, next_month),
    ).fetchone()
    top_exercise = db.execute(
        """
        SELECT e.name, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        GROUP BY e.name
        ORDER BY set_count DESC, e.name
        LIMIT 1
        """,
        (month_start, next_month),
    ).fetchone()
    duration_seconds = db.execute(
        """
        SELECT COALESCE(SUM(s.duration_seconds), 0) AS duration_seconds
        FROM workout_sessions s
        WHERE s.workout_date >= ? AND s.workout_date < ?
          AND EXISTS (SELECT 1 FROM workout_sets ws WHERE ws.session_id = s.id)
        """,
        (month_start, next_month),
    ).fetchone()["duration_seconds"]
    metrics = db.execute(
        """
        SELECT metric_date, body_weight
        FROM body_metrics
        WHERE metric_date >= ? AND metric_date < ? AND body_weight IS NOT NULL
        ORDER BY metric_date ASC
        """,
        (month_start, next_month),
    ).fetchall()
    weight_delta = 0.0
    if len(metrics) >= 2:
        weight_delta = float(metrics[-1]["body_weight"] or 0) - float(metrics[0]["body_weight"] or 0)
    pr_count = db.execute(
        "SELECT COUNT(id) AS count FROM pr_events WHERE workout_date >= ? AND workout_date < ?",
        (month_start, next_month),
    ).fetchone()["count"]
    balance = get_balance_score("monthly", base_date)
    return {
        "period": month_start[:7],
        "workout_days": int(totals["workout_days"] or 0),
        "set_count": int(totals["set_count"] or 0),
        "volume": float(totals["volume"] or 0),
        "duration_seconds": int(duration_seconds or 0),
        "top_exercise": top_exercise["name"] if top_exercise else "-",
        "top_exercise_sets": int(top_exercise["set_count"] or 0) if top_exercise else 0,
        "weight_delta": weight_delta,
        "balance_score": balance["score"],
        "missing": balance["missing"],
        "pr_count": int(pr_count or 0),
    }


def list_balance_warnings(scope: str = "weekly", date_text: str | None = None) -> list[str]:
    base_date = date_text or current_local_date()
    if scope == "weekly":
        start = week_start_for_date(base_date)
        end = shift_date(start, 6)
    else:
        start = normalize_month(base_date[:7])
        end = shift_month(start, 1)
    rows = get_db().execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date >= ? AND s.workout_date <= ?
        GROUP BY body_part
        """,
        (start, end),
    ).fetchall()
    counts = {part: 0 for part in body_part_options()}
    counts.update({row["body_part"]: int(row["set_count"]) for row in rows})
    total = sum(counts.values())
    warnings = []
    if total == 0:
        return ["이번 기간 운동 기록이 없습니다."]
    for part, count in counts.items():
        if part != "기타" and count == 0:
            warnings.append(f"{part} 운동이 비어 있습니다.")
    dominant = max(counts.items(), key=lambda item: item[1])
    if dominant[1] / total >= 0.5 and total >= 4:
        warnings.append(f"{dominant[0]} 비중이 높습니다. 다른 부위도 균형 있게 넣어보세요.")
    return warnings[:4]


def list_volume_warnings(date_text: str) -> list[str]:
    start_date = shift_date(date_text, -6)
    rows = get_db().execute(
        """
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COUNT(DISTINCT s.workout_date) AS workout_days
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date BETWEEN ? AND ?
        GROUP BY body_part
        ORDER BY set_count DESC
        """,
        (start_date, date_text),
    ).fetchall()
    warnings = []
    for row in rows:
        body_part = row["body_part"]
        if body_part != "유산소" and int(row["set_count"] or 0) >= 18:
            warnings.append(f"{body_part} 세트가 최근 7일 {row['set_count']}세트입니다.")
        if body_part != "유산소" and int(row["workout_days"] or 0) >= 3:
            warnings.append(f"{body_part}를 최근 7일 중 {row['workout_days']}일 운동했습니다.")
    return warnings[:3]


def get_balance_score(scope: str = "weekly", date_text: str | None = None) -> dict[str, object]:
    base_date = date_text or current_local_date()
    if scope == "weekly":
        start = week_start_for_date(base_date)
        end = shift_date(start, 6)
    else:
        start = normalize_month(base_date[:7])
        end = shift_date(shift_month(start, 1), -1)
    rows = get_db().execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date BETWEEN ? AND ?
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') != '기타'
        GROUP BY body_part
        """,
        (start, end),
    ).fetchall()
    target_parts = ["하체", "가슴", "등", "어깨", "팔", "유산소"]
    counts = {part: 0 for part in target_parts}
    counts.update({row["body_part"]: int(row["set_count"]) for row in rows if row["body_part"] in counts})
    filled = sum(1 for count in counts.values() if count > 0)
    score = round(filled / len(target_parts) * 100)
    missing = [part for part, count in counts.items() if count == 0]
    return {"score": score, "counts": counts, "missing": missing, "period": f"{start} ~ {end}"}


def list_recovery_recommendations(date_text: str) -> list[str]:
    start = shift_date(date_text, -2)
    rows = get_db().execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') NOT IN ('기타', '유산소')
        GROUP BY body_part
        ORDER BY set_count DESC
        """,
        (start, date_text),
    ).fetchall()
    if not rows:
        return ["최근 48시간 근력 기록이 적습니다. 원하는 부위를 진행해도 좋습니다."]
    overloaded = [row["body_part"] for row in rows if int(row["set_count"]) >= 4]
    rested = [part for part in ["하체", "가슴", "등", "어깨", "팔"] if part not in [row["body_part"] for row in rows]]
    messages = []
    if overloaded:
        messages.append(f"{', '.join(overloaded[:2])}는 최근 사용량이 많습니다.")
    if rested:
        messages.append(f"오늘 추천 부위: {', '.join(rested[:2])}")
    return messages[:2]


def build_period_insights(scope: str, date_text: str) -> list[str]:
    goals = get_goal_progress(date_text)
    if scope == "weekly":
        report = build_weekly_report(date_text)
        messages = [
            f"이번 주 운동일 목표는 {goals['weekly_workout_days']['percent']}% 달성했습니다.",
            f"식단 기록 목표는 {goals['weekly_meal_days']['percent']}% 달성했습니다.",
        ]
        if int(report["set_count"] or 0) == 0:
            messages.append("선택한 주에 운동 기록이 없습니다.")
        elif report["top_part"] != "-":
            messages.append(f"이번 주 가장 많이 한 부위는 {report['top_part']}입니다.")
        if float(report["cardio_minutes"] or 0) == 0:
            messages.append("이번 주 유산소 기록이 없습니다.")
        return messages[:4]

    report = build_monthly_report(date_text)
    messages = [
        f"월간 볼륨 목표는 {goals['monthly_volume']['percent']}% 달성했습니다.",
        f"월간 운동일 목표는 {goals['monthly_workout_days']['percent']}% 달성했습니다.",
        f"월간 유산소 목표는 {goals['monthly_cardio_minutes']['percent']}% 달성했습니다.",
    ]
    if int(report["pr_count"] or 0) > 0:
        messages.append(f"이번 달 신기록이 {report['pr_count']}개 있습니다.")
    if report["missing"]:
        messages.append(f"보강하면 좋은 부위: {', '.join(report['missing'][:3])}")
    return messages[:5]


def build_goal_insights(scope: str, date_text: str) -> list[str]:
    goals = get_goal_progress(date_text)
    keys = ["weekly_workout_days", "weekly_meal_days", "weekly_calories"] if scope == "weekly" else ["monthly_volume", "monthly_workout_days", "monthly_cardio_minutes"]
    messages = []
    for key in keys:
        goal = goals.get(key)
        if not goal or not goal["target"]:
            continue
        current = float(goal["current"] or 0)
        target = float(goal["target"] or 0)
        label = str(goal["label"])
        messages.append(f"{label} 목표 달성" if current >= target else f"{label} {target - current:.0f} 부족")
    return messages


def build_rpe_report(scope: str = "weekly", date_text: str | None = None) -> dict[str, object]:
    base_date = date_text or current_local_date()
    start = week_start_for_date(base_date) if scope == "weekly" else normalize_month(base_date[:7])
    end = shift_date(start, 6) if scope == "weekly" else shift_date(shift_month(start, 1), -1)
    row = get_db().execute(
        """
        SELECT AVG(rpe) AS avg_rpe, COUNT(rpe) AS rpe_count,
               SUM(CASE WHEN rpe >= 9 THEN 1 ELSE 0 END) AS hard_sets,
               SUM(CASE WHEN rpe <= 7 THEN 1 ELSE 0 END) AS easy_sets
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date BETWEEN ? AND ?
          AND ws.rpe IS NOT NULL
        """,
        (start, end),
    ).fetchone()
    avg_rpe = float(row["avg_rpe"] or 0)
    hard_sets = int(row["hard_sets"] or 0)
    easy_sets = int(row["easy_sets"] or 0)
    if not int(row["rpe_count"] or 0):
        message = "체감강도 기록이 아직 적습니다."
    elif hard_sets >= 5:
        message = "고강도 세트가 많아 다음 운동은 회복을 우선하세요."
    elif easy_sets >= 5 and avg_rpe <= 7.2:
        message = "여유 세트가 많아 주요 운동 증량을 고려해도 좋습니다."
    else:
        message = "강도 분포가 무난합니다."
    return {"avg_rpe": avg_rpe, "hard_sets": hard_sets, "easy_sets": easy_sets, "message": message}


def list_recovery_statuses(date_text: str) -> list[dict[str, object]]:
    start = shift_date(date_text, -2)
    rows = get_db().execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') IN ('하체', '등', '어깨', '가슴', '팔')
        GROUP BY body_part
        """,
        (start, date_text),
    ).fetchall()
    counts = {row["body_part"]: int(row["set_count"] or 0) for row in rows}
    statuses = []
    for part in ["하체", "등", "어깨", "가슴", "팔"]:
        count = counts.get(part, 0)
        state = "주의" if count >= 8 else "적정" if count >= 4 else "가능"
        statuses.append({"body_part": part, "set_count": count, "state": state})
    return statuses


def list_weekly_routine_recommendations(date_text: str) -> list[dict[str, object]]:
    balance = get_balance_score("weekly", date_text)
    missing = [part for part in balance["missing"] if part in ["하체", "등", "어깨", "가슴", "팔", "유산소"]]
    targets = (missing or ["하체", "등", "어깨"])[:3]
    recommendations = []
    for part in targets:
        items, equipment = list_preferred_exercises_for_body_part(part)
        reason = f"{part} 보강 추천"
        if equipment:
            reason = f"{reason} · {equipment}"
        recommendations.append({"body_part": part, "items": items, "reason": reason})
    return recommendations


def list_preferred_exercises_for_body_part(body_part: str, limit: int = 2) -> tuple[list[str], str]:
    rows = get_db().execute(
        """
        SELECT
            e.name,
            COALESCE(es.equipment, '') AS equipment,
            COALESCE(es.is_favorite, 0) AS is_favorite,
            COUNT(ws.id) AS set_count,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        WHERE COALESCE(NULLIF(ws.body_part, ''), '기타') = ?
        GROUP BY e.id, e.name, es.equipment, es.is_favorite
        ORDER BY is_favorite DESC, last_date DESC, set_count DESC, e.name
        LIMIT ?
        """,
        (body_part, limit),
    ).fetchall()
    items = [row["name"] for row in rows]
    for fallback in RECOMMENDED_EXERCISE_MAP.get(body_part, ["기록 운동"]):
        if len(items) >= limit:
            break
        if fallback not in items:
            items.append(fallback)
    equipment = next((row["equipment"] for row in rows if row["equipment"]), "")
    return items[:limit], equipment


def get_recovery_checkin(date_text: str) -> dict[str, object]:
    row = get_db().execute(
        "SELECT * FROM recovery_checkins WHERE checkin_date = ?",
        (date_text,),
    ).fetchone()
    if row:
        return dict(row)
    return {
        "checkin_date": date_text,
        "condition_score": 3,
        "sleep_score": 3,
        "soreness_score": 3,
        "fatigue_score": 3,
        "memo": "",
    }


def save_recovery_checkin(
    checkin_date: str,
    condition_score: int,
    sleep_score: int,
    soreness_score: int,
    fatigue_score: int,
    memo: str,
) -> None:
    def clamp_score(value: int) -> int:
        return max(1, min(5, int(value or 3)))

    get_db().execute(
        """
        INSERT INTO recovery_checkins (
            checkin_date, condition_score, sleep_score, soreness_score, fatigue_score, memo, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(checkin_date) DO UPDATE SET
            condition_score = excluded.condition_score,
            sleep_score = excluded.sleep_score,
            soreness_score = excluded.soreness_score,
            fatigue_score = excluded.fatigue_score,
            memo = excluded.memo,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            checkin_date,
            clamp_score(condition_score),
            clamp_score(sleep_score),
            clamp_score(soreness_score),
            clamp_score(fatigue_score),
            memo[:200],
        ),
    )
    get_db().commit()


def save_rest_day(date_text: str, reason: str, memo: str = "") -> None:
    get_db().execute(
        """
        INSERT INTO recovery_checkins (
            checkin_date, condition_score, sleep_score, soreness_score, fatigue_score,
            is_rest_day, rest_reason, memo, updated_at
        )
        VALUES (?, 3, 3, 3, 3, 1, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(checkin_date) DO UPDATE SET
            is_rest_day = 1,
            rest_reason = excluded.rest_reason,
            memo = excluded.memo,
            updated_at = CURRENT_TIMESTAMP
        """,
        (date_text, reason.strip()[:40] or "휴식", memo.strip()[:120]),
    )
    get_db().commit()


def list_daily_coaching(date_text: str) -> list[str]:
    checkin = get_recovery_checkin(date_text)
    condition = int(checkin["condition_score"] or 3)
    sleep = int(checkin["sleep_score"] or 3)
    soreness = int(checkin["soreness_score"] or 3)
    fatigue = int(checkin["fatigue_score"] or 3)
    messages = []
    if condition >= 4 and sleep >= 4 and fatigue <= 2:
        messages.append("컨디션이 좋습니다. 메인 운동은 지난 기록보다 1회 또는 2.5kg 도전을 고려하세요.")
    elif sleep <= 2 or fatigue >= 4:
        messages.append("회복 점수가 낮습니다. 고중량보다 가벼운 볼륨이나 유산소 위주가 낫습니다.")
    else:
        messages.append("평균 컨디션입니다. 지난 기록과 같은 중량에서 안정적으로 세트를 채우세요.")
    if soreness >= 4:
        messages.append("근육통이 높습니다. 같은 부위 반복보다 회복된 부위를 선택하세요.")
    messages.extend(list_recovery_recommendations(date_text))
    return messages[:4]


def build_readiness_profile(date_text: str) -> dict[str, object]:
    checkin = get_recovery_checkin(date_text)
    condition = int(checkin["condition_score"] or 3)
    sleep = int(checkin["sleep_score"] or 3)
    soreness = int(checkin["soreness_score"] or 3)
    fatigue = int(checkin["fatigue_score"] or 3)
    score = condition + sleep + (6 - soreness) + (6 - fatigue)
    percent = round(score / 20 * 100)
    if percent >= 75:
        label = "공격 가능"
        guide = "메인 운동은 지난 기록보다 1회 또는 2.5kg 상향을 시도하세요."
        tone = "high"
    elif percent >= 55:
        label = "표준 진행"
        guide = "지난 기록과 같은 중량에서 세트 완성도를 우선하세요."
        tone = "normal"
    else:
        label = "회복 우선"
        guide = "고중량보다 낮은 강도, 보조 운동, 유산소 위주로 조정하세요."
        tone = "low"
    return {
        "score": score,
        "percent": percent,
        "label": label,
        "guide": guide,
        "tone": tone,
    }


def build_period_highlights(scope: str, date_text: str) -> list[dict[str, str]]:
    if scope == "weekly":
        start = week_start_for_date(date_text)
        end = shift_date(start, 6)
    else:
        start = normalize_month(date_text[:7])
        end = shift_date(shift_month(start, 1), -1)
    db = get_db()
    top_exercise = db.execute(
        """
        SELECT e.name, COUNT(ws.id) AS set_count,
               COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.workout_date BETWEEN ? AND ?
        GROUP BY e.name
        ORDER BY set_count DESC, volume DESC, e.name
        LIMIT 1
        """,
        (start, end),
    ).fetchone()
    best_pr = db.execute(
        """
        SELECT workout_date, exercise_name, record_type, record_value
        FROM pr_events
        WHERE workout_date BETWEEN ? AND ?
        ORDER BY record_value DESC, workout_date DESC
        LIMIT 1
        """,
        (start, end),
    ).fetchone()
    avg_recovery = db.execute(
        """
        SELECT AVG(condition_score) AS condition_score, AVG(sleep_score) AS sleep_score,
               AVG(soreness_score) AS soreness_score, AVG(fatigue_score) AS fatigue_score
        FROM recovery_checkins
        WHERE checkin_date BETWEEN ? AND ?
        """,
        (start, end),
    ).fetchone()
    highlights: list[dict[str, str]] = []
    if top_exercise:
        highlights.append(
            {
                "label": "최다 운동",
                "value": top_exercise["name"],
                "note": f"{int(top_exercise['set_count'] or 0)}세트 · {float(top_exercise['volume'] or 0):.0f}kg",
            }
        )
    if best_pr:
        highlights.append(
            {
                "label": "대표 PR",
                "value": best_pr["exercise_name"],
                "note": f"{best_pr['record_type']} {float(best_pr['record_value'] or 0):.0f} · {best_pr['workout_date']}",
            }
        )
    if avg_recovery and avg_recovery["condition_score"]:
        readiness = (
            float(avg_recovery["condition_score"] or 0)
            + float(avg_recovery["sleep_score"] or 0)
            + (6 - float(avg_recovery["fatigue_score"] or 3))
            + (6 - float(avg_recovery["soreness_score"] or 3))
        ) / 4
        highlights.append({"label": "회복 평균", "value": f"{readiness:.1f}/5", "note": "컨디션·수면·피로·근육통 기준"})
    if not highlights:
        highlights.append({"label": "리포트", "value": "기록 대기", "note": "운동이나 회복 기록을 입력하면 표시됩니다."})
    return highlights[:3]


def get_data_counts() -> dict[str, int]:
    return build_data_counts(get_db())


def get_backup_status() -> dict[str, str]:
    return build_backup_status(BASE_DIR)


def get_sample_data_counts() -> dict[str, int]:
    return build_sample_data_counts(get_db())


def get_app_health_status() -> list[dict[str, str]]:
    return build_app_health_status(DATABASE, get_data_counts(), get_sample_data_counts(), get_backup_status())


def delete_sample_data() -> None:
    db = get_db()
    db.execute("DELETE FROM pr_events WHERE exercise_name LIKE '샘플%' OR exercise_name LIKE 'PR확인%'")
    db.execute(
        """
        DELETE FROM workout_sets
        WHERE exercise_id IN (
            SELECT id FROM exercises WHERE name LIKE '샘플%' OR name LIKE 'PR확인%'
        )
        """
    )
    db.execute("DELETE FROM exercises WHERE name LIKE '샘플%' OR name LIKE 'PR확인%'")
    db.execute("DELETE FROM meal_entries WHERE food_name LIKE '샘플%'")
    delete_empty_workout_sessions()
    db.commit()


def create_may_sample_data() -> None:
    delete_sample_data()
    db = get_db()
    body_part_exercises = {
        "하체": ["샘플하체 스쿼트", "샘플하체 레그프레스", "샘플하체 런지", "샘플하체 레그컬"],
        "가슴": ["샘플가슴 벤치프레스", "샘플가슴 인클라인프레스", "샘플가슴 덤벨프레스", "샘플가슴 케이블플라이"],
        "등": ["샘플등 랫풀다운", "샘플등 바벨로우", "샘플등 시티드로우", "샘플등 풀업"],
        "어깨": ["샘플어깨 숄더프레스", "샘플어깨 사이드레터럴", "샘플어깨 리어델트", "샘플어깨 업라이트로우"],
        "팔": ["샘플팔 바벨컬", "샘플팔 해머컬", "샘플팔 케이블푸시다운", "샘플팔 딥스"],
    }
    parts = list(body_part_exercises.keys())
    equipment_by_part = {
        "하체": "바벨",
        "가슴": "바벨",
        "등": "머신",
        "어깨": "덤벨",
        "팔": "케이블",
    }
    meal_plans = [
        [
            ("아침", "샘플현미밥", 1, 180, 290),
            ("아침", "샘플계란", 2, 100, 150),
            ("점심", "샘플닭가슴살도시락", 1, 320, 520),
            ("점심", "샘플바나나", 1, 120, 105),
            ("저녁", "샘플연어샐러드", 1, 260, 430),
            ("간식", "샘플그릭요거트", 1, 150, 160),
        ],
        [
            ("아침", "샘플오트밀", 1, 80, 300),
            ("아침", "샘플프로틴쉐이크", 1, 300, 180),
            ("점심", "샘플소고기덮밥", 1, 380, 650),
            ("점심", "샘플방울토마토", 1, 120, 35),
            ("저녁", "샘플닭가슴살샐러드", 1, 300, 390),
            ("간식", "샘플아몬드", 1, 25, 145),
        ],
        [
            ("아침", "샘플통밀토스트", 2, 120, 310),
            ("아침", "샘플우유", 1, 200, 130),
            ("점심", "샘플돼지고기김치볶음밥", 1, 360, 680),
            ("점심", "샘플두부", 1, 150, 120),
            ("저녁", "샘플고구마닭가슴살", 1, 330, 480),
            ("간식", "샘플사과", 1, 180, 95),
        ],
        [
            ("아침", "샘플김밥", 1, 250, 420),
            ("아침", "샘플삶은계란", 2, 100, 150),
            ("점심", "샘플신라면건면", 1, 97, 350),
            ("점심", "샘플닭가슴살만두", 1, 180, 320),
            ("저녁", "샘플불고기정식", 1, 420, 720),
            ("간식", "샘플단백질바", 1, 55, 210),
        ],
        [
            ("아침", "샘플요거트볼", 1, 260, 360),
            ("아침", "샘플블루베리", 1, 80, 45),
            ("점심", "샘플참치비빔밥", 1, 380, 610),
            ("점심", "샘플미역국", 1, 250, 80),
            ("저녁", "샘플닭다리살구이", 1, 300, 540),
            ("간식", "샘플프로틴음료", 1, 250, 165),
        ],
    ]
    for day in range(1, 26):
        workout_date = f"2026-05-{day:02d}"
        part = parts[(day - 1) % len(parts)]
        session = get_or_create_session(workout_date)
        db.execute(
            "UPDATE workout_sessions SET completed = 1, duration_seconds = ? WHERE id = ?",
            (90 * 60, session["id"]),
        )
        sort_order = 1
        for exercise_index, exercise_name in enumerate(body_part_exercises[part]):
            exercise_id = get_or_create_exercise(exercise_name)
            save_exercise_equipment(exercise_name, equipment_by_part[part])
            base_weight = 30 + (day % 5) * 2.5 + exercise_index * 5
            for set_index in range(3):
                reps = 12 - set_index
                db.execute(
                    """
                    INSERT INTO workout_sets (
                        session_id, exercise_id, weight, reps, memo, sort_order,
                        body_part, set_type, rpe, equipment
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session["id"],
                        exercise_id,
                        base_weight + set_index * 2.5,
                        reps,
                        "5월 샘플",
                        sort_order,
                        part,
                        "본세트",
                        7 + (set_index * 0.5),
                        equipment_by_part[part],
                    ),
                )
                sort_order += 1
        cardio_id = get_or_create_exercise("샘플런닝 30분")
        calories = estimate_exercise_calories("유산소", 5.0, 5.5, 30, workout_date)
        db.execute(
            """
            INSERT INTO workout_sets (
                session_id, exercise_id, cardio_incline, cardio_speed, cardio_minutes,
                estimated_calories, memo, sort_order, body_part, set_type, rpe, equipment
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session["id"], cardio_id, 5.0, 5.5, 30, calories, "5월 샘플", sort_order, "유산소", "유산소", 6, "런닝머신"),
        )
        for meal_type, food_name, quantity, grams, meal_calories in meal_plans[(day - 1) % len(meal_plans)]:
            db.execute(
                """
                INSERT INTO meal_entries (
                    meal_date, meal_type, food_name, quantity, grams, calories, memo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (workout_date, meal_type, food_name, quantity, grams, meal_calories, "5월 샘플"),
            )
    db.commit()


def delete_empty_workout_sessions() -> None:
    get_db().execute(
        """
        DELETE FROM workout_sessions
        WHERE COALESCE(completed, 0) = 0
          AND id NOT IN (SELECT DISTINCT session_id FROM workout_sets)
          AND workout_date NOT IN (SELECT DISTINCT meal_date FROM meal_entries)
        """
    )


def delete_all_data() -> None:
    db = get_db()
    backup_dir = BASE_DIR / "instance" / "delete_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"before-delete-all-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    backup_path.write_text(json.dumps(export_all_data(), ensure_ascii=False, indent=2), encoding="utf-8")
    for table in [
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
    ]:
        db.execute(f"DELETE FROM {table}")
    db.commit()


def delete_internal_test_data() -> None:
    db = get_db()
    db.execute("DELETE FROM exercise_settings WHERE exercise_name LIKE '__%점검__'")
    db.execute("DELETE FROM workout_plan_items WHERE exercise_name LIKE '__%점검%'")


def export_all_data() -> dict[str, object]:
    return export_all_data_from_db(get_db())


def export_workout_csv() -> str:
    return export_workout_csv_from_db(get_db())


def export_meal_csv() -> str:
    return export_meal_csv_from_db(get_db())


def import_all_data(payload: dict[str, object]) -> None:
    tables = payload.get("tables", {})
    if not isinstance(tables, dict):
        return
    ordered_tables = [
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
    db = get_db()
    backup_dir = BASE_DIR / "instance" / "restore_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"before-import-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    backup_path.write_text(json.dumps(export_all_data(), ensure_ascii=False, indent=2), encoding="utf-8")
    for table in reversed(ordered_tables):
        db.execute(f"DELETE FROM {table}")
    for table in ordered_tables:
        rows = tables.get(table, [])
        if not isinstance(rows, list):
            continue
        columns = [row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()]
        for row in rows:
            if not isinstance(row, dict):
                continue
            insert_columns = [column for column in columns if column in row]
            if not insert_columns:
                continue
            placeholders = ", ".join(["?"] * len(insert_columns))
            column_sql = ", ".join(insert_columns)
            db.execute(
                f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
                tuple(row[column] for column in insert_columns),
            )
    db.commit()


def body_part_options() -> list[str]:
    return BODY_PARTS


def body_part_class(body_part: str | None) -> str:
    return BODY_PART_CLASSES.get((body_part or "기타").strip(), "body-part-other")


def meal_type_class(meal_type: str | None) -> str:
    return MEAL_TYPE_CLASSES.get((meal_type or "기타").strip(), "meal-type-other")


def list_recent_sessions(limit: int = 10) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT
            s.id,
            s.workout_date,
            COALESCE(s.duration_seconds, 0) AS duration_seconds,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories
        FROM workout_sessions s
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        GROUP BY s.id, s.duration_seconds
        HAVING COUNT(ws.id) > 0 OR COALESCE(s.completed, 0) = 1
        ORDER BY s.workout_date DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def list_meals_for_date(meal_date: str) -> list[sqlite3.Row]:
    return list_meals_for_date_from_db(get_db(), meal_date)


def grouped_meals_for_date(meal_date: str) -> list[dict[str, object]]:
    return grouped_meals_for_date_from_db(get_db(), meal_date)


def list_weekly_meal_days(week_start: str) -> list[dict[str, object]]:
    return list_weekly_meal_days_from_db(get_db(), week_start, shift_date, meal_day_label)


def build_weekly_meal_summary(week_start: str) -> dict[str, object]:
    return build_weekly_meal_summary_from_db(get_db(), week_start, shift_date)


def build_monthly_meal_summary(month_start: str) -> dict[str, object]:
    return build_monthly_meal_summary_from_db(get_db(), month_start, normalize_month, shift_month)


def list_monthly_meal_weeks(month_start: str) -> list[dict[str, object]]:
    return list_monthly_meal_weeks_from_db(get_db(), month_start, normalize_month, shift_month)


def get_day_summary(day: str) -> dict[str, float]:
    db = get_db()
    workout = db.execute(
        """
        SELECT
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            COALESCE(MAX(s.duration_seconds), 0) AS duration_seconds
        FROM workout_sessions s
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date = ?
        """,
        (day,),
    ).fetchone()
    meal = db.execute(
        """
        SELECT
            COUNT(id) AS meal_count,
            COALESCE(SUM(quantity), 0) AS amount,
            COALESCE(SUM(grams), 0) AS grams,
            COALESCE(SUM(calories), 0) AS calories
        FROM meal_entries
        WHERE meal_date = ?
        """,
        (day,),
    ).fetchone()
    return {
        "set_count": workout["set_count"],
        "rep_count": workout["rep_count"],
        "volume": workout["volume"],
        "cardio_minutes": workout["cardio_minutes"],
        "exercise_calories": workout["exercise_calories"],
        "duration_seconds": workout["duration_seconds"],
        "meal_count": meal["meal_count"],
        "amount": meal["amount"],
        "grams": meal["grams"],
        "calories": meal["calories"],
    }


def list_daily_summary(
    limit: int | None = None,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[sqlite3.Row]:
    where_clause = ""
    limit_clause = ""
    params: list[object] = []
    if start_date and end_date:
        where_clause = "WHERE p.period BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    elif days is not None:
        start_date = shift_date(current_local_date(), -(max(1, days) - 1))
        where_clause = "WHERE p.period >= ?"
        params.append(start_date)
    elif limit is not None:
        limit_clause = "LIMIT ?"
        params.append(limit)
    return get_db().execute(
        f"""
        WITH workout AS (
            SELECT
                s.workout_date AS period,
                COUNT(ws.id) AS set_count,
                COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
                COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
                COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
                COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
                COALESCE(MAX(s.duration_seconds), 0) AS duration_seconds
            FROM workout_sessions s
            LEFT JOIN workout_sets ws ON ws.session_id = s.id
            GROUP BY s.workout_date
            HAVING COUNT(ws.id) > 0 OR COALESCE(MAX(s.completed), 0) = 1
        ),
        meal AS (
            SELECT
                meal_date AS period,
                COUNT(id) AS meal_count,
                COALESCE(SUM(quantity), 0) AS amount,
                COALESCE(SUM(grams), 0) AS grams,
                COALESCE(SUM(calories), 0) AS calories
            FROM meal_entries
            GROUP BY meal_date
        ),
        periods AS (
            SELECT period FROM workout
            UNION
            SELECT period FROM meal
        )
        SELECT
            p.period,
            COALESCE(w.set_count, 0) AS set_count,
            COALESCE(w.rep_count, 0) AS rep_count,
            COALESCE(w.volume, 0) AS volume,
            COALESCE(w.cardio_minutes, 0) AS cardio_minutes,
            COALESCE(w.exercise_calories, 0) AS exercise_calories,
            COALESCE(w.duration_seconds, 0) AS duration_seconds,
            COALESCE(m.meal_count, 0) AS meal_count,
            COALESCE(m.amount, 0) AS amount,
            COALESCE(m.grams, 0) AS grams,
            COALESCE(m.calories, 0) AS calories
        FROM periods p
        LEFT JOIN workout w ON w.period = p.period
        LEFT JOIN meal m ON m.period = p.period
        {where_clause}
        ORDER BY p.period DESC
        {limit_clause}
        """,
        params,
    ).fetchall()


def list_weekly_summary(limit: int = 12, month_start: str | None = None) -> list[sqlite3.Row]:
    workout_where = ""
    meal_where = ""
    params: list[object] = []
    if month_start:
        normalized_month = normalize_month(month_start)
        next_month = shift_month(normalized_month, 1)
        workout_where = "WHERE s.workout_date >= ? AND s.workout_date < ?"
        meal_where = "WHERE meal_date >= ? AND meal_date < ?"
        params.extend([normalized_month, next_month, normalized_month, next_month, normalized_month, next_month])
    params.append(limit)
    return get_db().execute(
        f"""
        WITH workout AS (
            SELECT
                strftime('%Y-%m', s.workout_date) AS month_key,
                CAST(strftime('%m', s.workout_date) AS INTEGER) AS month_number,
                ((CAST(strftime('%d', s.workout_date) AS INTEGER) - 1) / 7) + 1 AS week_of_month,
                COUNT(DISTINCT CASE WHEN ws.id IS NOT NULL THEN s.workout_date END) AS workout_days,
                COUNT(ws.id) AS set_count,
                COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
                COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
                COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
                COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories
            FROM workout_sessions s
            LEFT JOIN workout_sets ws ON ws.session_id = s.id
            {workout_where}
            GROUP BY month_key, week_of_month
            HAVING COUNT(ws.id) > 0
        ),
        workout_time AS (
            SELECT
                strftime('%Y-%m', workout_date) AS month_key,
                CAST(strftime('%m', workout_date) AS INTEGER) AS month_number,
                ((CAST(strftime('%d', workout_date) AS INTEGER) - 1) / 7) + 1 AS week_of_month,
                COALESCE(SUM(duration_seconds), 0) AS duration_seconds
            FROM workout_sessions s
            {workout_where.replace("s.workout_date", "workout_date")}
              {"AND" if workout_where else "WHERE"} EXISTS (SELECT 1 FROM workout_sets ws WHERE ws.session_id = s.id)
            GROUP BY month_key, week_of_month
        ),
        meal AS (
            SELECT
                strftime('%Y-%m', meal_date) AS month_key,
                CAST(strftime('%m', meal_date) AS INTEGER) AS month_number,
                ((CAST(strftime('%d', meal_date) AS INTEGER) - 1) / 7) + 1 AS week_of_month,
                COUNT(DISTINCT meal_date) AS meal_days,
                COUNT(id) AS meal_count,
                COALESCE(SUM(quantity), 0) AS amount,
                COALESCE(SUM(grams), 0) AS grams,
                COALESCE(SUM(calories), 0) AS calories
            FROM meal_entries
            {meal_where}
            GROUP BY month_key, week_of_month
        ),
        periods AS (
            SELECT month_key, month_number, week_of_month FROM workout
            UNION
            SELECT month_key, month_number, week_of_month FROM meal
        )
        SELECT
            p.month_key || '-' || p.week_of_month AS period_key,
            p.month_number || '월 ' || p.week_of_month || '주차' AS period,
            COALESCE(w.workout_days, 0) AS workout_days,
            COALESCE(w.set_count, 0) AS set_count,
            COALESCE(w.rep_count, 0) AS rep_count,
            COALESCE(w.volume, 0) AS volume,
            COALESCE(w.cardio_minutes, 0) AS cardio_minutes,
            COALESCE(w.exercise_calories, 0) AS exercise_calories,
            COALESCE(wt.duration_seconds, 0) AS duration_seconds,
            COALESCE(m.meal_days, 0) AS meal_days,
            COALESCE(m.meal_count, 0) AS meal_count,
            COALESCE(m.amount, 0) AS amount,
            COALESCE(m.grams, 0) AS grams,
            COALESCE(m.calories, 0) AS calories
        FROM periods p
        LEFT JOIN workout w
            ON w.month_key = p.month_key AND w.week_of_month = p.week_of_month
        LEFT JOIN workout_time wt
            ON wt.month_key = p.month_key AND wt.week_of_month = p.week_of_month
        LEFT JOIN meal m
            ON m.month_key = p.month_key AND m.week_of_month = p.week_of_month
        ORDER BY p.month_key DESC, p.week_of_month DESC
        LIMIT ?
        """,
        params,
    ).fetchall()


def build_period_chart(rows: list[sqlite3.Row]) -> list[dict[str, float | int | str]]:
    return build_period_chart_from_rows(rows)


def build_daily_chart(rows: list[sqlite3.Row]) -> list[dict[str, float | int | str]]:
    return build_daily_chart_from_rows(rows)


def build_yearly_report(year: str) -> dict[str, object]:
    return build_yearly_report_from_db(get_db(), year)


def list_yearly_month_rows(year: str) -> list[sqlite3.Row]:
    return list_yearly_month_rows_from_db(get_db(), year)


def list_yearly_body_part_summary(year: str) -> list[sqlite3.Row]:
    return list_yearly_body_part_summary_from_db(get_db(), year)


def list_yearly_top_exercises(year: str, limit: int = 10) -> list[sqlite3.Row]:
    return list_yearly_top_exercises_from_db(get_db(), year, limit)


def export_yearly_payload(year: str) -> dict[str, object]:
    return {
        "year": year,
        "report": build_yearly_report(year),
        "months": [dict(row) for row in list_yearly_month_rows(year)],
        "body_parts": [dict(row) for row in list_yearly_body_part_summary(year)],
        "top_exercises": [dict(row) for row in list_yearly_top_exercises(year, limit=20)],
    }


def rows_to_csv(rows: list[sqlite3.Row], headers: list[str]) -> str:
    lines = [",".join(headers)]
    for row in rows:
        values = []
        for header in headers:
            value = row[header]
            text = "" if value is None else str(value)
            values.append('"' + text.replace('"', '""') + '"')
        lines.append(",".join(values))
    return "\ufeff" + "\n".join(lines)


def export_yearly_workout_csv(year: str) -> str:
    headers = [
        "workout_date",
        "exercise_name",
        "body_part",
        "equipment",
        "set_type",
        "weight",
        "reps",
        "cardio_incline",
        "cardio_speed",
        "cardio_minutes",
        "estimated_calories",
        "rpe",
        "memo",
    ]
    return rows_to_csv(export_yearly_workout_rows(get_db(), year), headers)


def export_yearly_meal_csv(year: str) -> str:
    headers = ["meal_date", "meal_type", "food_name", "quantity", "grams", "calories", "memo"]
    return rows_to_csv(export_yearly_meal_rows(get_db(), year), headers)


def paged_rows(select_sql: str, count_sql: str, params: list[object], page: int, per_page: int) -> tuple[list[sqlite3.Row], object]:
    total = int(get_db().execute(count_sql, params).fetchone()[0] or 0)
    pagination = build_pagination(total, page, per_page)
    rows = get_db().execute(f"{select_sql} LIMIT ? OFFSET ?", (*params, pagination.per_page, pagination.offset)).fetchall()
    return rows, pagination


def allowed_sort(value: str, options: dict[str, str], default: str) -> str:
    return value if value in options else default


def paged_search_workout_records_filtered(
    query: str = "",
    body_part: str = "",
    equipment: str = "",
    location_id: int | None = None,
    start_date: str = "",
    end_date: str = "",
    sort: str = "newest",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object, str]:
    sort_options = {
        "newest": "s.workout_date DESC, ws.sort_order ASC, ws.id ASC",
        "oldest": "s.workout_date ASC, ws.sort_order ASC, ws.id ASC",
        "weight": "COALESCE(ws.weight, 0) DESC, s.workout_date DESC, ws.id DESC",
        "volume": "(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)) DESC, s.workout_date DESC, ws.id DESC",
    }
    selected_sort = allowed_sort(sort, sort_options, "newest")
    where = []
    params: list[object] = []
    if query:
        where.append("(e.name LIKE ? OR ws.memo LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    if body_part:
        where.append("COALESCE(NULLIF(ws.body_part, ''), '기타') = ?")
        params.append(body_part)
    if equipment:
        where.append("COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') = ?")
        params.append(equipment)
    if location_id:
        where.append("s.location_id = ?")
        params.append(location_id)
    if start_date:
        where.append("s.workout_date >= ?")
        params.append(start_date)
    if end_date:
        where.append("s.workout_date <= ?")
        params.append(end_date)
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    from_sql = f"""
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        LEFT JOIN workout_locations wl ON wl.id = s.location_id
        {where_sql}
    """
    rows, pagination = paged_rows(
        f"""
        SELECT
            s.workout_date,
            wl.name AS location_name,
            e.name AS exercise_name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') AS equipment,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.estimated_calories,
            ws.rpe,
            ws.memo
        {from_sql}
        ORDER BY {sort_options[selected_sort]}
        """,
        f"SELECT COUNT(*) {from_sql}",
        params,
        page,
        per_page,
    )
    return rows, pagination, selected_sort


def paged_search_workout_records(
    query: str,
    sort: str = "newest",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object, str]:
    return paged_search_workout_records_filtered(
        query=query,
        sort=sort,
        page=page,
        per_page=per_page,
    )


def paged_exercise_summary(sort: str = "sets", page: int = 1, per_page: int = 20) -> tuple[list[sqlite3.Row], object, str]:
    sort_options = {
        "sets": "set_count DESC, rep_count DESC, e.name",
        "volume": "volume DESC, set_count DESC, e.name",
        "recent": "last_date DESC, set_count DESC, e.name",
        "name": "e.name ASC",
    }
    selected_sort = allowed_sort(sort, sort_options, "sets")
    grouped_sql = """
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        GROUP BY e.id, e.name, COALESCE(NULLIF(ws.body_part, ''), '기타')
    """
    rows, pagination = paged_rows(
        f"""
        SELECT
            e.id,
            e.name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            MAX(s.workout_date) AS last_date
        {grouped_sql}
        ORDER BY {sort_options[selected_sort]}
        """,
        f"SELECT COUNT(*) FROM (SELECT e.id, COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part {grouped_sql})",
        [],
        page,
        per_page,
    )
    return rows, pagination, selected_sort


def paged_exercise_pr_summary(
    body_part: str = "",
    query: str = "",
    sort: str = "weight",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object, str]:
    sort_options = {
        "1rm": "estimated_1rm DESC, best_weight DESC, last_date DESC, e.name",
        "weight": "best_weight DESC, best_volume DESC, last_date DESC, e.name",
        "volume": "best_volume DESC, best_weight DESC, last_date DESC, e.name",
        "recent": "last_date DESC, best_weight DESC, e.name",
    }
    selected_sort = allowed_sort(sort, sort_options, "weight")
    filters = ["ws.weight IS NOT NULL", "ws.reps IS NOT NULL", "COALESCE(NULLIF(ws.body_part, ''), '기타') != '유산소'"]
    params: list[object] = []
    if body_part:
        filters.append("COALESCE(NULLIF(ws.body_part, ''), '기타') = ?")
        params.append(body_part)
    if query:
        filters.append("e.name LIKE ?")
        params.append(f"%{query}%")
    where_clause = " AND ".join(filters)
    from_sql = f"""
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE {where_clause}
        GROUP BY e.id, e.name
    """
    rows, pagination = paged_rows(
        f"""
        SELECT
            e.id,
            e.name,
            COALESCE(NULLIF(MAX(ws.body_part), ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COUNT(DISTINCT s.workout_date) AS workout_days,
            MAX(s.workout_date) AS last_date,
            COALESCE(MAX(ws.weight), 0) AS best_weight,
            COALESCE(MAX(ws.reps), 0) AS best_reps,
            COALESCE(MAX(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS best_volume,
            COALESCE(MAX(ws.weight * (1 + ws.reps / 30.0)), 0) AS estimated_1rm
        {from_sql}
        ORDER BY {sort_options[selected_sort]}
        """,
        f"SELECT COUNT(*) FROM (SELECT e.id {from_sql})",
        params,
        page,
        per_page,
    )
    return rows, pagination, selected_sort


def list_exercise_summary_by_body_part() -> dict[str, list[sqlite3.Row]]:
    rows = get_db().execute(
        """
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.name,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        GROUP BY body_part, e.name
        ORDER BY body_part, last_date DESC, set_count DESC, e.name
        """
    ).fetchall()
    grouped = {part: [] for part in body_part_options()}
    for row in rows:
        grouped.setdefault(row["body_part"] or "기타", []).append(row)
    return grouped


def equipment_scope_clause(scope: str) -> tuple[str, tuple[str, ...]]:
    today = current_local_date()
    if scope == "week":
        return "AND s.workout_date >= ? AND s.workout_date <= ?", (week_start_for_date(today), today)
    if scope == "month":
        month_start = f"{today[:7]}-01"
        return "AND s.workout_date >= ? AND s.workout_date < ?", (month_start, shift_month(month_start, 1))
    return "", ()


def paged_equipment_summary(
    scope: str = "month",
    sort: str = "sets",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object, str]:
    sort_options = {
        "sets": "set_count DESC, volume DESC, last_date DESC, equipment",
        "recent": "last_date DESC, set_count DESC, equipment",
        "days": "workout_days DESC, set_count DESC, equipment",
        "volume": "volume DESC, set_count DESC, equipment",
    }
    selected_sort = allowed_sort(sort, sort_options, "sets")
    where_sql, params_tuple = equipment_scope_clause(scope)
    params = list(params_tuple)
    from_sql = f"""
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        WHERE 1 = 1 {where_sql}
        GROUP BY COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정')
    """
    rows, pagination = paged_rows(
        f"""
        SELECT
            COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') AS equipment,
            COUNT(ws.id) AS set_count,
            COUNT(DISTINCT s.workout_date) AS workout_days,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            MAX(s.workout_date) AS last_date
        {from_sql}
        ORDER BY {sort_options[selected_sort]}
        """,
        f"SELECT COUNT(*) FROM (SELECT COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') AS equipment {from_sql})",
        params,
        page,
        per_page,
    )
    return rows, pagination, selected_sort


def paged_equipment_detail(
    equipment: str,
    scope: str = "month",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object]:
    where_sql, params_tuple = equipment_scope_clause(scope)
    params: list[object] = [equipment, *params_tuple]
    from_sql = f"""
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        WHERE COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') = ?
          {where_sql}
        GROUP BY COALESCE(NULLIF(ws.body_part, ''), '기타'), e.name
    """
    return paged_rows(
        f"""
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.name AS exercise_name,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            MAX(ws.weight) AS best_weight,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            MAX(s.workout_date) AS last_date
        {from_sql}
        ORDER BY set_count DESC, volume DESC, last_date DESC, exercise_name
        """,
        f"SELECT COUNT(*) FROM (SELECT e.name {from_sql})",
        params,
        page,
        per_page,
    )


def paged_equipment_daily(
    equipment: str,
    scope: str = "month",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object]:
    where_sql, params_tuple = equipment_scope_clause(scope)
    params: list[object] = [equipment, *params_tuple]
    from_sql = f"""
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        WHERE COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') = ?
          {where_sql}
        GROUP BY s.workout_date
    """
    return paged_rows(
        f"""
        SELECT
            s.workout_date,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes
        {from_sql}
        ORDER BY s.workout_date DESC
        """,
        f"SELECT COUNT(*) FROM (SELECT s.workout_date {from_sql})",
        params,
        page,
        per_page,
    )


def get_exercise_profile(exercise_id: int | None) -> dict[str, object] | None:
    if not exercise_id:
        return None
    row = get_db().execute(
        """
        SELECT
            e.name,
            COALESCE(NULLIF(MAX(ws.body_part), ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COUNT(DISTINCT s.workout_date) AS workout_days,
            MAX(s.workout_date) AS last_date,
            COALESCE(MAX(ws.weight), 0) AS best_weight,
            COALESCE(MAX(ws.reps), 0) AS best_reps,
            COALESCE(MAX(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS best_volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories
        FROM exercises e
        LEFT JOIN workout_sets ws ON ws.exercise_id = e.id
        LEFT JOIN workout_sessions s ON s.id = ws.session_id
        WHERE e.id = ?
        GROUP BY e.id, e.name
        """,
        (exercise_id,),
    ).fetchone()
    return dict(row) if row else None


def build_exercise_next_plan(exercise_id: int | None) -> list[str]:
    if not exercise_id:
        return []
    row = get_db().execute(
        """
        SELECT
            e.name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            s.workout_date
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.exercise_id = ?
        ORDER BY s.workout_date DESC, ws.sort_order DESC, ws.id DESC
        LIMIT 1
        """,
        (exercise_id,),
    ).fetchone()
    if not row:
        return ["아직 기록이 적어서 다음 목표를 만들 수 없습니다. 먼저 1회 기록을 남겨주세요."]

    body_part = row["body_part"] or "기타"
    if body_part == "유산소":
        minutes = float(row["cardio_minutes"] or 0)
        speed = float(row["cardio_speed"] or 0)
        incline = float(row["cardio_incline"] or 0)
        suggestions = []
        if minutes:
            suggestions.append(f"다음 유산소는 {minutes + 2:.0f}분을 1차 목표로 잡아보세요.")
        if speed:
            suggestions.append(f"컨디션이 좋으면 속도 {speed + 0.1:.1f}까지 올려보세요.")
        if incline:
            suggestions.append(f"인클라인은 {incline:.1f}을 유지하고 시간을 먼저 늘리는 편이 안정적입니다.")
        return suggestions or ["다음 유산소는 시간, 속도, 인클라인 중 하나만 올려서 기록해보세요."]

    weight = float(row["weight"] or 0)
    reps = int(row["reps"] or 0)
    if weight <= 0 or reps <= 0:
        return ["최근 세트에 중량/횟수가 비어 있습니다. 다음 기록부터 중량과 횟수를 같이 남겨주세요."]
    if reps >= 10:
        return [
            f"최근 {weight:.1f}kg x {reps}회까지 했습니다. 다음 목표는 {weight + 2.5:.1f}kg로 6~8회입니다.",
            "중량을 올린 날은 첫 세트 성공률을 보고 나머지 세트는 같은 중량으로 유지하세요.",
        ]
    return [
        f"최근 {weight:.1f}kg x {reps}회입니다. 다음 목표는 같은 중량으로 {reps + 1}회입니다.",
        "목표 횟수에 도달하면 그 다음 운동에서 2.5kg 증량을 고려하세요.",
    ]


def build_exercise_trend_summary(exercise_id: int | None) -> list[dict[str, object]]:
    if not exercise_id:
        return []
    rows = get_db().execute(
        """
        SELECT
            s.workout_date,
            MAX(COALESCE(ws.weight, 0)) AS max_weight,
            MAX(COALESCE(ws.weight, 0) * (1 + COALESCE(ws.reps, 0) / 30.0)) AS estimated_1rm,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.exercise_id = ?
        GROUP BY s.workout_date
        ORDER BY s.workout_date ASC
        """,
        (exercise_id,),
    ).fetchall()
    if not rows:
        return []
    first = rows[0]
    last = rows[-1]
    return [
        {
            "label": "중량 변화",
            "value": float(last["max_weight"] or 0) - float(first["max_weight"] or 0),
            "unit": "kg",
            "current": float(last["max_weight"] or 0),
        },
        {
            "label": "1RM 변화",
            "value": float(last["estimated_1rm"] or 0) - float(first["estimated_1rm"] or 0),
            "unit": "kg",
            "current": float(last["estimated_1rm"] or 0),
        },
        {
            "label": "볼륨 변화",
            "value": float(last["volume"] or 0) - float(first["volume"] or 0),
            "unit": "kg",
            "current": float(last["volume"] or 0),
        },
        {
            "label": "유산소 변화",
            "value": float(last["cardio_minutes"] or 0) - float(first["cardio_minutes"] or 0),
            "unit": "분",
            "current": float(last["cardio_minutes"] or 0),
        },
    ]


def build_exercise_growth_chart(exercise_id: int | None, limit: int = 10) -> list[dict[str, float | int | str]]:
    if not exercise_id:
        return []
    profile = get_exercise_profile(exercise_id)
    is_cardio = bool(profile and profile.get("body_part") == "유산소")
    rows = get_db().execute(
        """
        SELECT
            s.workout_date AS period,
            MAX(COALESCE(ws.weight, 0)) AS max_weight,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            MAX(COALESCE(ws.weight, 0) * (1 + COALESCE(ws.reps, 0) / 30.0)) AS estimated_1rm,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            MAX(COALESCE(ws.cardio_speed, 0)) AS cardio_speed,
            MAX(COALESCE(ws.cardio_incline, 0)) AS cardio_incline
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.exercise_id = ?
        GROUP BY s.workout_date
        ORDER BY s.workout_date DESC
        LIMIT ?
        """,
        (exercise_id, limit),
    ).fetchall()
    ordered = list(reversed(rows))
    max_weight = max([float(row["max_weight"]) for row in ordered] + [1.0])
    max_volume = max([float(row["volume"]) for row in ordered] + [1.0])
    max_1rm = max([float(row["estimated_1rm"]) for row in ordered] + [1.0])
    max_minutes = max([float(row["cardio_minutes"]) for row in ordered] + [1.0])
    max_speed = max([float(row["cardio_speed"]) for row in ordered] + [1.0])
    max_incline = max([float(row["cardio_incline"]) for row in ordered] + [1.0])
    return [
        {
            "period": row["period"][5:],
            "is_cardio": is_cardio,
            "max_weight": float(row["max_weight"]),
            "rep_count": int(row["rep_count"]),
            "volume": float(row["volume"]),
            "estimated_1rm": float(row["estimated_1rm"]),
            "cardio_minutes": float(row["cardio_minutes"]),
            "cardio_speed": float(row["cardio_speed"]),
            "cardio_incline": float(row["cardio_incline"]),
            "weight_height": max(3, round(float(row["max_weight"]) / max_weight * 100)),
            "weight_width": round(float(row["max_weight"]) / max_weight * 100),
            "volume_height": max(3, round(float(row["volume"]) / max_volume * 100)),
            "volume_width": round(float(row["volume"]) / max_volume * 100),
            "estimated_1rm_width": round(float(row["estimated_1rm"]) / max_1rm * 100),
            "cardio_minutes_width": round(float(row["cardio_minutes"]) / max_minutes * 100),
            "cardio_speed_width": round(float(row["cardio_speed"]) / max_speed * 100),
            "cardio_incline_width": round(float(row["cardio_incline"]) / max_incline * 100),
        }
        for row in ordered
    ]


def list_exercise_pr_timeline(exercise_id: int | None, limit: int = 12) -> list[dict[str, object]]:
    if not exercise_id:
        return []
    rows = get_db().execute(
        """
        SELECT
            s.workout_date,
            MAX(COALESCE(ws.weight, 0)) AS max_weight,
            MAX(COALESCE(ws.weight, 0) * (1 + COALESCE(ws.reps, 0) / 30.0)) AS estimated_1rm,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.exercise_id = ?
        GROUP BY s.workout_date
        ORDER BY s.workout_date DESC
        LIMIT ?
        """,
        (exercise_id, limit),
    ).fetchall()
    ordered = list(reversed(rows))
    max_weight = max([float(row["max_weight"] or 0) for row in ordered] + [1.0])
    max_1rm = max([float(row["estimated_1rm"] or 0) for row in ordered] + [1.0])
    return [
        {
            "period": row["workout_date"][5:],
            "max_weight": float(row["max_weight"] or 0),
            "estimated_1rm": float(row["estimated_1rm"] or 0),
            "volume": float(row["volume"] or 0),
            "weight_width": round(float(row["max_weight"] or 0) / max_weight * 100),
            "estimated_1rm_width": round(float(row["estimated_1rm"] or 0) / max_1rm * 100),
        }
        for row in ordered
    ]


def list_exercise_recent_sets(exercise_id: int | None, limit: int = 12) -> list[sqlite3.Row]:
    if not exercise_id:
        return []
    return get_db().execute(
        """
        SELECT
            s.workout_date,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            ws.weight,
            ws.reps,
            ws.set_type,
            ws.rpe,
            ws.equipment,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.estimated_calories
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.exercise_id = ?
        ORDER BY s.workout_date DESC, ws.sort_order DESC, ws.id DESC
        LIMIT ?
        """,
        (exercise_id, limit),
    ).fetchall()


def search_workout_records_filtered(
    query: str = "",
    body_part: str = "",
    equipment: str = "",
    start_date: str = "",
    end_date: str = "",
    limit: int = 120,
) -> list[sqlite3.Row]:
    where = []
    params: list[object] = []
    if query:
        where.append("(e.name LIKE ? OR ws.memo LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    if body_part:
        where.append("COALESCE(NULLIF(ws.body_part, ''), '기타') = ?")
        params.append(body_part)
    if equipment:
        where.append("COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') = ?")
        params.append(equipment)
    if start_date:
        where.append("s.workout_date >= ?")
        params.append(start_date)
    if end_date:
        where.append("s.workout_date <= ?")
        params.append(end_date)
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    params.append(limit)
    return get_db().execute(
        f"""
        SELECT
            s.workout_date,
            e.name AS exercise_name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') AS equipment,
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
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        {where_sql}
        ORDER BY s.workout_date DESC, ws.sort_order ASC, ws.id ASC
        LIMIT ?
        """,
        params,
    ).fetchall()


def list_month_calendar_days(month_start: str) -> list[dict[str, object]]:
    next_month = shift_month(month_start, 1)
    workout_rows = get_db().execute(
        """
        SELECT
            s.workout_date,
            COALESCE(s.duration_seconds, 0) AS duration_seconds,
            COALESCE(s.completed, 0) AS completed,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes
        FROM workout_sessions s
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        GROUP BY s.workout_date, s.duration_seconds, s.completed
        """,
        (month_start, next_month),
    ).fetchall()
    meal_rows = get_db().execute(
        """
        SELECT meal_date, COUNT(id) AS meal_count
        FROM meal_entries
        WHERE meal_date >= ? AND meal_date < ?
        GROUP BY meal_date
        """,
        (month_start, next_month),
    ).fetchall()
    workouts = {
        row["workout_date"]: {
            "set_count": int(row["set_count"]),
            "duration_seconds": int(row["duration_seconds"] or 0),
            "completed": bool(row["completed"]),
            "volume": float(row["volume"] or 0),
            "cardio_minutes": float(row["cardio_minutes"] or 0),
        }
        for row in workout_rows
    }
    meals = {row["meal_date"]: int(row["meal_count"]) for row in meal_rows}
    start = datetime.strptime(month_start, "%Y-%m-%d")
    next_start = datetime.strptime(next_month, "%Y-%m-%d")
    days = []
    current = start
    while current < next_start:
        key = current.strftime("%Y-%m-%d")
        days.append(
            {
                "date": key,
                "day": current.day,
                "weekday": current.weekday(),
                "set_count": workouts.get(key, {}).get("set_count", 0),
                "duration_seconds": workouts.get(key, {}).get("duration_seconds", 0),
                "completed": workouts.get(key, {}).get("completed", False),
                "volume": workouts.get(key, {}).get("volume", 0),
                "cardio_minutes": workouts.get(key, {}).get("cardio_minutes", 0),
                "meal_count": meals.get(key, 0),
            }
        )
        current += timedelta(days=1)
    return days


def list_body_part_summary(scope: str, limit: int = 30, date_text: str | None = None) -> list[sqlite3.Row]:
    where_clause = ""
    params: list[object] = []
    if scope == "daily":
        period_expr = "s.workout_date"
        order_clause = "MAX(s.workout_date) DESC, body_part"
    elif scope == "weekly":
        period_expr = (
            "CAST(strftime('%m', s.workout_date) AS INTEGER) || '월 ' || "
            "(((CAST(strftime('%d', s.workout_date) AS INTEGER) - 1) / 7) + 1) || '주차'"
        )
        order_clause = "body_part, MAX(s.workout_date) DESC"
        if date_text:
            week_start = week_start_for_date(date_text)
            period_expr = f"'{meal_week_label(week_start)}'"
            where_clause = "WHERE s.workout_date BETWEEN ? AND ?"
            params.extend([week_start, shift_date(week_start, 6)])
    else:
        period_expr = "strftime('%Y-%m', s.workout_date)"
        order_clause = "body_part, MAX(s.workout_date) DESC"
        if date_text:
            month_start = normalize_month(date_text)
            where_clause = "WHERE s.workout_date >= ? AND s.workout_date < ?"
            params.extend([month_start, shift_month(month_start, 1)])
    params.append(limit)

    return get_db().execute(
        f"""
        SELECT
            {period_expr} AS period,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            COUNT(DISTINCT pe.id) AS pr_count,
            MAX(CASE WHEN pe.record_type = '최고 중량' THEN pe.record_value END) AS best_pr_weight,
            MAX(CASE WHEN pe.record_type = '최고 반복' THEN pe.record_value END) AS best_pr_reps,
            MAX(CASE WHEN pe.record_type = '최고 볼륨' THEN pe.record_value END) AS best_pr_volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        LEFT JOIN pr_events pe ON pe.set_id = ws.id
        {where_clause}
        GROUP BY period, body_part
        ORDER BY {order_clause}
        LIMIT ?
        """,
        params,
    ).fetchall()


def list_weekly_body_part_details(date_text: str | None = None) -> dict[str, list[sqlite3.Row]]:
    where_clause = ""
    params: list[object] = []
    if date_text:
        week_start = week_start_for_date(date_text)
        where_clause = "WHERE s.workout_date BETWEEN ? AND ?"
        params.extend([week_start, shift_date(week_start, 6)])
        period_expr = f"'{meal_week_label(week_start)}'"
    else:
        period_expr = (
            "CAST(strftime('%m', s.workout_date) AS INTEGER) || '월 ' || "
            "(((CAST(strftime('%d', s.workout_date) AS INTEGER) - 1) / 7) + 1) || '주차'"
        )
    rows = get_db().execute(
        f"""
        SELECT
            {period_expr} AS period,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.name AS exercise_name,
            MIN(ws.weight) AS min_weight,
            MAX(ws.weight) AS max_weight,
            AVG(ws.cardio_incline) AS avg_cardio_incline,
            AVG(ws.cardio_speed) AS avg_cardio_speed,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COUNT(DISTINCT pe.id) AS pr_count,
            MAX(CASE WHEN pe.record_type = '최고 중량' THEN pe.record_value END) AS best_pr_weight,
            MAX(CASE WHEN pe.record_type = '최고 반복' THEN pe.record_value END) AS best_pr_reps,
            MAX(CASE WHEN pe.record_type = '최고 볼륨' THEN pe.record_value END) AS best_pr_volume,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN pr_events pe ON pe.set_id = ws.id
        {where_clause}
        GROUP BY period, body_part, e.name
        ORDER BY MAX(s.workout_date) DESC, body_part, e.name
        """,
        params,
    ).fetchall()

    details: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        details.setdefault(f"{row['period']}::{row['body_part']}", []).append(row)
    return details


def list_sets_for_session(session_id: int) -> list[sqlite3.Row]:
    return list_sets_for_session_from_db(get_db(), session_id)


def grouped_sets_for_session(session_id: int | None) -> list[dict[str, object]]:
    return grouped_sets_for_session_from_db(get_db(), session_id)


def current_local_date() -> str:
    try:
        app_timezone = ZoneInfo(APP_TIMEZONE)
    except ZoneInfoNotFoundError:
        app_timezone = timezone(timedelta(hours=9), name="KST")
    return datetime.now(app_timezone).strftime("%Y-%m-%d")


def normalize_date(date_text: str | None, max_future_days: int = 31) -> str:
    today_text = current_local_date()
    try:
        date_value = datetime.strptime((date_text or "").strip(), "%Y-%m-%d")
    except ValueError:
        return today_text

    today_value = datetime.strptime(today_text, "%Y-%m-%d")
    if date_value > today_value + timedelta(days=max_future_days):
        return today_text
    return date_value.strftime("%Y-%m-%d")


def normalize_optional_date(date_text: str | None, max_future_days: int = 31) -> str:
    if not (date_text or "").strip():
        return ""
    return normalize_date(date_text, max_future_days=max_future_days)


def shift_date(date_text: str, days: int) -> str:
    return (datetime.strptime(date_text, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")


def week_start_for_date(date_text: str) -> str:
    try:
        date_value = datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        date_value = datetime.strptime(current_local_date(), "%Y-%m-%d")
    return (date_value - timedelta(days=date_value.weekday())).strftime("%Y-%m-%d")


def meal_week_label(week_start: str) -> str:
    date_value = datetime.strptime(shift_date(week_start, 6), "%Y-%m-%d")
    week_of_month = ((date_value.day - 1) // 7) + 1
    return f"{date_value.month}월 {week_of_month}주차"


def meal_day_label(date_text: str) -> str:
    date_value = datetime.strptime(date_text, "%Y-%m-%d")
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    return f"{date_value.month}/{date_value.day}({weekdays[date_value.weekday()]})"


def normalize_month(month_text: str) -> str:
    today_month = datetime.strptime(current_local_date(), "%Y-%m-%d").replace(day=1)
    try:
        if len(month_text) == 7:
            month_value = datetime.strptime(f"{month_text}-01", "%Y-%m-%d")
        else:
            month_value = datetime.strptime(month_text, "%Y-%m-%d").replace(day=1)
    except ValueError:
        return today_month.strftime("%Y-%m-01")
    if month_value > today_month + timedelta(days=62):
        return today_month.strftime("%Y-%m-01")
    return month_value.strftime("%Y-%m-%d")


def shift_month(month_start: str, months: int) -> str:
    date_value = datetime.strptime(normalize_month(month_start), "%Y-%m-%d")
    month_index = date_value.month - 1 + months
    year = date_value.year + month_index // 12
    month = month_index % 12 + 1
    return f"{year:04d}-{month:02d}-01"


def get_body_weight_for_date(metric_date: str) -> float:
    row = get_db().execute(
        """
        SELECT body_weight
        FROM body_metrics
        WHERE metric_date <= ? AND body_weight IS NOT NULL
        ORDER BY metric_date DESC
        LIMIT 1
        """,
        (metric_date,),
    ).fetchone()
    if row and row["body_weight"]:
        return float(row["body_weight"])
    return DEFAULT_BODY_WEIGHT_KG


def estimate_cardio_met(speed: float | None, incline: float | None) -> float:
    speed_value = float(speed or 0)
    incline_value = max(0.0, float(incline or 0))
    if speed_value >= 8.0:
        base_met = 9.0
    elif speed_value >= 6.5:
        base_met = 7.0
    elif speed_value >= 5.0:
        base_met = 4.8
    else:
        base_met = 3.5
    return min(12.0, base_met + (incline_value * 0.12))


def estimate_exercise_calories(
    body_part: str,
    cardio_incline: float | None,
    cardio_speed: float | None,
    cardio_minutes: float | None,
    workout_date: str,
) -> float | None:
    if body_part != "유산소" or not cardio_minutes:
        return None
    met = estimate_cardio_met(cardio_speed, cardio_incline)
    body_weight = get_body_weight_for_date(workout_date)
    return round(met * body_weight * float(cardio_minutes) / 60)


def recalculate_missing_exercise_calories() -> None:
    db = get_db()
    rows = db.execute(
        """
        SELECT ws.id, s.workout_date, ws.body_part, ws.cardio_incline, ws.cardio_speed, ws.cardio_minutes
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE COALESCE(NULLIF(ws.body_part, ''), '기타') = '유산소'
          AND ws.cardio_minutes IS NOT NULL
          AND ws.estimated_calories IS NULL
        """
    ).fetchall()
    for row in rows:
        db.execute(
            "UPDATE workout_sets SET estimated_calories = ? WHERE id = ?",
            (
                estimate_exercise_calories(
                    row["body_part"],
                    row["cardio_incline"],
                    row["cardio_speed"],
                    row["cardio_minutes"],
                    row["workout_date"],
                ),
                row["id"],
            ),
        )


def recalculate_exercise_calories_for_date(workout_date: str) -> None:
    db = get_db()
    rows = db.execute(
        """
        SELECT ws.id, ws.body_part, ws.cardio_incline, ws.cardio_speed, ws.cardio_minutes
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date = ?
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') = '유산소'
        """,
        (workout_date,),
    ).fetchall()
    for row in rows:
        db.execute(
            "UPDATE workout_sets SET estimated_calories = ? WHERE id = ?",
            (
                estimate_exercise_calories(
                    row["body_part"],
                    row["cardio_incline"],
                    row["cardio_speed"],
                    row["cardio_minutes"],
                    workout_date,
                ),
                row["id"],
            ),
        )


app = create_app()
app.jinja_env.globals["grouped_sets_for_session"] = grouped_sets_for_session
app.jinja_env.globals["body_part_class"] = body_part_class
app.jinja_env.globals["meal_type_class"] = meal_type_class
app.jinja_env.globals["format_duration"] = format_duration
app.jinja_env.globals["duration_hours"] = duration_hours
app.jinja_env.globals["duration_minutes"] = duration_minutes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5000, type=int)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
