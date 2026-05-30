# Codex Handoff Notes

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

- 현재 버전: `2.8.13`
- 기본 브랜치: `main`
- 커밋 메시지는 한국어로 작성합니다.
- 작업 완료 후 `NOTES.md`, `CHANGELOG.md`, `VERSION`, manifest, service worker cache를 함께 갱신합니다.
- 브라우저는 사용자가 요청할 때만 엽니다.

## 최근 작업

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
