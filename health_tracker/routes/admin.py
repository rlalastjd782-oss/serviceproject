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
            error=request.args.get("error", ""),
        )

    @app.post("/admin/users/<int:account_id>/password")
    def admin_reset_user_password_route(account_id: int):
        blocked = require_admin()
        if blocked:
            return blocked
        if not reset_user_password(account_id, request.form.get("password", "")):
            return redirect(url_for("admin_user_detail_page", account_id=account_id, error="password"))
        return redirect(url_for("admin_user_detail_page", account_id=account_id))

    @app.post("/admin/users/<int:account_id>/status")
    def admin_update_user_status_route(account_id: int):
        blocked = require_admin()
        if blocked:
            return blocked
        if account_id == 1:
            return redirect(url_for("admin_user_detail_page", account_id=account_id, error="primary"))
        action = request.form.get("action", "")
        if action == "disable" and request.form.get("confirm_status", "").strip() == "비활성화":
            set_user_active(account_id, False)
        elif action == "enable":
            set_user_active(account_id, True)
        return redirect(url_for("admin_user_detail_page", account_id=account_id))

    @app.post("/admin/users/<int:account_id>/memo")
    def admin_update_user_memo_route(account_id: int):
        blocked = require_admin()
        if blocked:
            return blocked
        save_user_admin_note(account_id, request.form.get("memo", ""), request.form.get("display_name", ""))
        return redirect(url_for("admin_user_detail_page", account_id=account_id))
