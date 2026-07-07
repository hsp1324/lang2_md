#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import os

from PIL import Image, ImageDraw, ImageFont

import build_korean_chapter1 as chapter1


SRC = Path("Langrisser II (English).md")
OUT = Path(os.environ.get("KOREAN_OUT", "Langrisser II (Korean Chapter1 Setup Complete).md"))
ENABLE_DIRECT_NAME_SCREEN_FONT = False
DEFAULT_TEXTS = {"솔저", "가드"}
SAFE_MENU_OFFSETS = {
    0xA8DA9,  # Attack
    0xA8DB0,  # Magic
    0xA8DB6,  # Summon
    0xA8DBD,  # Treat
    0xA8DC3,  # Orders
    0xAE9A0,  # Knife
}
SAFE_PATCH_OVERRIDES = {
    0xA8DA2: (0xA8DA4, 4, "이동"),
}
EXTRA_FIXED_PATCHES = [
    (0x1B8E22, 4, "헤인"),
    (0x1B9C21, 4, "헤인"),
    (0x1BC1F5, 4, "헤인"),
    (0x1B9409, 7, "전사"),
]
TILEMAP16_PATCHES = [
    (0x09ABC2, len("Points"), "소지금"),
    (0x0A187E, len("Points"), "소지금"),
    (0x1E7E26, len("Assign Troops"), "용병 고용"),
    (0x1E7E44, len("Equip Items"), "장비 착용"),
    (0x1E7E5E, len("Item Shop"), "아이템 상점"),
    (0x1E7E74, len("Arrange Commanders"), "지휘관 배치"),
]
TILEBYTE_PATCHES = [
    (0xA2E12, len("Points"), "소지금"),
]
WIDE_FIXED_PATCHES = [
    (0xAE9A0, len("Knife"), "단검"),
    (0x1B8E22, len("Hein"), "헤인"),
    (0x1B9C21, len("Hein"), "헤인"),
    (0x1BC1F5, len("Hein"), "헤인"),
    (0x1B9409, len("Fighter"), "전사"),
    (0x1B9820, len("Soldier"), "솔저"),
    (0x1B9878, len("Guard"), "가드"),
]
WIDE_TILEMAP16_PATCHES = [
    (0x09ABC2, len("Points"), "소지금"),
    (0x0A187E, len("Points"), "소지금"),
    (0x1E7E26, len("Assign Troops"), "용병 고용"),
    (0x1E7E44, len("Equip Items"), "장비 착용"),
    (0x1E7E5E, len("Item Shop"), "상점"),
    (0x1E7E74, len("Arrange Commanders"), "지휘관 배치"),
]
WIDE_TILEBYTE_PATCHES = [
    (0xA2E12, len("Points"), "소지금"),
]
def main() -> int:
    text_patches: list[tuple[int, int, str]] = []
    if os.environ.get("SKIP_NAME_CLASS_PATCHES") == "1":
        fixed_patches = [patch for patch in chapter1.FIXED_TEXT_PATCHES if patch[0] < 0x100000]
    else:
        fixed_patches = [
            patch
            for patch in chapter1.FIXED_TEXT_PATCHES
            if patch[0] in SAFE_MENU_OFFSETS or patch[2] in DEFAULT_TEXTS
        ]
        fixed_patches.extend(SAFE_PATCH_OVERRIDES.values())
        fixed_patches.extend(EXTRA_FIXED_PATCHES)

    chars = []
    seen = set()
    for _, _, text in text_patches + fixed_patches:
        for ch in text:
            if ch != " " and ch not in seen:
                seen.add(ch)
                chars.append(ch)
    for _, _, text in TILEMAP16_PATCHES:
        for ch in text:
            if ch != " " and ch not in seen:
                seen.add(ch)
                chars.append(ch)
    for _, _, text in TILEBYTE_PATCHES:
        for ch in text:
            if ch != " " and ch not in seen:
                seen.add(ch)
                chars.append(ch)
    name_screen_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,;:'!?-#*\"/+"
    reserved_tiles = {ord(ch) for ch in name_screen_chars}
    reserved_tiles.update(chapter1.map_fixed_tile(ord(ch)) for ch in name_screen_chars)
    code_pool: list[int] = []
    used_tiles: set[int] = set()
    for code in chapter1.CODE_POOL:
        tile = chapter1.map_fixed_tile(code)
        if tile in used_tiles or tile in reserved_tiles:
            continue
        used_tiles.add(tile)
        code_pool.append(code)
    if len(chars) > len(code_pool):
        raise ValueError(f"Need {len(chars)} glyphs, only {len(code_pool)}")

    code_map = {ch: code_pool[idx] for idx, ch in enumerate(chars)}
    rom = bytearray(SRC.read_bytes())
    chapter1.patch_fixed_font(rom, code_map)
    if ENABLE_DIRECT_NAME_SCREEN_FONT:
        patch_direct_name_screen_font(rom, code_map, reserved_tiles)

    for offset, length, text in text_patches:
        chapter1.patch_text_at(rom, offset, length, text, code_map)
    for offset, length, text in fixed_patches:
        chapter1.patch_text_at(rom, offset, length, text, code_map)
    for offset, length, text in TILEMAP16_PATCHES:
        patch_tilemap16_at(rom, offset, length, text, code_map)
    for offset, length, text in TILEBYTE_PATCHES:
        patch_tilebytes_at(rom, offset, length, text, code_map)

    chapter1.update_checksum_and_header(rom)
    OUT.write_bytes(rom)
    print(f"wrote {OUT} ({len(rom)} bytes)")
    print(f"complete glyphs: {len(chars)}")
    print(f"scenario narration patches: {len(text_patches)}")
    print(f"setup/menu/name patches: {len(fixed_patches)}")
    print(f"tilemap menu patches: {len(TILEMAP16_PATCHES)}")
    print(f"tile byte patches: {len(TILEBYTE_PATCHES)}")
    return 0


def patch_tilemap16_at(rom: bytearray, offset: int, length: int, text: str, code_map: dict[str, int]) -> None:
    if len(text) > length:
        raise ValueError(f"tilemap patch too long at 0x{offset:x}: {len(text)} > {length}: {text}")
    tiles = []
    for ch in text:
        if ch == " ":
            tiles.append(0x20)
        else:
            tiles.append(chapter1.map_fixed_tile(code_map[ch]))
    tiles.extend([0x20] * (length - len(tiles)))
    for idx, tile in enumerate(tiles):
        pos = offset + idx * 2
        rom[pos : pos + 2] = tile.to_bytes(2, "big")


def patch_tilebytes_at(rom: bytearray, offset: int, length: int, text: str, code_map: dict[str, int]) -> None:
    if len(text) > length:
        raise ValueError(f"tile byte patch too long at 0x{offset:x}: {len(text)} > {length}: {text}")
    tiles = []
    for ch in text:
        if ch == " ":
            tiles.append(0x20)
        else:
            tiles.append(chapter1.map_fixed_tile(code_map[ch]))
    tiles.extend([0x20] * (length - len(tiles)))
    rom[offset : offset + length] = bytes(tiles)


def collect_wide_ui_chars() -> list[str]:
    chars: list[str] = []
    seen: set[str] = set()
    for _, _, text in WIDE_FIXED_PATCHES + WIDE_TILEMAP16_PATCHES + WIDE_TILEBYTE_PATCHES:
        for ch in text:
            if ch != " " and ch not in seen:
                seen.add(ch)
                chars.append(ch)
    return chars


def assign_wide_ui_codes(chars: list[str]) -> dict[str, tuple[int, int]]:
    name_screen_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,;:'!?-#*\"/+"
    reserved_tiles = {ord(ch) for ch in name_screen_chars}
    reserved_tiles.update(chapter1.map_fixed_tile(ord(ch)) for ch in name_screen_chars)
    code_pool: list[int] = []
    used_tiles: set[int] = set()
    for code in chapter1.CODE_POOL:
        tile = chapter1.map_fixed_tile(code)
        if tile in used_tiles or tile in reserved_tiles or code in reserved_tiles:
            continue
        used_tiles.add(tile)
        code_pool.append(code)
    if len(chars) * 2 > len(code_pool):
        raise ValueError(f"Need {len(chars) * 2} wide glyph slots, only {len(code_pool)}")
    return {ch: (code_pool[idx * 2], code_pool[idx * 2 + 1]) for idx, ch in enumerate(chars)}


def render_wide_fixed_glyph(text: str) -> tuple[bytes, bytes]:
    font_size = 8 if chapter1.FIXED_FONT_PATH.name.startswith("Galmuri") else 8 * 8
    font = ImageFont.truetype(str(chapter1.FIXED_FONT_PATH), font_size)
    canvas = Image.new("L", (16, 8), 0)
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = (16 - width) // 2 - bbox[0]
    y = (8 - height) // 2 - bbox[1]
    draw.text((x, y), text, fill=255, font=font)
    pixels: list[list[int]] = []
    for yy in range(8):
        row: list[int] = []
        for xx in range(16):
            row.append(3 if canvas.getpixel((xx, yy)) >= 96 else 1)
        pixels.append(row)
    left = [row[:8] for row in pixels]
    right = [row[8:] for row in pixels]
    return chapter1.encode_fixed_tile(left), chapter1.encode_fixed_tile(right)


def patch_wide_fixed_font(rom: bytearray, code_map: dict[str, tuple[int, int]]) -> None:
    used_tiles: dict[int, str] = {}
    for ch, (left_code, right_code) in code_map.items():
        left_tile = chapter1.map_fixed_tile(left_code)
        right_tile = chapter1.map_fixed_tile(right_code)
        for tile in (left_tile, right_tile):
            if tile in used_tiles:
                raise ValueError(f"tile collision: {ch!r} and {used_tiles[tile]!r} -> 0x{tile:02x}")
            used_tiles[tile] = ch
        left, right = render_wide_fixed_glyph(ch)
        left_off = chapter1.FIXED_FONT_BASE + left_tile * chapter1.FIXED_TILE_SIZE
        right_off = chapter1.FIXED_FONT_BASE + right_tile * chapter1.FIXED_TILE_SIZE
        rom[left_off : left_off + chapter1.FIXED_TILE_SIZE] = left
        rom[right_off : right_off + chapter1.FIXED_TILE_SIZE] = right


def encode_wide_tile_ids(text: str, code_map: dict[str, tuple[int, int]]) -> list[int]:
    tiles: list[int] = []
    for ch in text:
        if ch == " ":
            tiles.append(0x20)
        else:
            left_code, right_code = code_map[ch]
            tiles.append(chapter1.map_fixed_tile(left_code))
            tiles.append(chapter1.map_fixed_tile(right_code))
    return tiles


def patch_wide_text_at(rom: bytearray, offset: int, length: int, text: str, code_map: dict[str, tuple[int, int]]) -> None:
    codes: list[int] = []
    for ch in text:
        if ch == " ":
            codes.append(0x20)
        else:
            codes.extend(code_map[ch])
    if len(codes) > length:
        raise ValueError(f"wide patch too long at 0x{offset:x}: {len(codes)} > {length}: {text}")
    rom[offset : offset + length] = bytes(codes + [0x20] * (length - len(codes)))


def patch_wide_tilemap16_at(
    rom: bytearray, offset: int, length: int, text: str, code_map: dict[str, tuple[int, int]]
) -> None:
    tiles = encode_wide_tile_ids(text, code_map)
    if len(tiles) > length:
        raise ValueError(f"wide tilemap patch too long at 0x{offset:x}: {len(tiles)} > {length}: {text}")
    tiles.extend([0x20] * (length - len(tiles)))
    for idx, tile in enumerate(tiles):
        pos = offset + idx * 2
        rom[pos : pos + 2] = tile.to_bytes(2, "big")


def patch_wide_tilebytes_at(
    rom: bytearray, offset: int, length: int, text: str, code_map: dict[str, tuple[int, int]]
) -> None:
    tiles = encode_wide_tile_ids(text, code_map)
    if len(tiles) > length:
        raise ValueError(f"wide tile byte patch too long at 0x{offset:x}: {len(tiles)} > {length}: {text}")
    rom[offset : offset + length] = bytes(tiles + [0x20] * (length - len(tiles)))


def apply_wide_ui_patches(rom: bytearray, code_map: dict[str, tuple[int, int]]) -> None:
    patch_wide_fixed_font(rom, code_map)
    for offset, length, text in WIDE_FIXED_PATCHES:
        patch_wide_text_at(rom, offset, length, text, code_map)
    for offset, length, text in WIDE_TILEMAP16_PATCHES:
        patch_wide_tilemap16_at(rom, offset, length, text, code_map)
    for offset, length, text in WIDE_TILEBYTE_PATCHES:
        patch_wide_tilebytes_at(rom, offset, length, text, code_map)


def patch_direct_name_screen_font(rom: bytearray, code_map: dict[str, int], reserved_tiles: set[int]) -> None:
    """Mirror safe glyphs for screens that use text bytes as direct tile IDs."""
    from PIL import ImageFont

    font = ImageFont.truetype(str(chapter1.FONT_PATH), 8 * 8)
    for ch, code in code_map.items():
        if code < 0x80 or code in reserved_tiles:
            continue
        off = chapter1.FIXED_FONT_BASE + code * chapter1.FIXED_TILE_SIZE
        rom[off : off + chapter1.FIXED_TILE_SIZE] = chapter1.render_fixed_glyph(ch, font)


if __name__ == "__main__":
    raise SystemExit(main())
