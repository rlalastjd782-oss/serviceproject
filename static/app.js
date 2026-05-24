if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  });
}

const bodyPartClassMap = {
  "하체": "body-part-legs",
  "가슴": "body-part-chest",
  "팔": "body-part-arms",
  "등": "body-part-back",
  "어깨": "body-part-shoulders",
  "유산소": "body-part-cardio",
  "기타": "body-part-other",
};

const mealTypeClassMap = {
  "아침": "meal-type-breakfast",
  "점심": "meal-type-lunch",
  "저녁": "meal-type-dinner",
  "간식": "meal-type-snack",
  "기타": "meal-type-other",
};

const exerciseQuickPanel = document.querySelector("[data-exercise-quick-panel]");
const exerciseQuickList = document.querySelector("[data-exercise-quick-list]");
const exerciseQuickEmpty = document.querySelector("[data-exercise-quick-empty]");
const recentSetTitle = document.querySelector("[data-recent-set-title]");
const recentSetList = document.querySelector("[data-recent-set-list]");
const exerciseDatalist = document.querySelector("[data-exercise-datalist]");
const workoutForm = document.querySelector("[data-workout-form]");
const exerciseNameInput = workoutForm?.querySelector("[data-workout-exercise-input]");
const exercisesByBodyPart = parseExerciseQuickData();
const recentSetsByExercise = parseJsonData(exerciseQuickPanel, "recentSetsByExercise");
const exerciseStatsByName = parseJsonData(exerciseQuickPanel, "exerciseStatsByName");
const overloadSuggestions = parseJsonData(exerciseQuickPanel, "overloadSuggestions");
const exerciseNotes = parseJsonData(exerciseQuickPanel, "exerciseNotes");
const overloadSuggestionView = document.querySelector("[data-overload-suggestion]");
const exerciseStatView = document.querySelector("[data-exercise-stat-view]");
const exerciseNoteView = document.querySelector("[data-exercise-note-view]");
const foodQuickPanel = document.querySelector("[data-food-quick-panel]");
const foodQuickList = document.querySelector("[data-food-quick-list]");
const foodQuickEmpty = document.querySelector("[data-food-quick-empty]");
const foodsByMealType = parseJsonData(foodQuickPanel, "foodsByMealType");
const workoutClockPanel = document.querySelector("[data-workout-clock]");
let restTimerId = null;
let restRemaining = 0;
let workoutClockId = null;
let workoutClockSyncId = null;

initWorkoutClock();
restoreSavedScrollPosition();
initWorkoutTools();
startRestTimerFromUrl();

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
  if (event.target.closest("[data-plate-tool]") || event.target.closest("[data-warmup-tool]")) {
    renderWorkoutTools();
  }
});

document.addEventListener("submit", (event) => {
  const form = event.target.closest("form");
  const confirmMessage = form?.dataset.confirmSubmit;
  if (confirmMessage && !window.confirm(confirmMessage)) {
    event.preventDefault();
    return;
  }
  if (form?.method?.toLowerCase() === "post" && !form.dataset.noScrollRestore) {
    saveScrollPosition();
  }

  const durationForm = event.target.closest(".duration-edit-form");
  if (!durationForm || !workoutClockPanel) {
    return;
  }
  const action = event.submitter?.getAttribute("value");
  const hours = Number(durationForm.querySelector('input[name="duration_hours"]')?.value || 0);
  const minutes = Number(durationForm.querySelector('input[name="duration_minutes"]')?.value || 0);
  const durationSeconds = action === "reset" ? 0 : Math.max(0, hours * 3600 + minutes * 60);
  saveWorkoutClock({ startedAt: null, elapsedMs: durationSeconds * 1000, manualStarted: false });
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
  const quickExerciseButton = event.target.closest("[data-exercise-name]");
  const recentSetButton = event.target.closest("[data-load-recent-sets]");
  const copySetButton = event.target.closest("[data-copy-set-row]");
  const copySavedSetButton = event.target.closest("[data-copy-saved-set]");
  const foodQuickButton = event.target.closest("[data-food-entry]");
  const restButton = event.target.closest("[data-rest-seconds]");
  const restStopButton = event.target.closest("[data-rest-stop]");
  const workoutClockStartButton = event.target.closest("[data-workout-clock-start]");
  const workoutClockPauseButton = event.target.closest("[data-workout-clock-pause]");
  const workoutClockSaveButton = event.target.closest("[data-workout-clock-save]");
  const workoutClockResetButton = event.target.closest("[data-workout-clock-reset]");
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

  if (quickExerciseButton && exerciseNameInput) {
    setWorkoutExerciseName(quickExerciseButton.dataset.exerciseName || "");
    return;
  }

  if (copySetButton && setList) {
    copySetRow(copySetButton.closest(".set-entry-row"), setList);
    return;
  }

  if (copySavedSetButton && setList) {
    copySavedSet(copySavedSetButton, setList);
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
    }
    return;
  }

  if (addSetButton && setList) {
    addRow(setList, "set");
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
  select.classList.remove(...Object.values(bodyPartClassMap));
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
  select.classList.remove(...Object.values(mealTypeClassMap));
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

function renderExerciseQuickList(bodyPart) {
  if (!exerciseQuickPanel || !exerciseQuickList || !exerciseQuickEmpty) {
    return;
  }

  const names = exercisesByBodyPart[bodyPart] || [];
  exerciseQuickList.innerHTML = names
    .map((name) => {
      const safeName = escapeHtml(name);
      return `<button class="exercise-quick-button" type="button" data-exercise-name="${safeName}">${safeName}</button>`;
    })
    .join("");
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
  if (exerciseNoteView) {
    const note = exerciseNotes[exerciseName] || "";
    exerciseNoteView.textContent = note ? `메모: ${note}` : "";
    exerciseNoteView.hidden = !note;
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
  applyWorkoutInputMode(workoutForm?.querySelector("[data-body-part-select]")?.value || "");
}

function copySetRow(sourceRow, setList) {
  if (!sourceRow || !setList) {
    return;
  }
  const row = addRow(setList, "set");
  copyFieldValue(sourceRow, row, 'input[name="set_weight"]');
  copyFieldValue(sourceRow, row, 'input[name="set_reps"]');
  copyFieldValue(sourceRow, row, 'select[name="set_type"]');
  copyFieldValue(sourceRow, row, 'input[name="cardio_incline"]');
  copyFieldValue(sourceRow, row, 'input[name="cardio_speed"]');
  copyFieldValue(sourceRow, row, 'input[name="cardio_minutes"]');
  copyFieldValue(sourceRow, row, 'input[name="set_rpe"]');
  copyFieldValue(sourceRow, row, 'input[name="set_memo"]');
  applyWorkoutInputMode(workoutForm?.querySelector("[data-body-part-select]")?.value || "");
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
  const firstRow = setList.querySelector(".set-entry-row");
  const hasValue = firstRow && [...firstRow.querySelectorAll("input")].some((input) => input.value);
  const row = firstRow && !hasValue ? firstRow : addRow(setList, "set");
  setInputValue(row, 'input[name="set_weight"]', button.dataset.weight);
  setInputValue(row, 'input[name="set_reps"]', button.dataset.reps);
  setInputValue(row, 'select[name="set_type"]', button.dataset.setType || "본세트");
  setInputValue(row, 'input[name="cardio_incline"]', button.dataset.cardioIncline);
  setInputValue(row, 'input[name="cardio_speed"]', button.dataset.cardioSpeed);
  setInputValue(row, 'input[name="cardio_minutes"]', button.dataset.cardioMinutes);
  row.scrollIntoView({ behavior: "smooth", block: "center" });
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
    workoutClockPanel?.dataset.workoutDate ||
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

function addRow(list, type) {
  const selector = type === "set" ? ".set-entry-row" : ".meal-entry-row";
  const index = list.querySelectorAll(selector).length + 1;
  const row = document.createElement("div");
  row.className = type === "set" ? "set-entry-row" : "meal-entry-row";
  row.innerHTML = type === "set" ? setRowHtml(index) : mealRowHtml(index);
  list.append(row);
  row.querySelector("input").focus();
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
  return `
    <div class="compact-field-grid" data-strength-fields>
      <label>
        <span>무게 kg</span>
        <input name="set_weight" type="number" min="0" step="0.5" inputmode="decimal" placeholder="60">
      </label>
      <label>
        <span>횟수</span>
        <input name="set_reps" type="number" min="0" step="1" inputmode="numeric" placeholder="10">
      </label>
    </div>
    <select name="set_type" aria-label="세트 타입" data-strength-fields>
      <option value="본세트">본세트</option>
      <option value="워밍업">워밍업</option>
      <option value="드롭세트">드롭세트</option>
      <option value="실패">실패</option>
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
    <button class="row-copy-button" type="button" data-copy-set-row aria-label="세트 복사">복사</button>
    <button class="row-remove-button" type="button" data-remove-set-row aria-label="세트 삭제">×</button>
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
      number.textContent = index + 1;
    }
  });
}

function startRestTimer(seconds) {
  if (!seconds) {
    return;
  }
  restRemaining = seconds;
  updateRestTimerDisplay();
  clearInterval(restTimerId);
  restTimerId = setInterval(() => {
    restRemaining -= 1;
    updateRestTimerDisplay();
    if (restRemaining <= 0) {
      stopRestTimer();
    }
  }, 1000);
}

function stopRestTimer() {
  clearInterval(restTimerId);
  restTimerId = null;
  restRemaining = 0;
  updateRestTimerDisplay();
}

function updateRestTimerDisplay() {
  const display = document.querySelector("[data-rest-timer-display]");
  if (!display) {
    return;
  }
  const minutes = Math.floor(restRemaining / 60);
  const seconds = restRemaining % 60;
  display.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  display.classList.toggle("is-running", restRemaining > 0);
}

function startRestTimerFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const restSeconds = Number(params.get("rest") || 0);
  if (restSeconds > 0) {
    startRestTimer(restSeconds);
    params.delete("rest");
    const nextUrl = `${window.location.pathname}?${params.toString()}`.replace(/\?$/, "");
    window.history.replaceState({}, "", nextUrl);
  }
}

function workoutClockKey() {
  return `workout-clock:${workoutClockPanel?.dataset.workoutDate || "today"}`;
}

function readWorkoutClock() {
  try {
    return JSON.parse(localStorage.getItem(workoutClockKey()) || "{}");
  } catch {
    return {};
  }
}

function saveWorkoutClock(state) {
  try {
    localStorage.setItem(workoutClockKey(), JSON.stringify(state));
  } catch {
    // Timer display should keep working even if storage is unavailable.
  }
}

function updateWorkoutClockStatus(message) {
  const status = document.querySelector("[data-workout-clock-status]");
  if (!status) {
    return;
  }
  status.textContent = message;
}

function initWorkoutClock() {
  if (!workoutClockPanel) {
    return;
  }
  const state = readWorkoutClock();
  const initialElapsedMs = Number(workoutClockPanel.dataset.initialDuration || 0) * 1000;
  if (state.startedAt) {
    const elapsedMs = Number(state.elapsedMs || 0) + Math.max(0, Date.now() - Number(state.startedAt));
    saveWorkoutClock({ startedAt: null, elapsedMs, manualStarted: false });
    persistWorkoutClock("정지됨");
  } else if (state.elapsedMs === undefined || Math.abs(Number(state.elapsedMs || 0) - initialElapsedMs) > 1000) {
    saveWorkoutClock({ startedAt: null, elapsedMs: initialElapsedMs, manualStarted: false });
  }
  updateWorkoutClockStatus("시작 대기");
  updateWorkoutClockDisplay();
  clearInterval(workoutClockId);
  workoutClockId = setInterval(updateWorkoutClockDisplay, 1000);
  clearInterval(workoutClockSyncId);
  workoutClockSyncId = setInterval(() => {
    const currentState = readWorkoutClock();
    if (currentState.startedAt && currentState.manualStarted) {
      persistWorkoutClock();
    }
  }, 15000);
}

function startWorkoutClock(shouldUpdate = true) {
  const state = readWorkoutClock();
  if (state.startedAt) {
    return;
  }
  saveWorkoutClock({ startedAt: Date.now(), elapsedMs: Number(state.elapsedMs || 0), manualStarted: true });
  updateWorkoutClockStatus("측정 중");
  if (shouldUpdate) {
    updateWorkoutClockDisplay();
  }
}

function pauseWorkoutClock() {
  const state = readWorkoutClock();
  if (!state.startedAt) {
    return;
  }
  const elapsedMs = Number(state.elapsedMs || 0) + (Date.now() - Number(state.startedAt));
  saveWorkoutClock({ startedAt: null, elapsedMs, manualStarted: true });
  updateWorkoutClockDisplay();
  persistWorkoutClock("일시정지 저장됨");
}

function resetWorkoutClock() {
  saveWorkoutClock({ startedAt: null, elapsedMs: 0, manualStarted: false });
  updateWorkoutClockDisplay();
  persistWorkoutClock("시간 삭제됨");
}

function currentWorkoutElapsedMs() {
  const state = readWorkoutClock();
  return Number(state.elapsedMs || 0) + (state.startedAt ? Date.now() - Number(state.startedAt) : 0);
}

function currentWorkoutSeconds() {
  return Math.max(0, Math.floor(currentWorkoutElapsedMs() / 1000));
}

function persistWorkoutClock(successMessage = "자동 저장됨") {
  const url = workoutClockPanel?.dataset.durationUrl;
  if (!url) {
    return;
  }
  const clockState = readWorkoutClock();
  if (clockState.startedAt && !clockState.manualStarted) {
    saveWorkoutClock({ startedAt: null, elapsedMs: Number(clockState.elapsedMs || 0), manualStarted: false });
  }
  updateWorkoutClockStatus("저장 중");
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ duration_seconds: currentWorkoutSeconds() }),
    keepalive: true,
  })
    .then((response) => {
      if (!response.ok) {
        updateWorkoutClockStatus("저장 실패");
        return null;
      }
      updateWorkoutClockStatus(successMessage);
      return response.json();
    })
    .then((payload) => {
      if (payload?.duration_text) {
        updateSavedWorkoutDuration(payload.duration_text);
      }
    })
    .catch(() => {
      updateWorkoutClockStatus("저장 실패");
    });
}

function sendWorkoutClockBeacon() {
  const url = workoutClockPanel?.dataset.durationUrl;
  if (!url || !navigator.sendBeacon) {
    const fallbackState = readWorkoutClock();
    if (fallbackState.startedAt && fallbackState.manualStarted) {
      persistWorkoutClock();
    }
    return;
  }
  const state = readWorkoutClock();
  if (!state.startedAt || !state.manualStarted) {
    return;
  }
  const payload = new Blob([JSON.stringify({ duration_seconds: currentWorkoutSeconds() })], {
    type: "application/json",
  });
  navigator.sendBeacon(url, payload);
}

function updateWorkoutClockDisplay() {
  const display = document.querySelector("[data-workout-clock-display]");
  if (!display) {
    return;
  }
  const state = readWorkoutClock();
  const totalSeconds = currentWorkoutSeconds();
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  display.textContent = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  display.classList.toggle("is-running", Boolean(state.startedAt && state.manualStarted));
}

function updateSavedWorkoutDuration(durationText) {
  document.querySelectorAll("[data-workout-saved-duration]").forEach((element) => {
    element.textContent = durationText;
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

window.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden" && workoutClockPanel) {
    sendWorkoutClockBeacon();
  }
});

window.addEventListener("beforeunload", () => {
  if (workoutClockPanel) {
    sendWorkoutClockBeacon();
  }
});
