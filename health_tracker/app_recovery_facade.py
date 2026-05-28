from __future__ import annotations

from health_tracker.app_coaching_reports_facade import build_monthly_report, build_weekly_report, get_balance_score
from health_tracker.app_database import get_db
from health_tracker.app_workout_facade import get_goal_progress
from health_tracker.constants import RECOMMENDED_EXERCISE_MAP
from health_tracker.date_utils import current_local_date, normalize_month, shift_date, shift_month, week_start_for_date
from health_tracker.services.coaching import (
    build_readiness_profile_from_db,
    get_recovery_checkin_from_db,
    list_daily_coaching_from_db,
    list_recovery_recommendations_from_db,
    save_recovery_checkin_to_db,
    save_rest_day_to_db,
)
from health_tracker.services.exercise_rules import today_rule_cards_from_db, weekly_rule_report_from_db
from health_tracker.services.personal_coach import build_next_actions_from_db


def list_recovery_recommendations(date_text: str) -> list[str]:
    return list_recovery_recommendations_from_db(get_db(), date_text, shift_date)


def build_period_insights(scope: str, date_text: str) -> list[str]:
    goals = get_goal_progress(date_text)
    if scope == "weekly":
        report = build_weekly_report(date_text)
        messages = [
            f"이번 주 운동일 목표는 {goals['weekly_workout_days']['percent']}% 달성했습니다.",
            f"식단 기록 목표는 {goals['weekly_meal_days']['percent']}% 달성했습니다.",
        ]
        if int(report["set_count"] or 0) == 0:
            messages.append("선택한 주에 운동 기록이 없습니다.")
        elif report["top_part"] != "-":
            messages.append(f"이번 주 가장 많이 한 부위는 {report['top_part']}입니다.")
        if float(report["cardio_minutes"] or 0) == 0:
            messages.append("이번 주 유산소 기록이 없습니다.")
        return messages[:4]

    report = build_monthly_report(date_text)
    messages = [
        f"월간 볼륨 목표는 {goals['monthly_volume']['percent']}% 달성했습니다.",
        f"월간 운동일 목표는 {goals['monthly_workout_days']['percent']}% 달성했습니다.",
        f"월간 유산소 목표는 {goals['monthly_cardio_minutes']['percent']}% 달성했습니다.",
    ]
    if int(report["pr_count"] or 0) > 0:
        messages.append(f"이번 달 신기록이 {report['pr_count']}개 있습니다.")
    if report["missing"]:
        messages.append(f"보강하면 좋은 부위: {', '.join(report['missing'][:3])}")
    return messages[:5]


def build_goal_insights(scope: str, date_text: str) -> list[str]:
    goals = get_goal_progress(date_text)
    keys = ["weekly_workout_days", "weekly_meal_days", "weekly_calories"] if scope == "weekly" else ["monthly_volume", "monthly_workout_days", "monthly_cardio_minutes"]
    messages = []
    for key in keys:
        goal = goals.get(key)
        if not goal or not goal["target"]:
            continue
        current = float(goal["current"] or 0)
        target = float(goal["target"] or 0)
        label = str(goal["label"])
        messages.append(f"{label} 목표 달성" if current >= target else f"{label} {target - current:.0f} 부족")
    return messages


def build_rpe_report(scope: str = "weekly", date_text: str | None = None) -> dict[str, object]:
    base_date = date_text or current_local_date()
    start = week_start_for_date(base_date) if scope == "weekly" else normalize_month(base_date[:7])
    end = shift_date(start, 6) if scope == "weekly" else shift_date(shift_month(start, 1), -1)
    row = get_db().execute(
        """
        SELECT AVG(rpe) AS avg_rpe, COUNT(rpe) AS rpe_count,
               SUM(CASE WHEN rpe >= 9 THEN 1 ELSE 0 END) AS hard_sets,
               SUM(CASE WHEN rpe <= 7 THEN 1 ELSE 0 END) AS easy_sets
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date BETWEEN ? AND ?
          AND ws.rpe IS NOT NULL
        """,
        (start, end),
    ).fetchone()
    avg_rpe = float(row["avg_rpe"] or 0)
    hard_sets = int(row["hard_sets"] or 0)
    easy_sets = int(row["easy_sets"] or 0)
    if not int(row["rpe_count"] or 0):
        message = "체감강도 기록이 아직 적습니다."
    elif hard_sets >= 5:
        message = "고강도 세트가 많아 다음 운동은 회복을 우선하세요."
    elif easy_sets >= 5 and avg_rpe <= 7.2:
        message = "여유 세트가 많아 주요 운동 증량을 고려해도 좋습니다."
    else:
        message = "강도 분포가 무난합니다."
    return {"avg_rpe": avg_rpe, "hard_sets": hard_sets, "easy_sets": easy_sets, "message": message}


def list_recovery_statuses(date_text: str) -> list[dict[str, object]]:
    start = shift_date(date_text, -2)
    rows = get_db().execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') IN ('하체', '등', '어깨', '가슴', '팔')
        GROUP BY body_part
        """,
        (start, date_text),
    ).fetchall()
    counts = {row["body_part"]: int(row["set_count"] or 0) for row in rows}
    statuses = []
    for part in ["하체", "등", "어깨", "가슴", "팔"]:
        count = counts.get(part, 0)
        state = "주의" if count >= 8 else "적정" if count >= 4 else "가능"
        statuses.append({"body_part": part, "set_count": count, "state": state})
    return statuses


def list_weekly_routine_recommendations(date_text: str) -> list[dict[str, object]]:
    balance = get_balance_score("weekly", date_text)
    missing = [part for part in balance["missing"] if part in ["하체", "등", "어깨", "가슴", "팔", "유산소"]]
    targets = (missing or ["하체", "등", "어깨"])[:3]
    recommendations = []
    for part in targets:
        items, equipment = list_preferred_exercises_for_body_part(part)
        reason = f"{part} 보강 추천"
        if equipment:
            reason = f"{reason} · {equipment}"
        recommendations.append({"body_part": part, "items": items, "reason": reason})
    return recommendations


def list_preferred_exercises_for_body_part(body_part: str, limit: int = 2) -> tuple[list[str], str]:
    rows = get_db().execute(
        """
        SELECT
            e.name,
            COALESCE(es.equipment, '') AS equipment,
            COALESCE(es.is_favorite, 0) AS is_favorite,
            COUNT(ws.id) AS set_count,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        WHERE COALESCE(NULLIF(ws.body_part, ''), '기타') = ?
        GROUP BY e.id, e.name, es.equipment, es.is_favorite
        ORDER BY is_favorite DESC, last_date DESC, set_count DESC, e.name
        LIMIT ?
        """,
        (body_part, limit),
    ).fetchall()
    items = [row["name"] for row in rows]
    for fallback in RECOMMENDED_EXERCISE_MAP.get(body_part, ["기록 운동"]):
        if len(items) >= limit:
            break
        if fallback not in items:
            items.append(fallback)
    equipment = next((row["equipment"] for row in rows if row["equipment"]), "")
    return items[:limit], equipment


def get_recovery_checkin(date_text: str) -> dict[str, object]:
    return get_recovery_checkin_from_db(get_db(), date_text)


def save_recovery_checkin(
    checkin_date: str,
    condition_score: int,
    sleep_score: int,
    soreness_score: int,
    fatigue_score: int,
    memo: str,
) -> None:
    save_recovery_checkin_to_db(
        get_db(),
        checkin_date,
        condition_score,
        sleep_score,
        soreness_score,
        fatigue_score,
        memo,
    )


def save_rest_day(date_text: str, reason: str, memo: str = "") -> None:
    save_rest_day_to_db(get_db(), date_text, reason, memo)


def list_daily_coaching(date_text: str) -> list[str]:
    return list_daily_coaching_from_db(get_db(), date_text, shift_date)


def list_today_next_actions(date_text: str) -> list[dict[str, str]]:
    return build_next_actions_from_db(get_db(), date_text, shift_date)


def list_today_rule_cards(date_text: str) -> list[dict[str, object]]:
    return today_rule_cards_from_db(get_db(), date_text, shift_date)


def build_weekly_rule_report(week_start: str) -> dict[str, object]:
    return weekly_rule_report_from_db(get_db(), week_start, shift_date)


def build_readiness_profile(date_text: str) -> dict[str, object]:
    return build_readiness_profile_from_db(get_db(), date_text)


def build_period_highlights(scope: str, date_text: str) -> list[dict[str, str]]:
    if scope == "weekly":
        start = week_start_for_date(date_text)
        end = shift_date(start, 6)
    else:
        start = normalize_month(date_text[:7])
        end = shift_date(shift_month(start, 1), -1)
    db = get_db()
    top_exercise = db.execute(
        """
        SELECT e.name, COUNT(ws.id) AS set_count,
               COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.workout_date BETWEEN ? AND ?
        GROUP BY e.name
        ORDER BY set_count DESC, volume DESC, e.name
        LIMIT 1
        """,
        (start, end),
    ).fetchone()
    best_pr = db.execute(
        """
        SELECT workout_date, exercise_name, record_type, record_value
        FROM pr_events
        WHERE workout_date BETWEEN ? AND ?
        ORDER BY record_value DESC, workout_date DESC
        LIMIT 1
        """,
        (start, end),
    ).fetchone()
    avg_recovery = db.execute(
        """
        SELECT AVG(condition_score) AS condition_score, AVG(sleep_score) AS sleep_score,
               AVG(soreness_score) AS soreness_score, AVG(fatigue_score) AS fatigue_score
        FROM recovery_checkins
        WHERE checkin_date BETWEEN ? AND ?
        """,
        (start, end),
    ).fetchone()
    highlights: list[dict[str, str]] = []
    if top_exercise:
        highlights.append(
            {
                "label": "최다 운동",
                "value": top_exercise["name"],
                "note": f"{int(top_exercise['set_count'] or 0)}세트 · {float(top_exercise['volume'] or 0):.0f}kg",
            }
        )
    if best_pr:
        highlights.append(
            {
                "label": "대표 PR",
                "value": best_pr["exercise_name"],
                "note": f"{best_pr['record_type']} {float(best_pr['record_value'] or 0):.0f} · {best_pr['workout_date']}",
            }
        )
    if avg_recovery and avg_recovery["condition_score"]:
        readiness = (
            float(avg_recovery["condition_score"] or 0)
            + float(avg_recovery["sleep_score"] or 0)
            + (6 - float(avg_recovery["fatigue_score"] or 3))
            + (6 - float(avg_recovery["soreness_score"] or 3))
        ) / 4
        highlights.append({"label": "회복 평균", "value": f"{readiness:.1f}/5", "note": "컨디션·수면·피로·근육통 기준"})
    if not highlights:
        highlights.append({"label": "리포트", "value": "기록 대기", "note": "운동이나 회복 기록을 입력하면 표시됩니다."})
    return highlights[:3]
