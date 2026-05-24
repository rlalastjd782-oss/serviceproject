from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from flask import Flask, g, jsonify, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "instance" / "workout.db"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["DATABASE"] = DATABASE

    @app.before_request
    def before_request() -> None:
        init_db()

    @app.teardown_appcontext
    def close_db(error: Exception | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.get("/")
    def index():
        selected_date = request.args.get("date") or current_local_date()
        today_session = get_session_for_date(selected_date)
        sessions = list_recent_sessions()
        exercises = list_exercises()
        meals = list_meals_for_date(today_session["workout_date"])
        return render_template(
            "index.html",
            session=today_session,
            sessions=sessions,
            exercises=exercises,
            meals=meals,
            meal_groups=grouped_meals_for_date(today_session["workout_date"]),
            today_summary=get_day_summary(today_session["workout_date"]),
            body_parts=body_part_options(),
            active_page="today",
        )

    @app.get("/summaries")
    def summaries():
        return redirect(url_for("weekly_summary_page"))

    @app.get("/summaries/daily")
    def daily_summary_page():
        return render_template(
            "summary_page.html",
            page_title="일간 집계",
            page_kicker="Daily",
            table_kind="daily",
            daily_summary=list_daily_summary(),
            body_part_summary=list_body_part_summary("daily"),
            active_page="daily",
        )

    @app.get("/summaries/weekly")
    def weekly_summary_page():
        period_rows = list_weekly_summary()
        chart_rows = list_daily_summary(limit=7)
        return render_template(
            "summary_page.html",
            page_title="주간 집계",
            page_kicker="Weekly",
            table_kind="period",
            period_rows=period_rows,
            period_label="기간",
            chart_items=build_daily_chart(chart_rows),
            chart_title="일별 추이",
            chart_note="최근 기록일 7개를 일별로 표시합니다.",
            body_part_summary=list_body_part_summary("weekly"),
            body_part_details=list_weekly_body_part_details(),
            active_page="weekly",
        )

    @app.get("/summaries/monthly")
    def monthly_summary_page():
        period_rows = list_monthly_summary()
        chart_rows = list_weekly_summary(limit=6)
        return render_template(
            "summary_page.html",
            page_title="월간 집계",
            page_kicker="Monthly",
            table_kind="period",
            period_rows=period_rows,
            period_label="기간",
            chart_items=build_period_chart(chart_rows),
            chart_title="주간별 추이",
            chart_note="최근 6주를 주간 단위로 표시합니다.",
            body_part_summary=list_body_part_summary("monthly"),
            active_page="monthly",
        )

    @app.get("/summaries/exercises")
    def exercise_summary_page():
        return render_template(
            "summary_page.html",
            page_title="운동별 횟수",
            page_kicker="Exercise",
            table_kind="exercise",
            exercise_summary=list_exercise_summary(),
            active_page="exercises",
        )

    @app.post("/sets")
    def create_set():
        session = get_or_create_session(request.form.get("workout_date"))
        body_part = request.form.get("body_part", "").strip() or "기타"
        exercise_name = request.form.get("exercise_name", "").strip()
        if not exercise_name:
            return redirect(url_for("index", date=session["workout_date"]))

        set_weights = request.form.getlist("set_weight") or [request.form.get("weight", "")]
        set_reps = request.form.getlist("set_reps") or [request.form.get("reps", "")]
        set_memos = request.form.getlist("set_memo") or [request.form.get("memo", "")]
        set_count = max(len(set_weights), len(set_reps), len(set_memos))
        set_rows = []
        for index in range(set_count):
            weight_value = value_at(set_weights, index)
            reps_value = value_at(set_reps, index)
            memo_value = value_at(set_memos, index).strip()
            if weight_value.strip() == "" and reps_value.strip() == "" and memo_value == "":
                continue
            set_rows.append(
                (
                    parse_float(weight_value),
                    parse_int(reps_value),
                    memo_value,
                )
            )

        if not set_rows:
            return redirect(url_for("index", date=session["workout_date"]))

        db = get_db()
        exercise_id = get_or_create_exercise(exercise_name)
        next_order = db.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workout_sets WHERE session_id = ?",
            (session["id"],),
        ).fetchone()[0]
        for offset, (weight, reps, memo) in enumerate(set_rows):
            db.execute(
                """
                INSERT INTO workout_sets (session_id, exercise_id, weight, reps, memo, sort_order, body_part)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session["id"], exercise_id, weight, reps, memo, next_order + offset, body_part),
            )
        db.commit()
        return redirect(url_for("index", date=session["workout_date"]))

    @app.post("/meals")
    def create_meal():
        meal_date = request.form.get("meal_date") or current_local_date()
        meal_type = request.form.get("meal_type", "").strip()
        food_names = request.form.getlist("meal_food_name") or [request.form.get("food_name", "")]
        quantities = request.form.getlist("meal_quantity") or [request.form.get("amount", "")]
        grams_values = request.form.getlist("meal_grams") or [request.form.get("grams", "")]
        calories_values = request.form.getlist("meal_calories") or [request.form.get("calories", "")]
        memos = request.form.getlist("meal_memo") or [request.form.get("memo", "")]
        row_count = max(
            len(food_names),
            len(quantities),
            len(grams_values),
            len(calories_values),
            len(memos),
        )
        meal_rows = []
        for index in range(row_count):
            food_name = value_at(food_names, index).strip()
            quantity = value_at(quantities, index)
            grams = value_at(grams_values, index)
            calories = value_at(calories_values, index)
            memo = value_at(memos, index).strip()
            if food_name == "" and quantity.strip() == "" and grams.strip() == "" and calories.strip() == "" and memo == "":
                continue
            if food_name == "":
                continue
            meal_rows.append(
                (
                    food_name,
                    parse_float(quantity),
                    parse_float(grams),
                    parse_float(calories),
                    memo,
                )
            )

        if not meal_rows:
            return redirect(url_for("index", date=meal_date))

        db = get_db()
        for food_name, quantity, grams, calories, memo in meal_rows:
            db.execute(
                """
                INSERT INTO meal_entries
                    (meal_date, meal_type, food_name, quantity, grams, calories, memo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (meal_date, meal_type, food_name, quantity, grams, calories, memo),
            )
        db.commit()
        return redirect(url_for("index", date=meal_date))

    @app.post("/meals/<int:meal_id>/update")
    def update_meal(meal_id: int):
        db = get_db()
        meal = db.execute("SELECT meal_date FROM meal_entries WHERE id = ?", (meal_id,)).fetchone()
        meal_date = meal["meal_date"] if meal else current_local_date()
        food_name = request.form.get("food_name", "").strip()
        if food_name:
            db.execute(
                """
                UPDATE meal_entries
                SET food_name = ?, quantity = ?, grams = ?, calories = ?
                WHERE id = ?
                """,
                (
                    food_name,
                    parse_float(request.form.get("quantity")),
                    parse_float(request.form.get("grams")),
                    parse_float(request.form.get("calories")),
                    meal_id,
                ),
            )
            db.commit()
        return redirect(url_for("index", date=meal_date))

    @app.post("/meals/<int:meal_id>/delete")
    def delete_meal(meal_id: int):
        db = get_db()
        meal = db.execute("SELECT meal_date FROM meal_entries WHERE id = ?", (meal_id,)).fetchone()
        db.execute("DELETE FROM meal_entries WHERE id = ?", (meal_id,))
        db.commit()
        return redirect(url_for("index", date=meal["meal_date"] if meal else None))

    @app.post("/sets/<int:set_id>/update")
    def update_set(set_id: int):
        db = get_db()
        workout = db.execute(
            """
            SELECT s.workout_date
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            WHERE ws.id = ?
            """,
            (set_id,),
        ).fetchone()
        workout_date = workout["workout_date"] if workout else current_local_date()
        db.execute(
            """
            UPDATE workout_sets
            SET weight = ?, reps = ?
            WHERE id = ?
            """,
            (
                parse_float(request.form.get("weight")),
                parse_int(request.form.get("reps")),
                set_id,
            ),
        )
        db.commit()
        return redirect(url_for("index", date=workout_date))

    @app.post("/sets/<int:set_id>/delete")
    def delete_set(set_id: int):
        db = get_db()
        workout = db.execute(
            """
            SELECT s.workout_date
            FROM workout_sets ws
            JOIN workout_sessions s ON s.id = ws.session_id
            WHERE ws.id = ?
            """,
            (set_id,),
        ).fetchone()
        db.execute("DELETE FROM workout_sets WHERE id = ?", (set_id,))
        db.commit()
        return redirect(url_for("index", date=workout["workout_date"] if workout else None))

    @app.get("/api/sessions")
    def api_sessions():
        return jsonify([dict(row) for row in list_recent_sessions(limit=30)])

    return app


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        DATABASE.parent.mkdir(exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_date TEXT NOT NULL UNIQUE,
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS workout_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            body_part TEXT NOT NULL DEFAULT '기타',
            weight REAL,
            reps INTEGER,
            memo TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES workout_sessions (id) ON DELETE CASCADE,
            FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS meal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_date TEXT NOT NULL,
            meal_type TEXT NOT NULL DEFAULT '',
            food_name TEXT NOT NULL,
            quantity REAL,
            grams REAL,
            calories REAL,
            protein REAL,
            carbs REAL,
            fat REAL,
            memo TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    ensure_column(db, "workout_sets", "body_part", "TEXT NOT NULL DEFAULT '기타'")
    ensure_column(db, "meal_entries", "quantity", "REAL")
    ensure_column(db, "meal_entries", "grams", "REAL")
    db.execute(
        """
        UPDATE meal_entries
        SET
            quantity = COALESCE(quantity, calories),
            grams = COALESCE(grams, protein),
            calories = NULL,
            protein = NULL
        WHERE quantity IS NULL
          AND grams IS NULL
          AND (calories IS NOT NULL OR protein IS NOT NULL)
          AND carbs IS NULL
          AND fat IS NULL
        """
    )
    db.commit()


def ensure_column(db: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    columns = [row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def get_or_create_session(workout_date: str | None = None) -> sqlite3.Row:
    db = get_db()
    date_value = workout_date or current_local_date()
    existing = db.execute(
        "SELECT * FROM workout_sessions WHERE workout_date = ?",
        (date_value,),
    ).fetchone()
    if existing:
        return existing

    db.execute("INSERT INTO workout_sessions (workout_date) VALUES (?)", (date_value,))
    db.commit()
    return db.execute(
        "SELECT * FROM workout_sessions WHERE workout_date = ?",
        (date_value,),
    ).fetchone()


def get_session_for_date(workout_date: str) -> sqlite3.Row | dict[str, str | None]:
    existing = get_db().execute(
        "SELECT * FROM workout_sessions WHERE workout_date = ?",
        (workout_date,),
    ).fetchone()
    if existing:
        return existing
    return {"id": None, "workout_date": workout_date}


def get_or_create_exercise(name: str) -> int:
    db = get_db()
    existing = db.execute("SELECT id FROM exercises WHERE name = ?", (name,)).fetchone()
    if existing:
        return int(existing["id"])
    cursor = db.execute("INSERT INTO exercises (name) VALUES (?)", (name,))
    db.commit()
    return int(cursor.lastrowid)


def list_exercises() -> list[sqlite3.Row]:
    return get_db().execute("SELECT name FROM exercises ORDER BY name").fetchall()


def body_part_options() -> list[str]:
    return ["하체", "가슴", "팔", "등", "어깨", "기타"]


def list_recent_sessions(limit: int = 10) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT
            s.id,
            s.workout_date,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sessions s
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        GROUP BY s.id
        ORDER BY s.workout_date DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def list_meals_for_date(meal_date: str) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT *
        FROM meal_entries
        WHERE meal_date = ?
        ORDER BY created_at DESC, id DESC
        """,
        (meal_date,),
    ).fetchall()


def grouped_meals_for_date(meal_date: str) -> list[dict[str, object]]:
    rows = get_db().execute(
        """
        SELECT *
        FROM meal_entries
        WHERE meal_date = ?
        ORDER BY
            CASE meal_type
                WHEN '아침' THEN 1
                WHEN '점심' THEN 2
                WHEN '저녁' THEN 3
                WHEN '간식' THEN 4
                ELSE 5
            END,
            id
        """,
        (meal_date,),
    ).fetchall()
    groups: list[dict[str, object]] = []
    group_by_type: dict[str, dict[str, object]] = {}
    for item in rows:
        meal_type = item["meal_type"] or "식사"
        if meal_type not in group_by_type:
            group = {"meal_type": meal_type, "entries": []}
            group_by_type[meal_type] = group
            groups.append(group)
        group_by_type[meal_type]["entries"].append(item)
    return groups


def get_day_summary(day: str) -> dict[str, float]:
    db = get_db()
    workout = db.execute(
        """
        SELECT
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sessions s
        LEFT JOIN workout_sets ws ON ws.session_id = s.id
        WHERE s.workout_date = ?
        """,
        (day,),
    ).fetchone()
    meal = db.execute(
        """
        SELECT
            COUNT(id) AS meal_count,
            COALESCE(SUM(quantity), 0) AS amount,
            COALESCE(SUM(grams), 0) AS grams,
            COALESCE(SUM(calories), 0) AS calories
        FROM meal_entries
        WHERE meal_date = ?
        """,
        (day,),
    ).fetchone()
    return {
        "set_count": workout["set_count"],
        "rep_count": workout["rep_count"],
        "volume": workout["volume"],
        "meal_count": meal["meal_count"],
        "amount": meal["amount"],
        "grams": meal["grams"],
        "calories": meal["calories"],
    }


def list_daily_summary(limit: int = 14) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        WITH workout AS (
            SELECT
                s.workout_date AS period,
                COUNT(ws.id) AS set_count,
                COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
                COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
            FROM workout_sessions s
            LEFT JOIN workout_sets ws ON ws.session_id = s.id
            GROUP BY s.workout_date
        ),
        meal AS (
            SELECT
                meal_date AS period,
                COUNT(id) AS meal_count,
                COALESCE(SUM(quantity), 0) AS amount,
                COALESCE(SUM(grams), 0) AS grams,
                COALESCE(SUM(calories), 0) AS calories
            FROM meal_entries
            GROUP BY meal_date
        ),
        periods AS (
            SELECT period FROM workout
            UNION
            SELECT period FROM meal
        )
        SELECT
            p.period,
            COALESCE(w.set_count, 0) AS set_count,
            COALESCE(w.rep_count, 0) AS rep_count,
            COALESCE(w.volume, 0) AS volume,
            COALESCE(m.meal_count, 0) AS meal_count,
            COALESCE(m.amount, 0) AS amount,
            COALESCE(m.grams, 0) AS grams,
            COALESCE(m.calories, 0) AS calories
        FROM periods p
        LEFT JOIN workout w ON w.period = p.period
        LEFT JOIN meal m ON m.period = p.period
        ORDER BY p.period DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def list_weekly_summary(limit: int = 12) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        WITH workout AS (
            SELECT
                strftime('%Y-%m', s.workout_date) AS month_key,
                CAST(strftime('%m', s.workout_date) AS INTEGER) AS month_number,
                ((CAST(strftime('%d', s.workout_date) AS INTEGER) - 1) / 7) + 1 AS week_of_month,
                COUNT(DISTINCT s.workout_date) AS workout_days,
                COUNT(ws.id) AS set_count,
                COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
                COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
            FROM workout_sessions s
            LEFT JOIN workout_sets ws ON ws.session_id = s.id
            GROUP BY month_key, week_of_month
        ),
        meal AS (
            SELECT
                strftime('%Y-%m', meal_date) AS month_key,
                CAST(strftime('%m', meal_date) AS INTEGER) AS month_number,
                ((CAST(strftime('%d', meal_date) AS INTEGER) - 1) / 7) + 1 AS week_of_month,
                COUNT(DISTINCT meal_date) AS meal_days,
                COUNT(id) AS meal_count,
                COALESCE(SUM(quantity), 0) AS amount,
                COALESCE(SUM(grams), 0) AS grams,
                COALESCE(SUM(calories), 0) AS calories
            FROM meal_entries
            GROUP BY month_key, week_of_month
        ),
        periods AS (
            SELECT month_key, month_number, week_of_month FROM workout
            UNION
            SELECT month_key, month_number, week_of_month FROM meal
        )
        SELECT
            p.month_key || '-' || p.week_of_month AS period_key,
            p.month_number || '월 ' || p.week_of_month || '주차' AS period,
            COALESCE(w.workout_days, 0) AS workout_days,
            COALESCE(w.set_count, 0) AS set_count,
            COALESCE(w.rep_count, 0) AS rep_count,
            COALESCE(w.volume, 0) AS volume,
            COALESCE(m.meal_days, 0) AS meal_days,
            COALESCE(m.meal_count, 0) AS meal_count,
            COALESCE(m.amount, 0) AS amount,
            COALESCE(m.grams, 0) AS grams,
            COALESCE(m.calories, 0) AS calories
        FROM periods p
        LEFT JOIN workout w
            ON w.month_key = p.month_key AND w.week_of_month = p.week_of_month
        LEFT JOIN meal m
            ON m.month_key = p.month_key AND m.week_of_month = p.week_of_month
        ORDER BY p.month_key DESC, p.week_of_month DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def list_monthly_summary(limit: int = 12) -> list[sqlite3.Row]:
    return list_period_summary("%Y-%m", limit)


def list_period_summary(period_format: str, limit: int) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        WITH workout AS (
            SELECT
                strftime(?, s.workout_date) AS period,
                COUNT(DISTINCT s.workout_date) AS workout_days,
                COUNT(ws.id) AS set_count,
                COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
                COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
            FROM workout_sessions s
            LEFT JOIN workout_sets ws ON ws.session_id = s.id
            GROUP BY strftime(?, s.workout_date)
        ),
        meal AS (
            SELECT
                strftime(?, meal_date) AS period,
                COUNT(DISTINCT meal_date) AS meal_days,
                COUNT(id) AS meal_count,
                COALESCE(SUM(quantity), 0) AS amount,
                COALESCE(SUM(grams), 0) AS grams,
                COALESCE(SUM(calories), 0) AS calories
            FROM meal_entries
            GROUP BY strftime(?, meal_date)
        ),
        periods AS (
            SELECT period FROM workout
            UNION
            SELECT period FROM meal
        )
        SELECT
            p.period,
            COALESCE(w.workout_days, 0) AS workout_days,
            COALESCE(w.set_count, 0) AS set_count,
            COALESCE(w.rep_count, 0) AS rep_count,
            COALESCE(w.volume, 0) AS volume,
            COALESCE(m.meal_days, 0) AS meal_days,
            COALESCE(m.meal_count, 0) AS meal_count,
            COALESCE(m.amount, 0) AS amount,
            COALESCE(m.grams, 0) AS grams,
            COALESCE(m.calories, 0) AS calories
        FROM periods p
        LEFT JOIN workout w ON w.period = p.period
        LEFT JOIN meal m ON m.period = p.period
        ORDER BY p.period DESC
        LIMIT ?
        """,
        (period_format, period_format, period_format, period_format, limit),
    ).fetchall()


def build_period_chart(rows: list[sqlite3.Row]) -> list[dict[str, float | int | str]]:
    ordered_rows = list(reversed(rows))
    max_volume = max([float(row["volume"]) for row in ordered_rows] + [1.0])
    max_grams = max([float(row["grams"]) for row in ordered_rows] + [1.0])
    max_sets = max([int(row["set_count"]) for row in ordered_rows] + [1])
    return [
        {
            "period": row["period"],
            "volume": float(row["volume"]),
            "grams": float(row["grams"]),
            "set_count": int(row["set_count"]),
            "workout_days": int(row["workout_days"]),
            "meal_count": int(row["meal_count"]),
            "volume_height": max(3, round(float(row["volume"]) / max_volume * 100)),
            "grams_height": max(3, round(float(row["grams"]) / max_grams * 100)),
            "set_height": max(3, round(int(row["set_count"]) / max_sets * 100)),
        }
        for row in ordered_rows
    ]


def build_daily_chart(rows: list[sqlite3.Row]) -> list[dict[str, float | int | str]]:
    ordered_rows = list(reversed(rows))
    max_volume = max([float(row["volume"]) for row in ordered_rows] + [1.0])
    max_grams = max([float(row["grams"]) for row in ordered_rows] + [1.0])
    max_sets = max([int(row["set_count"]) for row in ordered_rows] + [1])
    return [
        {
            "period": row["period"],
            "volume": float(row["volume"]),
            "grams": float(row["grams"]),
            "set_count": int(row["set_count"]),
            "workout_days": 1 if int(row["set_count"]) > 0 else 0,
            "meal_count": int(row["meal_count"]),
            "volume_height": max(3, round(float(row["volume"]) / max_volume * 100)),
            "grams_height": max(3, round(float(row["grams"]) / max_grams * 100)),
            "set_height": max(3, round(int(row["set_count"]) / max_sets * 100)),
        }
        for row in ordered_rows
    ]


def list_exercise_summary(limit: int = 20) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT
            e.name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        GROUP BY e.id, e.name, body_part
        ORDER BY set_count DESC, rep_count DESC, e.name
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def list_body_part_summary(scope: str, limit: int = 30) -> list[sqlite3.Row]:
    if scope == "daily":
        period_expr = "s.workout_date"
    elif scope == "weekly":
        period_expr = (
            "CAST(strftime('%m', s.workout_date) AS INTEGER) || '월 ' || "
            "(((CAST(strftime('%d', s.workout_date) AS INTEGER) - 1) / 7) + 1) || '주차'"
        )
    else:
        period_expr = "strftime('%Y-%m', s.workout_date)"

    return get_db().execute(
        f"""
        SELECT
            {period_expr} AS period,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        GROUP BY period, body_part
        ORDER BY MAX(s.workout_date) DESC, volume DESC, body_part
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def list_weekly_body_part_details() -> dict[str, list[sqlite3.Row]]:
    period_expr = (
        "CAST(strftime('%m', s.workout_date) AS INTEGER) || '월 ' || "
        "(((CAST(strftime('%d', s.workout_date) AS INTEGER) - 1) / 7) + 1) || '주차'"
    )
    rows = get_db().execute(
        f"""
        SELECT
            {period_expr} AS period,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.name AS exercise_name,
            ws.weight AS weight,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        GROUP BY period, body_part, e.name, ws.weight
        ORDER BY MAX(s.workout_date) DESC, body_part, e.name, ws.weight
        """,
    ).fetchall()

    details: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        details.setdefault(f"{row['period']}::{row['body_part']}", []).append(row)
    return details


def list_sets_for_session(session_id: int) -> list[sqlite3.Row]:
    return get_db().execute(
        """
        SELECT ws.*, e.name AS exercise_name
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        WHERE ws.session_id = ?
        ORDER BY ws.sort_order, ws.id
        """,
        (session_id,),
    ).fetchall()


def sets_for_session(session_id: int) -> list[sqlite3.Row]:
    return list_sets_for_session(session_id)


def grouped_sets_for_session(session_id: int | None) -> list[dict[str, object]]:
    if session_id is None:
        return []

    groups: list[dict[str, object]] = []
    group_by_name: dict[str, dict[str, object]] = {}
    for item in list_sets_for_session(int(session_id)):
        body_part = item["body_part"] or "기타"
        exercise_name = item["exercise_name"]
        group_key = f"{body_part}:{exercise_name}"
        if group_key not in group_by_name:
            group = {"body_part": body_part, "exercise_name": exercise_name, "sets": []}
            group_by_name[group_key] = group
            groups.append(group)
        group_by_name[group_key]["sets"].append(item)
    return groups


def current_local_date() -> str:
    return get_db().execute("SELECT date('now', 'localtime')").fetchone()[0]


def value_at(values: list[str], index: int) -> str:
    if index >= len(values):
        return ""
    return values[index] or ""


def parse_float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    return float(value)


def parse_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    return int(value)


app = create_app()
app.jinja_env.globals["sets_for_session"] = sets_for_session
app.jinja_env.globals["grouped_sets_for_session"] = grouped_sets_for_session


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5000, type=int)
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=True)
