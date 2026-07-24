from __future__ import annotations

import sqlite3


BODY_PART_SET_TARGETS: dict[str, tuple[int, int]] = {
    "가슴": (10, 20),
    "등": (10, 20),
    "하체": (10, 20),
    "어깨": (8, 16),
    "팔(이두)": (6, 14),
    "팔(삼두)": (6, 14),
    "유산소": (2, 5),
}

BODY_PART_ALTERNATIVES: dict[str, list[str]] = {
    "가슴": ["덤벨프레스", "인클라인프레스", "체스트프레스", "푸시업"],
    "등": ["랫풀다운", "시티드로우", "암풀다운", "풀업"],
    "하체": ["레그프레스", "스쿼트", "런지", "레그컬"],
    "어깨": ["숄더프레스", "사이드레터럴레이즈", "리어델트", "페이스풀"],
    "팔(이두)": ["바벨컬", "해머컬", "덤벨컬", "프리처컬"],
    "팔(삼두)": ["케이블푸시다운", "딥스", "라잉트라이셉스익스텐션", "오버헤드익스텐션"],
    "유산소": ["런닝머신", "사이클", "스텝밀", "일립티컬"],
}

REST_RULES: dict[str, int] = {
    "가슴": 120,
    "등": 120,
    "하체": 150,
    "어깨": 90,
    "팔(이두)": 75,
    "팔(삼두)": 75,
    "유산소": 60,
    "기타": 90,
}


def weekly_rule_report_from_db(db: sqlite3.Connection, week_start: str, shift_date) -> dict[str, object]:
    week_end = shift_date(week_start, 6)
    rows = db.execute(
        """
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            AVG(ws.rpe) AS avg_rpe,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date BETWEEN ? AND ?
        GROUP BY body_part
        """,
        (week_start, week_end),
    ).fetchall()
    by_part = {row["body_part"]: row for row in rows}
    items = []
    for body_part, (target_min, target_max) in BODY_PART_SET_TARGETS.items():
        row = by_part.get(body_part)
        set_count = int(row["set_count"] or 0) if row else 0
        avg_rpe = float(row["avg_rpe"] or 0) if row and row["avg_rpe"] is not None else 0
        if set_count < target_min:
            state = "부족"
            advice = f"{target_min - set_count}세트 이상 보강 권장"
        elif set_count > target_max:
            state = "과다"
            advice = "다음 운동은 볼륨을 낮추거나 휴식 우선"
        else:
            state = "적정"
            advice = "현재 주간 볼륨 유지"
        if avg_rpe >= 9:
            advice = "RPE가 높습니다. 중량 유지 또는 세트 감량 권장"
        elif avg_rpe and avg_rpe <= 6 and set_count >= target_min:
            advice = "여유가 있습니다. 다음 운동은 반복수나 중량 소폭 증가 가능"
        items.append(
            {
                "body_part": body_part,
                "set_count": set_count,
                "target_min": target_min,
                "target_max": target_max,
                "avg_rpe": round(avg_rpe, 1),
                "state": state,
                "advice": advice,
                "alternatives": BODY_PART_ALTERNATIVES.get(body_part, [])[:3],
                "rest_seconds": REST_RULES.get(body_part, 90),
            }
        )
    priority = {"부족": 0, "과다": 1, "적정": 2}
    items.sort(key=lambda item: (priority.get(str(item["state"]), 9), int(item["set_count"])))
    return {
        "period": f"{week_start} ~ {week_end}",
        "items": items,
        "summary": build_rule_summary(items),
    }


def build_rule_summary(items: list[dict[str, object]]) -> str:
    low = [item["body_part"] for item in items if item["state"] == "부족"]
    high = [item["body_part"] for item in items if item["state"] == "과다"]
    if low:
        return f"{', '.join(low[:2])} 볼륨이 부족합니다. 다음 운동에서 먼저 보강하세요."
    if high:
        return f"{', '.join(high[:2])} 볼륨이 많습니다. 회복과 강도 조절이 우선입니다."
    return "부위별 주간 볼륨이 권장 범위 안에 있습니다."


def today_rule_cards_from_db(db: sqlite3.Connection, date_text: str, shift_date) -> list[dict[str, object]]:
    report = weekly_rule_report_from_db(db, shift_date(date_text, -6), shift_date)
    cards = []
    for item in report["items"][:4]:
        cards.append(
            {
                "title": f"{item['body_part']} · {item['state']}",
                "detail": f"{item['set_count']}세트 / 권장 {item['target_min']}-{item['target_max']}세트",
                "advice": item["advice"],
                "rest_seconds": item["rest_seconds"],
                "alternatives": item["alternatives"],
                "state": item["state"],
            }
        )
    return cards
