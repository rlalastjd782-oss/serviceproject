function openInlineEdit(item) {
  if (!item) {
    return;
  }
  item.classList.add("is-editing");
  item.querySelector("input, select")?.focus();
}

function parseExerciseQuickData() {
  return parseJsonData(exerciseQuickPanel, "exercisesByBodyPart");
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
      const label = equipment ? `${safeName} 쨌 ${equipment}` : safeName;
      return `<button class="exercise-quick-button" type="button" data-exercise-name="${safeName}" data-equipment="${equipment}">${label}</button>`;
    })
    .join("");
  if (hiddenCount > 0) {
    const libraryUrl = exerciseQuickPanel.dataset.libraryUrl || "/exercises/library";
    exerciseQuickList.insertAdjacentHTML(
      "beforeend",
      `<a class="exercise-quick-button exercise-quick-more" href="${libraryUrl}?part=${encodeURIComponent(bodyPart)}">+${hiddenCount}媛?/a>`,
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
    ? `<button class="exercise-quick-button" type="button" data-load-recent-sets data-exercise-name="${escapeHtml(exerciseName)}">吏???명듃 遺덈윭?ㅺ린</button>`
    : "";
}

function renderExerciseGuidance(exerciseName) {
  if (exerciseStatView) {
    const stats = exerciseStatsByName[exerciseName];
    if (stats) {
      const bestWeight = stats.best_weight ? `${Number(stats.best_weight).toFixed(1)}kg` : "-kg";
      const bestReps = stats.best_reps ? `${Number(stats.best_reps)}회` : "-회";
      const bestVolume = stats.best_volume ? `${Number(stats.best_volume).toFixed(0)}kg` : "-kg";
      exerciseStatView.textContent = `理쒓렐: ${stats.recent || "-"} 쨌 理쒓퀬: ${bestWeight} / ${bestReps} / 蹂쇰ⅷ ${bestVolume}`;
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
          <span>?ㅼ쓬 ?명듃 쨌 ${escapeHtml(advice.type || "異붿쿇")}</span>
          <strong>${escapeHtml(target || "湲곗? 湲곕줉")}</strong>
          <button type="button" class="btn-small" data-apply-next-set="${escapeHtml(exerciseName)}">?곸슜</button>
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
    exerciseNoteView.textContent = note ? `硫붾え: ${note}` : "";
    exerciseNoteView.hidden = !note;
  }
  if (exerciseTargetView) {
    const setting = exerciseSettings[exerciseName] || {};
    const parts = [];
    if (setting.equipment) {
      parts.push(`?λ퉬 ${setting.equipment}`);
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
    exerciseTargetView.textContent = parts.length ? `紐⑺몴: ${parts.join(" 쨌 ")}` : "";
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
    button.textContent = isCollapsed ? "?대룞 異붽?" : "?낅젰 ?リ린";
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
  const bodyPart = button.dataset.bodyPart || "湲고?";
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
  row.className = type === "set" ? "set-entry-row" : "meal-entry-row";
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
    <strong class="set-row-number">${index}?명듃</strong>
    <div class="compact-field-grid" data-strength-fields>
      <label class="weight-unit-field">
        <span>臾닿쾶</span>
        <div class="weight-unit-control">
          <input name="set_weight" type="number" min="0" step="0.5" inputmode="decimal" placeholder="${escapeHtml(weightPlaceholder)}">
          <select name="set_weight_unit" aria-label="臾닿쾶 ?⑥쐞">
            <option value="kg">kg</option>
            <option value="lb">lb</option>
          </select>
        </div>
        <small class="weight-preview" data-weight-preview>kg 湲곗? ???/small>
      </label>
      <label>
        <span>?잛닔</span>
        <input name="set_reps" type="number" min="0" step="1" inputmode="numeric" placeholder="${escapeHtml(repsPlaceholder)}">
      </label>
    </div>
    <div class="compact-field-grid cardio-field-grid" data-cardio-fields hidden>
      <label>
        <span>?명겢?쇱씤</span>
        <input name="cardio_incline" type="number" min="0" step="0.1" inputmode="decimal" placeholder="8">
      </label>
      <label>
        <span>?띾룄</span>
        <input name="cardio_speed" type="number" min="0" step="0.1" inputmode="decimal" placeholder="5.5">
      </label>
      <label>
        <span>?쒓컙 遺?/span>
        <input name="cardio_minutes" type="number" min="0" step="1" inputmode="numeric" placeholder="30">
      </label>
    </div>
    <details class="set-advanced-options">
      <summary>怨좉툒</summary>
      <div class="set-advanced-grid">
        <select name="set_type" aria-label="?명듃 ??? data-strength-fields>
          ${setTypeOptionHtml}
        </select>
        <input name="set_rpe" type="number" min="1" max="10" step="0.5" inputmode="decimal" placeholder="泥닿컧媛뺣룄">
        <input name="set_memo" autocomplete="off" placeholder="硫붾え">
      </div>
    </details>
    <div class="set-row-actions">
      <button class="btn-ghost row-copy-button" type="button" data-copy-set-row aria-label="?명듃 蹂듭궗">蹂듭궗</button>
      <button class="btn-danger row-remove-button" type="button" data-remove-set-row aria-label="?명듃 ??젣">X</button>
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


