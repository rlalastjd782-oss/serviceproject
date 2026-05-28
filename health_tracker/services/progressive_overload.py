from __future__ import annotations

import sqlite3
from datetime import datetime


def estimated_1rm(weight: float, reps: int) -> float:
    return round(weight * (1 + reps / 30), 1) if weight > 0 and reps > 0 else 0.0


def classify_overload_state(rows: list[sqlite3.Row]) -> tuple[str, str]:
    if len(rows) < 2:
        return "기록 부족", "비교할 최근 기록이 더 필요합니다."
    ordered = list(reversed(rows))
    first = ordered[0]
    last = ordered[-1]
    first_volume = float(first["volume"] or 0)
    last_volume = float(last["volume"] or 0)
    first_1rm = float(first["estimated_1rm"] or 0)
    last_1rm = float(last["estimated_1rm"] or 0)
    recent_rpe = float(last["avg_rpe"] or 0)
    if recent_rpe >= 9 and last_volume < first_volume * 1.05:
        return "회복 필요", "최근 체감강도가 높고 볼륨 증가가 제한적입니다."
    if last_1rm > first_1rm * 1.03 or last_volume > first_volume * 1.08:
        return "상승", "최근 기록이 중량 또는 볼륨 기준으로 상승 중입니다."
    if abs(last_volume - first_volume) <= max(50, first_volume * 0.03):
        return "정체", "최근 볼륨 변화가 작습니다. 반복 1회 또는 소폭 증량을 검토하세요."
    return "유지", "최근 기록은 유지권입니다. 세트 완성도를 우선하세요."


def next_set_advice_from_recent(
    exercise_name: str,
    body_part: str,
    rows: list[sqlite3.Row],
    readiness_percent: int = 60,
) -> dict[str, object]:
    if not rows:
        return {
            "exercise_name": exercise_name,
            "body_part": body_part or "기타",
            "type": "기록 시작",
            "weight": None,
            "reps": None,
            "sets": 3,
            "reason": "이 운동의 최근 기록이 없습니다. 편한 중량으로 기준 기록을 만드세요.",
        }
    recent = rows[0]
    weight = float(recent["max_weight"] or 0)
    reps = int(recent["max_reps"] or 0)
    avg_rpe = float(recent["avg_rpe"] or 0)
    state, _ = classify_overload_state(rows[:5])
    advice_type = "유지"
    target_weight = weight
    target_reps = reps
    target_sets = 3
    if body_part == "유산소":
        minutes = float(recent["cardio_minutes"] or 0)
        return {
            "exercise_name": exercise_name,
            "body_part": body_part,
            "type": "시간 증가" if readiness_percent >= 60 else "가볍게 유지",
            "weight": None,
            "reps": None,
            "sets": 1,
            "cardio_minutes": round(minutes + 2 if readiness_percent >= 60 and minutes else minutes or 20),
            "reason": "최근 유산소 시간을 기준으로 다음 목표를 계산했습니다.",
        }
    if readiness_percent < 50 or avg_rpe >= 9:
        advice_type = "감량/유지"
        target_weight = max(0, weight - 2.5) if avg_rpe >= 9 else weight
        target_reps = max(1, reps)
        target_sets = 2
    elif state in {"상승", "유지"} and reps >= 10:
        advice_type = "소폭 증량"
        target_weight = weight + 2.5
        target_reps = max(5, reps - 2)
    elif state == "정체":
        advice_type = "반복 추가"
        target_reps = reps + 1
    else:
        advice_type = "기록 반복"
        target_reps = reps + 1 if reps else None
    return {
        "exercise_name": exercise_name,
        "body_part": body_part or "기타",
        "type": advice_type,
        "weight": round(target_weight, 1) if target_weight else None,
        "reps": target_reps,
        "sets": target_sets,
        "reason": f"{state} · 최근 RPE {avg_rpe:.1f} · 컨디션 {readiness_percent}%",
    }


def recent_performance_rows(db: sqlite3.Connection, exercise_name: str, limit: int = 5) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT
            s.workout_date,
            COALESCE(NULLIF(MAX(ws.body_part), ''), '기타') AS body_part,
            MAX(COALESCE(ws.weight, 0)) AS max_weight,
            MAX(COALESCE(ws.reps, 0)) AS max_reps,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            MAX(COALESCE(ws.weight, 0) * (1 + COALESCE(ws.reps, 0) / 30.0)) AS estimated_1rm,
            AVG(ws.rpe) AS avg_rpe,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE e.name = ?
        GROUP BY s.workout_date
        ORDER BY s.workout_date DESC
        LIMIT ?
        """,
        (exercise_name, limit),
    ).fetchall()


def build_next_set_suggestions(
    db: sqlite3.Connection,
    exercise_names: list[str],
    readiness_percent: int = 60,
    limit: int = 8,
) -> dict[str, dict[str, object]]:
    suggestions: dict[str, dict[str, object]] = {}
    for name in exercise_names[:limit]:
        rows = recent_performance_rows(db, name, limit=5)
        body_part = rows[0]["body_part"] if rows else "기타"
        suggestions[name] = next_set_advice_from_recent(name, body_part, rows, readiness_percent)
    return suggestions


def list_progressive_overload_rows(
    db: sqlite3.Connection,
    limit: int = 30,
) -> list[dict[str, object]]:
    exercises = db.execute(
        """
        SELECT e.name, COALESCE(NULLIF(MAX(ws.body_part), ''), '기타') AS body_part, MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        GROUP BY e.id, e.name
        ORDER BY last_date DESC, e.name
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    items: list[dict[str, object]] = []
    for exercise in exercises:
        rows = recent_performance_rows(db, exercise["name"], limit=6)
        state, reason = classify_overload_state(rows)
        latest = rows[0] if rows else None
        previous = rows[1] if len(rows) > 1 else None
        latest_volume = float(latest["volume"] or 0) if latest else 0
        previous_volume = float(previous["volume"] or 0) if previous else 0
        volume_delta = latest_volume - previous_volume
        items.append(
            {
                "exercise_name": exercise["name"],
                "body_part": exercise["body_part"],
                "last_date": exercise["last_date"],
                "state": state,
                "reason": reason,
                "max_weight": float(latest["max_weight"] or 0) if latest else 0,
                "max_reps": int(latest["max_reps"] or 0) if latest else 0,
                "estimated_1rm": float(latest["estimated_1rm"] or 0) if latest else 0,
                "volume": latest_volume,
                "volume_delta": volume_delta,
                "sessions": len(rows),
                "days_since": (datetime.now().date() - datetime.strptime(exercise["last_date"], "%Y-%m-%d").date()).days
                if exercise["last_date"]
                else None,
            }
        )
    return items


def list_overload_suggestions_from_db(db: sqlite3.Connection) -> dict[str, str]:
    rows = db.execute(
        """
        SELECT e.name, ws.weight, ws.reps, s.workout_date
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.weight IS NOT NULL AND ws.reps IS NOT NULL
        ORDER BY s.workout_date DESC, ws.sort_order DESC, ws.id DESC
        """
    ).fetchall()
    suggestions: dict[str, str] = {}
    for row in rows:
        name = row["name"]
        if name in suggestions:
            continue
        next_weight = float(row["weight"]) + 2.5
        next_reps = int(row["reps"]) + 1
        suggestions[name] = (
            f"최근 기록 기준: {float(row['weight']):.1f}kg {int(row['reps'])}회 -> "
            f"{next_weight:.1f}kg 또는 {next_reps}회 도전"
        )
    return suggestions
