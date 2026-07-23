const $ = selector => document.querySelector(selector);

const scenarioSelect = $("#scenarioSelect");
const romSelect = $("#romSelect");
const filterSelect = $("#filterSelect");
const recordsBody = $("#recordsBody");
const sourcePath = $("#sourcePath");
const recordSummary = $("#recordSummary");
const buildButton = $("#buildButton");
const notice = $("#notice");
const itemFilter = $("#itemFilter");
const itemSummary = $("#itemSummary");
const itemsBody = $("#itemsBody");
const commanderSelect = $("#commanderSelect");
const classSummary = $("#classSummary");
const classTree = $("#classTree");
const classInspector = $("#classInspector");
const assetPicker = $("#assetPicker");
const assetPickerSearch = $("#assetPickerSearch");
const assetPickerOptions = $("#assetPickerOptions");

let scenarioModel = null;
let itemModel = null;
let classModel = null;
let scenarioModels = new Map();
let activeCommanderId = null;
let selectedTreeClassId = null;
let pickerState = null;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function hexId(value) {
  return Number(value).toString(16).padStart(2, "0").toUpperCase();
}

function showNotice(message, success = false) {
  notice.textContent = message;
  notice.hidden = false;
  notice.classList.toggle("success", success);
}

function classInfo(classId) {
  return classModel.classes[Number(classId)];
}

function genericSpritePath(classId, palette = 1) {
  return `/class-sprites/generic/${hexId(classId)}-p${palette}.png`;
}

function commanderSpritePath(commanderId, classId) {
  return `/class-sprites/commanders/${commanderId}/${hexId(classId)}-p1.png`;
}

function spriteImage(classId, options = {}) {
  if (Number(classId) === 255) {
    return '<span class="emptySprite">-</span>';
  }
  const palette = options.palette ?? 1;
  const fallback = genericSpritePath(classId, palette);
  const source = options.commanderId
    ? commanderSpritePath(options.commanderId, classId)
    : fallback;
  const label = classInfo(classId)?.ko || `클래스 ${hexId(classId)}`;
  return `<img class="pixelSprite" src="${source}" data-fallback="${fallback}" alt="${escapeHtml(label)}">`;
}

function installSpriteFallbacks(root = document) {
  root.querySelectorAll("img[data-fallback]").forEach(image => {
    image.addEventListener("error", () => {
      const fallback = image.dataset.fallback;
      if (fallback && image.src !== new URL(fallback, location.href).href) {
        image.src = fallback;
      } else {
        image.hidden = true;
      }
    }, {once: true});
  });
}

function classOptions(selected, allowEmpty = false) {
  const classes = classModel?.classes || scenarioModel?.classes || [];
  const empty = allowEmpty
    ? `<option value="255" ${selected === 255 ? "selected" : ""}>없음</option>`
    : "";
  return empty + classes.map(item =>
    `<option value="${item.id}" ${item.id === selected ? "selected" : ""}>` +
    `${hexId(item.id)} ${escapeHtml(item.ko)}</option>`
  ).join("");
}

function scenarioPalette(record) {
  if (record.role.includes("적군")) return 2;
  if (record.role.includes("NPC")) return 0;
  return 1;
}

function mercenaryButton(classId, recordIndex, slot, palette) {
  const info = classId === 255 ? null : classInfo(classId);
  return `
    <button class="assetChoice" type="button" data-merc-picker
      data-record-index="${recordIndex}" data-slot="${slot}">
      ${spriteImage(classId, {palette})}
      <span>${info ? `${hexId(classId)} ${escapeHtml(info.ko)}` : "없음"}</span>
    </button>`;
}

function renderScenario() {
  const filter = filterSelect.value;
  recordsBody.innerHTML = "";
  let visible = 0;
  scenarioModel.records.forEach(record => {
    const isEnemy = record.role === "적군";
    if ((filter === "enemy" && !isEnemy) ||
        (filter === "event" && isEnemy)) return;
    visible += 1;
    const palette = scenarioPalette(record);
    const commanderId = record.name.id >= 1 && record.name.id <= 10
      ? record.name.id
      : null;
    const row = document.createElement("tr");
    row.dataset.index = record.index;
    row.dataset.hidden = record.hidden;
    row.innerHTML = `
      <td>${record.index + 1}. ${escapeHtml(record.role)}</td>
      <td class="spriteCell" data-record-sprite>
        ${spriteImage(record.class_id, {palette, commanderId})}
      </td>
      <td class="identity">${escapeHtml(record.name.ko)}
        <small>${escapeHtml(record.name.jp)}</small>
      </td>
      <td><select data-field="class_id">${classOptions(record.class_id)}</select></td>
      <td><input data-field="level" type="number" min="0" max="255" value="${record.level}"></td>
      <td><input data-field="at" type="number" min="0" max="255" value="${record.at}"></td>
      <td><input data-field="df" type="number" min="0" max="255" value="${record.df}"></td>
      <td>${record.x === 255 ? "대기" : `${record.x}, ${record.y}`}</td>
      ${record.mercenaries.map((id, slot) =>
        `<td>${mercenaryButton(id, record.index, slot, palette)}</td>`
      ).join("")}
      <td class="offset">0x${record.offset.toString(16).toUpperCase()}</td>`;
    recordsBody.appendChild(row);
  });
  installSpriteFallbacks(recordsBody);
  recordSummary.textContent =
    `${visible} / ${scenarioModel.record_count}개 배치`;
}

function collectScenarioEdits() {
  if (!scenarioModel) return;
  recordsBody.querySelectorAll("tr").forEach(row => {
    const record = scenarioModel.records[Number(row.dataset.index)];
    row.querySelectorAll("[data-field]").forEach(input => {
      record[input.dataset.field] = Number(input.value);
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
  const response = await fetch(
    `/api/scenarios/${number}?rom=${romSelect.value}`
  );
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
      <td>${hexId(item.item_id)}</td>
      <td class="itemIconCell"><img src="${item.icon_url}" alt=""></td>
      <td>${escapeHtml(item.category)}</td>
      <td class="identity">${escapeHtml(item.name)}
        <small>${escapeHtml(item.original_name)}</small>
      </td>
      <td><div class="priceEditor">
        <input data-price type="number" min="0" max="65535" value="${item.price_units}">
        <span>×10P</span>
      </div></td>
      ${effects}
      <td class="special">${special}</td>
      <td class="offset">0x${item.effect_offset.toString(16).toUpperCase()}</td>`;
    itemsBody.appendChild(row);
  });
  itemSummary.textContent =
    `${visible} / ${itemModel.items.length}개 아이템`;
}

function collectItemEdits() {
  if (!itemModel) return;
  itemsBody.querySelectorAll("tr").forEach(row => {
    const item = itemModel.items.find(
      entry => entry.item_id === Number(row.dataset.itemId)
    );
    item.price_units = Number(row.querySelector("[data-price]").value);
    row.querySelectorAll("[data-effect-type]").forEach(input => {
      item.effects[Number(input.dataset.effectType)].effect_type =
        Number(input.value);
    });
    row.querySelectorAll("[data-effect-value]").forEach(input => {
      item.effects[Number(input.dataset.effectValue)].value =
        Number(input.value);
    });
  });
}

function activeCommander() {
  return classModel.commanders.find(
    entry => entry.commander_id === Number(commanderSelect.value)
  );
}

function unique(values) {
  return [...new Set(values)];
}

function buildClassGraph(commander) {
  const levels = [[], [], [], [], []];
  const edges = [];
  commander.transitions.forEach(transition => {
    const sourceLevel = transition.source_tier - 1;
    levels[sourceLevel].push(transition.current_class);
    transition.candidates.forEach(candidate => {
      levels[sourceLevel + 1].push(candidate);
      edges.push({
        from: `${sourceLevel}-${transition.current_class}`,
        to: `${sourceLevel + 1}-${candidate}`,
      });
    });
  });
  return {levels: levels.map(unique), edges};
}

function classNode(classId, level, commander) {
  const info = classInfo(classId);
  const selected = selectedTreeClassId === classId ? " selected" : "";
  return `
    <button class="classNode${selected}" type="button"
      data-tree-class="${classId}" data-node-id="${level}-${classId}">
      <span class="nodeSprite">
        ${spriteImage(classId, {commanderId: commander.commander_id})}
      </span>
      <span><strong>${escapeHtml(info.ko)}</strong>
        <small>${hexId(classId)} · ${escapeHtml(info.jp)}</small>
      </span>
    </button>`;
}

function drawClassEdges(edges) {
  const svg = $("#classEdges");
  if (!svg) return;
  const treeRect = classTree.getBoundingClientRect();
  svg.setAttribute("viewBox", `0 0 ${classTree.scrollWidth} ${classTree.scrollHeight}`);
  svg.setAttribute("width", classTree.scrollWidth);
  svg.setAttribute("height", classTree.scrollHeight);
  svg.innerHTML = edges.map(edge => {
    const from = classTree.querySelector(`[data-node-id="${edge.from}"]`);
    const to = classTree.querySelector(`[data-node-id="${edge.to}"]`);
    if (!from || !to) return "";
    const a = from.getBoundingClientRect();
    const b = to.getBoundingClientRect();
    const x1 = a.right - treeRect.left + classTree.scrollLeft;
    const y1 = a.top + a.height / 2 - treeRect.top + classTree.scrollTop;
    const x2 = b.left - treeRect.left + classTree.scrollLeft;
    const y2 = b.top + b.height / 2 - treeRect.top + classTree.scrollTop;
    const bend = Math.max(28, (x2 - x1) / 2);
    return `<path d="M ${x1} ${y1} C ${x1 + bend} ${y1}, ` +
      `${x2 - bend} ${y2}, ${x2} ${y2}"></path>`;
  }).join("");
}

function hireRowFor(classId) {
  return classModel.class_hires.find(row => row.class_id === classId);
}

function hirePickerButton(classId, slot) {
  const info = classId === 255 ? null : classInfo(classId);
  return `
    <button class="assetChoice inspectorChoice" type="button"
      data-hire-picker data-slot="${slot}">
      ${spriteImage(classId)}
      <span>${info ? `${hexId(classId)} ${escapeHtml(info.ko)}` : "없음"}</span>
    </button>`;
}

function renderClassInspector() {
  const commander = activeCommander();
  const classId = selectedTreeClassId;
  if (classId === null) {
    classInspector.innerHTML = "<h2>클래스를 선택하세요</h2>";
    return;
  }
  const info = classInfo(classId);
  const transition = commander.transitions.find(
    entry => entry.current_class === classId
  );
  const hireRow = hireRowFor(classId);
  const choices = transition
    ? transition.candidates.map((candidate, slot) => `
        <label>다음 클래스 ${slot + 1}
          <select data-next-class="${slot}">${classOptions(candidate)}</select>
        </label>`).join("")
    : '<p class="terminalNote">이 경로에서 다음 클래스가 없는 종착 클래스입니다.</p>';
  classInspector.innerHTML = `
    <div class="inspectorTitle">
      <span class="inspectorSprite">
        ${spriteImage(classId, {commanderId: commander.commander_id})}
      </span>
      <div><h2>${escapeHtml(info.ko)}</h2>
        <p>${hexId(classId)} · ${escapeHtml(info.jp)}</p>
      </div>
    </div>
    ${transition ? `
      <label>현재 클래스
        <select id="currentClassSelect">${classOptions(classId)}</select>
      </label>
      <div class="nextClassGrid">${choices}</div>
      <p class="offset">경로 ROM 0x${transition.offset.toString(16).toUpperCase()}</p>
    ` : choices}
    <div class="hireEditor">
      <h3>새로 해금되는 용병</h3>
      <div class="hireChoices">
        ${hirePickerButton(hireRow.hire_class_ids[0], 0)}
        ${hirePickerButton(hireRow.hire_class_ids[1], 1)}
      </div>
      <p>클래스 전직 시 기존 고용 목록에 누적됩니다.</p>
      <p class="offset">클래스 ROM 0x${hireRow.offset.toString(16).toUpperCase()}</p>
    </div>`;
  installSpriteFallbacks(classInspector);

  const currentSelect = $("#currentClassSelect");
  if (currentSelect) {
    currentSelect.addEventListener("change", () => {
      transition.current_class = Number(currentSelect.value);
      selectedTreeClassId = transition.current_class;
      renderClassRoutes();
    });
  }
  classInspector.querySelectorAll("[data-next-class]").forEach(select => {
    select.addEventListener("change", () => {
      transition.candidates[Number(select.dataset.nextClass)] =
        Number(select.value);
      renderClassRoutes();
    });
  });
}

function renderClassRoutes() {
  const commander = activeCommander();
  const graph = buildClassGraph(commander);
  if (selectedTreeClassId === null ||
      !graph.levels.some(level => level.includes(selectedTreeClassId))) {
    selectedTreeClassId = graph.levels[0][0];
  }
  classTree.innerHTML = `
    <svg id="classEdges" class="classEdges" aria-hidden="true"></svg>
    ${graph.levels.map((level, levelIndex) => `
      <div class="classTier" data-tier="${levelIndex + 1}">
        ${level.map(classId => classNode(classId, levelIndex, commander)).join("")}
      </div>`).join("")}`;
  classTree.querySelectorAll("[data-tree-class]").forEach(node => {
    node.addEventListener("click", () => {
      selectedTreeClassId = Number(node.dataset.treeClass);
      renderClassRoutes();
    });
  });
  installSpriteFallbacks(classTree);
  activeCommanderId = commander.commander_id;
  classSummary.textContent =
    `${commander.name} · 실제 성장 최대 5단계 · ROM 분기 레코드 10개`;
  renderClassInspector();
  requestAnimationFrame(() => drawClassEdges(graph.edges));
}

function collectClassEdits() {
  // Class tree and hire controls update classModel immediately.
}

function renderPickerOptions() {
  if (!pickerState) return;
  const query = assetPickerSearch.value.trim().toLowerCase();
  const allowed = pickerState.allowedIds;
  const rows = [{id: 255, ko: "없음", jp: ""}]
    .concat(classModel.classes.filter(row => allowed.includes(row.id)))
    .filter(row => {
      if (!query) return true;
      return `${hexId(row.id)} ${row.ko} ${row.jp}`
        .toLowerCase().includes(query);
    });
  assetPickerOptions.innerHTML = rows.map(row => `
    <button type="button" class="pickerOption" data-picker-value="${row.id}">
      ${spriteImage(row.id, {palette: pickerState.palette})}
      <strong>${row.id === 255 ? "" : hexId(row.id)}</strong>
      <span>${escapeHtml(row.ko)}</span>
      <small>${escapeHtml(row.jp)}</small>
    </button>`).join("");
  installSpriteFallbacks(assetPickerOptions);
}

function openPicker(anchor, options) {
  pickerState = options;
  assetPickerSearch.value = "";
  renderPickerOptions();
  assetPicker.hidden = false;
  const rect = anchor.getBoundingClientRect();
  const left = Math.min(
    window.innerWidth - assetPicker.offsetWidth - 12,
    Math.max(12, rect.left)
  );
  const top = Math.min(
    window.innerHeight - assetPicker.offsetHeight - 12,
    rect.bottom + 6
  );
  assetPicker.style.left = `${left}px`;
  assetPicker.style.top = `${Math.max(12, top)}px`;
  assetPickerSearch.focus();
}

function closePicker() {
  assetPicker.hidden = true;
  pickerState = null;
}

async function loadAll() {
  buildButton.disabled = true;
  notice.hidden = true;
  scenarioModels = new Map();
  activeCommanderId = null;
  selectedTreeClassId = null;
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
      `<option value="${commander.commander_id}">` +
      `${commander.commander_id}. ${escapeHtml(commander.name)}</option>`
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
        class_hires: classModel.class_hires,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    showNotice(
      `${data.output} 생성 완료 · 체크섬 ${data.checksum}`,
      true
    );
  } catch (error) {
    showNotice(error.message);
  } finally {
    buildButton.disabled = false;
  }
}

for (let number = 1; number <= 31; number += 1) {
  const option = document.createElement("option");
  option.value = number;
  option.textContent = number <= 27
    ? `시나리오 ${number}`
    : `시나리오 X${number - 27}`;
  scenarioSelect.appendChild(option);
}

document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(item => {
      item.classList.toggle("active", item === tab);
    });
    document.querySelectorAll(".tabPanel").forEach(panel => {
      panel.classList.toggle(
        "active",
        panel.id === `${tab.dataset.tab}Panel`
      );
    });
    if (tab.dataset.tab === "classes") {
      requestAnimationFrame(renderClassRoutes);
    }
  });
});

recordsBody.addEventListener("change", event => {
  const select = event.target.closest('[data-field="class_id"]');
  if (!select) return;
  const row = select.closest("tr");
  const record = scenarioModel.records[Number(row.dataset.index)];
  record.class_id = Number(select.value);
  renderScenario();
});

recordsBody.addEventListener("click", event => {
  const button = event.target.closest("[data-merc-picker]");
  if (!button) return;
  const record = scenarioModel.records[Number(button.dataset.recordIndex)];
  openPicker(button, {
    allowedIds: classModel.classes.map(row => row.id),
    palette: scenarioPalette(record),
    onSelect: classId => {
      record.mercenaries[Number(button.dataset.slot)] = classId;
      closePicker();
      renderScenario();
    },
  });
});

classInspector.addEventListener("click", event => {
  const button = event.target.closest("[data-hire-picker]");
  if (!button) return;
  openPicker(button, {
    allowedIds: classModel.hire_class_ids,
    palette: 1,
    onSelect: classId => {
      hireRowFor(selectedTreeClassId)
        .hire_class_ids[Number(button.dataset.slot)] = classId;
      closePicker();
      renderClassInspector();
    },
  });
});

assetPickerSearch.addEventListener("input", renderPickerOptions);
assetPickerOptions.addEventListener("click", event => {
  const option = event.target.closest("[data-picker-value]");
  if (option && pickerState) {
    pickerState.onSelect(Number(option.dataset.pickerValue));
  }
});
document.addEventListener("pointerdown", event => {
  if (!assetPicker.hidden &&
      !assetPicker.contains(event.target) &&
      !event.target.closest("[data-merc-picker], [data-hire-picker]")) {
    closePicker();
  }
});
window.addEventListener("resize", closePicker);
window.addEventListener("resize", () => {
  if (activeCommanderId !== null) renderClassRoutes();
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
  activeCommanderId = Number(commanderSelect.value);
  selectedTreeClassId = null;
  renderClassRoutes();
});
buildButton.addEventListener("click", buildRom);
loadAll();
