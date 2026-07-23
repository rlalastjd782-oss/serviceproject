from __future__ import annotations

from flask import jsonify, redirect, request, url_for


def register_today_action_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

    def parse_weight_kg(value: str, unit: str) -> float | None:
        parsed = parse_float(value)
        if parsed is None:
            return None
        if (unit or "").strip().lower() in {"lb", "lbs"}:
            return round(parsed * 0.45359237, 2)
        return parsed

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

    @app.post("/sets")
    def create_set():
        location_id = parse_int(request.form.get("location_id"))
        session = get_or_create_session(request.form.get("workout_date"), location_id)
        mode = request.form.get("mode")
        body_part = request.form.get("body_part", "").strip() or "기타"
        exercise_name = request.form.get("exercise_name", "").strip()
        equipment = normalize_equipment_category(request.form.get("equipment", ""))
        equipment_brand = request.form.get("equipment_brand", "").strip()[:30]
        if not exercise_name:
            return redirect(url_for("index", date=session["workout_date"], mode=mode or None, location_id=session["location_id"]))

        set_weights = request.form.getlist("set_weight") or [request.form.get("weight", "")]
        set_weight_units = request.form.getlist("set_weight_unit") or [request.form.get("weight_unit", "kg")]
        set_reps = request.form.getlist("set_reps") or [request.form.get("reps", "")]
        cardio_inclines = request.form.getlist("cardio_incline") or [request.form.get("cardio_incline", "")]
        cardio_speeds = request.form.getlist("cardio_speed") or [request.form.get("cardio_speed", "")]
        cardio_minutes = request.form.getlist("cardio_minutes") or [request.form.get("cardio_minutes", "")]
        set_memos = request.form.getlist("set_memo") or [request.form.get("memo", "")]
        preferences = get_app_preferences()
        default_set_type = str(preferences["set_type_options"][0]) if preferences["set_type_options"] else "본세트"
        set_types = request.form.getlist("set_type") or [request.form.get("set_type", default_set_type)]
        set_rpes = request.form.getlist("set_rpe") or [request.form.get("rpe", "")]
        set_count = max(
            len(set_weights),
            len(set_weight_units),
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
            weight_unit = value_at(set_weight_units, index).strip() or "kg"
            reps_value = value_at(set_reps, index)
            incline_value = value_at(cardio_inclines, index)
            speed_value = value_at(cardio_speeds, index)
            minutes_value = value_at(cardio_minutes, index)
            memo_value = value_at(set_memos, index).strip()
            set_type = value_at(set_types, index).strip() or default_set_type
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
                    None if is_cardio else parse_weight_kg(weight_value, weight_unit),
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
            return redirect(url_for("index", date=session["workout_date"], mode=mode or None, location_id=session["location_id"]))

        repeat_count = parse_int(request.form.get("set_repeat_count")) or 1
        if len(set_rows) == 1 and repeat_count > 1:
            set_rows = set_rows * min(repeat_count, 10)

        db = get_db()
        exercise_id = get_or_create_exercise(exercise_name)
        if equipment:
            save_exercise_equipment(exercise_name, equipment)
            upsert_location_equipment(db, int(session["location_id"]), equipment)
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
                    cardio_minutes, estimated_calories, memo, sort_order, body_part, set_type, rpe, equipment, equipment_brand
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    equipment_brand,
                ),
            )
            if body_part != "유산소":
                record_pr_events(cursor.lastrowid, session["workout_date"], exercise_id, exercise_name, weight, reps, previous_records)
                previous_records = update_record_values(previous_records, weight, reps)
        db.commit()
        return redirect(
            url_for(
                "index",
                date=session["workout_date"],
                mode=mode or None,
                location_id=session["location_id"],
            )
        )

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
                parse_int(request.form.get("rest_seconds")) or int(get_app_preferences()["default_rest_seconds"]),
                request.form.get("is_favorite") == "1",
                normalize_equipment_category(request.form.get("equipment", "")),
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
