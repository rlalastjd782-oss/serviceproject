from __future__ import annotations

from flask import Response


def register_aux_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

    @app.get("/more")
    def more_page():
        return render_template(
            "more/index.html",
            active_page="more",
            data_center=build_data_center_status(),
            location_preview=list_location_training_insights(limit=3),
        )

    @app.get("/data/center")
    def data_center_page():
        selected_date = normalize_date(request.args.get("date"))
        return render_template(
            "more/data_center.html",
            active_page="data_center",
            selected_date=selected_date,
            data_center=build_data_center_status(selected_date),
        )

    @app.get("/locations/insights")
    def location_insights_page():
        return render_template(
            "more/location_insights.html",
            active_page="location_insights",
            location_insights=list_location_training_insights(limit=24),
        )

    @app.get("/insights/actions")
    def action_insights_page():
        selected_date = normalize_date(request.args.get("date"))
        return render_template(
            "more/action_insights.html",
            active_page="action_insights",
            selected_date=selected_date,
            action_insights=build_action_insights(selected_date),
        )

    @app.get("/tools/plate-calculator")
    def plate_calculator_page():
        return render_template(
            "more/plate_calculator.html",
            active_page="plate_calculator",
        )

    @app.get("/records/check")
    def record_check_page():
        selected_date = normalize_date(request.args.get("date"))
        days = normalize_summary_days(request.args.get("days"))
        return render_template(
            "more/record_check.html",
            active_page="record_check",
            selected_date=selected_date,
            selected_days=days,
            data_quality_profile=build_data_quality_profile(selected_date, days),
            record_gaps=list_record_gaps(selected_date, days),
            duplicate_exercises=list_duplicate_exercise_candidates(),
            outlier_sets=list_outlier_set_candidates(),
            data_counts=get_data_counts(),
        )

    @app.get("/meals/templates")
    def meal_templates_page():
        selected_date = normalize_date(request.args.get("date"))
        return render_template(
            "more/meal_templates.html",
            active_page="meal_templates",
            selected_date=selected_date,
            meal_templates=list_meal_templates(),
            recent_meal_days=list_recent_meal_days(selected_date, limit=10),
        )

    @app.post("/meals/templates/<int:template_id>/delete")
    def delete_meal_template_route(template_id: int):
        delete_meal_template(template_id)
        return redirect(url_for("meal_templates_page", date=normalize_date(request.form.get("meal_date"))))

    @app.get("/locations")
    def locations_page():
        return render_template(
            "more/locations.html",
            active_page="locations",
            locations=list_workout_locations(include_inactive=True),
            active_locations=list_workout_locations(),
            selected_location_id=parse_int(request.args.get("location_id")),
            equipment_options=equipment_options(),
            equipment_by_location={
                location["id"]: list_location_equipment(location["id"])
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
            v2_readiness=build_v2_readiness(),
            performance_snapshot=build_performance_snapshot(get_db()),
            page_timings=build_page_timing_snapshot(
                app,
                int(session.get("account_id") or 0),
                [
                    ("오늘 운동", "/app?mode=workout"),
                    ("기록 검색", "/records/search"),
                    ("주간 분석", "/summaries/weekly"),
                    ("월간 분석", "/summaries/monthly"),
                    ("주간 식단", "/meals/weekly"),
                ],
            ),
            deployment_checklist=build_deployment_checklist(BASE_DIR),
            source_audit=list_long_source_files(BASE_DIR),
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

    @app.post("/qa/analyze")
    def run_database_analyze_route():
        run_database_analyze(get_db())
        return redirect(url_for("qa_report_page"))

    @app.get("/sw.js")
    def root_service_worker():
        response = Response(
            (BASE_DIR / "static" / "sw.js").read_text(encoding="utf-8"),
            content_type="text/javascript; charset=utf-8",
        )
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/favicon.ico")
    def root_favicon():
        response = Response(
            (BASE_DIR / "static" / "icon.svg").read_text(encoding="utf-8"),
            content_type="image/svg+xml; charset=utf-8",
        )
        response.headers["Cache-Control"] = f"public, max-age={FAVICON_CACHE_SECONDS}"
        return response

    @app.get("/exercises/library")
    def exercise_library_page():
        page, per_page = configured_page_params(request.args)
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
        if request.form.get("next") == "admin":
            return redirect(url_for("admin_dashboard_page"))
        return redirect(url_for("settings_page"))
