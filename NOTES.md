# Codex Handoff Notes

## 2026-05-28 v2.5.2 운동 중 집중 모드
- `/app?mode=workout&focus=1`로 운동 중 집중 모드를 추가했습니다.
- 오늘 운동 탭의 상단 모드 버튼에 집중 모드/집중 해제 토글을 추가했습니다.
- 집중 모드에서는 보조 섹션을 숨기고 운동 타이머, 휴식 타이머, 빠른 이동, 오늘 할 일, 운동 입력, 오늘 운동, 완료 리뷰를 중심으로 정렬합니다.
- 완료 리뷰 섹션에 `workout-finish` 앵커를 추가해 운동 중 빠른 메뉴에서 바로 이동할 수 있게 했습니다.
- 테스트에는 집중 모드 렌더링, 빠른 이동 앵커, CSS 숨김 규칙 검증을 추가했습니다.
- 검증은 Ruff, 전체 unittest, compileall, 주요 JS 문법 검사, `git diff --check`로 확인했습니다.

## 2026-05-28 v2.5.1 Ruff QC 도구 설치
- 현재 가상환경에 `ruff==0.15.14`를 설치했고 `requirements-dev.txt`에 개발 의존성으로 고정했습니다.
- `pyproject.toml`을 추가해 Ruff 기본 검사 범위를 `F` 계열로 설정했습니다.
- 현재 라우트 모듈은 `globals().update(ctx)`로 `app.py` 컨텍스트를 주입받는 구조라, `health_tracker/routes/*.py`의 F821은 per-file ignore로 예외 처리했습니다.
- `app.py`도 라우트 컨텍스트 전달을 위해 일부 import를 `globals()`에 남기는 구조라 F401을 예외 처리했습니다.
- `tests/test_app_flows.py`의 실제 미사용 import는 제거했습니다.
- 검증은 `ruff check health_tracker tests`, 전체 unittest, compileall, 주요 JS 문법 검사, `git diff --check`로 확인했습니다.

## 2026-05-28 v2.5.0 운동 완료 리뷰 및 목표 진행률
- 오늘 운동 완료 영역에 `workout_finish_review` 컨텍스트를 추가하고 `services/workout_plan.py`에서 완료 리뷰 데이터를 생성하도록 했습니다.
- 완료 리뷰는 총 세트, 운동 볼륨, PR, 유산소, 직전 운동 대비 볼륨, 계획 달성률, RPE 기반 회복 코멘트를 표시합니다.
- 운동별 목표 진행률은 기존 `exercise_settings.target_weight`, `target_reps`, `target_sets`를 활용해 `services/exercise_settings.py`에서 계산합니다.
- 오늘 운동 기록 카드에 목표 진행률 막대와 목표별 현재/목표 값을 표시합니다.
- 신규 DB 테이블 없이 기존 데이터만 재사용했습니다.
- `VERSION`, `static/manifest.webmanifest`, `static/sw.js`를 `2.5.0`으로 맞췄습니다.
- 검증은 전체 unittest, compileall, 주요 JS 문법 검사, `git diff --check`로 마무리했습니다.

## 2026-05-28 v2.4.5 라우트 및 서비스 추가 정리
- `routes/main.py`에 남아 있던 분석/캘린더/식단/기록/홈/프로그램/API 라우트를 `summaries.py`, `calendar.py`, `meal_pages.py`, `records.py`, `home.py`, `programs.py`, `api.py`로 나눴습니다.
- `app.py`에 직접 남아 있던 운동 세션 생성/조회, 운동 목록, 최근 세트, 운동 통계 SQL을 `services/workout.py`로 옮겼습니다.
- 즐겨찾기 운동 조회는 `services/exercise_settings.py`, 과부하 제안 조회는 `services/progressive_overload.py`로 분리했습니다.
- `meta.py`의 앱 갱신시각 참조 브랜치를 `master`에서 `main`으로 수정했습니다.
- `VERSION`, `static/manifest.webmanifest`, `static/sw.js`를 `2.4.5`로 맞췄습니다.
- 단위별 검증 후 커밋/푸시를 나눠 진행했습니다. 최종 검증은 전체 unittest, compileall, 주요 JS 문법 검사, `git diff --check`로 확인했습니다.

## 2026-05-28 v2.4.4 구조 및 성능 최적화
- `health_tracker/services/food_shortcuts.py`, `location_insights.py`, `goals.py`, `reminders.py`를 추가해 `app.py`에 몰려 있던 식단 빠른선택, 장소 인사이트, 목표, 리마인더 DB 로직을 분리했습니다.
- 장소 인사이트는 장소마다 top exercise/equipment/equipment list를 반복 조회하던 구조를 bulk 조회 후 Python에서 그룹핑하는 방식으로 바꿨습니다.
- SQLite 연결 설정에 foreign key, busy timeout, WAL, synchronous NORMAL을 적용했고 식단/운동/장소 장비 복합 인덱스를 추가했습니다.
- 응답 헤더에 `X-Request-Duration-ms`, `X-DB-Query-Count`, `Server-Timing`을 추가해 각 화면의 처리 시간과 DB 쿼리 수를 확인할 수 있게 했습니다.
- `static/notifications.js`, `static/meal_entry.js`, `static/meal.css`를 추가하고 service worker precache 및 layout 로드를 갱신했습니다.
- 오늘 화면은 `_body_metrics.html`, `_status_panels.html`, `_meal_input.html` partial로 추가 분리했습니다.
- 보안/마이그레이션 테스트는 `tests/test_security_and_migration.py`로 분리했고 전체 테스트는 27개로 통과했습니다.
- 로컬 `__pycache__` 산출물을 정리했습니다.
- 검증 완료: `python -m unittest discover -v`, `python -m compileall health_tracker tests`, `node --check static/app.js`, `node --check static/meal_entry.js`, `node --check static/notifications.js`, `node --check static/workout_entry.js`, `node --check static/offline_queue.js`, `node --check static/workout_tools.js`, `node --check static/ui_interactions.js`, `git diff --check`.

## 2026-05-28 v2.4.3 식단 빠른 선택 정리
- 식단 입력 저장 시 모든 음식이 `food_favorites`에 자동 등록되던 처리를 제거했습니다. 앞으로 고정 음식은 사용자가 직접 `고정` 버튼으로 등록한 항목만 표시됩니다.
- 식단 입력 패널을 `고정 음식`, `자주 먹는 음식`, `최근 입력 음식`으로 분리했습니다. 고정 음식은 최대 6개, 최근 입력은 식사 구분별 최대 6개만 노출됩니다.
- 고정 음식 행에 해제 버튼을 추가해 잘못 고정한 음식은 식단 화면에서 바로 제거할 수 있게 했습니다.
- 회귀 테스트에 “식단 저장만으로 즐겨찾기가 늘어나지 않는다”는 검증과 수동 고정 음식 렌더링 검증을 추가했습니다.
- 검증 완료: 전체 unittest 26개, compileall, 주요 JS 문법 검사, `git diff --check`.

## 2026-05-28 v2.4.2 장소 장비 인사이트 고도화
- 장소별 인사이트에 등록 장비 대비 실제 사용 장비 비율을 계산하는 `equipment_coverage` 값을 추가했습니다.
- 등록 장비 비교 기준은 장비명과 장비 유형을 함께 사용하도록 보강해, 운동 입력에서 저장되는 장비 분류와 장소 장비 관리 데이터가 더 잘 연결되게 했습니다.
- `/locations/insights` 화면에는 장비활용률과 미사용 장비 목록을 노출하고, 미사용 장비 행은 별도 강조 스타일을 적용했습니다.
- 버전은 `VERSION`, `static/manifest.webmanifest`, `static/sw.js` 모두 `2.4.2`로 맞췄습니다.
- 검증 완료: 전체 unittest 26개, compileall, 주요 JS 문법 검사, `git diff --check`.

## 2026-05-28 v2.4.1 구조 고도화 및 모바일 UX 보강
- GitHub 기본 브랜치는 `main`으로 변경했고 기존 원격 `master`는 삭제했습니다.
- `routes/main.py`를 추가 분리했습니다. 오늘 운동 액션은 `routes/today_actions.py`, 식단/세트 수정은 `routes/entries.py`, 백업/샘플/삭제 입출력은 `routes/data.py`에서 등록합니다.
- `health_tracker/app_accounts.py`를 추가해 계정 조회, 관리자 대시보드 집계, 사용자 상태/비밀번호/메모 변경 헬퍼를 `app.py`에서 분리했습니다. 테스트에서 DB 경로를 바꾸는 흐름을 위해 DB provider 방식으로 연결했습니다.
- `static/styles.css`의 화면별 규칙을 `static/feature_pages.css`, 하단 반응형 규칙을 `static/responsive.css`로 분리했습니다. 레이아웃 템플릿과 서비스워커 캐시 목록도 같이 갱신했습니다.
- 오프라인 폼 큐는 `static/offline_queue.js`로 분리했습니다. `app.js`는 기존처럼 `queueOfflineForm`, `processOfflineQueue`를 호출합니다.
- 모바일 UX 보강으로 기록/분석/식단/장비 카드의 줄바꿈, 배지, 필터 폼, 액션 버튼 간격을 좁은 폭 기준으로 정리했습니다.
- 검증 완료: `python -m unittest discover -v`, `python -m compileall health_tracker tests`, `node --check static/app.js`, `node --check static/offline_queue.js`, `node --check static/workout_entry.js`.

## 2026-05-28 v2.4.0 반응형 UI 및 소스 분리 정리
- 인증 라우트는 `health_tracker/routes/auth.py`, 설정 라우트는 `health_tracker/routes/settings.py`로 분리했습니다. 기존 흐름은 테스트로 유지 확인했습니다.
- 공통 반응형 보강은 `static/ui_rebuild.css` 하단에 추가했습니다. 모바일/폴드 폭에서 카드, 버튼, 필터, 폼, 테이블이 한 줄로 눌리거나 겹치는 경우를 줄이는 방어 규칙입니다.
- `today/index.html`에서 루틴/운동 입력, 운동 기록, 식단 기록을 각각 `today/_workout_library_input.html`, `today/_workout_records.html`, `today/_meal_records.html`로 분리했습니다.
- `summaries/summary.html`에서 운동별 분석과 장비별 분석을 각각 `summaries/_exercise_summary.html`, `summaries/_equipment_summary.html`로 분리했습니다.
- 버전은 `VERSION`, `static/manifest.webmanifest`, `static/sw.js` 모두 `2.4.0`으로 맞췄습니다.
- 이번 작업 중 확인한 다음 정리 대상은 `health_tracker/app.py`, `static/styles.css`, `health_tracker/routes/main.py`, `static/app.js`입니다. 기능 분리 범위가 커서 별도 회귀 테스트 단위로 나누는 것이 맞습니다.
- 검증 완료: `python -m unittest discover -v`, `python -m compileall health_tracker tests`, `node --check static/app.js`, `node --check static/timers.js`, `node --check static/workout_entry.js`.

## 2026-05-28 v2.3.11 렌더링 병목 추가 점검
- 속도 병목 후보를 다시 점검했고, `today/index.html`이 템플릿 안에서 `grouped_sets_for_session(session.id)`를 직접 호출하던 부분을 제거했습니다.
- `today_context.py`에서 운동 모드일 때 `workout_groups`를 미리 구성해 템플릿에는 렌더링 데이터만 전달하도록 정리했습니다.
- 큰 분리 대상은 `today/index.html` 약 63KB, `summaries/summary.html` 약 48KB, `routes/main.py` 약 53KB로 확인했습니다.
- 조건 렌더링 범위 조정 중 운동 입력 영역이 빠지는 회귀를 테스트로 확인했고, 운동 입력/빠른 선택/장소 영역이 정상 출력되도록 복구했습니다.
- 검증: `python -m unittest discover -v`, `python -m compileall health_tracker tests`, `node --check static/app.js`, `node --check static/workout_entry.js` 통과.

## 2026-05-28 v2.3.10 운동 탭 로딩 최적화
- `/app?mode=workout` 진입 시 `build_today_context`가 식단, 전체 요약, 최근 기록 데이터를 모두 만들던 구조를 모드별 컨텍스트로 분리했습니다.
- 운동 모드에서는 운동 입력, 오늘 운동, 루틴, 회복, PR에 필요한 데이터만 실제 조회하고 식단/전체 전용 값은 안전한 기본값으로 둡니다.
- 오늘 템플릿에서 CSS로 숨기던 전체 요약/식단 큰 영역을 `{% if today_mode == 'overview' %}`, `{% if meal_mode %}` 조건 렌더링으로 전환했습니다.
- 첫 테스트에서 식단 조건 범위가 운동 기록 카드까지 덮어 운동명 일괄 수정 UI가 빠지는 회귀를 확인했고, 조건 범위를 분리해 수정했습니다.
- 검증: `python -m unittest discover -v`, `python -m compileall health_tracker tests` 통과.

## 2026-05-28 v2.3.9 모바일 운동 빠른 메뉴 겹침 수정
- 430px 이하 모바일 화면에서 `.workout-action-dock`, `.mobile-action-dock` sticky 위치를 `122px`로 조정해 상단 앱 메뉴와 겹치지 않게 했습니다.
- `#workout-input`, `#today-workout`, `#rest-timer`, 오늘 할 일, 운동 타이머 섹션에 `scroll-margin-top: 174px`를 적용해 빠른 메뉴 이동 시 큰 섹션 제목이 가려지지 않도록 했습니다.
- 모바일 운동 메뉴 겹침 방지 CSS 회귀 테스트를 추가했습니다.
- 검증: `python -m unittest discover -v`, `python -m compileall health_tracker tests`, `node --check static/app.js` 통과.

## 2026-05-28 v2.3.8 모바일 헤더 겹침 수정
- 430px 이하 모바일 화면에서 `.header`를 1열 2줄 구조로 바꿔 `피트니스 트래커`, 환영 문구, 버전 배지가 겹치지 않도록 수정했습니다.
- 모바일에서 `.tabs` sticky top 값을 새 헤더 높이에 맞춰 조정했습니다.
- 사용자 앱 헤더에 `header-meta`, `account-greeting`, `app-version`이 렌더링되는 회귀 테스트를 추가했습니다.
- 검증: `python -m unittest discover -v`, `python -m compileall health_tracker tests`, `node --check static/app.js` 통과.

## 2026-05-28 v2.3.7 관리자 운영 기능 확장
- `/admin`에 사용자 검색, 상태 필터, 정렬 폼을 추가했습니다. 필터는 전체/활성/비활성/조치 필요/미사용/기록 부족, 정렬은 가입순/최근 로그인순/최근 기록순/세트 많은순/이름순입니다.
- 조치 필요 사용자 섹션을 추가해 미사용, 기록 부족, DB 확인 필요, 비활성 계정을 대시보드 상단에서 바로 볼 수 있게 했습니다.
- `admin_audit_logs` 테이블을 추가하고 관리자 비밀번호 변경, 사용자 비밀번호 초기화, 활성/비활성, 메모 수정, 사용자 데이터 내보내기를 기록합니다.
- `/admin/users/<id>/export`를 추가해 사용자별 JSON 내보내기를 지원합니다. 원본 테이블과 관리자 상세에서 보는 사용 요약을 함께 포함합니다.
- 관리자 대시보드와 사용자 상세 템플릿을 정상 한글 문구로 다시 정리했고, 필터/액션 버튼 모바일 정렬 CSS를 추가했습니다.
- 검증: `python -m unittest discover -v`, `python -m compileall health_tracker tests`, `node --check static/app.js`, `node --check static/timers.js`, `node --check static/workout_entry.js`, `git diff --check` 통과.

## 2026-05-28 v2.3.6 관리자 현황 집계 수정
- 관리자 계정은 운동/식단 사용자 현황 대상이 아니므로 `build_admin_dashboard`에서 `role == "user"` 계정만 집계하도록 수정했습니다.
- `/admin/users/<id>` 상세도 사용자 계정만 허용하고 관리자 계정 접근은 `/admin?error=user_only`로 되돌립니다.
- 관리자 대시보드에 운영 체크포인트를 추가했습니다: 가입/활성, 기록 상태, 데이터 규모.
- 확인된 추가 관리 컨택포인트: 계정 가입/활성 관리, 비밀번호 초기화, 관리자 메모, 사용자별 최근 기록, 부위/장비 사용량, 저활동/미사용 사용자 확인.
- 검증: `python -m unittest discover -v`, `python -m compileall health_tracker tests`, `node --check static/app.js`, `git diff --check` 통과.

## 2026-05-28 v2.3.5 미리보기 UI 개선
- `/auth/preview` 화면을 단순 카드 나열에서 히어로, 모바일형 오늘 운동 샘플, 핵심 기능 요약, 기록/분석/장소/식단 카드 구조로 재구성했습니다.
- 미리보기 템플릿의 깨진 한글을 정상 문구로 교체했습니다.
- 모바일에서 히어로, 지표 카드, 기록 행이 한 줄에 눌리지 않도록 반응형 CSS를 추가했습니다.
- 검증: `python -m unittest discover -v`, `python -m compileall health_tracker tests`, `node --check static/app.js`, `git diff --check` 통과.

## 2026-05-28 v2.3.4 가입 전 미리보기 페이지
- `/auth/preview` 공개 페이지를 추가해 가입 전에도 오늘 운동, 기록, 분석, 장소/장비 흐름을 샘플로 확인할 수 있게 했습니다.
- 로그인/회원가입 화면에 미리보기 이동 버튼을 추가했습니다.
- 미리보기는 샘플 전용 화면이며 `<form>` 입력과 실제 DB 데이터, 관리자 화면 정보가 노출되지 않도록 테스트로 고정했습니다.
- 공개 접근은 `preview_page` GET 엔드포인트만 허용했고, 기존 앱/관리자 데이터 접근은 로그인 보호를 유지합니다.
- 검증: `python -m unittest discover -v`, `python -m compileall health_tracker tests`, `node --check static/app.js`, `node --check static/timers.js`, `node --check static/workout_entry.js`, `git diff --check` 통과.

## 2026-05-28 v2.3.3 인증 UX 및 관리자 비밀번호 변경
- 사용자/관리자 레이아웃 헤더에서 `계정명님 환영합니다`와 `v2.3.3` 버전을 별도 영역으로 분리했습니다.
- 로그인 탭 선택 상태를 더 진한 배경/흰색 글자로 바꿔 사용자/관리자 선택이 명확해졌습니다.
- 로그인 화면에는 로그인 폼만 남기고, 사용자 회원가입은 `/auth/signup` 전용 화면으로 분리했습니다.
- 사용자 로그인에는 “비밀번호를 잊으셨나요? 관리자에게 초기화를 요청하세요.” 문구를, 관리자 로그인에는 서버 관리자 문의 문구를 추가했습니다.
- `/admin/password`를 추가해 관리자 본인 비밀번호를 현재 비밀번호 확인 후 변경할 수 있게 했습니다.
- 관리자 비밀번호 변경 시 `accounts.db`의 관리자 계정 해시와 `workout.db`의 `settings_password_hash`를 함께 갱신합니다.
- 검증: `python -m unittest discover -v`, `python -m compileall health_tracker tests`, `node --check static/app.js`, `node --check static/timers.js`, `node --check static/workout_entry.js`, `git diff --check` 통과.

## 2026-05-28 v2.3.2 인증 화면 CSRF 수정
- `layouts/auth.html`은 앱 공통 JS를 로드하지 않으므로, 로그인/회원가입 폼의 CSRF hidden input을 `templates/auth/login.html`에서 직접 렌더링하도록 수정했습니다.
- 실제 로컬 HTTP에서 `/auth/login?mode=admin` 페이지의 CSRF 토큰 존재와 `admin / 1234` 로그인 후 `/admin` 진입을 확인했습니다.
- 로컬 `instance/workout.db`, `instance/accounts.db`의 관리자 비밀번호는 테스트 편의를 위해 `1234`로 맞췄습니다.
- 검증: `python -m unittest discover -v`, `python -m compileall health_tracker tests`, `git diff --check` 통과.

## 2026-05-28 v2.3.1 인증/앱/관리자 화면 분리
- `/`는 더 이상 오늘 운동 화면을 렌더링하지 않고, 세션 상태에 따라 `/auth/login`, `/app`, `/admin`으로 이동하는 라우터가 되었습니다.
- 오늘 운동 화면은 `/app`으로 이동했습니다. 기존 `url_for("index")` 내부 링크는 `/app`을 가리킵니다.
- 로그인 화면은 `templates/auth/login.html`과 `layouts/auth.html`로 분리해 앱 헤더/메뉴가 나오지 않게 했습니다.
- 관리자 화면은 `layouts/admin.html`을 사용하도록 분리해 사용자 앱 메뉴와 섞이지 않게 했습니다.
- 기존 `/login`은 `/auth/login`으로 보내는 호환 라우트로만 남겼고, `/auth/logout`과 `/logout` 모두 세션을 완전히 비웁니다.
- PWA `start_url`은 `/`로 변경했습니다. 서비스워커 캐시는 `workout-pwa-v2.3.1`입니다.
- 검증: `python -m unittest discover -v`, `python -m compileall health_tracker tests`, `node --check static/app.js`, `node --check static/timers.js`, `node --check static/workout_entry.js` 통과.

## 2026-05-28 v2.3.0 로그인 게이트 및 관리자 전용 화면 분리
- `/login`을 앱 첫 진입점으로 고정하고, 로그인 전 일반 페이지 접근은 로그인 화면으로 보내도록 변경했습니다.
- 관리자 계정은 `/admin` 및 관리자 세부 화면만 볼 수 있게 라우트 단계에서 차단했습니다. 관리자가 일반 앱 주소를 직접 열면 `/admin`으로 이동합니다.
- 사용자 계정은 기존 운동 앱 화면만 사용하고, 관리자 화면 직접 접근은 관리자 로그인 화면으로 돌리도록 분리했습니다.
- 로그인 화면은 관리자/사용자 탭을 유지하되 사용자 회원가입에는 비밀번호 확인 필드를 추가했습니다.
- 기본 관리자 계정이 먼저 보장되도록 수정했고, 첫 일반 사용자 계정은 기존 메인 운동 DB를 이어받도록 DB 매핑을 조정했습니다.
- 검증: `python -m unittest discover -v` 전체 24개 테스트 통과.

## 2026-05-28 v2.2.0 관리자/사용자 로그인 및 운영 대시보드

- `/login`을 관리자/사용자 탭으로 재구성하고, 사용자 탭에서 일반 사용자 회원가입을 지원합니다.
- `/admin`과 `/admin/users/<id>`를 추가해 관리자만 사용자별 사용량과 상세 기록 요약을 볼 수 있습니다.
- 관리자 상세에서 사용자 비밀번호 초기화, 비활성/활성 전환, 표시 이름/관리자 메모 저장을 처리합니다.
- 설정 화면의 계정 생성 UI는 관리자 대시보드 진입점으로 정리했습니다.
- 검증: 단위별 계정/관리자 테스트, 전체 회귀 테스트, 로그인/관리자/서비스워커 로컬 HTTP 확인을 통과했습니다.

## 2026-05-27 v2.1.0 2인 계정 분리

- 계정별 데이터 분리를 위해 `health_tracker/services/accounts.py`를 추가했습니다.
- 기본 `admin` 계정은 기존 DB를 계속 사용하고, 추가 계정은 `instance/accounts/user_<id>.db` 형태의 별도 DB를 사용합니다.
- 설정 화면에서 계정을 생성하고 `/login`, `/logout`으로 계정을 전환할 수 있습니다.
- 기존 설정 비밀번호를 저장하면 기본 `admin` 계정의 비밀번호도 함께 동기화됩니다.
- 검증: 계정별 데이터 분리 테스트, 전체 회귀 테스트, 로그인/서비스워커 로컬 HTTP 확인을 통과했습니다.

## 2026-05-27 v2.0.7 PWA 메타 태그 경고 수정

- `health_tracker/templates/layouts/base.html`에 `<meta name="mobile-web-app-capable" content="yes">`를 추가했습니다.
- 기존 `apple-mobile-web-app-capable`은 iOS Safari 호환 목적으로 유지했습니다.
- 검증: 컴파일, 전체 회귀 테스트, 로컬 HTTP head/service worker 확인을 통과했습니다.

## 2026-05-27 v2.0.6 장비 카테고리 머신 분리

- 공통 장비 카테고리에서 `머신`을 제거하고 `핀머신`, `플레이트로디드머신`을 추가했습니다.
- 기존 `머신` 데이터는 초기화 마이그레이션에서 `핀머신`으로 정리되며, 스미스/플레이트 로디드 계열 텍스트는 `플레이트로디드머신`으로 정규화됩니다.
- 오늘 운동, 기록 검색, 장소 장비 관리, 운동 수정 select가 긴 장비명을 담을 수 있도록 장비 select 전용 글자 크기와 padding을 조정했습니다.
- 검증: 컴파일, JS 문법 검사, 전체 회귀 테스트, 운동/기록 검색/서비스워커 HTTP 확인을 통과했습니다.

## 2026-05-26 v2.0.5 운동 완료 타이머 재복원 방지

- `v2.0.4`는 완료 submit 순간에는 타이머를 0으로 만들었지만, 리다이렉트 후 `data-initial-duration`이 저장된 운동시간을 다시 타이머 표시로 복원하는 문제가 있었습니다.
- 완료 시 `completedReset` 플래그를 localStorage에 남겨, 완료된 날짜는 저장된 운동시간과 별개로 진행 타이머 표시를 `00:00:00`으로 유지하도록 수정했습니다.
- HTML이 최신 템플릿을 못 받은 배포 상태에서도 `/sessions/<id>/complete` form action을 감지해 같은 동작을 하도록 fallback을 추가했습니다.
- 검증: 컴파일, JS 문법 검사, 전체 회귀 테스트, 운동/서비스워커 HTTP 200 확인을 통과했습니다.

## 2026-05-26 v2.0.4 운동 완료 시 타이머 표시 리셋

- 운동 완료 버튼을 누르면 저장된 운동시간은 유지하고, 브라우저 로컬 타이머 표시만 `00:00:00`으로 리셋되도록 했습니다.
- `data-workout-complete-form` submit 시 `resetWorkoutClockDisplayOnly("운동 완료")`를 실행하며, 별도 duration 저장 API는 호출하지 않습니다.
- 검증: 컴파일, JS 문법 검사, 전체 회귀 테스트, 운동/서비스워커 HTTP 200 확인을 통과했습니다.

## 2026-05-26 v2.0.3 오늘 식단 공통 selector 덮어쓰기 수정

- `v2.0.2`의 식단 전용 CSS가 기존 `.record-list > .record-card:not(...)` 공통 selector보다 약해서 실제 화면에서 2열 규칙이 계속 적용됐습니다.
- 공통 selector에서 `meal-record-card`를 제외하고, `ui_rebuild.css` 하단에 `.record-list > .meal-record-card` 1열 고정 override를 추가했습니다.
- 검증: 식단 회귀 테스트, CSS 무결성 테스트, 식단 화면 HTTP 200 확인을 통과했습니다.

## 2026-05-26 v2.0.2 오늘 식단 리스트 UI 수정

- 오늘 식단 리스트가 공통 `.record-list > .record-card` 2열 규칙의 영향을 받아 식단 그룹/음식 행 배치가 깨지던 문제를 수정했습니다.
- 식단 그룹 카드에 `meal-record-card`, 음식 행에 `meal-record-item` 클래스를 추가하고 `today-meal-section` 전용 grid/버튼/입력폼 규칙을 `ui_rebuild.css`에 추가했습니다.
- 검증: 컴파일, JS 문법 검사, 전체 회귀 테스트, 식단/운동 HTTP 200 확인, CSS 무결성 검증을 통과했습니다.

## 2026-05-26 v2.0.1 부위별 분석 카드 겹침 수정

- 기록 탭의 부위별 분석 카드에서 날짜(`cat-stat-unit`)와 운동시간/칼로리 줄이 같은 `meta` grid area에 배치되어 겹치던 문제를 수정했습니다.
- `summary.html`에 `cat-stat-period`, `cat-stat-detail` 클래스를 추가하고, `ui_rebuild.css`에서 `period/detail/pr` 영역을 분리했습니다.
- 검증: 컴파일, 기록/분석 렌더링 테스트, CSS 중괄호/깨진 selector 테스트, 일별/주간 분석 HTTP 200 확인을 통과했습니다.

## 2026-05-26 v2.0.0 릴리즈 준비 완료

- 앱 버전을 `2.0.0`으로 전환하고 manifest/service worker cache도 같은 기준으로 갱신했습니다.
- 2.0 전 준비 정리로 `app.py`의 설정, 데이터 정리/복원, 요약 조회, 연간 export, 최근 세션 조회 로직을 서비스 계층으로 분리했습니다.
- README 기능 목록을 현재 실사용 범위에 맞춰 운동/식단, 위치/장비, 분석, 잠금, 백업/복원 중심으로 업데이트했습니다.
- 최종 검증은 전체 회귀 테스트, 컴파일, JS 문법 검사, diff 검사, 핵심 HTTP 렌더링 확인으로 진행합니다.

## 2026-05-26 v1.25.17 최근 세션 조회 서비스 분리

- `app.py`에 있던 최근 운동 세션 SQL을 `health_tracker/services/workout.py`의 `list_recent_sessions_from_db`로 이동했습니다.
- `/api/sessions`가 사용하는 기존 wrapper는 유지해 라우트 변경 없이 app.py SQL 본문을 줄였습니다.
- 검증: `python -m compileall health_tracker tests`, 메인/운동·식단 회귀 테스트, `/api/sessions`와 오늘 운동 HTTP 200 확인을 통과했습니다.

## 2026-05-26 v1.25.16 연간 export 서비스 분리

- `app.py`의 연간 JSON payload 조립, CSV 직렬화, 연간 운동/식단 CSV export 본문을 `health_tracker/services/yearly.py`로 이동했습니다.
- 라우트가 쓰는 기존 함수명은 wrapper로 유지해 호출부 변경 없이 app.py 책임을 줄였습니다.
- 검증: `python -m compileall health_tracker tests`, 연간 QA/메인 페이지 회귀 테스트, 연간 JSON/운동 CSV/식단 CSV HTTP 200 확인을 통과했습니다.

## 2026-05-26 v1.25.15 요약 조회 서비스 분리

- `app.py`에 있던 `get_day_summary`, `list_daily_summary`, `list_weekly_summary` SQL 본문을 `health_tracker/services/summary.py`로 이동했습니다.
- 분석/기록 화면의 데이터 조회 책임을 서비스 계층으로 넘기고, app.py는 기존 함수명 wrapper만 유지했습니다.
- 검증: `python -m compileall health_tracker tests`, 샘플 데이터/메인 페이지/분석 메뉴 회귀 테스트, 일별/주별/월별 분석 HTTP 200 확인을 통과했습니다.

## 2026-05-26 v1.25.14 데이터 복원 로직 분리

- `app.py`의 전체 데이터 import/복원 로직을 `health_tracker/services/export.py`의 `import_all_data_to_db`로 이동했습니다.
- export와 import가 같은 `EXPORT_TABLES`를 쓰도록 정리해 테이블 순서 중복을 제거했습니다.
- 연간 JSON export 라우트의 `json` 암묵 의존성을 `routes/main.py` 직접 import로 고쳤습니다.
- 검증: `python -m compileall health_tracker tests`, 전체 20개 회귀 테스트, 설정/데이터센터/연간 JSON export/서비스워커 HTTP 200 확인을 통과했습니다.

## 2026-05-26 v1.25.13 데이터 정리 서비스 분리

- `app.py`에 있던 전체 데이터 삭제 백업, 빈 운동 세션 삭제, 내부 점검 데이터 삭제 로직을 `health_tracker/services/data_maintenance.py`로 이동했습니다.
- 설정 화면/DB 초기화/라우트가 쓰는 기존 함수명은 wrapper로 유지해 호출부 변경 범위를 줄였습니다.
- 검증: `python -m compileall health_tracker tests`, 샘플 데이터/위험 삭제 확인/설정 잠금 회귀 테스트, 설정/데이터센터 HTTP 200 확인을 통과했습니다.

## 2026-05-26 v1.25.12 설정 서비스 분리

- `app.py`에 있던 앱 설정 조회/저장과 설정 비밀번호 해시/검증 로직을 `health_tracker/services/settings.py`로 분리했습니다.
- `app.py` wrapper는 기존 라우트 의존성을 유지하되, 세션 unlock 상태 처리만 담당하도록 줄였습니다.
- 검증: `python -m compileall health_tracker tests`, 설정 비밀번호 잠금/재설정, 비밀번호 해시, 방문자 read-only 보안 회귀 테스트를 통과했습니다.

## 2026-05-26 v1.25.11 분석 요약 내비게이션 분리

- `summaries/summary.html` 상단의 기록/분석 내비게이션 조건문을 `summaries/_summary_nav.html`로 분리했습니다.
- 일별 기록과 분석 화면의 공통 진입부를 partial화해 긴 요약 템플릿의 책임을 조금 더 줄였습니다.
- 검증: `python -m compileall health_tracker tests`, 메인 페이지/메뉴 분리 회귀 테스트, 일별/주간 분석 HTTP 200 확인을 통과했습니다.

## 2026-05-26 v1.25.10 오늘 식단 행 분리

- `today/index.html`의 식단 음식별 읽기/수정/삭제 행을 `today/_meal_record_item.html`로 분리했습니다.
- 운동 세트 행 분리와 같은 패턴으로 식단 반복 구조를 partial화해 `today/index.html`의 길이를 추가로 줄였습니다.
- 검증: `python -m compileall health_tracker tests`, 식단/메인 렌더링 회귀 테스트, 식단 모드 HTTP 200 확인을 통과했습니다.

## 2026-05-26 v1.25.9 오늘 운동 세트 행 분리

- `today/index.html`의 세트별 읽기/수정/복사/삭제 행을 `today/_workout_set_item.html`로 분리했습니다.
- 운동 기록 카드 내부 반복 구조를 partial로 빼서 `today/index.html` 과밀도를 낮췄습니다.
- 검증: `python -m compileall health_tracker tests`, `node --check static\app.js`, 운동/식단 핵심 회귀 테스트, 오늘 운동 HTTP 200 확인을 통과했습니다.

## 2026-05-26 v1.25.8 템플릿 구조 정리

- 2.0 준비 전 코드 정리로 긴 템플릿 블록을 partial로 분리했습니다.
- `summaries/summary.html`의 날짜별 기록 섹션을 `summaries/_daily_records.html`로 이동했습니다.
- `today/index.html`의 운동 바로 선택 패널을 `today/_workout_quick_panel.html`로 이동했습니다.
- 렌더링 유지 검증: `/?date=2026-05-26&mode=workout`, `/summaries/daily?days=7`, `/static/ui_rebuild.css` HTTP 200 확인.
- 회귀 검증: `test_fold_ui_regression_markers_render`, `test_main_pages_render` 통과.

## 2026-05-26 v1.25.7 코드 정리

- 2.0 준비 전 코드 정리로 QA 리포트의 오래된 `/sw.js 캐시 v1.4.0 기준` 문구를 현재 `app_version` 표시로 변경했습니다.
- `static/ui_rebuild.css`의 `v1.25.5` 고정 주석을 최종 UI override 파일 역할에 맞는 일반 주석으로 바꿨습니다.
- `tests/test_app_flows.py`에 `StaticAssetIntegrityTest`를 추가해 `styles.css`, `rules.css`, `ui_rebuild.css`의 중괄호 균형과 과거 UI 붕괴 원인이었던 `.next-set-advice-row {.next-set-advice-row` 패턴을 검사합니다.
- service worker precache 테스트에서 `/static/ui_rebuild.css` 포함 여부를 직접 확인하도록 보강했습니다.
- 이번 정리는 중복 CSS를 무리하게 삭제하지 않았습니다. `ui_rebuild.css`는 현재 후순위 override 역할이라 삭제/병합 전에 브라우저 computed style 검증이 필요합니다.

## 2026-05-26 UI 회귀 원인과 수정 내역

- 잘못된 점:
  - `static/styles.css` 안에 `.next-set-advice-row {.next-set-advice-row {`처럼 selector와 중괄호가 중복으로 들어간 문법 오류가 있었습니다.
  - 이 오류 때문에 해당 지점 뒤에 작성된 캘린더, 운동 라이브러리, 설정, 기록 관련 CSS가 브라우저에서 정상 적용되지 않았습니다.
  - 결과적으로 월간 캘린더가 7열 그리드가 아니라 세로 텍스트 목록처럼 보였고, 운동 라이브러리/기록/분석/데이터 관리 화면의 카드와 버튼 간격도 깨져 보였습니다.
  - 이전 수정에서 깨진 화면을 CSS로 덮는 데 집중했고, 원본 CSS 문법 오류까지 먼저 검증하지 못한 것이 문제였습니다.

- 수정한 내용:
  - 깨진 selector를 `.next-set-advice-row {`로 바로잡았습니다.
  - `static/styles.css`, `static/rules.css`, `static/ui_rebuild.css` 전체의 중괄호 균형을 검사해 CSS 문법 구조가 닫혀 있는지 확인했습니다.
  - `static/ui_rebuild.css`에 캘린더, 운동 라이브러리, 운동 입력 빠른 선택, 날짜별 기록, 부위별 분석, 데이터 관리/QA 카드의 공통 UI 보정 규칙을 추가했습니다.
  - `VERSION`, `static/manifest.webmanifest`, `static/sw.js`를 `v1.25.6`으로 올려 PWA와 브라우저 캐시가 이전 깨진 CSS를 계속 사용하지 않도록 했습니다.

- 검증한 내용:
  - `/calendar`, `/exercises/library`, `/summaries/daily`, `/summaries/weekly`, `/settings`, `/sw.js` HTTP 200 확인.
  - 브라우저 DOM 기준으로 주요 화면의 `overflowX = 0` 확인.
  - 캘린더는 `display:grid`와 7열 grid가 적용되는 것을 확인.
  - 운동 라이브러리와 기록 카드는 카드/그리드 레이아웃이 적용되는 것을 확인.
  - `.\.venv\Scripts\python.exe -m compileall health_tracker tests` 통과.
  - `.\.venv\Scripts\python.exe -m unittest discover -v` 19개 테스트 통과.

- 재발 방지 기준:
  - UI가 광범위하게 무너졌을 때는 먼저 CSS 문법 오류와 로드 순서를 확인합니다.
  - 새 CSS를 추가하기 전에 `styles.css`, `rules.css`, `ui_rebuild.css`의 중괄호 균형을 검사합니다.
  - 공통 UI 보정 후에는 실제 브라우저 DOM에서 `display`, `gridTemplateColumns`, `padding`, `overflowX`를 확인합니다.
  - PWA 앱은 CSS/JS/manifest/service worker 버전을 함께 올려 캐시 문제를 같이 차단합니다.

## 2026-05-26 v1.25.6 전체 UI 점검

- 업데이트 후 캘린더가 세로 텍스트처럼 무너진 핵심 원인은 `static/styles.css`의 `.next-set-advice-row {.next-set-advice-row {` 중괄호 오류였습니다. 이 줄 때문에 뒤쪽 CSS 블록이 브라우저에서 정상 적용되지 않았습니다.
- 오류를 `.next-set-advice-row {`로 바로잡고 `styles.css`, `rules.css`, `ui_rebuild.css`의 중괄호 균형을 검사했습니다.
- `static/ui_rebuild.css`에 캘린더, 운동 라이브러리, 빠른 운동 선택, 날짜별 기록, 부위별 분석, 데이터 관리/QA 카드의 공통 UI 보정 규칙을 추가했습니다.
- 브라우저 DOM 기준으로 `/calendar`, `/exercises/library`, `/summaries/daily`, `/summaries/weekly`의 주요 그리드와 카드가 적용되고 가로 overflow가 0인 것을 확인했습니다.
- 버전, manifest, service worker cache를 `v1.25.6`으로 올려 PWA 캐시가 예전 깨진 CSS를 잡고 있지 않게 했습니다.

## 2026-05-26 추가 UI 리빌딩 메모

- `v1.25.5` 보정 CSS가 일부 화면에서 캐시/로드 순서 영향으로 바로 반영되지 않는 문제가 있어 `static/ui_rebuild.css`를 별도 파일로 분리하고 `rules.css` 뒤에서 마지막으로 로드되게 했습니다.
- 캡처에서 보인 운동 입력, 세트 빌더, 최근/주별/일별 기록, 분석 상세행, 부위별 분석처럼 텍스트가 한 줄로 붙는 UI를 카드/그리드/배지 구조로 다시 고정했습니다.
- 브라우저 DOM 검증에서 `/summaries/weekly`의 `.detail-row`가 `display:grid`, `padding:10px`, `border-radius:8px`로 적용되는 것을 확인했습니다.
- 이후 UI 작업은 공통 CSS를 추가한 뒤 실제 브라우저에서 최종 로드 순서와 computed style까지 확인해야 합니다.

이 문서는 VS Code/CLI를 껐다가 새 Codex 세션을 시작했을 때 바로 이어받기 위한 작업 메모입니다.

## 2026-05-26 작업 기록

- `v1.25.5` UI 리빌딩:
  - 사용자가 제보한 운동 입력, 최근 기록, 주별 기록, 부위별 분석, 일별 추이의 텍스트 붙음/버튼 깨짐/세트 행 불균형을 공통 CSS 레이어로 재정리했습니다.
  - 운동 바로 선택은 탭 버튼과 운동 후보 버튼을 분리하고, 긴 운동명은 자연스럽게 줄바꿈되도록 했습니다.
  - 세트 빌더는 세트 번호, 입력 필드, 고급 옵션, 복사/삭제 액션 영역을 명확히 분리했습니다.
  - 기록/분석 리스트는 날짜/기간 제목과 지표 뱃지를 grid로 나눠 단순 텍스트 나열처럼 보이지 않게 했습니다.
  - `styles.css`, `rules.css`, `app.js`, `timers.js`, `workout_entry.js`에 앱 버전 쿼리를 붙여 서비스워커/브라우저 캐시가 예전 UI를 계속 보여주는 문제를 줄였습니다.
  - 검증: `.venv\Scripts\python.exe -m compileall health_tracker tests`, `.venv\Scripts\python.exe -m unittest discover -v` 19개 테스트 통과. 기본 Python은 Flask 미설치라 테스트 실패하므로 가상환경 Python을 사용해야 합니다.
- UI 관리 반성 및 다음 작업 기준:
  - 이번 UI 보정은 공통 CSS를 넓게 덮어쓰면서 실제 화면별 버튼/입력칸/리스트 구조를 충분히 확인하지 못해, 사용자가 보기 어려운 상태가 반복됐습니다.
  - 앞으로 UI 수정은 반드시 대상 URL을 먼저 명시하고 `운동 입력`, `기록 검색`, `날짜별 기록`, `식단`, `분석`처럼 화면 단위로 DOM 구조를 확인한 뒤 수정합니다.
  - 버튼은 용도별로 `탭 버튼`, `후보 선택 버튼`, `행 액션 버튼`, `폼 제출 버튼`을 분리해 같은 화면 안에서 크기/테두리/배치가 섞이지 않게 관리합니다.
  - 리스트는 단순 `텍스트 나열` 금지입니다. 각 행은 제목, 메타 정보, 핵심 값, 액션 영역을 명확히 분리하고 모바일에서는 세로 배치로 무너지지 않게 합니다.
  - `NOTES.md`는 작업이 끝날 때마다 항상 갱신합니다. 버전 변경이 없더라도 UI 검증/사용자 지적/남은 리스크를 기록합니다.
- `v1.25.4` 버튼/날짜별 기록 UI 재정리:
  - 운동 바로 선택의 최근/즐겨찾기/루틴 탭, 운동 후보 버튼, 기본 프로그램 버튼을 같은 버튼 체계로 통일했습니다.
  - 세트 복사/삭제 버튼의 폭과 높이를 다시 맞춰 운동 입력칸과 다른 버튼처럼 보이지 않게 했습니다.
  - 날짜별 기록 리스트를 날짜 헤더와 지표 카드가 분리된 형태로 재구성했습니다.
- `v1.25.3` 입력/기록 리스트 재보정:
  - 오늘 운동 입력의 운동명/장비/세트 행/복사/삭제 버튼 배치를 실제 폼 구조 기준으로 다시 잡았습니다.
  - 기록 검색 결과 템플릿을 날짜/장소/장비 메타 영역과 중량/횟수 값 영역으로 분리했습니다.
  - 오늘 기록 수정 행의 버튼 영역을 grid 기반으로 보정해 모바일에서 버튼이 깨지지 않도록 했습니다.
- `v1.25.2` 전체 리스트 UI 보정:
  - 기록/분석/식단/더보기에서 쓰는 `detail-row`, `ex-rank-item`, `ex-item`, 식단 일자/주차 항목, 누락/템플릿 항목을 카드형 박스 UI로 정리했습니다.
  - 모바일에서 목록 값, 배지, 버튼이 한 줄에 붙지 않도록 grid 기반 세로 재배치를 추가했습니다.
  - 앱 버전, manifest, service worker 캐시를 `v1.25.2`로 갱신했습니다.
- `v1.25.1` UI 긴급 보정:
  - 신규 기록 점검/QA 리포트 CSS의 범용 selector를 전용 클래스 기반으로 좁혀 다른 표/목록 UI에 영향이 가지 않도록 수정했습니다.
  - 공통 `summary-grid`, `detail-list`, `detail-row`, `table-wrap`, `table`의 모바일 폭/줄바꿈/가로 스크롤 처리를 보강했습니다.
  - 앱 버전, manifest, service worker 캐시를 `v1.25.1`로 갱신했습니다.
- `v1.19.0`~`v1.25.0` 연속 개발:
  - 오늘 운동 세트 입력에서 세트 타입/RPE/메모를 `고급` 접힘 영역으로 이동해 기본 입력 흐름을 간소화했습니다.
  - `services/data_cleanup.py`를 추가해 운동명 중복 후보와 이상 세트 후보를 기록 점검 화면에서 확인하도록 했습니다.
  - 기록 점검 화면에 정리 후보 UI를 추가해 누락일, 중복명, 과도한 중량/반복/RPE를 같은 흐름에서 점검합니다.
  - `services/release_readiness.py`를 추가해 QA 리포트에서 2.0 준비 상태를 점수와 체크리스트로 확인하게 했습니다.
  - 입력 UI/정리 후보/릴리즈 준비도 회귀 테스트 마커를 추가하고 앱 버전, manifest, service worker 캐시를 `v1.25.0`으로 갱신했습니다.
- `v1.18.0` 소스 정리 및 QA:
  - `services/summary_context.py`, `services/settings_context.py`를 추가해 분석/설정 화면 컨텍스트 생성을 라우트에서 분리했습니다.
  - `today/_rule_cards.html`, `summaries/_rule_report.html` partial을 추가해 룰셋 UI 블록을 템플릿 본문에서 분리했습니다.
  - `static/rules.css`를 추가하고 `base.html`, service worker 캐시에 반영해 룰셋 스타일을 분리했습니다.
  - 전체 테스트, JS 문법 검증, 주요 HTTP 렌더링 확인 후 앱 버전/manifest/service worker를 `v1.18.0`으로 갱신했습니다.
- `v1.17.0` 운동 지식 룰셋:
  - `services/exercise_rules.py`를 추가해 부위별 주간 권장 세트 범위, RPE 기반 조정, 권장 휴식시간, 대체 운동 후보를 로컬 룰셋으로 계산합니다.
  - 오늘 운동 화면에 `운동 룰셋` 카드를 추가해 부족/과다/적정 부위와 다음 액션을 보여줍니다.
  - 주간 분석 화면에 `운동 지식 룰셋` 섹션을 추가해 실제 기록과 권장 범위를 비교합니다.
  - 앱 버전, manifest, service worker 캐시를 `v1.17.0`으로 갱신했습니다.
- `v1.16.0` A/B/C 고도화 및 소스 분산:
  - A: `services/smart_workout.py`와 `static/workout_entry.js`를 추가해 운동명 선택 시 이전 기록/설정 기반으로 부위, 장비, 세트수, 무게, 횟수를 자동 채움 처리했습니다.
  - B: `services/personal_coach.py`를 추가해 오늘 화면의 `다음 액션` 패널에서 부족한 부위, 회복 확인, 식단 보강, 분석 확인을 제안합니다.
  - C: 설정 화면에 개인 사용 안전 상태를 추가해 관리자 잠금, 현재 세션 권한, 자동 백업 상태를 확인하도록 했습니다.
  - 구조: `services/today_context.py`로 오늘 화면 렌더링 컨텍스트를 분리해 `routes/main.py`의 `/` 라우트를 얇게 만들었습니다.
  - 앱 버전, manifest, service worker 캐시를 `v1.16.0`으로 갱신하고 `workout_entry.js`를 PWA 캐시에 포함했습니다.
- `v1.15.0` 오늘 운동 간소화:
  - 오늘 운동 모드 상단을 `오늘 할 일`로 재구성해 다음 입력, 마지막 기록, 휴식 타이머, 추천 운동을 한 번에 확인하게 했습니다.
  - 운동 입력 폼을 기본 접힘 상태로 바꾸고, 운동 추가/추천 적용/최근 운동 선택 시 자동으로 열리도록 `static/app.js` 흐름을 정리했습니다.
  - 운동 장소 패널은 현재 장소 중심으로 압축하고, 최근 운동/도구/계획은 접힘 보조 영역으로 낮춰 모바일 첫 화면 부담을 줄였습니다.
  - 앱 버전, manifest, service worker 캐시를 `v1.15.0`으로 갱신했습니다.
- `v1.14.0` 기능/분석 UI 고도화:
  - `services/progressive_overload.py`를 추가해 다음 세트 추천과 운동별 과부하 상태 분석을 구현했습니다.
  - `services/muscle_balance.py`를 추가해 최근 7일 부위별 세트/볼륨/유산소 분포를 계산합니다.
  - 오늘 운동 입력에 다음 세트 추천 카드와 추천값 적용 버튼을 연결했습니다.
  - 분석 > 운동별 화면에 과부하 분석 카드와 부위 밸런스 히트맵을 추가했습니다.
  - 더보기에 헬스장 도구 섹션과 `/tools/plate-calculator` 독립 페이지를 추가했습니다.
  - 검증: `python -m compileall health_tracker tests`, `node --check static\app.js`, `python -m unittest discover -v` 19개 테스트 통과.
- `v1.13.0` DB/운동 설정 분리:
  - DB schema, index, migration성 컬럼 보정, 식단 legacy 보정, 장소 bootstrap 호출을 `health_tracker/database/schema.py`로 분리했습니다.
  - 운동 세트 순서 변경과 운동 생성 helper를 `services/workout.py`로 이동했습니다.
  - 운동 메모/휴식시간/즐겨찾기/장비/목표 설정 로직을 `services/exercise_settings.py`로 분리했습니다.
  - `app.py`는 `3555`라인에서 `3200`라인까지 줄었습니다.
  - 검증: `python -m compileall health_tracker tests`, `python -m unittest discover -v` 19개 테스트 통과.
- `v1.12.0` app.py 추가 경량화:
  - 추천 세션, 운동 부위 추천, 회복 체크인, readiness, 일일 코칭, 적응형 추천을 `services/coaching.py`로 분리했습니다.
  - 루틴 템플릿 적용/저장/삭제와 운동 계획 생성/요약/기본 프로그램 적용을 각각 `services/routine.py`, `services/workout_plan.py`로 분리했습니다.
  - 체성분/진행 사진 로직을 `services/body.py`로 분리하고, 식단 템플릿/복사/자주 쓰는 식단 조합 로직을 `services/meal.py`로 이동했습니다.
  - `app.py`는 `4378`라인에서 `3555`라인까지 줄었습니다.
  - 검증: `python -m compileall health_tracker tests`, `python -m unittest discover -v` 19개 테스트 통과.
- `v1.11.0` 소스트리 리빌딩:
  - `app.py`에서 날짜/칼로리/샘플 데이터/캘린더/부위 분석/기록 검색/장비 분석/PR 조회 로직을 서비스 모듈로 분리했습니다.
  - 오늘 운동 화면의 운동 시간, 휴식 타이머, 장소 패널을 partial 템플릿으로 분리했습니다.
  - 운동 시간/휴식 타이머 스크립트를 `static/timers.js`로 분리하고 서비스워커 캐시에 반영했습니다.
  - 검증: `python -m compileall health_tracker tests`, `node --check static\app.js`, `node --check static\timers.js`, `python -m unittest discover -v` 19개 테스트 통과.
- `v1.10.0` 하드코딩 제거 1차:
  - 앱 기본값 설정 서비스를 추가하고 `app_settings` 기반으로 휴식 타이머, 기본 세트 수, 입력 힌트, 세트 타입, 목표 기본값을 조회/저장하게 했습니다.
  - 설정 화면에 앱 기본값 관리 섹션을 추가했습니다.
  - 오늘 운동 템플릿과 JS 세트 행 생성이 같은 설정값을 사용하도록 연결했습니다.
  - 일간 기록/기록 점검 기간 옵션과 기본 페이지 크기를 설정값으로 연결했습니다.
- `v1.9.8` 휴식 타이머 동작 수정:
  - 운동 모드 표시 순서에서 휴식 타이머를 운동 시간 바로 아래로 올렸습니다.
  - 세트 저장 후 `rest=90` 파라미터로 타이머가 자동 시작되던 흐름을 제거했습니다.
  - 이제 휴식 타이머는 60초/90초/120초/타이머 시작 버튼을 직접 눌렀을 때만 동작합니다.
- `v1.9.7` 운동 장소 카드 UI 보정:
  - 현재 장소 아래 장비 카테고리 칩 영역을 별도 박스로 분리하고 아래 최근 운동 목록과 간격/구분선을 추가했습니다.
  - 장소 안내 문구를 실제 동작에 맞게 수정했습니다.
- `v1.9.6` 운동명 수정/장비 표시 보강:
  - 오늘 운동 카드에서 운동명을 세트별이 아니라 같은 운동 그룹 단위로 일괄 수정할 수 있게 했습니다.
  - 운동별 기본 장비 설정값을 카드 헤더와 빠른 운동 선택 버튼에 같이 보여주도록 했습니다.
  - 세트 수정 폼이 열릴 때 입력칸이 밀리는 문제를 줄이도록 편집 레이아웃을 정리했습니다.
- `v1.9.5` 운동 입력 UX 보정:
  - 휴식 타이머를 운동 시간 카드 바로 아래로 이동했습니다.
  - 장비 카테고리는 장소와 무관하게 `바벨`, `덤벨`, `머신`, `케이블`, `프리웨이트`, `맨몸`, `유산소기구` 전체가 항상 보이게 수정했습니다.
  - 장소별 제한은 운동명 후보에만 적용되도록 안내 문구를 정리했습니다.
- `v1.9.4` 장소별 운동 입력 후보 제한:
  - 오늘 운동 입력의 운동명 datalist, 최근 세트, 운동 통계, 즐겨찾기, 루틴 목록을 선택 장소 기준으로 제한했습니다.
  - 다른 장소에서만 입력한 운동명은 현재 장소의 입력 후보에 보이지 않게 했습니다.
  - 루틴 저장 시 원본 세션의 장소도 함께 저장하도록 했습니다.
- `v1.9.3` 장비 카테고리 정규화:
  - 장비 후보에 운동명이나 세부 장비명이 섞이지 않도록 저장/조회/장소 동기화 단계에서 카테고리로 정규화했습니다.
  - 장소 장비 관리는 자유 텍스트 입력 대신 장비 카테고리 선택 방식으로 바꿨습니다.
  - `스미스 머신`, `런닝머신` 등 기존 세부 장비명은 `머신`, `유산소기구`로 정리되도록 했습니다.
- `v1.9.2` 장비 목록 보강:
  - 기본 장비 목록에 `프리웨이트`를 추가했습니다.
  - 오늘 운동 입력/수정/검색 fallback과 QA 더미데이터 장비 후보에 같은 장비 구성을 반영했습니다.
  - 장소 장비가 이미 있는 경우에도 `프리웨이트`는 공통 후보로 표시되게 보정했습니다.
- `v1.9.1` 장소별 장비 필터:
  - 오늘 운동의 장비 선택 목록을 선택 장소에 자동 수집된 장비 우선으로 변경했습니다.
  - 장소 장비가 하나라도 있으면 기본 장비 전체 목록을 섞지 않고 해당 장소 장비만 보여줍니다.
  - 신규 장소처럼 장비가 없을 때만 기본 장비 목록을 fallback으로 표시합니다.
- `v1.9.0` 고도화:
  - 더보기 화면을 섹션형 정보 구조로 재정리했습니다.
  - `데이터 센터`, `장소 인사이트`, `실행 인사이트` 화면을 추가했습니다.
  - 현재 운동 장소 기준 빠른 운동 불러오기를 오늘 운동 화면에 추가했습니다.
  - 장소별 운동/장비 사용, 데이터 상태, 백업/내보내기, 분석 신뢰도 기반 점검 흐름을 연결했습니다.
- `v1.8.0` 더보기 기능 추가:
  - `기록 점검` 화면을 추가해 분석 신뢰도, 누락일, 주요 데이터 수를 확인할 수 있게 했습니다.
  - `식단 템플릿` 화면을 추가해 저장된 템플릿 적용/삭제와 최근 식단 기반 템플릿 저장을 관리할 수 있게 했습니다.
  - 더보기 카드와 PWA 캐시에 신규 화면을 반영했습니다.
- `v1.7.6` 세트 입력 UI 보정:
  - 운동 입력의 무게/횟수 입력칸 기준선이 어긋나 보이던 문제를 수정했습니다.
  - 무게 단위와 kg 미리보기 줄 때문에 생기던 높이 차이를 세트 입력 전용 CSS로 맞췄습니다.
- `v1.7.5` 장소 삭제:
  - 기록이 없는 장소는 운동 장소 관리에서 완전 삭제할 수 있게 했습니다.
  - 기록이 연결된 장소는 기존 기록 보호를 위해 비활성화만 가능하게 유지했습니다.
- `v1.7.4` 장소 추가 UI 보정:
  - 장소 추가 입력칸이 grid 안에서 겹치지 않도록 input 폭과 최소 폭을 보정했습니다.
  - 기본 장소 체크박스가 너무 크게 보이지 않도록 장소 관리 화면 전용 크기를 적용했습니다.
- `v1.7.3` 운동 장소 관리 재정리:
  - 장소 카드 기본 화면은 요약과 장비 칩만 보이게 단순화했습니다.
  - 장소 수정과 장비 추가/제외는 접힘 관리 영역으로 이동했습니다.
  - 모바일 과밀 배치를 줄이기 위해 버튼/폼/장비 목록 CSS를 다시 보정했습니다.
- `v1.7.2` UI 정리:
  - 운동 장소 관리 화면을 요약 카드, 새 장소 추가, 장소별 수정/장비 관리 구조로 재정리했습니다.
  - 모바일에서 입력칸과 버튼이 겹치지 않도록 장소 관리 CSS 반응형 규칙을 보강했습니다.
  - 전체 소스 점검과 QA를 다시 진행했습니다.
- `v1.7.1` 긴급 수정:
  - 기존 로컬 DB에서 `location_id` 컬럼 추가보다 장소 인덱스 생성이 먼저 실행되어 `/more`가 500 오류가 나던 문제를 수정했습니다.
  - 기존 DB 마이그레이션 회귀 테스트를 추가했습니다.
- 앱 버전을 `v1.7.0`으로 올렸습니다.
- 운동 장소/헬스장 관리 기능을 추가했습니다.
  - `workout_locations`, `location_equipment` 테이블을 추가했습니다.
  - 기존 운동 세션은 기본 헬스장으로 자동 연결됩니다.
  - 오늘 운동 화면에서 현재 장소를 선택하고, 장소별 장비 목록을 우선 표시합니다.
  - 운동 저장 시 선택한 장소와 장비가 같이 저장되고, 새 장비는 해당 장소 장비 목록에 자동 등록됩니다.
  - 더보기 > 운동 장소에서 장소 추가, 기본 장소 지정, 비활성화, 장소별 장비 추가/제외를 관리합니다.
  - 기록 검색에서 장소 필터와 장소명을 표시합니다.
- 검증:
  - `python -m compileall health_tracker tests`
  - `node --check static\app.js`
  - `python -m unittest discover -v` 결과 16개 테스트 통과

## 프로젝트 개요

- Flask + SQLite 기반 운동/식단 기록 PWA입니다.
- 로컬 프로젝트 경로: `C:\Users\Minseong\Documents\Codex\2026-05-23\serviceproject`
- GitHub 저장소: `https://github.com/rlalastjd782-oss/serviceproject.git`
- PythonAnywhere 배포 주소: `https://kimmins.pythonanywhere.com`
- PythonAnywhere 계정/경로:
  - 사용자명: `kimmins`
  - 앱 경로: `/home/kimmins/serviceproject`
  - venv: `/home/kimmins/serviceproject/.venv`
  - WSGI: `/var/www/kimmins_pythonanywhere_com_wsgi.py`
  - 운영 DB: `/home/kimmins/serviceproject/instance/workout.db`

## 사용자 선호

- 답변은 한국어 존댓말로 합니다.
- 작업이 끝나면 한국어 커밋 메시지로 commit/push까지 진행합니다.
- 사용자는 모바일에서 보는 화면을 중요하게 봅니다.
- UI 방향은 사용자가 제공한 `health-tracker_10.html` 스타일을 선호합니다.
  - 최대 480px 모바일 앱 폭
  - 어두운 배경 `#0f0f14`
  - 카드 배경 `#15151e`, `#1a1a24`
  - sticky header + tabs
  - 조밀한 section/card/list UI
- 사용자는 기능보다 화면 흐름과 입력 편의성을 자주 지적합니다. 구현 후 반드시 실제 렌더링을 확인합니다.

## 현재 구조

- 진입점: `app.py`
- 라우트 등록: `app_routes.py`
- 설정/상수:
  - `app_config.py`
  - `app_constants.py`
  - `app_meta.py`
- 서비스 레이어:
  - `app_workout_service.py`
  - `app_meal_service.py`
  - `app_summary_service.py`
  - `app_export_service.py`
  - `app_data_service.py`
  - `app_admin_service.py`
  - `app_pr_service.py`
- 템플릿:
  - `templates/base.html`
  - `templates/index.html`
  - `templates/summary_page.html`
  - `templates/pr_page.html`
  - `templates/settings.html`
  - `templates/calendar.html`
  - `templates/meal_weekly.html`
  - `templates/meal_monthly.html`
  - `templates/record_search.html`
  - `templates/macros.html`
- 정적 파일:
  - `static/styles.css`
  - `static/app.js`
  - `static/sw.js`
  - `static/manifest.webmanifest`
- 테스트: `tests/test_app_flows.py`

## 주요 기능

- 오늘 화면은 `overview`, `workout`, `meal` 모드가 있습니다.
- 운동:
  - 날짜별 운동 입력
  - 부위: 하체, 가슴, 팔, 등, 어깨, 유산소, 기타
  - 세트별 무게/횟수/메모
  - 유산소 입력 필드
  - 장비 선택
  - 세트 수정/삭제/추가
  - 운동 시간 타이머
  - 휴식 타이머
  - 루틴 저장/적용
  - 운동 계획
  - PR 기록/분석
  - 운동별 기록, 장비별 기록
  - 회복 체크인/회복 상태/코칭
- 식단:
  - 아침/점심/저녁/간식/기타
  - 음식명, 수량, g, kcal
  - 식단 항목 수정/삭제/추가
  - 즐겨찾기/템플릿/최근 식단 복사
  - 주간/월간 식단 페이지
- 분석:
  - 일간/주간/월간 집계
  - 부위별 분석
  - 주간 상세 리스트
  - 목표 진행률
  - 균형/볼륨 경고
  - 체중/체지방/사진 기록
- 데이터:
  - JSON 전체 백업/복원
  - 운동 CSV export
  - 식단 CSV export
  - 샘플 데이터 삭제/생성

## 로컬 실행

```powershell
cd C:\Users\Minseong\Documents\Codex\2026-05-23\serviceproject
.\.venv\Scripts\Activate.ps1
python app.py
```

브라우저:

```text
http://127.0.0.1:5000
```

모바일 같은 Wi-Fi 테스트:

```powershell
python app.py --host 0.0.0.0
```

## 검증 명령

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
node --check static/app.js
.\.venv\Scripts\python.exe -c "from app import app; c=app.test_client(); print(c.get('/').status_code); print(c.get('/summaries/weekly').status_code)"
```

## PythonAnywhere 업데이트 배포

로컬에서 변경 후 push까지 끝난 다음, PythonAnywhere Bash에서:

```bash
cd ~/serviceproject
bash deploy_pythonanywhere.sh
```

스크립트가 `git pull`, 패키지 설치 확인, WSGI reload를 한 번에 처리합니다.
문제가 생기면 Web 탭에서 `Reload kimmins.pythonanywhere.com` 버튼을 눌러도 됩니다.

## 새 Codex 세션 시작 프롬프트

새 CLI 세션에서 아래처럼 말하면 됩니다.

```text
이 프로젝트는 Flask 운동/식단 기록 앱입니다. NOTES.md와 git log를 먼저 읽고 이어서 작업해 주세요.
한국어 존댓말로 답변하고, 작업이 끝나면 한국어 커밋 메시지로 push까지 진행해 주세요.
UI는 health-tracker_10.html 느낌의 모바일 앱 스타일을 유지해 주세요.
```

## 작업 시 주의

- 운영 데이터는 GitHub가 아니라 PythonAnywhere의 `instance/workout.db`에 저장됩니다.
- DB 스키마 변경 시 `init_db()`의 `CREATE TABLE`과 `ensure_column()` 흐름을 같이 확인합니다.
- PWA 캐시 때문에 배포 후 모바일에서 예전 화면이 보일 수 있습니다. 이 경우 새로고침, 앱 재시작, 홈 화면 바로가기 재설치 순서로 확인합니다.
- 사용자가 "배포"라고 말하면 일반적으로 `git push` 후 PythonAnywhere에서 `git pull`/reload가 필요합니다.

## 버전관리 규칙

- 앱 버전의 단일 기준은 루트의 `VERSION` 파일입니다.
- 화면/설정에 보이는 버전은 `health_tracker/meta.py`가 `VERSION`을 읽어 `vMAJOR.MINOR.PATCH` 형식으로 표시합니다.
- PWA 캐시명은 앱 버전과 맞춰 `workout-pwa-vMAJOR.MINOR.PATCH`로 올립니다.
- 기능 추가는 `MINOR`, 버그 수정은 `PATCH`, 데이터/호환성 깨짐은 `MAJOR`를 올립니다.
- 릴리즈마다 `CHANGELOG.md`에 변경사항과 날짜를 남깁니다.

## 2026-05-25 작업 노트

- Python/HTML 구조를 `health_tracker/` 패키지 기준으로 정리했습니다.
- 설정 비밀번호 잠금/재설정, 기록/분석 페이징, 연도별 기록, QA 더미데이터, QA 리포트, 연간 export를 추가했습니다.
- 더보기 중복 메뉴, 분석 PR 하단 메뉴, 모바일 목록 밀림, 연간 분석 active 표시를 수정했습니다.
- 기록 검색과 일별 기록 페이징 UI를 추가/개선했습니다.
- Galaxy Z Fold7 기준으로 모바일 UI 폭을 커버 화면(400px대)과 내부 화면(900px 이하) 중심으로 재정리하기 시작했습니다.
- 오늘 운동 입력의 이전 운동 전체 노출을 최근 사용 8개 중심으로 줄이고, 전체 탐색은 운동 라이브러리로 분리했습니다.
- 운동 입력 빠른 선택을 최근/즐겨찾기/루틴 탭으로 분리하고, 기록 검색 상세 필터를 접이식으로 정리했습니다.
- 컨디션 기반 운동 강도 코치 카드를 추가해 슬라이더 변경 시 점수와 권장 강도가 즉시 갱신되게 했습니다.
- 최근 14일 기준 기록 상태 카드를 추가해 운동/식단/체성분/누락일을 데이터 품질 점수로 확인할 수 있게 했습니다.
- Fold UI 회귀 테스트를 추가하고 QA 리포트 기준에 빠른 선택 탭, 컨디션 코치, 기록 상태 카드, 상세 필터 확인 항목을 보강했습니다.
- 프로젝트 루트/소스 폴더의 `__pycache__`와 로컬 서버 로그를 정리했습니다. `.venv`, `instance`, QA 더미데이터는 유지합니다.
- 브라우저는 사용자가 명시적으로 요청할 때만 엽니다.
- 기본 검증 명령은 `python -m unittest discover -v`, `node --check static\app.js`, 주요 Flask test client 응답 확인입니다.

## 2026-05-26 작업 노트

- 앱 버전 기준을 `VERSION` 파일로 통일하고 `CHANGELOG.md`를 추가했습니다.
- `기록 상태` 카드를 `분석 신뢰도` 카드로 바꾸고 원형 점수 링, 근거 미니 바, 부족 항목 액션을 추가했습니다.
- 분석 신뢰도 계산을 `health_tracker/services/data_quality.py`로 분리했습니다.
- 1년치 QA 더미데이터에 체성분 변화와 회복 패턴을 추가했습니다.
- 주간/월간 분석 상단 UI를 연간 리포트와 같은 대시보드형 UI로 정리했습니다.
- 기록 검색, PR 분석, 장비 분석 상단 UI도 대시보드형으로 정리했습니다.
- 오늘 화면, 기록 검색 결과, 더보기 화면을 대시보드형 UX로 개선했습니다.
- 공통 카드/버튼/빈 상태 스타일을 더 입체적으로 정리했습니다.
- 앱/PWA 버전을 `v1.4.0`으로 갱신했습니다.
## 2026-05-26 추가 작업 노트

- 운동 입력에 `kg/lb` 단위 선택을 추가했습니다. `lb`로 입력한 무게는 저장 시 kg로 자동 변환되어 기존 분석/PR/볼륨 계산과 호환됩니다.
- 모바일 운동 입력을 세트 빌더 중심으로 개선했습니다. 3/4/5세트 프리셋, 세트 수 직접 입력, 같은 무게 채우기, +5 증량 채우기, kg 저장 미리보기를 추가했습니다.
- 세트 빌더 UI와 LB 변환 저장 테스트를 추가했습니다.
- 기록/분석 목록의 기본 페이징 표시 개수를 10개로 낮췄습니다. 20개/50개 선택지는 유지했습니다.
- 운동 입력 세트 빌더의 행 레이아웃 깨짐을 수정했습니다. 세트 번호, 무게/횟수 입력, 복사/삭제 버튼을 카드형 그리드로 재배치했습니다.
- 세트 행을 상단 액션형 카드 구조로 다시 정리해 무게/횟수 입력칸과 복사/X 버튼 정렬 문제를 보정했습니다.
- 방문자 읽기 전용 모드와 관리자 잠금을 추가했습니다. 모든 POST 요청, export/import/delete/API 민감 라우트는 관리자 세션과 CSRF 토큰을 요구합니다.
- 방문자 화면에서는 작성/수정/삭제 UI를 숨기고, 관리자는 비밀번호 해제 후 기존 기능을 사용할 수 있게 했습니다.
- CSRF 토큰과 관리자 보호 라우트 기준을 `health_tracker/security.py`로 분리해 `app.py`의 보안 공통 로직을 정리했습니다.
- 설정 비밀번호 PBKDF2 해시 생성/검증도 `health_tracker/security.py`로 옮기고 회귀 테스트를 추가했습니다.
- 배포 서버 UTC 시간대 영향으로 오늘 화면이 한국 시간보다 하루 늦게 잡힐 수 있어 `APP_TIMEZONE` 기본값을 `Asia/Seoul`로 두고 앱 기준 오늘 날짜를 계산하게 수정했습니다.
- 날짜가 박히는 첫 화면(`/`, `/?mode=workout`, `/?mode=meal`)은 PWA precache에서 제외했습니다.
- 기록 탭의 일간 기록 화면 부위별 분석에만 부위 카테고리 필터가 나오도록 재정리하고, 필터/카드 사이 여백을 보정했습니다.
- 기록 탭 부위별 분석 전체 보기에서 특정 부위만 보이던 문제를 완화하고, 필터 클릭 시 부위별 분석 섹션에 머물도록 앵커를 추가했습니다.
- 오늘 운동 화면의 운동 진행 카드 휴식 버튼을 `타이머 시작`으로 정리하고, 오늘 컨디션 카드 점수 정렬을 보정했습니다.
- 오늘 컨디션 카드의 퍼센트 숫자가 `%`보다 작게 보이던 CSS 상속 문제를 수정했습니다.
- 현재 PWA 버전은 `v1.6.8`로 갱신했습니다.
