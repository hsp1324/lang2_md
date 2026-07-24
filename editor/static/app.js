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
const testCommanderSelect = $("#testCommanderSelect");
const testClassSummary = $("#testClassSummary");
const testClassTree = $("#testClassTree");
const testClassInspector = $("#testClassInspector");
const aiCommanderSelect = $("#aiCommanderSelect");
const aiClassSummary = $("#aiClassSummary");
const aiClassTree = $("#aiClassTree");
const aiClassInspector = $("#aiClassInspector");
const assetPicker = $("#assetPicker");
const assetPickerSearch = $("#assetPickerSearch");
const assetPickerOptions = $("#assetPickerOptions");

let scenarioModel = null;
let itemModel = null;
let classModel = null;
let testClassSpriteModel = null;
let aiClassSpriteModel = null;
let scenarioModels = new Map();
let activeCommanderId = null;
let selectedTreeClassId = null;
let selectedTestClassId = null;
let selectedAiClassId = null;
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
  return `/class-sprites/generic/${hexId(classId)}-p${palette}.png`;
}

function representativeSpritePath(classId) {
  return `/class-sprites/representative/${hexId(classId)}-p1.png`;
}

function commanderSpritePath(commanderId, classId) {
  return `/class-sprites/commanders/${commanderId}/${hexId(classId)}-p1.png`;
}

function testClassSpritePath(commanderId, classId) {
  return `/test-class-sprites/${commanderId}/${hexId(classId)}.png`;
}

function aiClassSpritePath(commanderId, classId) {
  const version =
    aiClassSpriteModel?.asset_version || "coherent-full-16-fit-2";
  return `/ai-class-sprites/${commanderId}/${hexId(classId)}.png` +
    `?v=${encodeURIComponent(version)}`;
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
        <small>${hexId(classId)} · ${escapeHtml(info.jp)}</small>
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
        <div class="nextClassChoice">
          <span>선택 ${slot + 1}</span>
          ${classPickerButton(
            candidate,
            `data-next-class-picker data-slot="${slot}"`,
            {commanderId: commander.commander_id}
          )}
        </div>`).join("")
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
        <h3>현재 클래스</h3>
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
  const graph = buildClassGraph(commander);
  if (selectedTreeClassId === null ||
      !graph.levels.some(level => level.includes(selectedTreeClassId))) {
    selectedTreeClassId = graph.levels[0][0];
  }
  const selectedTransition = commander.transitions.find(
    entry => entry.current_class === selectedTreeClassId
  );
  const nextClassIds = selectedTransition?.candidates || [];
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
    `${commander.name} · 실제 성장 최대 5단계 · ROM 분기 레코드 10개`;
  renderClassInspector();
  requestAnimationFrame(() => drawClassEdges(graph.edges));
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
        <small>${hexId(classId)} · ${escapeHtml(info.jp)}</small>
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
  const selectedTransition = commander.transitions.find(
    entry => entry.current_class === selectedTestClassId
  );
  const nextClassIds = selectedTransition?.candidates || [];
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
    `${commander.name} · 새 디자인 ${redesignedCount}개 · 실제 ROM 미적용`;
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
  const selected = selectedAiClassId === classId ? " selected" : "";
  const nextCandidate = nextClassIds.includes(classId) ? " nextCandidate" : "";
  const generated = row.redesigned ? " aiGenerated" : "";
  const pending = row.pending_redesign ? " aiPending" : "";
  return `
    <button class="classNode${generated}${pending}${selected}${nextCandidate}" type="button"
      data-ai-tree-class="${classId}" data-node-id="${level}-${classId}">
      <span class="nodeSprite">
        ${aiSpriteImage(commander.commander_id, classId)}
      </span>
      <span><strong>${escapeHtml(info.ko)}</strong>
        <small>${hexId(classId)} · ${escapeHtml(info.jp)}</small>
      </span>
    </button>`;
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
  const pending = Boolean(row.pending_redesign);
  const nativeAi16 = Boolean(
    row.redesigned && row.ai_source_kind.includes("네이티브 16×16")
  );
  const headPreservation = pending
    ? "실패 시안 제거·현재 ROM 원본 전체 256픽셀"
    : row.redesigned
    ? row.ai_source_kind.includes("네이티브 16×16") ||
      row.ai_source_kind.includes("마스크 인페인트")
      ? "ROM 얼굴·머리·윤곽을 처음부터 편집 잠금"
      : "원작 레퍼런스 얼굴·머리와 몸 연결 유지"
    : "원본 전체 256픽셀";
  aiClassInspector.innerHTML = `
    <div class="inspectorTitle">
      <span class="inspectorSprite">
        ${aiSpriteImage(commander.commander_id, classId)}
      </span>
      <div><h2>${escapeHtml(info.ko)}</h2>
        <p>${hexId(classId)} · ${escapeHtml(info.jp)} · ${row.tier}단계</p>
      </div>
    </div>
    <div class="aiSpriteComparison">
      <div>
        <span>${pending
          ? "전용 생성 대기"
          : row.redesigned
          ? nativeAi16
            ? "AI 원출력 (16×16)"
            : "AI 원화"
          : "AI 원화 · 미사용"}</span>
        <span class="aiSourceSprite">
          ${row.redesigned && row.ai_source_cell_file
            ? `<img src="/ai-class-sprites/${row.ai_source_cell_file}"
                alt="${escapeHtml(commander.name)} ${escapeHtml(info.ko)} AI 원화">`
            : spriteImage(classId, {commanderId: commander.commander_id})}
        </span>
      </div>
      <div>
        <span>${pending
          ? "현재 안전 복구본"
          : row.redesigned
          ? nativeAi16
            ? "에디터 적용본 (변환 없음)"
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
      <div><dt>ROM 반영</dt><dd>미적용 · 비교용 PNG만 생성</dd></div>
    </dl>`;
  installSpriteFallbacks(aiClassInspector);
}

function renderAiClassRoutes() {
  if (!aiClassSpriteModel) return;
  const commander = activeAiCommander();
  const graph = buildClassGraph(commander);
  if (selectedAiClassId === null ||
      !graph.levels.some(level => level.includes(selectedAiClassId))) {
    selectedAiClassId = graph.levels[0][0];
  }
  const selectedTransition = commander.transitions.find(
    entry => entry.current_class === selectedAiClassId
  );
  const nextClassIds = selectedTransition?.candidates || [];
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
    `${commander.name} · 중복 상위 클래스 AI 시안 ${redesignedCount}개 · 실제 ROM 미적용`;
  renderAiClassInspector();
  requestAnimationFrame(() => drawClassEdges(
    graph.edges,
    aiClassTree,
    "#aiClassEdges",
    selectedAiClassId,
  ));
}

function collectClassEdits() {
  // Class tree and hire controls update classModel immediately.
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
    const [
      itemsResponse,
      classesResponse,
      testSpritesResponse,
      aiSpritesResponse,
    ] = await Promise.all([
      fetch(`/api/items?rom=${rom}`),
      fetch(`/api/class-changes?rom=${rom}`),
      fetch("/test-class-sprites/manifest.json"),
      fetch("/ai-class-sprites/manifest.json"),
    ]);
    itemModel = await itemsResponse.json();
    classModel = await classesResponse.json();
    testClassSpriteModel = await testSpritesResponse.json();
    aiClassSpriteModel = await aiSpritesResponse.json();
    if (!itemsResponse.ok) throw new Error(itemModel.error);
    if (!classesResponse.ok) throw new Error(classModel.error);
    if (!testSpritesResponse.ok) {
      throw new Error("테스트 클래스 디자인을 읽지 못했습니다");
    }
    if (!aiSpritesResponse.ok) {
      throw new Error("AI 클래스 디자인을 읽지 못했습니다");
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
    renderClassRoutes();
    renderTestClassRoutes();
    renderAiClassRoutes();
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
    } else if (tab.dataset.tab === "testClasses") {
      requestAnimationFrame(renderTestClassRoutes);
    } else if (tab.dataset.tab === "aiClasses") {
      requestAnimationFrame(renderAiClassRoutes);
    }
  });
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
        transition.current_class = classId;
        selectedTreeClassId = classId;
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
        "[data-class-picker], [data-merc-picker], [data-hire-picker]"
      )) {
    closePicker();
  }
});
window.addEventListener("resize", closePicker);
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
buildButton.addEventListener("click", buildRom);
loadAll();
