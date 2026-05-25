from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE = BASE_DIR / "instance" / "workout.db"
PHOTO_DIR = BASE_DIR / "static" / "progress_photos"
