from __future__ import annotations

from flask import redirect, render_template, request, session, url_for

from health_tracker.services.settings_context import build_settings_context


def register_settings_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

    @app.get("/settings")
    def settings_page():
        if not settings_unlocked():
            return render_template(
                "settings/lock.html",
                active_page="settings",
                has_password=has_settings_password(),
                error=request.args.get("error", ""),
            )
        return render_template("settings/index.html", **build_settings_context(request.args, globals()))

    @app.post("/settings/unlock")
    def unlock_settings_route():
        password = request.form.get("password", "")
        if verify_settings_password(password):
            session["settings_unlocked"] = True
            return redirect(url_for("settings_page"))
        return redirect(url_for("settings_page", error="invalid"))

    @app.post("/settings/password")
    def save_settings_password_route():
        if has_settings_password() and not settings_unlocked():
            return redirect(url_for("settings_page"))
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        if password != password_confirm or not set_settings_password(password):
            return redirect(url_for("settings_page", error="password"))
        return redirect(url_for("settings_page"))

    @app.post("/settings/password/reset")
    def reset_settings_password_route():
        if settings_unlocked() and request.form.get("confirm_reset", "").strip() == "RESET":
            reset_settings_password()
        return redirect(url_for("settings_page"))

    @app.post("/settings/app-preferences")
    def save_app_preferences_route():
        if settings_unlocked():
            save_app_preferences(request.form)
        return redirect(url_for("settings_page"))

    @app.post("/settings/accounts")
    def create_account_route():
        if not settings_unlocked():
            return redirect(url_for("settings_page"))
        ok, error = create_account(
            request.form.get("username", ""),
            request.form.get("password", ""),
            request.form.get("display_name", ""),
            request.form.get("role", "user"),
        )
        if not ok:
            return redirect(url_for("settings_page", error=f"account_{error}"))
        return redirect(url_for("settings_page"))

    @app.post("/settings/lock")
    def lock_settings_route():
        session.pop("settings_unlocked", None)
        return redirect(url_for("settings_page"))

    @app.post("/qa-dummy/year")
    def generate_year_qa_dummy_route():
        if settings_unlocked():
            generate_year_qa_dummy_data()
        return redirect(url_for("settings_page"))

    @app.post("/data/cleanup-empty")
    def cleanup_empty_data_route():
        delete_empty_workout_sessions()
        get_db().commit()
        return redirect(url_for("settings_page"))
