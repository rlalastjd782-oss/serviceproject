from __future__ import annotations


def register_api_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

    @app.get("/api/sessions")
    def api_sessions():
        return jsonify([dict(row) for row in list_recent_sessions(limit=30)])
