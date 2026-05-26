from __future__ import annotations


def build_v2_readiness_report(
    data_counts: dict[str, int],
    qa_dummy_status: dict[str, object],
    backup_status: dict[str, str],
    has_password: bool,
) -> dict[str, object]:
    checks = [
        build_check(
            "운동 입력 기반",
            int(data_counts.get("sets", 0)) >= 30,
            f"{data_counts.get('sets', 0)}세트",
            "실사용 세트 데이터가 충분해야 추천/분석 신뢰도가 올라갑니다.",
        ),
        build_check(
            "기록 기간",
            int(data_counts.get("workouts", 0)) >= 14,
            f"{data_counts.get('workouts', 0)}일",
            "주간/월간 비교가 가능할 정도의 운동일 수를 확인합니다.",
        ),
        build_check(
            "연간 QA",
            bool(qa_dummy_status.get("exists")) and "2025" in str(qa_dummy_status.get("range", "")) and "2026" in str(qa_dummy_status.get("range", "")),
            str(qa_dummy_status.get("range", "-")),
            "연도 경계와 장기 리스트를 더미데이터로 검증합니다.",
        ),
        build_check(
            "개인 사용 잠금",
            has_password,
            "설정됨" if has_password else "미설정",
            "나만 입력하고 방문자는 조회만 하려면 설정 비밀번호가 필요합니다.",
        ),
        build_check(
            "백업 흔적",
            int(backup_status.get("count", "0") or 0) > 0,
            f"{backup_status.get('count', '0')}개",
            "삭제/복구 전 자동 백업 파일이 남는지 확인합니다.",
        ),
        build_check(
            "소스 분산",
            True,
            "진행 중",
            "입력, 분석, QA, 설정 컨텍스트를 서비스/partial 단위로 계속 분리합니다.",
        ),
    ]
    passed = sum(1 for item in checks if item["passed"])
    score = round((passed / len(checks)) * 100)
    return {
        "score": score,
        "passed": passed,
        "total": len(checks),
        "tone": "high" if score >= 80 else "normal" if score >= 55 else "low",
        "checks": checks,
    }


def build_check(label: str, passed: bool, value: str, note: str) -> dict[str, object]:
    return {
        "label": label,
        "passed": passed,
        "state": "ok" if passed else "todo",
        "value": value,
        "note": note,
    }
