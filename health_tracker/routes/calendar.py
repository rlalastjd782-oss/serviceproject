from __future__ import annotations


def register_calendar_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

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
