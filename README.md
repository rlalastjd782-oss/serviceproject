# Health Tracker PWA

운동, 식단, 신체 기록을 모바일에서 빠르게 남기고 주간/월간/연간 흐름을 확인할 수 있는 Flask 기반 PWA입니다.

이 프로젝트는 개인 운동 기록을 단순히 저장하는 데서 끝나지 않고, 운동 루틴, 식단 패턴, PR, 부위별 균형, 장소/장비별 히스토리를 한 화면 흐름 안에서 확인할 수 있게 만드는 것을 목표로 합니다.

## 주요 기능

- 날짜별 운동 세션과 식단 기록 저장
- 세트별 중량, 반복 수, RPE, 휴식, 메모 기록
- 오늘 운동, 오늘 식단, 오늘 요약 중심의 모바일 기록 흐름
- PR, 운동 추세, 부위별 균형, 장비별 기록 분석
- 주간, 월간, 연간 운동/식단 리포트
- 운동 장소와 장소별 장비 히스토리 관리
- 식단 템플릿, 자주 먹는 음식, 최근 식단 흐름 확인
- 설정 잠금으로 개인 쓰기 권한 보호
- SQLite 기반 로컬 데이터 저장
- 백업, 복원, CSV 내보내기
- 모바일 홈 화면에 설치 가능한 PWA

## 화면 구성

- 오늘: 운동, 식단, 요약을 빠르게 기록하는 기본 화면
- 기록: 날짜별 기록, 검색, 필터, 정렬
- 분석: 주간/월간/연간 통계, PR, 부위별/장비별 흐름
- 식단: 일간/주간 식단, 템플릿, 자주 먹는 음식
- 더보기: 캘린더, 장소, 데이터 관리, 설정 등 보조 기능
- 관리자: 계정, 데이터, 배포 전 점검용 관리 기능

## 기술 스택

- Python
- Flask
- SQLite
- HTML, CSS, JavaScript
- PWA manifest
- Service Worker

## 로컬 실행

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

브라우저에서 다음 주소를 엽니다.

```text
http://127.0.0.1:5000
```

같은 Wi-Fi의 휴대폰에서 확인하려면 다음처럼 실행합니다.

```powershell
python app.py --host 0.0.0.0
```

이후 휴대폰 브라우저에서 `http://YOUR_PC_IP:5000`으로 접속하고 홈 화면에 추가하면 앱처럼 사용할 수 있습니다.

## 데이터 저장

기본 SQLite 데이터베이스는 다음 위치에 생성됩니다.

```text
instance/workout.db
```

개인 기록 데이터가 들어가는 파일이므로 백업 또는 배포 시 취급에 주의해야 합니다.

## 테스트와 점검

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe tools\check_release.py
```

정적 자산, 릴리스 버전, 서비스 워커 캐시, 주요 UI 계약을 함께 확인합니다.

## 배포

PythonAnywhere 배포 절차는 별도 문서를 참고합니다.

[DEPLOY_PYTHONANYWHERE.md](DEPLOY_PYTHONANYWHERE.md)

## 개발 운영

이 프로젝트는 Claude Code 서브에이전트 기반 파이프라인으로 기획, 디자인, 개발, QA, 최종검수 단계를 관리합니다. 자세한 내용은 [CLAUDE.md](CLAUDE.md)를 참고합니다.

파이프라인 산출물(`docs/specs/`, `docs/design/`, `qa/reports/`, `qa/final-reviews/` 등)은 로컬 운영용이며, 서비스 소스와 분리해서 관리합니다.
