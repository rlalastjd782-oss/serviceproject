from __future__ import annotations


def register_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

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
            "today/index.html",
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
            workout_completion_summary=build_workout_completion_summary(today_session["workout_date"]),
            pr_cards=build_pr_cards(today_session["workout_date"]),
            weekly_routine_recommendations=list_weekly_routine_recommendations(today_session["workout_date"]),
            recommended_sessions=list_recommended_sessions(today_session["workout_date"]),
            workout_focus_recommendations=list_workout_focus_recommendations(today_session["workout_date"]),
            volume_warnings=list_volume_warnings(today_session["workout_date"]),
            frequent_meal_combos=list_frequent_meal_combos(),
            default_programs=DEFAULT_PROGRAMS.keys(),
            meal_templates=list_meal_templates(),
            body_metric=get_body_metric(today_session["workout_date"]),
            body_photos=list_body_photos(today_session["workout_date"]),
            goals=get_goal_progress(today_session["workout_date"]),
            meals=meals,
            meal_groups=grouped_meals_for_date(today_session["workout_date"]),
            today_summary=get_day_summary(today_session["workout_date"]),
            daily_calorie_goal=get_goal_value("daily_calories", 2200),
            data_quality_profile=build_data_quality_profile(today_session["workout_date"]),
            balance_score=get_balance_score("weekly", today_session["workout_date"]),
            recovery_statuses=list_recovery_statuses(today_session["workout_date"]),
            recovery_checkin=get_recovery_checkin(today_session["workout_date"]),
            readiness_profile=build_readiness_profile(today_session["workout_date"]),
            recovery_recommendations=list_recovery_recommendations(today_session["workout_date"]),
            adaptive_training_recommendations=build_adaptive_training_recommendations(today_session["workout_date"]),
            nutrition_training_link=build_nutrition_training_link("weekly", today_session["workout_date"]),
            body_progress_insights=build_body_progress_insights(today_session["workout_date"]),
            daily_coaching=list_daily_coaching(today_session["workout_date"]),
            workout_session_flow=build_workout_session_flow(today_session["workout_date"]),
            record_gaps=list_record_gaps(today_session["workout_date"]),
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
        page, per_page = page_params(request.args)
        days = parse_int(request.args.get("days")) or 7
        days = min(max(days, 7), 90)
        daily_sort = request.args.get("sort", "newest")
        daily_rows = list_daily_summary(days=days)
        if daily_sort == "oldest":
            daily_rows = list(reversed(daily_rows))
        else:
            daily_sort = "newest"
        daily_pagination = build_pagination(len(daily_rows), page, per_page)
        daily_summary = daily_rows[daily_pagination.offset : daily_pagination.offset + daily_pagination.per_page]
        return render_template(
            "summaries/summary.html",
            page_title="일간 집계",
            page_kicker="Daily",
            table_kind="daily",
            daily_summary=daily_summary,
            daily_pagination=daily_pagination,
            daily_sort=daily_sort,
            selected_days=days,
            body_part_summary=list_body_part_summary("daily"),
            active_page="daily",
        )

    @app.get("/summaries/weekly")
    def weekly_summary_page():
        page, per_page = page_params(request.args)
        period_sort = request.args.get("sort", "newest")
        selected_week = normalize_date(request.args.get("week"))
        week_start = week_start_for_date(selected_week)
        week_end = shift_date(week_start, 6)
        chart_rows = list_daily_summary(start_date=week_start, end_date=week_end)
        all_period_rows = list_weekly_summary(limit=240)
        if period_sort == "oldest":
            all_period_rows = list(reversed(all_period_rows))
        elif period_sort == "volume":
            all_period_rows = sorted(all_period_rows, key=lambda row: float(row["volume"] or 0), reverse=True)
        else:
            period_sort = "newest"
        period_pagination = build_pagination(len(all_period_rows), page, per_page)
        period_rows = all_period_rows[period_pagination.offset : period_pagination.offset + period_pagination.per_page]
        return render_template(
            "summaries/summary.html",
            page_title="주간 집계",
            page_kicker="Weekly",
            table_kind="period",
            period_rows=period_rows,
            period_pagination=period_pagination,
            period_sort=period_sort,
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
            nutrition_training_link=build_nutrition_training_link("weekly", week_start),
            selected_week=week_start,
            prev_week=shift_date(week_start, -7),
            next_week=shift_date(week_start, 7),
            active_page="weekly",
        )

    @app.get("/summaries/monthly")
    def monthly_summary_page():
        page, per_page = page_params(request.args)
        period_sort = request.args.get("sort", "newest")
        selected_month = request.args.get("month") or current_local_date()[:7]
        month_start = normalize_month(selected_month)
        all_period_rows = list_weekly_summary(month_start=month_start, limit=12)
        if period_sort == "oldest":
            all_period_rows = list(reversed(all_period_rows))
        elif period_sort == "volume":
            all_period_rows = sorted(all_period_rows, key=lambda row: float(row["volume"] or 0), reverse=True)
        else:
            period_sort = "newest"
        period_pagination = build_pagination(len(all_period_rows), page, per_page)
        period_rows = all_period_rows[period_pagination.offset : period_pagination.offset + period_pagination.per_page]
        return render_template(
            "summaries/summary.html",
            page_title="월간 집계",
            page_kicker="Monthly",
            table_kind="period",
            period_rows=period_rows,
            period_pagination=period_pagination,
            period_sort=period_sort,
            period_label="기간",
            chart_items=build_period_chart(period_rows),
            chart_title="주간별 추이",
            chart_note="선택한 월을 주간 단위로 표시합니다.",
            body_part_summary=list_body_part_summary("monthly", date_text=month_start),
            monthly_report=build_monthly_report(month_start),
            body_monthly_report=build_body_monthly_report(month_start),
            body_metric_trend=list_body_metric_trend(month_start),
            monthly_goals=get_goal_progress(month_start),
            monthly_goal_insights=build_goal_insights("monthly", month_start),
            report_insights=build_period_insights("monthly", month_start),
            period_highlights=build_period_highlights("monthly", month_start),
            nutrition_training_link=build_nutrition_training_link("monthly", month_start),
            selected_month=month_start[:7],
            prev_month=shift_month(month_start, -1)[:7],
            next_month=shift_month(month_start, 1)[:7],
            active_page="monthly",
        )

    @app.get("/summaries/yearly")
    def yearly_summary_page():
        selected_year = normalize_year(request.args.get("year"), current_local_date())
        prev_year = str(int(selected_year) - 1)
        next_year = str(int(selected_year) + 1)
        return render_template(
            "summaries/yearly.html",
            active_page="yearly",
            selected_year=selected_year,
            prev_year=prev_year,
            next_year=next_year,
            yearly_report=build_yearly_report(selected_year),
            month_rows=list_yearly_month_rows(selected_year),
            body_part_summary=list_yearly_body_part_summary(selected_year),
            top_exercises=list_yearly_top_exercises(selected_year),
        )

    @app.get("/summaries/yearly/compare")
    def yearly_compare_page():
        compare_year = normalize_year(request.args.get("compare_year"), current_local_date())
        base_year = normalize_year(request.args.get("base_year"), str(int(compare_year) - 1))
        base_report = build_yearly_report(base_year)
        compare_report = build_yearly_report(compare_year)
        return render_template(
            "summaries/yearly_compare.html",
            active_page="yearly",
            base_year=base_year,
            compare_year=compare_year,
            base_report=base_report,
            compare_report=compare_report,
            comparison_rows=compare_yearly_reports(base_report, compare_report),
            qa_dummy_status=get_qa_dummy_status(),
        )

    @app.get("/summaries/exercises")
    def exercise_summary_page():
        page, per_page = page_params(request.args)
        exercise_sort = request.args.get("sort", "sets")
        exercise_id = parse_int(request.args.get("exercise_id"))
        search_query = request.args.get("q", "").strip()
        exercise_choices = list_exercises()
        exercise_summary, exercise_pagination, exercise_sort = paged_exercise_summary(exercise_sort, page, per_page)
        if search_query:
            search_results, search_pagination, search_sort = paged_search_workout_records(
                search_query,
                sort=request.args.get("search_sort", "newest"),
                page=page,
                per_page=per_page,
            )
        else:
            search_results, search_pagination, search_sort = [], build_pagination(0, 1, per_page), "newest"
        selected_exercise = exercise_id or (int(exercise_summary[0]["id"]) if exercise_summary else None)
        return render_template(
            "summaries/summary.html",
            page_title="운동별 횟수",
            page_kicker="Exercise",
            table_kind="exercise",
            exercise_summary=exercise_summary,
            exercise_pagination=exercise_pagination,
            exercise_sort=exercise_sort,
            body_part_exercise_summary=list_exercise_summary_by_body_part(),
            body_parts=body_part_options(),
            exercise_choices=exercise_choices,
            selected_exercise_id=selected_exercise,
            selected_exercise_profile=get_exercise_profile(selected_exercise),
            selected_exercise_next_plan=build_exercise_next_plan(selected_exercise),
            selected_exercise_trend=build_exercise_trend_summary(selected_exercise),
            exercise_growth=build_exercise_growth_chart(selected_exercise),
            exercise_recent_sets=list_exercise_recent_sets(selected_exercise),
            exercise_pr_history=list_exercise_pr_history(selected_exercise),
            recent_pr_events=list_recent_pr_events(limit=20),
            search_query=search_query,
            search_results=search_results,
            search_pagination=search_pagination,
            search_sort=search_sort,
            active_page="exercises",
        )

    @app.get("/summaries/equipment")
    def equipment_summary_page():
        page, per_page = page_params(request.args)
        selected_equipment = request.args.get("equipment", "").strip()
        selected_scope = request.args.get("scope", "month").strip() or "month"
        equipment_sort = request.args.get("sort", "sets")
        equipment_rows, equipment_pagination, equipment_sort = paged_equipment_summary(selected_scope, equipment_sort, page, per_page)
        selected_equipment = selected_equipment or (equipment_rows[0]["equipment"] if equipment_rows else "")
        if selected_equipment:
            equipment_detail, equipment_detail_pagination = paged_equipment_detail(selected_equipment, selected_scope, page, per_page)
            equipment_daily, equipment_daily_pagination = paged_equipment_daily(selected_equipment, selected_scope, page, per_page)
        else:
            equipment_detail, equipment_daily = [], []
            equipment_detail_pagination = build_pagination(0, 1, per_page)
            equipment_daily_pagination = build_pagination(0, 1, per_page)
        return render_template(
            "summaries/summary.html",
            page_title="장비별 기록",
            page_kicker="Equipment",
            table_kind="equipment",
            equipment_summary=equipment_rows,
            equipment_pagination=equipment_pagination,
            equipment_sort=equipment_sort,
            equipment_detail=equipment_detail,
            equipment_detail_pagination=equipment_detail_pagination,
            equipment_daily=equipment_daily,
            equipment_daily_pagination=equipment_daily_pagination,
            selected_equipment=selected_equipment,
            selected_scope=selected_scope,
            active_page="equipment",
        )

    @app.get("/summaries/pr")
    def pr_summary_page():
        page, per_page = page_params(request.args)
        selected_part = request.args.get("part", "").strip()
        search_query = request.args.get("q", "").strip()
        pr_sort = request.args.get("sort", "weight")
        pr_rows, pr_pagination, pr_sort = paged_exercise_pr_summary(selected_part, search_query, pr_sort, page, per_page)
        recent_pr_events = list_recent_pr_events_filtered(selected_part, search_query, limit=30)
        selected_exercise = parse_int(request.args.get("exercise_id"))
        selected_exercise = selected_exercise or (int(pr_rows[0]["id"]) if pr_rows else None)
        return render_template(
            "summaries/pr.html",
            body_parts=body_part_options(),
            exercise_choices=list_pr_exercise_choices(selected_part, search_query),
            selected_part=selected_part,
            search_query=search_query,
            pr_rows=pr_rows,
            pr_pagination=pr_pagination,
            pr_sort=pr_sort,
            pr_dashboard=build_pr_dashboard(pr_rows, recent_pr_events),
            selected_exercise_id=selected_exercise,
            selected_profile=get_exercise_profile(selected_exercise),
            selected_growth=build_exercise_growth_chart(selected_exercise, limit=10),
            selected_pr_sets=list_exercise_best_sets(selected_exercise),
            selected_pr_timeline=list_exercise_pr_timeline(selected_exercise),
            recent_pr_events=recent_pr_events,
            active_page="pr",
        )

    @app.get("/calendar")
    def calendar_page():
        selected_month = request.args.get("month") or current_local_date()[:7]
        month_start = normalize_month(selected_month)
        current_date = current_local_date()
        goal_date = current_date if month_start[:7] == current_date[:7] else month_start
        return render_template(
            "more/calendar.html",
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
            "meals/weekly.html",
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

    @app.get("/meals/monthly")
    def meal_monthly_page():
        selected_month = request.args.get("month") or current_local_date()[:7]
        month_start = normalize_month(selected_month)
        return render_template(
            "meals/monthly.html",
            selected_month=month_start[:7],
            prev_month=shift_month(month_start, -1)[:7],
            next_month=shift_month(month_start, 1)[:7],
            month_summary=build_monthly_meal_summary(month_start),
            meal_weeks=list_monthly_meal_weeks(month_start),
            meal_goals=get_goal_progress(month_start),
            active_page="meals",
        )

    @app.get("/settings")
    def settings_page():
        if not settings_unlocked():
            return render_template(
                "settings/lock.html",
                active_page="settings",
                has_password=has_settings_password(),
                error=request.args.get("error", ""),
            )
        return render_template(
            "settings/index.html",
            active_page="settings",
            error=request.args.get("error", ""),
            sample_counts=get_sample_data_counts(),
            data_counts=get_data_counts(),
            backup_status=get_backup_status(),
            health_status=get_app_health_status(),
            reminder_settings=list_reminder_settings(),
            has_settings_password=has_settings_password(),
            qa_dummy_status=get_qa_dummy_status(),
        )

    @app.post("/settings/unlock")
    def unlock_settings_route():
        password = request.form.get("password", "")
        if verify_settings_password(password):
            session["settings_unlocked"] = True
            return redirect(url_for("settings_page"))
        return redirect(url_for("settings_page", error="invalid"))

    @app.post("/settings/password")
    def save_settings_password_route():
        if has_settings_password() and not settings_unlocked():
            return redirect(url_for("settings_page"))
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        if password != password_confirm or not set_settings_password(password):
            return redirect(url_for("settings_page", error="password"))
        return redirect(url_for("settings_page"))

    @app.post("/settings/password/reset")
    def reset_settings_password_route():
        if settings_unlocked() and request.form.get("confirm_reset", "").strip() == "RESET":
            reset_settings_password()
        return redirect(url_for("settings_page"))

    @app.post("/settings/lock")
    def lock_settings_route():
        session.pop("settings_unlocked", None)
        return redirect(url_for("settings_page"))

    @app.post("/qa-dummy/year")
    def generate_year_qa_dummy_route():
        if settings_unlocked():
            generate_year_qa_dummy_data()
        return redirect(url_for("settings_page"))

    from health_tracker.routes.auxiliary import register_aux_routes

    register_aux_routes(app, globals())

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

    @app.post("/rest-days")
    def save_rest_day_route():
        rest_date = normalize_date(request.form.get("rest_date"))
        save_rest_day(rest_date, request.form.get("rest_reason", ""), request.form.get("memo", ""))
        return redirect(url_for("index", date=rest_date))

    @app.post("/data/cleanup-empty")
    def cleanup_empty_data_route():
        delete_empty_workout_sessions()
        get_db().commit()
        return redirect(url_for("settings_page"))

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
                parse_float(request.form.get("target_weight")),
                parse_int(request.form.get("target_reps")),
                parse_int(request.form.get("target_sets")),
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

    @app.post("/meals/combo")
    def apply_meal_combo_route():
        meal_date = normalize_date(request.form.get("meal_date"))
        meal_type = request.form.get("meal_type", "").strip()
        source_date = normalize_optional_date(request.form.get("source_date"))
        if source_date and meal_type:
            copy_meal_type_from_day(source_date, meal_date, meal_type)
        return redirect(url_for("index", date=meal_date, mode="meal"))

    @app.get("/records/search")
    def record_search_page():
        page, per_page = page_params(request.args)
        selected_end = normalize_optional_date(request.args.get("end"), max_future_days=365) or current_local_date()
        selected_start = normalize_optional_date(request.args.get("start"), max_future_days=365) or shift_date(selected_end, -6)
        selected_part = request.args.get("part", "").strip()
        selected_equipment = request.args.get("equipment", "").strip()
        query = request.args.get("q", "").strip()
        sort = request.args.get("sort", "newest")
        results, pagination, selected_sort = paged_search_workout_records_filtered(
            query,
            selected_part,
            selected_equipment,
            selected_start,
            selected_end,
            sort,
            page,
            per_page,
        )
        return render_template(
            "records/search.html",
            active_page="search",
            body_parts=body_part_options(),
            equipment_options=equipment_options(),
            selected_start=selected_start,
            selected_end=selected_end,
            selected_part=selected_part,
            selected_equipment=selected_equipment,
            search_query=query,
            results=results,
            pagination=pagination,
            selected_sort=selected_sort,
        )

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

    @app.get("/export-meals.csv")
    def export_meal_csv_route():
        return Response(
            export_meal_csv(),
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=health-tracker-meals.csv"},
        )

    @app.get("/export/yearly.json")
    def export_yearly_json_route():
        year = normalize_year(request.args.get("year"), current_local_date())
        return Response(
            json.dumps(export_yearly_payload(year), ensure_ascii=False, indent=2),
            content_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename=health-tracker-{year}.json"},
        )

    @app.get("/export/yearly-workouts.csv")
    def export_yearly_workouts_csv_route():
        year = normalize_year(request.args.get("year"), current_local_date())
        return Response(
            export_yearly_workout_csv(year),
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename=health-tracker-workouts-{year}.csv"},
        )

    @app.get("/export/yearly-meals.csv")
    def export_yearly_meals_csv_route():
        year = normalize_year(request.args.get("year"), current_local_date())
        return Response(
            export_yearly_meal_csv(year),
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename=health-tracker-meals-{year}.csv"},
        )

    @app.post("/import.json")
    def import_json():
        file = request.files.get("backup_file")
        if file and request.form.get("confirm_restore", "").strip() == "복원":
            import_all_data(json.loads(file.read().decode("utf-8")))
        return redirect(url_for("settings_page"))

    @app.post("/samples/delete")
    def delete_sample_data_route():
        if request.form.get("confirm_sample_delete", "").strip() == "샘플삭제":
            delete_sample_data()
        return redirect(url_for("settings_page"))

    @app.post("/samples/may")
    def create_may_sample_data_route():
        create_may_sample_data()
        return redirect(url_for("settings_page"))

    @app.post("/data/delete-all")
    def delete_all_data_route():
        if request.form.get("confirm_delete_all", "").strip() == "전체삭제":
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
            save_food_favorite(food_name, quantity, grams, calories)
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
            SELECT s.workout_date, ws.body_part, e.name AS exercise_name
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            JOIN exercises e ON e.id = ws.exercise_id
            WHERE ws.id = ?
            """,
            (set_id,),
        ).fetchone()
        workout_date = workout["workout_date"] if workout else current_local_date()
        mode = request.form.get("mode")
        equipment = request.form.get("equipment", "").strip()
        body_part = request.form.get("body_part", workout["body_part"] if workout else "").strip() or "기타"
        exercise_name = request.form.get("exercise_name", workout["exercise_name"] if workout else "").strip()
        exercise_id = get_or_create_exercise(exercise_name) if exercise_name else None
        if exercise_name and equipment:
            save_exercise_equipment(exercise_name, equipment)
        if body_part == "유산소":
            cardio_incline = parse_float(request.form.get("cardio_incline"))
            cardio_speed = parse_float(request.form.get("cardio_speed"))
            cardio_minutes = parse_float(request.form.get("cardio_minutes"))
            db.execute(
                """
                UPDATE workout_sets
                SET exercise_id = COALESCE(?, exercise_id),
                    body_part = ?,
                    weight = NULL,
                    reps = NULL,
                    set_type = ?,
                    cardio_incline = ?,
                    cardio_speed = ?,
                    cardio_minutes = ?,
                    estimated_calories = ?,
                    rpe = ?,
                    equipment = ?
                WHERE id = ?
                """,
                (
                    exercise_id,
                    body_part,
                    body_part,
                    cardio_incline,
                    cardio_speed,
                    cardio_minutes,
                    estimate_exercise_calories(body_part, cardio_incline, cardio_speed, cardio_minutes, workout_date),
                    parse_float(request.form.get("rpe")),
                    equipment[:20],
                    set_id,
                ),
            )
        else:
            db.execute(
                """
                UPDATE workout_sets
                SET exercise_id = COALESCE(?, exercise_id),
                    body_part = ?,
                    weight = ?,
                    reps = ?,
                    set_type = ?,
                    rpe = ?,
                    equipment = ?,
                    cardio_incline = NULL,
                    cardio_speed = NULL,
                    cardio_minutes = NULL,
                    estimated_calories = NULL
                WHERE id = ?
                """,
                (
                    exercise_id,
                    body_part,
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

