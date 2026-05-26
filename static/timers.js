const workoutClockPanel = document.querySelector("[data-workout-clock]");
let restTimerId = null;
let restRemaining = 0;
let workoutClockId = null;
let workoutClockSyncId = null;

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
  let statusMessage = "시작 대기";
  if (state.startedAt && state.manualStarted) {
    statusMessage = "측정 중";
  } else if (state.startedAt) {
    const elapsedMs = Number(state.elapsedMs || 0) + Math.max(0, Date.now() - Number(state.startedAt));
    saveWorkoutClock({ startedAt: null, elapsedMs: Math.max(elapsedMs, initialElapsedMs), manualStarted: false });
  } else if (state.elapsedMs === undefined || Math.abs(Number(state.elapsedMs || 0) - initialElapsedMs) > 1000) {
    saveWorkoutClock({ startedAt: null, elapsedMs: initialElapsedMs, manualStarted: false });
  }
  updateWorkoutClockStatus(statusMessage);
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

function resetWorkoutClockDisplayOnly(message = "운동 완료") {
  saveWorkoutClock({ startedAt: null, elapsedMs: 0, manualStarted: false });
  updateWorkoutClockDisplay();
  updateWorkoutClockStatus(message);
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
    headers: { "Content-Type": "application/json", "X-CSRF-Token": currentCsrfToken() },
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
  const payload = new Blob([JSON.stringify({ duration_seconds: currentWorkoutSeconds(), csrf_token: currentCsrfToken() })], {
    type: "application/json",
  });
  navigator.sendBeacon(url, payload);
}

function currentCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";
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

window.addEventListener("beforeunload", () => {
  sendWorkoutClockBeacon();
});
