const CACHE_NAME = "workout-pwa-v2.6.3";
const ASSETS = [
  "/static/css/styles.css",
  "/static/css/core/styles_01.css",
  "/static/css/core/styles_02.css",
  "/static/css/core/styles_03.css",
  "/static/css/core/styles_04.css",
  "/static/css/today.css",
  "/static/css/feature_pages.css",
  "/static/css/features/feature_pages_01.css",
  "/static/css/features/feature_pages_02.css",
  "/static/css/features/feature_pages_03.css",
  "/static/css/features/feature_pages_04.css",
  "/static/css/features/feature_pages_05.css",
  "/static/css/features/feature_pages_06.css",
  "/static/css/features/feature_pages_07.css",
  "/static/css/meal.css",
  "/static/css/records.css",
  "/static/css/analysis.css",
  "/static/css/responsive.css",
  "/static/css/responsive/responsive_01.css",
  "/static/css/responsive/responsive_02.css",
  "/static/css/responsive/responsive_03.css",
  "/static/css/rules.css",
  "/static/css/ui_rebuild.css",
  "/static/css/overrides/ui_rebuild_01.css",
  "/static/css/overrides/ui_rebuild_02.css",
  "/static/css/overrides/ui_rebuild_03.css",
  "/static/css/overrides/ui_rebuild_04.css",
  "/static/js/dom_data.js",
  "/static/js/pwa.js",
  "/static/js/select_theme.js",
  "/static/js/readiness.js",
  "/static/js/timers.js",
  "/static/js/offline_queue.js",
  "/static/js/workout_tools.js",
  "/static/js/ui_interactions.js",
  "/static/js/notifications.js",
  "/static/js/meal_entry.js",
  "/static/js/form_submit.js",
  "/static/js/app.js",
  "/static/js/app_boot.js",
  "/static/js/workout_entry.js",
  "/sw.js",
  "/favicon.ico",
  "/static/manifest.webmanifest",
  "/static/icon.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))),
    ).then(() => self.clients.claim()),
  );
});

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("fetch", (event) => {
  const requestUrl = new URL(event.request.url);
  if (event.request.method !== "GET" || requestUrl.origin !== location.origin) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() => offlineFallback(event.request, requestUrl)),
  );
});

function offlineFallback(request, requestUrl) {
  return caches.match(request).then((cached) => {
    if (cached) {
      return cached;
    }
    if (request.mode !== "navigate") {
      return caches.match(requestUrl.pathname);
    }

    const mode = requestUrl.searchParams.get("mode");
    if (requestUrl.pathname === "/" && (mode === "workout" || mode === "meal")) {
      return caches.match(`/?mode=${mode}`);
    }
    return caches.match(requestUrl.pathname).then((page) => page || caches.match("/"));
  });
}
