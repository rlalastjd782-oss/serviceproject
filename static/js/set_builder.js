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
      preview.textContent = unit === "lb" ? "lb 입력 후 kg로 저장" : "kg 기준 저장";
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

function cloneFirstSetToCount(setList) {
  const rows = getSetRows(setList);
  if (!rows.length) {
    return;
  }
  const countInput = document.querySelector("[data-set-count-input]");
  const targetCount = Math.min(20, Math.max(1, Number(countInput?.value || rows.length || 1)));
  while (getSetRows(setList).length < targetCount) {
    copySetRow(rows[0], setList);
  }
  getSetRows(setList)
    .slice(1, targetCount)
    .forEach((row) => {
      copyFieldValue(rows[0], row, 'input[name="set_weight"]');
      copyFieldValue(rows[0], row, 'select[name="set_weight_unit"]');
      copyFieldValue(rows[0], row, 'input[name="set_reps"]');
      copyFieldValue(rows[0], row, 'select[name="set_type"]');
      copyFieldValue(rows[0], row, 'input[name="cardio_incline"]');
      copyFieldValue(rows[0], row, 'input[name="cardio_speed"]');
      copyFieldValue(rows[0], row, 'input[name="cardio_minutes"]');
      copyFieldValue(rows[0], row, 'input[name="set_rpe"]');
      copyFieldValue(rows[0], row, 'input[name="set_memo"]');
    });
  updateSetCountInput();
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

function addRow(list, type, options = {}) {
  const selector = type === "set" ? ".set-entry-row" : ".meal-entry-row";
  const index = list.querySelectorAll(selector).length + 1;
  const row = document.createElement("div");
  row.className = type === "set" ? "set-entry-row" : "meal-entry-card meal-entry-row";
  row.innerHTML = type === "set" ? setRowHtml(index) : mealRowHtml(index);
  list.append(row);
  if (options.focus !== false) {
    row.querySelector("input").focus();
  }
  return row;
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
    <details class="set-advanced-options">
      <summary>고급</summary>
      <div class="set-advanced-grid">
        <select name="set_type" aria-label="세트 타입" data-strength-fields>
          ${setTypeOptionHtml}
        </select>
        <input name="set_rpe" type="number" min="1" max="10" step="0.5" inputmode="decimal" placeholder="체감강도">
        <input name="set_memo" autocomplete="off" placeholder="메모">
      </div>
    </details>
    <div class="set-row-actions">
      <button class="btn-ghost row-copy-button" type="button" data-copy-set-row aria-label="세트 복사">복사</button>
      <button class="btn-danger row-remove-button" type="button" data-remove-set-row aria-label="세트 삭제">X</button>
    </div>
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
