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

function loadFoodEntry(button, mealList) {
  const firstRow = mealList.querySelector(".meal-entry-row");
  const row = firstRow && !firstRow.querySelector('input[name="meal_food_name"]').value ? firstRow : addRow(mealList, "meal");
  row.querySelector('input[name="meal_food_name"]').value = button.dataset.foodName || "";
  row.querySelector('input[name="meal_quantity"]').value = button.dataset.foodQuantity || "";
  row.querySelector('input[name="meal_grams"]').value = button.dataset.foodGrams || "";
  row.querySelector('input[name="meal_calories"]').value = button.dataset.foodCalories || "";
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
}

function mealRowHtml(index) {
  return `
    <strong>${index}</strong>
    <input name="meal_food_name" autocomplete="off" placeholder="음식" required>
    <div class="compact-field-grid meal-compact-grid">
      <input name="meal_quantity" type="number" min="0" step="1" inputmode="numeric" placeholder="개">
      <input name="meal_grams" type="number" min="0" step="0.1" inputmode="decimal" placeholder="g">
      <input name="meal_calories" type="number" min="0" step="1" inputmode="numeric" placeholder="kcal">
    </div>
    <button class="btn-danger row-remove-button" type="button" data-remove-meal-row aria-label="음식 삭제">×</button>
  `;
}
