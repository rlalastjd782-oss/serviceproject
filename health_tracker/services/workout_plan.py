from __future__ import annotations

import sqlite3
from collections.abc import Callable


def list_workout_plan_from_db(db: sqlite3.Connection, workout_date: str) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT
            wpi.*,
            COALESCE((
                SELECT COUNT(ws.id)
                FROM workout_sets ws
                JOIN workout_sessions s ON s.id = ws.session_id
                JOIN exercises e ON e.id = ws.exercise_id
                WHERE s.workout_date = wpi.workout_date
                  AND e.name = wpi.exercise_name
            ), 0) AS completed_sets
        FROM workout_plan_items wpi
        WHERE wpi.workout_date = ?
        ORDER BY wpi.sort_order, wpi.id
        """,
        (workout_date,),
    ).fetchall()


def build_workout_completion_summary_from_db(
    db: sqlite3.Connection,
    workout_date: str,
    get_or_create_session: Callable[[str | None, int | None], sqlite3.Row],
) -> dict[str, object]:
    session = get_or_create_session(workout_date, None)
    by_part = db.execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date = ?
        GROUP BY body_part
        ORDER BY set_count DESC, body_part
        """,
        (workout_date,),
    ).fetchall()
    top_exercise = db.execute(
        """
        SELECT e.name, COUNT(ws.id) AS set_count,
               COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.workout_date = ?
        GROUP BY e.name
        ORDER BY set_count DESC, volume DESC, e.name
        LIMIT 1
        """,
        (workout_date,),
    ).fetchone()
    plan_rows = list_workout_plan_from_db(db, workout_date)
    plan_total = len(plan_rows)
    plan_done = sum(1 for row in plan_rows if int(row["completed_sets"] or 0) >= int(row["target_sets"] or 1))
    return {
        "completed": bool(session["completed"]),
        "duration_seconds": int(session["duration_seconds"] or 0),
        "body_parts": [dict(row) for row in by_part],
        "top_exercise": dict(top_exercise) if top_exercise else None,
        "plan_total": plan_total,
        "plan_done": plan_done,
        "plan_percent": 0 if plan_total == 0 else round(plan_done / plan_total * 100),
    }


def build_workout_finish_review_from_db(
    db: sqlite3.Connection,
    workout_date: str,
    get_or_create_session: Callable[[str | None, int | None], sqlite3.Row],
) -> dict[str, object]:
    session = get_or_create_session(workout_date, None)
    summary = db.execute(
        """
        SELECT
            COUNT(ws.id) AS set_count,
            COUNT(DISTINCT ws.exercise_id) AS exercise_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            AVG(ws.rpe) AS avg_rpe
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date = ?
        """,
        (workout_date,),
    ).fetchone()
    set_count = int(summary["set_count"] or 0)
    volume = float(summary["volume"] or 0)
    cardio_minutes = float(summary["cardio_minutes"] or 0)
    avg_rpe = float(summary["avg_rpe"] or 0)
    pr_count = int(
        db.execute("SELECT COUNT(id) FROM pr_events WHERE workout_date = ?", (workout_date,)).fetchone()[0] or 0
    )
    previous = db.execute(
        """
        SELECT
            s.workout_date,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sessions s
        JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date < ?
        GROUP BY s.id, s.workout_date
        HAVING COUNT(ws.id) > 0
        ORDER BY s.workout_date DESC
        LIMIT 1
        """,
        (workout_date,),
    ).fetchone()
    top_parts = db.execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date = ?
        GROUP BY body_part
        ORDER BY set_count DESC, body_part
        LIMIT 3
        """,
        (workout_date,),
    ).fetchall()
    top_exercises = db.execute(
        """
        SELECT
            e.name,
            COALESCE(NULLIF(MAX(ws.body_part), ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.workout_date = ?
        GROUP BY e.id, e.name
        ORDER BY volume DESC, set_count DESC, e.name
        LIMIT 3
        """,
        (workout_date,),
    ).fetchall()
    plan_rows = list_workout_plan_from_db(db, workout_date)
    plan_total = len(plan_rows)
    plan_done = sum(1 for row in plan_rows if int(row["completed_sets"] or 0) >= int(row["target_sets"] or 1))

    metrics = [
        {"label": "총 세트", "value": f"{set_count}세트", "note": f"{int(summary['exercise_count'] or 0)}개 운동"},
        {"label": "운동 볼륨", "value": f"{volume:.0f}kg", "note": "중량 x 반복"},
        {"label": "신기록", "value": f"{pr_count}개", "note": "오늘 PR"},
    ]
    if cardio_minutes:
        metrics.append({"label": "유산소", "value": f"{cardio_minutes:.0f}분", "note": "오늘 누적"})

    insights: list[str] = []
    if set_count == 0:
        insights.append("아직 기록된 세트가 없어 완료 리뷰를 만들 수 없습니다.")
    elif bool(session["completed"]):
        insights.append("운동 완료 처리되었습니다. 오늘 기록을 기준으로 다음 행동을 정리했습니다.")
    else:
        insights.append("완료 전 상태입니다. 세트 입력이 끝나면 완료 버튼으로 오늘 리뷰를 확정할 수 있습니다.")
    if pr_count:
        insights.append(f"오늘 신기록 {pr_count}개가 나왔습니다. 다음 같은 운동에서는 동일 중량 반복 또는 소폭 증량을 검토하세요.")
    if previous and float(previous["volume"] or 0) > 0:
        delta_percent = round((volume - float(previous["volume"])) / float(previous["volume"]) * 100)
        direction = "증가" if delta_percent >= 0 else "감소"
        insights.append(f"직전 운동일({previous['workout_date']}) 대비 볼륨이 {abs(delta_percent)}% {direction}했습니다.")
    if plan_total:
        insights.append(f"오늘 계획 달성률은 {round(plan_done / plan_total * 100)}%입니다.")
    if avg_rpe >= 8.5:
        insights.append("평균 체감강도가 높습니다. 다음 세션은 같은 부위 볼륨을 조금 낮추거나 휴식을 길게 잡는 편이 좋습니다.")

    next_actions: list[dict[str, str]] = []
    if plan_total and plan_done < plan_total:
        next_actions.append({"label": "미완료 계획 정리", "detail": f"{plan_total - plan_done}개 계획이 남아 있습니다."})
    if top_parts:
        top_part = top_parts[0]["body_part"]
        next_actions.append({"label": "회복 우선 부위", "detail": f"{top_part} {top_parts[0]['set_count']}세트 기록. 다음 운동 전 피로도를 확인하세요."})
    if top_exercises:
        top = top_exercises[0]
        next_actions.append({"label": "다음 목표 운동", "detail": f"{top['name']} 기준으로 다음 세션 목표 중량/반복을 먼저 확인하세요."})
    if not next_actions:
        next_actions.append({"label": "다음 기록 준비", "detail": "오늘 운동 기록을 추가하면 다음 추천이 더 정확해집니다."})

    return {
        "visible": bool(set_count or session["completed"]),
        "completed": bool(session["completed"]),
        "metrics": metrics,
        "insights": insights[:5],
        "next_actions": next_actions[:4],
        "top_parts": [dict(row) for row in top_parts],
        "top_exercises": [dict(row) for row in top_exercises],
    }


def build_workout_session_flow_from_db(
    db: sqlite3.Connection,
    workout_date: str,
    get_exercise_rest_seconds: Callable[[str], int],
    default_rest_seconds: int,
) -> dict[str, object]:
    plan_rows = list_workout_plan_from_db(db, workout_date)
    next_item = None
    for row in plan_rows:
        if int(row["completed_sets"] or 0) < int(row["target_sets"] or 1):
            next_item = dict(row)
            break
    if next_item is None and plan_rows:
        next_item = dict(plan_rows[-1])

    last_set = db.execute(
        """
        SELECT
            e.name AS exercise_name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.equipment,
            ws.set_type
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date = ?
        ORDER BY ws.sort_order DESC, ws.id DESC
        LIMIT 1
        """,
        (workout_date,),
    ).fetchone()
    rest_seconds = get_exercise_rest_seconds(last_set["exercise_name"]) if last_set else default_rest_seconds
    return {
        "next_item": next_item,
        "last_set": dict(last_set) if last_set else None,
        "rest_seconds": rest_seconds,
        "has_plan": bool(plan_rows),
    }


def create_workout_plan_item_in_db(db: sqlite3.Connection, workout_date: str, body_part: str, exercise_name: str, target_sets: int) -> None:
    next_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workout_plan_items WHERE workout_date = ?",
        (workout_date,),
    ).fetchone()[0]
    db.execute(
        """
        INSERT INTO workout_plan_items (workout_date, body_part, exercise_name, target_sets, sort_order)
        VALUES (?, ?, ?, ?, ?)
        """,
        (workout_date, body_part, exercise_name, max(1, target_sets), next_order),
    )
    db.commit()


def delete_workout_plan_item_from_db(db: sqlite3.Connection, item_id: int) -> None:
    db.execute("DELETE FROM workout_plan_items WHERE id = ?", (item_id,))
    db.commit()


def apply_default_program_to_db(
    db: sqlite3.Connection,
    program_rows: list[tuple[str, str, str, float | None, int | None]] | None,
    workout_date: str,
    get_or_create_session: Callable[[str | None, int | None], sqlite3.Row],
    get_or_create_exercise: Callable[[str], int],
) -> None:
    if not program_rows:
        return
    session = get_or_create_session(workout_date, None)
    next_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workout_sets WHERE session_id = ?",
        (session["id"],),
    ).fetchone()[0]
    for offset, (body_part, exercise_name, set_type, weight, reps) in enumerate(program_rows):
        exercise_id = get_or_create_exercise(exercise_name)
        db.execute(
            """
            INSERT INTO workout_sets (
                session_id, exercise_id, body_part, set_type, weight, reps, equipment, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session["id"], exercise_id, body_part, set_type, weight, reps, "", next_order + offset),
        )
    db.commit()
