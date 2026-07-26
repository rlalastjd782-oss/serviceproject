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
  const tiers = parseJsonData(readinessCoach, "readinessTiers");
  const tierList = Array.isArray(tiers) && tiers.length ? tiers : [{ min: 0, label: "회복 우선", guide: "", tone: "low" }];
  const tier = tierList.find((item) => percent >= item.min) || tierList[tierList.length - 1];
  readinessCoach.classList.remove("state-high", "state-normal", "state-low");
  readinessCoach.classList.add(`state-${tier.tone}`);
  setReadinessText(readinessCoach, "[data-readiness-label]", tier.label);
  setReadinessText(readinessCoach, "[data-readiness-guide]", tier.guide);
  setReadinessText(readinessCoach, "[data-readiness-percent]", percent);
  setReadinessText(readinessCoach, "[data-readiness-score]", score);
}

function setReadinessText(readinessCoach, selector, value) {
  const element = readinessCoach?.querySelector(selector);
  if (element) {
    element.textContent = String(value);
  }
}
