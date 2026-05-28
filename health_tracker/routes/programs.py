from __future__ import annotations


def register_program_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

    @app.post("/programs/apply")
    def apply_program_route():
        workout_date = normalize_date(request.form.get("workout_date"))
        apply_default_program(request.form.get("program_name", ""), workout_date)
        return redirect(url_for("index", date=workout_date, mode=request.form.get("mode") or None))
