from __future__ import annotations


def register_aux_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

    @app.get("/more")
    def more_page():
        return render_template("more.html", active_page="more")

    @app.get("/sw.js")
    def root_service_worker():
        response = Response(
            (BASE_DIR / "static" / "sw.js").read_text(encoding="utf-8"),
            content_type="text/javascript; charset=utf-8",
        )
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/exercises/library")
    def exercise_library_page():
        selected_part = request.args.get("part", "").strip()
        search_query = request.args.get("q", "").strip()
        favorite_only = request.args.get("favorite") == "1"
        return render_template(
            "exercise_library.html",
            active_page="library",
            body_parts=body_part_options(),
            selected_part=selected_part,
            search_query=search_query,
            favorite_only=favorite_only,
            exercises=list_exercise_library(selected_part, search_query, favorite_only),
        )

    @app.get("/plans/weekly")
    def weekly_plan_page():
        selected_week = normalize_date(request.args.get("week"))
        week_start = week_start_for_date(selected_week)
        return render_template(
            "weekly_plan.html",
            active_page="plans",
            week_start=week_start,
            week_end=shift_date(week_start, 6),
            prev_week=shift_date(week_start, -7),
            next_week=shift_date(week_start, 7),
            plan_board=build_weekly_plan_board(week_start),
        )

    @app.post("/plans/weekly/generate")
    def generate_weekly_plan_route():
        week_start = week_start_for_date(normalize_date(request.form.get("week_start")))
        generate_weekly_plan(week_start)
        return redirect(url_for("weekly_plan_page", week=week_start))

    @app.post("/reminders")
    def save_reminders_route():
        for key in ("workout", "meal", "weekly"):
            save_reminder_settings(
                key,
                request.form.get(f"{key}_enabled") == "1",
                request.form.get(f"{key}_time", ""),
                request.form.get(f"{key}_message", ""),
            )
        return redirect(url_for("settings_page"))
