from __future__ import annotations

from health_tracker.services.today_context import build_today_context
from health_tracker.routes.auth import register_auth_routes
from health_tracker.routes.calendar import register_calendar_routes
from health_tracker.routes.settings import register_settings_routes
from health_tracker.routes.summaries import register_summary_routes
from health_tracker.routes.today_actions import register_today_action_routes
from health_tracker.routes.data import register_data_routes
from health_tracker.routes.entries import register_entry_routes
from health_tracker.routes.meal_pages import register_meal_page_routes
from health_tracker.routes.records import register_record_routes


def register_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)
    register_auth_routes(app, ctx)
    register_settings_routes(app, ctx)


    @app.get("/")
    def root_route():
        account = current_account()
        if not account:
            return redirect(url_for("login_page"))
        if account["role"] == "admin":
            return redirect(url_for("admin_dashboard_page"))
        return redirect(url_for("index"))

    @app.get("/app")
    def index():
        return render_template("today/index.html", **build_today_context(request.args, globals()))

    register_summary_routes(app, globals())

    register_calendar_routes(app, globals())

    register_meal_page_routes(app, globals())

    from health_tracker.routes.auxiliary import register_aux_routes
    from health_tracker.routes.admin import register_admin_routes

    register_aux_routes(app, globals())
    register_admin_routes(app, globals())

    register_today_action_routes(app, globals())

    register_record_routes(app, globals())

    @app.post("/programs/apply")
    def apply_program_route():
        workout_date = normalize_date(request.form.get("workout_date"))
        apply_default_program(request.form.get("program_name", ""), workout_date)
        return redirect(url_for("index", date=workout_date, mode=request.form.get("mode") or None))

    register_data_routes(app, globals())

    register_entry_routes(app, globals())

    @app.get("/api/sessions")
    def api_sessions():
        return jsonify([dict(row) for row in list_recent_sessions(limit=30)])

