from __future__ import annotations

import argparse
import sqlite3

from flask import Flask, g, has_request_context, jsonify, redirect, render_template, request, session, url_for
from jinja2 import FileSystemBytecodeCache

from health_tracker.app_database import configure_database_helpers, get_db, get_or_create_secret_key, init_db
from health_tracker.app_lifecycle import configure_lifecycle_hooks
from health_tracker.app_settings import (
    configure_settings_helpers,
    configured_page_params,
    get_app_preferences,
    get_app_setting,
    has_settings_password,
    normalize_summary_days,
    reset_settings_password,
    save_app_preferences,
    save_app_setting,
    set_settings_password,
    settings_unlocked,
    verify_settings_password,
)
from health_tracker.config import BASE_DIR, DATABASE, PHOTO_DIR
from health_tracker.constants import (
    BODY_PART_CLASSES,
    BODY_PARTS,
    DEFAULT_BODY_WEIGHT_KG,
    DEFAULT_DAILY_CALORIES,
    DEFAULT_REST_SECONDS,
    DEFAULT_PROGRAMS,
    EQUIPMENT_OPTIONS,
    FAVICON_CACHE_SECONDS,
    MEAL_TYPE_CLASSES,
    RECOMMENDED_EXERCISE_MAP,
    SET_TYPE_OPTIONS,
    SQLITE_BUSY_TIMEOUT_MS,
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
from health_tracker.app_accounts import (
    account_by_id,
    account_options,
    admin_audit_logs,
    build_account_usage,
    build_admin_dashboard,
    configure_account_helpers,
    create_account,
    current_account,
    ensure_default_account,
    is_admin_account,
    log_admin_action,
    mark_account_login,
    reset_user_password,
    save_user_admin_note,
    set_user_active,
    verify_account,
)
from health_tracker.app_data import (
    build_v2_readiness,
    configure_data_helpers,
    create_may_sample_data,
    delete_all_data,
    delete_empty_workout_sessions,
    delete_internal_test_data,
    delete_sample_data,
    export_all_data,
    export_meal_csv,
    export_workout_csv,
    generate_year_qa_dummy_data,
    get_app_health_status,
    get_backup_status,
    get_data_counts,
    get_data_safety_status,
    get_qa_dummy_status,
    get_sample_data_counts,
    import_all_data,
    list_duplicate_exercise_candidates,
    list_outlier_set_candidates,
)
from health_tracker.services.accounts import (
    init_accounts_db,
)
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
from health_tracker.services.deployment import build_deployment_checklist
from health_tracker.services.exercise_calorie import estimate_exercise_calories_from_weight
from health_tracker.services.exercise_settings import (
    get_exercise_rest_seconds_from_db,
    list_exercise_goal_progress_from_db,
    list_favorite_exercises_from_db,
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
from health_tracker.services.goals import (
    build_goal_progress_from_db,
    get_goal_value_from_db,
    goal_item as build_goal_item,
    save_goal_to_db,
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
from health_tracker.services.location_insights import (
    list_location_quick_exercises_from_db,
    list_location_training_insights_from_db,
)
from health_tracker.services.food_shortcuts import (
    delete_food_favorite_from_db,
    list_favorite_foods_from_db,
    list_foods_by_meal_type_from_db,
    list_frequent_foods_from_db,
    save_food_favorite_to_db,
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
    build_next_actions_from_db,
)
from health_tracker.services.pagination import build_pagination
from health_tracker.services.performance import build_page_timing_snapshot, build_performance_snapshot, run_database_analyze
from health_tracker.services.progressive_overload import (
    build_next_set_suggestions as build_next_set_suggestions_from_db,
    list_overload_suggestions_from_db,
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
from health_tracker.services.source_audit import list_long_source_files
from health_tracker.services.reminders import (
    list_reminder_settings_from_db,
    save_reminder_settings_to_db,
)
from health_tracker.services.summary import (
    build_daily_chart_from_rows,
    build_period_chart_from_rows,
    get_day_summary_from_db,
    list_daily_summary_from_db,
    list_weekly_summary_from_db,
)
from health_tracker.services.smart_workout import list_exercise_smart_defaults_from_db
from health_tracker.services.workout import (
    get_or_create_exercise_in_db,
    get_or_create_session_from_db,
    get_session_by_date_from_db,
    get_session_by_id_from_db,
    grouped_sets_for_session_from_db,
    list_exercise_stats_by_name_from_db,
    list_exercises_by_body_part_from_db,
    list_exercises_from_db,
    list_recent_sessions_from_db,
    list_recent_sets_by_exercise_from_db,
    list_sets_for_session_from_db,
    mark_session_completed_in_db,
    reorder_set_within_exercise_in_db,
    update_session_duration_in_db,
)
from health_tracker.services.workout_plan import (
    apply_default_program_to_db,
    build_workout_completion_summary_from_db,
    build_workout_finish_review_from_db,
    build_workout_session_flow_from_db,
    create_workout_plan_item_in_db,
    delete_workout_plan_item_from_db,
    list_workout_plan_from_db,
)
from health_tracker.services.yearly import (
    build_yearly_export_payload,
    build_yearly_report as build_yearly_report_from_db,
    compare_yearly_reports,
    export_yearly_meal_csv as export_yearly_meal_csv_from_db,
    export_yearly_workout_csv as export_yearly_workout_csv_from_db,
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
    jinja_cache_dir = BASE_DIR / "instance" / "jinja_cache"
    jinja_cache_dir.mkdir(parents=True, exist_ok=True)
    app.jinja_env.bytecode_cache = FileSystemBytecodeCache(str(jinja_cache_dir))
    app.config["DATABASE"] = DATABASE
    app.secret_key = get_or_create_secret_key()
    configure_database_helpers(
        get_database=lambda: DATABASE,
        recalculate_missing_exercise_calories=recalculate_missing_exercise_calories,
        bootstrap_locations=bootstrap_locations,
        delete_internal_test_data=delete_internal_test_data,
    )
    configure_account_helpers(get_db, lambda: DATABASE)
    configure_settings_helpers(get_db, DATABASE)
    configure_data_helpers(
        get_db_func=get_db,
        get_database_func=lambda: DATABASE,
        get_base_dir_func=lambda: BASE_DIR,
        has_settings_password_func=has_settings_password,
        settings_unlocked_func=settings_unlocked,
        get_or_create_session_func=get_or_create_session,
        get_or_create_exercise_func=get_or_create_exercise,
        save_exercise_equipment_func=save_exercise_equipment,
        estimate_exercise_calories_func=estimate_exercise_calories,
    )
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
    )
    configure_lifecycle_hooks(
        app,
        database=DATABASE,
        current_account=current_account,
        get_app_preferences=get_app_preferences,
        is_admin_account=is_admin_account,
        settings_unlocked=settings_unlocked,
    )

    from health_tracker.routes.main import register_routes

    register_routes(app, globals())

    return app


from health_tracker.app_workout_facade import (
    apply_default_program,
    apply_routine_template,
    apply_session_template,
    build_adaptive_training_recommendations,
    build_data_quality_profile,
    build_muscle_balance,
    build_next_set_suggestions,
    build_workout_completion_summary,
    build_workout_finish_review,
    build_workout_session_flow,
    build_weekly_plan_board,
    create_routine_template,
    create_workout_plan_item,
    delete_food_favorite,
    delete_routine_template,
    delete_workout_plan_item,
    generate_weekly_plan,
    get_goal_progress,
    get_goal_value,
    get_or_create_exercise,
    get_or_create_session,
    get_session_by_date,
    get_session_by_id,
    goal_item,
    list_exercise_stats_by_name,
    list_exercises,
    list_exercises_by_body_part,
    list_favorite_foods,
    list_foods_by_meal_type,
    list_frequent_foods,
    list_progressive_overload_rows,
    list_recent_sets_by_exercise,
    list_recommended_sessions,
    list_record_gaps,
    list_reminder_settings,
    list_routines,
    list_workout_focus_recommendations,
    list_workout_plan,
    mark_session_completed,
    rename_routine_template,
    reorder_set_within_exercise,
    save_food_favorite,
    save_goal,
    save_reminder_settings,
    update_session_duration,
)


from health_tracker.app_pr_facade import (
    build_pr_cards,
    build_pr_dashboard,
    get_exercise_record_values,
    list_exercise_best_sets,
    list_exercise_pr_history,
    list_exercise_pr_summary,
    list_pr_events,
    list_pr_exercise_choices,
    list_recent_pr_events,
    list_recent_pr_events_filtered,
    record_pr_events,
    update_record_values,
)



from health_tracker.app_analysis_facade import (
    build_action_insights,
    build_body_progress_insights,
    build_data_center_status,
    build_nutrition_training_link,
    list_exercise_library,
    list_location_quick_exercises,
    list_location_training_insights,
    paged_exercise_library,
)

from health_tracker.app_exercise_settings_facade import (
    get_exercise_rest_seconds,
    list_exercise_goal_progress,
    list_exercise_notes,
    list_exercise_settings,
    list_exercise_smart_defaults,
    list_favorite_exercises,
    list_overload_suggestions,
    save_exercise_equipment,
    save_exercise_note,
    save_exercise_settings,
)


from health_tracker.app_location_facade import (
    deactivate_workout_location,
    delete_location_equipment,
    delete_unused_workout_location,
    equipment_options,
    equipment_options_for_location,
    get_recent_or_default_location,
    get_workout_location,
    list_location_equipment,
    list_workout_locations,
    save_location_equipment,
    save_workout_location,
    set_default_workout_location,
    set_workout_session_location,
)



from health_tracker.app_body_meal_facade import (
    apply_meal_template,
    build_body_monthly_report,
    copy_meal_type_from_day,
    copy_meals_from_day,
    create_meal_template_from_day,
    delete_meal_template,
    get_body_metric,
    list_body_metric_trend,
    list_body_metrics,
    list_body_photos,
    list_frequent_meal_combos,
    list_meal_templates,
    list_recent_meal_days,
    save_body_metric,
    save_body_photo,
)


from health_tracker.app_coaching_reports_facade import (
    build_monthly_report,
    build_weekly_report,
    get_balance_score,
    list_balance_warnings,
    list_volume_warnings,
)

from health_tracker.app_recovery_facade import (
    build_goal_insights,
    build_period_highlights,
    build_period_insights,
    build_readiness_profile,
    build_rpe_report,
    build_weekly_rule_report,
    get_recovery_checkin,
    list_daily_coaching,
    list_preferred_exercises_for_body_part,
    list_recovery_recommendations,
    list_recovery_statuses,
    list_today_next_actions,
    list_today_rule_cards,
    list_weekly_routine_recommendations,
    save_recovery_checkin,
    save_rest_day,
)


from health_tracker.app_summary_facade import (
    body_part_class,
    body_part_options,
    build_daily_chart,
    build_monthly_meal_summary,
    build_period_chart,
    build_weekly_meal_summary,
    build_yearly_report,
    equipment_scope_clause,
    export_yearly_meal_csv,
    export_yearly_payload,
    export_yearly_workout_csv,
    get_day_summary,
    grouped_meals_for_date,
    list_daily_summary,
    list_exercise_summary_by_body_part,
    list_meals_for_date,
    list_recent_sessions,
    list_monthly_meal_weeks,
    list_weekly_meal_days,
    list_weekly_summary,
    list_yearly_body_part_summary,
    list_yearly_month_rows,
    list_yearly_top_exercises,
    meal_type_class,
    paged_equipment_daily,
    paged_equipment_detail,
    paged_equipment_summary,
    paged_exercise_pr_summary,
    paged_exercise_summary,
    paged_rows,
    paged_search_workout_records,
    paged_search_workout_records_filtered,
)

from health_tracker.app_exercise_facade import (
    build_exercise_growth_chart,
    build_exercise_next_plan,
    build_exercise_trend_summary,
    get_exercise_profile,
    list_exercise_pr_timeline,
    list_exercise_recent_sets,
    search_workout_records_filtered,
)


from health_tracker.app_activity_facade import (
    estimate_exercise_calories,
    get_body_weight_for_date,
    grouped_sets_for_session,
    list_body_part_summary,
    list_month_calendar_days,
    list_sets_for_session,
    list_weekly_body_part_details,
    recalculate_exercise_calories_for_date,
    recalculate_missing_exercise_calories,
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
