from __future__ import annotations

from pathlib import Path


STATIC_DEPLOYMENT_PATHS = (
    "/static/css/styles.css",
    "/static/js/app.js",
    "/static/manifest.webmanifest",
    "/static/icon.svg",
    "/sw.js",
    "/favicon.ico",
)

PYTHONANYWHERE_STATIC_URL = "/static/"


def build_deployment_checklist(base_dir: Path) -> dict[str, object]:
    static_dir = base_dir / "static"
    return {
        "pythonanywhere_static_url": PYTHONANYWHERE_STATIC_URL,
        "pythonanywhere_static_directory": str(static_dir),
        "expected_paths": list(STATIC_DEPLOYMENT_PATHS),
        "local_static_exists": static_dir.exists(),
    }
