# Codex Handoff Notes


## 2026-05-31 v3.0.0 UI 21개 항목 재보정

- 최종검수는 조건부 승인으로 정리했습니다. 배포 차단 이슈는 없고, 운영 전 실제 브라우저에서 390px, 430px, 560px, desktop 기준 핵심 화면의 한글 라벨 겹침과 버튼 위계를 수동 확인해야 합니다.
- 확인 범위: 전역 surface/depth token, date/control panel, file-control-row, 식사 시간 badge, list-card, result-row, 과부하 state card, 정적 UI 계약 테스트.
- 검증 통과: `.\.venv\Scripts\python.exe -m unittest tests.test_static_assets -v`, `.\.venv\Scripts\python.exe -m unittest discover -v`, `.\.venv\Scripts\python.exe -m compileall app.py health_tracker tests`, `.\.venv\Scripts\python.exe tools\check_release.py`, `git diff --check`, 로컬 HTTP `302 /auth/login` 확인.
- 작업 전부터 존재한 `.gitignore` 변경은 커밋 포함 전 의도 확인이 필요합니다.
## 2026-05-31 v3.0.0 후속 UI 구조 보정

- v3.0.0 이후 실제 화면 기준 UI 구조 보정 최종검수를 조건부 승인으로 정리했습니다.
- 확인 범위: 기간 선택, 주간 분석 정보 구조, 분석 quick action, 운동별 기록 필터, 식단 템플릿 row, 장소 관리 action row, 버튼 위계 CSS 계약.
- 검증 통과: `.\.venv\Scripts\python.exe -m unittest tests.test_static_assets -v`, `.\.venv\Scripts\python.exe -m unittest discover -v`, `.\.venv\Scripts\python.exe -m compileall app.py health_tracker tests`, `.\.venv\Scripts\python.exe tools\check_release.py`, `git diff --check`, `Invoke-WebRequest http://127.0.0.1:5000/ -UseBasicParsing -TimeoutSec 5`.
- 운영 전 실제 브라우저에서 390px, 430px, 560px, desktop 기준 한글 라벨 겹침, active 상태, 버튼 위계, PWA 캐시 교체를 수동 확인해야 합니다.
- 작업 전부터 존재한 `.gitignore` 변경은 커밋 포함 전 의도 확인이 필요합니다.

## 2026-05-31 v3.0.0

- v3.0 전체 UI 감사 및 화면 구조 재정립 최종검수를 조건부 승인으로 정리했습니다.
- 확인 범위: 스펙/디자인/QA 문서, 핵심 DOM/CSS selector 계약, `VERSION`, manifest, service worker cache `workout-pwa-v3.0.0`.
- 검증 통과: `.\.venv\Scripts\python.exe -m unittest tests.test_static_assets -v`, `.\.venv\Scripts\python.exe -m unittest discover -v`, `.\.venv\Scripts\python.exe -m compileall app.py health_tracker tests`, `.\.venv\Scripts\python.exe tools\check_release.py`, `git diff --check`, `Invoke-WebRequest http://127.0.0.1:5000/ -UseBasicParsing -TimeoutSec 5 -MaximumRedirection 0`.
- 운영 전 실제 브라우저에서 390px, 430px, 560px, desktop 기준 Level 0~4 depth, active 상태, 한글 라벨 겹침, PWA 캐시 교체를 수동 확인해야 합니다.

## 2026-05-31 v2.8.32

- 식단탭 기준 전역 UI 시스템 강제 적용 최종검수를 조건부 승인으로 정리했습니다.
- `v2.8.32 global surface enforcement pass`가 오늘, 기록, 분석, 식단, 더보기, 설정의 Level 0~4 surface/depth selector 계약을 덮는지 확인했습니다.
- 검증 통과: `.\.venv\Scripts\python.exe -m unittest tests.test_static_assets -v`, `.\.venv\Scripts\python.exe -m unittest discover -v`, `.\.venv\Scripts\python.exe -m compileall app.py health_tracker tests`, `.\.venv\Scripts\python.exe tools\check_release.py`, `git diff --check`, `Invoke-WebRequest http://127.0.0.1:5000/ -UseBasicParsing -TimeoutSec 5`.
- 운영 전 실제 브라우저에서 390px, 430px, 560px, desktop 기준 surface depth, active 상태, 한글 라벨 겹침 여부를 수동 확인해야 합니다.

## 2026-05-30 v2.8.28

- User reported that switching the whole today UI to gray made the design progressively worse.
- Changed direction from all-gray sections to clean white section cards, with light gray-blue only for inner rows, inputs, and controls.
- Kept the v2.8.27 workout ordering and overview-only hide guards.
- Added `v2.8.28 today visual reset` and a static asset regression test for white today section cards.
- Updated `UI_QA.md`, version, manifest, and service worker cache for `2.8.28`.

## 2026-05-30 v2.8.27

- User reported that the prior PDF review was not sufficient and several requested today UI fixes were still not reflected.
- Rechecked today pages with long mobile captures under `artifacts/ui_screenshots_20260530_04_long/png/`.
- Found the main workout flow bug: only some flex children had `order`, so unordered sections such as next actions and rule cards could appear before the workout clock/input flow.
- Added `v2.8.27 today layout correction pass` to explicitly order workout sections and flatten inner today cards/rows so the page stops looking like nested white boxes.
- Updated `UI_QA.md`, tests, release version, manifest, and service worker cache for `2.8.27`.
- Generated final post-fix PDF `artifacts/ui_screenshots_20260530_07/ui_screenshots.pdf`.
- Added a regression guard for workout-mode overview-only panels being hidden after final override display rules.
- Verification passed: static asset tests, release check, selected UI navigation tests, ruff, compileall, and full unittest discovery.

## 2026-05-30 v2.8.26

- Baseline PDF `artifacts/ui_screenshots_20260530_02/ui_screenshots.pdf` and today screenshots were reviewed before editing.
- Today overview still had too many white nested surfaces: summary button state, data-quality card interiors, record-add actions, and quality metrics.
- Today workout still had white remnants in current location, equipment, recent workout, clock/timer controls, save status, and additional recommendations.
- Added `UI_QA.md` with the PDF review findings and the v2.8.26 correction plan.
- Added the final `v2.8.26 today css audit pass` in `ui_rebuild_05.css`, restored the data-quality conic ring, neutralized white surfaces, and moved workout input closer to timer controls.
- Bumped `VERSION`, manifest, and service worker cache to `2.8.26`.
- Generated post-fix PDF `artifacts/ui_screenshots_20260530_03/ui_screenshots.pdf` and reviewed the today overview/workout/meal plus records reference captures.
- Verification passed: static asset tests, release check, selected UI navigation tests, ruff, compileall, and full unittest discovery.

## 2026-05-30 v2.8.25

- 장비 목록 badge, 운동시간, 휴식 타이머, 오늘 상태 완료 전 카드, 오늘 요약 overview 카드에 이전 배경/평면 스타일이 남은 문제를 확인했습니다.
- `location-equipment-strip`, `workout-clock-section`, `#rest-timer`, `completion-card`, overview 전용 `today-focus-card`/`summary-card`/`record-card`를 직접 덮는 최종 surface pass를 추가했습니다.
- 앱 버전, manifest, service worker cache를 `2.8.25`로 갱신했습니다.

## 2026-05-30 v2.8.24

- 오늘 UI가 다른 탭보다 너무 연약하고 평면적으로 보이는 문제를 확인했습니다.
- 오늘 화면에만 바깥 섹션, 내부 카드, badge/input의 3단계 깊이를 다시 정의하고, 더 분명한 layered shadow와 미세한 hover lift를 추가했습니다.
- 기록형 레이아웃은 유지하면서 gap을 12~14px 기준으로 보정했습니다.
- 앱 버전, manifest, service worker cache를 `2.8.24`로 갱신했습니다.

## 2026-05-30 v2.8.23

- v2.8.22에서 상단 메뉴 정리 중 운동 집중모드 진입 버튼이 화면에서 사라진 문제를 확인했습니다.
- 상단 `운동/식단/요약` 3탭은 유지하되, 운동 모드에서 집중모드 버튼을 3탭 아래 전체 폭 보조 액션으로 다시 보이도록 최종 CSS 레이어에서 복구했습니다.
- 앱 버전, manifest, service worker cache를 `2.8.23`으로 갱신했습니다.

## 2026-05-30 v2.8.22

- 운동 탭에서만 `집중 모드/집중 해제`가 상단 메뉴에 끼어들어 식단/요약 탭과 메뉴 개수가 달라지는 문제를 확인했습니다.
- 오늘 상단 모드 메뉴를 항상 3분할로 고정하고, 상단 메뉴 안의 집중 토글은 숨기도록 최종 CSS 레이어에서 보정했습니다.
- 오늘 페이지 카드와 섹션에 너무 평면적이지 않은 약한 그림자를 다시 부여해 기록형 레이아웃을 유지하면서 입체감을 조금 보강했습니다.
- 앱 버전, manifest, service worker cache를 `2.8.22`로 갱신했습니다.

## 2026-05-30 v2.8.21

- 오늘 페이지 전체가 기록 페이지와 간격/카드 체계가 맞지 않는 문제를 다시 확인했습니다.
- `today-shell` 전체 gap, 날짜/모드 바, overview summary grid, 오늘 운동/식단/기록 섹션, 내부 card/row/badge/input 간격을 기록 페이지의 `record-list`/`daily-record-card` 밀도에 맞추는 override를 추가했습니다.
- 앱 버전, manifest, service worker cache를 `2.8.21`로 갱신했습니다.

## 2026-05-30 v2.8.20

- 오늘 요약 화면의 색 변경이 실제 overview 화면에 적용되지 않은 문제를 확인했습니다.
- `workout-mode` 전용이 아니라 오늘 요약 기본 화면의 `today-hero-section`, `summary-grid overview-only`, `today-focus-card`, `summary-card`, `record-card`에 직접 적용되는 중립 흰색/회색 표면 override를 추가했습니다.
- 서비스워커 캐시와 앱 버전을 `2.8.20`으로 올려 브라우저가 새 CSS를 받도록 했습니다.

## 2026-05-30 작업 기록

- 전체 UI 회색톤 적용 후 깨져 보이던 화면들을 순차 점검했습니다.
- 헤더 영역에서 `피트니스 트래커`, 사용자 환영 문구, 버전 배지의 배경/글자색을 다시 맞췄습니다.
- 헤더 아래 상단 메뉴와 오늘 운동 빠른 메뉴 사이 간격을 조정했습니다.
- 오늘 화면의 분석 신뢰도, 오늘 상태, 최근 7일 누락, 개인화 다음 운동 카드의 배경색/글자색/배지 색을 정리했습니다.
- 식단 입력, 식단 목표 저장 입력칸, 오늘 식단 리스트 주변의 흰색 배경 계열을 회색 gradient 톤으로 맞췄습니다.
- 기록/분석 화면의 날짜별 기록, 기간 요약, 정렬 컨트롤, 페이지네이션, 내부 배지들이 층층이 쌓여 보이는 문제를 완화했습니다.
- 분석 화면에서 주간/월간/연간/운동별/PR/장비별 현재 범위 표시를 추가하고, 분석 탭 활성 표시 누락을 보완했습니다.
- 운동별 기록 페이지의 운동 상세 카드, 과부하 분석 카드, 운동별 순위 카드, 부위별 운동 리스트, 최근 세트 기록 UI를 같은 카드 체계로 맞췄습니다.
- PR 화면의 PR 랭킹 카드, 상세 PR 카드, 히스토리 그래프, 내부 메트릭 배지의 배경과 크기를 정리했습니다.
- 더보기 하위 화면의 기록 점검, 캘린더, 플레이트 계산기, 실행 인사이트, 데이터 센터 등에서 더보기 탭 활성 표시와 카드 색상 불일치를 보정했습니다.
- 로그아웃 버튼에 `로그아웃하시겠습니까?` 확인 팝업을 추가했습니다.
- `tools/capture_ui_screenshots.py`를 추가해 주요 화면 26개를 자동 캡처하도록 했습니다.
- 캡처 산출물은 `artifacts/ui_screenshots_20260530_01/`에 저장했습니다.
  - PNG: `artifacts/ui_screenshots_20260530_01/png/`
  - PDF: `artifacts/ui_screenshots_20260530_01/ui_screenshots.pdf`
  - HTML 갤러리: `artifacts/ui_screenshots_20260530_01/ui_screenshots_gallery.html`
- 실행한 검증:
  - `python -m unittest tests.test_static_assets -v`
  - `python -m unittest tests.test_ui_navigation_flows.UiNavigationFlowTest.test_main_pages_render tests.test_ui_navigation_flows.UiNavigationFlowTest.test_analysis_pages_show_current_scope_marker -v`
  - `python -m ruff check health_tracker tests tools`
  - `python tools/check_release.py`
- 현재 확인된 릴리스 버전은 `v2.8.12`입니다.
- 이번 작업은 커밋/푸시하지 않았습니다.

## 현재 상태

- 현재 버전: `2.8.19`
- 기본 브랜치: `main`
- 커밋 메시지는 한국어로 작성합니다.
- 작업 완료 후 `NOTES.md`, `CHANGELOG.md`, `VERSION`, manifest, service worker cache를 함께 갱신합니다.
- 앞으로 업데이트, 수정, 정리, 릴리스 준비 등 프로젝트 상태가 바뀌는 작업을 할 때는 작업 내용과 검증 결과를 먼저 `NOTES.md`와 `CHANGELOG.md`에 기록합니다.
- 사용자가 `CHANGED.MD`라고 말하면 현재 저장소의 실제 변경 기록 파일인 `CHANGELOG.md`를 의미하는 것으로 처리합니다.
- 브라우저는 사용자가 요청할 때만 엽니다.

## 최근 작업

- v2.8.19에서 오늘 운동 화면의 입력/빠른 선택/세트 빌더/운동 기록 카드 색상을 기록 카드와 같은 중립 흰회색 표면으로 맞췄습니다.
- v2.8.18에서 오늘 화면의 `기록 품질` 섹션 배경을 블루그레이가 아닌 중립 흰회색 표면으로 되돌렸습니다.
- v2.8.17에서 오늘 화면의 `요약` 활성 버튼과 `기록 품질` 카드 계열이 진한 회색으로 보이던 문제를 밝은 블루그레이 표면으로 낮췄습니다.
- v2.8.16에서 오늘 화면의 `전체` 모드명을 `요약`으로 바꾸고, 어색했던 `분석 신뢰도` 표현을 `기록 품질` 중심으로 정리했습니다.
- v2.8.15에서 상단 탭과 섹션 헤더를 가볍게 만들고, 카드 내부 row/badge/pill/form/toolbar의 그림자와 강한 배경을 제거해 계층처럼 쌓이는 UI를 줄였습니다.
- 다음 UI 개편 flow에 “계층처럼 쌓이는 카드/박스 구조 제거”를 최우선 조건으로 넣었습니다. 바깥 컨테이너만 입체감을 주고 내부 row, badge, pill, form control은 flat하게 낮추는 방향으로 진행합니다.
- 다음 UI 개편은 `상단 탭 경량화 → 섹션 헤더 위계 정리 → 카드 내부 계층 제거 → 기간/필터/정렬 공통화 → 빈 상태 compact화 → 화면별 재검수` 순서로 진행합니다.
- v2.8.14 작업 이후 문서 운영 규칙을 명확히 했습니다. 앞으로 모든 변경 작업은 `NOTES.md`와 `CHANGELOG.md`에 기록을 남깁니다.
- v2.8.14에서 초기 `ui_rebuild_01~03.css` override import와 파일을 제거해 CSS 로딩 경로를 `ui_rebuild_04.css`, `ui_rebuild_05.css` 중심으로 단순화했습니다.
- v2.8.14에서 기록/식단 기록 카드의 핵심 selector 계약을 최종 override 레이어로 옮기고 서비스워커 캐시 목록을 정리했습니다.
- v2.8.13에서 전역 폼/툴바 override의 강도를 낮추고 페이지별 scope로 필터 패널을 재정리했습니다.
- v2.8.13에서 모바일 상단 탭, 기간 선택, 결과 툴바, 빈 상태, 내부 badge/pill의 레이아웃과 그림자 계층을 보정했습니다.
- v2.8.13에서 `ui_rebuild_05.css`를 서비스워커 캐시에 포함하고 `VERSION`, manifest, cache name을 함께 갱신했습니다.
- v2.8.5에서 전체 CSS의 레거시 다크 배경 직접값을 정리했습니다.
- v2.8.6에서 쿨 그레이 운영툴형 UI 예시 페이지 `/auth/theme-preview`를 추가했습니다.
- v2.8.7에서 실제 앱 메인 UI에 차콜 헤더와 회색 표면 톤을 시범 적용했습니다.
- v2.8.8에서 차콜 톤을 연하게 조정하고 필드 내부 그라데이션과 보조 텍스트 대비를 보강했습니다.
- v2.8.9에서 입력/기록/휴식 시작 버튼을 조금 더 진하게 하고 컨테이너 내부 박스류의 그라데이션 범위를 넓혔습니다.
- v2.8.10에서 누적된 CSS override를 정리하고 기록 검색/일별 목록/카드/버튼류를 회색 그라데이션 테마로 통합했습니다.
- v2.8.11에서 메뉴, 오늘 기록, 일별/주별 기록, 식단 리스트, 식단 목표, 주간 계획, 분석 카드의 간격과 카드형 UI를 재보정했습니다.
- v2.8.12에서 분석 탭 전체의 활성 표시, 현재 분석 범위 표시줄, 분석 계열 카드형 UI 누락분을 보강했습니다.
- 분석신뢰도 원형, 기록 카드, 분석 카드, 식단 입력/목록, 더보기 카드에 남아 있던 검은색/짙은 남색 계열을 밝은 회색톤으로 교체했습니다.
- `ui_rebuild_01.css`, `ui_rebuild_02.css`, `ui_rebuild_03.css`의 과거 다크 override를 밝은 테마에 맞게 정리했습니다.
- CSS 정적 테스트에 레거시 다크 표면 색상과 밝은 글씨 토큰 재유입 방지 검사를 추가했습니다.
- 식단 저장 실패 원인이 될 수 있던 식단 관련 POST 폼의 CSRF 토큰 누락은 v2.8.4에서 보강했습니다.

## 검증 기준

- `python -m ruff check health_tracker tests tools`
- `python -m compileall health_tracker tests tools`
- `node --check` for `static/js/*.js`
- `python -m unittest discover -v`
- `python tools/check_release.py`

## 주의사항

- CSS 색상 변경은 마지막 override만 추가하지 말고 실제 원본 CSS의 직접값까지 같이 정리해야 합니다.
- 서비스워커 캐시가 남아 있으면 배포 후 예전 CSS가 보일 수 있으므로 버전과 cache name을 반드시 함께 올립니다.
- 문서 기록 없이 코드만 수정하지 않습니다. 최소한 `NOTES.md`에는 작업 맥락과 검증 결과를, `CHANGELOG.md`에는 사용자에게 의미 있는 변경 사항을 남깁니다.
- UI를 수정할 때 카드 안에 카드가 반복되는 구조를 만들지 않습니다. 내부 요소는 그림자 없는 flat row/pill로 처리하고, shadow/gradient는 바깥 카드나 최상위 panel에만 제한합니다.

