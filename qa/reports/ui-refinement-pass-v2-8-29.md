# UI 전반 다듬기 1차 패스 QA 리포트

## 1. 검증 대상

- 기능: UI 전반 다듬기 1차 패스
- 버전: `2.8.29`
- 기준 handoff: `handoff/dev-to-qa.md`
- 검증일: 2026-05-30

## 2. 참고 문서

- `docs/specs/ui-refinement-pass.md`
- `docs/design/ui-refinement-pass.md`
- `handoff/dev-to-qa.md`
- 이전 QA 참고: `qa/reports/today-ui-flow.md`

## 3. 테스트 환경

- OS/Shell: Windows PowerShell
- Python: 프로젝트 `.venv\Scripts\python.exe`
- 앱 URL: `http://127.0.0.1:5001/app`
- 검증 계정: `tester` / `1234`
- 제한 사항:
  - `git` 명령이 PowerShell PATH에 없어 `git status`, `git diff` 기반 확인은 수행하지 못했다.
  - Codex in-app browser backend `iab`가 현재 세션에서 제공되지 않아 Browser 플러그인 기반 시각 캡처는 수행하지 못했다.
  - 로컬 Chrome DevTools 포트 연결도 실패해 실제 픽셀 스크린샷은 남기지 못했다.

## 4. 실행한 검증

- `handoff/dev-to-qa.md`의 `QA 준비됨` 상태 확인
- 스펙/디자인 문서와 개발 handoff 검토
- 자동 테스트 및 정적 검증 실행
- 깨끗한 포트 `5001`에서 로컬 앱 실행 후 로그인 세션 기준 HTML 렌더링 확인
- 식단 모드 핵심 섹션/anchor/빈 상태 액션 렌더링 확인
- 운동 모드 핵심 DOM 순서 확인
- 식단 폼 토글 JS가 모든 `data-toggle-meal-form` 버튼 라벨을 함께 갱신하는지 정적 확인
- PWA 버전/서비스 워커 precache는 `tools/check_release.py`와 전체 테스트로 확인

## 5. 자동 검증 결과

- 통과: `.\.venv\Scripts\python.exe -m unittest tests.test_static_assets -v` (18 tests)
- 통과: `.\.venv\Scripts\python.exe tools\check_release.py` (`OK release 2.8.29`)
- 통과: `.\.venv\Scripts\python.exe -m unittest tests.test_ui_navigation_flows.UiNavigationFlowTest.test_fold_ui_regression_markers_render -v`
- 통과: `.\.venv\Scripts\python.exe -m ruff check health_tracker tests tools`
- 통과: `.\.venv\Scripts\python.exe -m compileall health_tracker tests tools`
- 통과: `.\.venv\Scripts\python.exe -m unittest discover -v` (55 tests)

## 6. 통과 항목

- `VERSION`, manifest, service worker cache는 release check 기준 `2.8.29`로 정합하다.
- 식단 모드 CSS 계약은 자동 테스트 기준 `오늘 칼로리 -> 식단 입력 -> 오늘 식단 -> 목표 달성률/체성분` 흐름을 보장한다.
- 로컬 `5001` 렌더링에서 `/app?mode=meal`은 `meal-goal-section`, `meal-input-section`, `id="meal-input"`, `today-meal-section`을 포함한다.
- 식단 기록이 없는 렌더링에서 `data-toggle-meal-form` 버튼 2개가 확인되어 상단 입력 버튼과 빈 상태 `입력 열기` 버튼이 함께 제공된다.
- `static/js/app_boot.js`의 `setMealFormToggleLabels()`는 `document.querySelectorAll("[data-toggle-meal-form]")` 전체를 순회해 라벨을 동시 갱신한다.
- 운동 모드 렌더링 순서는 DOM 기준 `workout-clock-section -> rest-timer -> workout-action-dock -> workout-input -> today-workout` 순서다.
- 검증 범위 내 사용자 노출 한글 깨짐, 린트, 컴파일, 전체 회귀 테스트 실패는 발견되지 않았다.

## 7. 발견한 이슈

### 배포 차단 이슈

- 없음

### 추후 확인 권장

- 실제 모바일 브라우저 픽셀 캡처와 PWA 캐시 갱신 체감 확인은 이번 세션의 browser backend 부재로 미검증이다.
- `git` PATH 부재로 변경 파일 목록은 검증하지 못했다.

## 8. 재현/확인 절차

1. `http://127.0.0.1:5001/auth/login?mode=user`로 접속한다.
2. `tester` / `1234`로 로그인한다.
3. `/app?mode=meal`에서 `오늘 칼로리`, `식단 입력`, `오늘 식단` 섹션과 빈 상태 `입력 열기` 버튼을 확인한다.
4. `/app?mode=workout`에서 `운동 시간`, `휴식 타이머`, 빠른 이동, 입력, 기록 순서를 확인한다.
5. 위 자동 검증 명령을 실행해 회귀 테스트와 release check를 확인한다.

## 9. 최종 판정

- 조건부 통과
- 배포 차단 이슈 없음
- 조건: 최종 검토자가 실제 모바일/PWA 환경에서 한 차례 시각 확인하면 충분하다.
