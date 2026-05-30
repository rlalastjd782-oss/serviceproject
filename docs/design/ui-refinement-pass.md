# UI Refinement Pass Design

## 1. 화면 목적

이번 디자인 작업은 새 기능 추가가 아니라 기존 헬스 트래커 UI의 사용 흐름과 시각 위계를 바로잡는 1차 정리 작업이다. 사용자는 모바일에서 오늘 운동/식단을 빠르게 기록하고, 기록/분석/더보기에서는 현재 범위와 결과를 막힘 없이 확인해야 한다.

우선순위는 오늘 화면이다. 특히 운동 모드에서 `운동 시간 -> 휴식 타이머 -> 빠른 이동 -> 운동 입력 -> 오늘 운동 기록`의 순서가 첫 흐름으로 읽혀야 한다.

## 2. 사용자 흐름

오늘 요약:

1. 날짜를 선택한다.
2. 운동/식단/요약 모드를 전환한다.
3. 오늘의 핵심 지표와 데이터 품질을 확인한다.
4. 최근 기록이 있으면 상세 화면으로 이동한다.
5. 기록이 없으면 운동 또는 식단 입력으로 바로 이동한다.

오늘 운동:

1. 날짜와 운동 모드를 확인한다.
2. 운동 시간을 시작하거나 저장한다.
3. 필요하면 휴식 타이머를 켠다.
4. `운동 추가`로 입력 폼을 열고 세트를 저장한다.
5. `오늘 운동`에서 운동별 세트 요약을 확인하고, 필요한 카드만 펼친다.
6. 루틴, 위치, 추천, 회복 상태는 첫 입력 흐름 이후의 보조 영역으로 둔다.

오늘 식단:

1. 칼로리 목표와 현재 섭취량을 확인한다.
2. 식단 입력 폼을 열고 음식 row를 저장한다.
3. 오늘 식단 기록을 확인한다.
4. 식단 조합, 지난 식단 복사, 즐겨찾기는 보조 영역에서 사용한다.

기록/분석/더보기:

1. 현재 기간/필터를 먼저 확인한다.
2. 결과 수와 정렬/표시 옵션을 확인한다.
3. 목록 또는 카드 결과를 스캔한다.
4. 결과가 없으면 compact empty state에서 다음 행동을 선택한다.

## 3. 레이아웃 구조

공통:

- 본문은 기존 최대 760px 모바일 중심 레이아웃을 유지한다.
- 최상위 정보 묶음만 `.section` 카드로 보이게 한다.
- `.section` 내부의 row, chip, badge, form block은 그림자 없는 flat surface로 낮춘다.
- 카드 안에 카드처럼 보이는 중첩 배경은 피하고, 내부 구획은 border, divider, gap으로만 나눈다.
- 전체 회색화는 금지한다. 주요 section은 흰색 표면을 유지하고 내부 보조 요소에만 옅은 gray-blue를 쓴다.

오늘 화면 상단:

- `.date-row`와 `.today-mode-actions`는 한 화면의 컨트롤 그룹처럼 연속해서 보여야 한다.
- 활성 모드는 `btn-primary`, 비활성 모드는 `btn-small`로 유지하되 active 대비를 더 분명히 둔다.
- 좁은 화면에서 mode button은 최소 높이 38px을 유지하고, 라벨이 잘리면 줄바꿈보다 짧은 한글 라벨을 우선한다.

오늘 운동 권장 순서:

1. `.date-row`
2. `.today-mode-actions`
3. `.workout-clock-section`
4. `#rest-timer`
5. `.workout-action-dock`
6. `#workout-input`
7. `#today-workout`
8. `.workout-location-section`
9. `.next-action-section`
10. `.workout-plan-section`, `.routine-library-section`, 회복/추천/도구 등 보조 섹션

오늘 식단 권장 순서:

1. `.date-row`
2. `.today-mode-actions`
3. `.meal-goal-section`
4. `.meal-input-section`
5. `.today-meal-section`
6. `.meal-helper-section`

## 4. 주요 컴포넌트

`section`

- 바깥 카드 역할만 담당한다.
- radius는 기존 8-10px 체계를 유지한다.
- section 배경은 `#ffffff` 또는 `var(--panel)`을 기본으로 한다.
- section 간 간격은 모바일에서 10-14px 범위로 통일한다.

`section-header`

- 제목, 보조 설명, 우측 액션의 역할을 분명히 나눈다.
- 하위 section에서는 어두운 헤더 박스를 쓰지 않고 텍스트 헤더만 둔다.
- 우측 badge가 좁은 화면에서 잘리면 제목 아래로 내려간다.

`timer-actions`

- 운동 시간/휴식 타이머 버튼은 같은 높이와 같은 gap을 가진다.
- `저장`은 primary, `초기화/정지/삭제`는 danger, 나머지는 secondary로 구분한다.
- 버튼이 4개 이상이면 모바일에서 2열 grid로 내려가도 된다.

`workout-action-dock`

- 운동 모드에서만 sticky 빠른 이동으로 유지한다.
- 내부 버튼은 작은 카드처럼 만들지 말고 flat segmented action으로 처리한다.
- focus mode에서 항목이 늘어나도 동일한 높이를 유지한다.

`record-card.workout-summary-card`

- 기본 상태는 접힌 summary row다.
- 운동명, 부위 badge, 세트 수, 장비, PR 여부만 먼저 보여준다.
- 세트 미리보기는 flat pill button으로 표시한다.
- 펼친 상세 영역은 별도 카드 배경을 반복하지 않고 divider와 form group으로 구분한다.

`goal-card`

- 목표 진행률은 section 내부의 주요 정보이지만 또 다른 큰 카드처럼 보이지 않게 한다.
- 진행률 숫자, bar, 목표 수정 form은 compact row로 묶는다.
- 오늘 식단 목표는 1개 primary goal로 보이고, 여러 목표 목록은 2열 compact grid 또는 접이식 영역으로 둔다.

`result-toolbar`

- 기록/분석/장비/검색 페이지에서 공통으로 사용한다.
- 결과 수는 좌측, 정렬/표시/초기화는 우측에 둔다.
- 모바일에서 우측 도구가 길면 2열로 wrap하되 label과 select가 세로로 쪼개지지 않게 한다.

`empty` / `compact-empty`

- 빈 상태는 큰 카드 반복 대신 한 줄 안내와 다음 행동 버튼 조합으로 구성한다.
- 오늘 운동 빈 상태: `운동 기록 없음` + `운동 추가` 액션.
- 오늘 식단 빈 상태: `식단 기록 없음` + `입력 열기` 액션.
- 분석/검색 빈 상태: 필터 초기화 또는 기간 변경 액션.

## 5. 상태별 UI

기본 상태:

- 흰 section 위에 제목, 수치, 입력/목록을 명확히 배치한다.
- 내부 row/chip/pill은 `var(--panel-2)` 또는 아주 옅은 gray-blue만 사용한다.
- badge와 chip에는 강한 shadow를 주지 않는다.

활성 상태:

- 최상위 탭 active는 현재처럼 파란 하단선과 파란 텍스트를 유지한다.
- 모드/필터 active는 배경, border, 텍스트 색 3가지 중 최소 2가지로 구분한다.
- 주요 CTA는 active tab과 혼동되지 않도록 버튼 면적과 위치로 행동 버튼임을 드러낸다.

입력 중 상태:

- 접힌 입력 폼은 section header 우측 `운동 추가`, `입력 열기` 버튼으로 연다.
- 펼친 입력 폼은 section 안에서 하나의 form panel처럼 보이되, 내부 row마다 별도 카드 그림자를 만들지 않는다.
- 저장/닫기 액션은 form 하단에 sticky가 아니라 일반 row로 둔다.

저장 중/저장 완료 상태:

- 운동 시간의 `저장 대기`, 저장 중, 저장 완료 상태는 timer display 아래 작은 status text로 유지한다.
- 비동기 저장 실패는 status text와 하단 toast를 함께 사용한다.
- 저장 중 버튼은 disabled와 label 변경을 함께 제공한다.

빈 상태:

- 신규 사용자에게 빈 summary card를 여러 개 쌓지 않는다.
- 오늘 화면에서는 빈 상태보다 입력 CTA가 먼저 보여야 한다.
- 빈 상태 문구는 짧게, 다음 행동은 하나만 명확히 둔다.

에러 상태:

- 폼 validation 에러는 해당 입력 row 가까이에 표시한다.
- danger 색은 삭제/초기화/오류에만 사용한다.
- section 전체를 붉게 만들지 않는다.

읽기 전용/방문자 상태:

- 쓰기 버튼과 post form은 숨김 또는 disabled 처리한다.
- 읽기 가능한 요약, 기록, 분석 구조는 유지한다.
- 빈 상태가 쓰기 액션만 안내하지 않도록 읽기 전용 문구를 별도로 둔다.

## 6. 반응형 기준

- 모바일 기준 폭은 390px 전후를 우선 검증한다.
- 본문 padding은 10-14px 범위에서 유지한다.
- 버튼/input 높이는 38-44px 범위로 통일한다.
- 3개 이상의 버튼 그룹은 좁은 화면에서 2열 grid 또는 가로 스크롤 segmented control 중 하나로 정한다.
- `month-picker-form-wide`, `date-picker-form`, `list-toolbar`, `compact-select`는 label과 control이 분리되어 줄 단위로 깨지지 않아야 한다.
- 긴 운동명, 음식명, 장소명, 파일명은 2줄 wrap 또는 ellipsis/clamp 기준을 둔다.
- sticky header, tabs, workout dock이 겹치지 않도록 `scroll-padding-top`을 유지한다.

## 7. 접근성 고려사항

- 날짜 이동, 기간 이동, 운동/식단 모드, 타이머 버튼에는 목적이 드러나는 `aria-label`을 유지한다.
- record card 펼침 버튼은 `aria-expanded` 상태를 정확히 갱신해야 한다.
- 세트 미리보기 pill button은 몇 세트인지와 수정 동작을 label로 제공한다.
- 색상만으로 PR, 완료, 오류를 표시하지 말고 텍스트도 함께 제공한다.
- 삭제/초기화 버튼은 danger 색과 명확한 라벨을 같이 사용한다.
- touch target은 최소 34px 이상, 주요 입력/저장 버튼은 40px 이상을 유지한다.

## 8. 개발 전달사항

우선 구현 범위:

1. 오늘 운동 화면의 flex/order를 위 권장 순서로 고정한다.
2. 오늘 화면에서 바깥 `.section`만 카드로 두고 내부 row/chip/form block의 shadow와 강한 배경을 제거한다.
3. 운동 시간, 휴식 타이머, 운동 입력, 오늘 운동 기록의 spacing과 button height를 통일한다.
4. 오늘 식단 목표/입력/기록 순서를 유지하고, 목표 카드는 compact goal로 낮춘다.
5. 기록/분석/더보기의 `result-toolbar`, 기간 선택, 빈 상태에 같은 규칙을 적용한다.

CSS 구현 원칙:

- 최근 override를 계속 누적하기보다 범위가 넓은 selector를 먼저 감사한다.
- 위험한 전역 selector는 페이지 래퍼로 scope를 좁힌다: `.filter-form`, `.list-toolbar`, `.compact-select`, `.month-picker-form-wide`, `.detail-row`, `.record-summary .badge`.
- 오늘 화면 전용 수정은 `.today-shell` 또는 모드 클래스 안으로 제한한다.
- PWA 캐시 영향이 있으므로 개발 완료 시 `VERSION`, service worker cache 갱신 필요 여부를 확인한다.

검증 기준:

- `03_today_overview`, `04_today_workout`, `05_today_meal`, `06_records_daily`를 먼저 비교한다.
- 운동 화면 긴 스크롤 캡처에서 타이머/휴식/입력/오늘 운동 순서가 유지되는지 확인한다.
- 모바일 390px 전후에서 상단 탭, 날짜 컨트롤, mode button, filter toolbar가 잘리지 않는지 확인한다.
- 빈 상태와 오류 상태가 section/card 규칙을 깨지 않는지 확인한다.

## 개발 요약

- 오늘 화면은 흰 section + flat 내부 요소 방향으로 정리한다.
- 운동 모드는 타이머, 휴식, 빠른 이동, 입력, 오늘 운동 순서가 최우선이다.
- 카드 중첩감을 만드는 내부 shadow/background를 줄인다.
- active/primary/danger/empty/loading 상태를 명확히 구분한다.
- 공통 toolbar와 기간 선택은 전역 selector 누적 대신 페이지별 scope로 정리한다.
