from __future__ import annotations

import sqlite3
from pathlib import Path

import app as app_module


from tests.flow_base import FlowTestBase


class AccountAdminFlowTest(FlowTestBase):
    def test_locations_manage_equipment_and_filter_records(self) -> None:
        self.client.post(
            "/locations",
            data={"name": "DELETE-LOCATION", "address": "", "memo": ""},
        )
        db = sqlite3.connect(app_module.DATABASE)
        try:
            delete_location_id = db.execute(
                "SELECT id FROM workout_locations WHERE name = ?",
                ("DELETE-LOCATION",),
            ).fetchone()[0]
        finally:
            db.close()
        self.client.post(f"/locations/{delete_location_id}/remove")
        db = sqlite3.connect(app_module.DATABASE)
        try:
            deleted_location = db.execute(
                "SELECT id FROM workout_locations WHERE id = ?",
                (delete_location_id,),
            ).fetchone()
        finally:
            db.close()
        self.assertIsNone(deleted_location)

        response = self.client.post(
            "/locations",
            data={
                "name": "테스트 헬스장",
                "address": "강남",
                "memo": "스미스 머신 있음",
                "is_default": "1",
            },
        )
        self.assertEqual(response.status_code, 302)

        db = sqlite3.connect(app_module.DATABASE)
        try:
            db.row_factory = sqlite3.Row
            location = db.execute("SELECT * FROM workout_locations WHERE name = ?", ("테스트 헬스장",)).fetchone()
        finally:
            db.close()
        self.assertIsNotNone(location)
        location_id = int(location["id"])

        self.client.post(
            f"/locations/{location_id}/equipment",
            data={"equipment_name": "스미스 머신", "equipment_type": "플레이트로디드머신", "memo": "하체 가능"},
        )
        workout_html = self.client.get(f"/app?mode=workout&location_id={location_id}").data.decode("utf-8")
        self.assertIn("운동 장소", workout_html)
        self.assertIn('<option value="핀머신">핀머신</option>', workout_html)
        self.assertIn('<option value="플레이트로디드머신">플레이트로디드머신</option>', workout_html)
        self.assertIn('<option value="프리웨이트">프리웨이트</option>', workout_html)
        self.assertIn('<option value="덤벨">덤벨</option>', workout_html)
        self.assertIn('<option value="케이블">케이블</option>', workout_html)
        self.assertNotIn('<option value="스미스 머신">스미스 머신</option>', workout_html)

        self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-26",
                "mode": "workout",
                "location_id": str(location_id),
                "body_part": "하체",
                "exercise_name": "장소 테스트 스쿼트",
                "equipment": "스미스 머신",
                "set_weight": ["60"],
                "set_reps": ["8"],
                "set_type": ["본세트"],
            },
        )
        other_location_response = self.client.post(
            "/locations",
            data={"name": "다른장소", "address": "", "memo": ""},
        )
        self.assertEqual(other_location_response.status_code, 302)
        with self.app.app_context():
            other_location = app_module.get_db().execute(
                "SELECT id FROM workout_locations WHERE name = ?",
                ("다른장소",),
            ).fetchone()
            other_location_id = int(other_location["id"])
        self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-27",
                "mode": "workout",
                "location_id": str(other_location_id),
                "body_part": "가슴",
                "exercise_name": "다른장소 전용운동",
                "equipment": "덤벨",
                "set_weight": ["20"],
                "set_reps": ["10"],
                "set_type": ["본세트"],
            },
        )
        scoped_workout_html = self.client.get(f"/app?date=2026-05-26&mode=workout&location_id={location_id}").data.decode("utf-8")
        self.assertIn("장소 테스트 스쿼트", scoped_workout_html)
        self.assertNotIn('<option value="다른장소 전용운동">', scoped_workout_html)
        self.assertNotIn('data-exercise-name="다른장소 전용운동"', scoped_workout_html)

        search_html = self.client.get(
            "/records/search",
            query_string={
                "q": "장소 테스트",
                "location_id": str(location_id),
                "start": "2026-05-26",
                "end": "2026-05-26",
            },
        ).data.decode("utf-8")
        self.assertIn("테스트 헬스장", search_html)
        self.assertIn("플레이트로디드머신", search_html)

    def test_visitor_is_read_only_and_admin_routes_are_locked(self) -> None:
        visitor = self.app.test_client()
        response = visitor.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers.get("Location", ""))

        response = visitor.get("/app?mode=workout")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers.get("Location", ""))
        self.assertIn("next=", response.headers.get("Location", ""))

        visitor.get("/app")
        response = self._visitor_post(
            visitor,
            "/sets",
            {
                "workout_date": "2026-05-20",
                "body_part": "가슴",
                "exercise_name": "__TEST__ blocked",
                "set_weight": ["80"],
                "set_reps": ["10"],
            },
        )
        self.assertEqual(response.status_code, 403)

        response = visitor.get("/export.json")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers.get("Location", ""))

        response = self.raw_post(
            "/sets",
            data={
                "workout_date": "2026-05-20",
                "body_part": "가슴",
                "exercise_name": "__TEST__ csrf",
                "set_weight": ["80"],
                "set_reps": ["10"],
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_settings_password_lock_unlock_and_reset(self) -> None:
        response = self.client.get("/settings")
        self.assertEqual(response.status_code, 200)
        settings_html = response.data.decode("utf-8")
        self.assertIn("비밀번호 변경", settings_html)
        self.assertNotIn("settings-overview-section", settings_html)
        self.assertNotIn("데이터 관리", settings_html)
        self.client.post("/logout")
        response = self.client.get("/settings")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers.get("Location", ""))
        self.client.get("/auth/login?mode=admin")
        response = self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        self.assertIn("/admin", response.headers.get("Location", ""))
        response = self.client.get("/settings")
        self.assertIn("/admin", response.headers.get("Location", ""))

    def test_two_accounts_use_separate_data_stores(self) -> None:
        response = self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-26",
                "mode": "workout",
                "body_part": "가슴",
                "exercise_name": "__TEST__ ADMIN ONLY",
                "equipment": "덤벨",
                "set_weight": ["30"],
                "set_reps": ["10"],
                "set_type": ["본세트"],
            },
        )
        self.assertEqual(response.status_code, 302)

        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        response = self.client.post(
            "/settings/accounts",
            data={
                "username": "partner",
                "display_name": "파트너",
                "password": "5678",
                "role": "user",
            },
        )
        self.assertEqual(response.status_code, 302)
        admin_html = self.client.get("/admin").data.decode("utf-8")
        self.assertIn("partner", admin_html)

        response = self.client.post("/logout")
        self.assertEqual(response.status_code, 302)
        self.client.get("/auth/login")
        response = self.client.post("/auth/login", data={"username": "partner", "password": "5678"})
        self.assertEqual(response.status_code, 302)

        partner_html = self.client.get("/app?mode=workout").data.decode("utf-8")
        self.assertIn("파트너", partner_html)
        self.assertNotIn("__TEST__ ADMIN ONLY", partner_html)

        response = self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-26",
                "mode": "workout",
                "body_part": "등",
                "exercise_name": "__TEST__ PARTNER ONLY",
                "equipment": "케이블",
                "set_weight": ["25"],
                "set_reps": ["12"],
                "set_type": ["본세트"],
            },
        )
        self.assertEqual(response.status_code, 302)
        partner_html = self.client.get("/app?date=2026-05-26&mode=workout").data.decode("utf-8")
        self.assertIn("__TEST__ PARTNER ONLY", partner_html)
        self.assertNotIn("__TEST__ ADMIN ONLY", partner_html)

        self.client.post("/logout")
        self.client.get("/auth/login")
        response = self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        self.assertEqual(response.status_code, 302)
        response = self.client.get("/app?date=2026-05-26&mode=workout")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin", response.headers.get("Location", ""))
        self.assertTrue((Path(self.tmpdir.name) / "accounts.db").exists())
        self.assertTrue((Path(self.tmpdir.name) / "accounts" / "user_3.db").exists())

    def test_login_tabs_signup_and_role_boundaries(self) -> None:
        self.client.post("/logout")
        html = self.client.get("/auth/login?mode=admin").data.decode("utf-8")
        self.assertIn("관리자 로그인", html)
        self.assertIn('name="csrf_token"', html)
        self.assertNotIn("<strong>회원가입</strong>", html)
        self.assertNotIn("href=\"/auth/signup", html)
        self.assertIn("서버 관리자에게 문의", html)
        html = self.client.get("/auth/login?mode=user").data.decode("utf-8")
        self.assertIn("사용자 로그인", html)
        self.assertIn("회원가입", html)
        self.assertIn("관리자에게 초기화", html)
        self.assertNotIn("사용자 회원가입</strong>", html)
        self.assertIn("미리보기", html)

        signup_html = self.client.get("/auth/signup").data.decode("utf-8")
        self.assertIn("사용자 회원가입", signup_html)
        self.assertIn("로그인으로 돌아가기", signup_html)
        self.assertIn("미리보기 보기", signup_html)

        response = self.client.post("/auth/signup", data={"username": "member_1", "password": "abcd", "password_confirm": "abcd"})
        self.assertEqual(response.status_code, 302)
        html = self.client.get("/app?mode=workout").data.decode("utf-8")
        self.assertIn("member_1", html)

        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "admin", "username": "member_1", "password": "abcd"},
        )
        self.assertIn("not_admin", response.headers.get("Location", ""))

        self.client.get("/auth/login?mode=user")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "user", "username": "admin", "password": "1234"},
        )
        self.assertIn("not_user", response.headers.get("Location", ""))

        self.client.get("/auth/login?mode=admin")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "admin", "username": "admin", "password": "1234"},
        )
        self.assertIn("/admin", response.headers.get("Location", ""))
        response = self.client.get("/app")
        self.assertIn("/admin", response.headers.get("Location", ""))

    def test_login_allows_stale_public_csrf_after_server_restart(self) -> None:
        self.client.get("/auth/login?mode=user")
        raw_response = self.raw_post(
            "/auth/login",
            data={
                "login_mode": "user",
                "username": "tester",
                "password": "1234",
                "csrf_token": "stale-token-from-before-restart",
            },
        )
        self.assertEqual(raw_response.status_code, 302)
        self.assertIn("/app", raw_response.headers.get("Location", ""))

    def test_account_seen_touch_is_throttled(self) -> None:
        self.client.get("/app")
        with self.client.session_transaction() as sess:
            first_touch = sess.get("last_seen_touch_at")
        self.assertIsNotNone(first_touch)

        self.client.get("/summaries/daily")
        with self.client.session_transaction() as sess:
            second_touch = sess.get("last_seen_touch_at")
        self.assertEqual(first_touch, second_touch)

    def test_qa_report_includes_performance_snapshot_and_analyze(self) -> None:
        html = self.client.get("/qa/report").data.decode("utf-8")
        self.assertIn("성능 진단", html)
        self.assertIn("핵심 인덱스", html)
        self.assertIn("recent_workout_sets", html)
        self.assertIn("/app?mode=workout", html)
        self.assertIn("HTTP", html)
        self.assertIn("배포 점검", html)
        self.assertIn("/static/css/styles.css", html)
        self.assertIn("소스 길이 점검", html)

        response = self.client.post("/qa/analyze", data={})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/qa/report", response.headers.get("Location", ""))

    def test_auth_preview_is_public_sample_only(self) -> None:
        self.client.post("/logout")
        response = self.client.get("/auth/preview")
        self.assertRegex(response.headers.get("X-Request-Duration-ms", ""), r"^\d+\.\d$")
        self.assertRegex(response.headers.get("X-DB-Query-Count", ""), r"^\d+$")
        self.assertIn("app;dur=", response.headers.get("Server-Timing", ""))
        html = response.data.decode("utf-8")
        self.assertIn("가입 전 미리보기", html)
        self.assertIn("운동 기록, 분석, 장소 관리를", html)
        self.assertIn("/auth/login", html)
        self.assertIn("/auth/signup", html)
        self.assertIn("랫풀다운", html)
        self.assertIn("아파트 헬스장", html)
        self.assertNotIn("<form", html)
        self.assertNotIn("__TEST__", html)
        self.assertNotIn("사용자 현황", html)

    def test_admin_can_change_own_password_and_settings_password_hash(self) -> None:
        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})

        dashboard_html = self.client.get("/admin").data.decode("utf-8")
        self.assertIn("관리자 비밀번호 변경", dashboard_html)

        response = self.client.post(
            "/admin/password",
            data={
                "current_password": "wrong",
                "new_password": "9999",
                "new_password_confirm": "9999",
            },
        )
        self.assertIn("error=password", response.headers.get("Location", ""))

        response = self.client.post(
            "/admin/password",
            data={
                "current_password": "1234",
                "new_password": "9999",
                "new_password_confirm": "9999",
            },
        )
        self.assertIn("updated=password", response.headers.get("Location", ""))

        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        response = self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        self.assertIn("invalid", response.headers.get("Location", ""))

        self.client.get("/auth/login?mode=admin")
        response = self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "9999"})
        self.assertIn("/admin", response.headers.get("Location", ""))
        with self.app.app_context():
            self.assertTrue(app_module.verify_settings_password("9999"))

    def test_admin_dashboard_reports_user_usage_and_blocks_users(self) -> None:
        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        self.client.post(
            "/settings/accounts",
            data={"username": "reportuser", "display_name": "리포트사용자", "password": "5678", "role": "user"},
        )
        self.client.post("/logout")
        self.client.get("/auth/login")
        self.client.post("/auth/login", data={"login_mode": "user", "username": "reportuser", "password": "5678"})
        response = self.client.post(
            "/sets",
            data={
                "workout_date": "2026-05-26",
                "mode": "workout",
                "body_part": "등",
                "exercise_name": "__TEST__ USER REPORT",
                "equipment": "케이블",
                "set_weight": ["25"],
                "set_reps": ["12"],
                "set_type": ["본세트"],
            },
        )
        self.assertEqual(response.status_code, 302)
        user_html = self.client.get("/app?mode=workout").data.decode("utf-8")
        self.assertIn("admin-mode", user_html)
        self.assertIn("header-meta", user_html)
        self.assertIn("account-greeting", user_html)
        self.assertIn("app-version", user_html)
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 302)
        self.assertIn("mode=admin", response.headers.get("Location", ""))

        self.client.post("/logout")
        self.client.get("/auth/login")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        admin_html = self.client.get("/admin").data.decode("utf-8")
        self.assertIn("관리자 대시보드", admin_html)
        self.assertIn("사용자 계정", admin_html)
        self.assertIn("운영 체크포인트", admin_html)
        self.assertIn("사용자 활성", admin_html)
        self.assertIn("조치 필요", admin_html)
        self.assertIn("데이터 규모", admin_html)
        self.assertNotRegex(admin_html, r"\?{3,}")
        self.assertIn("사용자 검색", admin_html)
        self.assertIn("조치 필요 사용자", admin_html)
        self.assertIn("관리자 활동 로그", admin_html)
        self.assertNotIn("admin · admin", admin_html)
        self.assertIn("리포트사용자", admin_html)
        self.assertIn("세트 1개", admin_html)
        filtered_html = self.client.get("/admin?q=reportuser&status=active&sort=sets").data.decode("utf-8")
        self.assertIn("reportuser", filtered_html)
        response = self.client.get("/admin/users/1")
        self.assertEqual(response.status_code, 302)
        self.assertIn("user_only", response.headers.get("Location", ""))
        detail_html = self.client.get("/admin/users/3").data.decode("utf-8")
        self.assertIn("__TEST__ USER REPORT", detail_html)
        self.assertIn("케이블", detail_html)
        self.assertIn("데이터 내보내기", detail_html)
        export_response = self.client.get("/admin/users/3/export")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("application/json", export_response.content_type)
        self.assertIn("__TEST__ USER REPORT", export_response.data.decode("utf-8"))

    def test_admin_can_manage_user_account_status_password_and_memo(self) -> None:
        self.client.post("/logout")
        self.client.get("/auth/login?mode=admin")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        self.client.post(
            "/settings/accounts",
            data={"username": "managed", "display_name": "관리대상", "password": "1111", "role": "user"},
        )
        detail_html = self.client.get("/admin/users/3").data.decode("utf-8")
        self.assertIn("계정 운영", detail_html)

        response = self.client.post(
            "/admin/users/3/memo",
            data={"display_name": "관리대상수정", "memo": "테스트 메모"},
        )
        self.assertEqual(response.status_code, 302)
        detail_html = self.client.get("/admin/users/3").data.decode("utf-8")
        self.assertIn("관리대상수정", detail_html)
        self.assertIn("테스트 메모", detail_html)
        self.assertIn("user_memo_update", detail_html)

        response = self.client.post("/admin/users/3/password", data={"password": "2222"})
        self.assertEqual(response.status_code, 302)
        self.client.post("/logout")
        self.client.get("/auth/login")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "user", "username": "managed", "password": "2222"},
        )
        self.assertEqual(response.status_code, 302)

        self.client.post("/logout")
        self.client.get("/auth/login")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        response = self.client.post(
            "/admin/users/3/status",
            data={"action": "disable", "confirm_status": "비활성화"},
        )
        self.assertEqual(response.status_code, 302)
        self.client.post("/logout")
        self.client.get("/auth/login")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "user", "username": "managed", "password": "2222"},
        )
        self.assertIn("invalid", response.headers.get("Location", ""))

        self.client.get("/auth/login")
        self.client.post("/auth/login", data={"login_mode": "admin", "username": "admin", "password": "1234"})
        response = self.client.post("/admin/users/3/status", data={"action": "enable"})
        self.assertEqual(response.status_code, 302)
        self.client.post("/logout")
        self.client.get("/auth/login")
        response = self.client.post(
            "/auth/login",
            data={"login_mode": "user", "username": "managed", "password": "2222"},
        )
        self.assertEqual(response.status_code, 302)
