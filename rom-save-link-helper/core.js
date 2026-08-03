(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.RomSaveLinkCore = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const CHECKSUM_OFFSET = 0x18e;
  const CHECKSUM_DATA_OFFSET = 0x200;
  const SRAM_START = 0x1b0;
  const SRAM_END = 0x1bc;
  const SAVE_EXTENSIONS = new Set(["srm", "sav", "sram"]);

  function toHex(bytes) {
    return Array.from(bytes, (value) =>
      value.toString(16).padStart(2, "0")
    ).join("").toUpperCase();
  }

  function mdChecksum(bytes) {
    if (bytes.length < CHECKSUM_DATA_OFFSET) {
      throw new Error("메가드라이브 ROM 헤더가 너무 짧습니다");
    }
    let checksum = 0;
    for (let offset = CHECKSUM_DATA_OFFSET; offset < bytes.length; offset += 2) {
      const word =
        (bytes[offset] << 8) |
        (offset + 1 < bytes.length ? bytes[offset + 1] : 0);
      checksum = (checksum + word) & 0xffff;
    }
    return checksum;
  }

  function inspectRomBytes(bytes) {
    if (!(bytes instanceof Uint8Array)) {
      throw new TypeError("ROM 데이터는 Uint8Array여야 합니다");
    }
    if (bytes.length < CHECKSUM_DATA_OFFSET) {
      throw new Error("ROM 파일이 너무 작습니다");
    }
    const signature = String.fromCharCode(...bytes.slice(0x100, 0x104));
    if (signature !== "SEGA") {
      throw new Error("메가드라이브 ROM 헤더가 아닙니다");
    }
    const headerChecksum =
      (bytes[CHECKSUM_OFFSET] << 8) | bytes[CHECKSUM_OFFSET + 1];
    const calculatedChecksum = mdChecksum(bytes);
    if (headerChecksum !== calculatedChecksum) {
      throw new Error(
        `ROM 체크섬 불일치: ${headerChecksum
          .toString(16)
          .padStart(4, "0")
          .toUpperCase()} / ${calculatedChecksum
          .toString(16)
          .padStart(4, "0")
          .toUpperCase()}`
      );
    }
    return {
      size: bytes.length,
      checksum: headerChecksum.toString(16).padStart(4, "0").toUpperCase(),
      sramDescriptor: toHex(bytes.slice(SRAM_START, SRAM_END)),
    };
  }

  function splitName(filename) {
    const index = filename.lastIndexOf(".");
    if (index <= 0) {
      return { stem: filename, extension: "" };
    }
    return {
      stem: filename.slice(0, index),
      extension: filename.slice(index + 1),
    };
  }

  function saveMatchesRom(saveName, romName) {
    const save = splitName(saveName);
    const rom = splitName(romName);
    return (
      SAVE_EXTENSIONS.has(save.extension.toLowerCase()) &&
      save.stem.toLocaleLowerCase() === rom.stem.toLocaleLowerCase()
    );
  }

  function renamedSaveName(saveName, romName) {
    const extension = splitName(saveName).extension || "srm";
    return `${splitName(romName).stem}.${extension}`;
  }

  function validateCompatibility(current, latest) {
    if (current.size !== latest.size) {
      throw new Error(`ROM 크기가 다릅니다: ${current.size} / ${latest.size}`);
    }
    if (current.sramDescriptor !== latest.sramDescriptor) {
      throw new Error("SRAM 주소 형식이 달라 저장을 연결할 수 없습니다");
    }
    return true;
  }

  return {
    inspectRomBytes,
    mdChecksum,
    renamedSaveName,
    saveMatchesRom,
    splitName,
    validateCompatibility,
  };
});
