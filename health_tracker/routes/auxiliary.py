from __future__ import annotations


def register_aux_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

    @app.get("/more")
    def more_page():
        return render_template("more/index.html", active_page="more")

    @app.get("/locations")
    def locations_page():
        return render_template(
            "more/locations.html",
            active_page="locations",
            locations=list_workout_locations(include_inactive=True),
            active_locations=list_workout_locations(),
            selected_location_id=parse_int(request.args.get("location_id")),
            equipment_by_location={
                location["id"]: list_location_equipment(location["id"], include_inactive=True)
                for location in list_workout_locations(include_inactive=True)
            },
        )

    @app.post("/locations")
    def save_location_route():
        location_id = parse_int(request.form.get("location_id"))
        saved_id = save_workout_location(
            request.form.get("name", ""),
            request.form.get("address", ""),
            request.form.get("memo", ""),
            location_id,
            request.form.get("is_default") == "1",
        )
        return redirect(url_for("locations_page", location_id=saved_id))

    @app.post("/locations/<int:location_id>/default")
    def set_default_location_route(location_id: int):
        set_default_workout_location(location_id)
        return redirect(url_for("locations_page", location_id=location_id))

    @app.post("/locations/<int:location_id>/delete")
    def delete_location_route(location_id: int):
        deactivate_workout_location(location_id)
        return redirect(url_for("locations_page"))

    @app.post("/locations/<int:location_id>/remove")
    def remove_location_route(location_id: int):
        delete_unused_workout_location(location_id)
        return redirect(url_for("locations_page"))

    @app.post("/locations/<int:location_id>/equipment")
    def save_location_equipment_route(location_id: int):
        save_location_equipment(
            location_id,
            request.form.get("equipment_name", ""),
            request.form.get("equipment_type", ""),
            request.form.get("memo", ""),
        )
        return redirect(url_for("locations_page", location_id=location_id))

    @app.post("/location-equipment/<int:equipment_id>/delete")
    def delete_location_equipment_route(equipment_id: int):
        location_id = parse_int(request.form.get("location_id"))
        delete_location_equipment(equipment_id)
        return redirect(url_for("locations_page", location_id=location_id))

    @app.get("/qa/report")
    def qa_report_page():
        return render_template(
            "qa/report.html",
            active_page="settings",
            qa_dummy_status=get_qa_dummy_status(),
            qa_links=[
                {"label": "2025 연간", "href": url_for("yearly_summary_page", year="2025")},
                {"label": "2026 연간", "href": url_for("yearly_summary_page", year="2026")},
                {
                    "label": "2025 vs 2026",
                    "href": url_for("yearly_compare_page", base_year="2025", compare_year="2026"),
                },
                {
                    "label": "연도 경계 검색",
                    "href": url_for("record_search_page", start="2025-12-31", end="2026-01-01", q="QA-"),
                },
                {"label": "서비스워커", "href": url_for("root_service_worker")},
            ],
        )

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
        page, per_page = page_params(request.args)
        selected_part = request.args.get("part", "").strip()
        search_query = request.args.get("q", "").strip()
        favorite_only = request.args.get("favorite") == "1"
        library_sort = request.args.get("sort", "favorite")
        exercises, pagination, library_sort = paged_exercise_library(
            selected_part,
            search_query,
            favorite_only,
            library_sort,
            page,
            per_page,
        )
        return render_template(
            "more/exercise_library.html",
            active_page="library",
            body_parts=body_part_options(),
            selected_part=selected_part,
            search_query=search_query,
            favorite_only=favorite_only,
            exercises=exercises,
            pagination=pagination,
            library_sort=library_sort,
        )

    @app.get("/plans/weekly")
    def weekly_plan_page():
        selected_week = normalize_date(request.args.get("week"))
        week_start = week_start_for_date(selected_week)
        return render_template(
            "more/weekly_plan.html",
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
