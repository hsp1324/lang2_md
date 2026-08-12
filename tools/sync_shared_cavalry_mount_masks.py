#!/usr/bin/env python3
"""Share Liana Silver Knight's edited mount mask with matching cavalry art."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MASK_FILE = ROOT / "editor/ai_mount_masks.json"
AI_DIR = ROOT / "editor/static/ai-class-sprites"
ROM_DIR = ROOT / "editor/static/class-sprites/commanders"
OUTPUT_DIR = (
    ROOT / "assets/class-sprites/source/latest/rom-mount-color-variants-v1"
)
MASK_GROUPS = {
    # Elwin's infantry-sized head uses its separately edited Highlander mount
    # mask for the matching Knight Master and Royal Knight ROM geometry.
    "1:0C": ("1:1B", "1:29"),
    # The manually edited Liana Silver Knight horse coordinates align with
    # the remaining stock cavalry layouts. Identity intersections are still
    # protected by the aggregate builder.
    "2:1D": (
        "2:19",
        "3:19",
        "3:1D",
        "4:19",
        "4:1D",
        "5:19",
        "6:0C",
        "6:19",
        "6:1B",
        "6:1D",
        "6:29",
        "7:19",
        "7:1D",
        "8:0C",
        "8:19",
        "8:1B",
        "9:0C",
        "9:19",
        "9:1B",
        "9:1D",
        "10:19",
    ),
    # Lester's stock Serpent Knight/Lord/Master geometry is byte-identical.
    # The freshly edited Serpent Lord mask can therefore protect the same
    # rider and isolate the mount on all three tiers.
    "9:1F": ("9:10", "9:2A"),
}

DRAGON_KEYS = ((4, 0x1E), (4, 0x24), (6, 0x1E), (7, 0x1E), (7, 0x24))


def build_comparison_and_report(
    masks: dict[str, list[list[int]]],
) -> list[dict[str, object]]:
    from tools.build_ai_class_sprite_assets import MOUNT_COLOR_VARIANTS

    keys = [
        (commander_id, class_id, "mount")
        for commander_id, class_id in sorted(MOUNT_COLOR_VARIANTS)
    ] + [
        (commander_id, class_id, "dragon")
        for commander_id, class_id in DRAGON_KEYS
    ]
    reports: list[dict[str, object]] = []
    cards: list[tuple[str, Image.Image]] = []
    for commander_id, class_id, kind in keys:
        final = Image.open(
            AI_DIR / str(commander_id) / f"{class_id:02X}.png"
        ).convert("RGBA")
        original = Image.open(
            ROM_DIR / str(commander_id) / f"{class_id:02X}-p1.png"
        ).convert("RGBA")
        changed = {
            (x, y)
            for y in range(16)
            for x in range(16)
            if final.getpixel((x, y)) != original.getpixel((x, y))
        }
        white_changed = {
            point
            for point in changed
            if original.getpixel(point) == (255, 255, 255, 255)
        }
        mask = {
            tuple(point)
            for point in masks.get(f"{commander_id}:{class_id:02X}", [])
        }
        outside_mask = changed - mask if kind == "mount" else set()
        alpha_match = (
            final.getchannel("A").tobytes()
            == original.getchannel("A").tobytes()
        )
        accepted = (
            alpha_match
            and not white_changed
            and (kind == "dragon" or not outside_mask)
            and bool(changed)
        )
        if not accepted:
            raise ValueError(
                f"invalid ROM {kind} recolor {commander_id}:{class_id:02X}"
            )
        reports.append({
            "commander_id": commander_id,
            "class_id": f"{class_id:02X}",
            "kind": kind,
            "alpha_matches_rom": alpha_match,
            "changed_pixel_count": len(changed),
            "changed_outside_mount_mask": len(outside_mask),
            "white_weapon_pixels_changed": len(white_changed),
            "accepted": True,
        })
        cards.append((f"{commander_id:02d}-{class_id:02X} {kind}", final))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    columns = 6
    card_width = 196
    card_height = 224
    rows = (len(cards) + columns - 1) // columns
    canvas = Image.new(
        "RGB", (columns * card_width, rows * card_height), (28, 28, 32)
    )
    font_path = Path(
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"
    )
    font = (
        ImageFont.truetype(str(font_path), 13)
        if font_path.is_file()
        else ImageFont.load_default()
    )
    draw = ImageDraw.Draw(canvas)
    for index, (label, sprite) in enumerate(cards):
        x = (index % columns) * card_width
        y = (index // columns) * card_height
        draw.text((x + 8, y + 7), label, fill=(245, 245, 245), font=font)
        backdrop = Image.new("RGBA", (16, 16), (52, 52, 58, 255))
        backdrop.alpha_composite(sprite)
        preview = backdrop.convert("RGB").resize(
            (192, 192), Image.Resampling.NEAREST
        )
        canvas.paste(preview, (x + 2, y + 30))
    canvas.save(
        OUTPUT_DIR / "all-rom-mount-and-dragon-variants.png",
        optimize=True,
    )
    (OUTPUT_DIR / "validation-report.json").write_text(
        json.dumps(
            {"version": 1, "all_accepted": True, "classes": reports},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return reports


def main() -> None:
    document = json.loads(MASK_FILE.read_text(encoding="utf-8"))
    if document.get("version") != 1:
        raise ValueError("unsupported mount-mask version")
    masks = document["masks"]
    reports = []
    for source_key, target_keys in MASK_GROUPS.items():
        source = masks[source_key]
        for target in target_keys:
            masks[target] = [point.copy() for point in source]
        reports.append({
            "source": source_key,
            "pixel_count": len(source),
            "targets": list(target_keys),
        })
    temporary = MASK_FILE.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(MASK_FILE)
    validation = build_comparison_and_report(masks)
    print(
        json.dumps(
            {"mask_groups": reports, "validated_classes": len(validation)},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
