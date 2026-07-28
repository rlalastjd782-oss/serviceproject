from __future__ import annotations

import io

from tests.flow_base import FlowTestBase


class BodyPhotoSecurityTest(FlowTestBase):
    """Regression: progress photos used to be saved under static/progress_photos/
    which Flask serves to anyone with no login required, and every account
    shared the same folder with guessable date-based filenames. Photos must
    now be served only through an authenticated route scoped to the current
    account's own folder."""

    def _upload_photo(self) -> str:
        response = self.client.post(
            "/body-photos",
            data={
                "photo_date": "2026-06-01",
                "photo": (io.BytesIO(b"fake-image-bytes"), "test.jpg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        html = self.client.get("/app?date=2026-06-01").data.decode("utf-8")
        return html

    def test_uploaded_photo_uses_authenticated_route_not_static(self) -> None:
        html = self._upload_photo()
        self.assertNotIn("/static/progress_photos/", html)
        self.assertIn("/body/photos/file/", html)

    def test_photo_file_is_served_while_logged_in(self) -> None:
        html = self._upload_photo()
        start = html.index("/body/photos/file/")
        end = html.index('"', start)
        photo_url = html[start:end]
        response = self.client.get(photo_url)
        self.assertEqual(response.status_code, 200)

    def test_photo_file_requires_login(self) -> None:
        html = self._upload_photo()
        start = html.index("/body/photos/file/")
        end = html.index('"', start)
        photo_url = html[start:end]

        self.client.post("/logout")
        response = self.client.get(photo_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])
