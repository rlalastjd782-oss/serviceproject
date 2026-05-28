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
