from __future__ import annotations

from health_tracker.app_database import get_db
from health_tracker.app_summary_facade import body_part_options
from health_tracker.date_utils import current_local_date, normalize_month, shift_date, shift_month, week_start_for_date


def build_weekly_report(date_text: str | None = None) -> dict[str, object]:
    week_start = week_start_for_date(date_text or current_local_date())
    week_end = shift_date(week_start, 6)
    db = get_db()
    totals = db.execute(
        """
        SELECT
            COUNT(DISTINCT CASE WHEN ws.id IS NOT NULL THEN s.workout_date END) AS workout_days,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories
        FROM workout_sessions s
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date BETWEEN ? AND ?
        """,
        (week_start, week_end),
    ).fetchone()
    meal_days = db.execute(
        "SELECT COUNT(DISTINCT meal_date) AS meal_days FROM meal_entries WHERE meal_date BETWEEN ? AND ?",
        (week_start, week_end),
    ).fetchone()["meal_days"]
    duration_seconds = db.execute(
        """
        SELECT COALESCE(SUM(s.duration_seconds), 0) AS duration_seconds
        FROM workout_sessions s
        WHERE s.workout_date BETWEEN ? AND ?
          AND EXISTS (SELECT 1 FROM workout_sets ws WHERE ws.session_id = s.id)
        """,
        (week_start, week_end),
    ).fetchone()["duration_seconds"]
    top_part = db.execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date BETWEEN ? AND ?
        GROUP BY body_part
        ORDER BY set_count DESC
        LIMIT 1
        """,
        (week_start, week_end),
    ).fetchone()
    return {
        "period": f"{week_start} ~ {week_end}",
        "workout_days": int(totals["workout_days"] or 0),
        "set_count": int(totals["set_count"] or 0),
        "volume": float(totals["volume"] or 0),
        "cardio_minutes": float(totals["cardio_minutes"] or 0),
        "exercise_calories": float(totals["exercise_calories"] or 0),
        "duration_seconds": int(duration_seconds or 0),
        "meal_days": int(meal_days or 0),
        "top_part": top_part["body_part"] if top_part else "-",
    }


def build_monthly_report(date_text: str | None = None) -> dict[str, object]:
    base_date = date_text or current_local_date()
    month_start = normalize_month(base_date[:7])
    next_month = shift_month(month_start, 1)
    db = get_db()
    totals = db.execute(
        """
        SELECT
            COUNT(DISTINCT CASE WHEN ws.id IS NOT NULL THEN s.workout_date END) AS workout_days,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sessions s
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        """,
        (month_start, next_month),
    ).fetchone()
    top_exercise = db.execute(
        """
        SELECT e.name, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE s.workout_date >= ? AND s.workout_date < ?
        GROUP BY e.name
        ORDER BY set_count DESC, e.name
        LIMIT 1
        """,
        (month_start, next_month),
    ).fetchone()
    duration_seconds = db.execute(
        """
        SELECT COALESCE(SUM(s.duration_seconds), 0) AS duration_seconds
        FROM workout_sessions s
        WHERE s.workout_date >= ? AND s.workout_date < ?
          AND EXISTS (SELECT 1 FROM workout_sets ws WHERE ws.session_id = s.id)
        """,
        (month_start, next_month),
    ).fetchone()["duration_seconds"]
    metrics = db.execute(
        """
        SELECT metric_date, body_weight
        FROM body_metrics
        WHERE metric_date >= ? AND metric_date < ? AND body_weight IS NOT NULL
        ORDER BY metric_date ASC
        """,
        (month_start, next_month),
    ).fetchall()
    weight_delta = 0.0
    if len(metrics) >= 2:
        weight_delta = float(metrics[-1]["body_weight"] or 0) - float(metrics[0]["body_weight"] or 0)
    pr_count = db.execute(
        "SELECT COUNT(id) AS count FROM pr_events WHERE workout_date >= ? AND workout_date < ?",
        (month_start, next_month),
    ).fetchone()["count"]
    balance = get_balance_score("monthly", base_date)
    return {
        "period": month_start[:7],
        "workout_days": int(totals["workout_days"] or 0),
        "set_count": int(totals["set_count"] or 0),
        "volume": float(totals["volume"] or 0),
        "duration_seconds": int(duration_seconds or 0),
        "top_exercise": top_exercise["name"] if top_exercise else "-",
        "top_exercise_sets": int(top_exercise["set_count"] or 0) if top_exercise else 0,
        "weight_delta": weight_delta,
        "balance_score": balance["score"],
        "missing": balance["missing"],
        "pr_count": int(pr_count or 0),
    }


def list_balance_warnings(scope: str = "weekly", date_text: str | None = None) -> list[str]:
    base_date = date_text or current_local_date()
    if scope == "weekly":
        start = week_start_for_date(base_date)
        end = shift_date(start, 6)
    else:
        start = normalize_month(base_date[:7])
        end = shift_month(start, 1)
    rows = get_db().execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date >= ? AND s.workout_date <= ?
        GROUP BY body_part
        """,
        (start, end),
    ).fetchall()
    counts = {part: 0 for part in body_part_options()}
    counts.update({row["body_part"]: int(row["set_count"]) for row in rows})
    total = sum(counts.values())
    warnings = []
    if total == 0:
        return ["이번 기간 운동 기록이 없습니다."]
    for part, count in counts.items():
        if part != "기타" and count == 0:
            warnings.append(f"{part} 운동이 비어 있습니다.")
    dominant = max(counts.items(), key=lambda item: item[1])
    if dominant[1] / total >= 0.5 and total >= 4:
        warnings.append(f"{dominant[0]} 비중이 높습니다. 다른 부위도 균형 있게 넣어보세요.")
    return warnings[:4]


def list_volume_warnings(date_text: str) -> list[str]:
    start_date = shift_date(date_text, -6)
    rows = get_db().execute(
        """
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COUNT(DISTINCT s.workout_date) AS workout_days
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date BETWEEN ? AND ?
        GROUP BY body_part
        ORDER BY set_count DESC
        """,
        (start_date, date_text),
    ).fetchall()
    warnings = []
    for row in rows:
        body_part = row["body_part"]
        if body_part != "유산소" and int(row["set_count"] or 0) >= 18:
            warnings.append(f"{body_part} 세트가 최근 7일 {row['set_count']}세트입니다.")
        if body_part != "유산소" and int(row["workout_days"] or 0) >= 3:
            warnings.append(f"{body_part}를 최근 7일 중 {row['workout_days']}일 운동했습니다.")
    return warnings[:3]


def get_balance_score(scope: str = "weekly", date_text: str | None = None) -> dict[str, object]:
    base_date = date_text or current_local_date()
    if scope == "weekly":
        start = week_start_for_date(base_date)
        end = shift_date(start, 6)
    else:
        start = normalize_month(base_date[:7])
        end = shift_date(shift_month(start, 1), -1)
    rows = get_db().execute(
        """
        SELECT COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part, COUNT(ws.id) AS set_count
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        WHERE s.workout_date BETWEEN ? AND ?
          AND COALESCE(NULLIF(ws.body_part, ''), '기타') != '기타'
        GROUP BY body_part
        """,
        (start, end),
    ).fetchall()
    target_parts = ["하체", "가슴", "등", "어깨", "팔(이두)", "팔(삼두)", "유산소"]
    counts = {part: 0 for part in target_parts}
    counts.update({row["body_part"]: int(row["set_count"]) for row in rows if row["body_part"] in counts})
    filled = sum(1 for count in counts.values() if count > 0)
    score = round(filled / len(target_parts) * 100)
    missing = [part for part, count in counts.items() if count == 0]
    return {"score": score, "counts": counts, "missing": missing, "period": f"{start} ~ {end}"}
