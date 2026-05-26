from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
from datetime import datetime

from flask import Flask, Response, abort, g, jsonify, redirect, render_template, request, session, url_for

from health_tracker.config import BASE_DIR, DATABASE, PHOTO_DIR
from health_tracker.constants import (
    BODY_PART_CLASSES,
    BODY_PARTS,
    DEFAULT_BODY_WEIGHT_KG,
    DEFAULT_DAILY_CALORIES,
    DEFAULT_REST_SECONDS,
    DEFAULT_PROGRAMS,
    EQUIPMENT_OPTIONS,
    MEAL_TYPE_CLASSES,
    RECOMMENDED_EXERCISE_MAP,
    SET_TYPE_OPTIONS,
    normalize_equipment_category,
)
from health_tracker.date_utils import (
    current_local_date,
    meal_day_label,
    meal_week_label,
    normalize_date,
    normalize_month,
    normalize_optional_date,
    shift_date,
    shift_month,
    week_start_for_date,
)
from health_tracker.database.schema import init_database
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
from health_tracker.services.body_part_analysis import (
    list_body_part_summary_from_db,
    list_weekly_body_part_details_from_db,
)
from health_tracker.services.body import (
    build_body_monthly_report_from_rows,
    get_body_metric_from_db,
    list_body_metric_trend_from_rows,
    list_body_metrics_from_db,
    list_body_photos_from_db,
    save_body_metric_to_db,
    save_body_photo_to_db,
)
from health_tracker.services.data import (
    get_backup_status as build_backup_status,
    get_data_counts as build_data_counts,
    get_sample_data_counts as build_sample_data_counts,
)
from health_tracker.services.calendar import list_month_calendar_days_from_db
from health_tracker.services.coaching import (
    build_adaptive_training_recommendations_from_db,
    build_readiness_profile_from_db,
    get_recovery_checkin_from_db,
    list_daily_coaching_from_db,
    list_recommended_sessions_from_db,
    list_recovery_recommendations_from_db,
    list_workout_focus_recommendations_from_db,
    save_recovery_checkin_to_db,
    save_rest_day_to_db,
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
from health_tracker.services.exercise_calorie import estimate_exercise_calories_from_weight
from health_tracker.services.exercise_settings import (
    get_exercise_rest_seconds_from_db,
    list_exercise_notes_from_db,
    list_exercise_settings_from_db,
    save_exercise_equipment_to_db,
    save_exercise_note_to_db,
    save_exercise_settings_to_db,
)
from health_tracker.services.exercise_rules import (
    today_rule_cards_from_db,
    weekly_rule_report_from_db,
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
    apply_meal_template_to_db,
    build_monthly_meal_summary_from_db,
    build_weekly_meal_summary_from_db,
    copy_meal_type_from_day_in_db,
    copy_meals_from_day_in_db,
    create_meal_template_from_day_in_db,
    delete_meal_template_from_db,
    grouped_meals_for_date_from_db,
    list_frequent_meal_combos_from_db,
    list_meal_templates_from_db,
    list_meals_for_date_from_db,
    list_monthly_meal_weeks_from_db,
    list_recent_meal_days_from_db,
    list_weekly_meal_days_from_db,
)
from health_tracker.services.muscle_balance import build_muscle_balance as build_muscle_balance_from_db
from health_tracker.services.personal_coach import (
    build_data_safety_status,
    build_next_actions_from_db,
)
from health_tracker.services.pagination import build_pagination, page_params, query_url
from health_tracker.services.preferences import app_preferences as build_app_preferences
from health_tracker.services.preferences import save_app_preferences as save_app_preferences_to_db
from health_tracker.services.progressive_overload import (
    build_next_set_suggestions as build_next_set_suggestions_from_db,
    list_progressive_overload_rows as list_progressive_overload_rows_from_db,
)
from health_tracker.services.pr import (
    build_pr_cards_from_rows,
    build_pr_dashboard_from_rows,
    list_exercise_pr_history_from_db,
    list_exercise_pr_summary_from_db,
    list_pr_events_from_db,
    list_pr_exercise_choices_from_db,
    list_recent_pr_events_filtered_from_db,
    list_recent_pr_events_from_db,
)
from health_tracker.services.records import (
    allowed_sort,
    list_exercise_summary_by_body_part_from_db,
    paged_equipment_daily_from_db,
    paged_equipment_detail_from_db,
    paged_equipment_summary_from_db,
    paged_exercise_summary_from_db,
    paged_rows_from_db,
    paged_search_workout_records_filtered_from_db,
)
from health_tracker.services.routine import (
    apply_routine_template_to_db,
    apply_session_template_to_db,
    create_routine_template_from_db,
    delete_routine_template_from_db,
    list_routines_from_db,
    rename_routine_template_in_db,
)
from health_tracker.services.sample_data import create_may_sample_data_in_db, delete_sample_data_from_db
from health_tracker.services.summary import build_daily_chart_from_rows, build_period_chart_from_rows
from health_tracker.services.smart_workout import list_exercise_smart_defaults_from_db
from health_tracker.services.workout import (
    get_or_create_exercise_in_db,
    grouped_sets_for_session_from_db,
    list_sets_for_session_from_db,
    reorder_set_within_exercise_in_db,
)
from health_tracker.services.workout_plan import (
    apply_default_program_to_db,
    build_workout_completion_summary_from_db,
    build_workout_session_flow_from_db,
    create_workout_plan_item_in_db,
    delete_workout_plan_item_from_db,
    list_workout_plan_from_db,
)
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
        preferences = get_app_preferences()
        return {
            "app_version": get_app_version(),
            "app_updated_at": get_app_updated_at(),
            "is_admin": settings_unlocked(),
            "csrf_token": ensure_csrf_token,
            "per_page_options": preferences["per_page_options"],
            "app_preferences": preferences,
            "body_part_class_map": BODY_PART_CLASSES,
            "meal_type_class_map": MEAL_TYPE_CLASSES,
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
    init_database(
        get_db(),
        recalculate_missing_exercise_calories,
        bootstrap_locations,
        delete_internal_test_data,
    )



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


def get_app_preferences() -> dict[str, object]:
    return build_app_preferences(get_db())


def configured_page_params(args) -> tuple[int, int]:
    return page_params(args, int(get_app_preferences()["default_per_page"]))


def normalize_summary_days(value: str | None) -> int:
    options = [int(item) for item in get_app_preferences()["summary_day_options"]]
    parsed = parse_int(value) or options[0]
    return min(max(parsed, min(options)), max(options))


def save_app_preferences(form) -> None:
    save_app_preferences_to_db(get_db(), form)


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
    reorder_set_within_exercise_in_db(db, set_id, requested_set_number)


def get_or_create_exercise(name: str) -> int:
    return get_or_create_exercise_in_db(get_db(), name)


def list_exercises(location_id: int | None = None) -> list[sqlite3.Row]:
    if location_id:
        return get_db().execute(
            """
            SELECT DISTINCT e.id, e.name
            FROM exercises e
            JOIN workout_sets ws ON ws.exercise_id = e.id
            JOIN workout_sessions s ON s.id = ws.session_id
            WHERE s.location_id = ?
            ORDER BY e.name
            """,
            (location_id,),
        ).fetchall()
    return get_db().execute("SELECT id, name FROM exercises ORDER BY name").fetchall()


def list_exercises_by_body_part(location_id: int | None = None) -> dict[str, list[str]]:
    location_where = "WHERE s.location_id = ?" if location_id else ""
    params = (location_id,) if location_id else ()
    rows = get_db().execute(
        f"""
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.name,
            COUNT(ws.id) AS use_count,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        {location_where}
        GROUP BY body_part, e.name
        ORDER BY body_part, last_date DESC, use_count DESC, e.name
        """,
        params,
    ).fetchall()
    exercises_by_part = {part: [] for part in body_part_options()}
    for row in rows:
        part = row["body_part"] or "기타"
        exercises_by_part.setdefault(part, []).append(row["name"])
    return exercises_by_part


def list_recent_sets_by_exercise(
    limit: int = 6,
    location_id: int | None = None,
) -> dict[str, list[dict[str, float | int | None]]]:
    location_filter = "AND s.location_id = ?" if location_id else ""
    params = (location_id,) if location_id else ()
    rows = get_db().execute(
        f"""
        SELECT e.name, ws.weight, ws.reps, s.workout_date, ws.sort_order
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.weight IS NOT NULL OR ws.reps IS NOT NULL
        {location_filter}
        ORDER BY s.workout_date DESC, ws.sort_order ASC, ws.id ASC
        """,
        params,
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


def list_exercise_stats_by_name(location_id: int | None = None) -> dict[str, dict[str, object]]:
    location_filter = "AND s.location_id = ?" if location_id else ""
    recent_location_filter = "AND s2.location_id = ?" if location_id else ""
    params: tuple[object, ...] = (location_id, location_id) if location_id else ()
    rows = get_db().execute(
        f"""
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
                  {recent_location_filter}
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS recent
        FROM exercises e
        JOIN workout_sets ws ON ws.exercise_id = e.id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.weight IS NOT NULL OR ws.reps IS NOT NULL
        {location_filter}
        GROUP BY e.id, e.name
        """,
        params,
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


def list_routines(location_id: int | None = None) -> list[dict[str, object]]:
    return list_routines_from_db(get_db(), location_id)


def rename_routine_template(routine_id: int, name: str) -> None:
    rename_routine_template_in_db(get_db(), routine_id, name)


def delete_routine_template(routine_id: int) -> None:
    delete_routine_template_from_db(get_db(), routine_id)


def create_routine_template(name: str, session_id: int) -> None:
    create_routine_template_from_db(get_db(), name, session_id)


def apply_routine_template(routine_id: int, workout_date: str) -> None:
    apply_routine_template_to_db(
        get_db(),
        routine_id,
        workout_date,
        get_or_create_session,
        get_or_create_exercise,
        estimate_exercise_calories,
    )


def apply_session_template(source_session_id: int, workout_date: str) -> None:
    apply_session_template_to_db(
        get_db(),
        source_session_id,
        workout_date,
        get_or_create_session,
        get_or_create_exercise,
        estimate_exercise_calories,
    )


def list_workout_plan(workout_date: str) -> list[sqlite3.Row]:
    return list_workout_plan_from_db(get_db(), workout_date)


def build_workout_completion_summary(workout_date: str) -> dict[str, object]:
    return build_workout_completion_summary_from_db(get_db(), workout_date, get_or_create_session)


def build_workout_session_flow(workout_date: str) -> dict[str, object]:
    return build_workout_session_flow_from_db(
        get_db(),
        workout_date,
        get_exercise_rest_seconds,
        int(get_app_preferences()["default_rest_seconds"]),
    )


def list_record_gaps(date_text: str, days: int = 7) -> list[dict[str, object]]:
    return list_record_gaps_from_db(get_db(), date_text, days)


def build_data_quality_profile(date_text: str, days: int = 14) -> dict[str, object]:
    return build_data_quality_profile_from_db(get_db(), normalize_date(date_text), days)


def create_workout_plan_item(workout_date: str, body_part: str, exercise_name: str, target_sets: int) -> None:
    create_workout_plan_item_in_db(get_db(), workout_date, body_part, exercise_name, target_sets)


def delete_workout_plan_item(item_id: int) -> None:
    delete_workout_plan_item_from_db(get_db(), item_id)


def apply_default_program(program_name: str, workout_date: str) -> None:
    apply_default_program_to_db(get_db(), DEFAULT_PROGRAMS.get(program_name), workout_date, get_or_create_session, get_or_create_exercise)


def list_recommended_sessions(workout_date: str, limit: int = 3) -> list[dict[str, object]]:
    return list_recommended_sessions_from_db(get_db(), workout_date, limit)


def list_workout_focus_recommendations(workout_date: str, limit: int = 5) -> list[dict[str, object]]:
    return list_workout_focus_recommendations_from_db(get_db(), workout_date, body_part_options, limit)


def build_adaptive_training_recommendations(workout_date: str, limit: int = 6) -> list[dict[str, object]]:
    return build_adaptive_training_recommendations_from_db(get_db(), workout_date, shift_date, limit)


def build_next_set_suggestions(exercise_names: list[str], workout_date: str, limit: int = 8) -> dict[str, dict[str, object]]:
    readiness = build_readiness_profile(workout_date)
    return build_next_set_suggestions_from_db(get_db(), exercise_names, int(readiness["percent"] or 60), limit)


def list_progressive_overload_rows(limit: int = 30) -> list[dict[str, object]]:
    return list_progressive_overload_rows_from_db(get_db(), limit)


def build_muscle_balance(start_date: str, end_date: str) -> dict[str, object]:
    return build_muscle_balance_from_db(get_db(), start_date, end_date, body_part_class)


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
        if float(row["calories"] or 0) < float(get_goal_value("daily_calories", int(get_app_preferences()["default_daily_calories"]))) * 0.75
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
    default_rest_seconds = int(get_app_preferences()["default_rest_seconds"])
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
            COALESCE(es.rest_seconds, {default_rest_seconds}) AS rest_seconds,
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
    default_rest_seconds = int(get_app_preferences()["default_rest_seconds"])
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
            COALESCE(es.rest_seconds, {default_rest_seconds}) AS rest_seconds,
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
    return list_pr_events_from_db(get_db(), workout_date)


def build_pr_cards(workout_date: str) -> list[dict[str, object]]:
    return build_pr_cards_from_rows(list_pr_events(workout_date))


def list_recent_pr_events(limit: int = 12) -> list[sqlite3.Row]:
    return list_recent_pr_events_from_db(get_db(), limit)


def list_recent_pr_events_filtered(body_part: str = "", query: str = "", limit: int = 30) -> list[sqlite3.Row]:
    return list_recent_pr_events_filtered_from_db(get_db(), body_part, query, limit)


def list_exercise_pr_history(exercise_id: int | None, limit: int = 12) -> list[sqlite3.Row]:
    return list_exercise_pr_history_from_db(get_db(), exercise_id, limit)


def list_exercise_pr_summary(body_part: str = "", query: str = "", limit: int = 80) -> list[sqlite3.Row]:
    return list_exercise_pr_summary_from_db(get_db(), body_part, query, limit)


def list_pr_exercise_choices(body_part: str = "", query: str = "") -> list[sqlite3.Row]:
    return list_pr_exercise_choices_from_db(get_db(), body_part, query)


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
    return list_exercise_notes_from_db(get_db())


def save_exercise_note(exercise_name: str, note: str) -> None:
    save_exercise_note_to_db(get_db(), exercise_name, note)


def list_exercise_settings() -> dict[str, dict[str, int | float | bool | str | None]]:
    return list_exercise_settings_from_db(get_db(), int(get_app_preferences()["default_rest_seconds"]))


def list_exercise_smart_defaults(location_id: int | None = None) -> dict[str, dict[str, object]]:
    return list_exercise_smart_defaults_from_db(get_db(), location_id)


def save_exercise_settings(
    exercise_name: str,
    rest_seconds: int,
    is_favorite: bool,
    equipment: str = "",
    target_weight: float | None = None,
    target_reps: int | None = None,
    target_sets: int | None = None,
) -> None:
    save_exercise_settings_to_db(
        get_db(),
        exercise_name,
        rest_seconds,
        is_favorite,
        int(get_app_preferences()["default_rest_seconds"]),
        equipment,
        target_weight,
        target_reps,
        target_sets,
    )


def save_exercise_equipment(exercise_name: str, equipment: str) -> None:
    save_exercise_equipment_to_db(get_db(), exercise_name, equipment)


def get_exercise_rest_seconds(exercise_name: str) -> int:
    return get_exercise_rest_seconds_from_db(get_db(), exercise_name, int(get_app_preferences()["default_rest_seconds"]))


def list_favorite_exercises(location_id: int | None = None) -> list[sqlite3.Row]:
    location_filter = (
        """
        AND EXISTS (
            SELECT 1
            FROM workout_sets lws
            JOIN workout_sessions ls ON ls.id = lws.session_id
            JOIN exercises le ON le.id = lws.exercise_id
            WHERE le.name = es.exercise_name AND ls.location_id = ?
        )
        """
        if location_id
        else ""
    )
    params = (location_id,) if location_id else ()
    return get_db().execute(
        f"""
        SELECT
            es.exercise_name,
            es.rest_seconds,
            es.equipment,
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
        {location_filter}
        ORDER BY es.updated_at DESC, es.exercise_name
        """,
        params,
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
    return list(EQUIPMENT_OPTIONS)


def build_data_center_status(date_text: str | None = None) -> dict[str, object]:
    date_value = normalize_date(date_text)
    counts = get_data_counts()
    backup_status = get_backup_status()
    quality = build_data_quality_profile(date_value, 30)
    gaps = list_record_gaps(date_value, 30)
    exports = [
        {"label": "전체 JSON", "href": url_for("export_json"), "note": "복원 가능한 전체 백업"},
        {"label": "운동 CSV", "href": url_for("export_csv"), "note": "운동 기록 표"},
        {"label": "식단 CSV", "href": url_for("export_meal_csv_route"), "note": "식단 기록 표"},
        {
            "label": f"{date_value[:4]} 운동 CSV",
            "href": url_for("export_yearly_workouts_csv_route", year=date_value[:4]),
            "note": "연간 운동 기록",
        },
        {
            "label": f"{date_value[:4]} 식단 CSV",
            "href": url_for("export_yearly_meals_csv_route", year=date_value[:4]),
            "note": "연간 식단 기록",
        },
    ]
    warnings = []
    if gaps:
        warnings.append(f"최근 30일 중 {len(gaps)}일은 운동/식단/휴식 기록이 없습니다.")
    if counts["empty_workouts"]:
        warnings.append(f"비어 있는 운동 세션 {counts['empty_workouts']}개를 정리할 수 있습니다.")
    if quality["score"] < 70:
        warnings.append("분석 신뢰도가 낮아 추천과 추세 해석이 제한될 수 있습니다.")
    if not warnings:
        warnings.append("백업과 기록 상태가 안정적입니다.")
    return {
        "date": date_value,
        "counts": counts,
        "backup_status": backup_status,
        "quality": quality,
        "gaps": gaps[:8],
        "exports": exports,
        "warnings": warnings,
    }


def list_location_training_insights(limit: int = 20) -> list[dict[str, object]]:
    rows = get_db().execute(
        """
        SELECT
            wl.id,
            wl.name,
            wl.is_default,
            wl.is_active,
            COUNT(DISTINCT s.workout_date) AS workout_days,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            MAX(s.workout_date) AS last_date
        FROM workout_locations wl
        LEFT JOIN workout_sessions s ON s.location_id = wl.id
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        GROUP BY wl.id
        ORDER BY wl.is_active DESC, workout_days DESC, last_date DESC, wl.name
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    insights = []
    for row in rows:
        top_exercises = get_db().execute(
            """
            SELECT e.name, COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
            FROM workout_sessions s
            JOIN workout_sets ws ON ws.session_id = s.id
            JOIN exercises e ON e.id = ws.exercise_id
            WHERE s.location_id = ?
            GROUP BY e.id, e.name, body_part
            ORDER BY set_count DESC, MAX(s.workout_date) DESC
            LIMIT 4
            """,
            (row["id"],),
        ).fetchall()
        equipment_rows = get_db().execute(
            """
            SELECT COALESCE(NULLIF(ws.equipment, ''), '미지정') AS equipment, COUNT(ws.id) AS use_count
            FROM workout_sessions s
            JOIN workout_sets ws ON ws.session_id = s.id
            WHERE s.location_id = ?
            GROUP BY equipment
            ORDER BY use_count DESC, equipment
            LIMIT 5
            """,
            (row["id"],),
        ).fetchall()
        equipment_counts: dict[str, int] = {}
        for equipment_row in equipment_rows:
            category = normalize_equipment_category(equipment_row["equipment"])
            if category:
                equipment_counts[category] = equipment_counts.get(category, 0) + int(equipment_row["use_count"] or 0)
        top_equipment = [
            {"equipment": name, "use_count": count}
            for name, count in sorted(equipment_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
        ]
        insights.append(
            {
                "location": row,
                "top_exercises": top_exercises,
                "top_equipment": top_equipment,
                "message": build_location_message(row, top_exercises),
            }
        )
    return insights


def build_location_message(location: sqlite3.Row, top_exercises: list[sqlite3.Row]) -> str:
    if not location["workout_days"]:
        return "아직 기록이 없어 오늘 운동을 저장하면 장소별 추천이 시작됩니다."
    if top_exercises:
        return f"{top_exercises[0]['name']} 기록이 가장 많습니다. 오늘 입력에서 이 운동을 빠르게 불러올 수 있습니다."
    return "장소 기록은 있지만 세트 상세가 부족합니다. 장비와 세트를 함께 저장하면 추천 정확도가 올라갑니다."


def list_location_quick_exercises(location_id: int | None, limit: int = 6) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT
            e.name AS exercise_name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COALESCE(NULLIF(ws.equipment, ''), '') AS equipment,
            COUNT(ws.id) AS set_count,
            MAX(s.workout_date) AS last_date,
            (
                SELECT recent.weight
                FROM workout_sets recent
                JOIN workout_sessions rs ON rs.id = recent.session_id
                JOIN exercises re ON re.id = recent.exercise_id
                WHERE rs.location_id = s.location_id AND re.name = e.name
                ORDER BY rs.workout_date DESC, recent.id DESC
                LIMIT 1
            ) AS last_weight,
            (
                SELECT recent.reps
                FROM workout_sets recent
                JOIN workout_sessions rs ON rs.id = recent.session_id
                JOIN exercises re ON re.id = recent.exercise_id
                WHERE rs.location_id = s.location_id AND re.name = e.name
                ORDER BY rs.workout_date DESC, recent.id DESC
                LIMIT 1
            ) AS last_reps
        FROM workout_sessions s
        JOIN workout_sets ws ON ws.session_id = s.id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.location_id = ?
        GROUP BY e.name, body_part, equipment
        ORDER BY set_count DESC, last_date DESC, e.name
        LIMIT ?
        """,
        (location_id, limit),
    ).fetchall()


def build_action_insights(date_text: str | None = None) -> dict[str, object]:
    date_value = normalize_date(date_text)
    weekly_report = build_weekly_report(date_value)
    quality = build_data_quality_profile(date_value, 30)
    recommendations = build_adaptive_training_recommendations(date_value, limit=8)
    balance_warnings = list_balance_warnings("weekly", date_value)
    volume_warnings = list_volume_warnings(date_value)
    nutrition_link = build_nutrition_training_link("weekly", date_value)
    alerts = [*balance_warnings[:3], *volume_warnings[:3]]
    if quality["score"] < 70:
        alerts.append("기록 점검에서 누락일을 먼저 채우면 분석 신뢰도가 올라갑니다.")
    if not alerts:
        alerts.append("이번 주 기록 흐름은 안정적입니다. PR 후보 운동을 중심으로 진행하면 됩니다.")
    return {
        "date": date_value,
        "weekly_report": weekly_report,
        "quality": quality,
        "recommendations": recommendations,
        "alerts": alerts[:6],
        "nutrition_link": nutrition_link,
        "location_insights": list_location_training_insights(limit=4),
    }


def get_body_metric(metric_date: str) -> sqlite3.Row | None:
    return get_body_metric_from_db(get_db(), metric_date)


def save_body_metric(
    metric_date: str,
    body_weight: float | None,
    muscle_mass: float | None,
    body_fat: float | None,
    waist: float | None,
) -> None:
    save_body_metric_to_db(
        get_db(),
        metric_date,
        body_weight,
        muscle_mass,
        body_fat,
        waist,
        recalculate_exercise_calories_for_date,
    )


def list_body_metrics(month_start: str) -> list[sqlite3.Row]:
    return list_body_metrics_from_db(get_db(), month_start, shift_month)


def build_body_monthly_report(month_start: str) -> dict[str, object]:
    return build_body_monthly_report_from_rows(list_body_metrics(month_start))


def list_body_metric_trend(month_start: str) -> list[dict[str, object]]:
    return list_body_metric_trend_from_rows(list_body_metrics(month_start))


def save_body_photo(photo_date: str, file) -> None:
    save_body_photo_to_db(get_db(), PHOTO_DIR, photo_date, file)


def list_body_photos(photo_date: str, limit: int = 3) -> list[sqlite3.Row]:
    return list_body_photos_from_db(get_db(), photo_date, limit)


def list_meal_templates() -> list[dict[str, object]]:
    return list_meal_templates_from_db(get_db())


def create_meal_template_from_day(name: str, meal_date: str) -> None:
    create_meal_template_from_day_in_db(get_db(), name, meal_date)


def apply_meal_template(template_id: int, meal_date: str) -> None:
    apply_meal_template_to_db(get_db(), template_id, meal_date)


def delete_meal_template(template_id: int) -> None:
    delete_meal_template_from_db(get_db(), template_id)


def list_recent_meal_days(target_date: str, limit: int = 3) -> list[sqlite3.Row]:
    return list_recent_meal_days_from_db(get_db(), target_date, limit)


def copy_meals_from_day(source_date: str, meal_date: str) -> None:
    copy_meals_from_day_in_db(get_db(), source_date, meal_date)


def copy_meal_type_from_day(source_date: str, meal_date: str, meal_type: str) -> None:
    copy_meal_type_from_day_in_db(get_db(), source_date, meal_date, meal_type)


def list_frequent_meal_combos(limit: int = 6) -> list[dict[str, object]]:
    return list_frequent_meal_combos_from_db(get_db(), limit)


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
    return list_recovery_recommendations_from_db(get_db(), date_text, shift_date)


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
    return get_recovery_checkin_from_db(get_db(), date_text)


def save_recovery_checkin(
    checkin_date: str,
    condition_score: int,
    sleep_score: int,
    soreness_score: int,
    fatigue_score: int,
    memo: str,
) -> None:
    save_recovery_checkin_to_db(
        get_db(),
        checkin_date,
        condition_score,
        sleep_score,
        soreness_score,
        fatigue_score,
        memo,
    )


def save_rest_day(date_text: str, reason: str, memo: str = "") -> None:
    save_rest_day_to_db(get_db(), date_text, reason, memo)


def list_daily_coaching(date_text: str) -> list[str]:
    return list_daily_coaching_from_db(get_db(), date_text, shift_date)


def list_today_next_actions(date_text: str) -> list[dict[str, str]]:
    return build_next_actions_from_db(get_db(), date_text, shift_date)


def list_today_rule_cards(date_text: str) -> list[dict[str, object]]:
    return today_rule_cards_from_db(get_db(), date_text, shift_date)


def build_weekly_rule_report(week_start: str) -> dict[str, object]:
    return weekly_rule_report_from_db(get_db(), week_start, shift_date)


def build_readiness_profile(date_text: str) -> dict[str, object]:
    return build_readiness_profile_from_db(get_db(), date_text)


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


def get_data_safety_status() -> list[dict[str, str]]:
    return build_data_safety_status(get_backup_status(), has_settings_password(), settings_unlocked())


def get_sample_data_counts() -> dict[str, int]:
    return build_sample_data_counts(get_db())


def get_app_health_status() -> list[dict[str, str]]:
    return build_app_health_status(DATABASE, get_data_counts(), get_sample_data_counts(), get_backup_status())


def delete_sample_data() -> None:
    delete_sample_data_from_db(get_db(), delete_empty_workout_sessions)


def create_may_sample_data() -> None:
    create_may_sample_data_in_db(
        get_db(),
        delete_sample_data,
        get_or_create_session,
        get_or_create_exercise,
        save_exercise_equipment,
        estimate_exercise_calories,
    )


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
    return paged_rows_from_db(get_db(), select_sql, count_sql, params, page, per_page)


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
    return paged_search_workout_records_filtered_from_db(
        get_db(),
        query,
        body_part,
        equipment,
        location_id,
        start_date,
        end_date,
        sort,
        page,
        per_page,
    )


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
    return paged_exercise_summary_from_db(get_db(), sort, page, per_page)


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
    return list_exercise_summary_by_body_part_from_db(get_db(), body_part_options)


def equipment_scope_clause(scope: str) -> tuple[str, tuple[str, ...]]:
    from health_tracker.services.records import equipment_scope_clause as build_equipment_scope_clause

    return build_equipment_scope_clause(scope, current_local_date(), week_start_for_date, shift_month)


def paged_equipment_summary(
    scope: str = "month",
    sort: str = "sets",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object, str]:
    return paged_equipment_summary_from_db(
        get_db(),
        scope,
        sort,
        page,
        per_page,
        current_local_date(),
        week_start_for_date,
        shift_month,
    )


def paged_equipment_detail(
    equipment: str,
    scope: str = "month",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object]:
    return paged_equipment_detail_from_db(
        get_db(),
        equipment,
        scope,
        page,
        per_page,
        current_local_date(),
        week_start_for_date,
        shift_month,
    )


def paged_equipment_daily(
    equipment: str,
    scope: str = "month",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object]:
    return paged_equipment_daily_from_db(
        get_db(),
        equipment,
        scope,
        page,
        per_page,
        current_local_date(),
        week_start_for_date,
        shift_month,
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
    return list_month_calendar_days_from_db(get_db(), month_start, shift_month)


def list_body_part_summary(scope: str, limit: int = 30, date_text: str | None = None) -> list[sqlite3.Row]:
    return list_body_part_summary_from_db(
        get_db(),
        scope,
        limit,
        date_text,
        week_start_for_date,
        meal_week_label,
        shift_date,
        normalize_month,
        shift_month,
    )


def list_weekly_body_part_details(date_text: str | None = None) -> dict[str, list[sqlite3.Row]]:
    return list_weekly_body_part_details_from_db(
        get_db(),
        date_text,
        week_start_for_date,
        meal_week_label,
        shift_date,
    )


def list_sets_for_session(session_id: int) -> list[sqlite3.Row]:
    return list_sets_for_session_from_db(get_db(), session_id)


def grouped_sets_for_session(session_id: int | None) -> list[dict[str, object]]:
    return grouped_sets_for_session_from_db(get_db(), session_id)


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
    return float(get_app_preferences()["default_body_weight_kg"])


def estimate_exercise_calories(
    body_part: str,
    cardio_incline: float | None,
    cardio_speed: float | None,
    cardio_minutes: float | None,
    workout_date: str,
) -> float | None:
    return estimate_exercise_calories_from_weight(
        body_part,
        cardio_incline,
        cardio_speed,
        cardio_minutes,
        get_body_weight_for_date(workout_date),
    )


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
