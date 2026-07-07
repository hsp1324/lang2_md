#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import os

from PIL import ImageFont

import build_korean_chapter1 as chapter1
import build_korean_chapter1_setup_complete as setup
import build_korean_hybrid_wip as hybrid
import build_korean_machine_jamo as base
import build_korean_wip as opening_wip


OUT = Path("Langrisser II (Korean Chapter1 Natural Jamo WIP).md")
ENABLE_EXPERIMENTAL_PROLOGUE = os.environ.get("ENABLE_EXPERIMENTAL_PROLOGUE") == "1"
ENABLE_COMPLETE_OPENING = os.environ.get("ENABLE_COMPLETE_OPENING") == "1"
ENABLE_WIDE_UI = os.environ.get("ENABLE_WIDE_UI", "1") != "0"
ENABLE_SCENARIO1_PROLOGUE = os.environ.get("ENABLE_SCENARIO1_PROLOGUE", "1") != "0"
VWF_UI_RESERVED = b"PlayerxEnemyNPCRangeAdjustLVHPMVATDFPressStartButtonNCSCorpDoneBackNextfhiX"
SCENARIO1_PROLOGUE_POINTER = 0x9CF7C
SCENARIO1_PROLOGUE_TEXT = """시나리오 1
시작의 날

홀로 여행하던 엘윈은
살라스의 작은 마을에서
잠시 쉬고 있었다.
그는 마을 사람들과
잘 어울렸고,
어린 마법사 헤인과도
곧 친구가 되었다.

어느 조용한 날,
헤인이 엘윈이 머무는
여관으로 다급히 뛰어왔다.
그는 레이가드 제국군이
마을을 습격하고 있으며,
헤인의 소꿉친구 리아나가
위험하다고 알렸다.

엘윈은 검을 움켜쥐고
그녀를 구하러 달려갔다."""


def chapter1_record_translations(records: list[dict[str, object]]) -> dict[int, str]:
    grouped: dict[int, list[str]] = {}
    text_patches = [patch for patch in chapter1.TEXT_PATCHES if 0x165000 <= patch[0] < 0x167100]
    for record in records:
        start = int(str(record["address"]), 16)
        end = start + int(record["size"])
        parts = [text for offset, _, text in text_patches if start <= offset < end]
        if parts:
            grouped[int(record["index"])] = "\n".join(parts)
    return grouped


def collect_record_jamo(records: list[dict[str, object]]) -> list[str]:
    chars: list[str] = []
    seen: set[str] = set()
    for record in records:
        for ch in base.to_compat_jamo(str(record["translation"])):
            if "\u3130" <= ch <= "\u318f" and ch not in seen:
                seen.add(ch)
                chars.append(ch)
    return chars


def collect_setup_fixed_chars() -> list[str]:
    fixed_patches = [
        patch
        for patch in chapter1.FIXED_TEXT_PATCHES
        if patch[0] in setup.SAFE_MENU_OFFSETS or patch[2] in setup.DEFAULT_TEXTS
    ]
    fixed_patches.extend(setup.SAFE_PATCH_OVERRIDES.values())
    fixed_patches.extend(setup.EXTRA_FIXED_PATCHES)

    chars: list[str] = []
    seen: set[str] = set()
    for _, _, text in fixed_patches + setup.TILEMAP16_PATCHES + setup.TILEBYTE_PATCHES:
        for ch in text:
            if ch != " " and ch not in seen:
                seen.add(ch)
                chars.append(ch)
    return chars


def assign_fixed_codes(chars: list[str], allow_unsafe_extra: bool = False) -> dict[str, int]:
    name_screen_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,;:'!?-#*\"/+"
    reserved_tiles = {ord(ch) for ch in name_screen_chars}
    reserved_tiles.update(chapter1.map_fixed_tile(ord(ch)) for ch in name_screen_chars)
    safe_pool: list[int] = []
    unsafe_pool: list[int] = []
    used_tiles: set[int] = set()
    for code in chapter1.CODE_POOL:
        tile = chapter1.map_fixed_tile(code)
        if tile in used_tiles:
            continue
        used_tiles.add(tile)
        if tile in reserved_tiles or code in reserved_tiles:
            unsafe_pool.append(code)
        else:
            safe_pool.append(code)
    unsafe_pool = [code for code in unsafe_pool if code >= 0x80] + [code for code in unsafe_pool if code < 0x80]
    code_pool = safe_pool + (unsafe_pool if allow_unsafe_extra else [])
    if len(chars) > len(code_pool):
        raise ValueError(f"Need {len(chars)} fixed glyphs, only {len(code_pool)}")
    return {ch: code_pool[idx] for idx, ch in enumerate(chars)}


def apply_safe_setup_patches(rom: bytearray, code_map: dict[str, int]) -> int:
    fixed_patches = [
        patch
        for patch in chapter1.FIXED_TEXT_PATCHES
        if patch[0] in setup.SAFE_MENU_OFFSETS or patch[2] in setup.DEFAULT_TEXTS
    ]
    fixed_patches.extend(setup.SAFE_PATCH_OVERRIDES.values())
    fixed_patches.extend(setup.EXTRA_FIXED_PATCHES)

    for offset, length, text in fixed_patches:
        chapter1.patch_text_at(rom, offset, length, text, code_map)
    for offset, length, text in setup.TILEMAP16_PATCHES:
        setup.patch_tilemap16_at(rom, offset, length, text, code_map)
    for offset, length, text in setup.TILEBYTE_PATCHES:
        setup.patch_tilebytes_at(rom, offset, length, text, code_map)
    return len(collect_setup_fixed_chars())


def collect_extra_jamo(chars: list[str], *texts: str) -> list[str]:
    seen = set(chars)
    out = list(chars)
    for text in texts:
        for ch in base.to_compat_jamo(text):
            if "\u3130" <= ch <= "\u318f" and ch not in seen:
                seen.add(ch)
                out.append(ch)
    return out


def assign_ui_safe_jamo_codes(chars: list[str]) -> dict[str, int]:
    reserved = set(b" .,!?-'\"/:|0123456789") | set(VWF_UI_RESERVED)
    pool = [c for c in range(0x21, 0x7F) if c not in reserved]
    if len(chars) > len(pool):
        raise ValueError(f"Need {len(chars)} jamo slots, only {len(pool)} UI-safe slots")
    return {ch: pool[idx] for idx, ch in enumerate(chars)}


def collect_text_jamo(text: str) -> list[str]:
    chars: list[str] = []
    seen: set[str] = set()
    for ch in base.to_compat_jamo(text):
        if "\u3130" <= ch <= "\u318f" and ch not in seen:
            seen.add(ch)
            chars.append(ch)
    return chars


def encode_prologue_text(text: str, code_map: dict[str, int]) -> bytes:
    out = bytearray()
    for ch in base.to_compat_jamo(text):
        if ch == "\n":
            out.append(0x0A)
        elif "\u3130" <= ch <= "\u318f":
            out.append(code_map[ch])
        elif 0x20 <= ord(ch) <= 0x7E:
            out.append(ord(ch))
        else:
            out.append(ord("?"))
    out.append(0x00)
    return bytes(out)


def patch_scenario1_prologue(rom: bytearray, cursor: int, code_map: dict[str, int]) -> int:
    missing = [ch for ch in collect_text_jamo(SCENARIO1_PROLOGUE_TEXT) if ch not in code_map]
    if missing:
        raise ValueError(f"scenario 1 prologue uses unmapped jamo: {''.join(missing)}")
    encoded = encode_prologue_text(SCENARIO1_PROLOGUE_TEXT, code_map)
    rom[SCENARIO1_PROLOGUE_POINTER : SCENARIO1_PROLOGUE_POINTER + 4] = cursor.to_bytes(4, "big")
    rom[cursor : cursor + len(encoded)] = encoded
    cursor += len(encoded)
    if cursor & 1:
        cursor += 1
    return cursor


def main() -> int:
    if not base.FONT_PATH.exists():
        raise FileNotFoundError(base.FONT_PATH)

    records = json.loads(base.TRANS.read_text(encoding="utf-8"))
    overrides = chapter1_record_translations(records)
    for record in records:
        idx = int(record["index"])
        if idx in overrides:
            record["translation"] = overrides[idx]
        else:
            record["translation"] = str(record["text"])

    rom = bytearray(base.SRC.read_bytes())

    jamo_chars = collect_record_jamo(records)
    if ENABLE_EXPERIMENTAL_PROLOGUE:
        jamo_chars = collect_extra_jamo(jamo_chars, SCENARIO1_PROLOGUE_TEXT)
    jamo_code_map = assign_ui_safe_jamo_codes(jamo_chars)
    opening_chars = hybrid.collect_opening_hangul() if ENABLE_COMPLETE_OPENING else []
    opening_code_map = hybrid.assign_opening_codes(jamo_code_map, opening_chars) if ENABLE_COMPLETE_OPENING else {}
    setup_fixed_chars = setup.collect_wide_ui_chars() if ENABLE_WIDE_UI else collect_setup_fixed_chars()
    prologue_fixed_jamo_chars = collect_text_jamo(SCENARIO1_PROLOGUE_TEXT) if ENABLE_EXPERIMENTAL_PROLOGUE else []
    if ENABLE_WIDE_UI and not ENABLE_EXPERIMENTAL_PROLOGUE:
        wide_code_map = setup.assign_wide_ui_codes(setup_fixed_chars)
        fixed_code_map = {}
    else:
        wide_code_map = {}
        fixed_code_map = assign_fixed_codes(
            setup_fixed_chars + prologue_fixed_jamo_chars,
            allow_unsafe_extra=ENABLE_EXPERIMENTAL_PROLOGUE,
        )

    font_vwf = ImageFont.truetype(str(base.FONT_PATH), 16 * 8)

    copy_size = base.font_copy_size(rom)
    rom[base.RELOCATED_BITMAP_TABLE : base.RELOCATED_BITMAP_TABLE + copy_size] = rom[
        base.ORIGINAL_BITMAP_TABLE : base.ORIGINAL_BITMAP_TABLE + copy_size
    ]
    rom[base.BITMAP_BASE_PATCH : base.BITMAP_BASE_PATCH + 4] = base.RELOCATED_BITMAP_TABLE.to_bytes(4, "big")
    cursor = base.RELOCATED_BITMAP_TABLE + copy_size

    for ch, code in jamo_code_map.items():
        glyph = base.render_glyph(ch, font_vwf)
        entry = base.WIDTH_TABLE + (code - 0x20) * 2
        rom[entry : entry + 2] = (cursor - base.RELOCATED_BITMAP_TABLE).to_bytes(2, "big")
        cursor_end = cursor + len(glyph)
        rom[cursor:cursor_end] = glyph
        cursor = cursor_end + (cursor_end & 1)

    if ENABLE_COMPLETE_OPENING:
        for ch, code in opening_code_map.items():
            glyph = opening_wip.render_opening_glyph(ch, font_vwf)
            entry = base.WIDTH_TABLE + (code - 0x20) * 2
            rom[entry : entry + 2] = (cursor - base.RELOCATED_BITMAP_TABLE).to_bytes(2, "big")
            cursor_end = cursor + len(glyph)
            rom[cursor:cursor_end] = glyph
            cursor = cursor_end + (cursor_end & 1)

    old_to_new: dict[int, int] = {}
    script_cursor = base.SCRIPT_BASE
    rom[base.SCRIPT_BASE : base.SCRIPT_LIMIT] = b"\xff" * (base.SCRIPT_LIMIT - base.SCRIPT_BASE)
    for record in records:
        old = int(str(record["address"]), 16)
        prefix = bytes.fromhex(str(record["prefix"]))
        encoded = prefix + base.encode_text(str(record["translation"]), jamo_code_map) + b"\xff\xff"
        old_to_new[old] = script_cursor
        rom[script_cursor : script_cursor + len(encoded)] = encoded
        script_cursor += len(encoded)
        if script_cursor & 1:
            script_cursor += 1

    patch_ranges = [(0x88000, 0x96000), (base.SCRIPT_LIMIT, 0x1F0000)]
    for old, new in old_to_new.items():
        old_b = old.to_bytes(4, "big")
        new_b = new.to_bytes(4, "big")
        for range_start, range_end in patch_ranges:
            start = range_start
            while True:
                hit = rom.find(old_b, start, range_end)
                if hit < 0:
                    break
                rom[hit : hit + 4] = new_b
                start = hit + 4

    opening_cursor = script_cursor
    if ENABLE_COMPLETE_OPENING:
        for name, parts in opening_wip.OPENING_PARTS.items():
            encoded = hybrid.encode_hybrid_opening(parts, opening_code_map)
            rom[base.OPENING_POINTER_PATCHES[name] : base.OPENING_POINTER_PATCHES[name] + 4] = opening_cursor.to_bytes(
                4, "big"
            )
            rom[opening_cursor : opening_cursor + len(encoded)] = encoded
            opening_cursor += len(encoded)
            if opening_cursor & 1:
                opening_cursor += 1

    if ENABLE_WIDE_UI and not ENABLE_EXPERIMENTAL_PROLOGUE:
        setup.apply_wide_ui_patches(rom, wide_code_map)
        fixed_glyphs = len(setup_fixed_chars) * 2
    else:
        chapter1.patch_fixed_font(rom, fixed_code_map)
        fixed_glyphs = apply_safe_setup_patches(rom, fixed_code_map)
    prologue_cursor = opening_cursor
    if ENABLE_SCENARIO1_PROLOGUE:
        prologue_cursor = patch_scenario1_prologue(rom, prologue_cursor, jamo_code_map)
    elif ENABLE_EXPERIMENTAL_PROLOGUE:
        prologue_cursor = patch_scenario1_prologue(rom, prologue_cursor, fixed_code_map)

    if prologue_cursor >= base.SCRIPT_LIMIT:
        raise ValueError(f"script overflow: 0x{prologue_cursor:x} >= 0x{base.SCRIPT_LIMIT:x}")

    base.update_checksum_and_header(rom)
    OUT.write_bytes(rom)
    print(f"wrote {OUT} ({len(rom)} bytes)")
    print(f"chapter 1 natural records: {len(overrides)}")
    print(f"main jamo glyphs: {len(jamo_chars)}")
    print(f"complete opening enabled: {ENABLE_COMPLETE_OPENING}")
    print(f"opening complete Hangul glyphs: {len(opening_chars)}")
    print(f"wide setup UI enabled: {ENABLE_WIDE_UI and not ENABLE_EXPERIMENTAL_PROLOGUE}")
    print(f"scenario 1 prologue enabled: {ENABLE_SCENARIO1_PROLOGUE}")
    print(f"setup fixed glyphs: {fixed_glyphs}")
    print(f"experimental prologue enabled: {ENABLE_EXPERIMENTAL_PROLOGUE}")
    print(f"scenario 1 prologue fixed jamo glyphs: {len(prologue_fixed_jamo_chars)}")
    print(f"fixed glyph slots: {len(fixed_code_map)}")
    print(f"font relocated: 0x{base.RELOCATED_BITMAP_TABLE:x}-0x{cursor:x}")
    print(f"script: 0x{base.SCRIPT_BASE:x}-0x{script_cursor:x}")
    print(f"opening: 0x{script_cursor:x}-0x{opening_cursor:x}")
    print(f"scenario 1 prologue: 0x{opening_cursor:x}-0x{prologue_cursor:x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
