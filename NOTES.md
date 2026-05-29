# Codex Handoff Notes

## 현재 상태

- 현재 버전: `2.8.7`
- 기본 브랜치: `main`
- 커밋 메시지는 한국어로 작성합니다.
- 작업 완료 후 `NOTES.md`, `CHANGELOG.md`, `VERSION`, manifest, service worker cache를 함께 갱신합니다.
- 브라우저는 사용자가 요청할 때만 엽니다.

## 최근 작업

- v2.8.5에서 전체 CSS의 레거시 다크 배경 직접값을 정리했습니다.
- v2.8.6에서 쿨 그레이 운영툴형 UI 예시 페이지 `/auth/theme-preview`를 추가했습니다.
- v2.8.7에서 실제 앱 메인 UI에 차콜 헤더와 회색 표면 톤을 시범 적용했습니다.
- 분석신뢰도 원형, 기록 카드, 분석 카드, 식단 입력/목록, 더보기 카드에 남아 있던 검은색/짙은 남색 계열을 밝은 회색톤으로 교체했습니다.
- `ui_rebuild_01.css`, `ui_rebuild_02.css`, `ui_rebuild_03.css`의 과거 다크 override를 밝은 테마에 맞게 정리했습니다.
- CSS 정적 테스트에 레거시 다크 표면 색상과 밝은 글씨 토큰 재유입 방지 검사를 추가했습니다.
- 식단 저장 실패 원인이 될 수 있던 식단 관련 POST 폼의 CSRF 토큰 누락은 v2.8.4에서 보강했습니다.

## 검증 기준

- `python -m ruff check health_tracker tests tools`
- `python -m compileall health_tracker tests tools`
- `node --check` for `static/js/*.js`
- `python -m unittest discover -v`
- `python tools/check_release.py`

## 주의사항

- CSS 색상 변경은 마지막 override만 추가하지 말고 실제 원본 CSS의 직접값까지 같이 정리해야 합니다.
- 서비스워커 캐시가 남아 있으면 배포 후 예전 CSS가 보일 수 있으므로 버전과 cache name을 반드시 함께 올립니다.
