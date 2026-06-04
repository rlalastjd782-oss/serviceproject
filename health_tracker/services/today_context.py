from __future__ import annotations


def _daily_action_item(
    source: str,
    priority: int,
    title: str,
    description: str,
    label: str,
    href: str,
    state: str = "open",
) -> dict[str, object]:
    source_labels = {
        "workout": "운동",
        "meal": "식단",
        "goal": "목표",
        "body": "체성분",
        "quality": "기록",
        "balance": "균형",
        "analysis": "분석",
    }
    return {
        "source": source,
        "source_label": source_labels.get(source, source),
        "priority": priority,
        "title": title,
        "description": description,
        "label": label,
        "href": href,
        "state": state,
    }


def _goal_shortfall(goal: dict[str, object] | None) -> int:
    if not goal:
        return 0
    target = float(goal.get("target") or 0)
    current = float(goal.get("current") or 0)
    return max(0, round(target - current))


def build_daily_action_recommendations(context: dict[str, object]) -> dict[str, object]:
    session = context["session"]
    workout_date = str(session["workout_date"])
    summary = context["today_summary"]
    goals = context.get("goals") or {}
    body_metric = context.get("body_metric")
    data_quality = context.get("data_quality_profile") or {}
    balance_score = context.get("balance_score") or {}
    recovery_checkin = context.get("recovery_checkin") or {}
    is_rest_day = bool(recovery_checkin.get("is_rest_day"))
    is_selected_today = workout_date == context.get("current_date")
    base_app_href = f"/app?date={workout_date}"
    items: list[dict[str, object]] = []

    if not is_rest_day and int(summary["set_count"] or 0) == 0:
        items.append(
            _daily_action_item(
                "workout",
                10,
                "오늘 운동 기록이 없습니다.",
                "첫 세트를 입력하면 오늘 기록이 시작됩니다.",
                "운동 입력",
                f"{base_app_href}&mode=workout#workout-input",
            )
        )

    if int(summary["meal_count"] or 0) == 0:
        items.append(
            _daily_action_item(
                "meal",
                20,
                "오늘 식단 기록이 없습니다.",
                "첫 식사를 입력해 섭취량을 확인합니다.",
                "식단 입력",
                f"{base_app_href}&mode=meal#meal-input",
            )
        )

    weekly_workout_goal = goals.get("weekly_workout_days") if isinstance(goals, dict) else None
    weekly_meal_goal = goals.get("weekly_meal_days") if isinstance(goals, dict) else None
    if weekly_workout_goal and int(weekly_workout_goal.get("target") or 0) <= 0:
        items.append(
            _daily_action_item(
                "goal",
                30,
                "주간 운동일 목표가 비어 있습니다.",
                "목표를 정하면 오늘 기록의 기준이 분명해집니다.",
                "목표 설정",
                "/summaries/weekly",
            )
        )
    elif weekly_meal_goal and int(weekly_meal_goal.get("target") or 0) <= 0:
        items.append(
            _daily_action_item(
                "goal",
                32,
                "주간 식단일 목표가 비어 있습니다.",
                "식단 목표를 정하면 기록 리듬을 확인하기 쉽습니다.",
                "목표 설정",
                "/summaries/weekly",
            )
        )
    else:
        workout_shortfall = _goal_shortfall(weekly_workout_goal)
        meal_shortfall = _goal_shortfall(weekly_meal_goal)
        if workout_shortfall > 0:
            items.append(
                _daily_action_item(
                    "goal",
                    31,
                    f"이번 주 운동일이 {workout_shortfall}일 부족합니다.",
                    "오늘 기록을 추가하면 목표에 가까워집니다.",
                    "목표 확인",
                    "/summaries/weekly",
                )
            )
        elif meal_shortfall > 0:
            items.append(
                _daily_action_item(
                    "goal",
                    33,
                    f"이번 주 식단 기록이 {meal_shortfall}일 부족합니다.",
                    "오늘 식사를 남기면 주간 흐름이 더 선명해집니다.",
                    "목표 확인",
                    "/summaries/weekly",
                )
            )

    if not body_metric:
        items.append(
            _daily_action_item(
                "body",
                40,
                "오늘 체성분 기록이 없습니다.",
                "체중만 입력해도 추세 확인에 도움이 됩니다.",
                "체성분 입력",
                f"{base_app_href}#body-metrics",
            )
        )

    if int(data_quality.get("score") or 0) < 55:
        items.append(
            _daily_action_item(
                "quality",
                50,
                "기록 품질이 낮습니다.",
                "누락된 날을 확인하면 분석 정확도가 올라갑니다.",
                "기록 점검",
                f"/records/check?date={workout_date}",
            )
        )

    missing_parts = [part for part in balance_score.get("missing", []) if part != "유산소"]
    if int(summary["set_count"] or 0) > 0 and missing_parts:
        items.append(
            _daily_action_item(
                "balance",
                60,
                f"{missing_parts[0]} 운동 공백이 있습니다.",
                "다음 운동 후보로 비어 있는 부위를 잡아볼 수 있습니다.",
                "운동 계획",
                f"{base_app_href}&mode=workout#workout-plan",
            )
        )

    if items and len(items) < 5 and int(data_quality.get("score") or 0) >= 55:
        items.append(
            _daily_action_item(
                "analysis",
                70,
                "주간 분석을 확인할 수 있습니다.",
                "최근 기록 흐름과 목표 달성률을 함께 살펴봅니다.",
                "분석 보기",
                "/summaries/weekly",
            )
        )

    items.sort(key=lambda item: int(item["priority"]))
    visible_items = items[:5]
    return {
        "items": visible_items,
        "badge": f"{len(visible_items)}개" if visible_items else "완료",
        "subtitle": "오늘 기록과 목표 기준으로 먼저 처리할 항목입니다."
        if is_selected_today
        else "선택한 날짜 기준 추천입니다.",
        "is_complete": len(visible_items) == 0,
        "complete_title": "오늘 핵심 기록이 채워졌습니다.",
        "complete_description": "주간 분석을 확인하거나 필요하면 휴식 메모를 남길 수 있습니다.",
        "complete_actions": [
            {"label": "주간 분석", "href": "/summaries/weekly"},
            {"label": "휴식 메모", "href": f"{base_app_href}&mode=workout#rest-timer"},
        ],
    }


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
        "workout_session_flow": {
            "next_item": None,
            "last_set": None,
            "rest_seconds": 90,
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
    today_session = deps["get_or_create_session"](selected_date, selected_location_id)
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
        context.update(
            {
                "exercises": exercises,
                "exercises_by_body_part": deps["list_exercises_by_body_part"](current_location["id"]),
                "recent_sets_by_exercise": deps["list_recent_sets_by_exercise"](location_id=current_location["id"]),
                "exercise_stats_by_name": deps["list_exercise_stats_by_name"](current_location["id"]),
                "exercise_smart_defaults": deps["list_exercise_smart_defaults"](current_location["id"]),
                "overload_suggestions": deps["list_overload_suggestions"](),
                "next_set_suggestions": deps["build_next_set_suggestions"](quick_names, today_session["workout_date"]),
                "exercise_notes": deps["list_exercise_notes"](),
                "exercise_settings": deps["list_exercise_settings"](),
                "exercise_goal_progress": deps["list_exercise_goal_progress"](),
                "pr_events": deps["list_pr_events"](today_session["workout_date"]),
                "recent_pr_events": deps["list_recent_pr_events"](limit=8),
                "favorite_exercises": deps["list_favorite_exercises"](current_location["id"]),
                "routines": deps["list_routines"](current_location["id"]),
                "workout_plan": deps["list_workout_plan"](today_session["workout_date"]),
                "workout_completion_summary": deps["build_workout_completion_summary"](today_session["workout_date"]),
                "workout_finish_review": deps["build_workout_finish_review"](today_session["workout_date"]),
                "pr_cards": deps["build_pr_cards"](today_session["workout_date"]),
                "weekly_routine_recommendations": deps["list_weekly_routine_recommendations"](today_session["workout_date"]),
                "recommended_sessions": deps["list_recommended_sessions"](today_session["workout_date"]),
                "workout_focus_recommendations": deps["list_workout_focus_recommendations"](today_session["workout_date"]),
                "today_next_actions": deps["list_today_next_actions"](today_session["workout_date"]),
                "today_rule_cards": deps["list_today_rule_cards"](today_session["workout_date"]),
                "volume_warnings": deps["list_volume_warnings"](today_session["workout_date"]),
                "default_programs": deps["DEFAULT_PROGRAMS"].keys(),
                "balance_score": deps["get_balance_score"]("weekly", today_session["workout_date"]),
                "recovery_statuses": deps["list_recovery_statuses"](today_session["workout_date"]),
                "recovery_checkin": deps["get_recovery_checkin"](today_session["workout_date"]),
                "readiness_profile": deps["build_readiness_profile"](today_session["workout_date"]),
                "recovery_recommendations": deps["list_recovery_recommendations"](today_session["workout_date"]),
                "adaptive_training_recommendations": deps["build_adaptive_training_recommendations"](today_session["workout_date"]),
                "daily_coaching": deps["list_daily_coaching"](today_session["workout_date"]),
                "workout_session_flow": deps["build_workout_session_flow"](today_session["workout_date"]),
                "workout_groups": deps["grouped_sets_for_session"](today_session["id"]),
                "location_equipment": location_equipment,
                "location_quick_exercises": deps["list_location_quick_exercises"](current_location["id"]),
                "equipment_options": deps["equipment_options_for_location"](current_location["id"]),
                "has_location_equipment": bool(location_equipment),
            }
        )

    if meal_mode:
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

    return context
