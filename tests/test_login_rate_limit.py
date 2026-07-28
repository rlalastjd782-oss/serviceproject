from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from health_tracker.services.accounts import (
    MAX_FAILED_LOGIN_ATTEMPTS,
    create_account,
    verify_account,
)

TEST_TMP_DIR = Path(__file__).resolve().parents[1] / ".test-tmp"


class LoginRateLimitTest(unittest.TestCase):
    """Regression: verify_account previously allowed unlimited login attempts
    with no lockout, so a brute-force attack could try passwords forever."""

    def setUp(self) -> None:
        TEST_TMP_DIR.mkdir(exist_ok=True)
        self.tmpdir = tempfile.TemporaryDirectory(dir=TEST_TMP_DIR)
        self.database = Path(self.tmpdir.name) / "workout.db"
        ok, error = create_account(self.database, "locktest", "correct-password")
        self.assertTrue(ok, error)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_correct_password_succeeds(self) -> None:
        account = verify_account(self.database, "locktest", "correct-password")
        self.assertIsNotNone(account)
        self.assertEqual(account["username"], "locktest")

    def test_wrong_password_fails_but_does_not_lock_before_threshold(self) -> None:
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS - 1):
            self.assertIsNone(verify_account(self.database, "locktest", "wrong-password"))
        # Still under the threshold, so the correct password should still work.
        self.assertIsNotNone(verify_account(self.database, "locktest", "correct-password"))

    def test_account_locks_out_after_max_failed_attempts(self) -> None:
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
            verify_account(self.database, "locktest", "wrong-password")
        # Even the correct password must fail now — the account is locked.
        self.assertIsNone(verify_account(self.database, "locktest", "correct-password"))

    def test_successful_login_resets_failed_count(self) -> None:
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS - 1):
            verify_account(self.database, "locktest", "wrong-password")
        self.assertIsNotNone(verify_account(self.database, "locktest", "correct-password"))
        # Counter reset, so a fresh run of failures shouldn't lock out immediately.
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS - 1):
            self.assertIsNone(verify_account(self.database, "locktest", "wrong-password"))
        self.assertIsNotNone(verify_account(self.database, "locktest", "correct-password"))


if __name__ == "__main__":
    unittest.main()
