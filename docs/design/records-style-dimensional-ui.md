# 기록탭 스타일 기준 전체 UI 입체감 통일 디자인

## 1. 목적

오늘탭, 기록탭, 분석탭, 더보기탭이 같은 제품의 화면처럼 보이도록 카드 깊이, 표면 색, 컨트롤 상태, 간격 규칙을 통일한다. 이번 변경의 기준점은 기록탭의 일간 기록 카드와 검색 결과 카드이며, 오늘탭은 운동/식단 입력 흐름을 유지한 채 같은 입체감 체계로 맞춘다.

핵심 목표는 다음 세 가지다.

- 오늘탭과 기록탭을 나란히 봤을 때 카드의 밝기, 그림자, 테두리, 간격이 같은 계열로 보인다.
- 전체 화면을 회색으로 덮지 않고, 흰 표면과 낮은 채도의 보조 표면으로 깊이를 만든다.
- 내부 row, chip, badge, input은 바깥 카드보다 낮은 깊이로 보여 중첩 카드처럼 과하게 떠 보이지 않는다.

## 2. 기준 화면

1순위 기준 화면은 기록탭의 날짜별 기록과 기록 검색이다.

- `health_tracker/templates/summaries/_daily_records.html`
  - `.section`, `.period-filter-form`, `.record-list-toolbar`, `.daily-record-card`, `.daily-metric`
- `health_tracker/templates/records/search.html`
  - `.record-search-dashboard`, `.record-search-form`, `.record-filter-details`, `.record-result-card`, `.record-result-value`
- `health_tracker/templates/today/index.html`
  - `.today-shell`, `.date-row`, `.today-mode-actions`, `.section`, `.workout-action-dock`, `.workout-form`, `.meal-form`, `.record-card`
- `health_tracker/templates/more/index.html`
  - `.more-section`, `.more-group-section`, `.more-link-card`

분석탭과 더보기탭은 같은 규칙을 확산 적용하는 범위다. 별도 테마처럼 보이는 색상/그림자/간격이 있으면 공통 표면 규칙으로 흡수한다.

## 3. 공통 깊이 규칙

| 단계 | 용도 | 시각 규칙 | 대표 클래스 |
|---|---|---|---|
| Page | 앱 배경 | 밝은 gray-blue 배경. 화면 전체를 진한 회색으로 채우지 않음 | `body`, `.content`, `.today-shell` |
| Surface 1 | 바깥 섹션 카드 | 흰색 또는 거의 흰 표면, 1px soft border, 부드러운 shadow | `.section`, `.record-search-dashboard`, `.more-group-section` |
| Surface 2 | 내부 정보 카드 | 아주 옅은 gray-blue 표면, shadow 없음 또는 매우 약한 shadow | `.daily-record-card`, `.summary-card`, `.more-link-card`, `.record-result-card` |
| Surface 3 | 내부 row/chip/input | 낮은 대비의 inset 표면, shadow 없음, border로만 구분 | `.daily-metric`, `.badge`, `.cat-badge`, `input`, `select`, `.detail-row` |
| Active | 현재 선택/주요 액션 | 어두운 blue-gray 또는 강한 대비 표면, 흰 텍스트, 보조 shadow | `.tab-btn.active`, `.btn-primary`, `.mode-button.btn-primary`, `.record-subnav a.active` |

개발 시 새 토큰을 추가한다면 기존 변수와 충돌하지 않도록 아래 의미를 유지한다.

- `--surface-page`: 화면 배경
- `--surface-card`: 바깥 카드
- `--surface-card-soft`: 내부 카드
- `--surface-control`: row, chip, input, toolbar
- `--surface-border`: 낮은 대비 테두리
- `--surface-shadow`: 바깥 카드용 shadow
- `--surface-shadow-active`: 활성/주요 액션용 shadow

## 4. 화면별 설계

### 오늘탭

오늘탭은 작업형 화면이므로 순서와 흐름을 바꾸지 않는다. 변경 대상은 표면, 간격, 활성 상태다.

- 날짜 선택 `.date-row`는 기록탭의 필터 바와 같은 Surface 1로 처리한다.
- 모드 전환 `.today-mode-actions`는 기록탭의 subnav/필터와 같은 컨트롤 그룹으로 보이게 한다.
- 선택된 모드의 `.mode-button.btn-primary`는 기록탭 활성 필터와 같은 강도여야 한다.
- 운동 시간, 휴식 타이머, 운동 입력, 오늘 운동 기록, 식단 입력, 오늘 식단 기록은 모두 Surface 1 섹션 안에 놓는다.
- 세트 row, 식단 row, badge, quick chip은 Surface 3으로 낮추고 shadow를 제거한다.
- 오늘탭 요약 모드의 `.summary-grid.overview-only`는 독립 카드처럼 떠 보이되 기록탭의 `.record-list`와 같은 간격을 유지한다.
- `workout-mode`와 `meal-mode`에서는 현재 순서를 유지한다.
  - 운동: 날짜, 모드, 운동 시간, 휴식 타이머, 빠른 이동, 운동 입력, 오늘 운동 기록, 위치/추천/루틴/회복
  - 식단: 날짜, 모드, 칼로리 목표, 식단 입력, 오늘 식단 기록, 식단 보조 영역

### 기록탭

기록탭은 이번 작업의 기준점이다.

- 날짜별 기록의 필터 섹션은 Surface 1, 기간 버튼과 정렬 컨트롤은 Surface 3으로 둔다.
- `.daily-record-card`와 `.record-result-card`는 Surface 2로 유지하되, 바깥 `.section`보다 shadow가 약해야 한다.
- `.daily-metric`과 `.record-result-value`는 내부 정보 block이므로 Surface 3으로 보이게 한다.
- 검색 결과 빈 상태는 큰 회색 덩어리가 아니라 Surface 2 안의 compact empty로 정리한다.

### 분석탭

분석탭은 이미 `analysis-dashboard-section`, `yearly-dashboard-section`, `equipment-dashboard-section`, `pr-hero-section` 등 큰 표면이 많다.

- dashboard section은 Surface 1로 통일한다.
- metric card, rank card, month card, PR card는 Surface 2로 맞춘다.
- action grid와 period/filter form은 카드가 아니라 컨트롤 그룹으로 처리한다.
- 그래프 track, progress bar, metric badge는 Surface 3으로 낮춘다.
- 분석 subnav의 active 상태는 오늘 모드 버튼과 동일한 대비를 사용한다.

### 더보기탭

더보기는 진입 카드가 많아 전체가 카드 묶음처럼 보이기 쉽다.

- `.more-group-section`만 Surface 1로 떠 보이게 한다.
- `.more-link-card`는 Surface 2로 처리하고 내부 `b`, `strong`, `span`은 별도 카드처럼 보이지 않게 한다.
- 개별 기능 페이지의 filter/form/list도 기록탭 규칙을 따른다.

## 5. 상태별 UI

- 기본: 흰 바깥 카드와 부드러운 border/shadow를 사용한다.
- 활성/선택: 배경, 텍스트, shadow 중 최소 두 가지가 바뀌어야 한다. `btn-primary`와 active nav는 같은 시각 강도를 쓴다.
- hover/focus: hover는 밝은 표면 변화로 충분하며, keyboard focus는 `outline` 또는 `box-shadow`로 2px 이상 보여야 한다.
- 입력 중: input/select/textarea는 흰색 또는 아주 밝은 control 표면, focus 시 border 대비를 높인다.
- 저장 중: 버튼은 disabled opacity만 낮추지 말고 label 또는 상태 text로 진행 중임을 표시한다.
- 저장 완료: 기존 toast/status text를 유지하고, 카드 전체 색을 바꾸지 않는다.
- 빈 상태: Surface 2 또는 Surface 3 안에서 compact 안내와 다음 행동 버튼을 제공한다.
- 오류 상태: 해당 row나 field 주변에 짧은 오류 문구와 danger border를 표시한다. section 전체를 danger 배경으로 덮지 않는다.
- 읽기 전용: 쓰기 액션만 disabled/숨김 처리하고, 요약/기록 카드의 표면 규칙은 동일하게 유지한다.

## 6. 반응형 기준

- 기준 검증 너비는 390px, 430px, 560px, desktop이다.
- 390px에서 상단 탭은 3열 이하로 줄바꿈되어야 하며 글자가 겹치면 안 된다.
- 오늘탭 모드 버튼은 기본 3열, 운동 모드에서 4개가 부담되면 2열로 접는다.
- 기록 검색 필터는 모바일에서 1열로 쌓고, 버튼/입력 높이는 최소 38px을 유지한다.
- `.record-result-card`는 모바일에서 값 영역이 오른쪽에 고정되어 본문을 압박하면 1열 전환을 허용한다.
- 카드 간격은 모바일 9-12px, desktop 12-14px 범위로 유지한다.
- shadow가 리스트 밀도를 해치면 내부 카드 shadow를 먼저 줄이고, 바깥 section shadow는 유지한다.

## 7. 접근성 고려사항

- 현재 위치는 색상만으로 구분하지 않고 active class의 배경/텍스트 대비를 함께 사용한다.
- 모든 입력은 기존 `aria-label`을 유지하고, 상세 필터 `summary`는 접힘 상태에서도 목적이 드러나야 한다.
- 삭제/정지/초기화 같은 위험 액션은 primary와 다른 색 계열 또는 명확한 label을 유지한다.
- 작은 chip과 badge의 텍스트 대비는 배경 대비 4.5:1에 가깝게 맞춘다.
- `focus-visible` 스타일을 전역에서 제거하지 않는다.

## 8. 개발 전달사항

- `health_tracker/templates/layouts/base.html` 기준 CSS 로드 순서는 `styles.css`, `today.css`, `feature_pages.css`, `meal.css`, `records.css`, `analysis.css`, `responsive.css`, `rules.css`, `ui_rebuild.css` 순서다. 최종 표면 규칙은 마지막 override에서 실제로 이겨야 한다.
- 현재 `static/css/overrides/ui_rebuild_05.css`에 오늘탭 전용 reset이 길게 누적되어 있다. 새 규칙은 가능하면 공통 surface token 또는 공통 selector로 정리하고, 오늘탭만 예외 처리하는 범위를 줄인다.
- 오늘탭의 `v2.8.28 today visual reset`은 흰 카드 방향이라 유지할 수 있지만, 기록탭 Surface 1/2/3 규칙과 수치가 달라 보이면 공통화한다.
- 전역 selector로 모든 `button`, `input`, `.section`을 덮는 방식은 회귀 위험이 크다. `.today-shell`, `.record-search-dashboard`, `.analysis-dashboard-section`, `.more-group-section`처럼 화면 래퍼 기준으로 범위를 좁힌다.
- 변경 후 `VERSION`과 service worker cache 갱신 필요 여부를 확인한다. 사용자가 “변경이 안 됨”을 이미 지적했으므로 캐시 반영 검증은 필수다.
- 개발 완료 시 오늘 요약, 오늘 운동, 오늘 식단, 기록 일별, 기록 검색, 분석 주간, 더보기 첫 화면을 같은 모바일 너비 기준의 DOM/HTML/CSS 조건으로 비교한다.
- PNG/JPG/WebP 이미지와 스크린샷 파일은 생성하지 않는다.

## 9. 완료 판정 기준

- 오늘탭과 기록탭의 바깥 카드가 같은 깊이로 보인다.
- 오늘탭 내부 row/chip/input이 바깥 카드와 같은 높이로 떠 보이지 않는다.
- 기록탭 기준의 밝은 카드 표면이 분석/더보기까지 유지된다.
- active 탭, active mode, active filter가 같은 강도로 보인다.
- 모바일 기준 DOM/HTML/CSS 검증에서 한글 라벨, 숫자, 버튼이 겹치거나 잘리지 않는다.
- 캐시 갱신 후 버전, CSS 적용 순서, 주요 selector 계산값에서 변경이 확인된다.
