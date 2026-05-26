# Codex Handoff Notes

이 문서는 VS Code/CLI를 껐다가 새 Codex 세션을 시작했을 때 바로 이어받기 위한 작업 메모입니다.

## 2026-05-26 작업 기록

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
