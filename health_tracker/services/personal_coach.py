from __future__ import annotations

import sqlite3


def build_next_actions_from_db(db: sqlite3.Connection, date_text: str, shift_date) -> list[dict[str, str]]:
    start = shift_date(date_text, -13)
    body_rows = db.execute(
        """
        SELECT
            ws.body_part,
            COUNT(*) AS set_count,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date BETWEEN ? AND ?
        GROUP BY ws.body_part
        ORDER BY set_count ASC, last_date ASC
        """,
        (start, date_text),
    ).fetchall()
    meal_days = db.execute(
        "SELECT COUNT(DISTINCT meal_date) AS count FROM meal_entries WHERE meal_date BETWEEN ? AND ?",
        (shift_date(date_text, -6), date_text),
    ).fetchone()
    recent_sets = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date BETWEEN ? AND ?
        """,
        (shift_date(date_text, -6), date_text),
    ).fetchone()

    actions: list[dict[str, str]] = []
    if body_rows:
        weakest = body_rows[0]
        actions.append(
            {
                "kind": "training",
                "title": f"{weakest['body_part']} 보강",
                "detail": f"최근 14일 {int(weakest['set_count'] or 0)}세트 · 마지막 {weakest['last_date']}",
                "href": f"/?date={date_text}&mode=workout",
            }
        )
    else:
        actions.append(
            {
                "kind": "training",
                "title": "첫 운동 기록",
                "detail": "운동명을 선택하면 이전 기록 기반 기본값을 자동으로 채웁니다.",
                "href": f"/?date={date_text}&mode=workout",
            }
        )

    if int(recent_sets["count"] or 0) >= 30:
        actions.append(
            {
                "kind": "recovery",
                "title": "회복 상태 확인",
                "detail": f"최근 7일 {int(recent_sets['count'] or 0)}세트가 기록됐습니다.",
                "href": f"/?date={date_text}&mode=workout#recovery-checkin",
            }
        )

    if int(meal_days["count"] or 0) < 4:
        actions.append(
            {
                "kind": "meal",
                "title": "식단 기록 보강",
                "detail": f"최근 7일 식단 기록 {int(meal_days['count'] or 0)}일입니다.",
                "href": f"/?date={date_text}&mode=meal",
            }
        )

    actions.append(
        {
            "kind": "analysis",
            "title": "분석 확인",
            "detail": "주간 볼륨, 부위 편중, PR 변화를 확인합니다.",
            "href": "/summaries/weekly",
        }
    )
    return actions[:4]


def build_data_safety_status(backup_status: dict[str, str], has_password: bool, is_unlocked: bool) -> list[dict[str, str]]:
    return [
        {
            "state": "ok" if has_password else "warning",
            "label": "관리자 잠금",
            "value": "설정됨" if has_password else "미설정",
            "note": "방문자는 조회만 가능하고 입력/삭제는 잠금 뒤 허용됩니다." if has_password else "나만 입력하려면 설정 비밀번호를 먼저 등록하세요.",
        },
        {
            "state": "ok" if is_unlocked else "info",
            "label": "현재 세션",
            "value": "관리자" if is_unlocked else "보기 전용",
            "note": "현재 브라우저에서 입력/관리 가능" if is_unlocked else "POST 작업은 차단됩니다.",
        },
        {
            "state": "ok" if backup_status.get("count") != "0" else "warning",
            "label": "자동 백업",
            "value": backup_status.get("count", "0"),
            "note": f"최근 백업: {backup_status.get('last_backup', '없음')}",
        },
    ]
