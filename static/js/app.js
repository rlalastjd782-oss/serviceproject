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
      const label = equipment ? `${safeName} · ${equipment}` : safeName;
      return `<button class="exercise-quick-button" type="button" data-exercise-name="${safeName}" data-equipment="${equipment}">${label}</button>`;
    })
    .join("");
  if (hiddenCount > 0) {
    const libraryUrl = exerciseQuickPanel.dataset.libraryUrl || "/exercises/library";
    exerciseQuickList.insertAdjacentHTML(
      "beforeend",
      `<a class="exercise-quick-button exercise-quick-more" href="${libraryUrl}?part=${encodeURIComponent(bodyPart)}">+${hiddenCount}개 더보기</a>`,
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
          <strong>${escapeHtml(target || "기존 기록")}</strong>
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


