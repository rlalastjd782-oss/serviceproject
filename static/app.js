if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  });
}

document.addEventListener("click", (event) => {
  const addButton = event.target.closest("[data-add-set-row]");
  const removeButton = event.target.closest("[data-remove-set-row]");

  const list = document.querySelector("[data-set-list]");
  if (!list) {
    return;
  }

  if (removeButton) {
    if (list.querySelectorAll(".set-entry-row").length > 1) {
      removeButton.closest(".set-entry-row").remove();
      renumberSetRows(list);
    }
    return;
  }

  if (!addButton) {
    return;
  }

  const index = list.querySelectorAll(".set-entry-row").length + 1;
  const row = document.createElement("div");
  row.className = "set-entry-row";
  row.innerHTML = `
    <strong>${index}</strong>
    <label>
      <span>무게 kg</span>
      <input name="set_weight" type="number" min="0" step="0.5" inputmode="decimal" placeholder="60">
    </label>
    <label>
      <span>횟수</span>
      <input name="set_reps" type="number" min="0" step="1" inputmode="numeric" placeholder="10">
    </label>
    <label>
      <span>메모</span>
      <input name="set_memo" autocomplete="off" placeholder="추가 세트">
    </label>
    <button class="row-remove-button" type="button" data-remove-set-row aria-label="세트 삭제">×</button>
  `;
  list.append(row);
  row.querySelector("input").focus();
});

function renumberSetRows(list) {
  list.querySelectorAll(".set-entry-row").forEach((row, index) => {
    row.querySelector("strong").textContent = index + 1;
  });
}
