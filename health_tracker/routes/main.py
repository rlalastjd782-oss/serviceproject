from __future__ import annotations

from health_tracker.services.summary_context import (
    build_daily_summary_context,
    build_monthly_summary_context,
    build_weekly_summary_context,
)
from health_tracker.services.today_context import build_today_context
from health_tracker.routes.auth import register_auth_routes
from health_tracker.routes.settings import register_settings_routes
from health_tracker.routes.today_actions import register_today_action_routes
from health_tracker.routes.data import register_data_routes
from health_tracker.routes.entries import register_entry_routes


def register_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)
    register_auth_routes(app, ctx)
    register_settings_routes(app, ctx)


    @app.get("/")
    def root_route():
        account = current_account()
        if not account:
            return redirect(url_for("login_page"))
        if account["role"] == "admin":
            return redirect(url_for("admin_dashboard_page"))
        return redirect(url_for("index"))

    @app.get("/app")
    def index():
        return render_template("today/index.html", **build_today_context(request.args, globals()))

    @app.get("/summaries")
    def summaries():
        return redirect(url_for("weekly_summary_page"))

    @app.get("/summaries/daily")
    def daily_summary_page():
        return render_template("summaries/summary.html", **build_daily_summary_context(request.args, globals()))

    @app.get("/summaries/weekly")
    def weekly_summary_page():
        return render_template("summaries/summary.html", **build_weekly_summary_context(request.args, globals()))

    @app.get("/summaries/monthly")
    def monthly_summary_page():
        return render_template("summaries/summary.html", **build_monthly_summary_context(request.args, globals()))

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
        page, per_page = configured_page_params(request.args)
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
            progressive_overload_rows=list_progressive_overload_rows(limit=24),
            muscle_balance=build_muscle_balance(shift_date(current_local_date(), -6), current_local_date()),
        )

    @app.get("/summaries/equipment")
    def equipment_summary_page():
        page, per_page = configured_page_params(request.args)
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
        page, per_page = configured_page_params(request.args)
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

    from health_tracker.routes.auxiliary import register_aux_routes
    from health_tracker.routes.admin import register_admin_routes

    register_aux_routes(app, globals())
    register_admin_routes(app, globals())

    register_today_action_routes(app, globals())

    @app.get("/records/search")
    def record_search_page():
        page, per_page = configured_page_params(request.args)
        selected_end = normalize_optional_date(request.args.get("end"), max_future_days=365) or current_local_date()
        selected_start = normalize_optional_date(request.args.get("start"), max_future_days=365) or shift_date(selected_end, -6)
        selected_part = request.args.get("part", "").strip()
        selected_equipment = request.args.get("equipment", "").strip()
        selected_location_id = parse_int(request.args.get("location_id"))
        query = request.args.get("q", "").strip()
        sort = request.args.get("sort", "newest")
        results, pagination, selected_sort = paged_search_workout_records_filtered(
            query,
            selected_part,
            selected_equipment,
            selected_location_id,
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
            locations=list_workout_locations(),
            selected_location_id=selected_location_id,
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

    register_data_routes(app, globals())

    register_entry_routes(app, globals())

    @app.get("/api/sessions")
    def api_sessions():
        return jsonify([dict(row) for row in list_recent_sessions(limit=30)])

