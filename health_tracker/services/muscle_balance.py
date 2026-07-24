from __future__ import annotations

import sqlite3
from collections.abc import Callable


TARGET_BODY_PARTS = ("하체", "가슴", "등", "어깨", "팔(이두)", "팔(삼두)", "유산소")


def build_muscle_balance(
    db: sqlite3.Connection,
    start_date: str,
    end_date: str,
    body_part_class: Callable[[str | None], str],
) -> dict[str, object]:
    rows = db.execute(
        """
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date BETWEEN ? AND ?
        GROUP BY body_part
        """,
        (start_date, end_date),
    ).fetchall()
    by_part = {row["body_part"]: row for row in rows}
    max_sets = max([int(row["set_count"] or 0) for row in rows] + [1])
    items = []
    missing = []
    overworked = []
    for part in TARGET_BODY_PARTS:
        row = by_part.get(part)
        set_count = int(row["set_count"] or 0) if row else 0
        intensity = round(set_count / max_sets * 100) if max_sets else 0
        if set_count == 0:
            state = "부족"
            missing.append(part)
        elif set_count >= max(12, max_sets * 0.75) and part != "유산소":
            state = "높음"
            overworked.append(part)
        else:
            state = "적정"
        items.append(
            {
                "body_part": part,
                "class_name": body_part_class(part),
                "set_count": set_count,
                "volume": float(row["volume"] or 0) if row else 0,
                "cardio_minutes": float(row["cardio_minutes"] or 0) if row else 0,
                "last_date": row["last_date"] if row else "",
                "intensity": intensity,
                "state": state,
            }
        )
    message = "부위 분포가 안정적입니다."
    if missing:
        message = f"보강 후보: {', '.join(missing[:3])}"
    elif overworked:
        message = f"최근 사용량이 높은 부위: {', '.join(overworked[:2])}"
    return {
        "period": f"{start_date} ~ {end_date}",
        "items": items,
        "missing": missing,
        "overworked": overworked,
        "message": message,
    }
