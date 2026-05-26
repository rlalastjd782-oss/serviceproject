from __future__ import annotations

import sqlite3
from datetime import date, timedelta


QA_PREFIX = "QA-연간"
QA_START_DATE = "2025-07-01"
QA_DAYS = 365
QA_END_DATE = "2026-06-30"


BODY_PARTS = ["가슴", "등", "하체", "어깨", "팔", "코어", "유산소"]
EQUIPMENT = ["바벨", "덤벨", "머신", "케이블", "프리웨이트", "랙", "맨몸", "트레드밀", "사이클"]
MEAL_TYPES = ["아침", "점심", "저녁", "간식"]


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def save_dummy_meta(db: sqlite3.Connection) -> None:
    db.execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES ('qa_dummy_range', ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """,
        (f"{QA_START_DATE}~{QA_END_DATE}",),
    )


def get_qa_dummy_status(db: sqlite3.Connection) -> dict[str, object]:
    exercise_count = db.execute("SELECT COUNT(id) FROM exercises WHERE name LIKE ?", (f"{QA_PREFIX}%",)).fetchone()[0]
    set_count = db.execute(
        """
        SELECT COUNT(ws.id)
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE e.name LIKE ?
        """,
        (f"{QA_PREFIX}%",),
    ).fetchone()[0]
    meal_count = db.execute("SELECT COUNT(id) FROM meal_entries WHERE food_name LIKE ?", (f"{QA_PREFIX}%",)).fetchone()[0]
    pr_count = db.execute("SELECT COUNT(id) FROM pr_events WHERE exercise_name LIKE ?", (f"{QA_PREFIX}%",)).fetchone()[0]
    metric_count = db.execute("SELECT COUNT(*) FROM body_metrics WHERE metric_date BETWEEN ? AND ?", (QA_START_DATE, QA_END_DATE)).fetchone()[0]
    recovery_count = db.execute(
        "SELECT COUNT(*) FROM recovery_checkins WHERE checkin_date BETWEEN ? AND ? AND memo LIKE ?",
        (QA_START_DATE, QA_END_DATE, f"{QA_PREFIX}%"),
    ).fetchone()[0]
    range_row = db.execute("SELECT value FROM app_settings WHERE key = 'qa_dummy_range'").fetchone()
    return {
        "exists": bool(exercise_count or set_count or meal_count),
        "range": range_row["value"] if range_row else f"{QA_START_DATE}~{QA_END_DATE}",
        "exercises": int(exercise_count or 0),
        "sets": int(set_count or 0),
        "meals": int(meal_count or 0),
        "prs": int(pr_count or 0),
        "body_metrics": int(metric_count or 0),
        "recovery": int(recovery_count or 0),
    }


def enrich_year_qa_dummy_data(db: sqlite3.Connection) -> None:
    start = parse_iso_date(QA_START_DATE)
    for day_index in range(QA_DAYS):
        current = start + timedelta(days=day_index)
        day_text = current.isoformat()
        week_phase = day_index % 28
        is_rest_day = day_index % 7 == 6
        is_deload = week_phase >= 21
        condition = 3 + (1 if not is_deload and not is_rest_day else 0)
        sleep = 4 if day_index % 11 not in {0, 1} else 2
        soreness = 4 if week_phase in {18, 19, 20} else 2 + (day_index % 2)
        fatigue = 4 if is_deload else 2 + (day_index % 3 == 0)
        db.execute(
            """
            INSERT INTO recovery_checkins (
                checkin_date, condition_score, sleep_score, soreness_score, fatigue_score,
                is_rest_day, rest_reason, memo, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(checkin_date) DO UPDATE SET
                condition_score = excluded.condition_score,
                sleep_score = excluded.sleep_score,
                soreness_score = excluded.soreness_score,
                fatigue_score = excluded.fatigue_score,
                is_rest_day = excluded.is_rest_day,
                rest_reason = excluded.rest_reason,
                memo = excluded.memo,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                day_text,
                condition,
                sleep,
                soreness,
                fatigue,
                1 if is_rest_day else 0,
                f"{QA_PREFIX} 휴식" if is_rest_day else "",
                f"{QA_PREFIX} 회복 패턴 {'디로드' if is_deload else '훈련'}",
            ),
        )

        if day_index % 7 == 0:
            month_wave = (day_index // 30) % 4
            body_weight = 82.0 - day_index * 0.018 + month_wave * 0.2
            muscle_mass = 34.5 + min(day_index, 240) * 0.006 - (0.2 if is_deload else 0)
            body_fat = 24.0 - day_index * 0.022 + (0.3 if is_deload else 0)
            waist = 89.0 - day_index * 0.025
            db.execute(
                """
                INSERT INTO body_metrics (metric_date, body_weight, muscle_mass, body_fat, waist, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(metric_date) DO UPDATE SET
                    body_weight = excluded.body_weight,
                    muscle_mass = excluded.muscle_mass,
                    body_fat = excluded.body_fat,
                    waist = excluded.waist,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    day_text,
                    round(body_weight, 1),
                    round(muscle_mass, 1),
                    round(max(12, body_fat), 1),
                    round(max(72, waist), 1),
                ),
            )


def generate_year_qa_dummy_data(db: sqlite3.Connection) -> dict[str, object]:
    status = get_qa_dummy_status(db)
    if status["exists"]:
        enrich_year_qa_dummy_data(db)
        save_dummy_meta(db)
        db.commit()
        return get_qa_dummy_status(db)

    exercise_ids: list[int] = []
    for index in range(100):
        name = f"{QA_PREFIX}-운동-{index + 1:03d}"
        db.execute("INSERT OR IGNORE INTO exercises (name) VALUES (?)", (name,))
        exercise_id = db.execute("SELECT id FROM exercises WHERE name = ?", (name,)).fetchone()["id"]
        exercise_ids.append(int(exercise_id))
        db.execute(
            """
            INSERT INTO exercise_settings (exercise_name, rest_seconds, is_favorite, equipment, target_weight, target_reps, target_sets)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(exercise_name) DO UPDATE SET
                rest_seconds = excluded.rest_seconds,
                is_favorite = excluded.is_favorite,
                equipment = excluded.equipment,
                target_weight = excluded.target_weight,
                target_reps = excluded.target_reps,
                target_sets = excluded.target_sets
            """,
            (
                name,
                60 + (index % 5) * 15,
                1 if index % 9 == 0 else 0,
                EQUIPMENT[index % len(EQUIPMENT)],
                40 + index % 45,
                8 + index % 5,
                3 + index % 3,
            ),
        )

    start = parse_iso_date(QA_START_DATE)
    for day_index in range(QA_DAYS):
        current = start + timedelta(days=day_index)
        day_text = current.isoformat()
        is_rest_day = day_index % 7 == 6
        db.execute(
            """
            INSERT OR IGNORE INTO workout_sessions (workout_date, note, completed, duration_seconds)
            VALUES (?, ?, ?, ?)
            """,
            (
                day_text,
                f"{QA_PREFIX} 더미 세션",
                0 if is_rest_day else 1,
                0 if is_rest_day else 2700 + (day_index % 6) * 300,
            ),
        )
        session = db.execute("SELECT id FROM workout_sessions WHERE workout_date = ?", (day_text,)).fetchone()
        session_id = int(session["id"])

        if not is_rest_day:
            for set_index in range(10):
                exercise_offset = (day_index * 3 + set_index) % len(exercise_ids)
                exercise_id = exercise_ids[exercise_offset]
                body_part = BODY_PARTS[(day_index + set_index) % len(BODY_PARTS)]
                equipment = EQUIPMENT[(day_index + set_index) % len(EQUIPMENT)]
                if body_part == "유산소":
                    weight = None
                    reps = None
                    cardio_minutes = 18 + (day_index + set_index) % 28
                    cardio_speed = 5.5 + ((day_index + set_index) % 10) / 10
                    cardio_incline = float((day_index + set_index) % 8)
                    estimated_calories = round(cardio_minutes * (6.5 + cardio_speed), 1)
                else:
                    weight = 30 + (exercise_offset % 35) * 2.5 + (day_index % 4) * 1.25
                    reps = 6 + (set_index % 8)
                    cardio_minutes = None
                    cardio_speed = None
                    cardio_incline = None
                    estimated_calories = None
                db.execute(
                    """
                    INSERT INTO workout_sets (
                        session_id, exercise_id, body_part, set_type, weight, reps,
                        cardio_incline, cardio_speed, cardio_minutes, estimated_calories,
                        rpe, equipment, memo, sort_order
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        exercise_id,
                        body_part,
                        "본세트" if set_index % 5 else "워밍업",
                        weight,
                        reps,
                        cardio_incline,
                        cardio_speed,
                        cardio_minutes,
                        estimated_calories,
                        6 + (set_index % 4) * 0.5,
                        equipment,
                        f"{QA_PREFIX} 연도 경계 검증",
                        set_index + 1,
                    ),
                )
                if day_index % 17 == 0 and set_index == 0:
                    exercise_name = f"{QA_PREFIX}-운동-{exercise_offset + 1:03d}"
                    db.execute(
                        """
                        INSERT INTO pr_events (workout_date, set_id, exercise_id, exercise_name, record_type, record_value)
                        VALUES (?, last_insert_rowid(), ?, ?, ?, ?)
                        """,
                        (day_text, exercise_id, exercise_name, "QA PR", float(weight or cardio_minutes or 0)),
                    )
        else:
            db.execute(
                """
                INSERT OR REPLACE INTO recovery_checkins
                    (checkin_date, condition_score, sleep_score, soreness_score, fatigue_score, is_rest_day, rest_reason, memo)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (day_text, 3, 4, 2, 2, f"{QA_PREFIX} 휴식", f"{QA_PREFIX} 회복일"),
            )

        for meal_index, meal_type in enumerate(MEAL_TYPES):
            db.execute(
                """
                INSERT INTO meal_entries (meal_date, meal_type, food_name, quantity, grams, calories, memo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    day_text,
                    meal_type,
                    f"{QA_PREFIX}-식단-{meal_index + 1}",
                    1,
                    120 + meal_index * 60,
                    280 + meal_index * 140 + (day_index % 9) * 10,
                    f"{QA_PREFIX} 식단 더미",
                ),
            )

    enrich_year_qa_dummy_data(db)
    save_dummy_meta(db)
    db.commit()
    return get_qa_dummy_status(db)
