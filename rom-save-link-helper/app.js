(function () {
  "use strict";

  const core = globalThis.RomSaveLinkCore;
  const elements = {
    currentRom: document.querySelector("#currentRom"),
    latestRom: document.querySelector("#latestRom"),
    saveFile: document.querySelector("#saveFile"),
    saveDirectory: document.querySelector("#saveDirectory"),
    currentField: document.querySelector("#currentField"),
    latestField: document.querySelector("#latestField"),
    currentMeta: document.querySelector("#currentMeta"),
    latestMeta: document.querySelector("#latestMeta"),
    saveState: document.querySelector("#saveState"),
    saveMeta: document.querySelector("#saveMeta"),
    compatibilityState: document.querySelector("#compatibilityState"),
    sizeValue: document.querySelector("#sizeValue"),
    sramValue: document.querySelector("#sramValue"),
    outputValue: document.querySelector("#outputValue"),
    saveOutputValue: document.querySelector("#saveOutputValue"),
    message: document.querySelector("#message"),
    downloadRom: document.querySelector("#downloadRom"),
    downloadSave: document.querySelector("#downloadSave"),
  };

  const state = {
    currentFile: null,
    latestFile: null,
    saveFile: null,
    currentInfo: null,
    latestInfo: null,
    compatible: false,
  };

  function formatBytes(value) {
    if (value % (1024 * 1024) === 0) {
      return `${value / (1024 * 1024)} MiB`;
    }
    return `${value.toLocaleString("ko-KR")} bytes`;
  }

  function setState(element, text, className) {
    element.textContent = text;
    element.className = `state ${className}`;
  }

  function setMessage(text, className = "") {
    elements.message.textContent = text;
    elements.message.className = `message ${className}`.trim();
  }

  async function inspectFile(file) {
    const bytes = new Uint8Array(await file.arrayBuffer());
    return core.inspectRomBytes(bytes);
  }

  function currentMode() {
    return document.querySelector('input[name="mode"]:checked').value;
  }

  function updateSaveDisplay() {
    const save = state.saveFile;
    if (!save) {
      setState(elements.saveState, "선택 사항", "neutral");
      elements.saveMeta.textContent =
        "기존 ROM 이름을 유지하면 선택하지 않아도 됩니다";
      return;
    }
    const matches =
      state.currentFile &&
      core.saveMatchesRom(save.name, state.currentFile.name);
    setState(
      elements.saveState,
      matches ? "연결 확인" : "이름 불일치",
      matches ? "pass" : "warn"
    );
    elements.saveMeta.textContent = `${save.name} · ${formatBytes(save.size)}`;
  }

  function updateModeDisplay() {
    const mode = currentMode();
    const currentName = state.currentFile?.name || "-";
    const latestName = state.latestFile?.name || "-";
    elements.outputValue.textContent =
      mode === "current" ? currentName : latestName;
    elements.downloadSave.hidden = mode !== "latest";
    if (mode === "latest" && state.saveFile && state.latestFile) {
      elements.saveOutputValue.textContent = core.renamedSaveName(
        state.saveFile.name,
        state.latestFile.name
      );
    } else {
      elements.saveOutputValue.textContent =
        mode === "current" ? "기존 파일 유지" : "저장 파일 선택 필요";
    }
    renderCompatibility();
  }

  function renderCompatibility() {
    state.compatible = false;
    elements.downloadRom.disabled = true;
    elements.downloadSave.disabled = true;
    if (!state.currentInfo || !state.latestInfo) {
      setState(elements.compatibilityState, "대기", "neutral");
      elements.sizeValue.textContent = "-";
      elements.sramValue.textContent = "-";
      setMessage("현재 플레이 ROM과 최신 ROM을 선택하세요");
      return;
    }
    try {
      core.validateCompatibility(state.currentInfo, state.latestInfo);
      state.compatible = true;
      setState(elements.compatibilityState, "호환", "pass");
      elements.sizeValue.textContent = formatBytes(state.currentInfo.size);
      elements.sramValue.textContent = state.currentInfo.sramDescriptor;
      elements.downloadRom.disabled = false;
      const needsSave = currentMode() === "latest";
      elements.downloadSave.disabled = !(needsSave && state.saveFile);
      setMessage(
        needsSave
          ? "최신 ROM과 이름을 맞춘 저장 파일을 각각 저장하세요"
          : "최신 ROM이 기존 파일명으로 저장됩니다. 기존 SRAM은 그대로 유지됩니다",
        needsSave && !state.saveFile ? "warn" : "pass"
      );
    } catch (error) {
      setState(elements.compatibilityState, "차단", "fail");
      elements.sizeValue.textContent = `${formatBytes(
        state.currentInfo.size
      )} / ${formatBytes(state.latestInfo.size)}`;
      elements.sramValue.textContent = `${state.currentInfo.sramDescriptor} / ${state.latestInfo.sramDescriptor}`;
      setMessage(error.message, "fail");
    }
  }

  async function chooseRom(kind, file) {
    const isCurrent = kind === "current";
    const field = isCurrent ? elements.currentField : elements.latestField;
    const meta = isCurrent ? elements.currentMeta : elements.latestMeta;
    field.classList.remove("valid", "invalid");
    if (!file) {
      if (isCurrent) {
        state.currentFile = null;
        state.currentInfo = null;
      } else {
        state.latestFile = null;
        state.latestInfo = null;
      }
      meta.textContent = "선택되지 않음";
      renderCompatibility();
      return;
    }
    meta.textContent = "검사 중";
    try {
      const info = await inspectFile(file);
      if (isCurrent) {
        state.currentFile = file;
        state.currentInfo = info;
      } else {
        state.latestFile = file;
        state.latestInfo = info;
      }
      field.classList.add("valid");
      meta.textContent = `${file.name} · ${formatBytes(file.size)} · ${info.checksum}`;
      if (isCurrent) {
        updateSaveDisplay();
        findSaveInDirectory(elements.saveDirectory.files);
      }
    } catch (error) {
      if (isCurrent) {
        state.currentFile = file;
        state.currentInfo = null;
      } else {
        state.latestFile = file;
        state.latestInfo = null;
      }
      field.classList.add("invalid");
      meta.textContent = error.message;
    }
    updateModeDisplay();
  }

  function findSaveInDirectory(files) {
    if (!state.currentFile || !files?.length) {
      return;
    }
    const matches = Array.from(files).filter((file) =>
      core.saveMatchesRom(file.name, state.currentFile.name)
    );
    if (matches.length === 1) {
      state.saveFile = matches[0];
      updateSaveDisplay();
      updateModeDisplay();
    } else if (matches.length > 1) {
      state.saveFile = null;
      setState(elements.saveState, "여러 파일 발견", "warn");
      elements.saveMeta.textContent = matches.map((file) => file.name).join(", ");
      updateModeDisplay();
    } else {
      state.saveFile = null;
      setState(elements.saveState, "찾지 못함", "warn");
      elements.saveMeta.textContent = "현재 ROM과 같은 이름의 저장 파일이 없습니다";
      updateModeDisplay();
    }
  }

  async function saveBlob(blob, suggestedName) {
    if ("showSaveFilePicker" in globalThis && globalThis.isSecureContext) {
      const handle = await globalThis.showSaveFilePicker({
        suggestedName,
        types: [
          {
            description: "Langrisser II file",
            accept: {
              "application/octet-stream": [
                ".md",
                ".bin",
                ".gen",
                ".srm",
                ".sav",
                ".sram",
              ],
            },
          },
        ],
      });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return;
    }
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = suggestedName;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  elements.currentRom.addEventListener("change", () => {
    chooseRom("current", elements.currentRom.files[0] || null);
  });
  elements.latestRom.addEventListener("change", () => {
    chooseRom("latest", elements.latestRom.files[0] || null);
  });
  elements.saveFile.addEventListener("change", () => {
    state.saveFile = elements.saveFile.files[0] || null;
    updateSaveDisplay();
    updateModeDisplay();
  });
  elements.saveDirectory.addEventListener("change", () => {
    findSaveInDirectory(elements.saveDirectory.files);
  });
  document.querySelectorAll('input[name="mode"]').forEach((input) => {
    input.addEventListener("change", updateModeDisplay);
  });
  elements.downloadRom.addEventListener("click", async () => {
    if (!state.compatible || !state.latestFile) {
      return;
    }
    const name =
      currentMode() === "current"
        ? state.currentFile.name
        : state.latestFile.name;
    try {
      await saveBlob(state.latestFile, name);
      setMessage(`ROM 저장 완료: ${name}`, "pass");
    } catch (error) {
      if (error.name !== "AbortError") {
        setMessage(`ROM 저장 실패: ${error.message}`, "fail");
      }
    }
  });
  elements.downloadSave.addEventListener("click", async () => {
    if (!state.compatible || !state.saveFile || !state.latestFile) {
      return;
    }
    const name = core.renamedSaveName(
      state.saveFile.name,
      state.latestFile.name
    );
    try {
      await saveBlob(state.saveFile, name);
      setMessage(`저장 파일 저장 완료: ${name}`, "pass");
    } catch (error) {
      if (error.name !== "AbortError") {
        setMessage(`저장 파일 저장 실패: ${error.message}`, "fail");
      }
    }
  });

  updateModeDisplay();
})();
