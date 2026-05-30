# UI QA - 2026-05-30

## Capture Set

- Baseline PDF: `artifacts/ui_screenshots_20260530_02/ui_screenshots.pdf`
- Baseline PNG folder: `artifacts/ui_screenshots_20260530_02/png/`
- Reviewed screens: `03_today_overview.png`, `04_today_workout.png`, `05_today_meal.png`, `06_records_daily.png`

## Baseline Findings

### Today Overview

- The `요약` mode button looked detached from the rest of the segmented control because the active button was still too pale and pill-like.
- The data-quality ring existed in the DOM, but the final CSS layer made the progress contrast too weak, so it looked like the percent ring had disappeared.
- The data-quality internal cards and metric rows used too many white surfaces, creating the same stacked-card problem reported by the user.
- The record-add and quality action controls looked like text floating inside the page instead of connected controls.

### Today Workout

- The current-location panel, equipment strip, recent workout list, and badges still had bright white backgrounds.
- The recent workout panel shape was too rectangular and did not match the surrounding cards.
- The workout clock, rest timer, action dock, and workout input were visually separated by too many intervening blocks.
- The workout timer display and start/pause/save/reset controls were too flat or too white compared with the rest of the page.
- The additional recommendation panel was also too white and did not fit the neutral gray surface system.

### Today Meal

- The meal tab was more stable than the workout tab, but its inner panels still used the same pale card treatment as the today overview.
- No urgent layout break was found in the reviewed capture.

### Records Reference

- `06_records_daily.png` remains the closest reference for the target direction: compact spacing, stronger active controls, and fewer random white blocks.
- Today should follow that direction without copying the record page literally.

## Applied Plan

- Add a scoped `v2.8.26` CSS audit layer for `.today-shell`.
- Replace remaining white today surfaces with neutral gray panel/card tokens.
- Restore data-quality ring visibility with a final `conic-gradient` rule.
- Tighten workout flow by moving `#workout-input` directly after the workout clock, rest timer, and action dock.
- Normalize current location, equipment, recent workout, timer controls, optional recommendations, and record-add buttons.
- Bump release assets to `2.8.26` so the browser and service worker request the updated CSS.

## Verification Notes

- Post-fix PDF: `artifacts/ui_screenshots_20260530_03/ui_screenshots.pdf`
- Post-fix PNG folder: `artifacts/ui_screenshots_20260530_03/png/`
- Reviewed post-fix screens: `03_today_overview.png`, `04_today_workout.png`, `05_today_meal.png`, `06_records_daily.png`
- The data-quality percent ring is visible again in the today overview capture.
- The today overview and workout visible panels now use a consistent neutral gray surface instead of the previous bright-white card stack.
- The workout mode top capture shows the segmented mode control, focus mode row, action cards, and workout closet cards using the same surface family.
- Remaining broader page issues outside this pass, such as the global mobile header/navigation density, are already noted in `UI_QA_FINDINGS_2026-05-30.md` and should be handled as a separate layout pass.

## Verification Commands

- `python -m unittest tests.test_static_assets -v`
- `python tools/check_release.py`
- `python -m unittest tests.test_ui_navigation_flows.UiNavigationFlowTest.test_fold_ui_regression_markers_render tests.test_ui_navigation_flows.UiNavigationFlowTest.test_main_pages_render -v`
- `python -m ruff check health_tracker tests tools`
- `python -m compileall health_tracker tests tools`
- `python -m unittest discover -v`
