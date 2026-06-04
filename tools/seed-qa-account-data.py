from __future__ import annotations

import argparse
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import session

from health_tracker.app import app, get_db, init_db
from health_tracker.config import DATABASE
from health_tracker.security import make_password_hash
from health_tracker.services.accounts import connect_auth_db, init_accounts_db
from health_tracker.services.dummy_data import generate_year_qa_dummy_data


def ensure_user_account(username: str, password: str) -> int:
    init_accounts_db(DATABASE)
    with closing(connect_auth_db(DATABASE)) as db:
        db.row_factory = sqlite3.Row
        with db:
            row = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if row:
                account_id = int(row["id"])
                db.execute(
                    """
                    UPDATE users
                    SET password_hash = ?,
                        role = 'user',
                        is_active = 1,
                        signup_status = 'active',
                        display_name = COALESCE(NULLIF(display_name, ''), ?),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (make_password_hash(password), username, account_id),
                )
                return account_id

            cursor = db.execute(
                """
                INSERT INTO users (
                    username, display_name, password_hash, role, is_active,
                    signup_status, memo, updated_at
                )
                VALUES (?, ?, ?, 'user', 1, 'active', 'QA 자동검수 계정', CURRENT_TIMESTAMP)
                """,
                (username, username, make_password_hash(password)),
            )
            return int(cursor.lastrowid)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed QA dummy data for the QA login account.")
    parser.add_argument("--username", default="test")
    parser.add_argument("--password", default="1234")
    args = parser.parse_args()

    account_id = ensure_user_account(args.username, args.password)

    with app.test_request_context("/"):
        session["account_id"] = account_id
        session["login_mode"] = "user"
        init_db()
        db = get_db()
        status = generate_year_qa_dummy_data(db)

    print(f"QA account: {args.username} / {args.password}")
    print(f"Account id: {account_id}")
    print(f"Range: {status['range']}")
    print(f"Exercises: {status['exercises']}")
    print(f"Sets: {status['sets']}")
    print(f"Meals: {status['meals']}")
    print(f"PRs: {status['prs']}")
    print(f"Body metrics: {status['body_metrics']}")
    print(f"Recovery: {status['recovery']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
