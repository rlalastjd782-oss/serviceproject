from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
import re

from health_tracker.security import make_password_hash, verify_password_hash

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{2,32}$")


def account_db_path(main_database: Path, account_id: int) -> Path:
    if account_id <= 1:
        return main_database
    return main_database.parent / "accounts" / f"user_{account_id}.db"


def auth_database_path(main_database: Path) -> Path:
    return main_database.parent / "accounts.db"


def connect_auth_db(main_database: Path) -> sqlite3.Connection:
    path = auth_database_path(main_database)
    path.parent.mkdir(exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


def init_accounts_db(main_database: Path) -> None:
    with closing(connect_auth_db(main_database)) as db:
        with db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL DEFAULT '',
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            columns = [row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()]
            for column, column_type in [
                ("last_login_at", "TEXT"),
                ("last_seen_at", "TEXT"),
                ("signup_status", "TEXT NOT NULL DEFAULT 'active'"),
                ("memo", "TEXT NOT NULL DEFAULT ''"),
            ]:
                if column not in columns:
                    db.execute(f"ALTER TABLE users ADD COLUMN {column} {column_type}")


def list_accounts(main_database: Path) -> list[sqlite3.Row]:
    init_accounts_db(main_database)
    with closing(connect_auth_db(main_database)) as db:
        return db.execute(
            """
            SELECT id, username, display_name, role, is_active, created_at, updated_at,
                   last_login_at, last_seen_at, signup_status, memo
            FROM users
            ORDER BY id
            """
        ).fetchall()


def get_account(main_database: Path, account_id: int | None) -> sqlite3.Row | None:
    if not account_id:
        return None
    init_accounts_db(main_database)
    with closing(connect_auth_db(main_database)) as db:
        return db.execute(
            """
            SELECT id, username, display_name, role, is_active, last_login_at, last_seen_at, memo
            FROM users
            WHERE id = ? AND is_active = 1
            """,
            (account_id,),
        ).fetchone()


def create_account(
    main_database: Path,
    username: str,
    password: str,
    display_name: str = "",
    role: str = "user",
) -> tuple[bool, str]:
    username = username.strip()
    display_name = display_name.strip() or username
    password = password.strip()
    role = role if role in {"admin", "user"} else "user"
    if not USERNAME_PATTERN.match(username) or len(password) < 4:
        return False, "invalid"
    init_accounts_db(main_database)
    try:
        with closing(connect_auth_db(main_database)) as db:
            with db:
                db.execute(
                    """
                    INSERT INTO users (
                        username, display_name, password_hash, role, is_active,
                        signup_status, memo, updated_at
                    )
                    VALUES (?, ?, ?, ?, 1, 'active', '', CURRENT_TIMESTAMP)
                    """,
                    (username, display_name, make_password_hash(password), role),
                )
    except sqlite3.IntegrityError:
        return False, "duplicate"
    return True, ""


def ensure_primary_account(main_database: Path, password_hash: str | None = None) -> None:
    init_accounts_db(main_database)
    fallback_hash = password_hash or make_password_hash("1234")
    with closing(connect_auth_db(main_database)) as db:
        with db:
            row = db.execute("SELECT id FROM users WHERE id = 1").fetchone()
            if row:
                if password_hash:
                    db.execute(
                        """
                        UPDATE users
                        SET username = COALESCE(NULLIF(username, ''), 'admin'),
                            display_name = COALESCE(NULLIF(display_name, ''), '관리자'),
                            password_hash = ?,
                            role = 'admin',
                            is_active = 1,
                            signup_status = 'active',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = 1
                        """,
                        (password_hash,),
                    )
            else:
                db.execute(
                    """
                    INSERT INTO users (id, username, display_name, password_hash, role, is_active, updated_at)
                    VALUES (1, 'admin', '관리자', ?, 'admin', 1, CURRENT_TIMESTAMP)
                    """,
                    (fallback_hash,),
                )


def verify_account(main_database: Path, username: str, password: str) -> sqlite3.Row | None:
    init_accounts_db(main_database)
    with closing(connect_auth_db(main_database)) as db:
        row = db.execute(
            "SELECT id, username, display_name, role, is_active, password_hash FROM users WHERE username = ? AND is_active = 1",
            (username.strip(),),
        ).fetchone()
    if not row or not verify_password_hash(password, row["password_hash"]):
        return None
    return row


def update_account_login(main_database: Path, account_id: int) -> None:
    init_accounts_db(main_database)
    with closing(connect_auth_db(main_database)) as db:
        with db:
            db.execute(
                """
                UPDATE users
                SET last_login_at = CURRENT_TIMESTAMP,
                    last_seen_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (account_id,),
            )


def touch_account_seen(main_database: Path, account_id: int) -> None:
    init_accounts_db(main_database)
    with closing(connect_auth_db(main_database)) as db:
        with db:
            db.execute(
                "UPDATE users SET last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
                (account_id,),
            )
