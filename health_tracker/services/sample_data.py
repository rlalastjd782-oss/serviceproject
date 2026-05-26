from __future__ import annotations

import sqlite3
from collections.abc import Callable


def delete_sample_data_from_db(db: sqlite3.Connection, cleanup_empty_sessions: Callable[[], None]) -> None:
    db.execute("DELETE FROM pr_events WHERE exercise_name LIKE '샘플%' OR exercise_name LIKE 'PR확인%'")
    db.execute(
        """
        DELETE FROM workout_sets
        WHERE exercise_id IN (
            SELECT id FROM exercises WHERE name LIKE '샘플%' OR name LIKE 'PR확인%'
        )
        """
    )
    db.execute("DELETE FROM exercises WHERE name LIKE '샘플%' OR name LIKE 'PR확인%'")
    db.execute("DELETE FROM meal_entries WHERE food_name LIKE '샘플%'")
    cleanup_empty_sessions()
    db.commit()


def create_may_sample_data_in_db(
    db: sqlite3.Connection,
    delete_sample_data: Callable[[], None],
    get_or_create_session: Callable[[str], sqlite3.Row],
    get_or_create_exercise: Callable[[str], int],
    save_exercise_equipment: Callable[[str, str], None],
    estimate_exercise_calories: Callable[[str, float | None, float | None, float | None, str], float | None],
) -> None:
    delete_sample_data()
    body_part_exercises = {
        "하체": ["샘플하체 스쿼트", "샘플하체 레그프레스", "샘플하체 런지", "샘플하체 레그컬"],
        "가슴": ["샘플가슴 벤치프레스", "샘플가슴 인클라인프레스", "샘플가슴 덤벨프레스", "샘플가슴 케이블플라이"],
        "등": ["샘플등 랫풀다운", "샘플등 바벨로우", "샘플등 시티드로우", "샘플등 풀업"],
        "어깨": ["샘플어깨 숄더프레스", "샘플어깨 사이드레터럴", "샘플어깨 리어델트", "샘플어깨 업라이트로우"],
        "팔": ["샘플팔 바벨컬", "샘플팔 해머컬", "샘플팔 케이블푸시다운", "샘플팔 딥스"],
    }
    parts = list(body_part_exercises.keys())
    equipment_by_part = {
        "하체": "바벨",
        "가슴": "바벨",
        "등": "핀머신",
        "어깨": "덤벨",
        "팔": "케이블",
    }
    meal_plans = [
        [
            ("아침", "샘플현미밥", 1, 180, 290),
            ("아침", "샘플계란", 2, 100, 150),
            ("점심", "샘플닭가슴살도시락", 1, 320, 520),
            ("점심", "샘플바나나", 1, 120, 105),
            ("저녁", "샘플연어샐러드", 1, 260, 430),
            ("간식", "샘플그릭요거트", 1, 150, 160),
        ],
        [
            ("아침", "샘플오트밀", 1, 80, 300),
            ("아침", "샘플프로틴쉐이크", 1, 300, 180),
            ("점심", "샘플소고기덮밥", 1, 380, 650),
            ("점심", "샘플방울토마토", 1, 120, 35),
            ("저녁", "샘플닭가슴살샐러드", 1, 300, 390),
            ("간식", "샘플아몬드", 1, 25, 145),
        ],
        [
            ("아침", "샘플통밀토스트", 2, 120, 310),
            ("아침", "샘플우유", 1, 200, 130),
            ("점심", "샘플돼지고기김치볶음밥", 1, 360, 680),
            ("점심", "샘플두부", 1, 150, 120),
            ("저녁", "샘플고구마닭가슴살", 1, 330, 480),
            ("간식", "샘플사과", 1, 180, 95),
        ],
        [
            ("아침", "샘플김밥", 1, 250, 420),
            ("아침", "샘플삶은계란", 2, 100, 150),
            ("점심", "샘플신라면건면", 1, 97, 350),
            ("점심", "샘플닭가슴살만두", 1, 180, 320),
            ("저녁", "샘플불고기정식", 1, 420, 720),
            ("간식", "샘플단백질바", 1, 55, 210),
        ],
        [
            ("아침", "샘플요거트볼", 1, 260, 360),
            ("아침", "샘플블루베리", 1, 80, 45),
            ("점심", "샘플참치비빔밥", 1, 380, 610),
            ("점심", "샘플미역국", 1, 250, 80),
            ("저녁", "샘플닭다리살구이", 1, 300, 540),
            ("간식", "샘플프로틴음료", 1, 250, 165),
        ],
    ]
    for day in range(1, 26):
        workout_date = f"2026-05-{day:02d}"
        part = parts[(day - 1) % len(parts)]
        session = get_or_create_session(workout_date)
        db.execute(
            "UPDATE workout_sessions SET completed = 1, duration_seconds = ? WHERE id = ?",
            (90 * 60, session["id"]),
        )
        sort_order = 1
        for exercise_index, exercise_name in enumerate(body_part_exercises[part]):
            exercise_id = get_or_create_exercise(exercise_name)
            save_exercise_equipment(exercise_name, equipment_by_part[part])
            base_weight = 30 + (day % 5) * 2.5 + exercise_index * 5
            for set_index in range(3):
                reps = 12 - set_index
                db.execute(
                    """
                    INSERT INTO workout_sets (
                        session_id, exercise_id, weight, reps, memo, sort_order,
                        body_part, set_type, rpe, equipment
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session["id"],
                        exercise_id,
                        base_weight + set_index * 2.5,
                        reps,
                        "5월 샘플",
                        sort_order,
                        part,
                        "본세트",
                        7 + (set_index * 0.5),
                        equipment_by_part[part],
                    ),
                )
                sort_order += 1
        cardio_id = get_or_create_exercise("샘플런닝 30분")
        calories = estimate_exercise_calories("유산소", 5.0, 5.5, 30, workout_date)
        db.execute(
            """
            INSERT INTO workout_sets (
                session_id, exercise_id, cardio_incline, cardio_speed, cardio_minutes,
                estimated_calories, memo, sort_order, body_part, set_type, rpe, equipment
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session["id"], cardio_id, 5.0, 5.5, 30, calories, "5월 샘플", sort_order, "유산소", "유산소", 6, "런닝머신"),
        )
        for meal_type, food_name, quantity, grams, meal_calories in meal_plans[(day - 1) % len(meal_plans)]:
            db.execute(
                """
                INSERT INTO meal_entries (
                    meal_date, meal_type, food_name, quantity, grams, calories, memo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (workout_date, meal_type, food_name, quantity, grams, meal_calories, "5월 샘플"),
            )
    db.commit()
