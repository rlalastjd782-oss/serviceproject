from __future__ import annotations

import sqlite3

from health_tracker.app_database import get_db


def get_exercise_profile(exercise_id: int | None) -> dict[str, object] | None:
    if not exercise_id:
        return None
    row = get_db().execute(
        """
        SELECT
            e.name,
            COALESCE(NULLIF(MAX(ws.body_part), ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COUNT(DISTINCT s.workout_date) AS workout_days,
            MAX(s.workout_date) AS last_date,
            COALESCE(MAX(ws.weight), 0) AS best_weight,
            COALESCE(MAX(ws.reps), 0) AS best_reps,
            COALESCE(MAX(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS best_volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories
        FROM exercises e
        LEFT JOIN workout_sets ws ON ws.exercise_id = e.id
        LEFT JOIN workout_sessions s ON s.id = ws.session_id
        WHERE e.id = ?
        GROUP BY e.id, e.name
        """,
        (exercise_id,),
    ).fetchone()
    return dict(row) if row else None


def build_exercise_next_plan(exercise_id: int | None) -> list[str]:
    if not exercise_id:
        return []
    row = get_db().execute(
        """
        SELECT
            e.name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            s.workout_date
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.exercise_id = ?
        ORDER BY s.workout_date DESC, ws.sort_order DESC, ws.id DESC
        LIMIT 1
        """,
        (exercise_id,),
    ).fetchone()
    if not row:
        return ["아직 기록이 적어서 다음 목표를 만들 수 없습니다. 먼저 1회 기록을 남겨주세요."]

    body_part = row["body_part"] or "기타"
    if body_part == "유산소":
        minutes = float(row["cardio_minutes"] or 0)
        speed = float(row["cardio_speed"] or 0)
        incline = float(row["cardio_incline"] or 0)
        suggestions = []
        if minutes:
            suggestions.append(f"다음 유산소는 {minutes + 2:.0f}분을 1차 목표로 잡아보세요.")
        if speed:
            suggestions.append(f"컨디션이 좋으면 속도 {speed + 0.1:.1f}까지 올려보세요.")
        if incline:
            suggestions.append(f"인클라인은 {incline:.1f}을 유지하고 시간을 먼저 늘리는 편이 안정적입니다.")
        return suggestions or ["다음 유산소는 시간, 속도, 인클라인 중 하나만 올려서 기록해보세요."]

    weight = float(row["weight"] or 0)
    reps = int(row["reps"] or 0)
    if weight <= 0 or reps <= 0:
        return ["최근 세트에 중량/횟수가 비어 있습니다. 다음 기록부터 중량과 횟수를 같이 남겨주세요."]
    if reps >= 10:
        return [
            f"최근 {weight:.1f}kg x {reps}회까지 했습니다. 다음 목표는 {weight + 2.5:.1f}kg로 6~8회입니다.",
            "중량을 올린 날은 첫 세트 성공률을 보고 나머지 세트는 같은 중량으로 유지하세요.",
        ]
    return [
        f"최근 {weight:.1f}kg x {reps}회입니다. 다음 목표는 같은 중량으로 {reps + 1}회입니다.",
        "목표 횟수에 도달하면 그 다음 운동에서 2.5kg 증량을 고려하세요.",
    ]


def build_exercise_trend_summary(exercise_id: int | None) -> list[dict[str, object]]:
    if not exercise_id:
        return []
    rows = get_db().execute(
        """
        SELECT
            s.workout_date,
            MAX(COALESCE(ws.weight, 0)) AS max_weight,
            MAX(COALESCE(ws.weight, 0) * (1 + COALESCE(ws.reps, 0) / 30.0)) AS estimated_1rm,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.exercise_id = ?
        GROUP BY s.workout_date
        ORDER BY s.workout_date ASC
        """,
        (exercise_id,),
    ).fetchall()
    if not rows:
        return []
    first = rows[0]
    last = rows[-1]
    return [
        {
            "label": "중량 변화",
            "value": float(last["max_weight"] or 0) - float(first["max_weight"] or 0),
            "unit": "kg",
            "current": float(last["max_weight"] or 0),
        },
        {
            "label": "1RM 변화",
            "value": float(last["estimated_1rm"] or 0) - float(first["estimated_1rm"] or 0),
            "unit": "kg",
            "current": float(last["estimated_1rm"] or 0),
        },
        {
            "label": "볼륨 변화",
            "value": float(last["volume"] or 0) - float(first["volume"] or 0),
            "unit": "kg",
            "current": float(last["volume"] or 0),
        },
        {
            "label": "유산소 변화",
            "value": float(last["cardio_minutes"] or 0) - float(first["cardio_minutes"] or 0),
            "unit": "분",
            "current": float(last["cardio_minutes"] or 0),
        },
    ]


def build_exercise_growth_chart(exercise_id: int | None, limit: int = 10) -> list[dict[str, float | int | str]]:
    if not exercise_id:
        return []
    profile = get_exercise_profile(exercise_id)
    is_cardio = bool(profile and profile.get("body_part") == "유산소")
    rows = get_db().execute(
        """
        SELECT
            s.workout_date AS period,
            MAX(COALESCE(ws.weight, 0)) AS max_weight,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            MAX(COALESCE(ws.weight, 0) * (1 + COALESCE(ws.reps, 0) / 30.0)) AS estimated_1rm,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            MAX(COALESCE(ws.cardio_speed, 0)) AS cardio_speed,
            MAX(COALESCE(ws.cardio_incline, 0)) AS cardio_incline
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.exercise_id = ?
        GROUP BY s.workout_date
        ORDER BY s.workout_date DESC
        LIMIT ?
        """,
        (exercise_id, limit),
    ).fetchall()
    ordered = list(reversed(rows))
    max_weight = max([float(row["max_weight"]) for row in ordered] + [1.0])
    max_volume = max([float(row["volume"]) for row in ordered] + [1.0])
    max_1rm = max([float(row["estimated_1rm"]) for row in ordered] + [1.0])
    max_minutes = max([float(row["cardio_minutes"]) for row in ordered] + [1.0])
    max_speed = max([float(row["cardio_speed"]) for row in ordered] + [1.0])
    max_incline = max([float(row["cardio_incline"]) for row in ordered] + [1.0])
    return [
        {
            "period": row["period"][5:],
            "is_cardio": is_cardio,
            "max_weight": float(row["max_weight"]),
            "rep_count": int(row["rep_count"]),
            "volume": float(row["volume"]),
            "estimated_1rm": float(row["estimated_1rm"]),
            "cardio_minutes": float(row["cardio_minutes"]),
            "cardio_speed": float(row["cardio_speed"]),
            "cardio_incline": float(row["cardio_incline"]),
            "weight_height": max(3, round(float(row["max_weight"]) / max_weight * 100)),
            "weight_width": round(float(row["max_weight"]) / max_weight * 100),
            "volume_height": max(3, round(float(row["volume"]) / max_volume * 100)),
            "volume_width": round(float(row["volume"]) / max_volume * 100),
            "estimated_1rm_width": round(float(row["estimated_1rm"]) / max_1rm * 100),
            "cardio_minutes_width": round(float(row["cardio_minutes"]) / max_minutes * 100),
            "cardio_speed_width": round(float(row["cardio_speed"]) / max_speed * 100),
            "cardio_incline_width": round(float(row["cardio_incline"]) / max_incline * 100),
        }
        for row in ordered
    ]


def list_exercise_pr_timeline(exercise_id: int | None, limit: int = 12) -> list[dict[str, object]]:
    if not exercise_id:
        return []
    rows = get_db().execute(
        """
        SELECT
            s.workout_date,
            MAX(COALESCE(ws.weight, 0)) AS max_weight,
            MAX(COALESCE(ws.weight, 0) * (1 + COALESCE(ws.reps, 0) / 30.0)) AS estimated_1rm,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.exercise_id = ?
        GROUP BY s.workout_date
        ORDER BY s.workout_date DESC
        LIMIT ?
        """,
        (exercise_id, limit),
    ).fetchall()
    ordered = list(reversed(rows))
    max_weight = max([float(row["max_weight"] or 0) for row in ordered] + [1.0])
    max_1rm = max([float(row["estimated_1rm"] or 0) for row in ordered] + [1.0])
    return [
        {
            "period": row["workout_date"][5:],
            "max_weight": float(row["max_weight"] or 0),
            "estimated_1rm": float(row["estimated_1rm"] or 0),
            "volume": float(row["volume"] or 0),
            "weight_width": round(float(row["max_weight"] or 0) / max_weight * 100),
            "estimated_1rm_width": round(float(row["estimated_1rm"] or 0) / max_1rm * 100),
        }
        for row in ordered
    ]


def list_exercise_recent_sets(exercise_id: int | None, limit: int = 12) -> list[sqlite3.Row]:
    if not exercise_id:
        return []
    return get_db().execute(
        """
        SELECT
            s.workout_date,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            ws.weight,
            ws.reps,
            ws.set_type,
            ws.rpe,
            ws.equipment,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.estimated_calories
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE ws.exercise_id = ?
        ORDER BY s.workout_date DESC, ws.sort_order DESC, ws.id DESC
        LIMIT ?
        """,
        (exercise_id, limit),
    ).fetchall()


def search_workout_records_filtered(
    query: str = "",
    body_part: str = "",
    equipment: str = "",
    start_date: str = "",
    end_date: str = "",
    limit: int = 120,
) -> list[sqlite3.Row]:
    where = []
    params: list[object] = []
    if query:
        where.append("(e.name LIKE ? OR ws.memo LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    if body_part:
        where.append("COALESCE(NULLIF(ws.body_part, ''), '기타') = ?")
        params.append(body_part)
    if equipment:
        where.append("COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') = ?")
        params.append(equipment)
    if start_date:
        where.append("s.workout_date >= ?")
        params.append(start_date)
    if end_date:
        where.append("s.workout_date <= ?")
        params.append(end_date)
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    params.append(limit)
    return get_db().execute(
        f"""
        SELECT
            s.workout_date,
            e.name AS exercise_name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') AS equipment,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.estimated_calories,
            ws.rpe,
            ws.memo
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        {where_sql}
        ORDER BY s.workout_date DESC, ws.sort_order ASC, ws.id ASC
        LIMIT ?
        """,
        params,
    ).fetchall()

