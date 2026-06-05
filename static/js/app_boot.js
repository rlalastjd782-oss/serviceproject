const exerciseQuickPanel = document.querySelector("[data-exercise-quick-panel]");
const appPreferenceElement = document.querySelector("[data-app-preferences]");
const appPreferences = parseJsonData(appPreferenceElement, "appPreferences");
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
initWorkoutClock();
restoreSavedScrollPosition();
scrollActiveTabIntoView();
initWorkoutTools();
initSetBuilder();
renderReadinessCoach();
processOfflineQueue();
initNotificationTools();

function setMealFormToggleLabels(label) {
  document.querySelectorAll("[data-toggle-meal-form]").forEach((button) => {
    const isClosing = label.includes("닫기");
    button.textContent = isClosing
      ? button.dataset.mealToggleCloseLabel || label
      : button.dataset.mealToggleOpenLabel || label;
  });
}

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
  syncMealTypeSegments(select.value);
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
    syncMealTypeSegments(mealTypeSelect.value);
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
  const mealCountInput = event.target.closest("[data-meal-count-input]");
  if (mealCountInput) {
    const mealList = document.querySelector("[data-meal-list]");
    if (mealList) {
      syncMealRowsToCount(mealList, mealCountInput.value);
    }
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

window.addEventListener("online", () => {
  processOfflineQueue();
});

document.addEventListener("click", (event) => {
  const addSetButton = event.target.closest("[data-add-set-row]");
  const removeSetButton = event.target.closest("[data-remove-set-row]");
  const addMealButton = event.target.closest("[data-add-meal-row]");
  const addMealPresetButton = event.target.closest("[data-add-meal-preset]");
  const removeMealButton = event.target.closest("[data-remove-meal-row]");
  const editButton = event.target.closest("[data-toggle-edit]");
  const openSetEditButton = event.target.closest("[data-open-set-edit]");
  const cancelEditButton = event.target.closest("[data-cancel-edit]");
  const inlineAddButton = event.target.closest("[data-toggle-add]");
  const inlineAddCancelButton = event.target.closest("[data-cancel-inline-add]");
  const detailButton = event.target.closest("[data-toggle-detail]");
  const workoutQuickTab = event.target.closest("[data-workout-quick-tab]");
  const mealQuickTab = event.target.closest("[data-meal-quick-tab]");
  const mealToolTab = event.target.closest("[data-meal-tool-tab]");
  const mealToolMoreButton = event.target.closest("[data-meal-tool-more]");
  const quickExerciseButton = event.target.closest("[data-exercise-name]");
  const applyNextSetButton = event.target.closest("[data-apply-next-set]");
  const recentSetButton = event.target.closest("[data-load-recent-sets]");
  const copySetButton = event.target.closest("[data-copy-set-row]");
  const copySavedSetButton = event.target.closest("[data-copy-saved-set]");
  const setCountPresetButton = event.target.closest("[data-set-count-preset]");
  const fillWeightButton = event.target.closest("[data-fill-weight]");
  const cloneFirstSetButton = event.target.closest("[data-clone-first-set]");
  const cloneFirstMealButton = event.target.closest("[data-clone-first-meal]");
  const rampWeightButton = event.target.closest("[data-ramp-weight]");
  const foodQuickButton = event.target.closest("[data-food-entry]");
  const mealTypeSegment = event.target.closest("[data-meal-type-option]");
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

  if (mealQuickTab) {
    setMealQuickTab(mealQuickTab.dataset.mealQuickTab || "recent");
    return;
  }

  if (mealToolTab) {
    setMealToolTab(mealToolTab.dataset.mealToolTab || "combo");
    return;
  }

  if (mealToolMoreButton) {
    expandMealToolRows(mealToolMoreButton.dataset.mealToolMore || "");
    return;
  }

  if (mealTypeSegment) {
    setMealTypeFromSegment(mealTypeSegment);
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
    setMealFormToggleLabels(isCollapsed ? "입력 열기" : "입력 닫기");
    if (!isCollapsed) {
      mealForm.querySelector("input:not([type='hidden'])")?.focus();
    }
    return;
  }

  if (mealFormCancelButton && mealForm && mealList) {
    resetMealForm(mealForm, mealList);
    setMealFormToggleLabels("입력 열기");
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

  if (cloneFirstSetButton && setList) {
    cloneFirstSetToCount(setList);
    return;
  }

  if (cloneFirstMealButton && mealList) {
    cloneFirstMealToRows(mealList);
    return;
  }

  if (rampWeightButton && setList) {
    rampSetWeights(setList, Number(rampWeightButton.dataset.rampStep || 5));
    return;
  }

  if (foodQuickButton && mealList) {
    if (mealForm?.classList.contains("is-collapsed")) {
      mealForm.classList.remove("is-collapsed");
      setMealFormToggleLabels("입력 닫기");
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
      updateMealCountInput(mealList);
    } else {
      removeMealButton.closest(".meal-entry-row")?.querySelectorAll("input").forEach((input) => {
        input.value = "";
      });
    }
    return;
  }

  if (addMealButton && mealList) {
    addRow(mealList, "meal");
    updateMealCountInput(mealList);
    return;
  }

  if (addMealPresetButton && mealList) {
    syncMealRowsToCount(mealList, addMealPresetButton.dataset.addMealPreset);
    mealList.querySelector(".meal-entry-row:last-child input")?.focus();
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
