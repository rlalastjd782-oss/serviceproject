function renderReadinessCoach() {
  const readinessForm = document.querySelector("[data-readiness-form]");
  const readinessCoach = document.querySelector("[data-readiness-coach]");
  if (!readinessForm || !readinessCoach) {
    return;
  }
  const condition = Number(readinessForm.querySelector('[name="condition_score"]')?.value || 3);
  const sleep = Number(readinessForm.querySelector('[name="sleep_score"]')?.value || 3);
  const soreness = Number(readinessForm.querySelector('[name="soreness_score"]')?.value || 3);
  const fatigue = Number(readinessForm.querySelector('[name="fatigue_score"]')?.value || 3);
  const score = condition + sleep + (6 - soreness) + (6 - fatigue);
  const percent = Math.round((score / 20) * 100);
  let label = "회복 우선";
  let guide = "고중량보다 낮은 강도, 보조 운동, 유산소 위주로 조정하세요.";
  let state = "low";
  if (percent >= 75) {
    label = "공격 가능";
    guide = "메인 운동은 지난 기록보다 1회 또는 2.5kg 상향을 시도하세요.";
    state = "high";
  } else if (percent >= 55) {
    label = "표준 진행";
    guide = "지난 기록과 같은 중량에서 세트 완성도를 우선하세요.";
    state = "normal";
  }
  readinessCoach.classList.remove("state-high", "state-normal", "state-low");
  readinessCoach.classList.add(`state-${state}`);
  setReadinessText(readinessCoach, "[data-readiness-label]", label);
  setReadinessText(readinessCoach, "[data-readiness-guide]", guide);
  setReadinessText(readinessCoach, "[data-readiness-percent]", percent);
  setReadinessText(readinessCoach, "[data-readiness-score]", score);
}

function setReadinessText(readinessCoach, selector, value) {
  const element = readinessCoach?.querySelector(selector);
  if (element) {
    element.textContent = String(value);
  }
}
