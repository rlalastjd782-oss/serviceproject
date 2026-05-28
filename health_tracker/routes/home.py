from __future__ import annotations

from health_tracker.services.today_context import build_today_context


def register_home_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

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
