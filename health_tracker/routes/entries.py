from __future__ import annotations

from flask import redirect, request, url_for


def register_entry_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

    def parse_weight_kg(value: str, unit: str) -> float | None:
        parsed = parse_float(value)
        if parsed is None:
            return None
        if (unit or "").strip().lower() in {"lb", "lbs"}:
            return round(parsed * 0.45359237, 2)
        return parsed

    @app.post("/meals")
    def create_meal():
        meal_date = normalize_date(request.form.get("meal_date"))
        mode = request.form.get("mode")
        meal_type = request.form.get("meal_type", "").strip()
        food_names = request.form.getlist("meal_food_name") or [request.form.get("food_name", "")]
        quantities = request.form.getlist("meal_quantity") or [request.form.get("amount", "")]
        grams_values = request.form.getlist("meal_grams") or [request.form.get("grams", "")]
        calories_values = request.form.getlist("meal_calories") or [request.form.get("calories", "")]
        memos = request.form.getlist("meal_memo") or [request.form.get("memo", "")]
        row_count = max(
            len(food_names),
            len(quantities),
            len(grams_values),
            len(calories_values),
            len(memos),
        )
        meal_rows = []
        for index in range(row_count):
            food_name = value_at(food_names, index).strip()
            quantity = value_at(quantities, index)
            grams = value_at(grams_values, index)
            calories = value_at(calories_values, index)
            memo = value_at(memos, index).strip()
            if food_name == "" and quantity.strip() == "" and grams.strip() == "" and calories.strip() == "" and memo == "":
                continue
            if food_name == "":
                continue
            meal_rows.append(
                (
                    food_name,
                    parse_float(quantity),
                    parse_float(grams),
                    parse_float(calories),
                    memo,
                )
            )

        if not meal_rows:
            return redirect(url_for("index", date=meal_date, mode=mode or None))

        db = get_db()
        for food_name, quantity, grams, calories, memo in meal_rows:
            db.execute(
                """
                INSERT INTO meal_entries
                    (meal_date, meal_type, food_name, quantity, grams, calories, memo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (meal_date, meal_type, food_name, quantity, grams, calories, memo),
            )
        db.commit()
        return redirect(url_for("index", date=meal_date, mode=mode or None))

    @app.post("/meals/<int:meal_id>/update")
    def update_meal(meal_id: int):
        db = get_db()
        meal = db.execute("SELECT meal_date FROM meal_entries WHERE id = ?", (meal_id,)).fetchone()
        meal_date = meal["meal_date"] if meal else current_local_date()
        mode = request.form.get("mode")
        food_name = request.form.get("food_name", "").strip()
        if food_name:
            db.execute(
                """
                UPDATE meal_entries
                SET food_name = ?, quantity = ?, grams = ?, calories = ?
                WHERE id = ?
                """,
                (
                    food_name,
                    parse_float(request.form.get("quantity")),
                    parse_float(request.form.get("grams")),
                    parse_float(request.form.get("calories")),
                    meal_id,
                ),
            )
            db.commit()
        return redirect(url_for("index", date=meal_date, mode=mode or None))

    @app.post("/meals/<int:meal_id>/delete")
    def delete_meal(meal_id: int):
        db = get_db()
        meal = db.execute("SELECT meal_date FROM meal_entries WHERE id = ?", (meal_id,)).fetchone()
        mode = request.form.get("mode")
        db.execute("DELETE FROM meal_entries WHERE id = ?", (meal_id,))
        db.commit()
        return redirect(url_for("index", date=meal["meal_date"] if meal else None, mode=mode or None))

    @app.post("/sets/<int:set_id>/update")
    def update_set(set_id: int):
        db = get_db()
        workout = db.execute(
            """
            SELECT s.workout_date, ws.body_part, e.name AS exercise_name
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            JOIN exercises e ON e.id = ws.exercise_id
            WHERE ws.id = ?
            """,
            (set_id,),
        ).fetchone()
        workout_date = workout["workout_date"] if workout else current_local_date()
        mode = request.form.get("mode")
        preferences = get_app_preferences()
        default_set_type = str(preferences["set_type_options"][0]) if preferences["set_type_options"] else "본세트"
        equipment = normalize_equipment_category(request.form.get("equipment", ""))
        equipment_brand = request.form.get("equipment_brand", "").strip()[:30]
        body_part = request.form.get("body_part", workout["body_part"] if workout else "").strip() or "기타"
        exercise_name = request.form.get("exercise_name", workout["exercise_name"] if workout else "").strip()
        exercise_id = get_or_create_exercise(exercise_name) if exercise_name else None
        if exercise_name and equipment:
            save_exercise_equipment(exercise_name, equipment)
        if body_part == "유산소":
            cardio_incline = parse_float(request.form.get("cardio_incline"))
            cardio_speed = parse_float(request.form.get("cardio_speed"))
            cardio_minutes = parse_float(request.form.get("cardio_minutes"))
            db.execute(
                """
                UPDATE workout_sets
                SET exercise_id = COALESCE(?, exercise_id),
                    body_part = ?,
                    weight = NULL,
                    reps = NULL,
                    set_type = ?,
                    cardio_incline = ?,
                    cardio_speed = ?,
                    cardio_minutes = ?,
                    estimated_calories = ?,
                    rpe = ?,
                    equipment = ?,
                    equipment_brand = ?
                WHERE id = ?
                """,
                (
                    exercise_id,
                    body_part,
                    body_part,
                    cardio_incline,
                    cardio_speed,
                    cardio_minutes,
                    estimate_exercise_calories(body_part, cardio_incline, cardio_speed, cardio_minutes, workout_date),
                    parse_float(request.form.get("rpe")),
                    equipment[:20],
                    equipment_brand,
                    set_id,
                ),
            )
        else:
            db.execute(
                """
                UPDATE workout_sets
                SET exercise_id = COALESCE(?, exercise_id),
                    body_part = ?,
                    weight = ?,
                    reps = ?,
                    set_type = ?,
                    rpe = ?,
                    equipment = ?,
                    equipment_brand = ?,
                    cardio_incline = NULL,
                    cardio_speed = NULL,
                    cardio_minutes = NULL,
                    estimated_calories = NULL
                WHERE id = ?
                """,
                (
                    exercise_id,
                    body_part,
                    parse_weight_kg(request.form.get("weight"), request.form.get("weight_unit", "kg")),
                    parse_int(request.form.get("reps")),
                    request.form.get("set_type", default_set_type).strip() or default_set_type,
                    parse_float(request.form.get("rpe")),
                    equipment[:20],
                    equipment_brand,
                    set_id,
                ),
            )
        requested_set_number = parse_int(request.form.get("set_number"))
        if requested_set_number:
            reorder_set_within_exercise(db, set_id, requested_set_number)
        db.commit()
        return redirect(url_for("index", date=workout_date, mode=mode or None))

    @app.post("/sessions/<int:session_id>/exercise-name/update")
    def update_session_exercise_name(session_id: int):
        db = get_db()
        workout = db.execute(
            "SELECT workout_date FROM workout_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        workout_date = workout["workout_date"] if workout else current_local_date()
        mode = request.form.get("mode")
        old_name = request.form.get("old_exercise_name", "").strip()
        new_name = request.form.get("exercise_name", "").strip()
        body_part = request.form.get("body_part", "").strip()
        if old_name and new_name and old_name != new_name:
            rows = db.execute(
                """
                SELECT ws.id
                FROM workout_sets ws
                JOIN exercises e ON e.id = ws.exercise_id
                WHERE ws.session_id = ?
                  AND e.name = ?
                  AND COALESCE(ws.body_part, '기타') = ?
                """,
                (session_id, old_name, body_part or "기타"),
            ).fetchall()
            set_ids = [row["id"] for row in rows]
            if set_ids:
                new_exercise_id = get_or_create_exercise(new_name)
                placeholders = ",".join("?" for _ in set_ids)
                db.execute(
                    f"UPDATE workout_sets SET exercise_id = ? WHERE id IN ({placeholders})",
                    (new_exercise_id, *set_ids),
                )
                db.execute(
                    f"UPDATE pr_events SET exercise_id = ?, exercise_name = ? WHERE set_id IN ({placeholders})",
                    (new_exercise_id, new_name, *set_ids),
                )
                db.execute(
                    """
                    INSERT INTO exercise_settings (
                        exercise_name, location_id, rest_seconds, is_favorite, equipment,
                        target_weight, target_reps, target_sets, updated_at
                    )
                    SELECT ?, location_id, rest_seconds, is_favorite, equipment,
                        target_weight, target_reps, target_sets, CURRENT_TIMESTAMP
                    FROM exercise_settings
                    WHERE exercise_name = ?
                      AND NOT EXISTS (
                          SELECT 1 FROM exercise_settings WHERE exercise_name = ?
                      )
                    """,
                    (new_name, old_name, new_name),
                )
                db.execute(
                    """
                    INSERT INTO exercise_notes (exercise_name, note, updated_at)
                    SELECT ?, note, CURRENT_TIMESTAMP
                    FROM exercise_notes
                    WHERE exercise_name = ?
                      AND NOT EXISTS (
                          SELECT 1 FROM exercise_notes WHERE exercise_name = ?
                      )
                    """,
                    (new_name, old_name, new_name),
                )
                db.commit()
        return redirect(url_for("index", date=workout_date, mode=mode or None))

    @app.post("/sets/<int:set_id>/delete")
    def delete_set(set_id: int):
        db = get_db()
        workout = db.execute(
            """
            SELECT s.workout_date
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            WHERE ws.id = ?
            """,
            (set_id,),
        ).fetchone()
        mode = request.form.get("mode")
        db.execute("DELETE FROM workout_sets WHERE id = ?", (set_id,))
        db.commit()
        return redirect(url_for("index", date=workout["workout_date"] if workout else None, mode=mode or None))

