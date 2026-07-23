#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
DEFAULT_OUTPUT = ROOT / "editor/static/class-sprites"
CLASS_COUNT = 157
GENERIC_SPRITE_TABLE = 0x05DDE6
COMMANDER_SPRITE_POINTER_TABLE = 0x05DB80
COMMANDER_COUNT = 10
SPRITE_GRAPHICS = 0x052980
SPRITE_BYTES = 0x80

# Palette captured from the stock class-change screen. GST stores CRAM words
# little-endian; these are the four original 16-color rows.
PALETTES = (
    (0x000, 0x600, 0x000, 0xEEE, 0x880, 0x666, 0x6AC, 0x446,
     0x0E0, 0xEE0, 0x006, 0x800, 0x08E, 0x04E, 0x00A, 0x0CE),
    (0x000, 0x888, 0x222, 0xEEE, 0xE64, 0xC00, 0x6AC, 0x248,
     0x2C2, 0x062, 0x0AE, 0x00C, 0x006, 0xE0E, 0x644, 0xEC6),
    (0x000, 0x4AC, 0x48A, 0x246, 0x0C2, 0x0A2, 0x800, 0xA00,
     0xE00, 0x400, 0x008, 0x860, 0x222, 0x644, 0xA88, 0xCEE),
    (0x000, 0xECE, 0xEAC, 0xC66, 0xAE4, 0xAC4, 0xE62, 0xC60,
     0xC62, 0xC22, 0xA28, 0xE82, 0xC44, 0xE64, 0xEA8, 0xEEE),
)


def be16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def be32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def genesis_color(value: int) -> tuple[int, int, int, int]:
    red = ((value >> 0) & 0x0E) >> 1
    green = ((value >> 4) & 0x0E) >> 1
    blue = ((value >> 8) & 0x0E) >> 1
    return (
        round(red * 255 / 7),
        round(green * 255 / 7),
        round(blue * 255 / 7),
        255,
    )


def render_sprite(data: bytes, sprite_id: int, palette_id: int) -> Image.Image:
    start = SPRITE_GRAPHICS + sprite_id * SPRITE_BYTES
    payload = data[start : start + SPRITE_BYTES]
    if len(payload) != SPRITE_BYTES:
        raise ValueError(f"sprite 0x{sprite_id:02X} exceeds the ROM")
    palette = [genesis_color(value) for value in PALETTES[palette_id]]
    palette[0] = (0, 0, 0, 0)
    image = Image.new("RGBA", (16, 16))
    for tile_index in range(4):
        # A 2x2 Genesis sprite consumes tiles column-major.
        tile_x = (tile_index // 2) * 8
        tile_y = (tile_index % 2) * 8
        tile = payload[tile_index * 32 : (tile_index + 1) * 32]
        for y in range(8):
            for x in range(8):
                packed = tile[y * 4 + x // 2]
                color_index = (
                    (packed >> 4) & 0x0F if x % 2 == 0 else packed & 0x0F
                )
                image.putpixel((tile_x + x, tile_y + y), palette[color_index])
    return image


def commander_sprite_map(data: bytes, commander_id: int) -> dict[int, int]:
    if not 1 <= commander_id <= COMMANDER_COUNT:
        raise ValueError(f"commander ID must be 1..{COMMANDER_COUNT}")
    pointer = be32(
        data,
        COMMANDER_SPRITE_POINTER_TABLE + (commander_id - 1) * 4,
    )
    result: dict[int, int] = {}
    while data[pointer] != 0xFF:
        class_id = data[pointer]
        sprite_id = be16(data, pointer + 1)
        if class_id in result:
            raise ValueError(
                f"commander {commander_id} repeats class 0x{class_id:02X}"
            )
        result[class_id] = sprite_id
        pointer += 3
    return result


def build_assets(
    rom_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    data = rom_path.read_bytes()
    generic_dir = output_dir / "generic"
    generic_dir.mkdir(parents=True, exist_ok=True)
    generic: dict[str, object] = {}
    for class_id in range(CLASS_COUNT):
        sprite_id = be16(data, GENERIC_SPRITE_TABLE + class_id * 2)
        files = []
        for palette_id in range(len(PALETTES)):
            target = generic_dir / f"{class_id:02X}-p{palette_id}.png"
            render_sprite(data, sprite_id, palette_id).save(target, optimize=True)
            files.append(str(target.relative_to(output_dir)))
        generic[str(class_id)] = {
            "sprite_id": sprite_id,
            "files": files,
        }

    commanders: dict[str, object] = {}
    for commander_id in range(1, COMMANDER_COUNT + 1):
        commander_dir = output_dir / "commanders" / str(commander_id)
        commander_dir.mkdir(parents=True, exist_ok=True)
        rows: dict[str, object] = {}
        for class_id, sprite_id in sorted(
            commander_sprite_map(data, commander_id).items()
        ):
            target = commander_dir / f"{class_id:02X}-p1.png"
            render_sprite(data, sprite_id, 1).save(target, optimize=True)
            rows[str(class_id)] = {
                "sprite_id": sprite_id,
                "file": str(target.relative_to(output_dir)),
            }
        commanders[str(commander_id)] = rows

    manifest = {
        "generated_from": str(rom_path.relative_to(ROOT)),
        "graphics_base": f"0x{SPRITE_GRAPHICS:06X}",
        "generic_table": f"0x{GENERIC_SPRITE_TABLE:06X}",
        "commander_pointer_table": f"0x{COMMANDER_SPRITE_POINTER_TABLE:06X}",
        "generic_class_count": len(generic),
        "commander_count": len(commanders),
        "generic": generic,
        "commanders": commanders,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract class and mercenary sprites for the local editor"
    )
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_assets(args.rom, args.output)
    print(
        f"{args.output}: {manifest['generic_class_count']} generic classes, "
        f"{manifest['commander_count']} commander maps"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
