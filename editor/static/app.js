const scenarioSelect = document.querySelector("#scenarioSelect");
const romSelect = document.querySelector("#romSelect");
const filterSelect = document.querySelector("#filterSelect");
const recordsBody = document.querySelector("#recordsBody");
const sourcePath = document.querySelector("#sourcePath");
const recordSummary = document.querySelector("#recordSummary");
const buildButton = document.querySelector("#buildButton");
const notice = document.querySelector("#notice");
let model = null;

function showNotice(message, success = false) {
  notice.textContent = message;
  notice.hidden = false;
  notice.classList.toggle("success", success);
}

function classOptions(selected, allowEmpty = false) {
  const empty = allowEmpty ? `<option value="255" ${selected === 255 ? "selected" : ""}>없음</option>` : "";
  return empty + model.classes.map(item =>
    `<option value="${item.id}" ${item.id === selected ? "selected" : ""}>${item.id.toString(16).padStart(2, "0").toUpperCase()} ${item.ko}</option>`
  ).join("");
}

function render() {
  const filter = filterSelect.value;
  recordsBody.innerHTML = "";
  let visible = 0;
  model.records.forEach(record => {
    const isEnemy = record.role === "적군";
    if ((filter === "enemy" && !isEnemy) || (filter === "event" && isEnemy)) return;
    visible += 1;
    const row = document.createElement("tr");
    row.dataset.index = record.index;
    row.dataset.hidden = record.hidden;
    row.innerHTML = `
      <td>${record.index + 1}. ${record.role}</td>
      <td class="identity">${record.name.ko}<small>${record.name.jp}</small></td>
      <td><select data-field="class_id">${classOptions(record.class_id)}</select></td>
      <td><input data-field="level" type="number" min="0" max="255" value="${record.level}"></td>
      <td><input data-field="at" type="number" min="0" max="255" value="${record.at}"></td>
      <td><input data-field="df" type="number" min="0" max="255" value="${record.df}"></td>
      <td>${record.x === 255 ? "대기" : `${record.x}, ${record.y}`}</td>
      ${record.mercenaries.map((id, slot) => `<td><select data-merc="${slot}">${classOptions(id, true)}</select></td>`).join("")}
      <td class="offset">0x${record.offset.toString(16).toUpperCase()}</td>`;
    recordsBody.appendChild(row);
  });
  recordSummary.textContent = `${visible} / ${model.record_count}개 배치`;
}

function collectVisibleEdits() {
  recordsBody.querySelectorAll("tr").forEach(row => {
    const record = model.records[Number(row.dataset.index)];
    row.querySelectorAll("[data-field]").forEach(input => record[input.dataset.field] = Number(input.value));
    row.querySelectorAll("[data-merc]").forEach(input => record.mercenaries[Number(input.dataset.merc)] = Number(input.value));
  });
}

async function loadScenario() {
  buildButton.disabled = true;
  notice.hidden = true;
  try {
    const response = await fetch(`/api/scenarios/${scenarioSelect.value}?rom=${romSelect.value}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    model = data;
    sourcePath.textContent = `${data.rom_path} · 헤더 0x${data.header_offset.toString(16).toUpperCase()} · 고정 배치표 0x${data.record_list_offset.toString(16).toUpperCase()}`;
    render();
  } catch (error) {
    showNotice(error.message);
  } finally {
    buildButton.disabled = false;
  }
}

async function buildRom() {
  collectVisibleEdits();
  buildButton.disabled = true;
  try {
    const response = await fetch("/api/build", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({number: model.number, rom: romSelect.value, records: model.records}),
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
scenarioSelect.addEventListener("change", loadScenario);
romSelect.addEventListener("change", loadScenario);
filterSelect.addEventListener("change", () => { collectVisibleEdits(); render(); });
buildButton.addEventListener("click", buildRom);
loadScenario();
