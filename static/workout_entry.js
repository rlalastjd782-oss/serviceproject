(function () {
  const panel = document.querySelector("[data-exercise-quick-panel]");
  const workoutForm = document.querySelector("[data-workout-form]");
  const exerciseInput = workoutForm?.querySelector("[data-workout-exercise-input]");
  const setList = document.querySelector("[data-set-list]");
  const status = document.querySelector("[data-smart-default-status]");

  if (!panel || !workoutForm || !exerciseInput || !setList) {
    return;
  }

  const smartDefaults = readJson(panel.dataset.exerciseSmartDefaults || "{}");

  exerciseInput.addEventListener("change", () => applySmartDefaults(exerciseInput.value));
  exerciseInput.addEventListener("blur", () => applySmartDefaults(exerciseInput.value));

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-copy-saved-set], [data-exercise-name]");
    if (!button) {
      return;
    }
    window.setTimeout(() => applySmartDefaults(exerciseInput.value), 0);
  });

  function readJson(value) {
    try {
      return JSON.parse(value || "{}");
    } catch {
      return {};
    }
  }

  function applySmartDefaults(rawName) {
    const exerciseName = String(rawName || "").trim();
    const defaults = smartDefaults[exerciseName];
    if (!defaults) {
      hideStatus();
      return;
    }

    setSelectValue('select[name="body_part"]', defaults.body_part);
    setSelectValue('select[name="equipment"]', defaults.equipment);

    const targetCount = Number(defaults.set_count || 0);
    if (targetCount > 0 && typeof window.setBuilderCount === "function") {
      window.setBuilderCount(Math.min(20, Math.max(1, targetCount)));
    }

    const rows = Array.from(setList.querySelectorAll(".set-entry-row"));
    rows.forEach((row) => fillRow(row, defaults));

    const restText = defaults.rest_seconds ? ` · 휴식 ${defaults.rest_seconds}초` : "";
    const lastDate = defaults.last_date ? ` · 최근 ${defaults.last_date}` : "";
    showStatus(`이전 기록 기준으로 ${defaults.set_count || 1}세트 기본값을 채웠습니다${restText}${lastDate}.`);
  }

  function fillRow(row, defaults) {
    setInputValue(row, 'input[name="set_weight"]', defaults.weight);
    setInputValue(row, 'input[name="set_reps"]', defaults.reps);
    setInputValue(row, 'input[name="cardio_incline"]', defaults.cardio_incline);
    setInputValue(row, 'input[name="cardio_speed"]', defaults.cardio_speed);
    setInputValue(row, 'input[name="cardio_minutes"]', defaults.cardio_minutes);
    setSelectValueIn(row, 'select[name="set_type"]', defaults.set_type);
    setSelectValueIn(row, 'select[name="set_weight_unit"]', "kg");
  }

  function setInputValue(root, selector, value) {
    if (value === null || value === undefined || value === "") {
      return;
    }
    const input = root.querySelector(selector);
    if (input && !input.value) {
      input.value = Number.isFinite(Number(value)) ? String(value) : value;
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  function setSelectValue(selector, value) {
    setSelectValueIn(workoutForm, selector, value);
  }

  function setSelectValueIn(root, selector, value) {
    if (!value) {
      return;
    }
    const select = root.querySelector(selector);
    if (!select) {
      return;
    }
    const option = Array.from(select.options).find((item) => item.value === value);
    if (option) {
      select.value = value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  function showStatus(message) {
    if (!status) {
      return;
    }
    status.textContent = message;
    status.hidden = false;
  }

  function hideStatus() {
    if (status) {
      status.hidden = true;
    }
  }
})();
