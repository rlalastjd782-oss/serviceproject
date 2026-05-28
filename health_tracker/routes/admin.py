from __future__ import annotations

import json
import sqlite3
from contextlib import closing

from health_tracker.services.export import export_all_data_from_db


def register_admin_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

    def require_admin():
        if not is_admin_account():
            return redirect(url_for("login_page", mode="admin", error="admin_required"))
        return None

    def require_user_account(account_id: int):
        account = account_by_id(account_id)
        if not account:
            abort(404)
        if account["role"] != "user":
            return None, redirect(url_for("admin_dashboard_page", error="user_only"))
        return account, None

    def exportable_usage_summary(usage: dict[str, object]) -> dict[str, object]:
        return {
            key: ([dict(row) for row in value] if isinstance(value, list) else value)
            for key, value in usage.items()
            if key not in {"account"}
        }

    @app.get("/admin")
    def admin_dashboard_page():
        blocked = require_admin()
        if blocked:
            return blocked
        dashboard = build_admin_dashboard(
            account_options(),
            query=request.args.get("q", ""),
            status=request.args.get("status", "all"),
            sort_key=request.args.get("sort", "id"),
        )
        return render_template(
            "admin/dashboard.html",
            active_page="admin",
            dashboard=dashboard,
            audit_logs=admin_audit_logs(12),
        )

    @app.get("/admin/users/<int:account_id>")
    def admin_user_detail_page(account_id: int):
        blocked = require_admin()
        if blocked:
            return blocked
        account, account_blocked = require_user_account(account_id)
        if account_blocked:
            return account_blocked
        usage = build_account_usage(account)
        return render_template(
            "admin/user_detail.html",
            active_page="admin",
            usage=usage,
            error=request.args.get("error", ""),
            audit_logs=admin_audit_logs(8),
        )

    @app.post("/admin/users/<int:account_id>/password")
    def admin_reset_user_password_route(account_id: int):
        blocked = require_admin()
        if blocked:
            return blocked
        account, account_blocked = require_user_account(account_id)
        if account_blocked:
            return account_blocked
        if not reset_user_password(account_id, request.form.get("password", "")):
            return redirect(url_for("admin_user_detail_page", account_id=account_id, error="password"))
        log_admin_action("password_reset", account_id, f"{account['username']} 비밀번호 초기화")
        return redirect(url_for("admin_user_detail_page", account_id=account_id))

    @app.post("/admin/password")
    def admin_update_own_password_route():
        blocked = require_admin()
        if blocked:
            return blocked
        account = current_account()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        new_password_confirm = request.form.get("new_password_confirm", "")
        if (
            not account
            or not verify_account(account["username"], current_password)
            or new_password != new_password_confirm
            or not reset_user_password(int(account["id"]), new_password)
            or not set_settings_password(new_password)
        ):
            return redirect(url_for("admin_dashboard_page", error="password"))
        log_admin_action("admin_password_change", int(account["id"]), "관리자 비밀번호 변경")
        return redirect(url_for("admin_dashboard_page", updated="password"))

    @app.post("/admin/users/<int:account_id>/status")
    def admin_update_user_status_route(account_id: int):
        blocked = require_admin()
        if blocked:
            return blocked
        account, account_blocked = require_user_account(account_id)
        if account_blocked:
            return account_blocked
        action = request.form.get("action", "")
        if action == "disable" and request.form.get("confirm_status", "").strip() == "비활성화":
            set_user_active(account_id, False)
            log_admin_action("user_disable", account_id, f"{account['username']} 비활성화")
        elif action == "enable":
            set_user_active(account_id, True)
            log_admin_action("user_enable", account_id, f"{account['username']} 활성화")
        return redirect(url_for("admin_user_detail_page", account_id=account_id))

    @app.post("/admin/users/<int:account_id>/memo")
    def admin_update_user_memo_route(account_id: int):
        blocked = require_admin()
        if blocked:
            return blocked
        account, account_blocked = require_user_account(account_id)
        if account_blocked:
            return account_blocked
        save_user_admin_note(account_id, request.form.get("memo", ""), request.form.get("display_name", ""))
        log_admin_action("user_memo_update", account_id, f"{account['username']} 메모/표시 이름 수정")
        return redirect(url_for("admin_user_detail_page", account_id=account_id))

    @app.get("/admin/users/<int:account_id>/export")
    def admin_export_user_data_route(account_id: int):
        blocked = require_admin()
        if blocked:
            return blocked
        account, account_blocked = require_user_account(account_id)
        if account_blocked:
            return account_blocked
        db_path = account_db_path(DATABASE, account_id)
        if not db_path.exists():
            abort(404)
        with closing(sqlite3.connect(db_path)) as db:
            db.row_factory = sqlite3.Row
            payload = export_all_data_from_db(db)
        payload["account"] = {
            "id": int(account["id"]),
            "username": account["username"],
            "display_name": account["display_name"],
        }
        payload["usage_summary"] = exportable_usage_summary(build_account_usage(account))
        log_admin_action("user_export", account_id, f"{account['username']} 데이터 내보내기")
        body = json.dumps(payload, ensure_ascii=False, indent=2)
        filename = f"user-{account_id}-{account['username']}-export.json"
        return Response(
            body,
            mimetype="application/json; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
