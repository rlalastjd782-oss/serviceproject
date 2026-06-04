from __future__ import annotations


def register_record_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

    @app.get("/records/search")
    def record_search_page():
        page, per_page = configured_page_params(request.args)
        selected_part = request.args.get("part", "").strip()
        selected_equipment = request.args.get("equipment", "").strip()
        selected_location_id = parse_int(request.args.get("location_id"))
        query = request.args.get("q", "").strip()
        has_explicit_filters = bool(query or selected_part or selected_equipment or selected_location_id)
        selected_end = normalize_optional_date(request.args.get("end"), max_future_days=365)
        selected_start = normalize_optional_date(request.args.get("start"), max_future_days=365)
        if not selected_start and not selected_end and not has_explicit_filters:
            selected_end = current_local_date()
            selected_start = shift_date(selected_end, -6)
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
