from __future__ import annotations

from health_tracker.services.today_context import build_today_context
from health_tracker.routes.auth import register_auth_routes
from health_tracker.routes.settings import register_settings_routes
from health_tracker.routes.summaries import register_summary_routes
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

    register_summary_routes(app, globals())

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

