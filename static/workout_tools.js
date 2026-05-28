function initWorkoutTools() {
  if (!document.querySelector("[data-plate-tool]") && !document.querySelector("[data-warmup-tool]")) {
    return;
  }
  renderWorkoutTools();
}

function renderWorkoutTools() {
  renderPlateCalculator();
  renderWarmupCalculator();
}

function renderPlateCalculator() {
  const tool = document.querySelector("[data-plate-tool]");
  if (!tool) {
    return;
  }
  const target = Number(tool.querySelector("[data-plate-target]")?.value || 0);
  const bar = Number(tool.querySelector("[data-plate-bar]")?.value || 20);
  const result = tool.querySelector("[data-plate-result]");
  if (!result) {
    return;
  }
  const perSide = (target - bar) / 2;
  if (target <= 0 || perSide < 0) {
    result.textContent = "목표 중량을 입력하세요.";
    return;
  }
  const plates = calculatePlates(perSide);
  if (!plates.length) {
    result.innerHTML = `<span>원판 없음</span>`;
    return;
  }
  const totalText = plates.map((item) => item.label || `${item.weight}kg x ${item.count * 2}`).join(" · ");
  const sideText = plates.map((item) => item.label || `${item.weight}kg x ${item.count}`).join(" · ");
  result.innerHTML = `<span>전체 ${totalText}</span><span>한쪽 ${sideText}</span>`;
}

function renderWarmupCalculator() {
  const tool = document.querySelector("[data-warmup-tool]");
  if (!tool) {
    return;
  }
  const target = Number(tool.querySelector("[data-warmup-target]")?.value || 0);
  const step = Number(tool.querySelector("[data-warmup-step]")?.value || 2.5);
  const result = tool.querySelector("[data-warmup-result]");
  if (!result) {
    return;
  }
  if (target <= 0 || step <= 0) {
    result.innerHTML = `<span>본세트 중량을 입력하세요.</span>`;
    return;
  }
  const warmups = [
    { ratio: 0.4, reps: 8 },
    { ratio: 0.6, reps: 5 },
    { ratio: 0.8, reps: 3 },
  ];
  result.innerHTML = warmups
    .map((item) => {
      const weight = Math.max(step, Math.round((target * item.ratio) / step) * step);
      return `<span>${Math.round(item.ratio * 100)}% · ${formatToolWeight(weight)}kg x ${item.reps}</span>`;
    })
    .join("");
}

function calculatePlates(perSide) {
  const available = [20, 10, 5, 2.5];
  let remaining = Math.max(0, perSide);
  const result = [];
  available.forEach((weight) => {
    const count = Math.floor((remaining + 0.001) / weight);
    if (count > 0) {
      result.push({ weight: formatToolWeight(weight), count });
      remaining -= count * weight;
    }
  });
  if (remaining > 0.1) {
    result.push({ label: `${formatToolWeight(remaining)}kg 부족` });
  }
  return result;
}

function formatToolWeight(value) {
  const numberValue = Number(value);
  if (Number.isInteger(numberValue)) {
    return String(numberValue);
  }
  return numberValue.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}
