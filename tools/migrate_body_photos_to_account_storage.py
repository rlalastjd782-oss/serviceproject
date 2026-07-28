"""진행 사진 저장 위치를 static/progress_photos/ (인증 없이 공개 노출) 에서
instance/progress_photos/account_<id>/ (로그인해야 보이는 라우트로만 서빙) 로 옮긴다.

이 스크립트는 실제 파일을 옮기지 않고 "복사"만 한다(원본은 그대로 둠). 계정별
body_photos 테이블의 file_path 값도 예전 "progress_photos/<파일명>" 형식이면
새 형식(파일명만)으로 갱신한다. 배포 후 딱 한 번 실행하면 된다. 반복 실행해도
안전하다(이미 새 형식이면 건너뜀).

사용법:
    .venv\\Scripts\\python.exe tools\\migrate_body_photos_to_account_storage.py
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from health_tracker.config import BASE_DIR, DATABASE, account_photo_dir  # noqa: E402

OLD_PHOTO_DIR = BASE_DIR / "static" / "progress_photos"


def migrate_one_database(db_path: Path, folder_id: int) -> int:
    if not db_path.is_file():
        return 0
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        tables = {row["name"] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "body_photos" not in tables:
            return 0
        rows = db.execute("SELECT id, file_path FROM body_photos").fetchall()
        target_dir = account_photo_dir(folder_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        migrated = 0
        for row in rows:
            file_path = str(row["file_path"])
            basename = Path(file_path).name
            source = OLD_PHOTO_DIR / basename
            destination = target_dir / basename
            if source.is_file() and not destination.exists():
                shutil.copy2(source, destination)
                migrated += 1
            if file_path != basename:
                db.execute("UPDATE body_photos SET file_path = ? WHERE id = ?", (basename, row["id"]))
        db.commit()
        return migrated
    finally:
        db.close()


def main() -> None:
    total = 0
    total += migrate_one_database(DATABASE, folder_id=1)
    accounts_dir = DATABASE.parent / "accounts"
    if accounts_dir.is_dir():
        for db_path in sorted(accounts_dir.glob("user_*.db")):
            account_id = int(db_path.stem.removeprefix("user_"))
            count = migrate_one_database(db_path, folder_id=account_id)
            if count:
                print(f"{db_path.name}: {count}개 사진 이전")
            total += count
    print(f"완료: 총 {total}개 사진을 instance/progress_photos/로 복사했습니다.")
    print(f"원본은 {OLD_PHOTO_DIR}에 그대로 남아있습니다. 정상 동작 확인 후 직접 정리하세요.")


if __name__ == "__main__":
    main()
