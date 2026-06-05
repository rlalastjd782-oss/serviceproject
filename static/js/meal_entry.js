function renderFoodQuickList(mealType) {
  const foodQuickPanel = document.querySelector("[data-food-quick-panel]");
  const foodQuickList = document.querySelector("[data-food-quick-list]");
  const foodQuickEmpty = document.querySelector("[data-food-quick-empty]");
  if (!foodQuickPanel || !foodQuickList || !foodQuickEmpty) {
    return;
  }
  const foodsByMealType = parseJsonData(foodQuickPanel, "foodsByMealType");
  const foods = foodsByMealType[mealType] || [];
  foodQuickList.innerHTML = foods
    .map((food) => {
      const name = escapeHtml(food.food_name || "");
      return `<button class="exercise-quick-button" type="button" data-food-entry data-food-name="${name}" data-food-quantity="${food.quantity ?? ""}" data-food-grams="${food.grams ?? ""}" data-food-calories="${food.calories ?? ""}">${name}</button>`;
    })
    .join("");
  foodQuickEmpty.hidden = foods.length > 0;
}

function setMealQuickTab(tabName) {
  document.querySelectorAll("[data-meal-quick-tab]").forEach((button) => {
    const isActive = button.dataset.mealQuickTab === tabName;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
  document.querySelectorAll("[data-meal-quick-pane]").forEach((pane) => {
    pane.hidden = pane.dataset.mealQuickPane !== tabName;
  });
}

function setMealToolTab(tabName) {
  document.querySelectorAll("[data-meal-tool-tab]").forEach((button) => {
    const isActive = button.dataset.mealToolTab === tabName;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
  document.querySelectorAll("[data-meal-tool-pane]").forEach((pane) => {
    pane.hidden = pane.dataset.mealToolPane !== tabName;
  });
}

function expandMealToolRows(kind) {
  document.querySelectorAll(`.meal-tool-extra-${kind}[hidden]`).forEach((row) => {
    row.hidden = false;
  });
  document.querySelectorAll(`[data-meal-tool-more="${kind}"]`).forEach((button) => {
    button.setAttribute("aria-expanded", "true");
    button.hidden = true;
  });
}

function syncMealTypeSegments(selectedMealType) {
  const segments = document.querySelectorAll("[data-meal-type-option]");
  if (!segments.length) {
    return;
  }
  segments.forEach((segment) => {
    const isActive = segment.dataset.mealTypeOption === selectedMealType;
    segment.classList.toggle("is-active", isActive);
    segment.setAttribute("aria-pressed", String(isActive));
  });
}

function setMealTypeFromSegment(segment) {
  const select = document.querySelector("[data-meal-type-select]");
  if (!select) {
    return;
  }
  const selectedMealType = segment.dataset.mealTypeOption || "기타";
  select.value = selectedMealType;
  if (select.value !== selectedMealType) {
    select.value = "기타";
  }
  select.dispatchEvent(new Event("change", { bubbles: true }));
}

function loadFoodEntry(button, mealList) {
  const row = getMealRows(mealList).find((entry) => !entry.querySelector('input[name="meal_food_name"]')?.value) || addRow(mealList, "meal");
  row.querySelector('input[name="meal_food_name"]').value = button.dataset.foodName || "";
  row.querySelector('input[name="meal_quantity"]').value = button.dataset.foodQuantity || "";
  row.querySelector('input[name="meal_grams"]').value = button.dataset.foodGrams || "";
  row.querySelector('input[name="meal_calories"]').value = button.dataset.foodCalories || "";
  updateMealCountInput(mealList);
}

function getMealRows(mealList = document.querySelector("[data-meal-list]")) {
  return mealList ? Array.from(mealList.querySelectorAll(".meal-entry-row")) : [];
}

function updateMealCountInput(mealList = document.querySelector("[data-meal-list]")) {
  const input = document.querySelector("[data-meal-count-input]");
  if (input) {
    input.value = String(getMealRows(mealList).length || 1);
  }
}

function syncMealRowsToCount(mealList, targetCount) {
  const count = Math.max(1, Math.min(10, Number(targetCount || 1)));
  while (getMealRows(mealList).length < count) {
    addRow(mealList, "meal", { focus: false });
  }
  while (getMealRows(mealList).length > count) {
    getMealRows(mealList).at(-1)?.remove();
  }
  renumberRows(mealList, ".meal-entry-row");
  updateMealCountInput(mealList);
}

function cloneFirstMealToRows(mealList) {
  const rows = getMealRows(mealList);
  if (!rows.length) {
    return;
  }
  rows.slice(1).forEach((row) => {
    copyFieldValue(rows[0], row, 'input[name="meal_food_name"]');
    copyFieldValue(rows[0], row, 'input[name="meal_quantity"]');
    copyFieldValue(rows[0], row, 'input[name="meal_grams"]');
    copyFieldValue(rows[0], row, 'input[name="meal_calories"]');
  });
}

function resetMealForm(form, mealList) {
  form.reset();
  mealList.querySelectorAll(".meal-entry-row").forEach((row, index) => {
    if (index === 0) {
      row.querySelectorAll("input").forEach((input) => {
        input.value = "";
      });
    } else {
      row.remove();
    }
  });
  form.classList.add("is-collapsed");
  updateMealCountInput(mealList);
}

function mealRowHtml(index) {
  return `
    <div class="meal-card-head">
      <input name="meal_food_name" autocomplete="off" placeholder="음식 이름" required>
      <button class="btn-danger row-remove-button" type="button" data-remove-meal-row aria-label="음식 삭제">×</button>
    </div>
    <div class="meal-card-fields meal-compact-grid">
      <label>
        <span>개</span>
        <input name="meal_quantity" type="number" min="0" step="1" inputmode="numeric" placeholder="1">
      </label>
      <label>
        <span>g</span>
        <input name="meal_grams" type="number" min="0" step="0.1" inputmode="decimal" placeholder="80">
      </label>
      <label>
        <span>kcal</span>
        <input name="meal_calories" type="number" min="0" step="1" inputmode="numeric" placeholder="120">
      </label>
    </div>
  `;
}
