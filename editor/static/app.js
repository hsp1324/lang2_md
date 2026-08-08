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
const commanderStartEditor = $("#commanderStartEditor");
const classStatsSelect = $("#classStatsSelect");
const classStatsSummary = $("#classStatsSummary");
const classStatsEditor = $("#classStatsEditor");
const testCommanderSelect = $("#testCommanderSelect");
const testClassSummary = $("#testClassSummary");
const testClassTree = $("#testClassTree");
const testClassInspector = $("#testClassInspector");
const aiCommanderSelect = $("#aiCommanderSelect");
const aiClassSummary = $("#aiClassSummary");
const aiClassTree = $("#aiClassTree");
const aiClassInspector = $("#aiClassInspector");
const sampleClassSummary = $("#sampleClassSummary");
const sampleClassGroups = $("#sampleClassGroups");
const assetPicker = $("#assetPicker");
const assetPickerSearch = $("#assetPickerSearch");
const assetPickerOptions = $("#assetPickerOptions");

let scenarioModel = null;
let itemModel = null;
let classModel = null;
let classProgressionModel = null;
let testClassSpriteModel = null;
let aiClassSpriteModel = null;
let sampleClassSpriteModel = null;
let scenarioModels = new Map();
let activeCommanderId = null;
let selectedTreeClassId = null;
let selectedTestClassId = null;
let selectedAiClassId = null;
let pickerState = null;
let aiMaskEditorState = null;
let aiMountMaskEditorState = null;
let aiDesignEditorState = null;
let aiSpriteReloadToken = Date.now();
const classSpriteAssetVersion = "paired-npc-and-pirates-v11";

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

function colorSwatches(colors) {
  return colors.map(color =>
    `<i class="colorSwatch" style="background:${color}" title="${color}"></i>`
  ).join("");
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
  return `/class-sprites/generic/${hexId(classId)}-p${palette}.png` +
    `?v=${classSpriteAssetVersion}`;
}

function representativeSpritePath(classId) {
  return `/class-sprites/representative/${hexId(classId)}-p1.png` +
    `?v=${classSpriteAssetVersion}`;
}

function commanderSpritePath(commanderId, classId) {
  return `/class-sprites/commanders/${commanderId}/${hexId(classId)}-p1.png` +
    `?v=${classSpriteAssetVersion}`;
}

function testClassSpritePath(commanderId, classId) {
  return `/test-class-sprites/${commanderId}/${hexId(classId)}.png`;
}

function aiClassSpritePath(commanderId, classId) {
  const version =
    aiClassSpriteModel?.asset_version ||
    "sherry-all-ai-v40";
  const revision = aiClassSpriteModel?.commanders?.[
    String(commanderId)
  ]?.classes?.[String(Number(classId))]?.design_revision || 0;
  return `/ai-class-sprites/${commanderId}/${hexId(classId)}.png` +
    `?v=${encodeURIComponent(version)}` +
    `&design=${encodeURIComponent(revision)}` +
    `&reload=${aiSpriteReloadToken}`;
}

function spriteImage(classId, options = {}) {
  if (Number(classId) === 255) {
    return '<span class="emptySprite">-</span>';
  }
  const palette = options.palette ?? 1;
  const fallback = options.representative === false
    ? genericSpritePath(classId, palette)
    : representativeSpritePath(classId);
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

function testSpriteImage(commanderId, classId) {
  const fallback = commanderSpritePath(commanderId, classId);
  const label = classInfo(classId)?.ko || `클래스 ${hexId(classId)}`;
  return `<img class="pixelSprite" src="${testClassSpritePath(
    commanderId,
    classId
  )}" data-fallback="${fallback}" alt="${escapeHtml(label)}">`;
}

function aiSpriteImage(commanderId, classId) {
  const fallback = commanderSpritePath(commanderId, classId);
  const label = classInfo(classId)?.ko || `클래스 ${hexId(classId)}`;
  return `<img class="pixelSprite" src="${aiClassSpritePath(
    commanderId,
    classId
  )}" data-fallback="${fallback}" alt="${escapeHtml(label)}">`;
}

function sampleClassAssetPath(path) {
  const normalized = String(path || "").replace(/^\/+/, "");
  const version = sampleClassSpriteModel?.asset_version || "sample-classes-v1";
  return `/${normalized}?v=${encodeURIComponent(version)}`;
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

function scenarioPalette() {
  // These assets are extracted against the class-change screen's CRAM.
  // Its other rows are not faction palettes, so p1 is the only canonical
  // preview for allied, enemy, and NPC records alike.
  return 1;
}

function mercenaryButton(classId, recordIndex, slot, palette) {
  const info = classId === 255 ? null : classInfo(classId);
  return `
    <button class="assetChoice" type="button" data-merc-picker
      data-record-index="${recordIndex}" data-slot="${slot}">
      ${spriteImage(classId, {palette, representative: false})}
      <span>${info ? `${hexId(classId)} ${escapeHtml(info.ko)}` : "없음"}</span>
    </button>`;
}

function classPickerButton(classId, attributes, options = {}) {
  const info = classInfo(classId);
  return `
    <button class="assetChoice classChoice" type="button" data-class-picker
      ${attributes}>
      ${spriteImage(classId, options)}
      <span>${hexId(classId)} ${escapeHtml(info.ko)}</span>
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
      <td class="identity">${escapeHtml(record.name.ko)}
        <small>${escapeHtml(record.name.jp)}</small>
      </td>
      <td>${classPickerButton(
        record.class_id,
        `data-scenario-class data-record-index="${record.index}"`,
        {palette, commanderId}
      )}</td>
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
  levels[0].push(commander.starting_class_id);
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
  (commander.hidden_class_routes || []).forEach(route => {
    levels[3].push(route.current_class);
    levels[4].push(route.hidden_class);
    edges.push({
      from: `3-${route.current_class}`,
      to: `4-${route.hidden_class}`,
    });
  });
  const uniqueEdges = [];
  const seenEdges = new Set();
  edges.forEach(edge => {
    const key = `${edge.from}>${edge.to}`;
    if (seenEdges.has(key)) return;
    seenEdges.add(key);
    uniqueEdges.push(edge);
  });
  return {levels: levels.map(unique), edges: uniqueEdges};
}

function recomputeCommanderTiers(commander) {
  const byCurrent = new Map(
    commander.transitions.map(transition => [
      transition.current_class,
      transition,
    ])
  );
  const tiers = new Map([[commander.starting_class_id, 1]]);
  const pending = [commander.starting_class_id];
  while (pending.length) {
    const current = pending.shift();
    const transition = byCurrent.get(current);
    if (!transition) continue;
    const nextTier = tiers.get(current) + 1;
    transition.candidates.forEach(candidate => {
      if (!byCurrent.has(candidate)) return;
      if (!tiers.has(candidate) || nextTier < tiers.get(candidate)) {
        tiers.set(candidate, nextTier);
        pending.push(candidate);
      }
    });
  }
  commander.transitions.forEach((transition, index) => {
    const fallback = index === 0 ? 1 : index <= 3 ? 2 : index <= 8 ? 3 : 4;
    transition.source_tier = Math.min(
      4,
      tiers.get(transition.current_class) || fallback,
    );
  });
}

function isHiddenClass(commander, classId) {
  return (commander.hidden_class_routes || []).some(
    route => route.hidden_class === classId
  );
}

function hiddenClassIdsFrom(commander, classId) {
  return (commander.hidden_class_routes || [])
    .filter(route => route.current_class === classId)
    .map(route => route.hidden_class);
}

function nextClassIdsFor(commander, classId) {
  const transition = commander.transitions.find(
    entry => entry.current_class === classId
  );
  return unique([
    ...(transition?.candidates || []),
    ...hiddenClassIdsFrom(commander, classId),
  ]);
}

function classNode(classId, level, commander, nextClassIds) {
  const info = classInfo(classId);
  const selected = selectedTreeClassId === classId ? " selected" : "";
  const nextCandidate = nextClassIds.includes(classId) ? " nextCandidate" : "";
  return `
    <button class="classNode${selected}${nextCandidate}" type="button"
      data-tree-class="${classId}" data-node-id="${level}-${classId}">
      <span class="nodeSprite">
        ${spriteImage(classId, {commanderId: commander.commander_id})}
      </span>
      <span><strong>${escapeHtml(info.ko)}</strong>
        <small>${hexId(classId)} · ${escapeHtml(info.jp)}${
          isHiddenClass(commander, classId) ? " · 히든" : ""
        }</small>
      </span>
    </button>`;
}

function drawClassEdges(
  edges,
  tree = classTree,
  svgSelector = "#classEdges",
  selectedClassId = selectedTreeClassId,
) {
  const svg = tree.querySelector(svgSelector);
  if (!svg) return;
  const treeRect = tree.getBoundingClientRect();
  svg.setAttribute("viewBox", `0 0 ${tree.scrollWidth} ${tree.scrollHeight}`);
  svg.setAttribute("width", tree.scrollWidth);
  svg.setAttribute("height", tree.scrollHeight);
  svg.innerHTML = edges.map(edge => {
    const from = tree.querySelector(`[data-node-id="${edge.from}"]`);
    const to = tree.querySelector(`[data-node-id="${edge.to}"]`);
    if (!from || !to) return "";
    const a = from.getBoundingClientRect();
    const b = to.getBoundingClientRect();
    const x1 = a.right - treeRect.left + tree.scrollLeft;
    const y1 = a.top + a.height / 2 - treeRect.top + tree.scrollTop;
    const x2 = b.left - treeRect.left + tree.scrollLeft;
    const y2 = b.top + b.height / 2 - treeRect.top + tree.scrollTop;
    const bend = Math.max(28, (x2 - x1) / 2);
    const active = Number(edge.from.split("-")[1]) === selectedClassId
      ? ' class="active"'
      : "";
    return `<path${active} d="M ${x1} ${y1} C ${x1 + bend} ${y1}, ` +
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

function renderCommanderStartEditor() {
  const commander = activeCommander();
  const classId = commander.starting_class_id;
  const hasProgression = commander.transitions.some(
    transition => transition.current_class === classId
  );
  commanderStartEditor.innerHTML = `
    <div>
      <strong>실제 시작 클래스</strong>
      <p>새 게임이나 해당 지휘관의 최초 합류 때 사용하는 초기 로스터입니다.</p>
    </div>
    ${classPickerButton(
      classId,
      "data-starting-class-picker",
      {commanderId: commander.commander_id}
    )}
    <span class="startClassMeta">LV${commander.starting_level} · EXP${
      commander.starting_experience
    } · ROM 0x${commander.starting_class_offset.toString(16).toUpperCase()}</span>
    ${hasProgression ? "" : `
      <p class="startClassWarning">이 클래스는 현재 전직 경로의 출발 레코드가 없어
      LV10에 도달해도 다음 클래스 선택지가 열리지 않습니다.</p>`}`;
  installSpriteFallbacks(commanderStartEditor);
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
  const hiddenClassIds = hiddenClassIdsFrom(commander, classId);
  const hireRow = hireRowFor(classId);
  const choices = transition
    ? transition.candidates.map((candidate, slot) => `
        <div class="nextClassChoice">
          <span>선택 ${slot + 1}</span>
          ${classPickerButton(
            candidate,
            `data-next-class-picker data-slot="${slot}"`,
            {commanderId: commander.commander_id}
          )}
        </div>`).join("")
    : hiddenClassIds.length
    ? `<div class="nextClassEditor">
        <h3>히든 클래스 ${hiddenClassIds.length}개</h3>
        <div class="nextClassGrid">${hiddenClassIds.map(candidate => `
          <div class="nextClassChoice">
            <span>읽기 전용 히든 경로</span>
            <div class="assetChoice inspectorChoice">
              ${spriteImage(candidate, {
                commanderId: commander.commander_id
              })}
              <span>${hexId(candidate)} ${escapeHtml(
                classInfo(candidate).ko
              )}</span>
            </div>
          </div>`).join("")}
        </div>
        <p>원작의 보조 5단계 경로이며 10개 물리 전직 레코드에는
          쓰지 않습니다.</p>
      </div>`
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
      <div class="currentClassEditor">
        <h3>경로 출발 클래스${
          classId === commander.starting_class_id
            ? " · 실제 시작 클래스"
            : ""
        }</h3>
        ${classPickerButton(
          classId,
          "data-current-class-picker",
          {commanderId: commander.commander_id}
        )}
      </div>
      <div class="nextClassEditor">
        <h3>다음 클래스 ${transition.candidates.length}개</h3>
        <div class="nextClassGrid">${choices}</div>
      </div>
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
}

function renderClassRoutes() {
  const commander = activeCommander();
  recomputeCommanderTiers(commander);
  const graph = buildClassGraph(commander);
  if (selectedTreeClassId === null ||
      !graph.levels.some(level => level.includes(selectedTreeClassId))) {
    selectedTreeClassId = graph.levels[0][0];
  }
  const nextClassIds = nextClassIdsFor(
    commander,
    selectedTreeClassId,
  );
  classTree.innerHTML = `
    <svg id="classEdges" class="classEdges" aria-hidden="true"></svg>
    ${graph.levels.map((level, levelIndex) => `
      <div class="classTier" data-tier="${levelIndex + 1}">
        ${level.map(classId =>
          classNode(classId, levelIndex, commander, nextClassIds)
        ).join("")}
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
    `${commander.name} · 시작 ${classInfo(commander.starting_class_id).ko} · ` +
    `실제 성장 최대 5단계 · 히든 ${
      (commander.hidden_class_routes || []).length
    }개 · ROM 분기 레코드 10개`;
  renderCommanderStartEditor();
  renderClassInspector();
  requestAnimationFrame(() => drawClassEdges(graph.edges));
}

function activeClassProgression() {
  return classProgressionModel.classes.find(
    row => row.class_id === Number(classStatsSelect.value)
  );
}

function abilityDefinition(abilityId) {
  return classProgressionModel.abilities.find(
    row => row.ability_id === Number(abilityId)
  );
}

function abilityOptions(selected) {
  const empty = classProgressionModel.empty_ability_id;
  return `<option value="${empty}" ${selected === empty ? "selected" : ""}>` +
    "없음</option>" + classProgressionModel.abilities.map(ability =>
      `<option value="${ability.ability_id}" ${
        selected === ability.ability_id ? "selected" : ""
      }>${hexId(ability.ability_id)} ${escapeHtml(ability.name)} · ${
        ability.kind === "summon" ? "소환" : "마법"
      }</option>`
    ).join("");
}

function renderClassStatsEditor() {
  if (!classProgressionModel) return;
  const row = activeClassProgression();
  if (!row) return;
  classStatsSummary.textContent =
    `${hexId(row.class_id)} ${row.name} · ROM 0x${
      row.record_offset.toString(16).toUpperCase()
    }`;
  classStatsEditor.innerHTML = `
    <header class="classStatsHeader">
      <span class="inspectorSprite">${spriteImage(row.class_id)}</span>
      <div>
        <h2>${escapeHtml(row.name)}</h2>
        <p>${hexId(row.class_id)} · ${escapeHtml(row.original_name)}</p>
      </div>
    </header>
    <section class="classStatCard">
      <h3>클래스 기본값</h3>
      <div class="classStatInputs">
        <label>MV
          <input data-class-stat="movement" type="number" min="0" max="255"
            value="${row.movement}">
        </label>
        <label>용병 수정 AT (A+)
          <input data-class-stat="soldier_at_correction" type="number"
            min="0" max="255" value="${row.soldier_at_correction}">
        </label>
        <label>용병 수정 DF (D+)
          <input data-class-stat="soldier_df_correction" type="number"
            min="0" max="255" value="${row.soldier_df_correction}">
        </label>
      </div>
      <p>같은 클래스 ID를 쓰는 아군·적군·NPC에 공통 적용됩니다.</p>
    </section>
    <section class="classStatCard">
      <h3>LV1~10 성장</h3>
      <p>선택한 지휘관 클래스만 쓰는 독립 성장표입니다. 일반 레벨업에서는
        도달한 레벨의 칸이 더해지며 LV1 칸은 원작 표의 시작 기준값입니다.</p>
      <div class="tableWrap compactTableWrap">
        <table class="growthTable">
          <thead><tr><th>도달 LV</th><th>MP</th><th>AT</th><th>DF</th></tr></thead>
          <tbody>${Array.from({length: 10}, (_, index) => `
            <tr><th>${index + 1}</th>${["mp", "at", "df"].map(stat => `
              <td><input data-growth-stat="${stat}" data-growth-level="${index}"
                type="number" min="0" max="99"
                value="${row.growth[stat][index]}"></td>`).join("")}
            </tr>`).join("")}</tbody>
        </table>
      </div>
      <p class="offset">원본 패턴 MP/AT/DF: ${row.growth_codes.map(
        value => `0x${hexId(value)}`
      ).join(" / ")}</p>
    </section>
    <section class="classStatCard">
      <h3>레벨업 마법·소환 습득</h3>
      <p>한 클래스에 최대 4개를 지정합니다. 습득 레벨은 마법 자체의 공통값이라
        여기서 바꾸면 그 마법을 가진 모든 클래스에 같이 적용됩니다.</p>
      <div class="abilitySlotGrid">${row.ability_ids.map((abilityId, slot) => {
        const ability = abilityId === classProgressionModel.empty_ability_id
          ? null
          : abilityDefinition(abilityId);
        return `<div class="abilitySlot">
          <label>슬롯 ${slot + 1}
            <select data-ability-slot="${slot}">${abilityOptions(abilityId)}</select>
          </label>
          ${ability ? `<label>공통 습득 LV
            <input data-ability-level="${ability.ability_id}" type="number"
              min="1" max="10" value="${ability.required_level}">
          </label>` : ""}
        </div>`;
      }).join("")}</div>
      <p>‘소환’은 소환 명령을 습득시킵니다. 실제 소환물 목록은 장비와 원작의
        별도 소환 테이블이 결정합니다.</p>
    </section>`;
  installSpriteFallbacks(classStatsEditor);
}

function activeTestCommander() {
  return classModel.commanders.find(
    entry => entry.commander_id === Number(testCommanderSelect.value)
  );
}

function testClassRow(commanderId, classId) {
  return testClassSpriteModel.commanders[String(commanderId)]
    .classes[String(classId)];
}

function testClassNode(classId, level, commander, nextClassIds) {
  const info = classInfo(classId);
  const row = testClassRow(commander.commander_id, classId);
  const selected = selectedTestClassId === classId ? " selected" : "";
  const nextCandidate = nextClassIds.includes(classId) ? " nextCandidate" : "";
  const redesigned = row.redesigned ? " redesigned" : "";
  return `
    <button class="classNode${selected}${nextCandidate}${redesigned}" type="button"
      data-test-tree-class="${classId}" data-node-id="${level}-${classId}">
      <span class="nodeSprite">
        ${testSpriteImage(commander.commander_id, classId)}
      </span>
      <span><strong>${escapeHtml(info.ko)}</strong>
        <small>${hexId(classId)} · ${escapeHtml(info.jp)}${
          isHiddenClass(commander, classId) ? " · 히든" : ""
        }</small>
      </span>
    </button>`;
}

function renderTestClassInspector() {
  const commander = activeTestCommander();
  const classId = selectedTestClassId;
  if (classId === null) {
    testClassInspector.innerHTML = "<h2>클래스를 선택하세요</h2>";
    return;
  }
  const info = classInfo(classId);
  const row = testClassRow(commander.commander_id, classId);
  testClassInspector.innerHTML = `
    <div class="inspectorTitle">
      <span class="inspectorSprite">
        ${testSpriteImage(commander.commander_id, classId)}
      </span>
      <div><h2>${escapeHtml(info.ko)}</h2>
        <p>${hexId(classId)} · ${escapeHtml(info.jp)} · ${row.tier}단계</p>
      </div>
    </div>
    <div class="spriteComparison">
      <div>
        <span>원본</span>
        <span class="comparisonSprite">
          ${spriteImage(classId, {commanderId: commander.commander_id})}
        </span>
      </div>
      <div>
        <span>${row.redesigned ? "새 디자인" : "원본 유지"}</span>
        <span class="comparisonSprite ${row.redesigned ? "changed" : ""}">
          ${testSpriteImage(commander.commander_id, classId)}
        </span>
      </div>
    </div>
    <dl class="designMetadata">
      <div><dt>디자인</dt><dd>${escapeHtml(row.feature)}</dd></div>
      <div><dt>원본 보존</dt><dd>얼굴·머리·외곽선 ${row.protected_face_pixel_count}픽셀 잠금</dd></div>
      <div><dt>변경량</dt><dd>${row.changed_pixel_count}픽셀 · 원본 불투명 픽셀 대비 ${Math.round(
        row.changed_ratio * 100
      )}%</dd></div>
      <div><dt>원본 그림</dt><dd>0x${hexId(row.source_sprite_id)}</dd></div>
      <div><dt>중복 클래스</dt><dd>${row.duplicate_group.map(
        value => `${hexId(value)} ${escapeHtml(classInfo(value).ko)}`
      ).join(" · ")}</dd></div>
    </dl>`;
  installSpriteFallbacks(testClassInspector);
}

function renderTestClassRoutes() {
  if (!testClassSpriteModel) return;
  const commander = activeTestCommander();
  const graph = buildClassGraph(commander);
  if (selectedTestClassId === null ||
      !graph.levels.some(level => level.includes(selectedTestClassId))) {
    selectedTestClassId = graph.levels[0][0];
  }
  const nextClassIds = nextClassIdsFor(
    commander,
    selectedTestClassId,
  );
  testClassTree.innerHTML = `
    <svg id="testClassEdges" class="classEdges" aria-hidden="true"></svg>
    ${graph.levels.map((level, levelIndex) => `
      <div class="classTier" data-tier="${levelIndex + 1}">
        ${level.map(classId =>
          testClassNode(classId, levelIndex, commander, nextClassIds)
        ).join("")}
      </div>`).join("")}`;
  testClassTree.querySelectorAll("[data-test-tree-class]").forEach(node => {
    node.addEventListener("click", () => {
      selectedTestClassId = Number(node.dataset.testTreeClass);
      renderTestClassRoutes();
    });
  });
  installSpriteFallbacks(testClassTree);
  const redesignedCount = Object.values(
    testClassSpriteModel.commanders[String(commander.commander_id)].classes
  ).filter(row => row.redesigned).length;
  testClassSummary.textContent =
    `${commander.name} · 새 디자인 ${redesignedCount}개 · 히든 ${
      (commander.hidden_class_routes || []).length
    }개 · 실제 ROM 미적용`;
  renderTestClassInspector();
  requestAnimationFrame(() => drawClassEdges(
    graph.edges,
    testClassTree,
    "#testClassEdges",
    selectedTestClassId,
  ));
}

function activeAiCommander() {
  return classModel.commanders.find(
    entry => entry.commander_id === Number(aiCommanderSelect.value)
  );
}

function aiClassRow(commanderId, classId) {
  return aiClassSpriteModel.commanders[String(commanderId)]
    .classes[String(classId)];
}

function aiClassNode(classId, level, commander, nextClassIds) {
  const info = classInfo(classId);
  const row = aiClassRow(commander.commander_id, classId);
  const displayClassName = row.class_name || info.ko;
  const selected = selectedAiClassId === classId ? " selected" : "";
  const nextCandidate = nextClassIds.includes(classId) ? " nextCandidate" : "";
  const generated = row.redesigned && row.ai_generated !== false
    ? " aiGenerated"
    : "";
  const pending = row.pending_redesign ? " aiPending" : "";
  return `
    <button class="classNode${generated}${pending}${selected}${nextCandidate}" type="button"
      data-ai-tree-class="${classId}" data-node-id="${level}-${classId}">
      <span class="nodeSprite">
        ${aiSpriteImage(commander.commander_id, classId)}
      </span>
      <span><strong>${escapeHtml(displayClassName)}</strong>
        <small>${hexId(classId)} · ${escapeHtml(info.jp)}${
          isHiddenClass(commander, classId) ? " · 히든" : ""
        }</small>
      </span>
    </button>`;
}

function identityMaskPointKey(x, y) {
  return `${x},${y}`;
}

function identityMaskPoints(set) {
  return [...set].map(value => value.split(",").map(Number))
    .sort((a, b) => a[1] - b[1] || a[0] - b[0]);
}

function drawIdentityMaskEditor() {
  const state = aiMaskEditorState;
  if (!state?.image.complete || !state.image.naturalWidth) return;
  const canvas = state.canvas;
  const context = canvas.getContext("2d");
  const cellSize = canvas.width / 16;
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.imageSmoothingEnabled = false;
  context.drawImage(state.image, 0, 0, canvas.width, canvas.height);
  context.fillStyle = "rgba(207, 65, 225, 0.52)";
  for (const point of identityMaskPoints(state.points)) {
    context.fillRect(
      point[0] * cellSize,
      point[1] * cellSize,
      cellSize,
      cellSize,
    );
  }
  context.beginPath();
  context.strokeStyle = "rgba(255, 255, 255, 0.22)";
  context.lineWidth = 1;
  for (let index = 0; index <= 16; index += 1) {
    const position = index * cellSize + (index < 16 ? 0.5 : -0.5);
    context.moveTo(position, 0);
    context.lineTo(position, canvas.height);
    context.moveTo(0, position);
    context.lineTo(canvas.width, position);
  }
  context.stroke();
  const count = $("#identityMaskCount");
  if (count) {
    const mode = state.useAutomatic
      ? "자동값"
      : state.dirty
      ? "수정 중"
      : state.savedMode === "custom"
      ? "사용자 저장값"
      : "자동 마스크";
    count.textContent = `${mode} · 원본 고정 ${state.points.size}픽셀`;
  }
}

function identityMaskCell(event, canvas) {
  const bounds = canvas.getBoundingClientRect();
  return [
    Math.max(0, Math.min(
      15,
      Math.floor((event.clientX - bounds.left) / bounds.width * 16),
    )),
    Math.max(0, Math.min(
      15,
      Math.floor((event.clientY - bounds.top) / bounds.height * 16),
    )),
  ];
}

function setIdentityMaskPoint(x, y, locked) {
  const state = aiMaskEditorState;
  const key = identityMaskPointKey(x, y);
  if (locked) {
    state.points.add(key);
  } else {
    state.points.delete(key);
  }
  state.dirty = true;
  state.useAutomatic = false;
  drawIdentityMaskEditor();
}

async function applyIdentityMask() {
  const state = aiMaskEditorState;
  if (!state || state.saving) return;
  const commanderId = state.commanderId;
  const classId = state.classId;
  state.saving = true;
  const applyButton = $("#identityMaskApply");
  const resetButton = $("#identityMaskReset");
  const clearButton = $("#identityMaskClear");
  for (const button of [applyButton, resetButton, clearButton]) {
    if (button) button.disabled = true;
  }
  applyButton.textContent = "마스크 저장 중…";
  try {
    const response = await fetch("/api/ai-class-mask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        commander_id: state.commanderId,
        class_id: state.classId,
        points: identityMaskPoints(state.points),
        reset: state.useAutomatic,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    const row = aiClassRow(commanderId, classId);
    row.identity_lock_points = identityMaskPoints(state.points);
    row.identity_lock_pixel_count = data.identity_lock_pixel_count;
    row.identity_lock_mode = data.identity_lock_mode;
    row.identity_mask_pending_rebuild = true;
    renderAiClassInspector();
    showNotice(
      `${activeAiCommander().name} ${classInfo(classId).ko} · ` +
      `원본 고정 ${data.identity_lock_pixel_count}픽셀 저장 완료 · ` +
      "다음 AI 변환 때 적용",
      true,
    );
  } catch (error) {
    showNotice(error.message);
    state.saving = false;
    if (applyButton) {
      applyButton.disabled = false;
      applyButton.textContent = "마스크 저장";
    }
    for (const button of [resetButton, clearButton]) {
      if (button) button.disabled = false;
    }
  }
}

function setupIdentityMaskEditor(commander, classId, row) {
  const canvas = $("#identityMaskCanvas");
  if (!canvas) {
    aiMaskEditorState = null;
    return;
  }
  const points = new Set(
    (row.identity_lock_points || []).map(point =>
      identityMaskPointKey(point[0], point[1])
    )
  );
  const defaultPoints = new Set(
    (row.identity_lock_default_points || []).map(point =>
      identityMaskPointKey(point[0], point[1])
    )
  );
  const image = new Image();
  aiMaskEditorState = {
    commanderId: commander.commander_id,
    classId,
    canvas,
    image,
    points,
    defaultPoints,
    savedMode: row.identity_lock_mode || "automatic",
    dirty: false,
    useAutomatic: false,
    saving: false,
    dragging: false,
    dragLocked: true,
    lastCell: null,
  };
  const state = aiMaskEditorState;
  image.addEventListener("load", () => {
    if (aiMaskEditorState === state) drawIdentityMaskEditor();
  });
  image.src = `${commanderSpritePath(
    commander.commander_id,
    classId,
  )}?mask=${aiSpriteReloadToken}`;
  canvas.addEventListener("pointerdown", event => {
    const [x, y] = identityMaskCell(event, canvas);
    const key = identityMaskPointKey(x, y);
    state.dragging = true;
    state.dragLocked = !state.points.has(key);
    state.lastCell = key;
    canvas.setPointerCapture(event.pointerId);
    setIdentityMaskPoint(x, y, state.dragLocked);
    event.preventDefault();
  });
  canvas.addEventListener("pointermove", event => {
    if (!state.dragging) return;
    const [x, y] = identityMaskCell(event, canvas);
    const key = identityMaskPointKey(x, y);
    if (key !== state.lastCell) {
      state.lastCell = key;
      setIdentityMaskPoint(x, y, state.dragLocked);
    }
  });
  const finishDrag = () => {
    state.dragging = false;
    state.lastCell = null;
  };
  canvas.addEventListener("pointerup", finishDrag);
  canvas.addEventListener("pointercancel", finishDrag);
  $("#identityMaskClear").addEventListener("click", () => {
    state.points.clear();
    state.dirty = true;
    state.useAutomatic = false;
    drawIdentityMaskEditor();
  });
  $("#identityMaskReset").addEventListener("click", () => {
    state.points = new Set(state.defaultPoints);
    state.dirty = true;
    state.useAutomatic = true;
    drawIdentityMaskEditor();
  });
  $("#identityMaskApply").addEventListener("click", applyIdentityMask);
  drawIdentityMaskEditor();
}

function drawMountMaskEditor() {
  const state = aiMountMaskEditorState;
  if (!state?.image.complete || !state.image.naturalWidth) return;
  const canvas = state.canvas;
  const context = canvas.getContext("2d");
  const cellSize = canvas.width / 16;
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.imageSmoothingEnabled = false;
  context.drawImage(state.image, 0, 0, canvas.width, canvas.height);
  context.fillStyle = "rgba(37, 190, 210, 0.52)";
  for (const point of identityMaskPoints(state.points)) {
    context.fillRect(
      point[0] * cellSize,
      point[1] * cellSize,
      cellSize,
      cellSize,
    );
  }
  context.beginPath();
  context.strokeStyle = "rgba(255, 255, 255, 0.22)";
  context.lineWidth = 1;
  for (let index = 0; index <= 16; index += 1) {
    const position = index * cellSize + (index < 16 ? 0.5 : -0.5);
    context.moveTo(position, 0);
    context.lineTo(position, canvas.height);
    context.moveTo(0, position);
    context.lineTo(canvas.width, position);
  }
  context.stroke();
  const count = $("#mountMaskCount");
  if (count) {
    count.textContent =
      `${state.dirty ? "수정 중" : "사용자 저장값"} · ` +
      `원본 탈것 고정 ${state.points.size}픽셀`;
  }
}

function setMountMaskPoint(x, y, locked) {
  const state = aiMountMaskEditorState;
  const key = identityMaskPointKey(x, y);
  if (locked) {
    state.points.add(key);
  } else {
    state.points.delete(key);
  }
  state.dirty = true;
  drawMountMaskEditor();
}

async function applyMountMask() {
  const state = aiMountMaskEditorState;
  if (!state || state.saving) return;
  const commanderId = state.commanderId;
  const classId = state.classId;
  state.saving = true;
  const applyButton = $("#mountMaskApply");
  const reloadButton = $("#mountMaskReload");
  const clearButton = $("#mountMaskClear");
  for (const button of [applyButton, reloadButton, clearButton]) {
    if (button) button.disabled = true;
  }
  if (applyButton) applyButton.textContent = "탈것 마스크 저장 중…";
  try {
    const response = await fetch("/api/ai-class-mount-mask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        commander_id: commanderId,
        class_id: classId,
        points: identityMaskPoints(state.points),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    const row = aiClassRow(commanderId, classId);
    row.mount_lock_points = identityMaskPoints(state.points);
    row.mount_lock_pixel_count = data.mount_lock_pixel_count;
    row.mount_lock_mode = data.mount_lock_mode;
    row.mount_mask_pending_rebuild = true;
    renderAiClassInspector();
    showNotice(
      `${activeAiCommander().name} ${classInfo(classId).ko} · ` +
      `원본 탈것 ${data.mount_lock_pixel_count}픽셀 저장 완료 · ` +
      "다음 AI 변환 때 적용",
      true,
    );
  } catch (error) {
    showNotice(error.message);
    state.saving = false;
    if (applyButton) {
      applyButton.disabled = false;
      applyButton.textContent = "탈것 마스크 저장";
    }
    for (const button of [reloadButton, clearButton]) {
      if (button) button.disabled = false;
    }
  }
}

function setupMountMaskEditor(commander, classId, row) {
  const canvas = $("#mountMaskCanvas");
  if (!canvas) {
    aiMountMaskEditorState = null;
    return;
  }
  const points = new Set(
    (row.mount_lock_points || []).map(point =>
      identityMaskPointKey(point[0], point[1])
    )
  );
  const image = new Image();
  aiMountMaskEditorState = {
    commanderId: commander.commander_id,
    classId,
    canvas,
    image,
    points,
    savedPoints: new Set(points),
    dirty: false,
    saving: false,
    dragging: false,
    dragLocked: true,
    lastCell: null,
  };
  const state = aiMountMaskEditorState;
  image.addEventListener("load", () => {
    if (aiMountMaskEditorState === state) drawMountMaskEditor();
  });
  image.src = `${commanderSpritePath(
    commander.commander_id,
    classId,
  )}?mount-mask=${aiSpriteReloadToken}`;
  canvas.addEventListener("pointerdown", event => {
    const [x, y] = identityMaskCell(event, canvas);
    const key = identityMaskPointKey(x, y);
    state.dragging = true;
    state.dragLocked = !state.points.has(key);
    state.lastCell = key;
    canvas.setPointerCapture(event.pointerId);
    setMountMaskPoint(x, y, state.dragLocked);
    event.preventDefault();
  });
  canvas.addEventListener("pointermove", event => {
    if (!state.dragging) return;
    const [x, y] = identityMaskCell(event, canvas);
    const key = identityMaskPointKey(x, y);
    if (key !== state.lastCell) {
      state.lastCell = key;
      setMountMaskPoint(x, y, state.dragLocked);
    }
  });
  const finishDrag = () => {
    state.dragging = false;
    state.lastCell = null;
  };
  canvas.addEventListener("pointerup", finishDrag);
  canvas.addEventListener("pointercancel", finishDrag);
  $("#mountMaskClear").addEventListener("click", () => {
    state.points.clear();
    state.dirty = true;
    drawMountMaskEditor();
  });
  $("#mountMaskReload").addEventListener("click", () => {
    state.points = new Set(state.savedPoints);
    state.dirty = false;
    drawMountMaskEditor();
  });
  $("#mountMaskApply").addEventListener("click", applyMountMask);
  drawMountMaskEditor();
}

const megaDriveColorLevels = [0, 36, 73, 109, 146, 182, 219, 255];

function cloneDesignPixels(pixels) {
  return pixels.map(pixel => [...pixel]);
}

function snapMegaDriveChannel(value) {
  if (!Number.isFinite(value)) return null;
  return megaDriveColorLevels.reduce((best, level) =>
    Math.abs(level - value) < Math.abs(best - value) ? level : best
  );
}

function hexDesignColor(pixel) {
  const channels = pixel?.slice?.(0, 3);
  if (
    !channels ||
    channels.length !== 3 ||
    channels.some(value => !Number.isFinite(value))
  ) {
    return "#49246d";
  }
  return `#${channels
    .map(value => Math.max(0, Math.min(255, Math.round(value)))
      .toString(16).padStart(2, "0"))
    .join("")}`;
}

function designColorFromHex(value) {
  const match = /^#([0-9a-f]{6})$/i.exec(
    String(value || "").trim()
  );
  if (!match) return null;
  const hex = match[1];
  const channels = [
    parseInt(hex.slice(0, 2), 16),
    parseInt(hex.slice(2, 4), 16),
    parseInt(hex.slice(4, 6), 16),
  ].map(snapMegaDriveChannel);
  if (channels.some(channel => channel === null)) return null;
  return [
    ...channels,
    255,
  ];
}

function designPixelKey(pixel) {
  return pixel.join(",");
}

function designVisibleColors(pixels) {
  const counts = new Map();
  for (const pixel of pixels) {
    if (!pixel[3]) continue;
    const key = designPixelKey(pixel);
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([key]) => key.split(",").map(Number));
}

function setAiDesignTool(tool) {
  const state = aiDesignEditorState;
  if (!state) return;
  state.tool = tool;
  document.querySelectorAll("[data-ai-design-tool]").forEach(button => {
    button.classList.toggle(
      "active",
      button.dataset.aiDesignTool === tool,
    );
  });
}

function drawAiDesignEditor() {
  const state = aiDesignEditorState;
  if (!state?.pixels) return;
  const context = state.canvas.getContext("2d");
  const cellSize = state.canvas.width / 16;
  context.clearRect(0, 0, state.canvas.width, state.canvas.height);
  for (let y = 0; y < 16; y += 1) {
    for (let x = 0; x < 16; x += 1) {
      const pixel = state.pixels[y * 16 + x];
      if (!pixel[3]) continue;
      context.fillStyle =
        `rgb(${pixel[0]} ${pixel[1]} ${pixel[2]})`;
      context.fillRect(
        x * cellSize,
        y * cellSize,
        cellSize,
        cellSize,
      );
    }
  }
  context.beginPath();
  context.strokeStyle = "rgba(255, 255, 255, 0.18)";
  context.lineWidth = 1;
  for (let index = 0; index <= 16; index += 1) {
    const position = index * cellSize + (index < 16 ? 0.5 : -0.5);
    context.moveTo(position, 0);
    context.lineTo(position, state.canvas.height);
    context.moveTo(0, position);
    context.lineTo(state.canvas.width, position);
  }
  context.stroke();
  context.strokeStyle = "rgba(225, 83, 255, 0.62)";
  context.lineWidth = 2;
  for (const key of state.lockPoints) {
    const [x, y] = key.split(",").map(Number);
    context.strokeRect(
      x * cellSize + 1,
      y * cellSize + 1,
      cellSize - 2,
      cellSize - 2,
    );
  }

  const colors = designVisibleColors(state.pixels);
  const palette = $("#aiDesignPalette");
  if (palette) {
    palette.innerHTML = colors.map(pixel => `
      <button type="button" class="aiDesignSwatch${
        designPixelKey(pixel) === designPixelKey(state.selectedColor)
          ? " selected"
          : ""
      }" data-design-color="${hexDesignColor(pixel)}"
        style="--swatch:${hexDesignColor(pixel)}"
        title="${hexDesignColor(pixel)}"></button>
    `).join("");
    palette.querySelectorAll("[data-design-color]").forEach(button => {
      button.addEventListener("click", () => {
        const selectedColor = designColorFromHex(
          button.dataset.designColor
        );
        if (!selectedColor) return;
        state.selectedColor = selectedColor;
        $("#aiDesignColor").value = hexDesignColor(
          state.selectedColor
        );
        setAiDesignTool("pencil");
        drawAiDesignEditor();
      });
    });
  }
  const count = $("#aiDesignColorCount");
  if (count) {
    count.textContent =
      `가시색 ${colors.length}/15 · 자주색 테두리는 얼굴 마스크 잠금`;
    count.classList.toggle("overLimit", colors.length > 15);
  }
  $("#aiDesignUndo").disabled = state.undo.length === 0;
  $("#aiDesignRedo").disabled = state.redo.length === 0;
}

function pushAiDesignHistory() {
  const state = aiDesignEditorState;
  state.undo.push(cloneDesignPixels(state.pixels));
  if (state.undo.length > 60) state.undo.shift();
  state.redo = [];
}

function floodAiDesign(startIndex, replacement) {
  const state = aiDesignEditorState;
  const targetKey = designPixelKey(state.pixels[startIndex]);
  if (targetKey === designPixelKey(replacement)) return;
  const pending = [startIndex];
  const visited = new Set();
  while (pending.length) {
    const index = pending.pop();
    if (visited.has(index)) continue;
    visited.add(index);
    const x = index % 16;
    const y = Math.floor(index / 16);
    if (state.lockPoints.has(`${x},${y}`)) continue;
    if (designPixelKey(state.pixels[index]) !== targetKey) continue;
    state.pixels[index] = [...replacement];
    if (x) pending.push(index - 1);
    if (x < 15) pending.push(index + 1);
    if (y) pending.push(index - 16);
    if (y < 15) pending.push(index + 16);
  }
}

function applyAiDesignPixel(x, y, beginStroke = false) {
  const state = aiDesignEditorState;
  const index = y * 16 + x;
  if (state.tool === "eyedropper") {
    const color = state.pixels[index];
    if (color[3]) {
      state.selectedColor = [...color];
      $("#aiDesignColor").value = hexDesignColor(color);
      setAiDesignTool("pencil");
      drawAiDesignEditor();
    }
    return;
  }
  if (state.lockPoints.has(`${x},${y}`)) return;
  if (beginStroke) pushAiDesignHistory();
  if (state.tool === "fill") {
    floodAiDesign(index, state.selectedColor);
  } else {
    state.pixels[index] = state.tool === "eraser"
      ? [0, 0, 0, 0]
      : [...state.selectedColor];
  }
  state.dirty = true;
  drawAiDesignEditor();
}

async function saveAiDesign(reset = false) {
  const state = aiDesignEditorState;
  if (!state || state.saving) return;
  state.saving = true;
  const buttons = [
    $("#aiDesignSave"),
    $("#aiDesignDeleteOverride"),
  ].filter(Boolean);
  buttons.forEach(button => button.disabled = true);
  try {
    const response = await fetch("/api/ai-class-design", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        commander_id: state.commanderId,
        class_id: state.classId,
        pixels: reset ? undefined : state.pixels,
        reset,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    const row = aiClassRow(state.commanderId, state.classId);
    row.design_override = data.design_override;
    row.design_revision = data.design_revision;
    row.changed_pixel_count = data.changed_pixel_count;
    row.pixel_palette = data.pixel_palette;
    row.identity_mask_pending_rebuild = false;
    aiSpriteReloadToken = Date.now();
    renderAiClassRoutes();
    showNotice(
      `${activeAiCommander().name} ${classInfo(state.classId).ko} · ` +
      `${data.visible_color_count}/15색 디자인 ${
        reset ? "자동 변환본 복원" : "저장 완료"
      }`,
      true,
    );
  } catch (error) {
    showNotice(error.message);
    state.saving = false;
    buttons.forEach(button => button.disabled = false);
  }
}

function setupAiDesignEditor(commander, classId, row) {
  const canvas = $("#aiDesignCanvas");
  if (!canvas || !row.redesigned) {
    aiDesignEditorState = null;
    return;
  }
  const state = {
    commanderId: commander.commander_id,
    classId,
    canvas,
    pixels: null,
    savedPixels: null,
    selectedColor: [73, 36, 109, 255],
    tool: "pencil",
    lockPoints: new Set(
      (row.identity_lock_points || []).map(
        point => `${point[0]},${point[1]}`
      )
    ),
    undo: [],
    redo: [],
    dirty: false,
    saving: false,
    dragging: false,
    lastCell: null,
    referenceObjectUrl: null,
  };
  aiDesignEditorState = state;

  const image = new Image();
  image.addEventListener("load", () => {
    if (aiDesignEditorState !== state) return;
    const buffer = document.createElement("canvas");
    buffer.width = 16;
    buffer.height = 16;
    const context = buffer.getContext("2d");
    context.imageSmoothingEnabled = false;
    context.clearRect(0, 0, 16, 16);
    context.drawImage(image, 0, 0, 16, 16);
    const data = context.getImageData(0, 0, 16, 16).data;
    state.pixels = Array.from({length: 256}, (_, index) => [
      data[index * 4],
      data[index * 4 + 1],
      data[index * 4 + 2],
      data[index * 4 + 3],
    ]);
    state.savedPixels = cloneDesignPixels(state.pixels);
    const colors = designVisibleColors(state.pixels);
    if (colors.length) state.selectedColor = [...colors[0]];
    $("#aiDesignColor").value = hexDesignColor(state.selectedColor);
    drawAiDesignEditor();
  });
  image.src = aiClassSpritePath(commander.commander_id, classId);

  canvas.addEventListener("pointerdown", event => {
    const [x, y] = identityMaskCell(event, canvas);
    state.dragging = true;
    state.lastCell = `${x},${y}`;
    canvas.setPointerCapture(event.pointerId);
    applyAiDesignPixel(x, y, true);
    event.preventDefault();
  });
  canvas.addEventListener("pointermove", event => {
    if (!state.dragging || ["fill", "eyedropper"].includes(state.tool)) {
      return;
    }
    const [x, y] = identityMaskCell(event, canvas);
    const key = `${x},${y}`;
    if (key !== state.lastCell) {
      state.lastCell = key;
      applyAiDesignPixel(x, y);
    }
  });
  const finish = () => {
    state.dragging = false;
    state.lastCell = null;
  };
  canvas.addEventListener("pointerup", finish);
  canvas.addEventListener("pointercancel", finish);

  document.querySelectorAll("[data-ai-design-tool]").forEach(button => {
    button.addEventListener("click", () =>
      setAiDesignTool(button.dataset.aiDesignTool)
    );
  });
  const applyColorInput = (event, canonicalize = false) => {
    const selectedColor = designColorFromHex(event.target.value);
    // Some native Linux color pickers emit a transient empty/non-hex value
    // while "pick a screen color" is active. Ignore that intermediate event
    // instead of allowing NaN into the RGB controls.
    if (!selectedColor) return;
    state.selectedColor = selectedColor;
    if (canonicalize) {
      event.target.value = hexDesignColor(state.selectedColor);
    }
    setAiDesignTool("pencil");
    drawAiDesignEditor();
  };
  $("#aiDesignColor").addEventListener(
    "input",
    event => applyColorInput(event, false),
  );
  $("#aiDesignColor").addEventListener(
    "change",
    event => applyColorInput(event, true),
  );
  $("#aiDesignUndo").addEventListener("click", () => {
    if (!state.undo.length) return;
    state.redo.push(cloneDesignPixels(state.pixels));
    state.pixels = state.undo.pop();
    state.dirty = true;
    drawAiDesignEditor();
  });
  $("#aiDesignRedo").addEventListener("click", () => {
    if (!state.redo.length) return;
    state.undo.push(cloneDesignPixels(state.pixels));
    state.pixels = state.redo.pop();
    state.dirty = true;
    drawAiDesignEditor();
  });
  $("#aiDesignReload").addEventListener("click", () => {
    pushAiDesignHistory();
    state.pixels = cloneDesignPixels(state.savedPixels);
    state.dirty = false;
    drawAiDesignEditor();
  });
  $("#aiDesignSave").addEventListener("click", () => saveAiDesign(false));
  $("#aiDesignDeleteOverride").addEventListener(
    "click",
    () => saveAiDesign(true),
  );

  const reference = $("#aiDesignReferenceImage");
  const referenceZoom = $("#aiDesignReferenceZoom");
  const defaultReference = reference.src;
  $("#aiDesignReferenceFile").addEventListener("change", event => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      showNotice("PNG, JPG, WEBP 같은 이미지 파일을 선택해주세요");
      return;
    }
    if (state.referenceObjectUrl) {
      URL.revokeObjectURL(state.referenceObjectUrl);
    }
    state.referenceObjectUrl = URL.createObjectURL(file);
    reference.src = state.referenceObjectUrl;
    $("#aiDesignReferenceName").textContent = file.name;
  });
  $("#aiDesignReferenceReset").addEventListener("click", () => {
    if (state.referenceObjectUrl) {
      URL.revokeObjectURL(state.referenceObjectUrl);
      state.referenceObjectUrl = null;
    }
    reference.src = defaultReference;
    $("#aiDesignReferenceFile").value = "";
    $("#aiDesignReferenceName").textContent = "현재 클래스 AI 원화";
  });
  const applyReferenceZoom = () => {
    reference.style.width = `${referenceZoom.value}%`;
  };
  referenceZoom.addEventListener("input", () => {
    applyReferenceZoom();
  });
  applyReferenceZoom();
  setAiDesignTool("pencil");
}

function renderAiClassInspector() {
  const commander = activeAiCommander();
  const classId = selectedAiClassId;
  if (classId === null) {
    aiClassInspector.innerHTML = "<h2>클래스를 선택하세요</h2>";
    return;
  }
  const info = classInfo(classId);
  const row = aiClassRow(commander.commander_id, classId);
  const displayClassName = row.class_name || info.ko;
  const pending = Boolean(row.pending_redesign);
  const identityLockedAi16 = Boolean(
    row.redesigned && row.identity_lock_box
  );
  const directStageAi = Boolean(
    row.redesigned && row.ai_source_kind.includes("direct_16x16")
  );
  const characterSheetAi = Boolean(
    row.redesigned && (
      row.ai_source_kind.includes("character-ai-v3") ||
      row.ai_source_kind.includes("logical16-v3")
    )
  );
  const eyeLockCount = Number(row.eye_lock_pixel_count || 0);
  const maskLockCount = Number(row.identity_lock_pixel_count || 0);
  const generatedIdentity = row.identity_lock_mode === "generated";
  const maskMode = generatedIdentity
    ? "AI 생성 정체성"
    : row.identity_lock_mode === "custom"
    ? "사용자 마스크"
    : "자동 마스크";
  const maskPending = Boolean(row.identity_mask_pending_rebuild);
  const aiOriginalFile = (
    row.ai_source_original_file || row.ai_source_cell_file
  );
  const aiReferencePath = aiOriginalFile
    ? `/ai-class-sprites/${aiOriginalFile}?v=${encodeURIComponent(
        aiClassSpriteModel.asset_version
      )}`
    : commanderSpritePath(commander.commander_id, classId);
  const headPreservation = pending
    ? "실패 시안 제거·현재 ROM 원본 전체 256픽셀"
    : row.redesigned
    ? generatedIdentity
      ? "AI 생성 단계에서 헤인 얼굴·눈·머리 형태 유지·원본 얼굴 덮어쓰기 없음"
      : directStageAi
      ? "ROM 얼굴·머리·눈 사각형 잠금·선택된 5단계 보병 실루엣 유지"
      : characterSheetAi
      ? "ROM 얼굴·머리 사용자 마스크 잠금·캐릭터별 AI 클래스 실루엣 유지"
      : row.identity_lock_box ||
      row.ai_source_kind.includes("네이티브 16×16") ||
      row.ai_source_kind.includes("마스크 인페인트")
      ? "ROM 얼굴·머리·윤곽·투명 실루엣을 픽셀 단위로 편집 잠금"
      : `원작 레퍼런스 얼굴·머리 연결 유지·ROM 눈/흰자 ${eyeLockCount}픽셀 잠금`
    : "원본 전체 256픽셀";
  aiClassInspector.innerHTML = `
    <div class="inspectorTitle">
      <span class="inspectorSprite">
        ${aiSpriteImage(commander.commander_id, classId)}
      </span>
      <div><h2>${escapeHtml(displayClassName)}</h2>
        <p>${hexId(classId)} · ${escapeHtml(info.jp)} · ${row.tier}단계</p>
      </div>
    </div>
    <div class="aiSpriteComparison">
      <div>
        <span>${pending
          ? "전용 생성 대기"
          : row.redesigned
          ? row.ai_source_original_file
            ? "AI 디자인 원본"
            : identityLockedAi16
            ? characterSheetAi
              ? "캐릭터별 전용 AI 원화"
              : "AI 장비 참고 원화"
            : "AI 원화"
          : "AI 원화 · 미사용"}</span>
        <span class="aiSourceSprite">
          ${row.redesigned && aiOriginalFile
            ? `<img src="/ai-class-sprites/${aiOriginalFile}?v=${encodeURIComponent(
                aiClassSpriteModel.asset_version
              )}"
                alt="${escapeHtml(commander.name)} ${escapeHtml(displayClassName)} AI 원화">`
            : spriteImage(classId, {commanderId: commander.commander_id})}
        </span>
      </div>
      <div>
        <span>${pending
          ? "현재 안전 복구본"
          : row.redesigned
          ? identityLockedAi16
            ? directStageAi
              ? "최종 16×16 (5단계 디자인·원본 얼굴)"
              : characterSheetAi
              ? "최종 16×16 (전용 AI·원본 머리)"
              : "최종 16×16 (원본 머리 잠금)"
            : "16×16 변환"
          : "ROM 원본 유지"}</span>
        <span class="comparisonSprite ${row.redesigned ? "changed" : ""}">
          ${aiSpriteImage(commander.commander_id, classId)}
        </span>
      </div>
      <div>
        <span>ROM 원본 비교</span>
        <span class="comparisonSprite">
          ${spriteImage(classId, {commanderId: commander.commander_id})}
        </span>
      </div>
    </div>
    <dl class="designMetadata">
      <div><dt>생성 방식</dt><dd>${escapeHtml(row.feature)}</dd></div>
      <div><dt>디자인 버전</dt><dd>${escapeHtml(
        aiClassSpriteModel.asset_version
      )}</dd></div>
      <div><dt>AI 원화</dt><dd>${escapeHtml(row.ai_source_kind)} · ${escapeHtml(
        row.ai_source_position
      )}</dd></div>
      <div><dt>대표 색상</dt><dd>
        <span class="paletteRow"><b>원화</b>${colorSwatches(row.source_palette)}</span>
        <span class="paletteRow"><b>16×16</b>${colorSwatches(row.pixel_palette)}</span>
      </dd></div>
      <div><dt>원본 고정</dt><dd>${headPreservation} · 그림 0x${hexId(
        row.face_source_sprite_id
      )}</dd></div>
      ${row.redesigned && !generatedIdentity
        ? `<div><dt>얼굴 마스크</dt><dd>${maskMode} · 원본 고정 ${
            maskLockCount
          }픽셀${maskPending ? " · 저장됨, 다음 AI 변환 때 적용" : ""}</dd></div>`
        : ""}
      <div><dt>눈 고정</dt><dd>${
        generatedIdentity
          ? "확대 원본 레퍼런스를 따라 AI 원화 자체에서 헤인의 눈을 유지"
          : row.redesigned
          ? `ROM 원본의 눈·흰자 ${eyeLockCount}픽셀 그대로 유지`
          : "ROM 원본 전체 유지에 포함"
      }</dd></div>
      ${row.redesigned
        ? `<div><dt>장비 변경</dt><dd>${row.changed_pixel_count}픽셀 · ${
            identityLockedAi16
              ? directStageAi
                ? "얼굴·머리·눈 제외"
                : characterSheetAi
                ? "사용자 얼굴·머리 마스크 제외"
                : "얼굴·머리·외곽선·눈 제외"
              : "원본 눈·흰자 제외"
          }</dd></div>`
        : ""}
      <div><dt>ROM 반영</dt><dd>미적용 · 비교용 PNG만 생성</dd></div>
    </dl>
    ${row.redesigned
      ? `<section class="aiDesignEditor">
          <h3>16×16 캐릭터 디자인 편집</h3>
          <p>${generatedIdentity
            ? "AI 디자인 원본을 보면서 최종 도트를 직접 수정합니다. 이 디자인은 얼굴을 덮어쓰지 않고 생성된 헤인 얼굴·머리를 그대로 사용합니다."
            : "AI 원화를 보면서 최종 도트를 직접 수정합니다. 자주색 테두리의 얼굴 마스크 픽셀은 원작 정체성을 위해 잠겨 있습니다."}</p>
          <div class="aiDesignWorkspace">
            <div class="aiDesignPixelPane">
              <canvas id="aiDesignCanvas" width="320" height="320"
                aria-label="${escapeHtml(displayClassName)} 16×16 디자인 편집"></canvas>
              <div class="aiDesignTools">
                <button type="button" data-ai-design-tool="pencil">연필</button>
                <button type="button" data-ai-design-tool="eraser">지우개</button>
                <button type="button" data-ai-design-tool="fill">채우기</button>
                <button type="button" data-ai-design-tool="eyedropper">스포이드</button>
              </div>
              <div class="aiDesignColorControl">
                <label>선택색
                  <input id="aiDesignColor" type="color" value="#49246d">
                </label>
                <span id="aiDesignColorCount"></span>
              </div>
              <div id="aiDesignPalette" class="aiDesignPalette"
                aria-label="현재 디자인 팔레트"></div>
              <div class="aiDesignHistory">
                <button id="aiDesignUndo" type="button">실행 취소</button>
                <button id="aiDesignRedo" type="button">다시 실행</button>
                <button id="aiDesignReload" type="button">저장본 다시 읽기</button>
              </div>
            </div>
            <div class="aiDesignReferencePane">
              <div class="aiDesignReferenceHeader">
                <strong>참고할 AI 그림</strong>
                <span id="aiDesignReferenceName">현재 클래스 AI 디자인 원본</span>
              </div>
              <div class="aiDesignReferenceViewport">
                <img id="aiDesignReferenceImage"
                  src="${aiReferencePath}"
                  alt="${escapeHtml(info.ko)} AI 디자인 참고 이미지">
              </div>
              <label class="aiDesignFileLabel">
                다른 AI 그림 불러오기
                <input id="aiDesignReferenceFile" type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif">
              </label>
              <label class="aiDesignZoomLabel">참고 그림 배율 (25%~200%)
                <input id="aiDesignReferenceZoom" type="range"
                  min="25" max="200" step="25" value="50">
              </label>
              <button id="aiDesignReferenceReset" type="button">
                현재 AI 원화로 돌아가기
              </button>
              <p>불러온 이미지는 참고용으로 브라우저에서만 열리며
                프로젝트 파일을 덮어쓰지 않습니다.</p>
            </div>
          </div>
          <div class="aiDesignSaveActions">
            <button id="aiDesignDeleteOverride" type="button"
              ${row.design_override ? "" : "disabled"}>
              수동 편집 삭제
            </button>
            <button id="aiDesignSave" class="primary" type="button">
              이 디자인 저장
            </button>
          </div>
          <p class="aiDesignNote">저장하면 선택한 클래스 PNG만 즉시
            갱신합니다. 전체 170개를 다시 만들지 않으며, 수동 편집은
            이후 AI 자산 재빌드 때도 유지됩니다.</p>
        </section>`
      : ""}
    ${row.redesigned && !generatedIdentity
      ? `<section class="identityMaskEditor">
          <h3>16×16 얼굴 마스크 편집</h3>
          <p>자주색 칸은 최종 이미지에서 ROM 원본 픽셀을 그대로
            고정합니다. 클릭은 한 칸 전환, 드래그는 같은 상태로
            연속 칠하기입니다.</p>
          <canvas id="identityMaskCanvas" width="320" height="320"
            aria-label="${escapeHtml(info.ko)} 원본 픽셀 고정 마스크"></canvas>
          <span id="identityMaskCount" class="identityMaskCount"></span>
          <div class="identityMaskActions">
            <button id="identityMaskClear" type="button">전체 해제</button>
            <button id="identityMaskReset" type="button">자동값 불러오기</button>
            <button id="identityMaskApply" class="primary" type="button">
              마스크 저장
            </button>
          </div>
          <p class="identityMaskNote">좌표만 즉시 저장합니다. 저장된
            마스크는 다음 AI 이미지의 16×16 변환 때 적용되며, 저장
            시점에는 PNG 170개나 실제 ROM을 다시 만들지 않습니다.</p>
        </section>`
      : ""}
    ${row.redesigned && !generatedIdentity
      ? `<section class="identityMaskEditor mountMaskEditor">
          <h3>16×16 탈것 마스크 편집</h3>
          <p>청록색 칸은 말·드래곤 등 탈것 부분을 ROM 원본 픽셀로
            복원합니다. 얼굴 마스크와 독립되어 있으므로 탈것에
            해당하는 칸만 직접 칠하면 됩니다.</p>
          <canvas id="mountMaskCanvas" width="320" height="320"
            aria-label="${escapeHtml(info.ko)} 원본 탈것 픽셀 고정 마스크"></canvas>
          <span id="mountMaskCount" class="identityMaskCount"></span>
          <div class="identityMaskActions">
            <button id="mountMaskClear" type="button">전체 해제</button>
            <button id="mountMaskReload" type="button">저장값 불러오기</button>
            <button id="mountMaskApply" class="primary" type="button">
              탈것 마스크 저장
            </button>
          </div>
          <p class="identityMaskNote">저장할 때는 이 클래스의 좌표만
            기록하며 전체 PNG를 검증하거나 다시 만들지 않습니다.
            다음 AI 변환·자산 재빌드 때 선택한 탈것 픽셀이 적용됩니다.</p>
        </section>`
      : ""}`;
  installSpriteFallbacks(aiClassInspector);
  setupAiDesignEditor(commander, classId, row);
  setupIdentityMaskEditor(commander, classId, row);
  setupMountMaskEditor(commander, classId, row);
}

function renderAiClassRoutes() {
  if (!aiClassSpriteModel) return;
  const commander = activeAiCommander();
  const graph = buildClassGraph(commander);
  if (selectedAiClassId === null ||
      !graph.levels.some(level => level.includes(selectedAiClassId))) {
    selectedAiClassId = graph.levels[0][0];
  }
  const nextClassIds = nextClassIdsFor(
    commander,
    selectedAiClassId,
  );
  aiClassTree.innerHTML = `
    <svg id="aiClassEdges" class="classEdges" aria-hidden="true"></svg>
    ${graph.levels.map((level, levelIndex) => `
      <div class="classTier" data-tier="${levelIndex + 1}">
        ${level.map(classId =>
          aiClassNode(classId, levelIndex, commander, nextClassIds)
        ).join("")}
      </div>`).join("")}`;
  aiClassTree.querySelectorAll("[data-ai-tree-class]").forEach(node => {
    node.addEventListener("click", () => {
      selectedAiClassId = Number(node.dataset.aiTreeClass);
      renderAiClassRoutes();
    });
  });
  installSpriteFallbacks(aiClassTree);
  const rows = Object.values(
    aiClassSpriteModel.commanders[String(commander.commander_id)].classes
  );
  const redesignedCount = rows.filter(row => row.redesigned).length;
  aiClassSummary.textContent =
    `${commander.name} · 편집 가능 디자인 ${redesignedCount}개 · 히든 ${
      (commander.hidden_class_routes || []).length
    }개 · 실제 ROM 미적용`;
  renderAiClassInspector();
  requestAnimationFrame(() => drawClassEdges(
    graph.edges,
    aiClassTree,
    "#aiClassEdges",
    selectedAiClassId,
  ));
}

function sampleClassCard(group, sample) {
  const aiSourcePath = sampleClassAssetPath(
    sample.ai_source || sample.ai_thumbnail
  );
  const spritePath = sampleClassAssetPath(sample.logical16);
  const previewPath = sample.preview
    ? sampleClassAssetPath(sample.preview)
    : spritePath;
  const detail = `${sample.label} · ${sample.description}`;
  const preservedClass = sample.preserved ? " preserved" : "";
  return `
    <article class="sampleClassCard${preservedClass}" title="${escapeHtml(detail)}">
      <button type="button" class="sampleLoadButton sampleCompactChoice"
        data-sample-group="${escapeHtml(group.id)}"
        data-sample-id="${escapeHtml(sample.id)}">
        <span class="sampleClassNumber">${escapeHtml(sample.id)}</span>
        ${sample.preserved
          ? '<span class="samplePreservedBadge" aria-label="사용자 확정 보존안">고정</span>'
          : ""}
        <img src="${previewPath}" loading="lazy"
          data-logical16="${spritePath}"
          alt="${escapeHtml(group.title)} ${escapeHtml(sample.label)} 16×16 디자인">
        <strong>${escapeHtml(sample.label)}</strong>
      </button>
      <a class="sampleAiLink" href="${aiSourcePath}" target="_blank"
        rel="noopener" aria-label="${escapeHtml(group.title)} ${escapeHtml(sample.label)} AI 원안 보기">
        AI 원안
      </a>
    </article>`;
}

function renderSampleClasses() {
  if (!sampleClassGroups || !sampleClassSummary) return;
  const groups = sampleClassSpriteModel?.groups || [];
  if (!groups.length) {
    sampleClassGroups.innerHTML = `
      <p class="sampleClassEmpty">아직 표시할 샘플이 없습니다.</p>`;
    sampleClassSummary.textContent = "0개";
    return;
  }
  sampleClassGroups.innerHTML = groups.map(group => `
    <section class="sampleClassGroup">
      <header class="sampleClassGroupHeader">
        <div>
          <h2>${escapeHtml(group.title)}</h2>
          <p>${escapeHtml(group.description)}</p>
        </div>
        <span>${group.samples.length}안</span>
      </header>
      <div class="sampleClassGrid" aria-label="${escapeHtml(group.title)} 디자인 후보">
        ${group.samples.map(sample => sampleClassCard(group, sample)).join("")}
      </div>
    </section>
  `).join("");
  const sampleCount = groups.reduce(
    (total, group) => total + group.samples.length,
    0,
  );
  sampleClassSummary.textContent =
    `${groups.length}개 클래스 · 총 ${sampleCount}개 디자인`;
}

function imagePixels16(image) {
  const buffer = document.createElement("canvas");
  buffer.width = 16;
  buffer.height = 16;
  const context = buffer.getContext("2d");
  context.imageSmoothingEnabled = false;
  context.clearRect(0, 0, 16, 16);
  context.drawImage(image, 0, 0, 16, 16);
  const data = context.getImageData(0, 0, 16, 16).data;
  return Array.from({length: 256}, (_, index) => [
    data[index * 4],
    data[index * 4 + 1],
    data[index * 4 + 2],
    data[index * 4 + 3],
  ]);
}

function loadSampleImage(path) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.addEventListener("load", () => resolve(image), {once: true});
    image.addEventListener(
      "error",
      () => reject(new Error("샘플 16×16 이미지를 읽지 못했습니다")),
      {once: true},
    );
    image.src = sampleClassAssetPath(path);
  });
}

async function waitForAiDesignEditor(commanderId, classId) {
  for (let attempt = 0; attempt < 240; attempt += 1) {
    const state = aiDesignEditorState;
    if (
      state?.commanderId === commanderId &&
      state.classId === classId &&
      state.pixels &&
      state.savedPixels
    ) {
      return state;
    }
    await new Promise(resolve => requestAnimationFrame(resolve));
  }
  throw new Error("New 클래스 편집기를 준비하지 못했습니다");
}

async function loadClassSample(group, sample) {
  const commanderId = Number(group.commander_id);
  const classId = Number(group.class_id);
  aiCommanderSelect.value = String(commanderId);
  selectedAiClassId = classId;
  document.querySelectorAll(".tab").forEach(tab => {
    tab.classList.toggle("active", tab.dataset.tab === "aiClasses");
  });
  document.querySelectorAll(".tabPanel").forEach(panel => {
    panel.classList.toggle("active", panel.id === "aiClassesPanel");
  });
  renderAiClassRoutes();
  const [state, image] = await Promise.all([
    waitForAiDesignEditor(commanderId, classId),
    loadSampleImage(sample.logical16),
  ]);
  if (aiDesignEditorState !== state) {
    throw new Error("편집 클래스가 바뀌어 샘플 불러오기를 취소했습니다");
  }
  pushAiDesignHistory();
  const imported = imagePixels16(image);
  const [identityDx, identityDy] = group.identity_translation || [0, 0];
  if (identityDx || identityDy) {
    const targetPoints = new Set(state.lockPoints);
    const sourcePoints = new Set();
    for (const key of targetPoints) {
      const [x, y] = key.split(",").map(Number);
      const sourceX = x - identityDx;
      const sourceY = y - identityDy;
      if (sourceX >= 0 && sourceX < 16 && sourceY >= 0 && sourceY < 16) {
        sourcePoints.add(`${sourceX},${sourceY}`);
      }
    }
    for (const key of sourcePoints) {
      if (targetPoints.has(key)) continue;
      const [x, y] = key.split(",").map(Number);
      imported[y * 16 + x] = [0, 0, 0, 0];
    }
  }
  for (const key of state.lockPoints) {
    const [x, y] = key.split(",").map(Number);
    const index = y * 16 + x;
    imported[index] = [...state.savedPixels[index]];
  }
  for (const point of group.identity_seam_points || []) {
    const [x, y] = point.map(Number);
    const index = y * 16 + x;
    if (!imported[index][3]) imported[index] = [36, 36, 36, 255];
  }
  state.pixels = imported;
  state.dirty = true;
  const colors = designVisibleColors(state.pixels);
  if (colors.length) state.selectedColor = [...colors[0]];
  $("#aiDesignColor").value = hexDesignColor(state.selectedColor);
  const reference = $("#aiDesignReferenceImage");
  if (state.referenceObjectUrl) {
    URL.revokeObjectURL(state.referenceObjectUrl);
    state.referenceObjectUrl = null;
  }
  reference.src = sampleClassAssetPath(
    sample.ai_source || sample.ai_thumbnail
  );
  $("#aiDesignReferenceName").textContent =
    `${group.title} · ${sample.label}`;
  drawAiDesignEditor();
  aiClassInspector.scrollIntoView({behavior: "smooth", block: "start"});
  showNotice(
    `${group.title} ${sample.id}안 불러오기 완료 · 저장 전까지 기존 디자인은 바뀌지 않습니다`,
    true,
  );
}

function collectClassEdits() {
  // Class tree and hire controls update classModel immediately.
}

function changeTransitionCurrentClass(commander, transition, classId) {
  const oldClassId = transition.current_class;
  const duplicate = commander.transitions.find(
    entry => entry !== transition && entry.current_class === classId
  );
  if (commander.starting_class_id === oldClassId && duplicate) {
    // Starting at an existing class should use that class's real next-stage
    // record. Replacing both labels would preserve uniqueness but can create
    // a self-loop when the chosen class was one of the old tier-two options.
    commander.starting_class_id = classId;
    selectedTreeClassId = classId;
    return;
  }
  if (duplicate) duplicate.current_class = oldClassId;
  transition.current_class = classId;
  if (commander.starting_class_id === oldClassId) {
    commander.starting_class_id = classId;
  }
  selectedTreeClassId = classId;
}

function renderPickerOptions() {
  if (!pickerState) return;
  const query = assetPickerSearch.value.trim().toLowerCase();
  const allowed = pickerState.allowedIds;
  const rows = (pickerState.allowEmpty
    ? [{id: 255, ko: "없음", jp: ""}]
    : [])
    .concat(classModel.classes.filter(row => allowed.includes(row.id)))
    .filter(row => {
      if (!query) return true;
      return `${hexId(row.id)} ${row.ko} ${row.jp}`
        .toLowerCase().includes(query);
    });
  assetPickerOptions.innerHTML = rows.map(row => `
    <button type="button" class="pickerOption" data-picker-value="${row.id}">
      ${spriteImage(row.id, {
        palette: pickerState.palette,
        commanderId: pickerState.commanderId,
        representative: pickerState.representative,
      })}
      <strong>${row.id === 255 ? "" : hexId(row.id)}</strong>
      <span>${escapeHtml(row.ko)}</span>
      <small>${escapeHtml(row.jp)}</small>
    </button>`).join("");
  installSpriteFallbacks(assetPickerOptions);
}

function pickerViewport() {
  const viewport = window.visualViewport;
  return {
    left: viewport?.offsetLeft || 0,
    top: viewport?.offsetTop || 0,
    width: viewport?.width || window.innerWidth,
    height: viewport?.height || window.innerHeight,
  };
}

function positionPicker(anchor) {
  if (!anchor?.isConnected || assetPicker.hidden) return;
  const viewport = pickerViewport();
  const height = Math.max(180, Math.min(520, viewport.height - 24));
  assetPicker.style.height = `${height}px`;
  const rect = anchor.getBoundingClientRect();
  const left = Math.min(
    viewport.left + viewport.width - assetPicker.offsetWidth - 12,
    Math.max(viewport.left + 12, rect.left)
  );
  const top = Math.min(
    viewport.top + viewport.height - height - 12,
    rect.bottom + 6
  );
  assetPicker.style.left = `${Math.max(viewport.left + 12, left)}px`;
  assetPicker.style.top = `${Math.max(viewport.top + 12, top)}px`;
}

function shouldAutoFocusPickerSearch() {
  // On phones, focusing immediately opens the virtual keyboard. That changes
  // the visual viewport before the initiating tap has settled and used to
  // close the picker through the global resize handler. Keep the keyboard
  // opt-in on coarse/touch pointers; desktop users retain keyboard search.
  if (!window.matchMedia?.("(hover: hover) and (pointer: fine)").matches) {
    return false;
  }
  const userAgent = (navigator?.userAgent || "").toLowerCase();
  const isTouchPhoneOrTablet = /iphone|ipad|ipod|android|mobile|blackberry|bb10|windows phone/.test(
    userAgent,
  );
  return !isTouchPhoneOrTablet;
}

function openPicker(anchor, options) {
  pickerState = {...options, anchor};
  assetPickerSearch.value = "";
  renderPickerOptions();
  assetPicker.hidden = false;
  positionPicker(anchor);
  if (shouldAutoFocusPickerSearch()) {
    requestAnimationFrame(() => {
      if (!assetPicker.hidden && pickerState?.anchor === anchor) {
        assetPickerSearch.focus({preventScroll: true});
      }
    });
  }
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
    const [
      itemsResponse,
      classesResponse,
      classProgressionResponse,
      testSpritesResponse,
      aiSpritesResponse,
      sampleSpritesResponse,
    ] = await Promise.all([
      fetch(`/api/items?rom=${rom}`),
      fetch(`/api/class-changes?rom=${rom}`),
      fetch(`/api/class-progression?rom=${rom}`),
      fetch("/test-class-sprites/manifest.json"),
      fetch(
        `/ai-class-sprites/manifest.json?reload=${Date.now()}`,
        {cache: "no-store"}
      ),
      fetch(
        `/sample-class-sprites/manifest.json?reload=${Date.now()}`,
        {cache: "no-store"}
      ),
    ]);
    itemModel = await itemsResponse.json();
    classModel = await classesResponse.json();
    classProgressionModel = await classProgressionResponse.json();
    testClassSpriteModel = await testSpritesResponse.json();
    aiClassSpriteModel = await aiSpritesResponse.json();
    sampleClassSpriteModel = await sampleSpritesResponse.json();
    if (!itemsResponse.ok) throw new Error(itemModel.error);
    if (!classesResponse.ok) throw new Error(classModel.error);
    if (!classProgressionResponse.ok) {
      throw new Error(classProgressionModel.error);
    }
    if (!testSpritesResponse.ok) {
      throw new Error("테스트 클래스 디자인을 읽지 못했습니다");
    }
    if (!aiSpritesResponse.ok) {
      throw new Error("AI 클래스 디자인을 읽지 못했습니다");
    }
    if (!sampleSpritesResponse.ok) {
      throw new Error("샘플 클래스 디자인을 읽지 못했습니다");
    }
    await loadScenario();
    sourcePath.textContent = itemModel.rom_path;
    renderItems();
    commanderSelect.innerHTML = classModel.commanders.map(commander =>
      `<option value="${commander.commander_id}">` +
      `${commander.commander_id}. ${escapeHtml(commander.name)}</option>`
    ).join("");
    testCommanderSelect.innerHTML = commanderSelect.innerHTML;
    aiCommanderSelect.innerHTML = commanderSelect.innerHTML;
    classStatsSelect.innerHTML = classProgressionModel.classes.map(row =>
      `<option value="${row.class_id}">${hexId(row.class_id)} ` +
      `${escapeHtml(row.name)}</option>`
    ).join("");
    renderClassRoutes();
    renderClassStatsEditor();
    renderTestClassRoutes();
    renderAiClassRoutes();
    renderSampleClasses();
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
        commander_starts: classModel.commanders.map(commander => ({
          commander_id: commander.commander_id,
          starting_class_id: commander.starting_class_id,
        })),
        class_hires: classModel.class_hires,
        class_progressions: classProgressionModel.classes,
        ability_requirements: classProgressionModel.abilities,
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
    } else if (tab.dataset.tab === "classStats") {
      requestAnimationFrame(renderClassStatsEditor);
    } else if (tab.dataset.tab === "testClasses") {
      requestAnimationFrame(renderTestClassRoutes);
    } else if (tab.dataset.tab === "aiClasses") {
      requestAnimationFrame(renderAiClassRoutes);
    } else if (tab.dataset.tab === "sampleClasses") {
      requestAnimationFrame(renderSampleClasses);
    }
  });
});

sampleClassGroups?.addEventListener("click", async event => {
  const button = event.target.closest("[data-sample-group][data-sample-id]");
  if (!button) return;
  const group = sampleClassSpriteModel?.groups?.find(
    entry => entry.id === button.dataset.sampleGroup
  );
  const sample = group?.samples?.find(
    entry => entry.id === button.dataset.sampleId
  );
  if (!group || !sample) {
    showNotice("선택한 샘플 정보를 찾지 못했습니다");
    return;
  }
  button.disabled = true;
  try {
    await loadClassSample(group, sample);
  } catch (error) {
    showNotice(error.message);
    button.disabled = false;
  }
});

recordsBody.addEventListener("click", event => {
  const classButton = event.target.closest("[data-scenario-class]");
  if (classButton) {
    const record = scenarioModel.records[Number(classButton.dataset.recordIndex)];
    const commanderId = record.name.id >= 1 && record.name.id <= 10
      ? record.name.id
      : null;
    openPicker(classButton, {
      allowedIds: classModel.classes.map(row => row.id),
      allowEmpty: false,
      palette: scenarioPalette(record),
      commanderId,
      onSelect: classId => {
        record.class_id = classId;
        closePicker();
        renderScenario();
      },
    });
    return;
  }
  const button = event.target.closest("[data-merc-picker]");
  if (!button) return;
  const record = scenarioModel.records[Number(button.dataset.recordIndex)];
  openPicker(button, {
      allowedIds: classModel.classes.map(row => row.id),
      allowEmpty: true,
      palette: scenarioPalette(record),
      representative: false,
    onSelect: classId => {
      record.mercenaries[Number(button.dataset.slot)] = classId;
      closePicker();
      renderScenario();
    },
  });
});

classInspector.addEventListener("click", event => {
  const commander = activeCommander();
  const transition = commander.transitions.find(
    entry => entry.current_class === selectedTreeClassId
  );
  const currentButton = event.target.closest("[data-current-class-picker]");
  if (currentButton && transition) {
    openPicker(currentButton, {
      allowedIds: classModel.classes.map(row => row.id),
      allowEmpty: false,
      palette: 1,
      commanderId: commander.commander_id,
      onSelect: classId => {
        changeTransitionCurrentClass(commander, transition, classId);
        closePicker();
        renderClassRoutes();
      },
    });
    return;
  }
  const nextButton = event.target.closest("[data-next-class-picker]");
  if (nextButton && transition) {
    openPicker(nextButton, {
      allowedIds: classModel.classes.map(row => row.id),
      allowEmpty: false,
      palette: 1,
      commanderId: commander.commander_id,
      onSelect: classId => {
        transition.candidates[Number(nextButton.dataset.slot)] = classId;
        closePicker();
        renderClassRoutes();
      },
    });
    return;
  }
  const button = event.target.closest("[data-hire-picker]");
  if (!button) return;
  openPicker(button, {
      allowedIds: classModel.hire_class_ids,
      allowEmpty: true,
      palette: 1,
      representative: false,
    onSelect: classId => {
      hireRowFor(selectedTreeClassId)
        .hire_class_ids[Number(button.dataset.slot)] = classId;
      closePicker();
      renderClassInspector();
    },
  });
});

commanderStartEditor.addEventListener("click", event => {
  const button = event.target.closest("[data-starting-class-picker]");
  if (!button) return;
  const commander = activeCommander();
  openPicker(button, {
    allowedIds: classModel.classes.map(row => row.id),
    allowEmpty: false,
    palette: 1,
    commanderId: commander.commander_id,
    onSelect: classId => {
      commander.starting_class_id = classId;
      selectedTreeClassId = classId;
      closePicker();
      renderClassRoutes();
    },
  });
});

classStatsEditor.addEventListener("input", event => {
  const row = activeClassProgression();
  if (!row) return;
  if (event.target.matches("[data-class-stat]")) {
    row[event.target.dataset.classStat] = Number(event.target.value);
  } else if (event.target.matches("[data-growth-stat]")) {
    row.growth[event.target.dataset.growthStat][
      Number(event.target.dataset.growthLevel)
    ] = Number(event.target.value);
  } else if (event.target.matches("[data-ability-level]")) {
    abilityDefinition(Number(event.target.dataset.abilityLevel)).required_level =
      Number(event.target.value);
  }
});

classStatsEditor.addEventListener("change", event => {
  if (!event.target.matches("[data-ability-slot]")) return;
  const row = activeClassProgression();
  row.ability_ids[Number(event.target.dataset.abilitySlot)] =
    Number(event.target.value);
  renderClassStatsEditor();
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
      !event.target.closest(
        "[data-class-picker], [data-current-class-picker], " +
          "[data-next-class-picker], [data-merc-picker], [data-hire-picker], " +
          "[data-starting-class-picker]"
      )) {
    closePicker();
  }
});
function repositionOpenPicker() {
  if (!assetPicker.hidden && pickerState?.anchor) {
    positionPicker(pickerState.anchor);
  }
}

window.addEventListener("resize", repositionOpenPicker);
window.visualViewport?.addEventListener("resize", repositionOpenPicker);
window.visualViewport?.addEventListener("scroll", repositionOpenPicker);
window.addEventListener("resize", () => {
  if (activeCommanderId !== null) renderClassRoutes();
  if (testClassSpriteModel) renderTestClassRoutes();
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
testCommanderSelect.addEventListener("change", () => {
  selectedTestClassId = null;
  renderTestClassRoutes();
});
aiCommanderSelect.addEventListener("change", () => {
  selectedAiClassId = null;
  renderAiClassRoutes();
});
classStatsSelect.addEventListener("change", renderClassStatsEditor);
buildButton.addEventListener("click", buildRom);
loadAll();
