function initNotificationTools() {
  document.querySelector("[data-enable-notifications]")?.addEventListener("click", async () => {
    if (!("Notification" in window)) {
      showOfflineQueueStatus("이 브라우저는 알림을 지원하지 않습니다.");
      return;
    }
    const permission = await Notification.requestPermission();
    showOfflineQueueStatus(permission === "granted" ? "알림을 허용했습니다." : "알림을 허용하지 않았습니다.");
  });

  const settingsPanel = document.querySelector("[data-reminder-settings]");
  if (!settingsPanel || !("Notification" in window) || Notification.permission !== "granted") {
    return;
  }
  const settings = parseJsonData(settingsPanel, "reminderSettings");
  const now = new Date();
  const todayKey = now.toISOString().slice(0, 10);
  Object.entries(settings).forEach(([key, item]) => {
    if (!item.enabled || !item.time_text) {
      return;
    }
    const [hour, minute] = item.time_text.split(":").map(Number);
    if (Number.isNaN(hour) || Number.isNaN(minute)) {
      return;
    }
    const due = new Date(now);
    due.setHours(hour, minute, 0, 0);
    const firedKey = `health-tracker-reminder-${key}-${todayKey}`;
    if (now >= due && localStorage.getItem(firedKey) !== "1") {
      new Notification(item.message || "기록을 확인하세요.");
      localStorage.setItem(firedKey, "1");
    }
  });
}
