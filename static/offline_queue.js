const offlineQueueKey = "health-tracker-offline-queue-v1";

function queueOfflineForm(form, event) {
  if (!form || form.method?.toLowerCase() !== "post" || navigator.onLine) {
    return false;
  }
  const actionUrl = new URL(form.getAttribute("action") || window.location.href, window.location.origin);
  const queueablePaths = ["/sets", "/meals", "/body-metrics", "/recovery-checkins", "/rest-days", "/plans"];
  if (!queueablePaths.includes(actionUrl.pathname) || form.enctype === "multipart/form-data") {
    return false;
  }
  const formData = new FormData(form);
  const entries = Array.from(formData.entries()).map(([key, value]) => [key, String(value)]);
  const queue = readOfflineQueue();
  queue.push({
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    action: actionUrl.pathname + actionUrl.search,
    entries,
    createdAt: new Date().toISOString(),
  });
  writeOfflineQueue(queue);
  event.preventDefault();
  showOfflineQueueStatus(`오프라인 저장 ${queue.length}건`);
  return true;
}

function readOfflineQueue() {
  try {
    return JSON.parse(localStorage.getItem(offlineQueueKey) || "[]");
  } catch {
    return [];
  }
}

function writeOfflineQueue(queue) {
  localStorage.setItem(offlineQueueKey, JSON.stringify(queue));
}

async function processOfflineQueue() {
  if (!navigator.onLine) {
    return;
  }
  const queue = readOfflineQueue();
  if (!queue.length) {
    return;
  }
  const remaining = [];
  for (const item of queue) {
    try {
      const body = new URLSearchParams();
      item.entries.forEach(([key, value]) => body.append(key, value));
      const response = await fetch(item.action, {
        method: "POST",
        body,
        headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
        redirect: "manual",
      });
      if (!(response.ok || response.type === "opaqueredirect" || response.status === 0 || response.status === 302)) {
        remaining.push(item);
      }
    } catch {
      remaining.push(item);
    }
  }
  writeOfflineQueue(remaining);
  if (remaining.length !== queue.length) {
    showOfflineQueueStatus(remaining.length ? `동기화 후 ${remaining.length}건 대기` : "오프라인 입력 동기화 완료");
  }
}

function showOfflineQueueStatus(message) {
  let panel = document.querySelector("[data-offline-queue-status]");
  if (!panel) {
    panel = document.createElement("div");
    panel.dataset.offlineQueueStatus = "1";
    panel.className = "offline-queue-status";
    document.body.append(panel);
  }
  panel.textContent = message;
  panel.classList.add("is-visible");
  window.setTimeout(() => panel.classList.remove("is-visible"), 3500);
}
