const scenarioSelect = document.querySelector("#scenarioSelect");
const romSelect = document.querySelector("#romSelect");
const filterSelect = document.querySelector("#filterSelect");
const recordsBody = document.querySelector("#recordsBody");
const sourcePath = document.querySelector("#sourcePath");
const recordSummary = document.querySelector("#recordSummary");
const buildButton = document.querySelector("#buildButton");
const notice = document.querySelector("#notice");
const itemFilter = document.querySelector("#itemFilter");
const itemSummary = document.querySelector("#itemSummary");
const itemsBody = document.querySelector("#itemsBody");
const commanderSelect = document.querySelector("#commanderSelect");
const classSummary = document.querySelector("#classSummary");
const classRoutesBody = document.querySelector("#classRoutesBody");

let scenarioModel = null;
let itemModel = null;
let classModel = null;
let scenarioModels = new Map();
let activeCommanderId = null;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function showNotice(message, success = false) {
  notice.textContent = message;
  notice.hidden = false;
  notice.classList.toggle("success", success);
}

function classOptions(selected, allowEmpty = false) {
  const empty = allowEmpty
    ? `<option value="255" ${selected === 255 ? "selected" : ""}>없음</option>`
    : "";
  return empty + scenarioModel.classes.map(item =>
    `<option value="${item.id}" ${item.id === selected ? "selected" : ""}>` +
    `${item.id.toString(16).padStart(2, "0").toUpperCase()} ${escapeHtml(item.ko)}</option>`
  ).join("");
}

function renderScenario() {
  const filter = filterSelect.value;
  recordsBody.innerHTML = "";
  let visible = 0;
  scenarioModel.records.forEach(record => {
    const isEnemy = record.role === "적군";
    if ((filter === "enemy" && !isEnemy) || (filter === "event" && isEnemy)) return;
    visible += 1;
    const row = document.createElement("tr");
    row.dataset.index = record.index;
    row.dataset.hidden = record.hidden;
    row.innerHTML = `
      <td>${record.index + 1}. ${escapeHtml(record.role)}</td>
      <td class="identity">${escapeHtml(record.name.ko)}<small>${escapeHtml(record.name.jp)}</small></td>
      <td><select data-field="class_id">${classOptions(record.class_id)}</select></td>
      <td><input data-field="level" type="number" min="0" max="255" value="${record.level}"></td>
      <td><input data-field="at" type="number" min="0" max="255" value="${record.at}"></td>
      <td><input data-field="df" type="number" min="0" max="255" value="${record.df}"></td>
      <td>${record.x === 255 ? "대기" : `${record.x}, ${record.y}`}</td>
      ${record.mercenaries.map((id, slot) =>
        `<td><select data-merc="${slot}">${classOptions(id, true)}</select></td>`
      ).join("")}
      <td class="offset">0x${record.offset.toString(16).toUpperCase()}</td>`;
    recordsBody.appendChild(row);
  });
  recordSummary.textContent = `${visible} / ${scenarioModel.record_count}개 배치`;
}

function collectScenarioEdits() {
  if (!scenarioModel) return;
  recordsBody.querySelectorAll("tr").forEach(row => {
    const record = scenarioModel.records[Number(row.dataset.index)];
    row.querySelectorAll("[data-field]").forEach(input => {
      record[input.dataset.field] = Number(input.value);
    });
    row.querySelectorAll("[data-merc]").forEach(input => {
      record.mercenaries[Number(input.dataset.merc)] = Number(input.value);
    });
  });
  scenarioModels.set(scenarioModel.number, scenarioModel);
}

async function loadScenario() {
  collectScenarioEdits();
  const number = Number(scenarioSelect.value);
  if (scenarioModels.has(number)) {
    scenarioModel = scenarioModels.get(number);
    renderScenario();
    return;
  }
  const response = await fetch(`/api/scenarios/${number}?rom=${romSelect.value}`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error);
  scenarioModel = data;
  scenarioModels.set(number, data);
  renderScenario();
}

function effectTypeOptions(selected) {
  return itemModel.effect_types.map(effect =>
    `<option value="${effect.id}" ${effect.id === selected ? "selected" : ""}>` +
    `${escapeHtml(effect.name)}</option>`
  ).join("");
}

function renderItems() {
  const filter = itemFilter.value;
  itemsBody.innerHTML = "";
  let visible = 0;
  itemModel.items.forEach(item => {
    if (filter !== "all" && item.category !== filter) return;
    visible += 1;
    const row = document.createElement("tr");
    row.dataset.itemId = item.item_id;
    const effects = item.effects.map((effect, slot) => `
      <td>
        <div class="effectEditor">
          <select data-effect-type="${slot}">${effectTypeOptions(effect.effect_type)}</select>
          <input data-effect-value="${slot}" type="number" min="-128" max="255" value="${effect.value}">
        </div>
      </td>`).join("");
    const special = item.special_behavior.length
      ? item.special_behavior.map(escapeHtml).join("<br>")
      : "";
    row.innerHTML = `
      <td>${item.item_id.toString(16).padStart(2, "0").toUpperCase()}</td>
      <td>${escapeHtml(item.category)}</td>
      <td class="identity">${escapeHtml(item.name)}<small>${escapeHtml(item.original_name)}</small></td>
      <td><div class="priceEditor"><input data-price type="number" min="0" max="65535" value="${item.price_units}"><span>×10P</span></div></td>
      ${effects}
      <td class="special">${special}</td>
      <td class="offset">0x${item.effect_offset.toString(16).toUpperCase()}</td>`;
    itemsBody.appendChild(row);
  });
  itemSummary.textContent = `${visible} / ${itemModel.items.length}개 아이템`;
}

function collectItemEdits() {
  if (!itemModel) return;
  itemsBody.querySelectorAll("tr").forEach(row => {
    const item = itemModel.items.find(entry => entry.item_id === Number(row.dataset.itemId));
    item.price_units = Number(row.querySelector("[data-price]").value);
    row.querySelectorAll("[data-effect-type]").forEach(input => {
      const slot = Number(input.dataset.effectType);
      item.effects[slot].effect_type = Number(input.value);
    });
    row.querySelectorAll("[data-effect-value]").forEach(input => {
      const slot = Number(input.dataset.effectValue);
      item.effects[slot].value = Number(input.value);
    });
  });
}

function editorClassOptions(selected) {
  return classModel.classes.map(item =>
    `<option value="${item.id}" ${item.id === selected ? "selected" : ""}>` +
    `${item.id.toString(16).padStart(2, "0").toUpperCase()} ${escapeHtml(item.ko)}</option>`
  ).join("");
}

function previewPath(classId) {
  return `/class-previews/${Number(classId).toString(16).padStart(2, "0").toUpperCase()}.png`;
}

function classChoice(classId, field, slot = "") {
  return `
    <div class="classChoice">
      <div class="classPreview">
        <img src="${previewPath(classId)}" alt="게임 내 편성 미리보기" onerror="this.hidden=true; this.nextElementSibling.hidden=false">
        <span hidden>원본<br>그림 없음</span>
      </div>
      <select data-class-field="${field}" data-class-slot="${slot}">${editorClassOptions(classId)}</select>
    </div>`;
}

function updateClassPreview(select) {
  const preview = select.closest(".classChoice").querySelector(".classPreview");
  const image = preview.querySelector("img");
  const fallback = preview.querySelector("span");
  image.hidden = false;
  fallback.hidden = true;
  image.src = `${previewPath(select.value)}?id=${select.value}`;
  fallback.innerHTML = "원본<br>그림 없음";
}

function renderClassRoutes() {
  const commander = classModel.commanders.find(
    entry => entry.commander_id === Number(commanderSelect.value)
  );
  classRoutesBody.innerHTML = "";
  commander.transitions.forEach(transition => {
    const row = document.createElement("tr");
    row.dataset.transitionIndex = transition.index;
    const candidates = transition.candidates.map((classId, slot) =>
      `<td>${classChoice(classId, "candidate", slot)}</td>`
    ).join("");
    row.innerHTML = `
      <td>${transition.index === 9 ? "최종" : transition.index + 1}</td>
      <td>${classChoice(transition.current_class, "current")}</td>
      ${candidates}
      ${transition.candidates.length < 3 ? "<td></td><td></td>" : ""}
      <td class="offset">0x${(commander.pointer + Math.min(transition.index, 9) * 8).toString(16).toUpperCase()}</td>`;
    classRoutesBody.appendChild(row);
  });
  classRoutesBody.querySelectorAll("[data-class-field]").forEach(select => {
    select.addEventListener("change", () => updateClassPreview(select));
  });
  activeCommanderId = commander.commander_id;
  classSummary.textContent = `${escapeHtml(commander.name)} · 10개 경로`;
}

function collectClassEdits() {
  if (!classModel || activeCommanderId === null) return;
  const commander = classModel.commanders.find(
    entry => entry.commander_id === activeCommanderId
  );
  classRoutesBody.querySelectorAll("tr").forEach(row => {
    const transition = commander.transitions[Number(row.dataset.transitionIndex)];
    transition.current_class = Number(
      row.querySelector('[data-class-field="current"]').value
    );
    row.querySelectorAll('[data-class-field="candidate"]').forEach(select => {
      transition.candidates[Number(select.dataset.classSlot)] = Number(select.value);
    });
  });
}

async function loadAll() {
  buildButton.disabled = true;
  notice.hidden = true;
  scenarioModels = new Map();
  activeCommanderId = null;
  try {
    const rom = romSelect.value;
    const [itemsResponse, classesResponse] = await Promise.all([
      fetch(`/api/items?rom=${rom}`),
      fetch(`/api/class-changes?rom=${rom}`),
    ]);
    itemModel = await itemsResponse.json();
    classModel = await classesResponse.json();
    if (!itemsResponse.ok) throw new Error(itemModel.error);
    if (!classesResponse.ok) throw new Error(classModel.error);
    await loadScenario();
    sourcePath.textContent = itemModel.rom_path;
    renderItems();
    commanderSelect.innerHTML = classModel.commanders.map(commander =>
      `<option value="${commander.commander_id}">${commander.commander_id}. ${escapeHtml(commander.name)}</option>`
    ).join("");
    renderClassRoutes();
  } catch (error) {
    showNotice(error.message);
  } finally {
    buildButton.disabled = false;
  }
}

async function buildRom() {
  collectScenarioEdits();
  collectItemEdits();
  collectClassEdits();
  buildButton.disabled = true;
  try {
    const response = await fetch("/api/build", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        rom: romSelect.value,
        scenarios: [...scenarioModels.values()].map(model => ({
          number: model.number,
          records: model.records,
        })),
        items: itemModel.items,
        class_changes: classModel.commanders,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    showNotice(`${data.output} 생성 완료 · 체크섬 ${data.checksum}`, true);
  } catch (error) {
    showNotice(error.message);
  } finally {
    buildButton.disabled = false;
  }
}

for (let number = 1; number <= 31; number += 1) {
  const option = document.createElement("option");
  option.value = number;
  option.textContent = number <= 27 ? `시나리오 ${number}` : `시나리오 X${number - 27}`;
  scenarioSelect.appendChild(option);
}

document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(item => item.classList.toggle("active", item === tab));
    document.querySelectorAll(".tabPanel").forEach(panel => {
      panel.classList.toggle("active", panel.id === `${tab.dataset.tab}Panel`);
    });
  });
});
scenarioSelect.addEventListener("change", async () => {
  try {
    await loadScenario();
  } catch (error) {
    showNotice(error.message);
  }
});
romSelect.addEventListener("change", loadAll);
filterSelect.addEventListener("change", () => {
  collectScenarioEdits();
  renderScenario();
});
itemFilter.addEventListener("change", () => {
  collectItemEdits();
  renderItems();
});
commanderSelect.addEventListener("change", () => {
  collectClassEdits();
  renderClassRoutes();
});
buildButton.addEventListener("click", buildRom);
loadAll();
