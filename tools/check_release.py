from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC_ASSETS = [
    "static/css/styles.css",
    "static/css/today.css",
    "static/css/feature_pages.css",
    "static/css/meal.css",
    "static/css/analysis.css",
    "static/css/responsive.css",
    "static/css/rules.css",
    "static/css/ui_rebuild.css",
    "static/js/dom_data.js",
    "static/js/pwa.js",
    "static/js/select_theme.js",
    "static/js/readiness.js",
    "static/js/form_submit.js",
    "static/js/app.js",
    "static/js/workout_entry.js",
    "static/manifest.webmanifest",
    "static/icon.svg",
]


def main() -> int:
    errors: list[str] = []
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    manifest = json.loads((ROOT / "static" / "manifest.webmanifest").read_text(encoding="utf-8"))
    sw_source = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    cache_match = re.search(r'CACHE_NAME = "workout-pwa-v([^"]+)"', sw_source)
    cache_version = cache_match.group(1) if cache_match else ""

    if manifest.get("version") != version:
        errors.append(f"manifest version mismatch: {manifest.get('version')} != {version}")
    if cache_version != version:
        errors.append(f"service worker cache mismatch: {cache_version} != {version}")
    for asset in STATIC_ASSETS:
        if not (ROOT / asset).exists():
            errors.append(f"missing static asset: {asset}")

    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    print(f"OK release {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
