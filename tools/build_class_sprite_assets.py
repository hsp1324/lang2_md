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

# Bald uses a second Fighter record (0x2E) that otherwise looks identical to
# the generic imperial Fighter (0x2D). Give only his representative editor
# preview distinctive violet armor with a gold-rimmed crimson shield while
# preserving the white blade and every ROM-backed pixel.
REPRESENTATIVE_PALETTE_OVERRIDES = {
    # Shaman (0x0A) and the NPC Priest (0x9C) share stock sprite 0x1D.
    # Recolor Shaman's robe and hood to one lavender-to-mauve ramp so the two
    # classes are visually distinct without changing the white hood highlight,
    # face, staff, or silhouette.
    0x0A: {
        0x1: 0xA8A,  # gray hood face -> soft lavender
        0x4: 0xA8A,  # blue robe face -> soft lavender
        0x5: 0x646,  # navy robe shadow -> deep mauve
        0xE: 0x646,  # rear hood shadow -> deep mauve
        0xF: 0xEEE,  # cyan robe highlight -> white
    },
    0x2E: {
        0x4: 0xE6C,  # light violet armor
        0x5: 0xA04,  # deep violet armor
        0x8: 0x00E,  # crimson shield center
        0x9: 0x006,  # crimson shield shadow
        0xE: 0x624,  # dark armor outline
        0xF: 0xEAC,  # pale lavender highlight
    },
    # Scenario 10's hostile Pirates use NPC class 0x9A. Keep their shared
    # silhouette and blue shield, but cool the neutral armor into a restrained
    # sky-blue naval ramp while preserving the blade.
    0x9A: {
        0x1: 0xECA,  # gray armor shade -> light sky blue
        0xE: 0xA86,  # deepest gray -> muted naval blue-gray
    },
    # Scenario 1's Militia uses NPC Lord 0x99. Give it Loren's former ivory
    # ramp so it matches the 0x9C Priest while retaining the stock blue/cyan
    # shield, gold trim, white blade, and every original pixel coordinate.
    0x99: {
        0x1: 0x6AC,  # gray armor shade -> pale gold
        0xE: 0x248,  # deepest armor shade -> warm brown
    },
    # Loren keeps the same stock silhouette and protected equipment, but uses
    # a warm crimson-to-deep-red armor gradient that matches the live map.
    0x9B: {
        0x1: 0x46E,  # gray armor shade -> bright warm red
        0xE: 0x008,  # deepest armor shade -> deep red
    },
    # Sorcerer 0x09, Shaman 0x0A, and NPC Priest 0x9C all share sprite 0x1D.
    # Keep Sorcerer blue, make Shaman violet above, and give only the Priest
    # representative the same white, pale-gold ivory, and warm-brown ramp as
    # Loren's 0x9B High Lord. Their distinct silhouettes still communicate
    # their roles while the shared colors make the pair read as a matched set.
    0x9C: {
        0x1: 0x6AC,  # gray hood face -> same pale-gold ivory as High Lord
        0x5: 0x6AC,  # navy robe shadow -> pale-gold ivory
        0xE: 0x248,  # rear hood shadow -> High Lord's deep warm ivory
        0xF: 0x248,  # cyan robe accent -> warm brown
    },
}

# These near-white tints are editor-design colors rather than ROM palette
# replacements. The Mega Drive's next legal channel step is too saturated for
# the requested subtle tint, so keep this finer RGB adjustment preview-only.
REPRESENTATIVE_RGBA_OVERRIDES = {
    0x99: {
        0x3: (255, 251, 234, 255),  # white armor -> barely warm ivory
    },
    0x9A: {
        0x3: (240, 250, 255, 255),  # white armor -> barely icy sky blue
    },
    0x9B: {
        0x3: (255, 242, 238, 255),  # white helmet -> warm red highlight
    },
    0x9C: {
        0x3: (255, 251, 234, 255),  # white hood -> barely warm ivory
        0x4: (255, 251, 234, 255),  # white robe face -> same ivory
    },
}

# The right-hand blade shares palette indexes 1/3/E with the armor. Render
# these exact frame-0 coordinates with the stock palette so only the armor is
# recolored.
LOREN_BLADE_COORDS = frozenset(
    {
        (14, 3),
        (14, 4),
        (14, 5),
        (14, 6),
        (13, 7),
        (14, 7),
        (13, 8),
        (14, 8),
        (13, 9),
    }
)

# Commander-specific Shaman sprites keep character-specific hair and faces.
# Their robe pixels are confined to the lower body, so apply the Shaman color
# ramp only there and leave blue hair or head ornaments untouched.
SHAMAN_ROBE_COORDS = frozenset(
    (x, y) for y in range(9, 16) for x in range(1, 11)
)
SHAMAN_COMMANDER_PALETTE_OVERRIDES = {
    1: {0x4: 0xA8A, 0x5: 0x646, 0xF: 0xEEE},
    2: {0x6: 0xA8A, 0x7: 0x646},
    3: {0x4: 0xA8A, 0x6: 0xA8A, 0x7: 0x646},
    4: {0x6: 0xA8A, 0x7: 0x646, 0xB: 0xA8A, 0xC: 0x646},
    5: {0x1: 0xA8A, 0xE: 0x646},
    8: {0x6: 0xA8A, 0x7: 0x646},
    9: {0x6: 0xA8A, 0x7: 0x646},
}


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


def render_sprite(
    data: bytes,
    sprite_id: int,
    palette_id: int,
    *,
    palette_override: dict[int, int] | None = None,
    rgba_override: dict[int, tuple[int, int, int, int]] | None = None,
    stock_palette_coords: frozenset[tuple[int, int]] = frozenset(),
    palette_override_coords: frozenset[tuple[int, int]] | None = None,
) -> Image.Image:
    start = SPRITE_GRAPHICS + sprite_id * SPRITE_BYTES
    payload = data[start : start + SPRITE_BYTES]
    if len(payload) != SPRITE_BYTES:
        raise ValueError(f"sprite 0x{sprite_id:02X} exceeds the ROM")
    stock_palette = [
        genesis_color(value) for value in PALETTES[palette_id]
    ]
    stock_palette[0] = (0, 0, 0, 0)
    palette_values = list(PALETTES[palette_id])
    if palette_override:
        for color_index, value in palette_override.items():
            palette_values[color_index] = value
    palette = [genesis_color(value) for value in palette_values]
    if rgba_override:
        for color_index, rgba in rgba_override.items():
            palette[color_index] = rgba
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
                coords = (tile_x + x, tile_y + y)
                use_override = (
                    palette_override is not None
                    and (
                        palette_override_coords is None
                        or coords in palette_override_coords
                    )
                    and coords not in stock_palette_coords
                )
                color = (
                    palette[color_index]
                    if use_override
                    else stock_palette[color_index]
                )
                image.putpixel(coords, color)
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
    representative_sprite_ids: dict[int, int] = {}
    for commander_id in range(1, COMMANDER_COUNT + 1):
        commander_dir = output_dir / "commanders" / str(commander_id)
        commander_dir.mkdir(parents=True, exist_ok=True)
        rows: dict[str, object] = {}
        for class_id, sprite_id in sorted(
            commander_sprite_map(data, commander_id).items()
        ):
            representative_sprite_ids.setdefault(class_id, sprite_id)
            target = commander_dir / f"{class_id:02X}-p1.png"
            palette_override = (
                SHAMAN_COMMANDER_PALETTE_OVERRIDES[commander_id]
                if (
                    class_id == 0x0A
                    and commander_id in SHAMAN_COMMANDER_PALETTE_OVERRIDES
                )
                else REPRESENTATIVE_PALETTE_OVERRIDES.get(class_id)
            )
            palette_override_coords = (
                SHAMAN_ROBE_COORDS if class_id == 0x0A else None
            )
            render_sprite(
                data,
                sprite_id,
                1,
                palette_override=palette_override,
                palette_override_coords=palette_override_coords,
            ).save(target, optimize=True)
            rows[str(class_id)] = {
                "sprite_id": sprite_id,
                "file": str(target.relative_to(output_dir)),
            }
        commanders[str(commander_id)] = rows

    # The stock generic table deliberately maps many playable commander
    # classes to the Aniki placeholder (sprite 0x18). Their real map sprites
    # live in the per-commander override tables above. Give class-only editor
    # pickers a ROM-backed representative instead of exposing that placeholder.
    representative_dir = output_dir / "representative"
    representative_dir.mkdir(parents=True, exist_ok=True)
    representatives: dict[str, object] = {}
    for class_id in range(CLASS_COUNT):
        generic_sprite_id = int(generic[str(class_id)]["sprite_id"])
        sprite_id = (
            representative_sprite_ids[class_id]
            if generic_sprite_id == 0x18 and class_id in representative_sprite_ids
            else generic_sprite_id
        )
        target = representative_dir / f"{class_id:02X}-p1.png"
        palette_override = REPRESENTATIVE_PALETTE_OVERRIDES.get(class_id)
        rgba_override = REPRESENTATIVE_RGBA_OVERRIDES.get(class_id)
        stock_palette_coords = (
            LOREN_BLADE_COORDS
            if class_id in (0x99, 0x9A, 0x9B)
            else frozenset()
        )
        render_sprite(
            data,
            sprite_id,
            1,
            palette_override=palette_override,
            rgba_override=rgba_override,
            stock_palette_coords=stock_palette_coords,
        ).save(target, optimize=True)
        representatives[str(class_id)] = {
            "sprite_id": sprite_id,
            "generic_sprite_id": generic_sprite_id,
            "uses_commander_override": sprite_id != generic_sprite_id,
            "uses_palette_override": palette_override is not None,
            "file": str(target.relative_to(output_dir)),
        }

    manifest = {
        "generated_from": str(rom_path.relative_to(ROOT)),
        "graphics_base": f"0x{SPRITE_GRAPHICS:06X}",
        "generic_table": f"0x{GENERIC_SPRITE_TABLE:06X}",
        "commander_pointer_table": f"0x{COMMANDER_SPRITE_POINTER_TABLE:06X}",
        "generic_class_count": len(generic),
        "representative_class_count": len(representatives),
        "commander_count": len(commanders),
        "generic": generic,
        "representatives": representatives,
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
