from __future__ import annotations

from health_tracker.constants import DEFAULT_REST_SECONDS, READINESS_TIERS
from health_tracker.services.today_context_coach import (
    build_daily_action_recommendations,
    build_fuel_coach,
    build_workout_execution_coach,
)


def _empty_today_context() -> dict[str, object]:
    return {
        "sessions": [],
        "exercises": [],
        "exercises_by_body_part": {},
        "recent_sets_by_exercise": {},
        "exercise_stats_by_name": {},
        "exercise_smart_defaults": {},
        "overload_suggestions": [],
        "next_set_suggestions": {},
        "exercise_notes": {},
        "exercise_settings": {},
        "exercise_goal_progress": {},
        "pr_events": [],
        "recent_pr_events": [],
        "foods_by_meal_type": {},
        "favorite_foods": [],
        "frequent_foods": [],
        "favorite_exercises": [],
        "routines": [],
        "workout_plan": [],
        "workout_completion_summary": {"body_parts": [], "top_exercise": None},
        "workout_finish_review": {
            "visible": False,
            "metrics": [],
            "insights": [],
            "next_actions": [],
            "top_parts": [],
            "top_exercises": [],
        },
        "pr_cards": [],
        "weekly_routine_recommendations": [],
        "recommended_sessions": [],
        "workout_focus_recommendations": [],
        "today_next_actions": [],
        "daily_action_recommendations": {
            "items": [],
            "badge": "완료",
            "subtitle": "",
            "is_complete": True,
            "complete_title": "오늘 핵심 기록이 채워졌습니다.",
            "complete_description": "주간 분석을 확인하거나 필요하면 휴식 메모를 남길 수 있습니다.",
            "complete_actions": [],
        },
        "today_rule_cards": [],
        "volume_warnings": [],
        "frequent_meal_combos": [],
        "default_programs": [],
        "meal_templates": [],
        "meals": [],
        "meal_groups": [],
        "workout_groups": [],
        "body_metric": None,
        "body_photos": [],
        "goals": {},
        "body_progress_insights": [],
        "data_quality_profile": {
            "score": 0,
            "label": "-",
            "tone": "low",
            "period": "",
            "message": "",
            "criteria": "",
            "components": [],
            "actions": [],
        },
        "balance_score": {"score": 0, "missing": []},
        "recovery_statuses": [],
        "recovery_checkin": None,
        "readiness_profile": {},
        "recovery_recommendations": [],
        "adaptive_training_recommendations": [],
        "nutrition_training_link": {
            "period": "",
            "workout_days": 0,
            "meal_days": 0,
            "workout_calorie_avg": 0,
            "message": "",
            "low_fuel_days": [],
        },
        "daily_coaching": [],
        "workout_execution_coach": {
            "source": "manual",
            "status": "insufficient_data",
            "selected_date": "",
            "recommended_items": [],
            "active_item": None,
            "target_sets": None,
            "target_reps": None,
            "target_weight": None,
            "rest_seconds": DEFAULT_REST_SECONDS,
            "warmup_sets": [],
            "plate_combo": [],
            "actions": {},
        },
        "fuel_coach": {
            "status": "no_workout",
            "workout_context": {},
            "calories_current": 0,
            "calories_goal": 0,
            "calories_remaining": 0,
            "protein_known": False,
            "primary_action": {},
            "combo_actions": [],
            "template_actions": [],
        },
        "workout_session_flow": {
            "next_item": None,
            "last_set": None,
            "rest_seconds": DEFAULT_REST_SECONDS,
        },
        "record_gaps": [],
        "meal_copy_sources": [],
        "location_equipment": [],
        "location_quick_exercises": [],
        "equipment_options": [],
        "has_location_equipment": False,
        "current_date": "",
    }


def build_today_context(args, deps: dict[str, object]) -> dict[str, object]:
    selected_date = deps["normalize_date"](args.get("date"))
    today_mode = args.get("mode", "overview")
    if today_mode not in {"overview", "workout", "meal"}:
        today_mode = "overview"

    workout_mode = today_mode == "workout"
    meal_mode = today_mode == "meal"
    focus_mode = workout_mode and args.get("focus") == "1"
    selected_location_id = deps["parse_int"](args.get("location_id"))
    today_session = deps["get_session_or_placeholder"](selected_date, selected_location_id)
    current_location = deps["get_workout_location"](today_session["location_id"])
    preferences = deps["get_app_preferences"]()
    context = {
        **_empty_today_context(),
        "session": today_session,
        "body_metric": deps["get_body_metric"](today_session["workout_date"]),
        "body_photos": deps["list_body_photos"](today_session["workout_date"]),
        "goals": deps["get_goal_progress"](today_session["workout_date"]),
        "today_summary": deps["get_day_summary"](today_session["workout_date"]),
        "daily_calorie_goal": deps["get_goal_value"]("daily_calories", int(preferences["default_daily_calories"])),
        "body_progress_insights": deps["build_body_progress_insights"](today_session["workout_date"]),
        "locations": deps["list_workout_locations"](),
        "current_location": current_location,
        "set_type_options": preferences["set_type_options"],
        "today_mode": today_mode,
        "workout_mode": workout_mode,
        "meal_mode": meal_mode,
        "focus_mode": focus_mode,
        "body_parts": deps["body_part_options"](),
        "prev_date": deps["shift_date"](today_session["workout_date"], -1),
        "next_date": deps["shift_date"](today_session["workout_date"], 1),
        "current_date": deps["current_local_date"](),
        "active_page": "today",
        "logging_streak": deps["build_logging_streak"](deps["current_local_date"]()),
    }

    if today_mode == "overview":
        context.update(
            {
                "sessions": deps["list_recent_sessions"](),
                "data_quality_profile": deps["build_data_quality_profile"](today_session["workout_date"]),
                "nutrition_training_link": deps["build_nutrition_training_link"]("weekly", today_session["workout_date"]),
                "record_gaps": deps["list_record_gaps"](today_session["workout_date"]),
                "balance_score": deps["get_balance_score"]("weekly", today_session["workout_date"]),
                "recovery_checkin": deps["get_recovery_checkin"](today_session["workout_date"]),
            }
        )
        context["daily_action_recommendations"] = build_daily_action_recommendations(context)

    if workout_mode:
        exercises = deps["list_exercises"](current_location["id"])
        quick_names = [row["name"] for row in exercises[:12]]
        location_equipment = deps["list_location_equipment"](current_location["id"])
        # These are each needed by 2+ of the calls below (recovery_checkin by 4,
        # workout_plan_rows by 4, balance_score by 2) — fetch once here instead
        # of letting each function re-query the same row(s) internally.
        recovery_checkin = deps["get_recovery_checkin"](today_session["workout_date"])
        readiness_profile = deps["build_readiness_profile"](today_session["workout_date"], recovery_checkin)
        workout_plan_rows = deps["list_workout_plan"](today_session["workout_date"])
        balance_score = deps["get_balance_score"]("weekly", today_session["workout_date"])
        context.update(
            {
                "exercises": exercises,
                "exercises_by_body_part": deps["list_exercises_by_body_part"](current_location["id"]),
                "recent_sets_by_exercise": deps["list_recent_sets_by_exercise"](location_id=current_location["id"]),
                "exercise_stats_by_name": deps["list_exercise_stats_by_name"](current_location["id"]),
                "exercise_smart_defaults": deps["list_exercise_smart_defaults"](current_location["id"]),
                "overload_suggestions": deps["list_overload_suggestions"](),
                "next_set_suggestions": deps["build_next_set_suggestions"](
                    quick_names, today_session["workout_date"], readiness_percent=int(readiness_profile["percent"] or 60)
                ),
                "exercise_notes": deps["list_exercise_notes"](),
                "exercise_settings": deps["list_exercise_settings"](),
                "exercise_goal_progress": deps["list_exercise_goal_progress"](),
                "pr_events": deps["list_pr_events"](today_session["workout_date"]),
                "recent_pr_events": deps["list_recent_pr_events"](limit=8),
                "favorite_exercises": deps["list_favorite_exercises"](current_location["id"]),
                "routines": deps["list_routines"](current_location["id"]),
                "workout_plan": workout_plan_rows,
                "workout_completion_summary": deps["build_workout_completion_summary"](today_session["workout_date"], workout_plan_rows),
                "workout_finish_review": deps["build_workout_finish_review"](today_session["workout_date"], workout_plan_rows),
                "pr_cards": deps["build_pr_cards"](today_session["workout_date"]),
                "weekly_routine_recommendations": deps["list_weekly_routine_recommendations"](today_session["workout_date"], balance_score),
                "recommended_sessions": deps["list_recommended_sessions"](today_session["workout_date"]),
                "workout_focus_recommendations": deps["list_workout_focus_recommendations"](today_session["workout_date"]),
                "today_next_actions": deps["list_today_next_actions"](today_session["workout_date"]),
                "today_rule_cards": deps["list_today_rule_cards"](today_session["workout_date"]),
                "volume_warnings": deps["list_volume_warnings"](today_session["workout_date"]),
                "default_programs": deps["DEFAULT_PROGRAMS"].keys(),
                "balance_score": balance_score,
                "recovery_statuses": deps["list_recovery_statuses"](today_session["workout_date"]),
                "recovery_checkin": recovery_checkin,
                "readiness_profile": readiness_profile,
                "readiness_tiers": READINESS_TIERS,
                "recovery_recommendations": deps["list_recovery_recommendations"](today_session["workout_date"]),
                "adaptive_training_recommendations": deps["build_adaptive_training_recommendations"](
                    today_session["workout_date"], checkin=recovery_checkin
                ),
                "daily_coaching": deps["list_daily_coaching"](today_session["workout_date"], recovery_checkin),
                "workout_session_flow": deps["build_workout_session_flow"](today_session["workout_date"], plan_rows=workout_plan_rows),
                "workout_groups": deps["grouped_sets_for_session"](today_session["id"]),
                "location_equipment": location_equipment,
                "location_quick_exercises": deps["list_location_quick_exercises"](current_location["id"]),
                "equipment_options": deps["equipment_options_for_location"](current_location["id"]),
                "has_location_equipment": bool(location_equipment),
            }
        )
        context["workout_execution_coach"] = build_workout_execution_coach(
            context,
            int(preferences["default_rest_seconds"]),
        )
        context["fuel_coach"] = build_fuel_coach(context, context.get("workout_plan") or [])

    if meal_mode:
        workout_plan = deps["list_workout_plan"](today_session["workout_date"])
        context.update(
            {
                "foods_by_meal_type": deps["list_foods_by_meal_type"](),
                "favorite_foods": deps["list_favorite_foods"](),
                "frequent_foods": deps["list_frequent_foods"](),
                "frequent_meal_combos": deps["list_frequent_meal_combos"](),
                "meal_templates": deps["list_meal_templates"](),
                "meals": deps["list_meals_for_date"](today_session["workout_date"]),
                "meal_groups": deps["grouped_meals_for_date"](today_session["workout_date"]),
                "meal_copy_sources": deps["list_recent_meal_days"](today_session["workout_date"]),
            }
        )
        context["fuel_coach"] = build_fuel_coach(context, workout_plan)

    return context
