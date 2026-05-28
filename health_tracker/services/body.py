from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

BODY_METRIC_COLUMNS = "metric_date, body_weight, muscle_mass, body_fat, waist, created_at, updated_at"


def get_body_metric_from_db(db: sqlite3.Connection, metric_date: str) -> sqlite3.Row | None:
    return db.execute(f"SELECT {BODY_METRIC_COLUMNS} FROM body_metrics WHERE metric_date = ?", (metric_date,)).fetchone()


def save_body_metric_to_db(
    db: sqlite3.Connection,
    metric_date: str,
    body_weight: float | None,
    muscle_mass: float | None,
    body_fat: float | None,
    waist: float | None,
    recalculate_exercise_calories_for_date: Callable[[str], None],
) -> None:
    db.execute(
        """
        INSERT INTO body_metrics (metric_date, body_weight, muscle_mass, body_fat, waist, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(metric_date) DO UPDATE SET
            body_weight = excluded.body_weight,
            muscle_mass = excluded.muscle_mass,
            body_fat = excluded.body_fat,
            waist = excluded.waist,
            updated_at = CURRENT_TIMESTAMP
        """,
        (metric_date, body_weight, muscle_mass, body_fat, waist),
    )
    recalculate_exercise_calories_for_date(metric_date)
    db.commit()


def list_body_metrics_from_db(
    db: sqlite3.Connection,
    month_start: str,
    shift_month: Callable[[str, int], str],
) -> list[sqlite3.Row]:
    return db.execute(
        f"""
        SELECT {BODY_METRIC_COLUMNS}
        FROM body_metrics
        WHERE metric_date >= ? AND metric_date < ?
        ORDER BY metric_date DESC
        """,
        (month_start, shift_month(month_start, 1)),
    ).fetchall()


def build_body_monthly_report_from_rows(rows: list[sqlite3.Row]) -> dict[str, object]:
    if not rows:
        return {"has_data": False}
    first = rows[0]
    last = rows[-1]
    return {
        "has_data": True,
        "first_date": first["metric_date"],
        "last_date": last["metric_date"],
        "body_weight": last["body_weight"],
        "muscle_mass": last["muscle_mass"],
        "body_fat": last["body_fat"],
        "waist": last["waist"],
        "weight_delta": float(last["body_weight"] or 0) - float(first["body_weight"] or 0),
        "muscle_delta": float(last["muscle_mass"] or 0) - float(first["muscle_mass"] or 0),
        "fat_delta": float(last["body_fat"] or 0) - float(first["body_fat"] or 0),
        "waist_delta": float(last["waist"] or 0) - float(first["waist"] or 0),
    }


def list_body_metric_trend_from_rows(rows: list[sqlite3.Row]) -> list[dict[str, object]]:
    max_weight = max([float(row["body_weight"] or 0) for row in rows] + [1.0])
    return [
        {
            "period": row["metric_date"][5:],
            "body_weight": float(row["body_weight"] or 0),
            "muscle_mass": float(row["muscle_mass"] or 0),
            "body_fat": float(row["body_fat"] or 0),
            "weight_width": round(float(row["body_weight"] or 0) / max_weight * 100),
        }
        for row in rows
    ]


def save_body_photo_to_db(db: sqlite3.Connection, photo_dir: Path, photo_date: str, file) -> None:
    photo_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    filename = f"{photo_date}-{datetime.now().strftime('%H%M%S')}{suffix}"
    target = photo_dir / filename
    file.save(target)
    relative_path = f"progress_photos/{filename}"
    db.execute(
        "INSERT INTO body_photos (photo_date, file_path) VALUES (?, ?)",
        (photo_date, relative_path),
    )
    db.commit()


def list_body_photos_from_db(db: sqlite3.Connection, photo_date: str, limit: int = 3) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT id, photo_date, file_path, created_at
        FROM body_photos
        WHERE photo_date <= ?
        ORDER BY photo_date DESC, id DESC
        LIMIT ?
        """,
        (photo_date, limit),
    ).fetchall()
