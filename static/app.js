if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      navigator.serviceWorker.register("/static/sw.js").catch(() => {});
    });
  });
}

const exerciseQuickPanel = document.querySelector("[data-exercise-quick-panel]");
const appPreferenceElement = document.querySelector("[data-app-preferences]");
const appPreferences = parseJsonData(appPreferenceElement, "appPreferences");
const bodyPartClassMap = parseJsonData(appPreferenceElement, "bodyPartClasses");
const mealTypeClassMap = parseJsonData(appPreferenceElement, "mealTypeClasses");
const setTypeOptions = Array.isArray(appPreferences.set_type_options) && appPreferences.set_type_options.length
  ? appPreferences.set_type_options
  : ["본세트"];
const exerciseQuickList = document.querySelector("[data-exercise-quick-list]");
const exerciseQuickEmpty = document.querySelector("[data-exercise-quick-empty]");
const workoutQuickTabs = document.querySelectorAll("[data-workout-quick-tab]");
const workoutQuickPanes = document.querySelectorAll("[data-workout-quick-pane]");
const recentSetTitle = document.querySelector("[data-recent-set-title]");
const recentSetList = document.querySelector("[data-recent-set-list]");
const exerciseDatalist = document.querySelector("[data-exercise-datalist]");
const workoutForm = document.querySelector("[data-workout-form]");
const exerciseNameInput = workoutForm?.querySelector("[data-workout-exercise-input]");
const exercisesByBodyPart = parseExerciseQuickData();
const recentSetsByExercise = parseJsonData(exerciseQuickPanel, "recentSetsByExercise");
const exerciseStatsByName = parseJsonData(exerciseQuickPanel, "exerciseStatsByName");
const overloadSuggestions = parseJsonData(exerciseQuickPanel, "overloadSuggestions");
const nextSetSuggestions = parseJsonData(exerciseQuickPanel, "nextSetSuggestions");
const exerciseNotes = parseJsonData(exerciseQuickPanel, "exerciseNotes");
const exerciseSettings = parseJsonData(exerciseQuickPanel, "exerciseSettings");
const overloadSuggestionView = document.querySelector("[data-overload-suggestion]");
const nextSetAdviceView = document.querySelector("[data-next-set-advice]");
const exerciseStatView = document.querySelector("[data-exercise-stat-view]");
const exerciseNoteView = document.querySelector("[data-exercise-note-view]");
const exerciseTargetView = document.querySelector("[data-exercise-target-view]");
const readinessForm = document.querySelector("[data-readiness-form]");
const readinessCoach = document.querySelector("[data-readiness-coach]");
const foodQuickPanel = document.querySelector("[data-food-quick-panel]");
const foodQuickList = document.querySelector("[data-food-quick-list]");
const foodQuickEmpty = document.querySelector("[data-food-quick-empty]");
const foodsByMealType = parseJsonData(foodQuickPanel, "foodsByMealType");
initWorkoutClock();
restoreSavedScrollPosition();
scrollActiveTabIntoView();
initWorkoutTools();
initSetBuilder();
renderReadinessCoach();
processOfflineQueue();
initNotificationTools();

document.querySelectorAll("[data-body-part-select]").forEach((select) => {
  applyBodyPartSelectColor(select);
  if (select.closest("[data-workout-form]")) {
    renderExerciseQuickList(select.value);
    applyWorkoutInputMode(select.value);
  }
});
document.querySelectorAll("[data-meal-type-select]").forEach((select) => {
  applyMealTypeSelectColor(select);
  renderFoodQuickList(select.value);
});

document.addEventListener("change", (event) => {
  if (event.target.matches('select[name="set_weight_unit"]')) {
    updateSetWeightPreviews();
    return;
  }

  const bodyPartSelect = event.target.closest("[data-body-part-select]");
  if (bodyPartSelect) {
    applyBodyPartSelectColor(bodyPartSelect);
    if (bodyPartSelect.closest("[data-workout-form]")) {
      renderExerciseQuickList(bodyPartSelect.value);
      applyWorkoutInputMode(bodyPartSelect.value);
    }
    return;
  }

  const mealTypeSelect = event.target.closest("[data-meal-type-select]");
  if (mealTypeSelect) {
    applyMealTypeSelectColor(mealTypeSelect);
    renderFoodQuickList(mealTypeSelect.value);
    return;
  }

  if (event.target === exerciseNameInput) {
    renderRecentSetList(exerciseNameInput.value);
    renderExerciseGuidance(exerciseNameInput.value);
  }
});

document.addEventListener("input", (event) => {
  if (event.target.closest("[data-set-count-input]")) {
    syncSetRowsToCount();
  }
  if (event.target.matches('input[name="set_weight"], select[name="set_weight_unit"]')) {
    updateSetWeightPreviews();
  }
  if (event.target.closest("[data-plate-tool]") || event.target.closest("[data-warmup-tool]")) {
    renderWorkoutTools();
  }
  if (event.target.closest("[data-readiness-form]")) {
    renderReadinessCoach();
  }
});

document.addEventListener("submit", (event) => {
  const form = event.target.closest("form");
  attachCsrfToken(form);
  const confirmMessage = form?.dataset.confirmSubmit;
  if (confirmMessage && !window.confirm(confirmMessage)) {
    event.preventDefault();
    return;
  }
  if (queueOfflineForm(form, event)) {
    return;
  }
  if (form?.method?.toLowerCase() === "post" && !form.dataset.noScrollRestore) {
    saveScrollPosition();
  }

  const durationForm = event.target.closest(".duration-edit-form");
  if (!durationForm || !document.querySelector("[data-workout-clock]")) {
    return;
  }
  const action = event.submitter?.getAttribute("value");
  const hours = Number(durationForm.querySelector('input[name="duration_hours"]')?.value || 0);
  const minutes = Number(durationForm.querySelector('input[name="duration_minutes"]')?.value || 0);
  const durationSeconds = action === "reset" ? 0 : Math.max(0, hours * 3600 + minutes * 60);
  saveWorkoutClock({ startedAt: null, elapsedMs: durationSeconds * 1000, manualStarted: false });
});

function attachCsrfToken(form) {
  if (!form || form.method?.toLowerCase() !== "post") {
    return;
  }
  const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";
  if (!token) {
    return;
  }
  let input = form.querySelector('input[name="csrf_token"]');
  if (!input) {
    input = document.createElement("input");
    input.type = "hidden";
    input.name = "csrf_token";
    form.append(input);
  }
  input.value = token;
}

window.addEventListener("online", () => {
  processOfflineQueue();
});

document.addEventListener("click", (event) => {
  const addSetButton = event.target.closest("[data-add-set-row]");
  const removeSetButton = event.target.closest("[data-remove-set-row]");
  const addMealButton = event.target.closest("[data-add-meal-row]");
  const removeMealButton = event.target.closest("[data-remove-meal-row]");
  const editButton = event.target.closest("[data-toggle-edit]");
  const openSetEditButton = event.target.closest("[data-open-set-edit]");
  const cancelEditButton = event.target.closest("[data-cancel-edit]");
  const inlineAddButton = event.target.closest("[data-toggle-add]");
  const inlineAddCancelButton = event.target.closest("[data-cancel-inline-add]");
  const detailButton = event.target.closest("[data-toggle-detail]");
  const workoutQuickTab = event.target.closest("[data-workout-quick-tab]");
  const quickExerciseButton = event.target.closest("[data-exercise-name]");
  const applyNextSetButton = event.target.closest("[data-apply-next-set]");
  const recentSetButton = event.target.closest("[data-load-recent-sets]");
  const copySetButton = event.target.closest("[data-copy-set-row]");
  const copySavedSetButton = event.target.closest("[data-copy-saved-set]");
  const setCountPresetButton = event.target.closest("[data-set-count-preset]");
  const fillWeightButton = event.target.closest("[data-fill-weight]");
  const rampWeightButton = event.target.closest("[data-ramp-weight]");
  const foodQuickButton = event.target.closest("[data-food-entry]");
  const restButton = event.target.closest("[data-rest-seconds]");
  const restStopButton = event.target.closest("[data-rest-stop]");
  const workoutClockStartButton = event.target.closest("[data-workout-clock-start]");
  const workoutClockPauseButton = event.target.closest("[data-workout-clock-pause]");
  const workoutClockSaveButton = event.target.closest("[data-workout-clock-save]");
  const workoutClockResetButton = event.target.closest("[data-workout-clock-reset]");
  const workoutFormToggleButton = event.target.closest("[data-toggle-workout-form]");
  const workoutFormCancelButton = event.target.closest("[data-cancel-workout-form]");
  const mealFormToggleButton = event.target.closest("[data-toggle-meal-form]");
  const mealFormCancelButton = event.target.closest("[data-cancel-meal-form]");
  const cardToggleButton = event.target.closest("[data-toggle-card]");

  const setList = document.querySelector("[data-set-list]");
  const mealList = document.querySelector("[data-meal-list]");
  const mealForm = document.querySelector("[data-meal-form]");

  if (cardToggleButton) {
    const card = cardToggleButton.closest("[data-collapsible-card]");
    const isCollapsed = card?.classList.toggle("is-collapsed");
    cardToggleButton.setAttribute("aria-expanded", String(!isCollapsed));
    return;
  }

  if (workoutQuickTab) {
    setWorkoutQuickTab(workoutQuickTab.dataset.workoutQuickTab || "recent");
    return;
  }

  if (workoutFormToggleButton && workoutForm) {
    toggleWorkoutForm();
    return;
  }

  if (workoutFormCancelButton && workoutForm) {
    closeWorkoutForm();
    return;
  }

  if (mealFormToggleButton && mealForm) {
    const isCollapsed = mealForm.classList.toggle("is-collapsed");
    mealFormToggleButton.textContent = isCollapsed ? "입력 열기" : "입력 닫기";
    if (!isCollapsed) {
      mealForm.querySelector("input:not([type='hidden']), select")?.focus();
    }
    return;
  }

  if (mealFormCancelButton && mealForm && mealList) {
    resetMealForm(mealForm, mealList);
    const toggleButton = document.querySelector("[data-toggle-meal-form]");
    if (toggleButton) {
      toggleButton.textContent = "입력 열기";
    }
    return;
  }

  if (restButton) {
    startRestTimer(Number(restButton.dataset.restSeconds || 0));
    return;
  }

  if (restStopButton) {
    stopRestTimer();
    return;
  }

  if (workoutClockStartButton) {
    startWorkoutClock();
    return;
  }

  if (workoutClockPauseButton) {
    pauseWorkoutClock();
    return;
  }

  if (workoutClockSaveButton) {
    persistWorkoutClock("저장됨");
    return;
  }

  if (workoutClockResetButton) {
    resetWorkoutClock();
    return;
  }

  if (recentSetButton && setList) {
    loadRecentSets(recentSetButton.dataset.exerciseName || "", setList);
    return;
  }

  if (copySetButton && setList) {
    copySetRow(copySetButton.closest(".set-entry-row"), setList);
    return;
  }

  if (copySavedSetButton && setList) {
    openWorkoutForm();
    copySavedSet(copySavedSetButton, setList);
    return;
  }

  if (applyNextSetButton && setList) {
    openWorkoutForm();
    applyNextSetSuggestion(applyNextSetButton.dataset.applyNextSet || "", setList);
    return;
  }

  if (quickExerciseButton && exerciseNameInput) {
    openWorkoutForm();
    setWorkoutExerciseName(quickExerciseButton.dataset.exerciseName || "");
    const equipmentSelect = workoutForm?.querySelector('select[name="equipment"]');
    if (equipmentSelect && quickExerciseButton.dataset.equipment) {
      equipmentSelect.value = quickExerciseButton.dataset.equipment;
    }
    return;
  }

  if (setCountPresetButton && setList) {
    setBuilderCount(Number(setCountPresetButton.dataset.setCountPreset || 1));
    return;
  }

  if (fillWeightButton && setList) {
    fillSetWeightsFromFirst(setList);
    return;
  }

  if (rampWeightButton && setList) {
    rampSetWeights(setList, Number(rampWeightButton.dataset.rampStep || 5));
    return;
  }

  if (foodQuickButton && mealList) {
    if (mealForm?.classList.contains("is-collapsed")) {
      mealForm.classList.remove("is-collapsed");
      const toggleButton = document.querySelector("[data-toggle-meal-form]");
      if (toggleButton) {
        toggleButton.textContent = "입력 닫기";
      }
    }
    loadFoodEntry(foodQuickButton, mealList);
    return;
  }

  if (removeSetButton && setList) {
    if (setList.querySelectorAll(".set-entry-row").length > 1) {
      removeSetButton.closest(".set-entry-row").remove();
      renumberRows(setList, ".set-entry-row");
      updateSetCountInput();
      updateSetWeightPreviews();
    }
    return;
  }

  if (addSetButton && setList) {
    addRow(setList, "set");
    updateSetCountInput();
    updateSetWeightPreviews();
    return;
  }

  if (removeMealButton && mealList) {
    if (mealList.querySelectorAll(".meal-entry-row").length > 1) {
      removeMealButton.closest(".meal-entry-row").remove();
      renumberRows(mealList, ".meal-entry-row");
    }
    return;
  }

  if (addMealButton && mealList) {
    addRow(mealList, "meal");
    return;
  }

  if (editButton) {
    const item = editButton.closest(".editable-list-item");
    openInlineEdit(item);
    return;
  }

  if (cancelEditButton) {
    const item = cancelEditButton.closest(".editable-list-item");
    item?.classList.remove("is-editing");
    return;
  }

  if (openSetEditButton) {
    const card = openSetEditButton.closest("[data-collapsible-card]");
    card?.classList.remove("is-collapsed");
    card?.querySelector("[data-toggle-card]")?.setAttribute("aria-expanded", "true");
    const item = card?.querySelector(`[data-set-item-id="${openSetEditButton.dataset.setId}"]`);
    openInlineEdit(item);
    return;
  }

  if (inlineAddButton) {
    const panel = inlineAddButton.closest(".inline-add-panel");
    panel?.classList.add("is-adding");
    panel?.querySelector("input:not([type='hidden'])")?.focus();
    return;
  }

  if (inlineAddCancelButton) {
    const panel = inlineAddCancelButton.closest(".inline-add-panel");
    const form = inlineAddCancelButton.closest("form");
    form?.reset();
    panel?.classList.remove("is-adding");
    return;
  }

  if (detailButton) {
    const target = document.getElementById(detailButton.dataset.detailTarget);
    if (!target) return;

    const isOpening = target.classList.contains("is-collapsed");
    if (detailButton.classList.contains("body-part-toggle")) {
      document.querySelectorAll(".body-part-exercise-list").forEach((list) => {
        if (list !== target) {
          list.classList.add("is-collapsed");
          list.setAttribute("aria-hidden", "true");
        }
      });
      document.querySelectorAll(".body-part-toggle").forEach((button) => {
        if (button !== detailButton) {
          button.classList.remove("is-active");
          button.setAttribute("aria-expanded", "false");
        }
      });
    }
    target.classList.toggle("is-collapsed", !isOpening);
    target.setAttribute("aria-hidden", String(!isOpening));
    detailButton.setAttribute("aria-expanded", String(isOpening));
    detailButton.classList.toggle("is-active", isOpening);
  }
});

function applyBodyPartSelectColor(select) {
  const classNames = Object.values(bodyPartClassMap);
  if (classNames.length) {
    select.classList.remove(...classNames);
  }
  select.classList.add(bodyPartClassMap[select.value] || "body-part-other");
}

function openInlineEdit(item) {
  if (!item) {
    return;
  }
  item.classList.add("is-editing");
  item.querySelector("input, select")?.focus();
}

function applyMealTypeSelectColor(select) {
  const classNames = Object.values(mealTypeClassMap);
  if (classNames.length) {
    select.classList.remove(...classNames);
  }
  select.classList.add(mealTypeClassMap[select.value] || "meal-type-other");
}

function parseJsonData(element, key) {
  if (!element) {
    return {};
  }

  try {
    return JSON.parse(element.dataset[key] || "{}");
  } catch {
    return {};
  }
}

function parseExerciseQuickData() {
  return parseJsonData(exerciseQuickPanel, "exercisesByBodyPart");
}

function renderReadinessCoach() {
  if (!readinessForm || !readinessCoach) {
    return;
  }
  const condition = Number(readinessForm.querySelector('[name="condition_score"]')?.value || 3);
  const sleep = Number(readinessForm.querySelector('[name="sleep_score"]')?.value || 3);
  const soreness = Number(readinessForm.querySelector('[name="soreness_score"]')?.value || 3);
  const fatigue = Number(readinessForm.querySelector('[name="fatigue_score"]')?.value || 3);
  const score = condition + sleep + (6 - soreness) + (6 - fatigue);
  const percent = Math.round((score / 20) * 100);
  let label = "회복 우선";
  let guide = "고중량보다 낮은 강도, 보조 운동, 유산소 위주로 조정하세요.";
  let state = "low";
  if (percent >= 75) {
    label = "공격 가능";
    guide = "메인 운동은 지난 기록보다 1회 또는 2.5kg 상향을 시도하세요.";
    state = "high";
  } else if (percent >= 55) {
    label = "표준 진행";
    guide = "지난 기록과 같은 중량에서 세트 완성도를 우선하세요.";
    state = "normal";
  }
  readinessCoach.classList.remove("state-high", "state-normal", "state-low");
  readinessCoach.classList.add(`state-${state}`);
  setReadinessText("[data-readiness-label]", label);
  setReadinessText("[data-readiness-guide]", guide);
  setReadinessText("[data-readiness-percent]", percent);
  setReadinessText("[data-readiness-score]", score);
}

function setReadinessText(selector, value) {
  const element = readinessCoach?.querySelector(selector);
  if (element) {
    element.textContent = String(value);
  }
}

function setWorkoutQuickTab(tabName) {
  workoutQuickTabs.forEach((button) => {
    const isActive = button.dataset.workoutQuickTab === tabName;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
  workoutQuickPanes.forEach((pane) => {
    pane.hidden = pane.dataset.workoutQuickPane !== tabName;
  });
}

function renderExerciseQuickList(bodyPart) {
  if (!exerciseQuickPanel || !exerciseQuickList || !exerciseQuickEmpty) {
    return;
  }

  const names = exercisesByBodyPart[bodyPart] || [];
  const visibleNames = names.slice(0, 8);
  const hiddenCount = Math.max(0, names.length - visibleNames.length);
  exerciseQuickList.innerHTML = visibleNames
    .map((name) => {
      const safeName = escapeHtml(name);
      const setting = exerciseSettings[name] || {};
      const equipment = setting.equipment ? escapeHtml(setting.equipment) : "";
      const label = equipment ? `${safeName} · ${equipment}` : safeName;
      return `<button class="exercise-quick-button" type="button" data-exercise-name="${safeName}" data-equipment="${equipment}">${label}</button>`;
    })
    .join("");
  if (hiddenCount > 0) {
    const libraryUrl = exerciseQuickPanel.dataset.libraryUrl || "/exercises/library";
    exerciseQuickList.insertAdjacentHTML(
      "beforeend",
      `<a class="exercise-quick-button exercise-quick-more" href="${libraryUrl}?part=${encodeURIComponent(bodyPart)}">+${hiddenCount}개</a>`,
    );
  }
  if (exerciseDatalist) {
    exerciseDatalist.innerHTML = names
      .map((name) => `<option value="${escapeHtml(name)}"></option>`)
      .join("");
  }
  exerciseQuickEmpty.hidden = names.length > 0;
  renderRecentSetList(exerciseNameInput?.value || "");
  renderExerciseGuidance(exerciseNameInput?.value || "");
}

function applyWorkoutInputMode(bodyPart) {
  const isCardio = bodyPart === "유산소";
  workoutForm?.classList.toggle("is-cardio", isCardio);
  workoutForm?.classList.toggle("is-strength", !isCardio);

  document.querySelectorAll("[data-workout-form] [data-strength-fields]").forEach((element) => {
    element.hidden = isCardio;
    if (element.matches("input, select")) {
      element.disabled = isCardio;
    }
    element.querySelectorAll("input, select").forEach((input) => {
      input.disabled = isCardio;
    });
  });
  document.querySelectorAll("[data-workout-form] [data-cardio-fields]").forEach((element) => {
    element.hidden = !isCardio;
    if (element.matches("input, select")) {
      element.disabled = !isCardio;
    }
    element.querySelectorAll("input").forEach((input) => {
      input.disabled = !isCardio;
    });
  });
}

function renderRecentSetList(exerciseName) {
  if (!recentSetTitle || !recentSetList) {
    return;
  }
  const sets = recentSetsByExercise[exerciseName] || [];
  recentSetTitle.hidden = sets.length === 0;
  recentSetList.innerHTML = sets.length
    ? `<button class="exercise-quick-button" type="button" data-load-recent-sets data-exercise-name="${escapeHtml(exerciseName)}">지난 세트 불러오기</button>`
    : "";
}

function renderExerciseGuidance(exerciseName) {
  if (exerciseStatView) {
    const stats = exerciseStatsByName[exerciseName];
    if (stats) {
      const bestWeight = stats.best_weight ? `${Number(stats.best_weight).toFixed(1)}kg` : "-kg";
      const bestReps = stats.best_reps ? `${Number(stats.best_reps)}회` : "-회";
      const bestVolume = stats.best_volume ? `${Number(stats.best_volume).toFixed(0)}kg` : "-kg";
      exerciseStatView.textContent = `최근: ${stats.recent || "-"} · 최고: ${bestWeight} / ${bestReps} / 볼륨 ${bestVolume}`;
      exerciseStatView.hidden = false;
    } else {
      exerciseStatView.textContent = "";
      exerciseStatView.hidden = true;
    }
  }
  if (overloadSuggestionView) {
    const suggestion = overloadSuggestions[exerciseName] || "";
    overloadSuggestionView.textContent = suggestion;
    overloadSuggestionView.hidden = !suggestion;
  }
  if (nextSetAdviceView) {
    const advice = nextSetSuggestions[exerciseName];
    if (advice) {
      const weight = advice.weight ? `${Number(advice.weight).toFixed(1)}kg` : "";
      const reps = advice.reps ? `${Number(advice.reps)}회` : "";
      const minutes = advice.cardio_minutes ? `${Number(advice.cardio_minutes)}분` : "";
      const target = [weight, reps, minutes, advice.sets ? `${advice.sets}세트` : ""].filter(Boolean).join(" · ");
      nextSetAdviceView.innerHTML = `
        <div class="next-set-advice-row">
          <span>다음 세트 · ${escapeHtml(advice.type || "추천")}</span>
          <strong>${escapeHtml(target || "기준 기록")}</strong>
          <button type="button" class="btn-small" data-apply-next-set="${escapeHtml(exerciseName)}">적용</button>
        </div>
        <small>${escapeHtml(advice.reason || "")}</small>
      `;
      nextSetAdviceView.hidden = false;
    } else {
      nextSetAdviceView.innerHTML = "";
      nextSetAdviceView.hidden = true;
    }
  }
  if (exerciseNoteView) {
    const note = exerciseNotes[exerciseName] || "";
    exerciseNoteView.textContent = note ? `메모: ${note}` : "";
    exerciseNoteView.hidden = !note;
  }
  if (exerciseTargetView) {
    const setting = exerciseSettings[exerciseName] || {};
    const parts = [];
    if (setting.equipment) {
      parts.push(`장비 ${setting.equipment}`);
    }
    if (setting.target_weight) {
      parts.push(`${Number(setting.target_weight).toFixed(1)}kg`);
    }
    if (setting.target_reps) {
      parts.push(`${Number(setting.target_reps)}회`);
    }
    if (setting.target_sets) {
      parts.push(`${Number(setting.target_sets)}세트`);
    }
    exerciseTargetView.textContent = parts.length ? `목표: ${parts.join(" · ")}` : "";
    exerciseTargetView.hidden = parts.length === 0;
  }
}

function setWorkoutExerciseName(exerciseName) {
  if (!exerciseNameInput) {
    return;
  }
  exerciseNameInput.value = exerciseName;
  renderRecentSetList(exerciseNameInput.value);
  renderExerciseGuidance(exerciseNameInput.value);
  exerciseNameInput.focus();
}

function getWorkoutFormToggleButtons() {
  return Array.from(document.querySelectorAll("[data-toggle-workout-form]"));
}

function setWorkoutFormToggleText(isCollapsed) {
  getWorkoutFormToggleButtons().forEach((button) => {
    button.textContent = isCollapsed ? "운동 추가" : "입력 닫기";
    button.setAttribute("aria-expanded", String(!isCollapsed));
  });
}

function openWorkoutForm() {
  if (!workoutForm) {
    return;
  }
  workoutForm.classList.remove("is-collapsed");
  setWorkoutFormToggleText(false);
}

function closeWorkoutForm() {
  if (!workoutForm) {
    return;
  }
  workoutForm.classList.add("is-collapsed");
  setWorkoutFormToggleText(true);
}

function toggleWorkoutForm() {
  if (!workoutForm) {
    return;
  }
  const isCollapsed = workoutForm.classList.toggle("is-collapsed");
  setWorkoutFormToggleText(isCollapsed);
  if (!isCollapsed) {
    workoutForm.querySelector("input:not([type='hidden']), select")?.focus();
  }
}

function applyNextSetSuggestion(exerciseName, setList) {
  const advice = nextSetSuggestions[exerciseName];
  if (!advice || !setList) {
    return;
  }
  if (advice.sets) {
    setBuilderCount(Number(advice.sets));
  }
  const rows = getSetRows(setList);
  rows.forEach((row) => {
    if (advice.weight) {
      setInputValue(row, 'input[name="set_weight"]', Number(advice.weight).toFixed(1));
      const unit = row.querySelector('select[name="set_weight_unit"]');
      if (unit) {
        unit.value = "kg";
      }
    }
    if (advice.reps) {
      setInputValue(row, 'input[name="set_reps"]', String(advice.reps));
    }
    if (advice.cardio_minutes) {
      setInputValue(row, 'input[name="cardio_minutes"]', String(advice.cardio_minutes));
    }
  });
  updateSetWeightPreviews();
}

function renderFoodQuickList(mealType) {
  if (!foodQuickList || !foodQuickEmpty) {
    return;
  }
  const foods = foodsByMealType[mealType] || [];
  foodQuickList.innerHTML = foods
    .map((food) => {
      const name = escapeHtml(food.food_name || "");
      return `<button class="exercise-quick-button" type="button" data-food-entry data-food-name="${name}" data-food-quantity="${food.quantity ?? ""}" data-food-grams="${food.grams ?? ""}" data-food-calories="${food.calories ?? ""}">${name}</button>`;
    })
    .join("");
  foodQuickEmpty.hidden = foods.length > 0;
}

function initSetBuilder() {
  const setList = document.querySelector("[data-set-list]");
  if (!setList) {
    return;
  }
  syncSetRowsToCount();
  updateSetWeightPreviews();
}

function getSetRows(setList = document.querySelector("[data-set-list]")) {
  return setList ? Array.from(setList.querySelectorAll(".set-entry-row")) : [];
}

function setBuilderCount(count) {
  const input = document.querySelector("[data-set-count-input]");
  if (input) {
    input.value = String(Math.min(20, Math.max(1, count || 1)));
  }
  syncSetRowsToCount();
}

function syncSetRowsToCount() {
  const setList = document.querySelector("[data-set-list]");
  const input = document.querySelector("[data-set-count-input]");
  if (!setList || !input) {
    return;
  }
  const targetCount = Math.min(20, Math.max(1, Number(input.value || 1)));
  while (getSetRows(setList).length < targetCount) {
    addRow(setList, "set", { focus: false });
  }
  while (getSetRows(setList).length > targetCount) {
    getSetRows(setList).at(-1)?.remove();
  }
  renumberRows(setList, ".set-entry-row");
  applyWorkoutInputMode(workoutForm?.querySelector("[data-body-part-select]")?.value || "");
  updateSetWeightPreviews();
}

function updateSetCountInput() {
  const input = document.querySelector("[data-set-count-input]");
  if (input) {
    input.value = String(getSetRows().length || 1);
  }
}

function updateSetWeightPreviews() {
  getSetRows().forEach((row) => {
    const input = row.querySelector('input[name="set_weight"]');
    const unit = row.querySelector('select[name="set_weight_unit"]')?.value || "kg";
    const preview = row.querySelector("[data-weight-preview]");
    if (!input || !preview) {
      return;
    }
    const value = Number(input.value || 0);
    if (!input.value || Number.isNaN(value)) {
      preview.textContent = unit === "lb" ? "lb 입력 시 kg로 저장" : "kg 기준 저장";
      return;
    }
    const kgValue = unit === "lb" ? value * 0.45359237 : value;
    preview.textContent = `${formatToolWeight(kgValue)}kg 저장`;
  });
}

function fillSetWeightsFromFirst(setList) {
  const rows = getSetRows(setList);
  const firstWeight = rows[0]?.querySelector('input[name="set_weight"]')?.value || "";
  const firstUnit = rows[0]?.querySelector('select[name="set_weight_unit"]')?.value || "kg";
  if (!firstWeight) {
    return;
  }
  rows.slice(1).forEach((row) => {
    setInputValue(row, 'input[name="set_weight"]', firstWeight);
    setInputValue(row, 'select[name="set_weight_unit"]', firstUnit);
  });
  updateSetWeightPreviews();
}

function rampSetWeights(setList, step) {
  const rows = getSetRows(setList);
  const first = Number(rows[0]?.querySelector('input[name="set_weight"]')?.value || 0);
  if (!first || Number.isNaN(first)) {
    return;
  }
  rows.forEach((row, index) => {
    setInputValue(row, 'input[name="set_weight"]', formatToolWeight(first + step * index));
  });
  updateSetWeightPreviews();
}

function loadRecentSets(exerciseName, setList) {
  const sets = recentSetsByExercise[exerciseName] || [];
  if (!sets.length) {
    return;
  }
  setList.innerHTML = "";
  sets.forEach((set) => {
    const row = document.createElement("div");
    row.className = "set-entry-row";
    row.innerHTML = setRowHtml(0);
    row.querySelector('input[name="set_weight"]').value = set.weight ?? "";
    row.querySelector('input[name="set_reps"]').value = set.reps ?? "";
    setList.append(row);
  });
  updateSetCountInput();
  updateSetWeightPreviews();
  applyWorkoutInputMode(workoutForm?.querySelector("[data-body-part-select]")?.value || "");
}

function copySetRow(sourceRow, setList) {
  if (!sourceRow || !setList) {
    return;
  }
  const row = addRow(setList, "set");
  copyFieldValue(sourceRow, row, 'input[name="set_weight"]');
  copyFieldValue(sourceRow, row, 'select[name="set_weight_unit"]');
  copyFieldValue(sourceRow, row, 'input[name="set_reps"]');
  copyFieldValue(sourceRow, row, 'select[name="set_type"]');
  copyFieldValue(sourceRow, row, 'input[name="cardio_incline"]');
  copyFieldValue(sourceRow, row, 'input[name="cardio_speed"]');
  copyFieldValue(sourceRow, row, 'input[name="cardio_minutes"]');
  copyFieldValue(sourceRow, row, 'input[name="set_rpe"]');
  copyFieldValue(sourceRow, row, 'input[name="set_memo"]');
  applyWorkoutInputMode(workoutForm?.querySelector("[data-body-part-select]")?.value || "");
  updateSetWeightPreviews();
}

function copySavedSet(button, setList) {
  const bodyPartSelect = workoutForm?.querySelector("[data-body-part-select]");
  const bodyPart = button.dataset.bodyPart || "기타";
  if (bodyPartSelect) {
    bodyPartSelect.value = bodyPart;
    applyBodyPartSelectColor(bodyPartSelect);
    renderExerciseQuickList(bodyPart);
    applyWorkoutInputMode(bodyPart);
  }
  if (exerciseNameInput) {
    setWorkoutExerciseName(button.dataset.exerciseName || "");
  }
  const equipmentSelect = workoutForm?.querySelector('select[name="equipment"]');
  if (equipmentSelect && button.dataset.equipment) {
    equipmentSelect.value = button.dataset.equipment;
  }
  const firstRow = setList.querySelector(".set-entry-row");
  const hasValue = firstRow && [...firstRow.querySelectorAll("input")].some((input) => input.value);
  const row = firstRow && !hasValue ? firstRow : addRow(setList, "set");
  setInputValue(row, 'input[name="set_weight"]', button.dataset.weight);
  setInputValue(row, 'select[name="set_weight_unit"]', "kg");
  setInputValue(row, 'input[name="set_reps"]', button.dataset.reps);
  setInputValue(row, 'select[name="set_type"]', button.dataset.setType || setTypeOptions[0]);
  setInputValue(row, 'input[name="cardio_incline"]', button.dataset.cardioIncline);
  setInputValue(row, 'input[name="cardio_speed"]', button.dataset.cardioSpeed);
  setInputValue(row, 'input[name="cardio_minutes"]', button.dataset.cardioMinutes);
  row.scrollIntoView({ behavior: "smooth", block: "center" });
  updateSetCountInput();
  updateSetWeightPreviews();
}

function copyFieldValue(sourceRow, targetRow, selector) {
  const source = sourceRow.querySelector(selector);
  setInputValue(targetRow, selector, source?.value || "");
}

function setInputValue(row, selector, value) {
  const input = row.querySelector(selector);
  if (input) {
    input.value = value || "";
  }
}

function loadFoodEntry(button, mealList) {
  const firstRow = mealList.querySelector(".meal-entry-row");
  const row = firstRow && !firstRow.querySelector('input[name="meal_food_name"]').value ? firstRow : addRow(mealList, "meal");
  row.querySelector('input[name="meal_food_name"]').value = button.dataset.foodName || "";
  row.querySelector('input[name="meal_quantity"]').value = button.dataset.foodQuantity || "";
  row.querySelector('input[name="meal_grams"]').value = button.dataset.foodGrams || "";
  row.querySelector('input[name="meal_calories"]').value = button.dataset.foodCalories || "";
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[char];
  });
}

function scrollRestoreKey() {
  const params = new URLSearchParams(window.location.search);
  const selectedDate =
    document.querySelector('.date-picker-form input[name="date"]')?.value ||
    document.querySelector("[data-workout-clock]")?.dataset.workoutDate ||
    params.get("date") ||
    "";
  return `scroll-restore:${window.location.pathname}:${selectedDate}`;
}

function saveScrollPosition() {
  try {
    sessionStorage.setItem(scrollRestoreKey(), String(window.scrollY));
  } catch {
    // Scroll restoration is a convenience feature; form submission should continue.
  }
}

function restoreSavedScrollPosition() {
  let savedScroll = null;
  try {
    const key = scrollRestoreKey();
    savedScroll = sessionStorage.getItem(key);
    if (savedScroll !== null) {
      sessionStorage.removeItem(key);
    }
  } catch {
    return;
  }
  if (savedScroll === null) {
    return;
  }
  requestAnimationFrame(() => {
    window.scrollTo({ top: Math.max(0, Number(savedScroll) || 0), behavior: "auto" });
  });
}

function scrollActiveTabIntoView() {
  const activeTab = document.querySelector(".tabs .tab-btn.active");
  if (!activeTab) {
    return;
  }
  requestAnimationFrame(() => {
    activeTab.scrollIntoView({ behavior: "auto", block: "nearest", inline: "center" });
  });
}

function addRow(list, type, options = {}) {
  const selector = type === "set" ? ".set-entry-row" : ".meal-entry-row";
  const index = list.querySelectorAll(selector).length + 1;
  const row = document.createElement("div");
  row.className = type === "set" ? "set-entry-row" : "meal-entry-row";
  row.innerHTML = type === "set" ? setRowHtml(index) : mealRowHtml(index);
  list.append(row);
  if (options.focus !== false) {
    row.querySelector("input").focus();
  }
  return row;
}

function resetMealForm(form, mealList) {
  form.reset();
  mealList.querySelectorAll(".meal-entry-row").forEach((row, index) => {
    if (index === 0) {
      row.querySelectorAll("input").forEach((input) => {
        input.value = "";
      });
    } else {
      row.remove();
    }
  });
  form.classList.add("is-collapsed");
}

function setRowHtml(index) {
  const setTypeOptionHtml = setTypeOptions
    .map((option) => `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`)
    .join("");
  const weightPlaceholder = appPreferences.default_weight_placeholder ?? 60;
  const repsPlaceholder = appPreferences.default_reps_placeholder ?? 10;
  return `
    <strong class="set-row-number">${index}세트</strong>
    <div class="compact-field-grid" data-strength-fields>
      <label class="weight-unit-field">
        <span>무게</span>
        <div class="weight-unit-control">
          <input name="set_weight" type="number" min="0" step="0.5" inputmode="decimal" placeholder="${escapeHtml(weightPlaceholder)}">
          <select name="set_weight_unit" aria-label="무게 단위">
            <option value="kg">kg</option>
            <option value="lb">lb</option>
          </select>
        </div>
        <small class="weight-preview" data-weight-preview>kg 기준 저장</small>
      </label>
      <label>
        <span>횟수</span>
        <input name="set_reps" type="number" min="0" step="1" inputmode="numeric" placeholder="${escapeHtml(repsPlaceholder)}">
      </label>
    </div>
    <select name="set_type" aria-label="세트 타입" data-strength-fields>
      ${setTypeOptionHtml}
    </select>
    <div class="compact-field-grid cardio-field-grid" data-cardio-fields hidden>
      <label>
        <span>인클라인</span>
        <input name="cardio_incline" type="number" min="0" step="0.1" inputmode="decimal" placeholder="8">
      </label>
      <label>
        <span>속도</span>
        <input name="cardio_speed" type="number" min="0" step="0.1" inputmode="decimal" placeholder="5.5">
      </label>
      <label>
        <span>시간 분</span>
        <input name="cardio_minutes" type="number" min="0" step="1" inputmode="numeric" placeholder="30">
      </label>
    </div>
    <input name="set_rpe" type="number" min="1" max="10" step="0.5" inputmode="decimal" placeholder="체감강도">
    <input name="set_memo" autocomplete="off" placeholder="메모">
    <div class="set-row-actions">
      <button class="btn-ghost row-copy-button" type="button" data-copy-set-row aria-label="세트 복사">복사</button>
      <button class="btn-danger row-remove-button" type="button" data-remove-set-row aria-label="세트 삭제">X</button>
    </div>
  `;
}

function mealRowHtml(index) {
  return `
    <input name="meal_food_name" autocomplete="off" placeholder="음식" required>
    <div class="compact-field-grid meal-compact-grid">
      <input name="meal_quantity" type="number" min="0" step="1" inputmode="numeric" placeholder="개">
      <input name="meal_grams" type="number" min="0" step="0.1" inputmode="decimal" placeholder="g">
      <input name="meal_calories" type="number" min="0" step="1" inputmode="numeric" placeholder="kcal">
    </div>
    <button class="btn-danger row-remove-button" type="button" data-remove-meal-row aria-label="음식 삭제">×</button>
  `;
}

function renumberRows(list, selector) {
  list.querySelectorAll(selector).forEach((row, index) => {
    const number = row.querySelector("strong");
    if (number) {
      number.textContent = row.classList.contains("set-entry-row") ? `${index + 1}세트` : index + 1;
    }
  });
}

function initWorkoutTools() {
  if (!document.querySelector("[data-plate-tool]") && !document.querySelector("[data-warmup-tool]")) {
    return;
  }
  renderWorkoutTools();
}

function renderWorkoutTools() {
  renderPlateCalculator();
  renderWarmupCalculator();
}

function renderPlateCalculator() {
  const tool = document.querySelector("[data-plate-tool]");
  if (!tool) {
    return;
  }
  const target = Number(tool.querySelector("[data-plate-target]")?.value || 0);
  const bar = Number(tool.querySelector("[data-plate-bar]")?.value || 20);
  const result = tool.querySelector("[data-plate-result]");
  if (!result) {
    return;
  }
  const perSide = (target - bar) / 2;
  if (target <= 0 || perSide < 0) {
    result.textContent = "목표 중량을 입력하세요.";
    return;
  }
  const plates = calculatePlates(perSide);
  if (!plates.length) {
    result.innerHTML = `<span>원판 없음</span>`;
    return;
  }
  const totalText = plates.map((item) => item.label || `${item.weight}kg x ${item.count * 2}`).join(" · ");
  const sideText = plates.map((item) => item.label || `${item.weight}kg x ${item.count}`).join(" · ");
  result.innerHTML = `<span>전체 ${totalText}</span><span>한쪽 ${sideText}</span>`;
}

function renderWarmupCalculator() {
  const tool = document.querySelector("[data-warmup-tool]");
  if (!tool) {
    return;
  }
  const target = Number(tool.querySelector("[data-warmup-target]")?.value || 0);
  const step = Number(tool.querySelector("[data-warmup-step]")?.value || 2.5);
  const result = tool.querySelector("[data-warmup-result]");
  if (!result) {
    return;
  }
  if (target <= 0 || step <= 0) {
    result.innerHTML = `<span>본세트 중량을 입력하세요.</span>`;
    return;
  }
  const warmups = [
    { ratio: 0.4, reps: 8 },
    { ratio: 0.6, reps: 5 },
    { ratio: 0.8, reps: 3 },
  ];
  result.innerHTML = warmups
    .map((item) => {
      const weight = Math.max(step, Math.round((target * item.ratio) / step) * step);
      return `<span>${Math.round(item.ratio * 100)}% · ${formatToolWeight(weight)}kg x ${item.reps}</span>`;
    })
    .join("");
}

function calculatePlates(perSide) {
  const available = [20, 10, 5, 2.5];
  let remaining = Math.max(0, perSide);
  const result = [];
  available.forEach((weight) => {
    const count = Math.floor((remaining + 0.001) / weight);
    if (count > 0) {
      result.push({ weight: formatToolWeight(weight), count });
      remaining -= count * weight;
    }
  });
  if (remaining > 0.1) {
    result.push({ label: `${formatToolWeight(remaining)}kg 부족` });
  }
  return result;
}

function formatToolWeight(value) {
  const numberValue = Number(value);
  if (Number.isInteger(numberValue)) {
    return String(numberValue);
  }
  return numberValue.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

const offlineQueueKey = "health-tracker-offline-queue-v1";

function queueOfflineForm(form, event) {
  if (!form || form.method?.toLowerCase() !== "post" || navigator.onLine) {
    return false;
  }
  const actionUrl = new URL(form.getAttribute("action") || window.location.href, window.location.origin);
  const queueablePaths = ["/sets", "/meals", "/body-metrics", "/recovery-checkins", "/rest-days", "/plans"];
  if (!queueablePaths.includes(actionUrl.pathname) || form.enctype === "multipart/form-data") {
    return false;
  }
  const formData = new FormData(form);
  const entries = Array.from(formData.entries()).map(([key, value]) => [key, String(value)]);
  const queue = readOfflineQueue();
  queue.push({
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    action: actionUrl.pathname + actionUrl.search,
    entries,
    createdAt: new Date().toISOString(),
  });
  writeOfflineQueue(queue);
  event.preventDefault();
  showOfflineQueueStatus(`오프라인 저장 ${queue.length}건`);
  return true;
}

function readOfflineQueue() {
  try {
    return JSON.parse(localStorage.getItem(offlineQueueKey) || "[]");
  } catch {
    return [];
  }
}

function writeOfflineQueue(queue) {
  localStorage.setItem(offlineQueueKey, JSON.stringify(queue));
}

async function processOfflineQueue() {
  if (!navigator.onLine) {
    return;
  }
  const queue = readOfflineQueue();
  if (!queue.length) {
    return;
  }
  const remaining = [];
  for (const item of queue) {
    try {
      const body = new URLSearchParams();
      item.entries.forEach(([key, value]) => body.append(key, value));
      const response = await fetch(item.action, {
        method: "POST",
        body,
        headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
        redirect: "manual",
      });
      if (!(response.ok || response.type === "opaqueredirect" || response.status === 0 || response.status === 302)) {
        remaining.push(item);
      }
    } catch {
      remaining.push(item);
    }
  }
  writeOfflineQueue(remaining);
  if (remaining.length !== queue.length) {
    showOfflineQueueStatus(remaining.length ? `동기화 후 ${remaining.length}건 대기` : "오프라인 입력 동기화 완료");
  }
}

function showOfflineQueueStatus(message) {
  let panel = document.querySelector("[data-offline-queue-status]");
  if (!panel) {
    panel = document.createElement("div");
    panel.dataset.offlineQueueStatus = "1";
    panel.className = "offline-queue-status";
    document.body.append(panel);
  }
  panel.textContent = message;
  panel.classList.add("is-visible");
  window.setTimeout(() => panel.classList.remove("is-visible"), 3500);
}

function initNotificationTools() {
  document.querySelector("[data-enable-notifications]")?.addEventListener("click", async () => {
    if (!("Notification" in window)) {
      showOfflineQueueStatus("이 브라우저는 알림을 지원하지 않습니다.");
      return;
    }
    const permission = await Notification.requestPermission();
    showOfflineQueueStatus(permission === "granted" ? "알림이 허용되었습니다." : "알림이 허용되지 않았습니다.");
  });

  const settingsPanel = document.querySelector("[data-reminder-settings]");
  if (!settingsPanel || !("Notification" in window) || Notification.permission !== "granted") {
    return;
  }
  const settings = parseJsonData(settingsPanel, "reminderSettings");
  const now = new Date();
  const todayKey = now.toISOString().slice(0, 10);
  Object.entries(settings).forEach(([key, item]) => {
    if (!item.enabled || !item.time_text) {
      return;
    }
    const [hour, minute] = item.time_text.split(":").map(Number);
    if (Number.isNaN(hour) || Number.isNaN(minute)) {
      return;
    }
    const due = new Date(now);
    due.setHours(hour, minute, 0, 0);
    const firedKey = `health-tracker-reminder-${key}-${todayKey}`;
    if (now >= due && localStorage.getItem(firedKey) !== "1") {
      new Notification(item.message || "기록을 확인하세요.");
      localStorage.setItem(firedKey, "1");
    }
  });
}

window.addEventListener("visibilitychange", () => {
  if (!document.querySelector("[data-workout-clock]")) {
    return;
  }
  if (document.visibilityState === "hidden") {
    sendWorkoutClockBeacon();
    return;
  }
  updateWorkoutClockDisplay();
  const currentState = readWorkoutClock();
  if (currentState.startedAt && currentState.manualStarted) {
    updateWorkoutClockStatus("측정 중");
  }
});
