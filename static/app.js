if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  });
}

const bodyPartClassMap = {
  "하체": "body-part-legs",
  "가슴": "body-part-chest",
  "팔": "body-part-arms",
  "등": "body-part-back",
  "어깨": "body-part-shoulders",
  "기타": "body-part-other",
};

const mealTypeClassMap = {
  "아침": "meal-type-breakfast",
  "점심": "meal-type-lunch",
  "저녁": "meal-type-dinner",
  "간식": "meal-type-snack",
  "기타": "meal-type-other",
};

const exerciseQuickPanel = document.querySelector("[data-exercise-quick-panel]");
const exerciseQuickList = document.querySelector("[data-exercise-quick-list]");
const exerciseQuickEmpty = document.querySelector("[data-exercise-quick-empty]");
const recentSetTitle = document.querySelector("[data-recent-set-title]");
const recentSetList = document.querySelector("[data-recent-set-list]");
const exerciseDatalist = document.querySelector("[data-exercise-datalist]");
const exerciseNameInput = document.querySelector('input[name="exercise_name"]');
const exercisesByBodyPart = parseExerciseQuickData();
const recentSetsByExercise = parseJsonData(exerciseQuickPanel, "recentSetsByExercise");
const foodQuickPanel = document.querySelector("[data-food-quick-panel]");
const foodQuickList = document.querySelector("[data-food-quick-list]");
const foodQuickEmpty = document.querySelector("[data-food-quick-empty]");
const foodsByMealType = parseJsonData(foodQuickPanel, "foodsByMealType");

document.querySelectorAll("[data-body-part-select]").forEach((select) => {
  applyBodyPartSelectColor(select);
  renderExerciseQuickList(select.value);
});
document.querySelectorAll("[data-meal-type-select]").forEach((select) => {
  applyMealTypeSelectColor(select);
  renderFoodQuickList(select.value);
});

document.addEventListener("change", (event) => {
  const bodyPartSelect = event.target.closest("[data-body-part-select]");
  if (bodyPartSelect) {
    applyBodyPartSelectColor(bodyPartSelect);
    renderExerciseQuickList(bodyPartSelect.value);
    return;
  }

  const mealTypeSelect = event.target.closest("[data-meal-type-select]");
  if (mealTypeSelect) {
    applyMealTypeSelectColor(mealTypeSelect);
    renderFoodQuickList(mealTypeSelect.value);
    return;
  }

  if (event.target === exerciseNameInput) {
    renderRecentSetList(exerciseNameInput.value);
  }
});

document.addEventListener("click", (event) => {
  const addSetButton = event.target.closest("[data-add-set-row]");
  const removeSetButton = event.target.closest("[data-remove-set-row]");
  const addMealButton = event.target.closest("[data-add-meal-row]");
  const removeMealButton = event.target.closest("[data-remove-meal-row]");
  const editButton = event.target.closest("[data-toggle-edit]");
  const inlineAddButton = event.target.closest("[data-toggle-add]");
  const detailButton = event.target.closest("[data-toggle-detail]");
  const quickExerciseButton = event.target.closest("[data-exercise-name]");
  const recentSetButton = event.target.closest("[data-load-recent-sets]");
  const foodQuickButton = event.target.closest("[data-food-entry]");

  const setList = document.querySelector("[data-set-list]");
  const mealList = document.querySelector("[data-meal-list]");

  if (quickExerciseButton && exerciseNameInput) {
    exerciseNameInput.value = quickExerciseButton.dataset.exerciseName || "";
    renderRecentSetList(exerciseNameInput.value);
    exerciseNameInput.focus();
    return;
  }

  if (recentSetButton && setList) {
    loadRecentSets(recentSetButton.dataset.exerciseName || "", setList);
    return;
  }

  if (foodQuickButton && mealList) {
    loadFoodEntry(foodQuickButton, mealList);
    return;
  }

  if (removeSetButton && setList) {
    if (setList.querySelectorAll(".set-entry-row").length > 1) {
      removeSetButton.closest(".set-entry-row").remove();
      renumberRows(setList, ".set-entry-row");
    }
    return;
  }

  if (addSetButton && setList) {
    addRow(setList, "set");
    return;
  }

  if (removeMealButton && mealList) {
    if (mealList.querySelectorAll(".meal-entry-row").length > 1) {
      removeMealButton.closest(".meal-entry-row").remove();
      renumberRows(mealList, ".meal-entry-row");
    }
    return;
  }

  if (addMealButton && mealList) {
    addRow(mealList, "meal");
    return;
  }

  if (editButton) {
    const item = editButton.closest(".editable-list-item");
    item?.classList.add("is-editing");
    item?.querySelector("input")?.focus();
    return;
  }

  if (inlineAddButton) {
    const panel = inlineAddButton.closest(".inline-add-panel");
    panel?.classList.add("is-adding");
    panel?.querySelector("input:not([type='hidden'])")?.focus();
    return;
  }

  if (detailButton) {
    const target = document.getElementById(detailButton.dataset.detailTarget);
    if (!target) return;

    const isOpening = target.classList.contains("is-collapsed");
    if (detailButton.classList.contains("body-part-toggle")) {
      document.querySelectorAll(".body-part-exercise-list").forEach((list) => {
        if (list !== target) {
          list.classList.add("is-collapsed");
          list.setAttribute("aria-hidden", "true");
        }
      });
      document.querySelectorAll(".body-part-toggle").forEach((button) => {
        if (button !== detailButton) {
          button.classList.remove("is-active");
          button.setAttribute("aria-expanded", "false");
        }
      });
    }
    target.classList.toggle("is-collapsed", !isOpening);
    target.setAttribute("aria-hidden", String(!isOpening));
    detailButton.setAttribute("aria-expanded", String(isOpening));
    detailButton.classList.toggle("is-active", isOpening);
  }
});

function applyBodyPartSelectColor(select) {
  select.classList.remove(...Object.values(bodyPartClassMap));
  select.classList.add(bodyPartClassMap[select.value] || "body-part-other");
}

function applyMealTypeSelectColor(select) {
  select.classList.remove(...Object.values(mealTypeClassMap));
  select.classList.add(mealTypeClassMap[select.value] || "meal-type-other");
}

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

function parseExerciseQuickData() {
  return parseJsonData(exerciseQuickPanel, "exercisesByBodyPart");
}

function renderExerciseQuickList(bodyPart) {
  if (!exerciseQuickPanel || !exerciseQuickList || !exerciseQuickEmpty) {
    return;
  }

  const names = exercisesByBodyPart[bodyPart] || [];
  exerciseQuickList.innerHTML = names
    .map((name) => {
      const safeName = escapeHtml(name);
      return `<button class="exercise-quick-button" type="button" data-exercise-name="${safeName}">${safeName}</button>`;
    })
    .join("");
  if (exerciseDatalist) {
    exerciseDatalist.innerHTML = names
      .map((name) => `<option value="${escapeHtml(name)}"></option>`)
      .join("");
  }
  exerciseQuickEmpty.hidden = names.length > 0;
  renderRecentSetList(exerciseNameInput?.value || "");
}

function renderRecentSetList(exerciseName) {
  if (!recentSetTitle || !recentSetList) {
    return;
  }
  const sets = recentSetsByExercise[exerciseName] || [];
  recentSetTitle.hidden = sets.length === 0;
  recentSetList.innerHTML = sets.length
    ? `<button class="exercise-quick-button" type="button" data-load-recent-sets data-exercise-name="${escapeHtml(exerciseName)}">지난 세트 불러오기</button>`
    : "";
}

function renderFoodQuickList(mealType) {
  if (!foodQuickList || !foodQuickEmpty) {
    return;
  }
  const foods = foodsByMealType[mealType] || [];
  foodQuickList.innerHTML = foods
    .map((food) => {
      const name = escapeHtml(food.food_name || "");
      return `<button class="exercise-quick-button" type="button" data-food-entry data-food-name="${name}" data-food-quantity="${food.quantity ?? ""}" data-food-grams="${food.grams ?? ""}" data-food-calories="${food.calories ?? ""}">${name}</button>`;
    })
    .join("");
  foodQuickEmpty.hidden = foods.length > 0;
}

function loadRecentSets(exerciseName, setList) {
  const sets = recentSetsByExercise[exerciseName] || [];
  if (!sets.length) {
    return;
  }
  setList.innerHTML = "";
  sets.forEach((set) => {
    const row = document.createElement("div");
    row.className = "set-entry-row";
    row.innerHTML = setRowHtml(0);
    row.querySelector('input[name="set_weight"]').value = set.weight ?? "";
    row.querySelector('input[name="set_reps"]').value = set.reps ?? "";
    setList.append(row);
  });
}

function loadFoodEntry(button, mealList) {
  const firstRow = mealList.querySelector(".meal-entry-row");
  const row = firstRow && !firstRow.querySelector('input[name="meal_food_name"]').value ? firstRow : addRow(mealList, "meal");
  row.querySelector('input[name="meal_food_name"]').value = button.dataset.foodName || "";
  row.querySelector('input[name="meal_quantity"]').value = button.dataset.foodQuantity || "";
  row.querySelector('input[name="meal_grams"]').value = button.dataset.foodGrams || "";
  row.querySelector('input[name="meal_calories"]').value = button.dataset.foodCalories || "";
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[char];
  });
}

function addRow(list, type) {
  const selector = type === "set" ? ".set-entry-row" : ".meal-entry-row";
  const index = list.querySelectorAll(selector).length + 1;
  const row = document.createElement("div");
  row.className = type === "set" ? "set-entry-row" : "meal-entry-row";
  row.innerHTML = type === "set" ? setRowHtml(index) : mealRowHtml(index);
  list.append(row);
  row.querySelector("input").focus();
  return row;
}

function setRowHtml(index) {
  return `
    <div class="compact-field-grid">
      <label>
        <span>무게 kg</span>
        <input name="set_weight" type="number" min="0" step="0.5" inputmode="decimal" placeholder="60">
      </label>
      <label>
        <span>횟수</span>
        <input name="set_reps" type="number" min="0" step="1" inputmode="numeric" placeholder="10">
      </label>
    </div>
    <input name="set_memo" autocomplete="off" placeholder="메모">
    <button class="row-remove-button" type="button" data-remove-set-row aria-label="세트 삭제">×</button>
  `;
}

function mealRowHtml(index) {
  return `
    <input name="meal_food_name" autocomplete="off" placeholder="음식" required>
    <div class="compact-field-grid meal-compact-grid">
      <input name="meal_quantity" type="number" min="0" step="1" inputmode="numeric" placeholder="개">
      <input name="meal_grams" type="number" min="0" step="0.1" inputmode="decimal" placeholder="g">
      <input name="meal_calories" type="number" min="0" step="1" inputmode="numeric" placeholder="kcal">
    </div>
    <button class="row-remove-button" type="button" data-remove-meal-row aria-label="음식 삭제">×</button>
  `;
}

function renumberRows(list, selector) {
  list.querySelectorAll(selector).forEach((row, index) => {
    const number = row.querySelector("strong");
    if (number) {
      number.textContent = index + 1;
    }
  });
}
