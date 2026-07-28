from __future__ import annotations

import random
import sqlite3
from collections.abc import Callable
from datetime import datetime

from health_tracker.constants import PROGRESSIVE_OVERLOAD_WEIGHT_INCREMENT_KG, READINESS_TIERS, STRENGTH_BODY_PARTS

_NO_RECENT_ACTIVITY_MESSAGES = [
    "최근 48시간 근력 기록이 적습니다. 원하는 부위를 진행해도 좋습니다.",
    "최근 이틀간 기록이 많지 않습니다. 오늘은 원하는 부위부터 자유롭게 시작하세요.",
    "최근 48시간 기록이 비어 있습니다. 컨디션에 맞춰 자유롭게 골라보세요.",
]

_OVERLOADED_TEMPLATES = [
    "{parts}는 최근 사용량이 많습니다.",
    "{parts} 부위는 최근 자극이 많이 들어갔습니다.",
    "{parts}는 최근 48시간 안에 이미 많이 다뤘습니다.",
]

_RESTED_TEMPLATES = [
    "오늘 추천 부위: {parts}",
    "오늘은 {parts} 위주로 진행해보세요.",
    "{parts}는 쉬어서 오늘 우선순위로 좋습니다.",
]

_CONDITION_GOOD_MESSAGES = [
    "컨디션이 좋습니다. 메인 운동은 지난 기록보다 1회 또는 {increment}kg 도전을 고려하세요.",
    "오늘 컨디션이 좋아 보입니다. 평소보다 살짝 더 밀어붙여도 좋은 타이밍입니다.",
    "회복이 잘 된 상태입니다. 지난 기록을 넘어설 좋은 기회입니다.",
]

_CONDITION_LOW_MESSAGES = [
    "회복 점수가 낮습니다. 고중량보다 가벼운 볼륨이나 유산소 위주가 낫습니다.",
    "오늘은 몸이 덜 회복된 상태입니다. 무리한 중량보다 가벼운 세트로 마무리하세요.",
    "회복이 부족합니다. 강도를 낮추고 다음 회복을 우선하세요.",
]

_CONDITION_AVERAGE_MESSAGES = [
    "평균 컨디션입니다. 지난 기록과 같은 중량에서 안정적으로 세트를 채우세요.",
    "무난한 컨디션입니다. 평소 페이스를 유지하며 세트 완성도에 집중하세요.",
    "특별히 좋거나 나쁘지 않은 상태입니다. 지난 기록 수준을 안정적으로 반복하세요.",
]

_SORENESS_HIGH_MESSAGES = [
    "근육통이 높습니다. 같은 부위 반복보다 회복된 부위를 선택하세요.",
    "근육통이 남아있습니다. 오늘은 다른 부위 위주로 진행하는 게 좋습니다.",
]


def get_recovery_checkin_from_db(db: sqlite3.Connection, date_text: str) -> dict[str, object]:
    row = db.execute(
        """
        SELECT checkin_date, condition_score, sleep_score, soreness_score, fatigue_score,
               is_rest_day, rest_reason, memo, created_at, updated_at
        FROM recovery_checkins
        WHERE checkin_date = ?
        """,
        (date_text,),
    ).fetchone()
    if row:
        return dict(row)
    return {
        "checkin_date": date_text,
        "condition_score": 3,
        "sleep_score": 3,
        "soreness_score": 3,
        "fatigue_score": 3,
        "memo": "",
    }


def save_recovery_checkin_to_db(
    db: sqlite3.Connection,
    checkin_date: str,
    condition_score: int,
    sleep_score: int,
    soreness_score: int,
    fatigue_score: int,
    memo: str,
) -> None:
    def clamp_score(value: int) -> int:
        return max(1, min(5, int(value or 3)))

    db.execute(
        """
        INSERT INTO recovery_checkins (
            checkin_date, condition_score, sleep_score, soreness_score, fatigue_score, memo, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(checkin_date) DO UPDATE SET
            condition_score = excluded.condition_score,
            sleep_score = excluded.sleep_score,
            soreness_score = excluded.soreness_score,
            fatigue_score = excluded.fatigue_score,
            memo = excluded.memo,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            checkin_date,
            clamp_score(condition_score),
            clamp_score(sleep_score),
            clamp_score(soreness_score),
            clamp_score(fatigue_score),
            memo[:200],
        ),
    )
    db.commit()


def save_rest_day_to_db(db: sqlite3.Connection, date_text: str, reason: str, memo: str = "") -> None:
    db.execute(
        """
        INSERT INTO recovery_checkins (
            checkin_date, condition_score, sleep_score, soreness_score, fatigue_score,
            is_rest_day, rest_reason, memo, updated_at
        )
        VALUES (?, 3, 3, 3, 3, 1, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(checkin_date) DO UPDATE SET
            is_rest_day = 1,
            rest_reason = excluded.rest_reason,
            memo = excluded.memo,
            updated_at = CURRENT_TIMESTAMP
        """,
        (date_text, reason.strip()[:40] or "휴식", memo.strip()[:120]),
    )
    db.commit()


def list_recommended_sessions_from_db(db: sqlite3.Connection, workout_date: str, limit: int = 3) -> list[dict[str, object]]:
    weekday = datetime.strptime(workout_date, "%Y-%m-%d").weekday()
    rows = db.execute(
        """
        SELECT
            s.id,
            s.workout_date,
            COALESCE(s.duration_seconds, 0) AS duration_seconds,
            COUNT(ws.id) AS set_count,
            GROUP_CONCAT(DISTINCT COALESCE(NULLIF(ws.body_part, ''), '기타')) AS body_parts
        FROM workout_sessions s
        JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date < ?
        GROUP BY s.id, s.workout_date, s.duration_seconds
        ORDER BY s.workout_date DESC
        LIMIT 30
        """,
        (workout_date,),
    ).fetchall()
    recommendations = []
    for row in rows:
        if datetime.strptime(row["workout_date"], "%Y-%m-%d").weekday() != weekday:
            continue
        recommendations.append(
            {
                "id": row["id"],
                "workout_date": row["workout_date"],
                "duration_seconds": int(row["duration_seconds"] or 0),
                "set_count": row["set_count"],
                "body_parts": (row["body_parts"] or "").replace(",", " · "),
            }
        )
        if len(recommendations) >= limit:
            break
    return recommendations


def list_workout_focus_recommendations_from_db(
    db: sqlite3.Connection,
    workout_date: str,
    body_part_options: Callable[[], list[str]],
    limit: int = 5,
) -> list[dict[str, object]]:
    recent_part_rows = db.execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date < ?
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') NOT IN ('기타')
        GROUP BY body_part
        """,
        (workout_date,),
    ).fetchall()
    last_part_dates = {row["body_part"]: row["last_date"] for row in recent_part_rows}
    today_parts = {
        row["body_part"]
        for row in db.execute(
            """
            SELECT DISTINCT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            WHERE s.workout_date = ?
            """,
            (workout_date,),
        ).fetchall()
    }
    rows = db.execute(
        """
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.id AS exercise_id,
            e.name AS exercise_name,
            COUNT(ws.id) AS set_count,
            MAX(s.workout_date) AS last_date,
            (
                SELECT ws2.weight
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id
                  AND s2.workout_date <= ?
                  AND ws2.weight IS NOT NULL
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_weight,
            (
                SELECT ws2.reps
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id
                  AND s2.workout_date <= ?
                  AND ws2.reps IS NOT NULL
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_reps,
            (
                SELECT ws2.cardio_incline
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id
                  AND s2.workout_date <= ?
                  AND ws2.cardio_incline IS NOT NULL
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_cardio_incline,
            (
                SELECT ws2.cardio_speed
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id
                  AND s2.workout_date <= ?
                  AND ws2.cardio_speed IS NOT NULL
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_cardio_speed,
            (
                SELECT ws2.cardio_minutes
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id
                  AND s2.workout_date <= ?
                  AND ws2.cardio_minutes IS NOT NULL
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_cardio_minutes
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date <= ?
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') NOT IN ('기타')
        GROUP BY body_part, e.id, e.name
        ORDER BY last_date DESC, set_count DESC, e.name
        """,
        (workout_date, workout_date, workout_date, workout_date, workout_date, workout_date),
    ).fetchall()
    if not rows:
        return []

    date_value = datetime.strptime(workout_date, "%Y-%m-%d")
    body_priority = {part: index for index, part in enumerate(body_part_options())}
    candidates = []
    for row in rows:
        body_part = row["body_part"] or "기타"
        last_date = last_part_dates.get(body_part) or row["last_date"]
        days_since = 99
        if last_date:
            days_since = max(0, (date_value - datetime.strptime(last_date, "%Y-%m-%d")).days)
        is_today = body_part in today_parts
        if is_today:
            reason = "오늘 이미 진행 중"
        elif days_since >= 3:
            reason = f"{days_since}일 쉬어서 우선 추천"
        elif days_since >= 1:
            reason = f"최근 {days_since}일 전 진행"
        else:
            reason = "최근 기록 기반 추천"
        candidates.append(
            {
                "body_part": body_part,
                "exercise_name": row["exercise_name"],
                "set_count": int(row["set_count"] or 0),
                "last_date": row["last_date"],
                "last_weight": row["last_weight"],
                "last_reps": row["last_reps"],
                "last_cardio_incline": row["last_cardio_incline"],
                "last_cardio_speed": row["last_cardio_speed"],
                "last_cardio_minutes": row["last_cardio_minutes"],
                "reason": reason,
                "_score": (
                    1 if is_today else 0,
                    -days_since,
                    body_priority.get(body_part, 99),
                    -int(row["set_count"] or 0),
                ),
            }
        )
    candidates.sort(key=lambda item: item["_score"])
    return [{key: value for key, value in item.items() if key != "_score"} for item in candidates[:limit]]


def list_recovery_recommendations_from_db(
    db: sqlite3.Connection,
    date_text: str,
    shift_date: Callable[[str, int], str],
) -> list[str]:
    start = shift_date(date_text, -2)
    rows = db.execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') NOT IN ('기타', '유산소')
        GROUP BY body_part
        ORDER BY set_count DESC
        """,
        (start, date_text),
    ).fetchall()
    if not rows:
        return [random.choice(_NO_RECENT_ACTIVITY_MESSAGES)]
    overloaded = [row["body_part"] for row in rows if int(row["set_count"]) >= 4]
    rested = [part for part in STRENGTH_BODY_PARTS if part not in [row["body_part"] for row in rows]]
    messages = []
    if overloaded:
        messages.append(random.choice(_OVERLOADED_TEMPLATES).format(parts=", ".join(overloaded[:2])))
    if rested:
        messages.append(random.choice(_RESTED_TEMPLATES).format(parts=", ".join(rested[:2])))
    return messages[:2]


def list_daily_coaching_from_db(
    db: sqlite3.Connection,
    date_text: str,
    shift_date: Callable[[str, int], str],
    checkin: dict[str, object] | None = None,
) -> list[str]:
    if checkin is None:
        checkin = get_recovery_checkin_from_db(db, date_text)
    condition = int(checkin["condition_score"] or 3)
    sleep = int(checkin["sleep_score"] or 3)
    soreness = int(checkin["soreness_score"] or 3)
    fatigue = int(checkin["fatigue_score"] or 3)
    messages = []
    if condition >= 4 and sleep >= 4 and fatigue <= 2:
        messages.append(random.choice(_CONDITION_GOOD_MESSAGES).format(increment=PROGRESSIVE_OVERLOAD_WEIGHT_INCREMENT_KG))
    elif sleep <= 2 or fatigue >= 4:
        messages.append(random.choice(_CONDITION_LOW_MESSAGES))
    else:
        messages.append(random.choice(_CONDITION_AVERAGE_MESSAGES))
    if soreness >= 4:
        messages.append(random.choice(_SORENESS_HIGH_MESSAGES))
    messages.extend(list_recovery_recommendations_from_db(db, date_text, shift_date))
    return messages[:4]


def _compute_readiness_score(checkin: dict[str, object]) -> int:
    condition = int(checkin["condition_score"] or 3)
    sleep = int(checkin["sleep_score"] or 3)
    soreness = int(checkin["soreness_score"] or 3)
    fatigue = int(checkin["fatigue_score"] or 3)
    return condition + sleep + (6 - soreness) + (6 - fatigue)


def classify_readiness_percent(percent: int) -> dict[str, object]:
    for tier in READINESS_TIERS:
        if percent >= tier["min"]:
            return tier
    return READINESS_TIERS[-1]


def build_readiness_profile_from_db(
    db: sqlite3.Connection,
    date_text: str,
    checkin: dict[str, object] | None = None,
) -> dict[str, object]:
    if checkin is None:
        checkin = get_recovery_checkin_from_db(db, date_text)
    score = _compute_readiness_score(checkin)
    percent = round(score / 20 * 100)
    tier = classify_readiness_percent(percent)
    return {
        "score": score,
        "percent": percent,
        "label": tier["label"],
        "guide": tier["guide"],
        "tone": tier["tone"],
    }


def build_adaptive_training_recommendations_from_db(
    db: sqlite3.Connection,
    workout_date: str,
    shift_date: Callable[[str, int], str],
    limit: int = 6,
    checkin: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    if checkin is None:
        checkin = get_recovery_checkin_from_db(db, workout_date)
    readiness_ratio = _compute_readiness_score(checkin) / 20
    recent_start = shift_date(workout_date, -10)
    recent_load_rows = db.execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
               COUNT(ws.id) AS set_count,
               AVG(ws.rpe) AS avg_rpe
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        GROUP BY body_part
        """,
        (recent_start, workout_date),
    ).fetchall()
    recent_load = {
        row["body_part"]: {
            "set_count": int(row["set_count"] or 0),
            "avg_rpe": float(row["avg_rpe"] or 0),
        }
        for row in recent_load_rows
    }
    rows = db.execute(
        """
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.name AS exercise_name,
            MAX(s.workout_date) AS last_date,
            COUNT(ws.id) AS history_sets,
            AVG(ws.rpe) AS avg_rpe,
            (
                SELECT ws2.weight
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id AND ws2.weight IS NOT NULL AND s2.workout_date < ?
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_weight,
            (
                SELECT ws2.reps
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id AND ws2.reps IS NOT NULL AND s2.workout_date < ?
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_reps,
            (
                SELECT ws2.cardio_minutes
                FROM workout_sets ws2
                JOIN workout_sessions s2 ON s2.id = ws2.session_id
                WHERE ws2.exercise_id = e.id AND ws2.cardio_minutes IS NOT NULL AND s2.workout_date < ?
                ORDER BY s2.workout_date DESC, ws2.sort_order DESC, ws2.id DESC
                LIMIT 1
            ) AS last_cardio_minutes
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.workout_date < ?
        GROUP BY body_part, e.id, e.name
        ORDER BY last_date DESC, history_sets DESC
        LIMIT 80
        """,
        (workout_date, workout_date, workout_date, workout_date),
    ).fetchall()
    date_value = datetime.strptime(workout_date, "%Y-%m-%d")
    items = []
    for row in rows:
        body_part = row["body_part"] or "기타"
        if body_part == "기타":
            continue
        last_date = row["last_date"]
        days_since = (date_value - datetime.strptime(last_date, "%Y-%m-%d")).days if last_date else 99
        load = recent_load.get(body_part, {"set_count": 0, "avg_rpe": 0})
        avg_rpe = float(row["avg_rpe"] or load["avg_rpe"] or 0)
        load_penalty = int(load["set_count"]) * 2 + (8 if avg_rpe >= 8.5 else 0)
        readiness_bonus = round(readiness_ratio * 12)
        score = min(100, max(0, days_since * 8 + readiness_bonus + min(int(row["history_sets"] or 0), 15) - load_penalty))
        if readiness_ratio < 0.45 and body_part != "유산소":
            action = "가볍게 유지"
            target_sets = 2
        elif avg_rpe >= 8.5 or int(load["set_count"]) >= 12:
            action = "강도 낮춤"
            target_sets = 2
        elif days_since >= 3 and readiness_ratio >= 0.65:
            action = "증량 시도"
            target_sets = 4
        else:
            action = "기록 반복"
            target_sets = 3
        next_weight = row["last_weight"]
        next_reps = row["last_reps"]
        if next_weight is not None and action == "증량 시도":
            next_weight = round(float(next_weight) + PROGRESSIVE_OVERLOAD_WEIGHT_INCREMENT_KG, 1)
        items.append(
            {
                "body_part": body_part,
                "exercise_name": row["exercise_name"],
                "score": score,
                "action": action,
                "target_sets": target_sets,
                "last_date": last_date,
                "last_weight": next_weight,
                "last_reps": next_reps,
                "last_cardio_minutes": row["last_cardio_minutes"],
                "reason": f"회복 {round(readiness_ratio * 100)}% · 최근 {days_since}일 전",
            }
        )
    items.sort(key=lambda item: (-int(item["score"]), item["body_part"], item["exercise_name"]))
    return items[:limit]
