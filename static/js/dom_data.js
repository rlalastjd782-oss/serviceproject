function parseJsonData(element, key) {
  if (!element) {
    return {};
  }

  try {
    return JSON.parse(element.dataset[key] || "{}");
  } catch {
    return {};
  }
}
