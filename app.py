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
        today_session = get_or_create_session()
        sessions = list_recent_sessions()
        exercises = list_exercises()
        return render_template(
            "index.html",
            session=today_session,
            sessions=sessions,
            exercises=exercises,
        )

    @app.post("/sets")
    def create_set():
        session = get_or_create_session(request.form.get("workout_date"))
        exercise_name = request.form.get("exercise_name", "").strip()
        if not exercise_name:
            return redirect(url_for("index"))

        exercise_id = get_or_create_exercise(exercise_name)
        weight = parse_float(request.form.get("weight"))
        reps = parse_int(request.form.get("reps"))
        memo = request.form.get("memo", "").strip()

        db = get_db()
        next_order = db.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workout_sets WHERE session_id = ?",
            (session["id"],),
        ).fetchone()[0]
        db.execute(
            """
            INSERT INTO workout_sets (session_id, exercise_id, weight, reps, memo, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session["id"], exercise_id, weight, reps, memo, next_order),
        )
        db.commit()
        return redirect(url_for("index"))

    @app.post("/sets/<int:set_id>/delete")
    def delete_set(set_id: int):
        db = get_db()
        db.execute("DELETE FROM workout_sets WHERE id = ?", (set_id,))
        db.commit()
        return redirect(url_for("index"))

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
            weight REAL,
            reps INTEGER,
            memo TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES workout_sessions (id) ON DELETE CASCADE,
            FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE CASCADE
        );
        """
    )
    db.commit()


def get_or_create_session(workout_date: str | None = None) -> sqlite3.Row:
    db = get_db()
    date_value = workout_date or db.execute("SELECT date('now', 'localtime')").fetchone()[0]
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5000, type=int)
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=True)
