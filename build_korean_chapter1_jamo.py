#!/usr/bin/env python3
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import build_korean_chapter1 as chapter1
import build_korean_machine_jamo as base


SRC = Path("Langrisser II (Korean Hybrid WIP).md")
OUT = Path("Langrisser II (Korean Chapter1 Jamo).md")


PREFIX2 = {
    'z"', "z.", "z:", "zt", '{"', "{@", "{L", "{X", "{v", "}F", "}p", "}x", "~X",
    "HX", "Hr", "J*", "Jd", "K$", "K2", "LF", "Lz", "M$", "MF", "MP", "Ml",
    "N8", "N@", "N|", "O ", "Qb", "Q~", "RR", "Rr", "SZ", "Sf", "Ur", "VB",
    "Vd", "W6", "WJ", "Wh", "XF", "Xb", "YH", "Z*", "Z@", "Z`", "[*",
    "[:", "[d", "[l", "[~", "\\4", "]j", "^0", "^P", "_$", "_F", "_~",
    "`T", "`b", "`n", "`~",
}

PREFIX1 = {"Z", "h", "t"}


def to_compat_jamo(text: str) -> str:
    out: list[str] = []
    for ch in unicodedata.normalize("NFKD", text):
        out.append(base.JAMO_MAP.get(ch, ch))
    return "".join(out)


def detect_prefix(raw: bytes) -> bytes:
    text = raw.decode("latin1")
    if len(text) >= 2 and text[:2] in PREFIX2:
        return raw[:2]
    if text and text[0] in PREFIX1:
        return raw[:1]
    return b""


def encode_text(text: str, code_map: dict[str, int]) -> bytes:
    out = bytearray()
    for ch in to_compat_jamo(text):
        if ch == " ":
            out.append(0x20)
        elif "\u3130" <= ch <= "\u318f":
            out.append(code_map[ch])
        else:
            # Keep simple ASCII punctuation if it appears.
            out.append(ord(ch) if 0x20 <= ord(ch) <= 0x7E else ord("?"))
    return bytes(out)


def patch_text_at(
    rom: bytearray, offset: int, length: int, text: str, code_map: dict[str, int], preserve_prefix: bool
) -> None:
    raw = bytes(rom[offset : offset + length])
    prefix = detect_prefix(raw) if preserve_prefix else b""
    encoded = prefix + encode_text(text, code_map)
    if len(encoded) > length:
        raise ValueError(f"patch too long at 0x{offset:x}: {len(encoded)} > {length}: {text}")
    rom[offset : offset + length] = encoded + b" " * (length - len(encoded))


def update_checksum_and_header(rom: bytearray) -> None:
    rom[0x1A0:0x1A4] = (0).to_bytes(4, "big")
    rom[0x1A4:0x1A8] = (len(rom) - 1).to_bytes(4, "big")
    checksum = 0
    for i in range(0x200, len(rom), 2):
        checksum = (checksum + ((rom[i] << 8) | rom[i + 1])) & 0xFFFF
    rom[0x18E:0x190] = checksum.to_bytes(2, "big")


def main() -> int:
    records = json.loads(base.TRANS.read_text(encoding="utf-8"))
    code_map = base.assign_codes(base.collect_jamo(records))
    rom = bytearray(SRC.read_bytes())

    for offset, length, text in chapter1.TEXT_PATCHES:
        patch_text_at(rom, offset, length, text, code_map, preserve_prefix=offset >= 0x165000)
    for offset, length, text in chapter1.FIXED_TEXT_PATCHES:
        patch_text_at(rom, offset, length, text, code_map, preserve_prefix=False)

    update_checksum_and_header(rom)
    OUT.write_bytes(rom)
    print(f"wrote {OUT} ({len(rom)} bytes)")
    print(f"patched chapter text: {len(chapter1.TEXT_PATCHES)}")
    print(f"patched fixed/menu/name text: {len(chapter1.FIXED_TEXT_PATCHES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
