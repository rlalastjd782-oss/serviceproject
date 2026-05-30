# 오늘 화면 UI 흐름 QA 리포트

## 1. 검증 대상

- 기능: 오늘 화면 UI 흐름 재점검 및 수정
- 버전: `2.8.28`
- 브랜치: `.git/HEAD` 기준 `main`
- 마지막 커밋 메시지: `오늘 UI 흐름 재점검 및 수정`
- 주요 변경 범위 추정: `CHANGELOG.md`의 `v2.8.28` 항목 기준, 오늘 화면 섹션 표면을 흰색 카드 중심으로 되돌리고 `v2.8.27`의 운동 흐름 순서 보정을 유지하는 변경
- 제한 사항: 현재 환경에서 `git` 명령이 PATH에 없어 `git status`, `git diff` 기반 변경사항 확인은 수행하지 못함

## 2. 참고한 스펙/디자인 문서

- `docs/specs/`: 확인 가능한 기능 기획 문서 없음
- `docs/design/health-tracker-ui-structure.md`
- 보조 참고: `CHANGELOG.md`, `UI_QA.md`, `README.md`

## 3. 테스트 환경

- OS/Shell: Windows PowerShell
- 프로젝트 경로: `C:\Users\Minseong\Documents\Codex\2026-05-23\serviceproject`
- Python: 프로젝트 `.venv\Scripts\python.exe`
- 앱 URL: `http://127.0.0.1:5000/app`
- 계정: 사용자 `tester` / `1234`
- 브라우저 검증 뷰포트: 430 x 932 모바일 기준
- 검증일: 2026-05-30
- 캡처 산출물:
  - `artifacts/qa_today_ui_v2828/meal-mode-fullpage.png`
  - `artifacts/qa_today_ui_v2828/workout-mode-fullpage.png`

## 4. 실행한 검증

- `docs/specs/`, `docs/design/` 문서 확인
- `.git/HEAD`, `.git/COMMIT_EDITMSG`, `VERSION`, `CHANGELOG.md` 확인
- 로컬 앱 `http://127.0.0.1:5000/app` 응답 확인
- 브라우저에서 `/app` 접근 후 로그인 흐름 확인
- 오늘 요약, 운동 모드, 식단 모드, 기록 화면의 DOM/레이아웃 순서 확인
- 모바일 뷰포트에서 가로 overflow 여부 확인
- 주요 사용자 노출 한글 깨짐 여부 확인
- 자동 검증 실행:
  - `.\.venv\Scripts\python.exe -m unittest tests.test_static_assets -v`
  - `.\.venv\Scripts\python.exe tools\check_release.py`
  - `.\.venv\Scripts\python.exe -m ruff check health_tracker tests tools`
  - `.\.venv\Scripts\python.exe -m compileall health_tracker tests tools`
  - `.\.venv\Scripts\python.exe -m unittest discover -v`

## 5. 통과 항목

- 릴리스 버전은 `VERSION`과 `static/manifest.webmanifest`에서 `2.8.28`로 일치함
- `/app`는 로그인 후 오늘 화면으로 정상 진입함
- 상단 탭은 `오늘`, `기록`, `분석`, `식단`, `더보기`, `설정`, `로그아웃`을 표시하고 현재 화면 active 상태를 제공함
- 오늘 요약 모드는 `운동`, `식단`, `요약` 모드 전환을 제공하며 `요약` 버튼이 active 상태임
- 운동 모드는 `운동`, `식단`, `요약`, `집중 모드` 전환을 제공하며 `운동` 버튼이 active 상태임
- 운동 모드에서 상단 주요 흐름은 운동 시간, 휴식 타이머, 운동 입력, 오늘 운동 기록 순으로 노출됨
- 식단 모드는 `식단` 버튼이 active 상태임
- 430px 모바일 뷰포트에서 오늘/운동/식단/기록 화면의 가로 overflow는 발견되지 않음
- 브라우저 DOM 기준 주요 사용자 노출 한글 깨짐은 발견되지 않음
- 자동 테스트 54개 전체 통과
- Ruff 통과, compileall 통과, release check 통과

## 6. 발견한 이슈

### 배포 차단 이슈

- 없음

### 추후 수정 가능 이슈

#### QA-TODAY-001: 식단 모드에서 식단 입력보다 목표/체성분 섹션이 먼저 노출됨

- 화면: `/app?mode=meal`
- 심각도: Medium
- 관련 문서 기준: `docs/design/health-tracker-ui-structure.md`의 사용자 흐름 5번은 식단 모드에서 `식단 입력`, `오늘 식단 기록`, `목표/도움말 영역` 순으로 확인한다고 정의함
- 실제 DOM 위치:
  - `목표 달성률`: top 398
  - `체성분`: top 992
  - `식단 입력`: top 1490
  - `오늘 식단`: top 1878
  - `오늘 칼로리`: top 1989
- 관련 파일/조건:
  - `health_tracker/templates/today/index.html`에서 `_body_metrics.html` 포함부가 식단 입력 include보다 앞에 배치된 것으로 보임
  - `static/css/today.css`에는 `.meal-mode .meal-input-section { order: 10; }`, `.today-meal-section { order: 20; }`, `.meal-goal-section { order: 30; }`가 있으나 `.optional-section` 계열은 식단 모드에서 order가 지정되지 않아 더 먼저 배치됨

## 7. 재현 절차

1. 로컬 앱을 실행한 상태에서 `http://127.0.0.1:5000/app`에 접속한다.
2. 사용자 계정 `tester` / `1234`로 로그인한다.
3. 모바일 뷰포트 430 x 932 기준으로 `/app?mode=meal`에 접속한다.
4. 화면 상단에서 `식단` 모드가 active 상태인지 확인한다.
5. 첫 번째 visible section부터 아래로 스크롤하며 섹션 순서를 확인한다.

## 8. 기대 결과

- 식단 모드 진입 직후 사용자가 먼저 `식단 입력`을 볼 수 있어야 한다.
- 그 다음 `오늘 식단` 기록이 나오고, 이후 `목표/도움말/체성분` 같은 보조 영역이 배치되어야 한다.
- 문서의 사용자 흐름처럼 식단 기록 업무가 화면의 1차 행동으로 노출되어야 한다.

## 9. 실제 결과

- 식단 모드 진입 직후 첫 visible section은 `목표 달성률`이다.
- `체성분` 섹션이 그 다음에 노출된다.
- `식단 입력`은 약 1490px 아래에 위치해 첫 화면에서 보이지 않는다.
- `오늘 식단` 기록은 `식단 입력`보다도 아래에 위치한다.

## 10. 심각도

- Medium
- 배포 차단 수준은 아니지만, 식단 모드의 핵심 사용자 행동이 첫 화면에서 밀려나 디자인 문서의 사용자 흐름과 어긋난다.
- 모바일 사용자가 식단 기록 화면으로 들어왔을 때 먼저 기록 입력을 찾기 어렵다.

## 11. 최종 판정

- 조건부 통과
- 자동 테스트, 릴리스 검증, 린트, 컴파일은 모두 통과했다.
- 오늘 요약/운동 모드의 핵심 흐름은 검증 범위 내 치명 이슈 없음.
- 식단 모드는 핵심 입력 섹션 순서 이슈가 있어 추후 수정 권장.
