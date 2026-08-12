#!/usr/bin/env python3
"""Build mounted tier-1 aliases and stronger tier-2 mount recolors."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import load_identity_mask_overrides
from tools.build_class_sprite_assets import (
    DEFAULT_ROM,
    commander_sprite_map,
    render_sprite,
)
from tools.build_shared_new_class_variants import resolve_identity_points


OUTPUT = (
    ROOT
    / "assets/class-sprites/source/latest/keith-lester-tier1-mounted-v1"
)
RESAMPLING = getattr(Image, "Resampling", Image)

# The tier-1 Fighter slots deliberately reuse each commander's original
# mounted tier-2 geometry.  The old tier-2 slots become stronger-colored Lord
# variants while retaining the exact same 16x16 alpha mask and coordinates.
TARGETS = {
    (7, 0x01): {"source_class": 0x06, "name": "호크나이트", "strong": False},
    (7, 0x06): {"source_class": 0x06, "name": "호크로드", "strong": True},
    (9, 0x01): {"source_class": 0x07, "name": "크로코나이트", "strong": False},
    (9, 0x07): {"source_class": 0x07, "name": "크로코로드", "strong": True},
}


def visible_points(image: Image.Image) -> set[tuple[int, int]]:
    return {
        (x, y)
        for y in range(16)
        for x in range(16)
        if image.getpixel((x, y))[3]
    }


def resolved_head_mask(
    rom: bytes,
    masks: dict[tuple[int, int], set[tuple[int, int]]],
    commander_id: int,
    source_class: int,
    source: Image.Image,
) -> set[tuple[int, int]]:
    points, _ = resolve_identity_points(
        rom,
        masks,
        commander_id,
        source_class,
        source,
    )
    # Mounted references need a compact rider-head mask.  The translated
    # masks can otherwise reach into the bird/crocodile body below the rider.
    max_y = 9 if commander_id == 7 else 8
    return {point for point in points if point[1] <= max_y}


def resolved_mount_mask(
    commander_id: int,
    source: Image.Image,
    identity: set[tuple[int, int]],
) -> set[tuple[int, int]]:
    visible = visible_points(source)
    if commander_id == 7:
        # Hawk body/wing occupies the right half from row 4 and the full lower
        # silhouette.  Rider-head pixels always win if the regions overlap.
        region = {
            (x, y)
            for x, y in visible
            if (x >= 8 and y >= 4) or y >= 9
        }
    else:
        # Lester's green crocodile body is the connected lower silhouette.
        region = {(x, y) for x, y in visible if y >= 9}
    return region - identity


def recolor_strong_mount(
    commander_id: int,
    image: Image.Image,
    mount: set[tuple[int, int]],
) -> Image.Image:
    result = image.copy()
    if commander_id == 7:
        color_map = {
            (146, 73, 36, 255): (219, 36, 36, 255),
            (219, 182, 109, 255): (255, 146, 0, 255),
        }
    else:
        color_map = {
            (36, 109, 0, 255): (109, 0, 0, 255),
            (36, 219, 36, 255): (219, 36, 36, 255),
        }
    for point in mount:
        color = result.getpixel(point)
        if color in color_map:
            result.putpixel(point, color_map[color])
    return result


def write_contact(rows: list[dict[str, object]]) -> None:
    cell = 256
    header = 36
    canvas = Image.new(
        "RGBA",
        (2 * cell, 2 * (cell + header)),
        (210, 210, 210, 255),
    )
    draw = ImageDraw.Draw(canvas)
    for index, row in enumerate(rows):
        x = (index % 2) * cell
        y = (index // 2) * (cell + header)
        draw.text(
            (x + 5, y + 6),
            f"{row['commander_id']}:{row['class_id']} {row['name']}",
            fill=(24, 24, 24, 255),
        )
        sprite = Image.open(OUTPUT / str(row["file"])).convert("RGBA")
        canvas.alpha_composite(
            sprite.resize((cell, cell), RESAMPLING.NEAREST),
            (x, y + header),
        )
    canvas.save(OUTPUT / "all-tier-mounted-variants.png", optimize=True)


def build() -> dict[str, object]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    logical_dir = OUTPUT / "logical16"
    preview_dir = OUTPUT / "previews"
    logical_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    rom = DEFAULT_ROM.read_bytes()
    masks = load_identity_mask_overrides()
    rows: list[dict[str, object]] = []
    identity_masks: dict[str, list[list[int]]] = {}
    mount_masks: dict[str, list[list[int]]] = {}

    for (commander_id, class_id), spec in TARGETS.items():
        source_class = int(spec["source_class"])
        source = render_sprite(
            rom,
            commander_sprite_map(rom, commander_id)[source_class],
            1,
        )
        identity = resolved_head_mask(
            rom,
            masks,
            commander_id,
            source_class,
            source,
        )
        mount = resolved_mount_mask(commander_id, source, identity)
        result = (
            recolor_strong_mount(commander_id, source, mount)
            if bool(spec["strong"])
            else source.copy()
        )
        filename = f"{commander_id:02d}-{class_id:02X}.png"
        result.save(logical_dir / filename, optimize=True)
        result.resize((512, 512), RESAMPLING.NEAREST).save(
            preview_dir / filename,
            optimize=True,
        )
        key = f"{commander_id}:{class_id:02X}"
        identity_masks[key] = [[x, y] for x, y in sorted(identity)]
        mount_masks[key] = [[x, y] for x, y in sorted(mount)]
        rows.append({
            "commander_id": commander_id,
            "class_id": f"{class_id:02X}",
            "source_class_id": f"{source_class:02X}",
            "name": spec["name"],
            "strong_mount": bool(spec["strong"]),
            "identity_pixel_count": len(identity),
            "mount_pixel_count": len(mount),
            "same_geometry_as_source": (
                result.getchannel("A").tobytes()
                == source.getchannel("A").tobytes()
            ),
            "file": f"logical16/{filename}",
        })

    for name, payload in (
        ("identity-masks.json", {"version": 1, "masks": identity_masks}),
        ("mount-masks.json", {"version": 1, "masks": mount_masks}),
    ):
        (OUTPUT / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    write_contact(rows)
    report = {
        "version": 1,
        "mode": "stock mounted geometry; stronger tier-2 mount-only recolor",
        "classes": rows,
        "all_same_geometry": all(row["same_geometry_as_source"] for row in rows),
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
