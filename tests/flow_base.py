from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import app as app_module


TEST_TMP_DIR = Path(__file__).resolve().parents[1] / ".test-tmp"


class FlowTestBase(unittest.TestCase):
    def setUp(self) -> None:
        TEST_TMP_DIR.mkdir(exist_ok=True)
        self.tmpdir = tempfile.TemporaryDirectory(dir=TEST_TMP_DIR)
        self.original_database = app_module.DATABASE
        app_module.DATABASE = Path(self.tmpdir.name) / "test-workout.db"
        self.app = app_module.app
        self.client = self.app.test_client()
        self.raw_post = self.client.post
        self.client.post = self._post_with_csrf
        self.client.get("/auth/login?mode=user")
        response = self.client.post(
            "/signup",
            data={"username": "tester", "password": "1234", "password_confirm": "1234"},
        )
        self.assertEqual(response.status_code, 302)

    def tearDown(self) -> None:
        app_module.DATABASE = self.original_database
        self.tmpdir.cleanup()

    def _csrf_token(self, client=None) -> str:
        target_client = client or self.client
        with target_client.session_transaction() as sess:
            return str(sess.get("csrf_token", ""))

    def _post_with_csrf(self, *args, **kwargs):
        headers = dict(kwargs.pop("headers", {}) or {})
        token = self._csrf_token(self.client)
        if kwargs.get("json") is not None:
            headers["X-CSRF-Token"] = token
            kwargs["headers"] = headers
            return self.raw_post(*args, **kwargs)
        data = kwargs.pop("data", None)
        if data is None:
            data = {}
        if isinstance(data, dict):
            data = {**data, "csrf_token": token}
        kwargs["data"] = data
        kwargs["headers"] = headers
        return self.raw_post(*args, **kwargs)

    def _visitor_post(self, client, path: str, data: dict[str, object] | None = None):
        payload = dict(data or {})
        payload["csrf_token"] = self._csrf_token(client)
        return client.post(path, data=payload)
