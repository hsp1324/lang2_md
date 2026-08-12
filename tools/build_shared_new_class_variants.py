#!/usr/bin/env python3
"""Build fresh shared AI silhouettes for seven missing/weak class designs."""

from __future__ import annotations

from collections import Counter
import colorsys
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (
    ROM_INK,
    box_points,
    identity_locked_character_sprite,
    load_identity_mask_overrides,
    protected_eye_points,
)
from tools.build_class_sprite_assets import (
    DEFAULT_ROM,
    commander_sprite_map,
    render_sprite,
)
from tools.build_liana_lana_native16_assets import (
    limit_visible_palette,
    use_outer_canvas,
)
from tools.pixellab_elwin_inpaint import head_lock_box
from tools.scenario_data import KOREAN_NAME_BY_ID


OUTPUT = ROOT / "assets/class-sprites/source/latest/shared-new-classes-v1"
TRANSPARENT = (0, 0, 0, 0)
RESAMPLING = getattr(Image, "Resampling", Image)

CLASS_SPECS = {
    0x08: {
        "name": "힐러",
        "slug": "healer",
        "targets": (2, 3, 7, 10),
        "base_commander": 7,
        "base_face_class": 0x08,
        "base_mask": (7, 0x16),
    },
    0x16: {
        "name": "하이프리스트",
        "slug": "high-priest",
        "targets": (2, 3, 5, 7, 8, 10),
        "base_commander": 5,
        "base_face_class": 0x16,
        "base_mask": (5, 0x16),
    },
    0x18: {
        "name": "세이지",
        "slug": "sage",
        "targets": (2, 3, 5, 6, 10),
        "base_commander": 5,
        "base_face_class": 0x18,
        "base_mask": (5, 0x18),
    },
    0x15: {
        "name": "위저드",
        "slug": "wizard",
        "targets": (2, 3, 4, 5, 7, 9, 10),
        "base_commander": 5,
        "base_face_class": 0x15,
        "base_mask": (5, 0x15),
    },
    0x28: {
        "name": "서머너",
        "slug": "summoner",
        "targets": (2, 3, 5, 10),
        "base_commander": 5,
        "base_face_class": 0x28,
        "base_mask": (5, 0x28),
    },
    0x25: {
        "name": "에이전트",
        "slug": "agent",
        "targets": (2, 3),
        "base_commander": 5,
        "base_face_class": 0x15,
        "base_mask": (5, 0x15),
    },
    0x26: {
        "name": "자베라",
        "slug": "zarvera",
        "targets": (2, 3, 5, 9, 10),
        "base_commander": 5,
        "base_face_class": 0x26,
        "base_mask": (5, 0x14),
    },
}

# Dark/main/highlight equipment ramps. Skin, hair, white, gold, wood, and the
# exact identity pixels are intentionally excluded from this recolor pass.
COMMANDER_RAMPS = {
    2: ((109, 0, 0, 255), (219, 0, 0, 255), (255, 109, 109, 255)),
    3: ((0, 0, 109, 255), (0, 36, 182, 255), (73, 109, 255, 255)),
    4: ((0, 73, 73, 255), (0, 146, 146, 255), (73, 219, 219, 255)),
    5: ((36, 73, 0, 255), (36, 146, 36, 255), (109, 219, 146, 255)),
    6: ((0, 36, 109, 255), (36, 109, 219, 255), (109, 182, 255, 255)),
    7: ((0, 73, 73, 255), (0, 146, 109, 255), (36, 219, 146, 255)),
    8: ((36, 73, 109, 255), (73, 146, 219, 255), (109, 219, 255, 255)),
    9: ((73, 36, 109, 255), (146, 73, 182, 255), (219, 182, 219, 255)),
    10: ((73, 0, 109, 255), (146, 36, 182, 255), (219, 109, 255, 255)),
}

# This point in Hein's manually painted Wizard mask contains the editor's
# chroma-key magenta in the stock/reference cell.  It is background, not hair
# or face, so restoring it would leak the matte into the final sprite.
IDENTITY_MASK_EXCLUDED_POINTS = {
    (5, 0x15): {(12, 6)},
}


def visible_palette(image: Image.Image) -> list[str]:
    counts = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common()
    ]


def eye_anchor(image: Image.Image) -> tuple[int, int]:
    eyes = sorted(protected_eye_points(image))
    if not eyes:
        raise ValueError("identity source has no protected eye pixels")
    return eyes[len(eyes) // 2]


def translated_points(
    points: set[tuple[int, int]],
    dx: int,
    dy: int,
) -> set[tuple[int, int]] | None:
    result = {(x + dx, y + dy) for x, y in points}
    if any(not (0 <= x < 16 and 0 <= y < 16) for x, y in result):
        return None
    return result


def resolve_identity_points(
    rom: bytes,
    masks: dict[tuple[int, int], set[tuple[int, int]]],
    commander_id: int,
    class_id: int,
    original: Image.Image,
) -> tuple[set[tuple[int, int]], str]:
    key = (commander_id, class_id)
    if key in masks:
        return set(masks[key]) | protected_eye_points(original), "custom"

    sprite_map = commander_sprite_map(rom, commander_id)
    sprite_id = sprite_map[class_id]
    for other_class, other_sprite in sprite_map.items():
        other_key = (commander_id, other_class)
        if other_sprite == sprite_id and other_key in masks:
            return (
                set(masks[other_key]) | protected_eye_points(original),
                f"same-sprite:{other_class:02X}",
            )

    target_eye = eye_anchor(original)
    candidates: list[tuple[float, set[tuple[int, int]], int]] = []
    for (mask_commander, mask_class), source_points in masks.items():
        if mask_commander != commander_id or mask_class not in sprite_map:
            continue
        source = render_sprite(rom, sprite_map[mask_class], 1)
        source_eye = eye_anchor(source)
        shifted = translated_points(
            set(source_points),
            target_eye[0] - source_eye[0],
            target_eye[1] - source_eye[1],
        )
        if shifted is None:
            continue
        visible = sum(original.getpixel(point)[3] != 0 for point in shifted)
        score = visible / max(1, len(shifted)) - abs(len(shifted) - 72) / 500
        candidates.append((score, shifted, mask_class))
    if candidates:
        _, points, source_class = max(candidates, key=lambda row: row[0])
        return points | protected_eye_points(original), f"translated:{source_class:02X}"

    lock_box = head_lock_box(original)
    return (
        box_points(lock_box) | protected_eye_points(original),
        "automatic",
    )


def recolor_equipment(image: Image.Image, commander_id: int) -> Image.Image:
    dark, main, light = COMMANDER_RAMPS[commander_id]
    result = image.copy().convert("RGBA")
    for y in range(16):
        for x in range(16):
            red, green, blue, alpha = result.getpixel((x, y))
            if not alpha:
                continue
            hue, saturation, value = colorsys.rgb_to_hsv(
                red / 255, green / 255, blue / 255
            )
            # Generated class cloth uses blue, teal, violet, or magenta.
            # Brown skin/wood and yellow/gold trim live outside this range.
            if saturation < 0.28 or not 0.45 <= hue <= 0.96:
                continue
            result.putpixel(
                (x, y),
                dark if value < 0.36 else main if value < 0.72 else light,
            )
    return result


def close_zarvera_robe(image: Image.Image) -> Image.Image:
    """Close the matte-cut hole in the center of the Zarvera robe."""
    result = image.copy().convert("RGBA")
    dark = (36, 36, 73, 255)
    main = (73, 73, 109, 255)
    light = (73, 109, 255, 255)
    rows = {
        9: {7: main, 8: main},
        10: {7: light, 8: main},
        12: {
            5: dark, 6: main, 7: light, 8: light, 9: main, 10: dark,
        },
        13: {
            5: dark, 6: main, 7: main, 8: light, 9: main, 10: dark,
        },
        14: {
            5: dark, 6: dark, 7: main, 8: main, 9: dark, 10: dark,
        },
    }
    for y, columns in rows.items():
        for x, color in columns.items():
            result.putpixel((x, y), color)
    return result


def validate(
    image: Image.Image,
    original: Image.Image,
    identity: set[tuple[int, int]],
) -> dict[str, object]:
    visible_identity = {
        point for point in identity if original.getpixel(point)[3]
    }
    identity_match = sum(
        image.getpixel(point) == original.getpixel(point)
        for point in visible_identity
    )
    palette = visible_palette(image)
    empty_rows = [
        y for y in range(16)
        if not any(image.getpixel((x, y))[3] for x in range(16))
    ]
    empty_columns = [
        x for x in range(16)
        if not any(image.getpixel((x, y))[3] for y in range(16))
    ]
    pure_black = (0, 0, 0, 255) in image.getdata()
    magenta = any(
        color[3] and color[0] > 200 and color[2] > 200 and color[1] < 80
        for color in image.getdata()
    )
    return {
        "identity_match": identity_match,
        "identity_pixel_count": len(visible_identity),
        "mask_pixel_count": len(identity),
        "visible_color_count": len(palette),
        "palette": palette,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "pure_black": pure_black,
        "magenta_contamination": magenta,
        "accepted": (
            identity_match == len(visible_identity)
            and len(palette) <= 15
            and not empty_rows
            and not empty_columns
            and not pure_black
            and not magenta
        ),
    }


def write_contact(reports: list[dict[str, object]]) -> None:
    columns = 6
    cell = 192
    header = 34
    rows = (len(reports) + columns - 1) // columns
    canvas = Image.new(
        "RGBA", (columns * cell, rows * (cell + header)), (210, 210, 210, 255)
    )
    draw = ImageDraw.Draw(canvas)
    for index, report in enumerate(reports):
        x = (index % columns) * cell
        y = (index // columns) * (cell + header)
        draw.text(
            (x + 4, y + 4),
            f"{report['commander_id']:02d} {report['commander_name']} "
            f"{report['class_id']}",
            fill=(24, 24, 24, 255),
        )
        sprite = Image.open(OUTPUT / str(report["file"])).convert("RGBA")
        canvas.alpha_composite(
            sprite.resize((cell, cell), RESAMPLING.NEAREST), (x, y + header)
        )
    canvas.save(OUTPUT / "all-new-class-variants.png", optimize=True)


def build() -> dict[str, object]:
    rom = DEFAULT_ROM.read_bytes()
    masks = load_identity_mask_overrides()
    for key, excluded_points in IDENTITY_MASK_EXCLUDED_POINTS.items():
        if key in masks:
            masks[key] = set(masks[key]) - excluded_points
    master_dir = OUTPUT / "masters"
    logical_dir = OUTPUT / "logical16"
    preview_dir = OUTPUT / "previews"
    for directory in (master_dir, logical_dir, preview_dir):
        directory.mkdir(parents=True, exist_ok=True)

    reports: list[dict[str, object]] = []
    master_rows: dict[str, object] = {}
    resolved_identity_masks: dict[str, list[list[int]]] = {}
    for class_id, spec in CLASS_SPECS.items():
        slug = str(spec["slug"])
        base_commander = int(spec["base_commander"])
        base_face_class = int(spec["base_face_class"])
        base_original = render_sprite(
            rom,
            commander_sprite_map(rom, base_commander)[base_face_class],
            1,
        )
        base_identity = set(masks[tuple(spec["base_mask"])])
        master = Image.open(
            OUTPUT / "prototype16" / f"{class_id:02X}-{slug}.png"
        ).convert("RGBA")
        master = use_outer_canvas(master, class_id, base_identity)
        if class_id == 0x26:
            master = close_zarvera_robe(master)
        master, _ = limit_visible_palette(master, base_identity)
        master.save(master_dir / f"{class_id:02X}.png", optimize=True)
        master_rows[f"{class_id:02X}"] = {
            "file": f"masters/{class_id:02X}.png",
            "candidate": f"candidates/{class_id:02X}-{slug}.png",
        }

        equipment = master.copy()
        for point in base_identity:
            equipment.putpixel(point, TRANSPARENT)

        for commander_id in spec["targets"]:
            sprite_map = commander_sprite_map(rom, commander_id)
            original = render_sprite(rom, sprite_map[class_id], 1)
            identity, identity_source = resolve_identity_points(
                rom, masks, commander_id, class_id, original
            )
            resolved_identity_masks[f"{commander_id}:{class_id:02X}"] = [
                [x, y] for x, y in sorted(identity)
            ]
            colored = recolor_equipment(equipment, commander_id)
            converted, _, _, _ = identity_locked_character_sprite(
                colored,
                original,
                [ROM_INK],
                identity,
                preserve_generated_palette=True,
                restore_transparent_locked_points=False,
            )
            converted, remapped = limit_visible_palette(converted, identity)
            output_path = logical_dir / f"{commander_id:02d}-{class_id:02X}.png"
            converted.save(output_path, optimize=True)
            converted.resize((512, 512), RESAMPLING.NEAREST).save(
                preview_dir / f"{commander_id:02d}-{class_id:02X}.png",
                optimize=True,
            )
            row = {
                "commander_id": commander_id,
                "commander_name": KOREAN_NAME_BY_ID[commander_id],
                "class_id": f"{class_id:02X}",
                "class_name": spec["name"],
                "identity_source": identity_source,
                "palette_remapped_pixels": remapped,
                "file": str(output_path.relative_to(OUTPUT)),
                **validate(converted, original, identity),
            }
            reports.append(row)

    write_contact(reports)
    (OUTPUT / "identity-masks.json").write_text(
        json.dumps(
            {"version": 1, "masks": resolved_identity_masks},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    result = {
        "version": 1,
        "mode": (
            "fresh OpenAI class masters; whole-canvas fixed 16-cell sampling; "
            "shared equipment coordinates; commander identity and palette variants"
        ),
        "masters": master_rows,
        "all_accepted": all(row["accepted"] for row in reports),
        "classes": reports,
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    report = build()
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if report["all_accepted"] else 1)
