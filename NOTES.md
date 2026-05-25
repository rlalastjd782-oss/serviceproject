# Codex Handoff Notes

이 문서는 VS Code/CLI를 껐다가 새 Codex 세션을 시작했을 때 바로 이어받기 위한 작업 메모입니다.

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
git pull origin master
source .venv/bin/activate
pip install -r requirements.txt
touch /var/www/kimmins_pythonanywhere_com_wsgi.py
```

또는 Web 탭에서 `Reload kimmins.pythonanywhere.com` 버튼을 눌러도 됩니다.

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
