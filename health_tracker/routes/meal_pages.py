from __future__ import annotations


def register_meal_page_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

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
