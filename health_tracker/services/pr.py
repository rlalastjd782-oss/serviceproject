from __future__ import annotations

import sqlite3


def build_pr_cards_from_rows(rows: list[sqlite3.Row]) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    for row in rows:
        unit = "kg" if row["record_type"] in {"최고 중량", "최고 볼륨"} else "회"
        cards.append(
            {
                "exercise_name": row["exercise_name"],
                "record_type": row["record_type"],
                "record_value": float(row["record_value"] or 0),
                "unit": unit,
            }
        )
    return cards


def build_pr_dashboard_from_rows(pr_rows: list[sqlite3.Row], recent_events: list[sqlite3.Row]) -> dict[str, object]:
    best_weight = max(pr_rows, key=lambda row: float(row["best_weight"] or 0), default=None)
    best_volume = max(pr_rows, key=lambda row: float(row["best_volume"] or 0), default=None)
    best_1rm = max(pr_rows, key=lambda row: float(row["estimated_1rm"] or 0), default=None)
    recent_30_dates = {row["workout_date"] for row in recent_events[:30]}
    return {
        "exercise_count": len(pr_rows),
        "recent_event_count": len(recent_events),
        "recent_day_count": len(recent_30_dates),
        "best_weight": best_weight,
        "best_volume": best_volume,
        "best_1rm": best_1rm,
    }
