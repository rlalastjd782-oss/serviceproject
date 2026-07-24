function initPhotoCompare() {
  const stage = document.querySelector("[data-photo-compare]");
  if (!stage) {
    return;
  }
  const beforeImage = stage.querySelector("[data-photo-compare-before]");
  const afterImage = stage.querySelector("[data-photo-compare-after]");
  const overlay = stage.querySelector("[data-photo-compare-overlay]");
  const handle = stage.querySelector("[data-photo-compare-handle]");
  const range = stage.querySelector("[data-photo-compare-range]");
  const beforeSelect = document.querySelector("[data-photo-compare-before-select]");
  const afterSelect = document.querySelector("[data-photo-compare-after-select]");

  function setPosition(value) {
    overlay.style.clipPath = `inset(0 ${100 - value}% 0 0)`;
    handle.style.left = `${value}%`;
  }

  range?.addEventListener("input", () => setPosition(range.value));
  beforeSelect?.addEventListener("change", () => {
    beforeImage.src = beforeSelect.value;
  });
  afterSelect?.addEventListener("change", () => {
    afterImage.src = afterSelect.value;
  });

  setPosition(range?.value || 50);
}
