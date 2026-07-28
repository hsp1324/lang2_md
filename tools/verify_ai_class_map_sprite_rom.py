#!/usr/bin/env python3
"""Verify and render production AI-class map sprites without emulation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools.build_class_sprite_assets import render_sprite
from tools.jp_byte_table_analyzer import KOREAN_CLASS_LABELS


DEFAULT_ROM = (
    ROOT
    / "roms/releases/Langrisser II (Korean Hard T1.0.0 B1.0.0).md"
)
DEFAULT_JSON = ROOT / "localization/ai_class_map_sprite_rom.json"
DEFAULT_IMAGE = (
    ROOT / "docs/assets/ai_class_map_sprite_rom_contact_sheet.png"
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def verify(rom_path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    rom = rom_path.read_bytes()
    rows: list[dict[str, object]] = []
    for commander_id, class_id, custom_sprite_id in (
        builder.AI_CLASS_MAP_SPRITE_SPECS
    ):
        asset_path = (
            ROOT
            / builder.AI_CLASS_MAP_SPRITE_ASSET_ROOT
            / str(commander_id)
            / f"{class_id:02X}.png"
        )
        asset_payload = asset_path.read_bytes()
        expected = builder.encode_ai_class_map_sprite(
            Image.open(asset_path)
        )
        record_offset = builder.commander_sprite_record_offset(
            rom, commander_id, class_id
        )
        actual_sprite_id = builder.be16(rom, record_offset + 1)
        if actual_sprite_id != custom_sprite_id:
            raise ValueError(
                f"commander {commander_id} class 0x{class_id:02X}: "
                f"sprite 0x{actual_sprite_id:04X} != "
                f"0x{custom_sprite_id:04X}"
            )
        frame_offsets = []
        for frame_base in builder.MAP_SPRITE_FRAME_BASES:
            offset = (
                frame_base
                + custom_sprite_id * builder.MAP_SPRITE_BYTES
            )
            actual = rom[offset : offset + builder.MAP_SPRITE_BYTES]
            if actual != expected:
                raise ValueError(
                    f"sprite payload differs at 0x{offset:06X}"
                )
            frame_offsets.append(f"0x{offset:06X}")
        rows.append({
            "commander_id": commander_id,
            "class_id": f"0x{class_id:02X}",
            "class_name": KOREAN_CLASS_LABELS[class_id],
            "mapping_record": f"0x{record_offset:06X}",
            "sprite_id": f"0x{custom_sprite_id:04X}",
            "frame_offsets": frame_offsets,
            "asset": str(asset_path.relative_to(ROOT)),
            "asset_sha256": sha256(asset_payload),
            "encoded_sha256": sha256(expected),
        })

    model: dict[str, object] = {
        "schema_version": 1,
        "status": "all_promoted_class_map_sprites_verified",
        "rom": {
            "path": str(rom_path.relative_to(ROOT)),
            "size": len(rom),
            "md_checksum": rom[0x18E:0x190].hex().upper(),
            "sha256": sha256(rom),
        },
        "scope": {
            "sprite_count": len(rows),
            "class_ids": sorted({row["class_id"] for row in rows}),
            "animation_policy": (
                "the reviewed 16x16 design is stored in both stock-timed "
                "map animation frame slots"
            ),
            "runtime_execution": (
                "outside this static verifier; see "
                "localization/ai_class_runtime_spot_check.json"
            ),
        },
        "sprites": rows,
    }
    return model, rows


def contact_sheet(rom_path: Path, rows: list[dict[str, object]]) -> Image.Image:
    rom = rom_path.read_bytes()
    columns = (0x04, 0x0B, 0x11, 0x13, 0x14, 0x16)
    by_key = {
        (int(row["commander_id"]), int(str(row["class_id"]), 16)): row
        for row in rows
    }
    cell_w = 118
    cell_h = 62
    header_h = 42
    sheet = Image.new(
        "RGBA",
        (cell_w * len(columns), header_h + cell_h * 10),
        (22, 25, 23, 255),
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(
        str(ROOT / "tools/fonts/Galmuri9.ttf"),
        9,
    )
    draw.text(
        (8, 5),
        "Accepted editor design -> bytes rendered back from built ROM",
        fill=(238, 242, 238, 255),
        font=font,
    )
    for column, class_id in enumerate(columns):
        draw.text(
            (column * cell_w + 7, 25),
            f"{class_id:02X} {KOREAN_CLASS_LABELS[class_id]}",
            fill=(155, 214, 169, 255),
            font=font,
        )
    for commander_id in range(1, 11):
        y = header_h + (commander_id - 1) * cell_h
        for column, class_id in enumerate(columns):
            x = column * cell_w
            draw.rectangle(
                (x, y, x + cell_w - 1, y + cell_h - 1),
                outline=(60, 70, 64, 255),
            )
            row = by_key.get((commander_id, class_id))
            draw.text(
                (x + 5, y + 4),
                f"C{commander_id:02d}",
                fill=(190, 196, 190, 255),
                font=font,
            )
            if row is None:
                draw.text(
                    (x + 42, y + 25),
                    "stock",
                    fill=(100, 108, 102, 255),
                    font=font,
                )
                continue
            asset = Image.open(ROOT / str(row["asset"])).convert("RGBA")
            rom_sprite = render_sprite(
                rom,
                int(str(row["sprite_id"]), 16),
                1,
            )
            asset = asset.resize((32, 32), Image.Resampling.NEAREST)
            rom_sprite = rom_sprite.resize(
                (32, 32), Image.Resampling.NEAREST
            )
            sheet.alpha_composite(asset, (x + 18, y + 21))
            draw.text(
                (x + 53, y + 31),
                ">",
                fill=(238, 242, 238, 255),
                font=font,
            )
            sheet.alpha_composite(rom_sprite, (x + 67, y + 21))
    return sheet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify production AI-class map sprite bytes"
    )
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model, rows = verify(args.rom)
    json_text = json.dumps(model, ensure_ascii=False, indent=2) + "\n"
    image = contact_sheet(args.rom, rows)
    if args.check:
        if args.json.read_text(encoding="utf-8") != json_text:
            raise SystemExit(f"stale sprite verification: {args.json}")
        current = Image.open(args.image).convert("RGBA")
        if current.tobytes() != image.tobytes():
            raise SystemExit(f"stale sprite contact sheet: {args.image}")
    else:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.image.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json_text, encoding="utf-8")
        image.save(args.image, optimize=True)
    print(
        f"verified {len(rows)} class map sprites in "
        f"{model['rom']['sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
