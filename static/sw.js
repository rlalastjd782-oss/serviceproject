const CACHE_NAME = "workout-pwa-v1.25.11";
const ASSETS = [
  "/summaries/daily",
  "/summaries/weekly",
  "/summaries/monthly",
  "/summaries/yearly",
  "/summaries/yearly/compare",
  "/summaries/exercises",
  "/summaries/equipment",
  "/summaries/pr",
  "/calendar",
  "/meals/weekly",
  "/meals/monthly",
  "/records/search",
  "/records/check",
  "/meals/templates",
  "/data/center",
  "/locations/insights",
  "/insights/actions",
  "/tools/plate-calculator",
  "/locations",
  "/settings",
  "/static/styles.css",
  "/static/rules.css",
  "/static/ui_rebuild.css",
  "/static/timers.js",
  "/static/app.js",
  "/static/workout_entry.js",
  "/sw.js",
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
