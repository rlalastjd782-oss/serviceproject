from __future__ import annotations

import sqlite3
from datetime import datetime


def build_next_workout_plan_from_db(db: sqlite3.Connection, date_text: str) -> dict[str, object]:
    body_parts = _body_part_recent_status(db, date_text)
    focus = _pick_focus_body_part(body_parts)
    candidates = _exercise_candidates(db, str(focus["body_part"]), date_text)
    location = _preferred_location(db, date_text)
    return {
        "focus": focus,
        "target_sets": _target_sets(focus),
        "exercise_candidates": candidates,
        "location": location,
        "recovery_note": _recovery_note(focus),
        "summary": _summary_text(focus, candidates),
    }


def _body_part_recent_status(db: sqlite3.Connection, date_text: str) -> list[dict[str, object]]:
    rows = db.execute(
        """
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COUNT(DISTINCT s.workout_date) AS workout_days,
            MAX(s.workout_date) AS last_date,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date BETWEEN date(?, '-21 day') AND ?
        GROUP BY body_part
        ORDER BY last_date ASC, set_count ASC
        """,
        (date_text, date_text),
    ).fetchall()
    if not rows:
        return []

    base_date = datetime.strptime(date_text, "%Y-%m-%d").date()
    status = []
    for row in rows:
        last_date = row["last_date"]
        days_since = (base_date - datetime.strptime(last_date, "%Y-%m-%d").date()).days if last_date else 99
        set_count = int(row["set_count"] or 0)
        status.append(
            {
                "body_part": row["body_part"],
                "set_count": set_count,
                "workout_days": int(row["workout_days"] or 0),
                "last_date": last_date,
                "days_since": days_since,
                "volume": float(row["volume"] or 0),
                "priority": days_since * 2 - min(set_count, 20),
            }
        )
    return status


def _pick_focus_body_part(body_parts: list[dict[str, object]]) -> dict[str, object]:
    if not body_parts:
        return {
            "body_part": "전신",
            "set_count": 0,
            "workout_days": 0,
            "last_date": "-",
            "days_since": None,
            "volume": 0,
            "priority": 0,
            "state": "start",
        }
    candidates = [item for item in body_parts if item["body_part"] != "유산소"] or body_parts
    focus = max(candidates, key=lambda item: (int(item["priority"]), int(item["days_since"] or 0)))
    focus = dict(focus)
    focus["state"] = "recovery" if int(focus["days_since"] or 0) >= 3 else "maintain"
    return focus


def _target_sets(focus: dict[str, object]) -> int:
    if focus["body_part"] == "전신":
        return 9
    days_since = int(focus["days_since"] or 0)
    if days_since >= 5:
        return 8
    if days_since >= 3:
        return 6
    return 4


def _exercise_candidates(db: sqlite3.Connection, body_part: str, date_text: str) -> list[sqlite3.Row]:
    if body_part == "전신":
        return db.execute(
            """
            SELECT
                e.name AS exercise_name,
                COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
                COALESCE(NULLIF(ws.equipment, ''), '') AS equipment,
                COUNT(ws.id) AS set_count,
                MAX(s.workout_date) AS last_date
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            JOIN exercises e ON e.id = ws.exercise_id
            WHERE s.workout_date <= ?
            GROUP BY e.id, e.name, body_part, equipment
            ORDER BY set_count DESC, last_date DESC
            LIMIT 5
            """,
            (date_text,),
        ).fetchall()
    return db.execute(
        """
        SELECT
            e.name AS exercise_name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COALESCE(NULLIF(ws.equipment, ''), '') AS equipment,
            COUNT(ws.id) AS set_count,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.workout_date <= ?
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') = ?
        GROUP BY e.id, e.name, body_part, equipment
        ORDER BY set_count DESC, last_date DESC
        LIMIT 5
        """,
        (date_text, body_part),
    ).fetchall()


def _preferred_location(db: sqlite3.Connection, date_text: str) -> sqlite3.Row | None:
    return db.execute(
        """
        SELECT
            wl.id,
            wl.name,
            COUNT(ws.id) AS set_count,
            MAX(s.workout_date) AS last_date
        FROM workout_locations wl
        JOIN workout_sessions s ON s.location_id = wl.id
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date <= ?
        GROUP BY wl.id, wl.name
        ORDER BY last_date DESC, set_count DESC
        LIMIT 1
        """,
        (date_text,),
    ).fetchone()


def _recovery_note(focus: dict[str, object]) -> str:
    if focus["body_part"] == "전신":
        return "기록이 아직 부족합니다. 전신 기준으로 가볍게 시작하고 이후 부위별 패턴을 쌓으세요."
    days_since = int(focus["days_since"] or 0)
    if days_since >= 5:
        return "최근 공백이 긴 부위입니다. 첫 운동은 워밍업을 충분히 잡고 본세트 볼륨을 확인하세요."
    if days_since >= 3:
        return "회복 시간이 확보된 부위입니다. 최근 기록을 기준으로 반복 또는 소폭 증량을 검토하세요."
    return "최근에 이미 건드린 부위입니다. 강도보다 품질과 반복성을 우선하세요."


def _summary_text(focus: dict[str, object], candidates: list[sqlite3.Row]) -> str:
    body_part = str(focus["body_part"])
    if body_part == "전신":
        return "아직 개인화 기준 기록이 부족합니다. 오늘 기록을 쌓으면 다음 추천이 더 정확해집니다."
    candidate_text = candidates[0]["exercise_name"] if candidates else "새 운동"
    return f"{body_part} 중심으로 {candidate_text}부터 시작하는 흐름이 적합합니다."
