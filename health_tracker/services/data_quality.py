from __future__ import annotations

import sqlite3
from datetime import date, timedelta


def shift_date(date_text: str, days: int) -> str:
    return (date.fromisoformat(date_text) + timedelta(days=days)).isoformat()


def list_record_gaps_from_db(db: sqlite3.Connection, date_text: str, days: int = 7) -> list[dict[str, object]]:
    start = shift_date(date_text, -(days - 1))
    workout_dates = {
        row["workout_date"]
        for row in db.execute(
            """
            SELECT DISTINCT s.workout_date
            FROM workout_sessions s
            JOIN workout_sets ws ON ws.session_id = s.id
            WHERE s.workout_date BETWEEN ? AND ?
            """,
            (start, date_text),
        ).fetchall()
    }
    meal_dates = {
        row["meal_date"]
        for row in db.execute(
            "SELECT DISTINCT meal_date FROM meal_entries WHERE meal_date BETWEEN ? AND ?",
            (start, date_text),
        ).fetchall()
    }
    rest_dates = {
        row["checkin_date"]
        for row in db.execute(
            """
            SELECT checkin_date
            FROM recovery_checkins
            WHERE checkin_date BETWEEN ? AND ? AND is_rest_day = 1
            """,
            (start, date_text),
        ).fetchall()
    }
    gaps = []
    for offset in range(days):
        day = shift_date(start, offset)
        if day in workout_dates or day in meal_dates or day in rest_dates:
            continue
        gaps.append({"date": day, "label": "기록 없음"})
    return gaps


def build_data_quality_profile_from_db(db: sqlite3.Connection, date_text: str, days: int = 14) -> dict[str, object]:
    end = date.fromisoformat(date_text).isoformat()
    start = shift_date(end, -(days - 1))
    workout_days = db.execute(
        """
        SELECT COUNT(DISTINCT s.workout_date)
        FROM workout_sessions s
        JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date BETWEEN ? AND ?
        """,
        (start, end),
    ).fetchone()[0] or 0
    meal_days = db.execute(
        "SELECT COUNT(DISTINCT meal_date) FROM meal_entries WHERE meal_date BETWEEN ? AND ?",
        (start, end),
    ).fetchone()[0] or 0
    metric_days = db.execute(
        "SELECT COUNT(*) FROM body_metrics WHERE metric_date BETWEEN ? AND ?",
        (start, end),
    ).fetchone()[0] or 0
    missing_days = len(list_record_gaps_from_db(db, end, days=days))
    metric_target = max(1, days // 7)
    component_values = {
        "workout": min(1, workout_days / days),
        "meal": min(1, meal_days / days),
        "metric": min(1, metric_days / metric_target),
        "covered": max(0, (days - missing_days) / days),
    }
    score = round(
        (component_values["workout"] * 35)
        + (component_values["meal"] * 35)
        + (component_values["metric"] * 20)
        + (component_values["covered"] * 10)
    )
    if score >= 80:
        label = "높음"
        tone = "high"
        message = "최근 기록이 충분해 운동·식단 분석을 안정적으로 볼 수 있습니다."
    elif score >= 55:
        label = "보통"
        tone = "normal"
        message = "일부 기록이 부족해 분석 결과가 제한될 수 있습니다."
    else:
        label = "낮음"
        tone = "low"
        message = "기록이 부족해 추천과 추세 분석의 신뢰도가 낮습니다."

    components = [
        build_component("운동 기록", workout_days, days, "일", component_values["workout"]),
        build_component("식단 기록", meal_days, days, "일", component_values["meal"]),
        build_component("체성분 기록", metric_days, metric_target, "회", component_values["metric"]),
        build_component("기록된 날", days - missing_days, days, "일", component_values["covered"]),
    ]
    actions = []
    if workout_days < max(3, round(days * 0.35)):
        actions.append({"label": "운동 입력", "href": "/?mode=workout"})
    if meal_days < max(5, round(days * 0.5)):
        actions.append({"label": "식단 입력", "href": "/?mode=meal"})
    if metric_days < metric_target:
        actions.append({"label": "체성분 입력", "href": "/#body-metrics"})
    if missing_days >= 3:
        actions.append({"label": "오늘 기록 추가", "href": "/"})

    return {
        "score": score,
        "label": label,
        "tone": tone,
        "message": message,
        "workout_days": workout_days,
        "meal_days": meal_days,
        "metric_days": metric_days,
        "missing_days": missing_days,
        "metric_target": metric_target,
        "period": f"{start} ~ {end}",
        "components": components,
        "actions": actions[:3],
        "criteria": "운동 35점, 식단 35점, 체성분 20점, 누락 없는 날 10점 기준입니다.",
    }


def build_component(label: str, count: int, target: int, unit: str, ratio: float) -> dict[str, object]:
    percent = round(max(0, min(1, ratio)) * 100)
    return {
        "label": label,
        "count": count,
        "target": target,
        "unit": unit,
        "percent": percent,
    }
