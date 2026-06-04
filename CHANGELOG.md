# Changelog
## 2026-06-04 Fold7 반응형 화면 정리 및 404 재발 방지

- `/summaries/annual` 계열 URL을 `/summaries/yearly`로 안정적으로 이동시키고 query string 보존을 확인했습니다.
- Fold7 기준 `360px`, `390px`, `656px`, `768px`, `1280px`에서 식단 입력 우선순위, 중간 폭 grid, 운동별/PR 그래프 내부 스크롤 표현을 정리했습니다.
- 사용자 화면의 `__TEST__` prefix 노출과 주요 화면 대표 `h1` 구조를 정리했습니다.
- 최종검수에서 최신 Playwright 화면검수 산출물, 로컬 HTTP `200`, 컴파일, 지정 unittest 23개 통과를 확인해 조건부 승인했습니다. 잔여 axe 경고는 별도 접근성 개선으로 분리합니다.

## 2026-06-04 Playwright 화면 실검수 기반 UI 정리

- 식단 모드 첫 viewport에서 식단 입력과 오늘 식단 흐름이 먼저 보이도록 순서를 정리했습니다.
- `/summaries/annual` 직접 접근을 `/summaries/yearly`로 redirect하고 주요 분석·식단·도구 화면의 대표 제목 구조를 보강했습니다.
- 모바일 필터 라벨, 분석 subnav, 식단 기간 컨트롤의 줄바꿈과 overflow를 정리하고 사용자 화면의 `__TEST__` 표시 노출을 제거했습니다.
- 최종검수에서 최신 Playwright 화면검수 산출물, 로컬 HTTP `200`, 컴파일, 지정 unittest 23개 통과를 확인해 조건부 승인했습니다. 잔여 axe 경고는 별도 접근성 개선으로 분리합니다.
## 2026-06-03 오늘 할 일 자동 추천

- `/app` 오늘 화면에 규칙 기반 `오늘 할 일` 추천 섹션을 추가해 운동, 식단, 목표, 체성분, 기록 품질 기준의 다음 행동을 최대 5개까지 보여줍니다.
- 추천 카드를 단일 링크 action으로 구성해 운동 입력, 식단 입력, 목표 확인, 체성분 입력, 기록 점검 흐름으로 바로 이동할 수 있게 했습니다.
- 휴식일, 과거 날짜, 목표 미설정, 완료 상태 예외를 처리하고 완료 상태에서도 주간 분석과 휴식 메모 선택지를 유지합니다.
- 최종검수에서 `python -m unittest tests.test_daily_action_recommendations tests.test_ui_navigation_flows`, 로컬 HTTP `200`, 최신 Playwright 화면검수 산출물 확인을 통과해 승인했습니다.

## v3.0.0 UI v2.6.5 기준 실제 복구 - 2026-06-01

- v3.0.0 기능은 유지하면서 `static/css` 전체와 주요 기존 템플릿을 v2.6.5 기준선에 맞춰 복구했습니다.
- `ui_rebuild_05.css`는 파일을 보존하되 `ui_rebuild.css`, template link, service worker cache 적용 경로에서 제외했습니다.
- 대표 화면 20개 조합의 Playwright 화면검수에서 `HTTP 200`, 콘솔 오류 0, 응답 오류 0을 확인했습니다.
- 최종검수는 조건부 승인입니다. 접근성 axe 위반과 `로그아웃` control 시각 이슈는 후속 개발 필수 항목으로 남겼습니다.

## v3.0.0 UI 최종 마감 보정 - 2026-06-01

- `/app` overview의 첫 화면 순서를 `오늘 상태`, `오늘 할 일`, `빠른 기록`, `최근 기록`, `기록 품질`, 날짜 control 중심으로 재정렬했습니다.
- 기록 검색, 주간/월간 분석, 식단, 더보기, 캘린더, 데이터 센터, 장소, 플레이트 계산기, 설정 화면의 role별 surface와 compact control 기준을 보강했습니다.
- 자동 테스트 66개, 정적 자산 테스트 29개, navigation/static 조합 테스트 39개, 컴파일, 릴리스 검사, 공백 검사, 로컬 HTTP `200` 확인을 통과했습니다.
- 최신 visual QA 재실행은 Chromium `spawn EPERM`으로 실패해, 운영 전 실제 브라우저에서 `/app` 첫 viewport와 hero tint를 수동 확인하는 조건을 남겼습니다.

## v3.0.0 UI 브랜드 컬러 리부트 재기획 - 2026-05-31

- 확정 팔레트와 대표 화면 selector 계약을 최종 CSS cascade와 정적 테스트로 고정했습니다.
- 공통 헤더/탭, 오늘 hero, 분석 결론 카드와 4분할, 식단 hero/badge, 더보기 tool group tint, 플레이트 result panel 기준을 재검증했습니다.
- 릴리스 검사, 공백 검사, 자동 테스트 64개, 컴파일, 로컬 HTTP `200` 응답 확인을 통과했습니다.
- 실제 브라우저의 390px, 430px, 560px, desktop 기준 한글 라벨 겹침과 computed style 확인은 운영 전 수동 조건으로 남겼습니다.

## v3.0.0 전체 UI 전면 재정비 - 2026-05-31

- 오늘, 기록, 분석, 식단, 더보기, 설정과 하위 도구 전체에 `v3.0.0 global UI final overhaul` CSS 레이어를 추가해 Level 0~4 surface/depth 계약을 통일했습니다.
- 날짜/주/월 선택, 필터, form/input, 버튼 위계, 위험 action, 식단 badge, 플레이트 계산 결과를 전역 UI 시스템으로 정리했습니다.
- 정적 UI 계약 테스트 25개, 전체 자동 테스트 62개, 컴파일, 릴리스 검사, `git diff --check`, 로컬 HTTP `302 /auth/login` 확인을 통과했습니다.
- 최종검수 환경에서 in-app browser가 제공되지 않아 실제 390px, 430px, 560px, desktop 브라우저 육안 확인은 운영 전 수동 조건으로 남겼습니다.

## v3.0.0 UI 21개 항목 재보정 - 2026-05-31

- v3.0.0 이후 남은 21개 UI 문제를 전역 surface/depth, 배경 layer, 색상 accent, 간격, 버튼 위계 기준으로 재보정했습니다.
- 날짜/주/월 선택, 파일 선택, 식사 시간 badge, list-card, 플레이트 계산 결과, 과부하 state card를 공통 CSS 계약으로 정리했습니다.
- 정적 UI 계약 테스트를 24개로 보강하고 전체 자동 테스트 61개, 컴파일, 릴리스 검사, 로컬 HTTP `302 /auth/login` 확인을 통과했습니다.
- 실제 브라우저의 390px, 430px, 560px, desktop 기준 한글 라벨 겹침과 PWA 캐시 교체는 운영 전 수동 확인 조건으로 남겼습니다.
## v3.0.0 후속 UI 구조 보정 - 2026-05-31

- 기간 선택, 주간 분석, 운동별 기록 필터, 식단 템플릿 최근 식단 row, 장소 관리 action row의 구조를 v3.0.0 이후 실제 화면 기준으로 보정했습니다.
- 주간 분석을 핵심 결론, 대표 지표, 보조 지표, 성과/식단·영양/균형 경고/다음 행동 그룹으로 재정리했습니다.
- 조회, 적용, 저장, 관리, 위험/account 액션의 버튼 위계를 최종 CSS 레이어에서 보강했습니다.
- 자동 테스트 60개, 정적 UI 계약 테스트 23개, 컴파일, 릴리스 검사, 로컬 HTTP `302` 및 로그인 페이지 `200` 응답 확인을 통과했습니다.
- 실제 브라우저의 390px, 430px, 560px, desktop 기준 한글 라벨 겹침과 버튼 위계 체감은 운영 전 수동 확인 조건으로 남겼습니다.

## v3.0.0 - 2026-05-31

- 전체 UI 감사 및 화면 구조 재정립을 적용해 오늘, 기록, 분석, 식단, 더보기, 설정 화면을 같은 v3.0 surface/depth 계약으로 정리했습니다.
- 공통 헤더에서 로그아웃을 주요 탭과 분리하고, 오늘 overview와 분석 결론, 기록 필터, 더보기 그룹, 설정 조작 영역의 정보 위계를 재정렬했습니다.
- 앱 버전, manifest, service worker cache를 `3.0.0` / `workout-pwa-v3.0.0`으로 갱신했습니다.
- 자동 테스트 59개, 정적 자산 테스트 22개, 컴파일, 릴리스 검사, 로컬 HTTP `302` 응답 확인을 통과했습니다.
- 실제 브라우저의 390px, 430px, 560px, desktop 기준 한글 라벨 겹침과 PWA 캐시 교체는 운영 전 수동 확인 조건으로 남겼습니다.

## v2.8.32 - 2026-05-31

- 식단탭 기준 전역 UI 시스템 강제 적용 pass를 추가해 오늘, 기록, 분석, 식단, 더보기, 설정 화면의 surface/depth 체계를 공통 토큰으로 고정했습니다.
- Level 1/2/3/4 selector 계약을 보강해 카드, 입력, 필터, 리스트 row, active 버튼이 같은 밝은 입체 UI 체계를 쓰도록 정리했습니다.
- 앱 버전, manifest, service worker cache를 `2.8.32`로 갱신하고 정적 자산 테스트를 보강했습니다.
- 자동 테스트 58개, 정적 자산 테스트 21개, 컴파일, 릴리스 검사, 로컬 HTTP 응답 확인을 통과했습니다.

## v2.8.28 - 2026-05-30

- Reversed the all-gray today UI direction after it made the screen feel heavier and less polished.
- Restored today section cards to clean white surfaces while keeping inner rows, chips, inputs, and secondary controls in light gray-blue.
- Preserved the workout flow ordering and overview-only visibility fixes from v2.8.27.
- Updated QA notes, release version, manifest, service worker cache, and static asset tests.

## v2.8.27 - 2026-05-30

- Rechecked the today UI with long mobile captures after the prior QA pass missed the full workout scroll order.
- Fixed the workout page flow by explicitly ordering clock, rest timer, action dock, workout input, records, location, next actions, and rule sections.
- Flattened today inner cards, buttons, timer controls, location panels, and recommendation cards so only the outer sections carry depth.
- Hid overview-only summary panels again in workout/meal modes after final CSS display rules had accidentally exposed them.
- Generated the final post-fix PDF at `artifacts/ui_screenshots_20260530_07/ui_screenshots.pdf`.
- Updated `UI_QA.md`, tests, release version, manifest, and service worker cache to `2.8.27`.

## v2.8.26 - 2026-05-30

- Added `UI_QA.md` with PDF-based today page findings and the correction plan.
- Reworked the today tab final CSS layer so summary buttons, data-quality cards, current location, equipment, recent workouts, timers, workout actions, and optional recommendations no longer fall back to bright white surfaces.
- Restored the data-quality percent ring contrast and moved workout input closer to the workout clock/rest timer flow.
- Generated a post-fix UI capture PDF at `artifacts/ui_screenshots_20260530_03/ui_screenshots.pdf` and recorded verification results.
- Updated release version, manifest, and service worker cache to `2.8.26`.

## v2.8.25 - 2026-05-30

- 오늘 화면의 장비 목록, 운동시간, 휴식 타이머, 오늘 상태, 오늘 요약 카드에 남아 있던 평면/진회색 배경을 최종 override로 정리했습니다.
- 오늘 overview 카드와 운동 모드 보조 패널들이 같은 입체 표면 체계를 쓰도록 직접 선택자를 보강했습니다.
- 앱 버전, manifest, service worker cache를 `2.8.25`로 갱신했습니다.

## v2.8.24 - 2026-05-30

- 오늘 화면이 다른 탭보다 지나치게 평면적으로 보이던 문제를 줄이기 위해 섹션, 카드, badge, input의 깊이 단계를 다시 잡았습니다.
- 오늘 화면 전용으로 layered shadow, 약한 gradient surface, hover lift를 추가해 기록형 간격은 유지하면서 입체감을 보강했습니다.
- 앱 버전, manifest, service worker cache를 `2.8.24`로 갱신했습니다.

## v2.8.23 - 2026-05-30

- 운동 집중모드 버튼이 상단 메뉴 정리 과정에서 사라진 문제를 바로잡았습니다.
- 오늘 화면 상단은 `운동/식단/요약` 3탭으로 유지하고, 운동 모드에서는 집중모드 버튼을 3탭 아래 전체 폭 보조 액션으로 다시 표시합니다.
- 앱 버전, manifest, service worker cache를 `2.8.23`으로 갱신했습니다.

## v2.8.22 - 2026-05-30

- 오늘 화면 상단 메뉴가 운동/식단/요약 3개 탭으로 항상 유지되도록 운동 모드에서만 보이던 집중 토글을 상단 메뉴에서 숨겼습니다.
- 오늘 페이지 섹션, 요약 카드, 기록 카드, badge에 약한 그림자를 더해 평면감을 줄이고 기록 페이지와 맞는 정도의 입체감을 보강했습니다.
- 앱 버전, manifest, service worker cache를 `2.8.22`로 갱신했습니다.

## v2.8.21 - 2026-05-30

- 오늘 페이지 전체의 박스 간격, 섹션 padding, summary grid, 기록 카드, 입력 패널 내부 row 간격을 기록 페이지 체계에 맞춰 재정렬했습니다.
- 날짜 선택 바, 오늘/운동/식단 모드 바, 운동/식단/요약 섹션이 같은 폭과 같은 gap으로 쌓이도록 오늘 페이지 전용 layout override를 추가했습니다.
- 앱 버전, manifest, service worker cache를 `2.8.21`로 갱신했습니다.

## v2.8.20 - 2026-05-30

- 오늘 요약 화면의 상단 요약, 핵심 요약 카드, 기록 품질, 최근 기록 카드가 기록 카드와 같은 밝은 중립 표면으로 보이도록 overview 전용 색상 override를 추가했습니다.
- 이전 수정이 운동 모드에만 적용되어 오늘 요약 화면이 그대로 보이던 범위를 바로잡았습니다.
- 앱 버전, manifest, service worker cache를 `2.8.20`으로 갱신했습니다.

## Unreleased

- 앞으로 프로젝트 변경 작업을 진행할 때 `NOTES.md`와 `CHANGELOG.md`에 작업 내용과 검증 결과를 함께 남기도록 문서 운영 규칙을 명시했습니다.
- 사용자가 `CHANGED.MD`를 언급하면 현재 저장소의 실제 변경 기록 파일인 `CHANGELOG.md`로 처리하기로 정리했습니다.
- 다음 UI 개편 flow에 카드/박스가 계층처럼 쌓이는 문제를 최우선 개선 항목으로 추가했습니다.
- UI 개편 순서를 상단 탭 경량화, 섹션 헤더 위계 정리, 카드 내부 계층 제거, 기간/필터/정렬 공통화, 빈 상태 compact화, 화면별 재검수로 정리했습니다.

## v2.8.19 - 2026-05-30

- 오늘 운동 화면의 입력 폼, 운동 빠른 선택, 세트 빌더, 운동 기록 카드 배경을 기록 카드와 같은 중립 흰회색 표면으로 맞췄습니다.
- 운동 화면 내부 row, chip, quick note, 세트 행은 더 밝은 flat 표면으로 낮춰 기록 화면과 색상 위계를 통일했습니다.
- 오늘 운동 화면의 활성 모드 버튼도 진한 회색 덩어리 대신 밝은 선택 상태로 보이도록 조정했습니다.

## v2.8.18 - 2026-05-30

- 오늘 화면의 `기록 품질` 섹션 배경을 블루그레이 계열에서 중립 흰회색 표면으로 조정했습니다.
- 기록 품질 카드, 내부 메시지, 품질 지표, 진행 바의 배경을 더 밝고 평평한 흰회색으로 맞췄습니다.
- 기록 품질 원형 지표도 강한 색 트랙 대신 부드러운 회색-녹색 트랙으로 낮췄습니다.

## v2.8.17 - 2026-05-30

- 오늘 화면의 `요약` 활성 버튼이 진한 회색 CTA처럼 보이지 않도록 밝은 블루그레이 선택 상태로 낮췄습니다.
- `기록 품질` 섹션, 품질 카드, 내부 메시지, 품질 지표, 배지 색을 더 밝은 회색 표면으로 조정했습니다.
- 기록 품질 원형 지표의 트랙과 그림자를 가볍게 조정해 카드 내부가 묵직한 회색 블록처럼 보이는 문제를 완화했습니다.

## v2.8.16 - 2026-05-30

- 오늘 화면의 모드 탭 `전체`를 `요약`으로 바꿔 현재 화면의 역할이 더 명확하게 보이도록 했습니다.
- 오늘 요약, 더보기, 데이터 센터, 실행 인사이트, 테마 미리보기의 `분석 신뢰도` 문구를 `기록 품질` 중심으로 정리했습니다.

## v2.8.15 - 2026-05-30

- 상단 탭과 분석/기록 서브탭의 비활성 상태를 더 flat하게 낮추고 활성 위치만 진한 배경으로 구분했습니다.
- 섹션 헤더, 기록 헤더, 분석 카드 헤더의 배경 박스와 그림자를 제거해 제목 영역이 카드처럼 반복되는 문제를 줄였습니다.
- 카드 내부 row, badge, pill, form, toolbar의 그림자를 제거하고 평평한 회색 표면으로 낮춰 계층처럼 쌓이는 UI를 완화했습니다.
- 바깥 카드에는 약한 그림자만 남기고 내부 중첩 카드에는 그림자를 금지하는 최종 override 규칙을 추가했습니다.

## v2.8.14 - 2026-05-30

- 더 이상 최종 UI에 필요하지 않은 초기 `ui_rebuild_01~03.css` override import를 제거하고 파일을 정리했습니다.
- 기록 카드와 식단 기록 카드의 핵심 레이아웃 계약을 최종 `ui_rebuild_05.css` 레이어로 옮겼습니다.
- 서비스워커 캐시 목록에서 제거된 override 파일을 제외하고 릴리스 버전을 `2.8.14`로 갱신했습니다.

## v2.8.13 - 2026-05-30

- 전역 폼/툴바 CSS override의 범위를 낮추고, 기록/분석/더보기/관리자 화면의 필터 패널은 페이지별 scope에서 다시 정리했습니다.
- 모바일 상단 탭, 기간 선택, 결과 툴바가 화면 밖으로 밀리지 않도록 grid 기준과 줄바꿈 기준을 보강했습니다.
- 카드 내부 badge, 빈 상태, 진행률 보조 요소의 그림자 강도를 낮춰 카드 안 카드처럼 보이는 층층 구조를 줄였습니다.
- `ui_rebuild_05.css`를 서비스워커 캐시 대상에 추가하고 릴리스 버전을 `2.8.13`으로 갱신했습니다.

## v2.8.12 - 2026-05-30

- 분석 서브메뉴의 활성 상태가 분명히 보이도록 버튼형 탭 스타일을 보강했습니다.
- 주간, 월간, 연간, PR, 운동별, 장비별 분석의 현재 분석 범위 표시줄을 추가했습니다.
- 분석 카드, 연간 월별 카드, 장비/PR/운동별 카드까지 회색 그라데이션 카드형 UI를 동일하게 적용했습니다.

## v2.8.11 - 2026-05-30

- 메뉴 탭을 버튼형 UI로 다시 정렬하고 줄간격, 글자 간격, 활성 상태를 보정했습니다.
- 오늘 기록, 날짜별 기록, 주별 기록, 일자별 식단 리스트의 카드 간격과 텍스트 대비를 재정리했습니다.
- 식단 목표 저장, 주간 계획, 분석 진입 카드, 일별 추이 카드의 배경과 그라데이션을 통일했습니다.
- 카드 내부 긴 구분선과 억지로 끼워 넣은 듯한 날짜/주차 표시를 부드러운 카드형 구조로 보정했습니다.

## v2.8.10 - 2026-05-29

- 누적된 회색/차콜 UI override를 정리해 최종 테마 레이어 하나로 재구성했습니다.
- 기록 검색, 일별 목록, 카드, 툴바, 버튼류의 색상 체계를 회색 그라데이션 기준으로 통일했습니다.
- 선색 의존을 줄이고 면 색상, 그림자, 그라데이션으로 카드 구분이 나도록 조정했습니다.
- 라운드 모서리 뒤쪽 흰 사각형이 보이지 않도록 주요 컨테이너 overflow와 배경 처리를 정리했습니다.

## v2.8.9 - 2026-05-29

- 입력, 기록, 휴식 시작 계열 버튼을 기존 차콜톤보다 조금 더 진하게 조정했습니다.
- 컨테이너 내부 카드, 행, 툴바, 칩, 목록 박스에 일관된 미세 그라데이션을 적용했습니다.
- 흰색/밝은 회색 표면 위 보조 텍스트 대비를 추가 보강했습니다.

## v2.8.8 - 2026-05-29

- 차콜 헤더와 주요 CTA 색상을 한 단계 연하게 조정했습니다.
- 입력칸, 선택칸, 세트/식단 필드 내부에 미세한 회색 그라데이션을 적용했습니다.
- 흰색 표면 위에서 약하게 보이던 보조 텍스트 대비를 보강했습니다.

## v2.8.7 - 2026-05-29

- 실제 앱 메인 UI에 차콜 헤더와 차분한 회색 표면 톤을 시범 적용했습니다.
- 상단 헤더, 탭, 섹션 헤더, 주요 저장 버튼, 기록/식단 행의 명도 체계를 조정했습니다.
- 서비스워커 캐시를 갱신해 새 CSS가 배포 후 반영되도록 했습니다.

## v2.8.6 - 2026-05-29

- 쿨 그레이 운영툴형 UI 예시 페이지를 추가했습니다.
- `/auth/theme-preview`에서 로그인 없이 회색 배경, 회색 카드, 무채색 버튼, 회색 기록/분석/식단 카드 조합을 확인할 수 있습니다.
- 예시 페이지는 기존 앱 화면에 바로 적용하지 않고 색상 방향 검토용으로 분리했습니다.

## v2.8.5 - 2026-05-29

- 전체 CSS에서 과거 다크 테마 배경 직접값을 정리했습니다.
- 분석신뢰도 원형, 기록 카드, 분석 카드, 식단 입력/목록, 더보기 카드에 남아 있던 검은색/짙은 남색 배경을 회색톤 UI로 교체했습니다.
- `ui_rebuild_01.css`, `ui_rebuild_02.css`, `ui_rebuild_03.css`에 남아 있던 예전 다크 override를 밝은 회색 계열로 수정했습니다.
- CSS 정적 테스트에 레거시 다크 표면 색상과 밝은 글씨 토큰 재유입 방지 검사를 추가했습니다.
- `VERSION`, manifest, service worker cache를 `2.8.5`로 갱신했습니다.

## v2.8.4 - 2026-05-29

- 식단 입력, 수정, 삭제, 복사, 즐겨찾기, 템플릿 폼에 CSRF 토큰을 보강했습니다.
- 회색톤 UI override를 추가해 카드, 패널, 버튼, 입력칸의 기본 배경과 글자색을 정리했습니다.
- 식단 저장 플로우 테스트를 보강했습니다.

## v2.8.3 - 2026-05-29

- 서버 재시작 후 오래된 공개 CSRF 토큰으로 로그인하면 Bad Request가 발생하던 문제를 수정했습니다.
- 로그인과 회원가입 같은 공개 POST는 토큰을 갱신하고 인증 흐름을 계속 진행하도록 조정했습니다.

## v2.8.2 - 2026-05-29

- 회색톤 테마가 배경에만 적용되지 않도록 버튼, 카드, 탭, 리스트, 입력칸의 내부 배경을 정리했습니다.

## v2.8.1 - 2026-05-29

- 화면 전체 기본 톤을 어두운 색상에서 밝은 회색 계열로 전환했습니다.
- PWA theme color, manifest 배경색, service worker cache를 갱신했습니다.

## v2.8.0 - 2026-05-29

- 실행 인사이트에 개인화 다음 운동 카드를 추가했습니다.
- 최근 운동 기록을 기반으로 다음 운동 초점과 목표 힌트를 제안하도록 개선했습니다.
- 개인화 계산 로직을 `health_tracker/services/personalization.py`로 분리했습니다.
