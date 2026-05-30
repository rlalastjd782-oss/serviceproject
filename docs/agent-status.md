# Agent Status Board

Status values: `대기`, `진행중`, `검토필요`, `막힘`, `완료`

| 역할 | 상태 | 현재 작업 | 마지막 업데이트 | 산출물 | 다음 액션 |
|---|---|---|---|---|---|
| 기획 | 완료 | 기록탭 스타일 기준 전체 UI 입체감 통일 요구사항 정리 | 2026-05-30 | `docs/specs/records-style-dimensional-ui.md`, `handoff/planning-to-design.md` | 디자인 담당자는 기록탭 기준 전체 UI 통일안을 작성 |
| 디자인 | 완료 | 기록탭 스타일 기준 전체 UI 입체감 통일 | 2026-05-31 | `docs/design/records-style-dimensional-ui.md`, `handoff/design-to-dev.md` | 개발 담당자는 디자인 문서 기준으로 구현 |
| 개발 | 완료 | 기록탭 스타일 기준 전체 UI 입체감 통일 구현 | 2026-05-31 | `static/css/overrides/ui_rebuild_05.css`, `tests/test_static_assets.py`, `handoff/dev-to-qa.md` | QA 담당자는 모바일 주요 화면에서 Surface 1/2/3와 active 상태 적용을 확인 |
| QA | 완료 | 기록탭 스타일 기준 전체 UI 입체감 통일 QA | 2026-05-31 | `qa/reports/records-style-dimensional-ui-v2-8-30.md`, `handoff/qa-to-final.md` | 최종검수자는 실제 모바일/PWA 환경에서 시각 깊이와 라벨 겹침 여부를 수동 확인 |
| 최종검수자 | 완료 | 기록탭 스타일 기준 전체 UI 입체감 통일 최종검수 | 2026-05-31 | `qa/final-reviews/v2-8-30-final-review.md`, `handoff/final-to-git.md` | Git 자동화는 소스 변경 파일만 검토 후 stage/commit/push |

## 운영 규칙

- 각 역할은 작업 시작 전에 이 파일과 관련 handoff 파일을 먼저 확인한다.
- 자기 차례가 아니면 파일을 수정하지 않고 현재 상태만 보고한다.
- 자기 역할 행만 갱신한다. 단, 작업 완료 시 다음 역할이 이어받을 수 있도록 필요한 handoff 파일은 갱신한다.
- 작업 시작 시 상태를 `진행중`으로 바꾼다.
- 작업 완료 시 상태를 `완료`, `검토필요`, 또는 `막힘`으로 바꾼다.
- 산출물에는 실제 파일 경로를 적는다.
- 다음 액션에는 다음 역할이 해야 할 일을 명확히 적는다.

## 기획 스레드 추가 규칙

- 이 프로젝트의 모든 신규 기능 요청은 이 기획 스레드에서 계속 접수한다.
- 요청을 받을 때마다 새 작업 단위로 처리한다.
- 새 기능이면 `docs/specs/` 아래에 기능명 기준 소문자 kebab-case 스펙 문서를 만든다.
- 기존 기능 수정이면 기존 스펙을 업데이트하거나 별도 변경 스펙을 만든다.
- 아직 디자인/개발/QA가 끝나지 않은 작업은 덮어쓰지 않고 별도 스펙 또는 대기열로 관리한다.
- 작업이 끝나면 `handoff/planning-to-design.md`를 최신 작업 기준으로 갱신하고 상태를 `디자인 준비됨`으로 둔다.
- 한 번에 여러 요청이 들어오면 기능별로 쪼개서 처리한다.

## 대기 중 작업

- `기록탭 스타일 기준 전체 UI 입체감 통일`: 최종검수 완료, Git 자동화 준비 상태다.














