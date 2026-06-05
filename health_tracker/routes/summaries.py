from __future__ import annotations

from health_tracker.services.summary_context import (
    build_daily_summary_context,
    build_monthly_summary_context,
    build_weekly_summary_context,
)


TEST_EXERCISE_PREFIX = "__TEST__"


def display_exercise_name(name: object) -> str:
    value = str(name or "").strip()
    if value.startswith(TEST_EXERCISE_PREFIX):
        value = value[len(TEST_EXERCISE_PREFIX) :].strip()
    return value or "샘플 운동"


def display_row_names(row: object, *fields: str) -> object:
    if not row:
        return row
    item = dict(row)
    for field in fields:
        if field in item:
            item[field] = display_exercise_name(item[field])
    return item


def display_rows(rows: list[object], *fields: str) -> list[object]:
    return [display_row_names(row, *fields) for row in rows]


def register_summary_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

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

    @app.get("/summaries/annual")
    @app.get("/summaries/annual/")
    def annual_summary_redirect():
        target = url_for("yearly_summary_page")
        query_string = request.query_string.decode("utf-8")
        if query_string:
            target = f"{target}?{query_string}"
        return redirect(target)

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
        if "per_page" not in request.args:
            per_page = 5
        exercise_sort = request.args.get("sort", "sets")
        exercise_id = parse_int(request.args.get("exercise_id"))
        search_query = request.args.get("q", "").strip()
        exercise_choices = display_rows(list_exercises(), "name")
        exercise_summary, exercise_pagination, exercise_sort = paged_exercise_summary(exercise_sort, page, per_page)
        exercise_summary = display_rows(exercise_summary, "name")
        if search_query:
            search_results, search_pagination, search_sort = paged_search_workout_records(
                search_query,
                sort=request.args.get("search_sort", "newest"),
                page=page,
                per_page=per_page,
            )
            search_results = display_rows(search_results, "exercise_name")
        else:
            search_results, search_pagination, search_sort = [], build_pagination(0, 1, per_page), "newest"
        selected_exercise = exercise_id
        body_part_exercise_summary = {
            part: display_rows(rows, "name") for part, rows in list_exercise_summary_by_body_part().items()
        }
        selected_exercise_profile = display_row_names(get_exercise_profile(selected_exercise), "name") if selected_exercise else None
        exercise_pr_history = display_rows(list_exercise_pr_history(selected_exercise), "exercise_name") if selected_exercise else []
        recent_pr_events = display_rows(list_recent_pr_events(limit=5), "exercise_name")
        progressive_overload_rows = display_rows(list_progressive_overload_rows(limit=24), "exercise_name")
        return render_template(
            "summaries/summary.html",
            page_title="운동별 횟수",
            page_kicker="Exercise",
            table_kind="exercise",
            exercise_summary=exercise_summary,
            exercise_pagination=exercise_pagination,
            exercise_sort=exercise_sort,
            body_part_exercise_summary=body_part_exercise_summary,
            body_parts=body_part_options(),
            exercise_choices=exercise_choices,
            selected_exercise_id=selected_exercise,
            selected_exercise_profile=selected_exercise_profile,
            selected_exercise_next_plan=build_exercise_next_plan(selected_exercise) if selected_exercise else [],
            selected_exercise_trend=build_exercise_trend_summary(selected_exercise) if selected_exercise else [],
            exercise_growth=build_exercise_growth_chart(selected_exercise) if selected_exercise else [],
            exercise_recent_sets=list_exercise_recent_sets(selected_exercise)[:5] if selected_exercise else [],
            exercise_pr_history=exercise_pr_history,
            recent_pr_events=recent_pr_events,
            search_query=search_query,
            search_results=search_results,
            search_pagination=search_pagination,
            search_sort=search_sort,
            active_page="exercises",
            progressive_overload_rows=progressive_overload_rows,
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
        if "per_page" not in request.args:
            per_page = 5
        selected_part = request.args.get("part", "").strip()
        search_query = request.args.get("q", "").strip()
        pr_sort = request.args.get("sort", "weight")
        pr_rows, pr_pagination, pr_sort = paged_exercise_pr_summary(selected_part, search_query, pr_sort, page, per_page)
        pr_rows = display_rows(pr_rows, "name")
        recent_pr_events = display_rows(list_recent_pr_events_filtered(selected_part, search_query, limit=5), "exercise_name")
        selected_exercise = parse_int(request.args.get("exercise_id"))
        selected_profile = display_row_names(get_exercise_profile(selected_exercise), "name") if selected_exercise else None
        return render_template(
            "summaries/pr.html",
            body_parts=body_part_options(),
            exercise_choices=display_rows(list_pr_exercise_choices(selected_part, search_query), "name"),
            selected_part=selected_part,
            search_query=search_query,
            pr_rows=pr_rows,
            pr_pagination=pr_pagination,
            pr_sort=pr_sort,
            pr_dashboard=build_pr_dashboard(pr_rows, recent_pr_events),
            selected_exercise_id=selected_exercise,
            selected_profile=selected_profile,
            selected_growth=build_exercise_growth_chart(selected_exercise, limit=10) if selected_exercise else [],
            selected_pr_sets=list_exercise_best_sets(selected_exercise) if selected_exercise else [],
            selected_pr_timeline=list_exercise_pr_timeline(selected_exercise) if selected_exercise else [],
            recent_pr_events=recent_pr_events,
            active_page="pr",
        )
