# CLAUDE.md

이 파일은 Claude Code가 이 저장소에서 작업할 때 참고하는 가이드다.

## 프로젝트 개요

Health Tracker PWA — 운동, 식단, 신체 기록을 모바일에서 기록하고 주간/월간/연간 흐름을 확인하는 Flask 기반 PWA. 한국어 서비스. 상세 기능은 [README.md](README.md) 참고.

- 기술 스택: Python, Flask, SQLite, HTML/CSS/JS, PWA manifest, Service Worker
- 데이터: `instance/workout.db` (개인 기록이 들어가므로 취급 주의)

## 디렉터리 구조

- `health_tracker/` — 서비스 소스. `app_*_facade.py`(도메인별 파사드) → `routes/`(블루프린트) → `services/`(비즈니스 로직) → `database/`(스키마) 순서로 계층화되어 있다.
- `static/` — CSS/JS/manifest/service worker.
- `tests/` — `unittest` 기반 테스트.
- `tools/` — 릴리스 점검, 로컬 서버 실행, QA 스크린샷 등 운영 스크립트.
- `docs/specs/`, `docs/design/`, `docs/planning-final-reviews/`, `qa/reports/`, `qa/final-reviews/` — 기능 파이프라인 산출물(로컬 전용, git에 커밋되지 않음). 아래 "기능 파이프라인" 참고.

## 개발 명령

```powershell
python -m unittest discover -v          # 전체 테스트
.\.venv\Scripts\python.exe tools\check_release.py   # 정적 자산/버전/서비스워커 캐시/UI 계약 릴리스 게이트
python -m compileall app.py health_tracker tests
ruff check .                             # pyproject.toml 설정 기준 lint
.\tools\start-local-app-server.ps1 -Port 5000        # 로컬 서버 백그라운드 실행 (포그라운드로 python app.py를 직접 띄우지 않는다)
```

로컬 서버 확인은 `Invoke-WebRequest http://127.0.0.1:5000/ -UseBasicParsing -TimeoutSec 5`처럼 짧게 끝나는 요청만 사용한다.

## 기능 파이프라인

새 기능/변경은 기획 → 디자인 → 개발 → QA → 최종검수 → 기획 의도검수 순서로 진행한다. 각 단계는 `.claude/agents/`에 정의된 전용 서브에이전트(`planner`, `designer`, `developer`, `qa-tester`, `final-reviewer`)가 맡고, `/pipeline` 스킬(`.claude/skills/pipeline/SKILL.md`)이 전체 흐름을 조율한다. "파이프라인 실행해줘"처럼 전체 흐름을 요청받으면 이 스킬을 따른다.

- 산출물 위치: 스펙 `docs/specs/`, 디자인 `docs/design/`, QA 리포트 `qa/reports/`, 최종검수 `qa/final-reviews/`, 기획 의도검수 `docs/planning-final-reviews/`. 이 폴더들은 로컬 산출물이며 `.gitignore`에 의해 커밋되지 않는다.
- 승인/조건부 승인 시 `CHANGELOG.md`와 `NOTES.md`는 최종검수 서브에이전트가 갱신한다. 이 두 파일은 공개 문서이며 커밋 대상이다.
- **Git 커밋/푸시는 파이프라인이 끝까지 승인돼도 자동으로 실행하지 않는다.** 항상 변경 파일 목록과 커밋 메시지를 보여주고 사용자 확인을 받은 뒤 커밋하며, push는 별도로 다시 확인한다.

## PowerShell + 한국어 문서 작업 시 주의사항

이 환경은 Windows PowerShell 5.1이며 프로젝트 문서 대부분이 한국어다. 인코딩 문제를 피하려면:

```powershell
Get-Content -LiteralPath "path" -Raw -Encoding UTF8    # 한국어 문서 읽기
Set-Content -LiteralPath "path" -Value $content -Encoding UTF8   # 한국어 문서 쓰기
```

`�`, `?곹깭`, `?붿옄`, `湲곕줉`, `媛쒕컻` 같은 문자가 보이면 인코딩이 깨진 것이니 그대로 쓰지 말고 UTF-8로 다시 읽는다. Read/Write/Edit 도구를 쓸 때는 이 문제가 거의 발생하지 않지만, PowerShell로 직접 파일을 읽고 쓸 때는 위 규칙을 따른다.

## 코딩 컨벤션

- `ruff.toml`/`pyproject.toml` 기준 lint(`F` 규칙)를 통과해야 한다.
- 기존 파사드/라우트/서비스 계층 구조를 따르고, 불필요한 리팩터링이나 추상화를 추가하지 않는다.
- PNG/스크린샷 산출물은 QA 단계에서만, `qa/screenshots/` 아래에만 임시로 만든다. Git 커밋 대상이 아니다.
