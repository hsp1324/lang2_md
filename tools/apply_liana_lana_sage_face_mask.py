#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import protected_eye_points
from tools.build_class_sprite_assets import (
    DEFAULT_ROM,
    commander_sprite_map,
    render_sprite,
)
from tools.build_liana_lana_native16_assets import visible_palette
from tools.build_liana_lana_strict16_candidates import (
    OUTPUT_ROOT,
    RESAMPLING,
    SELECTED_CANDIDATES,
    write_preview,
)

MASK_PATH = ROOT / "editor/ai_identity_masks.json"


def comparison_sheet() -> None:
    comparison = Image.new(
        "RGB",
        (860, 55 + len(SELECTED_CANDIDATES) * 270),
        (238, 238, 238),
    )
    draw = ImageDraw.Draw(comparison)
    draw.text(
        (12, 16),
        "selected strict-grid AI | Liana red native16 | Lana blue native16",
        fill=(24, 24, 24),
    )
    for index, class_id in enumerate(SELECTED_CANDIDATES):
        class_text = f"{class_id:02X}"
        y = 55 + index * 270
        draw.text((8, y + 115), class_text, fill=(24, 24, 24))
        candidate = Image.open(
            OUTPUT_ROOT / "selected-sources" / f"{class_text}.png"
        ).convert("RGB")
        candidate.thumbnail((240, 240), RESAMPLING.NEAREST)
        red = Image.open(
            OUTPUT_ROOT / "previews-red" / f"{class_text}.png"
        ).convert("RGB")
        blue = Image.open(
            OUTPUT_ROOT / "previews-blue" / f"{class_text}.png"
        ).convert("RGB")
        comparison.paste(candidate, (55, y + 10))
        comparison.paste(red, (315, y + 10))
        comparison.paste(blue, (585, y + 10))
    comparison.save(
        OUTPUT_ROOT / "strict16-ai-and-native16-comparison.png",
        optimize=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply the saved Liana Sage face mask to every Liana/Lana "
            "native16 class without changing equipment pixels"
        )
    )
    parser.add_argument(
        "--baseline-root",
        type=Path,
        help=(
            "optional snapshot containing native16-red/native16-blue; "
            "pixels outside the face are restored byte-exactly from it"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    masks = json.loads(MASK_PATH.read_text(encoding="utf-8"))["masks"]
    face_points = {
        tuple(point)
        for point in masks["2:18"]
    }
    if len(face_points) != 82:
        raise ValueError(
            "expected the latest Liana Sage face mask to contain 82 pixels"
        )

    rom = DEFAULT_ROM.read_bytes()
    rows: list[dict[str, object]] = []
    paired_images: dict[int, dict[int, Image.Image]] = {2: {}, 3: {}}
    for commander_id, color_name in ((2, "red"), (3, "blue")):
        sprite_map = commander_sprite_map(rom, commander_id)
        source_dir = OUTPUT_ROOT / f"native16-{color_name}"
        baseline_dir = (
            args.baseline_root / f"native16-{color_name}"
            if args.baseline_root is not None
            else source_dir
        )
        for class_id in SELECTED_CANDIDATES:
            class_text = f"{class_id:02X}"
            source_path = source_dir / f"{class_text}.png"
            before = Image.open(
                baseline_dir / f"{class_text}.png"
            ).convert("RGBA")
            original = render_sprite(
                rom,
                sprite_map[class_id],
                1,
            )
            effective_points = (
                face_points | protected_eye_points(original)
            )

            result = before.copy()
            for point in effective_points:
                result.putpixel(point, original.getpixel(point))
            if len(visible_palette(result)) > 15:
                raise ValueError(
                    f"{commander_id}:{class_text} exceeds 4bpp after "
                    "face-only restoration"
                )
            result.save(source_path, optimize=True)
            write_preview(
                result,
                OUTPUT_ROOT
                / f"previews-{color_name}"
                / f"{class_text}.png",
            )
            paired_images[commander_id][class_id] = result
            rows.append(
                {
                    "commander_id": commander_id,
                    "class_id": class_text,
                    "face_exact": all(
                        result.getpixel(point)
                        == original.getpixel(point)
                        for point in effective_points
                    ),
                    "outside_face_changes": sum(
                        result.getpixel((x, y))
                        != before.getpixel((x, y))
                        for y in range(16)
                        for x in range(16)
                        if (x, y) not in effective_points
                    ),
                    "visible_colors": len(visible_palette(result)),
                }
            )

    all_pair_alpha_equal = all(
        paired_images[2][class_id].getchannel("A").tobytes()
        == paired_images[3][class_id].getchannel("A").tobytes()
        for class_id in SELECTED_CANDIDATES
    )
    report = {
        "version": 1,
        "canonical_mask": "2:18",
        "identity_pixel_count": len(face_points),
        "mode": (
            "face-only restoration from each class ROM original; every "
            "pixel outside the saved Liana Sage mask is preserved from "
            "the selected baseline"
        ),
        "classes": rows,
        "all_face_exact": all(row["face_exact"] for row in rows),
        "all_equipment_unchanged": all(
            row["outside_face_changes"] == 0 for row in rows
        ),
        "all_4bpp": all(
            row["visible_colors"] <= 15 for row in rows
        ),
        "all_pair_alpha_equal": all_pair_alpha_equal,
    }
    (OUTPUT_ROOT / "sage-face-refresh-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    comparison_sheet()
    if not all(
        (
            report["all_face_exact"],
            report["all_equipment_unchanged"],
            report["all_4bpp"],
            report["all_pair_alpha_equal"],
        )
    ):
        raise ValueError("Liana/Lana Sage face refresh validation failed")
    print(
        OUTPUT_ROOT,
        len(rows),
        "face-only Liana/Lana sprites",
    )


if __name__ == "__main__":
    main()
