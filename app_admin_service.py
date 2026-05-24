from __future__ import annotations

from pathlib import Path


def build_app_health_status(
    database: Path,
    data_counts: dict[str, int],
    sample_counts: dict[str, int],
    backup_status: dict[str, str],
) -> list[dict[str, str]]:
    database_exists = database.exists()
    return [
        {
            "label": "DB 파일",
            "value": "정상" if database_exists else "없음",
            "note": str(database),
            "state": "ok" if database_exists else "warn",
        },
        {
            "label": "저장 데이터",
            "value": f"운동 {data_counts['workouts']}일 · 식단 {data_counts['meals']}개",
            "note": f"세트 {data_counts['sets']}개 · 빈 기록 {data_counts['empty_workouts']}개",
            "state": "warn" if data_counts["empty_workouts"] else "ok",
        },
        {
            "label": "샘플 데이터",
            "value": f"세트 {sample_counts['sets']}개 · 식단 {sample_counts['meals']}개",
            "note": "화면 확인용 데이터입니다.",
            "state": "info" if sample_counts["sets"] or sample_counts["meals"] else "ok",
        },
        {
            "label": "백업",
            "value": f"{backup_status['count']}개",
            "note": f"최근 {backup_status['last_backup']}",
            "state": "ok" if backup_status["count"] != "0" else "warn",
        },
    ]
