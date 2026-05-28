const selectThemePreferenceElement = document.querySelector("[data-app-preferences]");
const selectThemeBodyPartClassMap = parseJsonData(selectThemePreferenceElement, "bodyPartClasses");
const selectThemeMealTypeClassMap = parseJsonData(selectThemePreferenceElement, "mealTypeClasses");

function applyBodyPartSelectColor(select) {
  const classNames = Object.values(selectThemeBodyPartClassMap);
  if (classNames.length) {
    select.classList.remove(...classNames);
  }
  select.classList.add(selectThemeBodyPartClassMap[select.value] || "body-part-other");
}

function applyMealTypeSelectColor(select) {
  const classNames = Object.values(selectThemeMealTypeClassMap);
  if (classNames.length) {
    select.classList.remove(...classNames);
  }
  select.classList.add(selectThemeMealTypeClassMap[select.value] || "meal-type-other");
}
