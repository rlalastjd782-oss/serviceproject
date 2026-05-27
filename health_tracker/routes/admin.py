from __future__ import annotations


def register_admin_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

    def require_admin():
        if not is_admin_account():
            return redirect(url_for("login_page", mode="admin", error="admin_required"))
        return None

    @app.get("/admin")
    def admin_dashboard_page():
        blocked = require_admin()
        if blocked:
            return blocked
        dashboard = build_admin_dashboard(account_options())
        return render_template(
            "admin/dashboard.html",
            active_page="admin",
            dashboard=dashboard,
        )

    @app.get("/admin/users/<int:account_id>")
    def admin_user_detail_page(account_id: int):
        blocked = require_admin()
        if blocked:
            return blocked
        account = account_by_id(account_id)
        if not account:
            abort(404)
        usage = build_account_usage(account)
        return render_template(
            "admin/user_detail.html",
            active_page="admin",
            usage=usage,
        )
