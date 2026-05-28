from __future__ import annotations

import os
from datetime import datetime

from health_tracker.config import BASE_DIR


def normalize_version(version: str) -> str:
    version = version.strip()
    if not version:
        return ""
    return version if version.startswith("v") else f"v{version}"


def get_app_version() -> str:
    env_version = os.environ.get("APP_VERSION", "").strip()
    if env_version:
        return normalize_version(env_version)

    version_path = BASE_DIR / "VERSION"
    try:
        version = version_path.read_text(encoding="utf-8").strip()
        if version:
            return normalize_version(version)
    except OSError:
        pass

    head_path = BASE_DIR / ".git" / "HEAD"
    try:
        head_value = head_path.read_text(encoding="utf-8").strip()
        if head_value.startswith("ref:"):
            ref_path = BASE_DIR / ".git" / head_value.split(" ", 1)[1]
            commit_hash = ref_path.read_text(encoding="utf-8").strip()
        else:
            commit_hash = head_value
        if commit_hash:
            return f"v-{commit_hash[:7]}"
    except OSError:
        pass
    return "local"


def get_app_updated_at() -> str:
    ref_path = BASE_DIR / ".git" / "refs" / "heads" / "main"
    fallback_path = BASE_DIR / "app.py"
    target_path = ref_path if ref_path.exists() else fallback_path
    try:
        return datetime.fromtimestamp(target_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return datetime.now().strftime("%Y-%m-%d %H:%M")
