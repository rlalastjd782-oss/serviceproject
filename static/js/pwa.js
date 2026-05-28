if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      navigator.serviceWorker.register("/static/sw.js").catch(() => {});
    });
  });
}
