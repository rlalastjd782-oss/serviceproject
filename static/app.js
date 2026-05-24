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
const exerciseNameInput = document.querySelector('input[name="exercise_name"]');
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

document.querySelectorAll("[data-body-part-select]").forEach((select) => {
  applyBodyPartSelectColor(select);
  renderExerciseQuickList(select.value);
  applyWorkoutInputMode(select.value);
});
document.querySelectorAll("[data-meal-type-select]").forEach((select) => {
  applyMealTypeSelectColor(select);
  renderFoodQuickList(select.value);
});

document.addEventListener("change", (event) => {
  const bodyPartSelect = event.target.closest("[data-body-part-select]");
  if (bodyPartSelect) {
    applyBodyPartSelectColor(bodyPartSelect);
    renderExerciseQuickList(bodyPartSelect.value);
    applyWorkoutInputMode(bodyPartSelect.value);
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

document.addEventListener("submit", (event) => {
  const durationForm = event.target.closest(".duration-edit-form");
  if (!durationForm || !workoutClockPanel) {
    return;
  }
  const action = event.submitter?.getAttribute("value");
  const hours = Number(durationForm.querySelector('input[name="duration_hours"]')?.value || 0);
  const minutes = Number(durationForm.querySelector('input[name="duration_minutes"]')?.value || 0);
  const durationSeconds = action === "reset" ? 0 : Math.max(0, hours * 3600 + minutes * 60);
  saveWorkoutClock({ startedAt: null, elapsedMs: durationSeconds * 1000 });
});

document.addEventListener("click", (event) => {
  const addSetButton = event.target.closest("[data-add-set-row]");
  const removeSetButton = event.target.closest("[data-remove-set-row]");
  const addMealButton = event.target.closest("[data-add-meal-row]");
  const removeMealButton = event.target.closest("[data-remove-meal-row]");
  const editButton = event.target.closest("[data-toggle-edit]");
  const inlineAddButton = event.target.closest("[data-toggle-add]");
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
  const workoutClockResetButton = event.target.closest("[data-workout-clock-reset]");

  const setList = document.querySelector("[data-set-list]");
  const mealList = document.querySelector("[data-meal-list]");

  if (quickExerciseButton && exerciseNameInput) {
    exerciseNameInput.value = quickExerciseButton.dataset.exerciseName || "";
    renderRecentSetList(exerciseNameInput.value);
    renderExerciseGuidance(exerciseNameInput.value);
    exerciseNameInput.focus();
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
    copySavedSet(copySavedSetButton, setList);
    return;
  }

  if (foodQuickButton && mealList) {
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
    item?.classList.add("is-editing");
    item?.querySelector("input")?.focus();
    return;
  }

  if (inlineAddButton) {
    const panel = inlineAddButton.closest(".inline-add-panel");
    panel?.classList.add("is-adding");
    panel?.querySelector("input:not([type='hidden'])")?.focus();
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
  const workoutForm = document.querySelector("[data-workout-form]");
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
  applyWorkoutInputMode(document.querySelector("[data-body-part-select]")?.value || "");
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
  copyFieldValue(sourceRow, row, 'input[name="set_memo"]');
  applyWorkoutInputMode(document.querySelector("[data-body-part-select]")?.value || "");
}

function copySavedSet(button, setList) {
  const bodyPartSelect = document.querySelector("[data-body-part-select]");
  const bodyPart = button.dataset.bodyPart || "기타";
  if (bodyPartSelect) {
    bodyPartSelect.value = bodyPart;
    applyBodyPartSelectColor(bodyPartSelect);
    renderExerciseQuickList(bodyPart);
    applyWorkoutInputMode(bodyPart);
  }
  if (exerciseNameInput) {
    exerciseNameInput.value = button.dataset.exerciseName || "";
    renderRecentSetList(exerciseNameInput.value);
    renderExerciseGuidance(exerciseNameInput.value);
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
    <button class="row-remove-button" type="button" data-remove-meal-row aria-label="음식 삭제">×</button>
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

function initWorkoutClock() {
  if (!workoutClockPanel) {
    return;
  }
  const state = readWorkoutClock();
  const initialElapsedMs = Number(workoutClockPanel.dataset.initialDuration || 0) * 1000;
  if (!state.startedAt && (state.elapsedMs === undefined || Math.abs(Number(state.elapsedMs || 0) - initialElapsedMs) > 1000)) {
    saveWorkoutClock({ startedAt: null, elapsedMs: initialElapsedMs });
  }
  if (workoutClockPanel.dataset.workoutMode === "1" && !readWorkoutClock().startedAt) {
    startWorkoutClock(false);
  }
  updateWorkoutClockDisplay();
  clearInterval(workoutClockId);
  workoutClockId = setInterval(updateWorkoutClockDisplay, 1000);
  clearInterval(workoutClockSyncId);
  workoutClockSyncId = setInterval(() => {
    const currentState = readWorkoutClock();
    if (currentState.startedAt) {
      persistWorkoutClock();
    }
  }, 15000);
}

function startWorkoutClock(shouldUpdate = true) {
  const state = readWorkoutClock();
  if (state.startedAt) {
    return;
  }
  saveWorkoutClock({ startedAt: Date.now(), elapsedMs: Number(state.elapsedMs || 0) });
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
  saveWorkoutClock({ startedAt: null, elapsedMs });
  updateWorkoutClockDisplay();
  persistWorkoutClock();
}

function resetWorkoutClock() {
  saveWorkoutClock({ startedAt: null, elapsedMs: 0 });
  updateWorkoutClockDisplay();
  persistWorkoutClock();
}

function currentWorkoutElapsedMs() {
  const state = readWorkoutClock();
  return Number(state.elapsedMs || 0) + (state.startedAt ? Date.now() - Number(state.startedAt) : 0);
}

function currentWorkoutSeconds() {
  return Math.max(0, Math.floor(currentWorkoutElapsedMs() / 1000));
}

function persistWorkoutClock() {
  const url = workoutClockPanel?.dataset.durationUrl;
  if (!url) {
    return;
  }
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ duration_seconds: currentWorkoutSeconds() }),
    keepalive: true,
  }).catch(() => {});
}

function sendWorkoutClockBeacon() {
  const url = workoutClockPanel?.dataset.durationUrl;
  if (!url || !navigator.sendBeacon) {
    persistWorkoutClock();
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
  display.classList.toggle("is-running", Boolean(state.startedAt));
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
