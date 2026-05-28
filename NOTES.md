# Codex Handoff Notes

## 현재 상태

- 현재 버전: `2.6.3`
- 기본 브랜치: `main`
- 최근 작업은 모두 커밋/푸시 완료되었습니다.
- 브라우저는 사용자가 요청할 때만 엽니다.
- 커밋 메시지는 한국어로 작성합니다.
- 작업 완료 시 `NOTES.md`, `CHANGELOG.md`를 갱신합니다.

## 최근 커밋

- 진행 중: v2.5.11 안정화/성능/UI/분석/관리자 고도화
- 진행 중: v2.5.10 구조 정리, `app.py` 경량화, JS boot 분리, 오늘 화면 partial 분리
- `0a5ba63` 2.5.9 대형 파일 정리 기록 갱신
- `2954b01` 배포 점검 도구 추가
- `a48100d` 폼 제출 스크립트 분리
- `ffcd913` 흐름 테스트 도메인별 분리
- `3a94d00` 데이터베이스 헬퍼 모듈 분리
- `ba0706d` 2.5.8 구조 정리 기록 갱신
- `92b0438` 서비스 조회 컬럼 명시화
- `4e8c7fa` 프론트 공통 스크립트 분리
- `59f382b` 대형 CSS 파일 구조 분리
- `2b3b324` 설정 헬퍼 모듈 분리
- `f18348b` 앱 생명주기 훅 분리

## 2026-05-29 v2.5.9 문서 복구

- 기존 `NOTES.md`, `CHANGELOG.md`에 깨진 인코딩 텍스트가 많이 남아 있어 문서 전체를 정상 한국어로 다시 작성했습니다.
- 깨진 과거 전문은 유지하지 않았고, 현재 운영에 필요한 핵심 이력과 인수인계 정보만 남겼습니다.
- 이후 문서 수정 시 PowerShell 인코딩 변환으로 한글이 깨지지 않도록 주의해야 합니다.

## 2026-05-29 v2.5.10 전체 소스 구조 정리

- `app.py`에 집중되어 있던 기능 wrapper와 직접 SQL helper를 `app_analysis_facade.py`, `app_workout_facade.py`, `app_pr_facade.py`, `app_location_facade.py`, `app_summary_facade.py`, `app_activity_facade.py`, `app_body_meal_facade.py`, `app_coaching_reports_facade.py`, `app_recovery_facade.py`로 분리했습니다.
- `app.py`는 앱 생성, 설정 주입, 라우트 등록, 전역 Jinja helper 연결 중심으로 줄였습니다.
- `static/js/app.js`에서 초기화와 이벤트 리스너를 `static/js/app_boot.js`로 분리했습니다.
- `today/index.html`의 전체 보기 섹션을 `today/_overview_panels.html` partial로 분리했습니다.
- `VERSION`, manifest, service worker cache를 `2.5.10`으로 맞췄습니다.
- QA 기준: Ruff, compileall, release check, JS syntax check, 전체 unittest 30개 통과를 기준으로 마무리합니다.

## 2026-05-29 v2.5.11 고도화 1차

- 안정화: 오늘/운동/식단 모드별 서버 렌더링 범위를 분리해 숨김 CSS에 의존하던 불필요한 화면 생성을 줄였습니다.
- 성능: 전체/식단 모드에서 운동 루틴, 추천, 세트 빌더, 운동 기록 데이터를 만들지 않도록 `today_context` 계산 범위를 축소했습니다.
- UI/UX: 식단 모드는 식단 입력/기록만, 운동 모드는 운동 입력/루틴/기록만 보이도록 템플릿 포함 구조를 정리했습니다.
- 분석: 주간/월간 분석에 다음 행동 카드(`analysis-action-plan`)를 추가했습니다.
- 관리자: 사용자 활성률, 기록 없는 계정, 조치 필요 상태를 대시보드 지표로 보강했습니다.
- 회귀 테스트: Fold UI 테스트에 모드별 렌더링과 분석 액션 카드 검증을 추가했습니다.

## 2026-05-29 v2.6.0 실사용 안정 버전

- QA 리포트에 오늘 운동, 기록 검색, 주간 분석, 월간 분석, 주간 식단의 서버 렌더링 시간 측정을 추가했습니다.
- 식단 입력에 2개/3개/4개 빠른 행 추가 버튼을 추가했습니다.
- 식단 빠른 후보는 최근 180일 기준으로 제한해 장기 데이터가 누적되어도 식단탭 계산량이 과하게 커지지 않게 했습니다.
- 기록 검색 결과 CSS를 `static/css/records.css`로 분리했습니다.
- `server*.log`를 `.gitignore`에 추가했습니다.
- `VERSION`, manifest, service worker cache를 `2.6.0`으로 맞췄습니다.
- 전체 QA 기준은 release check, Ruff, compileall, 전체 JS syntax check, 전체 unittest입니다.

## 2026-05-29 v2.6.1 관리자 문구 수정

- 관리자 대시보드 운영 체크포인트 카드에 깨진 물음표로 보이던 사용자 활성/조치 필요/데이터 규모 문구를 정상 한국어로 수정했습니다.
- 관리자 대시보드 회귀 테스트에 해당 문구와 반복 물음표 미노출 검증을 추가했습니다.

## 2026-05-29 v2.6.2 전체 깨진 문구 정리

- 오늘 운동 입력 JS의 세트 라벨, 최근 세트 버튼, 다음 세트 추천, 운동 추가/닫기 버튼 문구를 정상 한국어로 복구했습니다.
- 식단 입력 접기/열기 버튼, 주간/월간 분석 액션 카드, 장소 기본 메모와 장비 fallback 문구를 정상 한국어로 복구했습니다.
- 사용자 화면 소스에 반복 물음표와 깨진 인코딩 흔적이 다시 들어오면 실패하는 정적 회귀 테스트를 추가했습니다.

## 2026-05-29 v2.6.3 추가 깨진 문구 및 캐시 갱신

- 분석 카드 렌더링을 다시 확인하고 주간/월간/일간 분석 HTML에 반복 물음표가 노출되지 않는 것을 검증했습니다.
- 식단 빠른 입력 개수 버튼, 운동 시간 저장 상태, 회복 칩 CSS에 남아 있던 깨진 문구를 정상 한국어로 복구했습니다.
- service worker 캐시 버전을 올려 브라우저가 이전 정적 파일을 계속 물고 있는 상황을 줄였습니다.

## 2026-05-29 v2.5.9 대형 파일 추가 분리

- `app_database.py`를 추가해 DB 연결, DB 초기화, secret key 생성을 `app.py`에서 분리했습니다.
- `tests/test_app_flows.py`를 공통 base와 도메인별 테스트 파일로 분리했습니다.
- `form_submit.js`를 추가해 submit, CSRF, 운동완료 타이머 리셋 처리 로직을 `app.js`에서 분리했습니다.
- `tools/check_release.py`를 추가해 배포 전 버전/정적파일 상태를 확인할 수 있게 했습니다.
- 테스트 분리 중 PowerShell 저장 방식으로 인코딩이 깨지는 문제가 있었고, Node UTF-8 방식으로 다시 분리해 해결했습니다.

## 2026-05-29 v2.5.8 구조 분리와 쿼리 경량화

- `app_lifecycle.py`로 before/after request, DB teardown, 템플릿 컨텍스트 주입을 분리했습니다.
- `app_settings.py`로 app setting, app preferences, 설정 잠금/해제 헬퍼를 분리했습니다.
- 기존 CSS URL은 유지하면서 `static/css/core`, `features`, `overrides`, `responsive` 하위 파일로 대형 CSS를 나눴습니다.
- `dom_data.js`, `pwa.js`, `select_theme.js`, `readiness.js`를 추가해 `app.js`의 공통 기능을 분리했습니다.
- 서비스 계층의 주요 `SELECT *`를 명시 컬럼 조회로 바꿔 불필요한 컬럼 로딩을 줄였습니다.

## 2026-05-29 v2.5.7 성능/배포/소스 진단 개선

- 요청 단위 `current_account`, app setting, app preferences 캐시를 추가했습니다.
- `touch_account_seen`은 세션 기준 5분 간격으로 제한해 페이지 이동마다 계정 DB write가 발생하지 않게 했습니다.
- SQLite 성능 진단용 `services/performance.py`를 추가했습니다.
- QA 화면에서 인덱스 상태, 누락 인덱스, 주요 쿼리 계획, `ANALYZE` 실행을 볼 수 있게 했습니다.
- 배포 점검용 `services/deployment.py`와 소스 길이 점검용 `services/source_audit.py`를 추가했습니다.
- 서비스워커 precache에서 HTML 페이지를 제거하고 핵심 정적 파일 중심으로 줄였습니다.

## 계정/권한 구조

- 일반 사용자는 운동, 기록, 분석, 식단, 더보기, 설정 흐름을 사용합니다.
- 관리자는 관리자 페이지 중심으로 접근합니다.
- 관리자는 운동 사용자처럼 기록 집계에 포함되지 않도록 처리되어 있습니다.
- 사용자 계정별 DB가 분리되어 있으므로 1번 사용자 장소/운동기록은 2번 사용자에게 보이지 않는 것이 정상입니다.
- 계정별 DB 구조 때문에 PythonAnywhere 배포 시 기존 DB 파일을 유지해야 기존 데이터가 보존됩니다.

## 배포 메모

- PythonAnywhere 배포는 기본적으로 `git pull` 후 Web 탭 Reload 흐름입니다.
- DB 파일을 삭제하거나 새로 덮어쓰지 않으면 기존 데이터는 유지됩니다.
- Static files mapping에서 `/static/`이 실제 프로젝트의 `static` 폴더를 가리키는지 확인해야 합니다.
- 배포 전 로컬에서 다음 명령을 실행합니다.

```powershell
python tools\check_release.py
python -m ruff check health_tracker tests tools
python -m unittest discover -v
python -m compileall health_tracker tests tools
```

## QA 기준

- 전체 unittest는 30개입니다.
- 정적 CSS는 `tests/test_static_assets.py`에서 전체 CSS 파일을 재귀 검사합니다.
- JS는 `static/js/*.js`와 `static/sw.js`를 `node --check`로 확인합니다.
- `tools/check_release.py`는 다음을 확인합니다.
  - `VERSION`
  - `static/manifest.webmanifest`의 version
  - `static/sw.js`의 cache version
  - 주요 static 파일 존재 여부

## 현재 큰 파일 현황

- `health_tracker/app.py`: 약 2046줄
- `static/js/app.js`: 약 787줄
- `static/css/meal.css`: 약 646줄
- `health_tracker/templates/today/index.html`: 약 568줄
- `health_tracker/templates/summaries/summary.html`: 약 461줄
- `tests/test_workout_meal_flows.py`: 약 459줄
- `tests/test_account_admin_flows.py`: 약 451줄
- `health_tracker/services/coaching.py`: 약 448줄

## 다음 정리 우선순위

1. `app.py`의 분석/운동 wrapper 추가 분리
2. `app.js`의 클릭 핸들러, 세트 빌더, 운동 빠른메뉴 분리
3. `meal.css`를 식단 입력, 식단 리스트, 즐겨찾기/최근음식 UI로 재분류
4. `today/index.html`을 운동 입력, 오늘 기록, 빠른 메뉴, 식단 섹션 partial로 분리
5. `summaries/summary.html`을 분석 카드, 목록, 필터, 차트 섹션 partial로 분리
6. `services/coaching.py`를 회복 체크인, 추천, 경고/인사이트 계산으로 분리
7. 테스트 파일 중 `test_workout_meal_flows.py`, `test_account_admin_flows.py`를 더 작게 분리

## 주의사항

- 문서나 테스트 파일에 이미 깨진 문자열이 섞여 있으면 PowerShell `Set-Content`로 저장하면서 문법 오류가 커질 수 있습니다.
- 한글 문서 전체 재작성은 `apply_patch`로 처리하는 것이 안전합니다.
- 테스트 파일을 기계적으로 나눌 때는 Node `fs.readFileSync(..., "utf8")` 방식이 PowerShell보다 안전했습니다.
- 사용자가 브라우저를 요청하기 전까지 브라우저를 열지 않습니다.
