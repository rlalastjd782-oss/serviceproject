# 기록탭 스타일 기준 전체 UI 입체감 통일 QA 리포트

## 1. 검증 대상

- 기능: 기록탭 스타일 기준 전체 UI 입체감 통일
- 버전: `2.8.30`
- 기준 handoff: `handoff/dev-to-qa.md`
- 검증일: 2026-05-31

## 2. 참고 문서

- `docs/specs/records-style-dimensional-ui.md`
- `docs/design/records-style-dimensional-ui.md`
- `handoff/dev-to-qa.md`
- `docs/agent-status.md`

## 3. 테스트 환경

- OS/Shell: Windows PowerShell
- Python: 프로젝트 `.venv\Scripts\python.exe`
- 로컬 앱 URL: `http://127.0.0.1:5000`
- 검증 계정: QA 중 생성한 임시 사용자 계정
- 제한 사항:
  - 프로젝트 정책에 따라 PNG/JPG/WebP 이미지와 스크린샷 파일은 생성하지 않았다.
  - Codex in-app browser backend `iab`가 현재 세션에서 제공되지 않아 Browser 플러그인 기반 실제 픽셀 시각 검증은 수행하지 못했다.
  - 새 QA 계정 기준 렌더링이라 `/summaries/daily`의 `.daily-record-card`, `.daily-metric` 실데이터 카드는 화면 HTML에 생성되지 않았다. 해당 항목은 CSS 계약과 자동 테스트로 확인했다.

## 4. 실행한 검증

- `handoff/dev-to-qa.md`의 `QA 준비됨` 상태 확인
- 스펙/디자인/handoff 검토
- `static/css/overrides/ui_rebuild_05.css`의 `v2.8.30 records-style dimensional UI pass` 토큰과 selector 확인
- `health_tracker/templates/layouts/base.html` CSS 로드 순서 확인
- `VERSION`, `static/manifest.webmanifest`, `static/sw.js` 버전 및 PWA precache 항목 확인
- 로컬 Flask 서버 실행 후 `/auth/login?mode=user` 응답 `200` 확인
- 로그인 세션 기준 주요 화면 HTML 렌더링과 최종 CSS 로드 확인
- 자동 테스트, 릴리스 검증, 린트, 컴파일, 전체 회귀 테스트 실행
- SourceTree 내장 Git 경로로 `git status --short` 확인

## 5. 자동 검증 결과

- 통과: `.\.venv\Scripts\python.exe -m unittest tests.test_static_assets -v` (19 tests)
- 통과: `.\.venv\Scripts\python.exe tools\check_release.py` (`OK release 2.8.30`)
- 통과: `.\.venv\Scripts\python.exe -m ruff check health_tracker tests tools`
- 통과: `.\.venv\Scripts\python.exe -m compileall health_tracker tests tools`
- 통과: `.\.venv\Scripts\python.exe -m unittest discover -v` (56 tests)

## 6. 렌더링 확인 결과

- `/app`: `today-shell`, `date-row`, `today-mode-actions`, `summary-grid`, `summary-card` 렌더링 확인. `css/ui_rebuild.css?v=v2.8.30`이 마지막 CSS로 로드됨.
- `/app?mode=workout`: `today-shell`, `workout-mode`, `workout-action-dock`, `workout-form`, `set-entry-list` 렌더링 확인. `css/ui_rebuild.css?v=v2.8.30`이 마지막 CSS로 로드됨.
- `/app?mode=meal`: `today-shell`, `meal-mode`, `meal-goal-section`, `meal-input-section`, `today-meal-section` 렌더링 확인. `css/ui_rebuild.css?v=v2.8.30`이 마지막 CSS로 로드됨.
- `/summaries/daily`: `record-subnav`, `section`, `period-filter-form` 렌더링 확인. 새 계정이라 일별 기록 카드 실데이터는 없음.
- `/records/search`: `record-search-dashboard`, `record-search-form`, `record-filter-details` 렌더링 확인.
- `/summaries/weekly`: `analysis-subnav`, `analysis-dashboard-section` 렌더링 확인.
- `/more`: `more-section`, `more-group-section`, `more-link-card` 렌더링 확인.

## 7. 통과 항목

- 공통 `--surface-page`, `--surface-card`, `--surface-card-soft`, `--surface-control`, `--surface-shadow`, `--surface-shadow-active` 토큰이 최종 override에 정의되어 있다.
- 오늘탭 바깥 섹션, 기록 subnav/필터 섹션, 기록 검색, 분석 dashboard section, 더보기 group section이 Surface 1 계열 selector에 포함되어 있다.
- 오늘탭 내부 카드, 기록 카드, 검색 결과 카드, 분석 metric/rank 카드, 더보기 link card가 Surface 2 계열 selector에 포함되어 있다.
- `.daily-metric`, `.record-result-value`, `.detail-row`, `.set-entry-row`, `.timer-actions`, `.record-search-form`, `.period-filter-form` 등 내부 row/control이 Surface 3 계열 selector에 포함되어 있다.
- active 탭, 기록/분석 subnav, 오늘 mode, primary action은 배경/텍스트/shadow가 함께 바뀌는 active selector에 포함되어 있다.
- `@media (max-width: 560px)`에서 `.record-result-card`가 1열로 전환되고 값 영역 정렬이 왼쪽으로 바뀌는 규칙이 있다.
- `VERSION`, manifest version, service worker cache name이 `2.8.30`으로 정합하다.
- 한글 인코딩 깨짐, CSS brace 불균형, 린트/컴파일/회귀 테스트 실패는 발견되지 않았다.

## 8. 발견한 이슈

### 배포 차단 이슈

- 검증 범위 내 이슈 없음

### 추후 확인 권장

- 실제 모바일/PWA 환경에서 390px, 430px, 560px, desktop 기준 시각 확인을 한 차례 권장한다. 이번 세션에서는 browser backend `iab` 부재와 이미지 생성 금지 정책 때문에 실제 픽셀 캡처를 수행하지 못했다.
- 실데이터가 있는 계정에서 `/summaries/daily`의 `.daily-record-card`, `.daily-metric` 깊이 구분을 수동 확인하면 좋다.

## 9. 재현/확인 절차

1. `http://127.0.0.1:5000/auth/login?mode=user`로 접속한다.
2. 사용자 계정으로 로그인한다.
3. `/app`, `/app?mode=workout`, `/app?mode=meal`, `/summaries/daily`, `/records/search`, `/summaries/weekly`, `/more`를 연다.
4. 개발자 도구에서 `css/ui_rebuild.css?v=v2.8.30`이 마지막 스타일시트로 로드되는지 확인한다.
5. 각 화면에서 Surface 1 바깥 카드, Surface 2 내부 카드, Surface 3 row/control, active 상태의 배경/텍스트/shadow 차이를 확인한다.
6. 위 자동 검증 명령을 실행해 릴리스와 회귀 테스트를 확인한다.

## 10. 최종 판정

- 조건부 통과
- 배포 차단 이슈 없음
- 조건: 최종검수 단계에서 실제 모바일 또는 PWA 환경으로 주요 화면의 시각 깊이와 한글 라벨 겹침 여부를 수동 확인한다.
