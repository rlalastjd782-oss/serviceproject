from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE = BASE_DIR / "instance" / "workout.db"
PHOTO_DIR = BASE_DIR / "instance" / "progress_photos"
APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "Asia/Seoul")


def account_photo_dir(account_id: int) -> Path:
    # 계정 1(admin)과 2(최초 가입자)는 accounts.py의 account_db_path와 동일하게
    # 같은 workout.db(=같은 body_photos 테이블)를 공유하므로 사진 폴더도 같이 써야
    # 한다. 그 외 계정은 각자 자신의 폴더를 쓴다.
    folder_id = account_id if account_id > 2 else 1
    return PHOTO_DIR / f"account_{folder_id}"
