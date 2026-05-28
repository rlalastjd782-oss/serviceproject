from __future__ import annotations

import sqlite3
from collections import defaultdict

from health_tracker.constants import normalize_equipment_category


def list_location_training_insights_from_db(db: sqlite3.Connection, limit: int = 20) -> list[dict[str, object]]:
    rows = db.execute(
        """
        SELECT
            wl.id,
            wl.name,
            wl.is_default,
            wl.is_active,
            COUNT(DISTINCT s.workout_date) AS workout_days,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            MAX(s.workout_date) AS last_date
        FROM workout_locations wl
        LEFT JOIN workout_sessions s ON s.location_id = wl.id
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        GROUP BY wl.id
        ORDER BY wl.is_active DESC, workout_days DESC, last_date DESC, wl.name
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    location_ids = [int(row["id"]) for row in rows]
    top_exercises_by_location = _top_exercises_by_location(db, location_ids)
    equipment_counts_by_location = _equipment_counts_by_location(db, location_ids)
    registered_equipment_by_location = _registered_equipment_by_location(db, location_ids)

    insights = []
    for row in rows:
        location_id = int(row["id"])
        top_exercises = top_exercises_by_location.get(location_id, [])[:4]
        equipment_counts = equipment_counts_by_location.get(location_id, {})
        top_equipment = [
            {"equipment": name, "use_count": count}
            for name, count in sorted(equipment_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
        ]
        registered_equipment = registered_equipment_by_location.get(location_id, [])
        unused_equipment = [item for item in registered_equipment if item not in set(equipment_counts)]
        equipment_coverage = (
            round(((len(registered_equipment) - len(unused_equipment)) / len(registered_equipment)) * 100)
            if registered_equipment
            else 0
        )
        insights.append(
            {
                "location": row,
                "top_exercises": top_exercises,
                "top_equipment": top_equipment,
                "registered_equipment": registered_equipment,
                "unused_equipment": unused_equipment[:6],
                "equipment_coverage": equipment_coverage,
                "message": build_location_message(row, top_exercises),
            }
        )
    return insights


def list_location_quick_exercises_from_db(db: sqlite3.Connection, location_id: int | None, limit: int = 6) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT
            e.name AS exercise_name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COALESCE(NULLIF(ws.equipment, ''), '') AS equipment,
            COUNT(ws.id) AS set_count,
            MAX(s.workout_date) AS last_date,
            (
                SELECT recent.weight
                FROM workout_sets recent
                JOIN workout_sessions rs ON rs.id = recent.session_id
                JOIN exercises re ON re.id = recent.exercise_id
                WHERE rs.location_id = s.location_id AND re.name = e.name
                ORDER BY rs.workout_date DESC, recent.id DESC
                LIMIT 1
            ) AS last_weight,
            (
                SELECT recent.reps
                FROM workout_sets recent
                JOIN workout_sessions rs ON rs.id = recent.session_id
                JOIN exercises re ON re.id = recent.exercise_id
                WHERE rs.location_id = s.location_id AND re.name = e.name
                ORDER BY rs.workout_date DESC, recent.id DESC
                LIMIT 1
            ) AS last_reps
        FROM workout_sessions s
        JOIN workout_sets ws ON ws.session_id = s.id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.location_id = ?
        GROUP BY e.name, body_part, equipment
        ORDER BY set_count DESC, last_date DESC, e.name
        LIMIT ?
        """,
        (location_id, limit),
    ).fetchall()


def build_location_message(location: sqlite3.Row, top_exercises: list[sqlite3.Row]) -> str:
    if not location["workout_days"]:
        return "아직 기록이 없어 오늘 운동을 저장하면 장소별 추천을 시작합니다."
    if top_exercises:
        return f"{top_exercises[0]['name']} 기록이 가장 많습니다. 오늘 입력에서 이 운동을 빠르게 불러올 수 있습니다."
    return "장소 기록은 있지만 세트 상세가 부족합니다. 장비와 세트를 함께 저장하면 추천 정확도가 올라갑니다."


def _placeholders(values: list[int]) -> str:
    return ",".join("?" for _ in values)


def _top_exercises_by_location(db: sqlite3.Connection, location_ids: list[int]) -> dict[int, list[sqlite3.Row]]:
    if not location_ids:
        return {}
    rows = db.execute(
        f"""
        SELECT
            s.location_id,
            e.name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            MAX(s.workout_date) AS last_date
        FROM workout_sessions s
        JOIN workout_sets ws ON ws.session_id = s.id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.location_id IN ({_placeholders(location_ids)})
        GROUP BY s.location_id, e.id, e.name, body_part
        ORDER BY s.location_id, set_count DESC, last_date DESC
        """,
        location_ids,
    ).fetchall()
    grouped: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        grouped[int(row["location_id"])].append(row)
    return grouped


def _equipment_counts_by_location(db: sqlite3.Connection, location_ids: list[int]) -> dict[int, dict[str, int]]:
    if not location_ids:
        return {}
    rows = db.execute(
        f"""
        SELECT
            s.location_id,
            COALESCE(NULLIF(ws.equipment, ''), '미지정') AS equipment,
            COUNT(ws.id) AS use_count
        FROM workout_sessions s
        JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.location_id IN ({_placeholders(location_ids)})
        GROUP BY s.location_id, equipment
        ORDER BY s.location_id, use_count DESC, equipment
        """,
        location_ids,
    ).fetchall()
    grouped: dict[int, dict[str, int]] = defaultdict(dict)
    for row in rows:
        category = normalize_equipment_category(row["equipment"])
        if category:
            location_id = int(row["location_id"])
            grouped[location_id][category] = grouped[location_id].get(category, 0) + int(row["use_count"] or 0)
    return grouped


def _registered_equipment_by_location(db: sqlite3.Connection, location_ids: list[int]) -> dict[int, list[str]]:
    if not location_ids:
        return {}
    rows = db.execute(
        f"""
        SELECT location_id, equipment_name, equipment_type
        FROM location_equipment
        WHERE is_active = 1
          AND location_id IN ({_placeholders(location_ids)})
        ORDER BY location_id, updated_at DESC, equipment_name
        """,
        location_ids,
    ).fetchall()
    grouped: dict[int, list[str]] = defaultdict(list)
    for row in rows:
        category = normalize_equipment_category(str(row["equipment_name"] or "")) or normalize_equipment_category(
            str(row["equipment_type"] or "")
        )
        if category and category not in grouped[int(row["location_id"])]:
            grouped[int(row["location_id"])].append(category)
    return grouped
