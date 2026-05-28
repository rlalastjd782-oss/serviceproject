from __future__ import annotations

from urllib.parse import urlparse

from flask import redirect, render_template, request, session, url_for


def register_auth_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

    def safe_next_url(value: str | None) -> str:
        value = (value or "").strip()
        parsed = urlparse(value)
        if not value or parsed.scheme or parsed.netloc or not value.startswith("/"):
            return ""
        if value.startswith("/login") or value.startswith("/auth/login"):
            return ""
        return value

    @app.get("/auth/login")
    def login_page():
        return render_template(
            "auth/login.html",
            active_page="settings",
            error=request.args.get("error", ""),
            mode=request.args.get("mode", "user"),
            next_url=safe_next_url(request.args.get("next")),
        )

    @app.get("/login")
    def legacy_login_page():
        return redirect(
            url_for(
                "login_page",
                mode=request.args.get("mode", "user"),
                error=request.args.get("error", ""),
                next=safe_next_url(request.args.get("next")),
            )
        )

    @app.get("/auth/signup")
    def signup_page():
        return render_template(
            "auth/signup.html",
            error=request.args.get("error", ""),
            next_url=safe_next_url(request.args.get("next")),
        )

    @app.get("/auth/preview")
    def preview_page():
        return render_template("auth/preview.html")

    @app.post("/auth/login")
    @app.post("/login")
    def login_route():
        login_mode = request.form.get("login_mode", "user")
        next_url = safe_next_url(request.form.get("next"))
        account = verify_account(request.form.get("username", ""), request.form.get("password", ""))
        if not account:
            return redirect(url_for("login_page", mode=login_mode, error="invalid", next=next_url))
        if login_mode == "admin" and account["role"] != "admin":
            return redirect(url_for("login_page", mode="admin", error="not_admin", next=next_url))
        if login_mode == "user" and account["role"] != "user":
            return redirect(url_for("login_page", mode="user", error="not_user", next=next_url))
        session["account_id"] = int(account["id"])
        session["settings_unlocked"] = True
        mark_account_login(int(account["id"]))
        if account["role"] == "admin":
            return redirect(url_for("admin_dashboard_page"))
        return redirect(next_url or url_for("index"))

    @app.post("/signup")
    @app.post("/auth/signup")
    def signup_route():
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        next_url = safe_next_url(request.form.get("next"))
        if password != password_confirm:
            return redirect(url_for("signup_page", error="signup_password", next=next_url))
        ok, error = create_account(
            request.form.get("username", ""),
            password,
            request.form.get("username", ""),
            "user",
        )
        if not ok:
            return redirect(url_for("signup_page", error=f"signup_{error}", next=next_url))
        account = verify_account(request.form.get("username", ""), password)
        if account:
            session["account_id"] = int(account["id"])
            session["settings_unlocked"] = True
            mark_account_login(int(account["id"]))
        return redirect(next_url or url_for("index"))

    @app.post("/auth/logout")
    @app.post("/logout")
    def logout_route():
        session.clear()
        return redirect(url_for("login_page"))
