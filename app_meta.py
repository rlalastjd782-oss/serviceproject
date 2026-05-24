from __future__ import annotations

import os
from datetime import datetime

from app_config import BASE_DIR


def get_app_version() -> str:
    env_version = os.environ.get("APP_VERSION", "").strip()
    if env_version:
        return env_version

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
    ref_path = BASE_DIR / ".git" / "refs" / "heads" / "master"
    fallback_path = BASE_DIR / "app.py"
    target_path = ref_path if ref_path.exists() else fallback_path
    try:
        return datetime.fromtimestamp(target_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return datetime.now().strftime("%Y-%m-%d %H:%M")
