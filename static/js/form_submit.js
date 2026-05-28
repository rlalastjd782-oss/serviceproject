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

  if (form?.matches("[data-workout-complete-form]") || /\/sessions\/\d+\/complete$/.test(form?.getAttribute("action") || "")) {
    const completedValue = form.querySelector('input[name="completed"]')?.value;
    if (completedValue === "1" && typeof resetWorkoutClockDisplayOnly === "function") {
      resetWorkoutClockDisplayOnly("운동 완료");
    }
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
