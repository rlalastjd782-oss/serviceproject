from __future__ import annotations

import argparse
import html
import http.cookiejar
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path


BASE_URL = "http://127.0.0.1:5000"
VIEWPORT = "430,932"


USER_PAGES = [
    ("01_login_user", "/auth/login?mode=user"),
    ("02_preview", "/auth/preview"),
    ("03_today_overview", "/app"),
    ("04_today_workout", "/app?mode=workout"),
    ("05_today_meal", "/app?mode=meal"),
    ("06_records_daily", "/summaries/daily"),
    ("07_records_search", "/records/search"),
    ("08_analysis_weekly", "/summaries/weekly"),
    ("09_analysis_monthly", "/summaries/monthly"),
    ("10_analysis_yearly", "/summaries/yearly"),
    ("11_analysis_exercises", "/summaries/exercises"),
    ("12_analysis_pr", "/summaries/pr"),
    ("13_analysis_equipment", "/summaries/equipment"),
    ("14_meals_weekly", "/meals/weekly"),
    ("15_meals_monthly", "/meals/monthly"),
    ("16_more", "/more"),
    ("17_locations", "/locations"),
    ("18_action_insights", "/insights/actions"),
    ("19_record_check", "/records/check"),
    ("20_calendar", "/calendar"),
    ("21_plate_calculator", "/tools/plate-calculator"),
    ("22_data_center", "/data/center"),
    ("23_meal_templates", "/meals/templates"),
    ("24_settings", "/settings"),
]

ADMIN_PAGES = [
    ("25_login_admin", "/auth/login?mode=admin"),
    ("26_admin_dashboard", "/admin"),
]


def request_text(opener: urllib.request.OpenerDirector, path: str, data: dict[str, str] | None = None) -> str:
    url = urllib.parse.urljoin(BASE_URL, path)
    encoded = None
    headers = {"User-Agent": "ui-capture/1.0"}
    if data is not None:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=encoded, headers=headers)
    with opener.open(req, timeout=12) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_csrf(page: str) -> str:
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', page)
    if match:
        return html.unescape(match.group(1))
    match = re.search(r'name="csrf-token"\s+content="([^"]+)"', page)
    return html.unescape(match.group(1)) if match else ""


def login(username: str, password: str, mode: str) -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    login_page = request_text(opener, f"/auth/login?mode={mode}")
    request_text(
        opener,
        "/auth/login",
        {
            "csrf_token": extract_csrf(login_page),
            "login_mode": mode,
            "username": username,
            "password": password,
        },
    )
    return opener


def localize_html(source: str, title: str) -> str:
    source = source.replace("<head>", f'<head><base href="{BASE_URL}/">', 1)
    source = source.replace("</body>", f"<script>document.title={title!r};</script></body>", 1)
    return source


def run_chrome(chrome_path: Path, args: list[str]) -> None:
    command = [
        str(chrome_path),
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--hide-scrollbars",
        "--allow-file-access-from-files",
        f"--user-data-dir={(Path.cwd() / 'artifacts' / '.chrome-capture-profile').resolve()}",
        f"--window-size={VIEWPORT}",
        *args,
    ]
    subprocess.run(command, check=True)


def capture_page(chrome_path: Path, html_file: Path, image_file: Path) -> None:
    run_chrome(chrome_path, [f"--screenshot={image_file.resolve()}", html_file.resolve().as_uri()])


def build_gallery(output_dir: Path, captures: list[tuple[str, str, Path]]) -> Path:
    image_blocks = []
    for title, path, image_file in captures:
        image_blocks.append(
            f"""
            <section class="page">
              <h2>{html.escape(title)} <small>{html.escape(path)}</small></h2>
              <img src="{image_file.name}" alt="{html.escape(title)}">
            </section>
            """
        )
    gallery = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>Fitness Tracker UI Screenshots</title>
  <style>
    @page {{ size: A4 portrait; margin: 10mm; }}
    body {{ margin: 0; font-family: Arial, sans-serif; color: #1f2933; background: #e5e7eb; }}
    .page {{ break-after: page; padding: 10px; }}
    h1, h2 {{ margin: 0 0 10px; }}
    h1 {{ font-size: 20px; }}
    h2 {{ font-size: 14px; display: grid; gap: 3px; }}
    small {{ color: #52616e; font-size: 10px; }}
    img {{ width: 100%; border-radius: 10px; box-shadow: 0 4px 14px rgb(0 0 0 / 16%); background: white; }}
  </style>
</head>
<body>
  <section class="page">
    <h1>Fitness Tracker UI Screenshots</h1>
    <p>Viewport: {VIEWPORT}. Generated from local server {BASE_URL}.</p>
  </section>
  {''.join(image_blocks)}
</body>
</html>"""
    gallery_file = output_dir / "ui_screenshots_gallery.html"
    gallery_file.write_text(gallery, encoding="utf-8")
    return gallery_file


def main() -> None:
    if os.environ.get("ALLOW_PNG_CAPTURE") != "1":
        raise SystemExit(
            "PNG screenshot capture is disabled for this project. "
            "Use DOM/HTML/CSS checks instead. Set ALLOW_PNG_CAPTURE=1 only for a manual one-off run."
        )

    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", required=True)
    parser.add_argument("--output", default="qa/screenshots/latest")
    args = parser.parse_args()

    chrome_path = Path(args.chrome)
    output_dir = Path(args.output)
    html_dir = output_dir / "html"
    png_dir = output_dir / "png"
    html_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)

    user = login("tester", "1234", "user")
    admin = login("admin", "1234", "admin")
    captures: list[tuple[str, str, Path]] = []

    for title, path in USER_PAGES:
        page = request_text(user, path)
        html_file = html_dir / f"{title}.html"
        image_file = png_dir / f"{title}.png"
        html_file.write_text(localize_html(page, title), encoding="utf-8")
        capture_page(chrome_path, html_file, image_file)
        captures.append((title, path, image_file))

    for title, path in ADMIN_PAGES:
        page = request_text(admin, path)
        html_file = html_dir / f"{title}.html"
        image_file = png_dir / f"{title}.png"
        html_file.write_text(localize_html(page, title), encoding="utf-8")
        capture_page(chrome_path, html_file, image_file)
        captures.append((title, path, image_file))

    gallery_file = build_gallery(output_dir, captures)
    (output_dir / "README.txt").write_text(
        f"Generated {len(captures)} screenshots at {time.strftime('%Y-%m-%d %H:%M:%S')}.\n"
        f"PNG folder: {png_dir}\n"
        f"Gallery: {gallery_file}\n"
        "This is a temporary QA artifact. Final review must delete it after approval.\n",
        encoding="utf-8",
    )
    print(output_dir)
    print(gallery_file)


if __name__ == "__main__":
    main()
