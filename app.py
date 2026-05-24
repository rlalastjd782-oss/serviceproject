from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, Response, g, jsonify, redirect, render_template, request, url_for

from app_constants import (
    BODY_PART_CLASSES,
    BODY_PARTS,
    DEFAULT_BODY_WEIGHT_KG,
    DEFAULT_PROGRAMS,
    EQUIPMENT_OPTIONS,
    MEAL_TYPE_CLASSES,
    RECOMMENDED_EXERCISE_MAP,
)


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "instance" / "workout.db"
PHOTO_DIR = BASE_DIR / "static" / "progress_photos"
APP_VERSION = ""


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["DATABASE"] = DATABASE

    @app.before_request
    def before_request() -> None:
        init_db()

    @app.teardown_appcontext
    def close_db(error: Exception | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.get("/")
    def index():
        selected_date = normalize_date(request.args.get("date"))
        today_mode = request.args.get("mode", "overview")
        if today_mode not in {"overview", "workout", "meal"}:
            today_mode = "overview"
        workout_mode = today_mode == "workout"
        meal_mode = today_mode == "meal"
        today_session = get_or_create_session(selected_date)
        sessions = list_recent_sessions()
        exercises = list_exercises()
        meals = list_meals_for_date(today_session["workout_date"])
        return render_template(
            "index.html",
            session=today_session,
            sessions=sessions,
            exercises=exercises,
            exercises_by_body_part=list_exercises_by_body_part(),
            recent_sets_by_exercise=list_recent_sets_by_exercise(),
            exercise_stats_by_name=list_exercise_stats_by_name(),
            overload_suggestions=list_overload_suggestions(),
            exercise_notes=list_exercise_notes(),
            exercise_settings=list_exercise_settings(),
            pr_events=list_pr_events(today_session["workout_date"]),
            recent_pr_events=list_recent_pr_events(limit=8),
            foods_by_meal_type=list_foods_by_meal_type(),
            favorite_foods=list_favorite_foods(),
            favorite_exercises=list_favorite_exercises(),
            routines=list_routines(),
            workout_plan=list_workout_plan(today_session["workout_date"]),
            weekly_routine_recommendations=list_weekly_routine_recommendations(today_session["workout_date"]),
            recommended_sessions=list_recommended_sessions(today_session["workout_date"]),
            workout_focus_recommendations=list_workout_focus_recommendations(today_session["workout_date"]),
            default_programs=DEFAULT_PROGRAMS.keys(),
            meal_templates=list_meal_templates(),
            body_metric=get_body_metric(today_session["workout_date"]),
            body_photos=list_body_photos(today_session["workout_date"]),
            goals=get_goal_progress(today_session["workout_date"]),
            meals=meals,
            meal_groups=grouped_meals_for_date(today_session["workout_date"]),
            today_summary=get_day_summary(today_session["workout_date"]),
            daily_calorie_goal=get_goal_value("daily_calories", 2200),
            balance_score=get_balance_score("weekly", today_session["workout_date"]),
            recovery_statuses=list_recovery_statuses(today_session["workout_date"]),
            recovery_checkin=get_recovery_checkin(today_session["workout_date"]),
            recovery_recommendations=list_recovery_recommendations(today_session["workout_date"]),
            daily_coaching=list_daily_coaching(today_session["workout_date"]),
            meal_copy_sources=list_recent_meal_days(today_session["workout_date"]),
            equipment_options=equipment_options(),
            today_mode=today_mode,
            workout_mode=workout_mode,
            meal_mode=meal_mode,
            body_parts=body_part_options(),
            prev_date=shift_date(today_session["workout_date"], -1),
            next_date=shift_date(today_session["workout_date"], 1),
            active_page="today",
        )

    @app.get("/summaries")
    def summaries():
        return redirect(url_for("weekly_summary_page"))

    @app.get("/summaries/daily")
    def daily_summary_page():
        days = parse_int(request.args.get("days")) or 14
        days = min(max(days, 7), 90)
        return render_template(
            "summary_page.html",
            page_title="일간 집계",
            page_kicker="Daily",
            table_kind="daily",
            daily_summary=list_daily_summary(days=days),
            selected_days=days,
            body_part_summary=list_body_part_summary("daily"),
            active_page="daily",
        )

    @app.get("/summaries/weekly")
    def weekly_summary_page():
        selected_week = normalize_date(request.args.get("week"))
        week_start = week_start_for_date(selected_week)
        week_end = shift_date(week_start, 6)
        chart_rows = list_daily_summary(start_date=week_start, end_date=week_end)
        return render_template(
            "summary_page.html",
            page_title="주간 집계",
            page_kicker="Weekly",
            table_kind="period",
            period_rows=list_weekly_summary(),
            period_label="기간",
            chart_items=build_daily_chart(chart_rows),
            chart_title="일별 추이",
            chart_note="선택한 주를 일별로 표시합니다.",
            body_part_summary=list_body_part_summary("weekly", date_text=week_start),
            body_part_details=list_weekly_body_part_details(week_start),
            weekly_report=build_weekly_report(week_start),
            weekly_goals=get_goal_progress(week_start),
            weekly_goal_insights=build_goal_insights("weekly", week_start),
            rpe_report=build_rpe_report("weekly", week_start),
            report_insights=build_period_insights("weekly", week_start),
            period_highlights=build_period_highlights("weekly", week_start),
            balance_warnings=list_balance_warnings("weekly", week_start),
            selected_week=week_start,
            prev_week=shift_date(week_start, -7),
            next_week=shift_date(week_start, 7),
            active_page="weekly",
        )

    @app.get("/summaries/monthly")
    def monthly_summary_page():
        selected_month = request.args.get("month") or current_local_date()[:7]
        month_start = normalize_month(selected_month)
        period_rows = list_weekly_summary(month_start=month_start, limit=6)
        return render_template(
            "summary_page.html",
            page_title="월간 집계",
            page_kicker="Monthly",
            table_kind="period",
            period_rows=period_rows,
            period_label="기간",
            chart_items=build_period_chart(period_rows),
            chart_title="주간별 추이",
            chart_note="선택한 월을 주간 단위로 표시합니다.",
            body_part_summary=list_body_part_summary("monthly", date_text=month_start),
            monthly_report=build_monthly_report(month_start),
            monthly_goals=get_goal_progress(month_start),
            monthly_goal_insights=build_goal_insights("monthly", month_start),
            report_insights=build_period_insights("monthly", month_start),
            period_highlights=build_period_highlights("monthly", month_start),
            selected_month=month_start[:7],
            prev_month=shift_month(month_start, -1)[:7],
            next_month=shift_month(month_start, 1)[:7],
            active_page="monthly",
        )

    @app.get("/summaries/exercises")
    def exercise_summary_page():
        exercise_id = parse_int(request.args.get("exercise_id"))
        search_query = request.args.get("q", "").strip()
        exercise_choices = list_exercises()
        exercise_summary = list_exercise_summary()
        selected_exercise = exercise_id or (int(exercise_summary[0]["id"]) if exercise_summary else None)
        return render_template(
            "summary_page.html",
            page_title="운동별 횟수",
            page_kicker="Exercise",
            table_kind="exercise",
            exercise_summary=exercise_summary,
            body_part_exercise_summary=list_exercise_summary_by_body_part(),
            body_parts=body_part_options(),
            exercise_choices=exercise_choices,
            selected_exercise_id=selected_exercise,
            selected_exercise_profile=get_exercise_profile(selected_exercise),
            selected_exercise_next_plan=build_exercise_next_plan(selected_exercise),
            exercise_growth=build_exercise_growth_chart(selected_exercise),
            exercise_pr_history=list_exercise_pr_history(selected_exercise),
            recent_pr_events=list_recent_pr_events(limit=20),
            search_query=search_query,
            search_results=search_workout_records(search_query) if search_query else [],
            active_page="exercises",
        )

    @app.get("/summaries/equipment")
    def equipment_summary_page():
        selected_equipment = request.args.get("equipment", "").strip()
        selected_scope = request.args.get("scope", "month").strip() or "month"
        equipment_rows = list_equipment_summary(selected_scope)
        selected_equipment = selected_equipment or (equipment_rows[0]["equipment"] if equipment_rows else "")
        return render_template(
            "summary_page.html",
            page_title="장비별 기록",
            page_kicker="Equipment",
            table_kind="equipment",
            equipment_summary=equipment_rows,
            equipment_detail=list_equipment_detail(selected_equipment, selected_scope) if selected_equipment else [],
            equipment_daily=list_equipment_daily(selected_equipment, selected_scope) if selected_equipment else [],
            selected_equipment=selected_equipment,
            selected_scope=selected_scope,
            active_page="equipment",
        )

    @app.get("/calendar")
    def calendar_page():
        selected_month = request.args.get("month") or current_local_date()[:7]
        month_start = normalize_month(selected_month)
        current_date = current_local_date()
        goal_date = current_date if month_start[:7] == current_date[:7] else month_start
        return render_template(
            "calendar.html",
            month=month_start[:7],
            month_label=f"{int(month_start[5:7])}월",
            prev_month=shift_month(month_start, -1)[:7],
            next_month=shift_month(month_start, 1)[:7],
            calendar_days=list_month_calendar_days(month_start),
            goals=get_goal_progress(goal_date),
            body_metrics=list_body_metrics(month_start),
            active_page="calendar",
        )

    @app.get("/meals/weekly")
    def meal_weekly_page():
        selected_week = normalize_date(request.args.get("week"))
        week_start = week_start_for_date(selected_week)
        week_end = shift_date(week_start, 6)
        return render_template(
            "meal_weekly.html",
            week_start=week_start,
            week_end=week_end,
            prev_week=shift_date(week_start, -7),
            next_week=shift_date(week_start, 7),
            week_label=meal_week_label(week_start),
            selected_date=selected_week,
            meal_days=list_weekly_meal_days(week_start),
            meal_summary=build_weekly_meal_summary(week_start),
            meal_goals=get_goal_progress(week_start),
            active_page="meals",
        )

    @app.get("/settings")
    def settings_page():
        return render_template(
            "settings.html",
            active_page="settings",
            sample_counts=get_sample_data_counts(),
            data_counts=get_data_counts(),
            backup_status=get_backup_status(),
        )

    @app.post("/recovery-checkins")
    def save_recovery_checkin_route():
        checkin_date = normalize_date(request.form.get("checkin_date"))
        save_recovery_checkin(
            checkin_date,
            parse_int(request.form.get("condition_score")) or 3,
            parse_int(request.form.get("sleep_score")) or 3,
            parse_int(request.form.get("soreness_score")) or 3,
            parse_int(request.form.get("fatigue_score")) or 3,
            request.form.get("memo", "").strip(),
        )
        return redirect(url_for("index", date=checkin_date, mode=request.form.get("mode") or "workout"))

    @app.post("/sets")
    def create_set():
        session = get_or_create_session(request.form.get("workout_date"))
        mode = request.form.get("mode")
        body_part = request.form.get("body_part", "").strip() or "기타"
        exercise_name = request.form.get("exercise_name", "").strip()
        equipment = request.form.get("equipment", "").strip()
        if not exercise_name:
            return redirect(url_for("index", date=session["workout_date"], mode=mode or None))

        set_weights = request.form.getlist("set_weight") or [request.form.get("weight", "")]
        set_reps = request.form.getlist("set_reps") or [request.form.get("reps", "")]
        cardio_inclines = request.form.getlist("cardio_incline") or [request.form.get("cardio_incline", "")]
        cardio_speeds = request.form.getlist("cardio_speed") or [request.form.get("cardio_speed", "")]
        cardio_minutes = request.form.getlist("cardio_minutes") or [request.form.get("cardio_minutes", "")]
        set_memos = request.form.getlist("set_memo") or [request.form.get("memo", "")]
        set_types = request.form.getlist("set_type") or [request.form.get("set_type", "본세트")]
        set_rpes = request.form.getlist("set_rpe") or [request.form.get("rpe", "")]
        set_count = max(
            len(set_weights),
            len(set_reps),
            len(cardio_inclines),
            len(cardio_speeds),
            len(cardio_minutes),
            len(set_memos),
            len(set_types),
            len(set_rpes),
        )
        set_rows = []
        for index in range(set_count):
            weight_value = value_at(set_weights, index)
            reps_value = value_at(set_reps, index)
            incline_value = value_at(cardio_inclines, index)
            speed_value = value_at(cardio_speeds, index)
            minutes_value = value_at(cardio_minutes, index)
            memo_value = value_at(set_memos, index).strip()
            set_type = value_at(set_types, index).strip() or "본세트"
            rpe_value = value_at(set_rpes, index)
            is_cardio = body_part == "유산소"
            if (
                weight_value.strip() == ""
                and reps_value.strip() == ""
                and incline_value.strip() == ""
                and speed_value.strip() == ""
                and minutes_value.strip() == ""
                and memo_value == ""
            ):
                continue
            set_rows.append(
                (
                    None if is_cardio else parse_float(weight_value),
                    None if is_cardio else parse_int(reps_value),
                    parse_float(incline_value) if is_cardio else None,
                    parse_float(speed_value) if is_cardio else None,
                    parse_float(minutes_value) if is_cardio else None,
                    memo_value,
                    "유산소" if is_cardio else set_type,
                    parse_float(rpe_value),
                )
            )

        if not set_rows:
            return redirect(url_for("index", date=session["workout_date"], mode=mode or None))

        db = get_db()
        exercise_id = get_or_create_exercise(exercise_name)
        if equipment:
            save_exercise_equipment(exercise_name, equipment)
        previous_records = get_exercise_record_values(exercise_id)
        next_order = db.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workout_sets WHERE session_id = ?",
            (session["id"],),
        ).fetchone()[0]
        for offset, (weight, reps, cardio_incline, cardio_speed, cardio_minutes_value, memo, set_type, rpe) in enumerate(set_rows):
            estimated_calories = estimate_exercise_calories(
                body_part,
                cardio_incline,
                cardio_speed,
                cardio_minutes_value,
                session["workout_date"],
            )
            cursor = db.execute(
                """
                INSERT INTO workout_sets (
                    session_id, exercise_id, weight, reps, cardio_incline, cardio_speed,
                    cardio_minutes, estimated_calories, memo, sort_order, body_part, set_type, rpe, equipment
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session["id"],
                    exercise_id,
                    weight,
                    reps,
                    cardio_incline,
                    cardio_speed,
                    cardio_minutes_value,
                    estimated_calories,
                    memo,
                    next_order + offset,
                    body_part,
                    set_type,
                    rpe,
                    equipment[:20],
                ),
            )
            if body_part != "유산소":
                record_pr_events(cursor.lastrowid, session["workout_date"], exercise_id, exercise_name, weight, reps, previous_records)
                previous_records = update_record_values(previous_records, weight, reps)
        db.commit()
        rest_seconds = get_exercise_rest_seconds(exercise_name)
        return redirect(url_for("index", date=session["workout_date"], mode=mode or None, rest=rest_seconds if mode == "workout" else None))

    @app.post("/routines/from-day")
    def create_routine_from_day():
        workout_date = normalize_date(request.form.get("workout_date"))
        mode = request.form.get("mode")
        routine_name = request.form.get("routine_name", "").strip() or f"{workout_date} 루틴"
        session = get_session_by_date(workout_date)
        if session and session["id"]:
            create_routine_template(routine_name, int(session["id"]))
        return redirect(url_for("index", date=workout_date, mode=mode or None))

    @app.post("/routines/<int:routine_id>/apply")
    def apply_routine(routine_id: int):
        workout_date = normalize_date(request.form.get("workout_date"))
        mode = request.form.get("mode")
        apply_routine_template(routine_id, workout_date)
        return redirect(url_for("index", date=workout_date, mode=mode or None))

    @app.post("/routines/<int:routine_id>/update")
    def update_routine(routine_id: int):
        workout_date = normalize_date(request.form.get("workout_date"))
        mode = request.form.get("mode")
        name = request.form.get("routine_name", "").strip()
        if name:
            rename_routine_template(routine_id, name)
        return redirect(url_for("index", date=workout_date, mode=mode or None))

    @app.post("/routines/<int:routine_id>/delete")
    def delete_routine(routine_id: int):
        workout_date = normalize_date(request.form.get("workout_date"))
        mode = request.form.get("mode")
        delete_routine_template(routine_id)
        return redirect(url_for("index", date=workout_date, mode=mode or None))

    @app.post("/plans")
    def create_plan_item_route():
        workout_date = normalize_date(request.form.get("workout_date"))
        body_part = request.form.get("body_part", "").strip() or "기타"
        exercise_name = request.form.get("exercise_name", "").strip()
        target_sets = parse_int(request.form.get("target_sets")) or 3
        if exercise_name:
            create_workout_plan_item(workout_date, body_part, exercise_name, target_sets)
        return redirect(url_for("index", date=workout_date, mode="workout"))

    @app.post("/plans/<int:item_id>/delete")
    def delete_plan_item_route(item_id: int):
        workout_date = normalize_date(request.form.get("workout_date"))
        delete_workout_plan_item(item_id)
        return redirect(url_for("index", date=workout_date, mode="workout"))

    @app.post("/plans/from-recommendation")
    def add_recommendation_plan_route():
        workout_date = normalize_date(request.form.get("workout_date"))
        body_part = request.form.get("body_part", "").strip() or "기타"
        for exercise_name in request.form.getlist("exercise_name"):
            exercise_name = exercise_name.strip()
            if exercise_name:
                create_workout_plan_item(workout_date, body_part, exercise_name, 3)
        return redirect(url_for("index", date=workout_date, mode="workout"))

    @app.post("/exercise-settings")
    def save_exercise_settings_route():
        workout_date = normalize_date(request.form.get("workout_date"))
        exercise_name = request.form.get("exercise_name", "").strip()
        if exercise_name:
            save_exercise_settings(
                exercise_name,
                parse_int(request.form.get("rest_seconds")) or 90,
                request.form.get("is_favorite") == "1",
                request.form.get("equipment", "").strip(),
            )
        return redirect(url_for("index", date=workout_date, mode="workout"))

    @app.post("/sessions/<int:source_session_id>/apply")
    def apply_session(source_session_id: int):
        workout_date = normalize_date(request.form.get("workout_date"))
        mode = request.form.get("mode")
        apply_session_template(source_session_id, workout_date)
        return redirect(url_for("index", date=workout_date, mode=mode or None))

    @app.post("/sessions/<int:session_id>/complete")
    def toggle_session_complete(session_id: int):
        session = get_session_by_id(session_id)
        if not session:
            return redirect(url_for("index"))
        mode = request.form.get("mode")
        mark_session_completed(session_id, request.form.get("completed") == "1")
        return redirect(url_for("index", date=session["workout_date"], mode=mode or None))

    @app.post("/sessions/<int:session_id>/duration")
    def update_session_duration_route(session_id: int):
        session = get_session_by_id(session_id)
        if not session:
            if request.is_json:
                return jsonify({"ok": False, "error": "session_not_found"}), 404
            return redirect(url_for("index"))

        if request.is_json:
            payload = request.get_json(silent=True) or {}
            duration_seconds = parse_int(str(payload.get("duration_seconds", ""))) or 0
        else:
            if request.form.get("action") == "reset":
                duration_seconds = 0
            else:
                duration_seconds = parse_duration_seconds(
                    request.form.get("duration_hours"),
                    request.form.get("duration_minutes"),
                )

        duration_seconds = max(0, duration_seconds)
        update_session_duration(session_id, duration_seconds)
        if request.is_json:
            return jsonify(
                {
                    "ok": True,
                    "duration_seconds": duration_seconds,
                    "duration_text": format_duration(duration_seconds),
                }
            )
        mode = request.form.get("mode")
        route_args = {"date": session["workout_date"]}
        if mode:
            route_args["mode"] = mode
        return redirect(url_for("index", **route_args))

    @app.post("/goals")
    def update_goals():
        target_date = normalize_date(request.form.get("target_date"))
        scope = request.form.get("scope", "today")
        if scope == "weekly":
            save_goal("weekly_workout_days", parse_int(request.form.get("weekly_workout_days")) or 0)
            save_goal("weekly_meal_days", parse_int(request.form.get("weekly_meal_days")) or 0)
            if "weekly_calories" in request.form:
                save_goal("weekly_calories", parse_int(request.form.get("weekly_calories")) or 0)
            return redirect(url_for("weekly_summary_page", week=target_date))
        if scope == "weekly_meals":
            save_goal("weekly_meal_days", parse_int(request.form.get("weekly_meal_days")) or 0)
            save_goal("weekly_calories", parse_int(request.form.get("weekly_calories")) or 0)
            return redirect(url_for("meal_weekly_page", week=target_date))
        if scope == "daily_meals":
            save_goal("daily_calories", parse_int(request.form.get("daily_calories")) or 0)
            return redirect(url_for("index", date=target_date, mode="meal"))
        if scope == "monthly":
            save_goal("monthly_volume", parse_int(request.form.get("monthly_volume")) or 0)
            save_goal("monthly_workout_days", parse_int(request.form.get("monthly_workout_days")) or 0)
            save_goal("monthly_cardio_minutes", parse_int(request.form.get("monthly_cardio_minutes")) or 0)
            return redirect(url_for("monthly_summary_page", month=target_date[:7]))
        return redirect(url_for("index", date=target_date))

    @app.post("/exercise-notes")
    def update_exercise_note():
        target_date = normalize_date(request.form.get("target_date"))
        mode = request.form.get("mode")
        exercise_name = request.form.get("exercise_name", "").strip()
        note = request.form.get("note", "").strip()
        if exercise_name:
            save_exercise_note(exercise_name, note)
        return redirect(url_for("index", date=target_date, mode=mode or None))

    @app.post("/body-metrics")
    def save_body_metric_route():
        target_date = normalize_date(request.form.get("metric_date"))
        save_body_metric(
            target_date,
            parse_float(request.form.get("body_weight")),
            parse_float(request.form.get("muscle_mass")),
            parse_float(request.form.get("body_fat")),
            parse_float(request.form.get("waist")),
        )
        return redirect(url_for("index", date=target_date))

    @app.post("/body-photos")
    def save_body_photo_route():
        photo_date = normalize_date(request.form.get("photo_date"))
        file = request.files.get("photo")
        if file and file.filename:
            save_body_photo(photo_date, file)
        return redirect(url_for("index", date=photo_date))

    @app.post("/meal-templates/from-day")
    def create_meal_template_from_day_route():
        meal_date = normalize_date(request.form.get("meal_date"))
        mode = request.form.get("mode")
        template_name = request.form.get("template_name", "").strip() or f"{meal_date} 식단"
        create_meal_template_from_day(template_name, meal_date)
        return redirect(url_for("index", date=meal_date, mode=mode or None))

    @app.post("/meal-templates/<int:template_id>/apply")
    def apply_meal_template_route(template_id: int):
        meal_date = normalize_date(request.form.get("meal_date"))
        mode = request.form.get("mode")
        apply_meal_template(template_id, meal_date)
        return redirect(url_for("index", date=meal_date, mode=mode or None))

    @app.post("/food-favorites")
    def save_food_favorite_route():
        meal_date = normalize_date(request.form.get("meal_date"))
        food_name = request.form.get("food_name", "").strip()
        if food_name:
            save_food_favorite(
                food_name,
                parse_float(request.form.get("quantity")),
                parse_float(request.form.get("grams")),
                parse_float(request.form.get("calories")),
            )
        return redirect(url_for("index", date=meal_date, mode="meal"))

    @app.post("/food-favorites/<path:food_name>/delete")
    def delete_food_favorite_route(food_name: str):
        meal_date = normalize_date(request.form.get("meal_date"))
        delete_food_favorite(food_name)
        return redirect(url_for("index", date=meal_date, mode="meal"))

    @app.post("/meals/copy-day")
    def copy_meal_day_route():
        source_date = normalize_optional_date(request.form.get("source_date"))
        meal_date = normalize_date(request.form.get("meal_date"))
        mode = request.form.get("mode")
        if source_date:
            copy_meals_from_day(source_date, meal_date)
        return redirect(url_for("index", date=meal_date, mode=mode or None))

    @app.post("/programs/apply")
    def apply_program_route():
        workout_date = normalize_date(request.form.get("workout_date"))
        apply_default_program(request.form.get("program_name", ""), workout_date)
        return redirect(url_for("index", date=workout_date, mode=request.form.get("mode") or None))

    @app.get("/export.json")
    def export_json():
        payload = export_all_data()
        return Response(
            json.dumps(payload, ensure_ascii=False, indent=2),
            content_type="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=health-tracker-export.json"},
        )

    @app.get("/export.csv")
    def export_csv():
        return Response(
            export_workout_csv(),
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=health-tracker-workouts.csv"},
        )

    @app.post("/import.json")
    def import_json():
        file = request.files.get("backup_file")
        if file:
            import_all_data(json.loads(file.read().decode("utf-8")))
        return redirect(url_for("settings_page"))

    @app.post("/samples/delete")
    def delete_sample_data_route():
        delete_sample_data()
        return redirect(url_for("settings_page"))

    @app.post("/data/delete-all")
    def delete_all_data_route():
        delete_all_data()
        return redirect(url_for("settings_page"))

    @app.post("/meals")
    def create_meal():
        meal_date = normalize_date(request.form.get("meal_date"))
        mode = request.form.get("mode")
        meal_type = request.form.get("meal_type", "").strip()
        food_names = request.form.getlist("meal_food_name") or [request.form.get("food_name", "")]
        quantities = request.form.getlist("meal_quantity") or [request.form.get("amount", "")]
        grams_values = request.form.getlist("meal_grams") or [request.form.get("grams", "")]
        calories_values = request.form.getlist("meal_calories") or [request.form.get("calories", "")]
        memos = request.form.getlist("meal_memo") or [request.form.get("memo", "")]
        row_count = max(
            len(food_names),
            len(quantities),
            len(grams_values),
            len(calories_values),
            len(memos),
        )
        meal_rows = []
        for index in range(row_count):
            food_name = value_at(food_names, index).strip()
            quantity = value_at(quantities, index)
            grams = value_at(grams_values, index)
            calories = value_at(calories_values, index)
            memo = value_at(memos, index).strip()
            if food_name == "" and quantity.strip() == "" and grams.strip() == "" and calories.strip() == "" and memo == "":
                continue
            if food_name == "":
                continue
            meal_rows.append(
                (
                    food_name,
                    parse_float(quantity),
                    parse_float(grams),
                    parse_float(calories),
                    memo,
                )
            )

        if not meal_rows:
            return redirect(url_for("index", date=meal_date, mode=mode or None))

        db = get_db()
        for food_name, quantity, grams, calories, memo in meal_rows:
            db.execute(
                """
                INSERT INTO meal_entries
                    (meal_date, meal_type, food_name, quantity, grams, calories, memo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (meal_date, meal_type, food_name, quantity, grams, calories, memo),
            )
        db.commit()
        return redirect(url_for("index", date=meal_date, mode=mode or None))

    @app.post("/meals/<int:meal_id>/update")
    def update_meal(meal_id: int):
        db = get_db()
        meal = db.execute("SELECT meal_date FROM meal_entries WHERE id = ?", (meal_id,)).fetchone()
        meal_date = meal["meal_date"] if meal else current_local_date()
        mode = request.form.get("mode")
        food_name = request.form.get("food_name", "").strip()
        if food_name:
            db.execute(
                """
                UPDATE meal_entries
                SET food_name = ?, quantity = ?, grams = ?, calories = ?
                WHERE id = ?
                """,
                (
                    food_name,
                    parse_float(request.form.get("quantity")),
                    parse_float(request.form.get("grams")),
                    parse_float(request.form.get("calories")),
                    meal_id,
                ),
            )
            db.commit()
        return redirect(url_for("index", date=meal_date, mode=mode or None))

    @app.post("/meals/<int:meal_id>/delete")
    def delete_meal(meal_id: int):
        db = get_db()
        meal = db.execute("SELECT meal_date FROM meal_entries WHERE id = ?", (meal_id,)).fetchone()
        mode = request.form.get("mode")
        db.execute("DELETE FROM meal_entries WHERE id = ?", (meal_id,))
        db.commit()
        return redirect(url_for("index", date=meal["meal_date"] if meal else None, mode=mode or None))

    @app.post("/sets/<int:set_id>/update")
    def update_set(set_id: int):
        db = get_db()
        workout = db.execute(
            """
            SELECT s.workout_date, ws.body_part
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            WHERE ws.id = ?
            """,
            (set_id,),
        ).fetchone()
        workout_date = workout["workout_date"] if workout else current_local_date()
        mode = request.form.get("mode")
        equipment = request.form.get("equipment", "").strip()
        if workout and workout["body_part"] == "유산소":
            cardio_incline = parse_float(request.form.get("cardio_incline"))
            cardio_speed = parse_float(request.form.get("cardio_speed"))
            cardio_minutes = parse_float(request.form.get("cardio_minutes"))
            db.execute(
                """
                UPDATE workout_sets
                SET cardio_incline = ?, cardio_speed = ?, cardio_minutes = ?, estimated_calories = ?, rpe = ?, equipment = ?
                WHERE id = ?
                """,
                (
                    cardio_incline,
                    cardio_speed,
                    cardio_minutes,
                    estimate_exercise_calories("유산소", cardio_incline, cardio_speed, cardio_minutes, workout_date),
                    parse_float(request.form.get("rpe")),
                    equipment[:20],
                    set_id,
                ),
            )
        else:
            db.execute(
                """
                UPDATE workout_sets
                SET weight = ?, reps = ?, set_type = ?, rpe = ?, equipment = ?
                WHERE id = ?
                """,
                (
                    parse_float(request.form.get("weight")),
                    parse_int(request.form.get("reps")),
                    request.form.get("set_type", "본세트").strip() or "본세트",
                    parse_float(request.form.get("rpe")),
                    equipment[:20],
                    set_id,
                ),
            )
        requested_set_number = parse_int(request.form.get("set_number"))
        if requested_set_number:
            reorder_set_within_exercise(db, set_id, requested_set_number)
        db.commit()
        return redirect(url_for("index", date=workout_date, mode=mode or None))

    @app.post("/sets/<int:set_id>/delete")
    def delete_set(set_id: int):
        db = get_db()
        workout = db.execute(
            """
            SELECT s.workout_date
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            WHERE ws.id = ?
            """,
            (set_id,),
        ).fetchone()
        mode = request.form.get("mode")
        db.execute("DELETE FROM workout_sets WHERE id = ?", (set_id,))
        db.commit()
        return redirect(url_for("index", date=workout["workout_date"] if workout else None, mode=mode or None))

    @app.get("/api/sessions")
    def api_sessions():
        return jsonify([dict(row) for row in list_recent_sessions(limit=30)])

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
            rest_seconds INTEGER NOT NULL DEFAULT 90,
            is_favorite INTEGER NOT NULL DEFAULT 0,
            equipment TEXT NOT NULL DEFAULT '',
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
            memo TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    ensure_column(db, "workout_sets", "body_part", "TEXT NOT NULL DEFAULT '기타'")
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
    ensure_column(db, "routine_items", "set_type", "TEXT NOT NULL DEFAULT '본세트'")
    ensure_column(db, "routine_items", "cardio_incline", "REAL")
    ensure_column(db, "routine_items", "cardio_speed", "REAL")
    ensure_column(db, "routine_items", "cardio_minutes", "REAL")
    ensure_column(db, "routine_items", "equipment", "TEXT NOT NULL DEFAULT ''")
    ensure_column(db, "meal_entries", "quantity", "REAL")
    ensure_column(db, "meal_entries", "grams", "REAL")
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
    delete_internal_test_data()
    db.commit()


def ensure_column(db: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    columns = [row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def get_or_create_session(workout_date: str | None = None) -> sqlite3.Row:
    db = get_db()
    date_value = normalize_date(workout_date)
    existing = db.execute(
        "SELECT * FROM workout_sessions WHERE workout_date = ?",
        (date_value,),
    ).fetchone()
    if existing:
        return existing

    db.execute("INSERT INTO workout_sessions (workout_date) VALUES (?)", (date_value,))
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
        SELECT rt.id, rt.name, COUNT(ri.id) AS item_count
        FROM routine_templates rt
        LEFT JOIN routine_items ri ON ri.routine_id = rt.id
        GROUP BY rt.id
        ORDER BY rt.created_at DESC, rt.id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


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
        SELECT *
        FROM workout_plan_items
        WHERE workout_date = ?
        ORDER BY sort_order, id
        """,
        (workout_date,),
    ).fetchall()


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


def list_exercise_settings() -> dict[str, dict[str, int | bool]]:
    rows = get_db().execute("SELECT * FROM exercise_settings").fetchall()
    return {
        row["exercise_name"]: {
            "rest_seconds": int(row["rest_seconds"] or 90),
            "is_favorite": bool(row["is_favorite"]),
            "equipment": row["equipment"] or "",
        }
        for row in rows
    }


def save_exercise_settings(exercise_name: str, rest_seconds: int, is_favorite: bool, equipment: str = "") -> None:
    get_db().execute(
        """
        INSERT INTO exercise_settings (exercise_name, rest_seconds, is_favorite, equipment, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(exercise_name) DO UPDATE SET
            rest_seconds = excluded.rest_seconds,
            is_favorite = excluded.is_favorite,
            equipment = excluded.equipment,
            updated_at = CURRENT_TIMESTAMP
        """,
        (exercise_name, max(15, min(600, int(rest_seconds or 90))), 1 if is_favorite else 0, equipment[:20]),
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


def build_weekly_report(date_text: str | None = None) -> dict[str, object]:
    week_start = week_start_for_date(date_text or current_local_date())
    week_end = shift_date(week_start, 6)
    db = get_db()
    totals = db.execute(
        """
        SELECT
            COUNT(DISTINCT s.workout_date) AS workout_days,
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
        "SELECT COALESCE(SUM(duration_seconds), 0) AS duration_seconds FROM workout_sessions WHERE workout_date BETWEEN ? AND ?",
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
            COUNT(DISTINCT s.workout_date) AS workout_days,
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
        "SELECT COALESCE(SUM(duration_seconds), 0) AS duration_seconds FROM workout_sessions WHERE workout_date >= ? AND workout_date < ?",
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
        message = "RPE 기록이 아직 적습니다."
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
    db = get_db()
    return {
        "workouts": db.execute("SELECT COUNT(*) FROM workout_sessions").fetchone()[0],
        "sets": db.execute("SELECT COUNT(*) FROM workout_sets").fetchone()[0],
        "meals": db.execute("SELECT COUNT(*) FROM meal_entries").fetchone()[0],
        "routines": db.execute("SELECT COUNT(*) FROM routine_templates").fetchone()[0],
        "meal_templates": db.execute("SELECT COUNT(*) FROM meal_templates").fetchone()[0],
        "recovery": db.execute("SELECT COUNT(*) FROM recovery_checkins").fetchone()[0],
    }


def get_backup_status() -> dict[str, str]:
    backup_dirs = [BASE_DIR / "instance" / "delete_backups", BASE_DIR / "instance" / "restore_backups"]
    files = []
    for backup_dir in backup_dirs:
        if backup_dir.exists():
            files.extend(path for path in backup_dir.glob("*.json") if path.is_file())
    if not files:
        return {"last_backup": "없음", "count": "0"}
    latest = max(files, key=lambda path: path.stat().st_mtime)
    return {"last_backup": latest.name, "count": str(len(files))}


def get_sample_data_counts() -> dict[str, int]:
    db = get_db()
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
    db = get_db()
    tables = [
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
    return {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "tables": {table: [dict(row) for row in db.execute(f"SELECT * FROM {table}").fetchall()] for table in tables},
    }


def export_workout_csv() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "body_part", "exercise", "set_type", "weight", "reps", "incline", "speed", "minutes", "estimated_calories", "rpe"])
    rows = get_db().execute(
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
    return get_db().execute(
        """
        SELECT *
        FROM meal_entries
        WHERE meal_date = ?
        ORDER BY created_at DESC, id DESC
        """,
        (meal_date,),
    ).fetchall()


def grouped_meals_for_date(meal_date: str) -> list[dict[str, object]]:
    rows = get_db().execute(
        """
        SELECT *
        FROM meal_entries
        WHERE meal_date = ?
        ORDER BY
            CASE meal_type
                WHEN '아침' THEN 1
                WHEN '점심' THEN 2
                WHEN '저녁' THEN 3
                WHEN '간식' THEN 4
                ELSE 5
            END,
            id
        """,
        (meal_date,),
    ).fetchall()
    groups: list[dict[str, object]] = []
    group_by_type: dict[str, dict[str, object]] = {}
    for item in rows:
        meal_type = item["meal_type"] or "식사"
        if meal_type not in group_by_type:
            group = {"meal_type": meal_type, "entries": []}
            group_by_type[meal_type] = group
            groups.append(group)
        group_by_type[meal_type]["entries"].append(item)
    return groups


def list_weekly_meal_days(week_start: str) -> list[dict[str, object]]:
    week_end = shift_date(week_start, 6)
    rows = get_db().execute(
        """
        SELECT *
        FROM meal_entries
        WHERE meal_date BETWEEN ? AND ?
        ORDER BY meal_date ASC,
            CASE meal_type
                WHEN '아침' THEN 1
                WHEN '점심' THEN 2
                WHEN '저녁' THEN 3
                WHEN '간식' THEN 4
                ELSE 5
            END,
            created_at ASC,
            id ASC
        """,
        (week_start, week_end),
    ).fetchall()
    rows_by_date: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        rows_by_date.setdefault(row["meal_date"], []).append(row)

    days = []
    for offset in range(7):
        date_value = shift_date(week_start, offset)
        entries = rows_by_date.get(date_value, [])
        days.append(
            {
                "date": date_value,
                "label": meal_day_label(date_value),
                "entry_rows": entries,
                "meal_count": len(entries),
                "calories": sum(float(entry["calories"] or 0) for entry in entries),
            }
        )
    return days


def build_weekly_meal_summary(week_start: str) -> dict[str, object]:
    week_end = shift_date(week_start, 6)
    totals = get_db().execute(
        """
        SELECT
            COUNT(DISTINCT meal_date) AS meal_days,
            COUNT(id) AS meal_count,
            COALESCE(SUM(calories), 0) AS calories,
            COALESCE(SUM(grams), 0) AS grams
        FROM meal_entries
        WHERE meal_date BETWEEN ? AND ?
        """,
        (week_start, week_end),
    ).fetchone()
    top_food = get_db().execute(
        """
        SELECT food_name, COUNT(id) AS count
        FROM meal_entries
        WHERE meal_date BETWEEN ? AND ?
        GROUP BY food_name
        ORDER BY count DESC, food_name
        LIMIT 1
        """,
        (week_start, week_end),
    ).fetchone()
    meal_days = int(totals["meal_days"] or 0)
    calories = float(totals["calories"] or 0)
    return {
        "meal_days": meal_days,
        "meal_count": int(totals["meal_count"] or 0),
        "calories": calories,
        "grams": float(totals["grams"] or 0),
        "avg_calories": round(calories / meal_days) if meal_days else 0,
        "top_food": top_food["food_name"] if top_food else "-",
        "top_food_count": int(top_food["count"] or 0) if top_food else 0,
    }


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
                COUNT(DISTINCT s.workout_date) AS workout_days,
                COUNT(ws.id) AS set_count,
                COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
                COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
                COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
                COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories
            FROM workout_sessions s
            LEFT JOIN workout_sets ws ON ws.session_id = s.id
            {workout_where}
            GROUP BY month_key, week_of_month
        ),
        workout_time AS (
            SELECT
                strftime('%Y-%m', workout_date) AS month_key,
                CAST(strftime('%m', workout_date) AS INTEGER) AS month_number,
                ((CAST(strftime('%d', workout_date) AS INTEGER) - 1) / 7) + 1 AS week_of_month,
                COALESCE(SUM(duration_seconds), 0) AS duration_seconds
            FROM workout_sessions
            {workout_where.replace("s.workout_date", "workout_date")}
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
    ordered_rows = list(reversed(rows))
    max_volume = max([float(row["volume"]) for row in ordered_rows] + [1.0])
    max_grams = max([float(row["grams"]) for row in ordered_rows] + [1.0])
    max_exercise_calories = max([float(row["exercise_calories"]) for row in ordered_rows] + [1.0])
    max_sets = max([int(row["set_count"]) for row in ordered_rows] + [1])
    max_duration = max([int(row["duration_seconds"]) for row in ordered_rows] + [1])
    return [
        {
            "period": row["period"],
            "volume": float(row["volume"]),
            "grams": float(row["grams"]),
            "exercise_calories": float(row["exercise_calories"]),
            "duration_seconds": int(row["duration_seconds"]),
            "set_count": int(row["set_count"]),
            "workout_days": int(row["workout_days"]),
            "meal_count": int(row["meal_count"]),
            "volume_height": max(3, round(float(row["volume"]) / max_volume * 100)),
            "volume_width": round(float(row["volume"]) / max_volume * 100),
            "grams_height": max(3, round(float(row["grams"]) / max_grams * 100)),
            "grams_width": round(float(row["grams"]) / max_grams * 100),
            "exercise_calorie_height": max(3, round(float(row["exercise_calories"]) / max_exercise_calories * 100)),
            "exercise_calorie_width": round(float(row["exercise_calories"]) / max_exercise_calories * 100),
            "set_height": max(3, round(int(row["set_count"]) / max_sets * 100)),
            "set_width": round(int(row["set_count"]) / max_sets * 100),
            "duration_width": round(int(row["duration_seconds"]) / max_duration * 100),
        }
        for row in ordered_rows
    ]


def build_daily_chart(rows: list[sqlite3.Row]) -> list[dict[str, float | int | str]]:
    ordered_rows = list(reversed(rows))
    max_volume = max([float(row["volume"]) for row in ordered_rows] + [1.0])
    max_grams = max([float(row["grams"]) for row in ordered_rows] + [1.0])
    max_exercise_calories = max([float(row["exercise_calories"]) for row in ordered_rows] + [1.0])
    max_sets = max([int(row["set_count"]) for row in ordered_rows] + [1])
    max_duration = max([int(row["duration_seconds"]) for row in ordered_rows] + [1])
    return [
        {
            "period": row["period"],
            "volume": float(row["volume"]),
            "grams": float(row["grams"]),
            "exercise_calories": float(row["exercise_calories"]),
            "duration_seconds": int(row["duration_seconds"]),
            "set_count": int(row["set_count"]),
            "workout_days": 1 if int(row["set_count"]) > 0 else 0,
            "meal_count": int(row["meal_count"]),
            "volume_height": max(3, round(float(row["volume"]) / max_volume * 100)),
            "volume_width": round(float(row["volume"]) / max_volume * 100),
            "grams_height": max(3, round(float(row["grams"]) / max_grams * 100)),
            "grams_width": round(float(row["grams"]) / max_grams * 100),
            "exercise_calorie_height": max(3, round(float(row["exercise_calories"]) / max_exercise_calories * 100)),
            "exercise_calorie_width": round(float(row["exercise_calories"]) / max_exercise_calories * 100),
            "set_height": max(3, round(int(row["set_count"]) / max_sets * 100)),
            "set_width": round(int(row["set_count"]) / max_sets * 100),
            "duration_width": round(int(row["duration_seconds"]) / max_duration * 100),
        }
        for row in ordered_rows
    ]


def list_exercise_summary(limit: int = 20) -> list[sqlite3.Row]:
    return get_db().execute(
        """
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
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        GROUP BY e.id, e.name, body_part
        ORDER BY set_count DESC, rep_count DESC, e.name
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


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


def list_equipment_summary(scope: str = "month") -> list[sqlite3.Row]:
    where_sql, params = equipment_scope_clause(scope)
    return get_db().execute(
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
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        WHERE 1 = 1 {where_sql}
        GROUP BY 1
        ORDER BY set_count DESC, volume DESC, last_date DESC, 1
        """,
        params,
    ).fetchall()


def list_equipment_detail(equipment: str, scope: str = "month") -> list[sqlite3.Row]:
    where_sql, params = equipment_scope_clause(scope)
    return get_db().execute(
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
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        WHERE COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') = ?
          {where_sql}
        GROUP BY body_part, e.name
        ORDER BY set_count DESC, volume DESC, last_date DESC, exercise_name
        """,
        (equipment, *params),
    ).fetchall()


def list_equipment_daily(equipment: str, scope: str = "month") -> list[sqlite3.Row]:
    where_sql, params = equipment_scope_clause(scope)
    return get_db().execute(
        f"""
        SELECT
            s.workout_date,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        WHERE COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') = ?
          {where_sql}
        GROUP BY s.workout_date
        ORDER BY s.workout_date DESC
        LIMIT 30
        """,
        (equipment, *params),
    ).fetchall()


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


def search_workout_records(query: str, limit: int = 50) -> list[sqlite3.Row]:
    like_query = f"%{query}%"
    return get_db().execute(
        """
        SELECT
            s.workout_date,
            e.name AS exercise_name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.estimated_calories
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE e.name LIKE ? OR ws.body_part LIKE ?
        ORDER BY s.workout_date DESC, ws.sort_order ASC, ws.id ASC
        LIMIT ?
        """,
        (like_query, like_query, limit),
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
    elif scope == "weekly":
        period_expr = (
            "CAST(strftime('%m', s.workout_date) AS INTEGER) || '월 ' || "
            "(((CAST(strftime('%d', s.workout_date) AS INTEGER) - 1) / 7) + 1) || '주차'"
        )
        if date_text:
            week_start = week_start_for_date(date_text)
            period_expr = f"'{meal_week_label(week_start)}'"
            where_clause = "WHERE s.workout_date BETWEEN ? AND ?"
            params.extend([week_start, shift_date(week_start, 6)])
    else:
        period_expr = "strftime('%Y-%m', s.workout_date)"
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
        ORDER BY
            CASE body_part
                WHEN '하체' THEN 1
                WHEN '등' THEN 2
                WHEN '어깨' THEN 3
                WHEN '가슴' THEN 4
                WHEN '팔' THEN 5
                WHEN '유산소' THEN 6
                ELSE 7
            END,
            MAX(s.workout_date) DESC,
            body_part
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
    return get_db().execute(
        """
        SELECT ws.*, e.name AS exercise_name
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE ws.session_id = ?
        ORDER BY ws.sort_order, ws.id
        """,
        (session_id,),
    ).fetchall()


def grouped_sets_for_session(session_id: int | None) -> list[dict[str, object]]:
    if session_id is None:
        return []

    groups: list[dict[str, object]] = []
    group_by_name: dict[str, dict[str, object]] = {}
    for item in list_sets_for_session(int(session_id)):
        body_part = item["body_part"] or "기타"
        exercise_name = item["exercise_name"]
        group_key = f"{body_part}:{exercise_name}"
        if group_key not in group_by_name:
            group = {"body_part": body_part, "exercise_name": exercise_name, "sets": []}
            group_by_name[group_key] = group
            groups.append(group)
        group_by_name[group_key]["sets"].append(item)
    return groups


def current_local_date() -> str:
    return get_db().execute("SELECT date('now', 'localtime')").fetchone()[0]


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


def value_at(values: list[str], index: int) -> str:
    if index >= len(values):
        return ""
    return values[index] or ""


def parse_float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_duration_seconds(hours: str | None, minutes: str | None, seconds: str | None = None) -> int:
    hour_value = parse_int(hours) or 0
    minute_value = parse_int(minutes) or 0
    second_value = parse_int(seconds) or 0
    return max(0, hour_value * 3600 + minute_value * 60 + second_value)


def format_duration(seconds: int | float | None) -> str:
    total_seconds = max(0, int(seconds or 0))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    remaining_seconds = total_seconds % 60
    if hours:
        return f"{hours}시간 {minutes:02d}분 {remaining_seconds:02d}초"
    if minutes:
        return f"{minutes}분 {remaining_seconds:02d}초"
    return f"{remaining_seconds}초"


def duration_hours(seconds: int | float | None) -> int:
    return max(0, int(seconds or 0)) // 3600


def duration_minutes(seconds: int | float | None) -> int:
    return (max(0, int(seconds or 0)) % 3600) // 60


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


def get_app_version() -> str:
    env_version = os.environ.get("APP_VERSION", "").strip()
    if env_version:
        return env_version

    head_path = BASE_DIR / ".git" / "HEAD"
    try:
        head_value = head_path.read_text(encoding="utf-8").strip()
        if head_value.startswith("ref:"):
            ref_path = BASE_DIR / ".git" / head_value.split(" ", 1)[1]
            commit_hash = ref_path.read_text(encoding="utf-8").strip()
        else:
            commit_hash = head_value
        if commit_hash:
            return f"v-{commit_hash[:7]}"
    except OSError:
        pass
    return "local"


app = create_app()
APP_VERSION = get_app_version()
app.jinja_env.globals["grouped_sets_for_session"] = grouped_sets_for_session
app.jinja_env.globals["body_part_class"] = body_part_class
app.jinja_env.globals["meal_type_class"] = meal_type_class
app.jinja_env.globals["format_duration"] = format_duration
app.jinja_env.globals["duration_hours"] = duration_hours
app.jinja_env.globals["duration_minutes"] = duration_minutes
app.jinja_env.globals["app_version"] = APP_VERSION


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5000, type=int)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)
