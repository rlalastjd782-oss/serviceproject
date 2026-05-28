from __future__ import annotations

import re
from pathlib import Path

import app as app_module

from tests.flow_base import FlowTestBase


class YearlyStaticFlowTest(FlowTestBase):
    def test_yearly_qa_dummy_data_crosses_year_boundary(self) -> None:
        response = self.client.post("/qa-dummy/year")
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            status = app_module.get_qa_dummy_status()
            self.assertTrue(status["exists"])
            self.assertGreaterEqual(status["exercises"], 100)
            self.assertGreaterEqual(status["sets"], 3000)
            self.assertGreaterEqual(status["meals"], 1400)
            self.assertGreaterEqual(status["body_metrics"], 50)
            self.assertGreaterEqual(status["recovery"], 360)

        for path in [
            "/summaries/yearly?year=2025",
            "/summaries/yearly?year=2026",
            "/summaries/yearly/compare?base_year=2025&compare_year=2026",
            "/summaries/monthly?month=2025-12",
            "/summaries/monthly?month=2026-01",
            "/records/search?start=2025-12-31&end=2026-01-01&q=QA-",
        ]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn("QA-", response.data.decode("utf-8", errors="ignore"))

        response = self.client.get("/export/yearly.json?year=2026")
        self.assertEqual(response.status_code, 200)
        self.assertIn('"year": "2026"', response.data.decode("utf-8"))
        response = self.client.get("/export/yearly-workouts.csv?year=2026")
        self.assertEqual(response.status_code, 200)
        self.assertIn("QA-", response.data.decode("utf-8-sig"))

    def test_service_worker_precache_assets_are_valid(self) -> None:
        sw_path = Path(__file__).resolve().parents[1] / "static" / "sw.js"
        sw_source = sw_path.read_text(encoding="utf-8")
        assets_match = re.search(r"const ASSETS = \[(.*?)\];", sw_source, re.S)
        self.assertIsNotNone(assets_match)
        assets = re.findall(r'"([^"]+)"', assets_match.group(1))
        self.assertNotIn("/app", assets)
        self.assertNotIn("/app?mode=workout", assets)
        self.assertNotIn("/app?mode=meal", assets)
        self.assertNotIn("/calendar", assets)
        self.assertNotIn("/meals/weekly", assets)
        self.assertNotIn("/summaries/exercises", assets)
        self.assertNotIn("/summaries/yearly", assets)
        self.assertIn("/static/css/ui_rebuild.css", assets)
        self.assertIn("/sw.js", assets)
        self.assertIn("/favicon.ico", assets)
        self.assertIn("self.skipWaiting()", sw_source)
        self.assertIn("self.clients.claim()", sw_source)
        self.assertIn("offlineFallback", sw_source)

        for asset in assets:
            with self.subTest(asset=asset):
                response = self.client.get(asset)
                self.assertEqual(response.status_code, 200)
                response.close()

        response = self.client.get("/sw.js")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-DB-Query-Count"), "0")
        self.assertEqual(response.headers.get("Service-Worker-Allowed"), "/")
        expected_version = Path("VERSION").read_text(encoding="utf-8").strip()
        self.assertIn(f"workout-pwa-v{expected_version}", response.data.decode("utf-8"))

        public_client = self.app.test_client()
        response = public_client.get("/favicon.ico")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-DB-Query-Count"), "0")
        self.assertIn("image/svg+xml", response.headers.get("Content-Type", ""))
        self.assertIn("<svg", response.data.decode("utf-8"))

        response = public_client.get("/static/css/styles.css")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-DB-Query-Count"), "0")
        response.close()
