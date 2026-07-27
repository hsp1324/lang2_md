#!/usr/bin/env python3
"""Build one AI-source/16x16/ROM comparison PNG per commander."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AI_OUTPUT = ROOT / "editor/static/ai-class-sprites"
CHARACTER_AI_ROOT = (
    ROOT / "docs/assets/ai-class-source/character-ai-v3"
)
COMMANDER_SLUGS = {
    1: "elwin",
    2: "liana",
    3: "lana",
    4: "sherry",
    5: "hein",
    6: "scott",
    7: "keith",
    8: "aaron",
    9: "lester",
    10: "jessica",
}
BACKGROUND = (15, 17, 15, 255)
CARD_BACKGROUND = (29, 32, 29, 255)
LABEL = (229, 234, 226, 255)
MUTED = (151, 160, 149, 255)
AI_BORDER = (132, 84, 155, 255)
FINAL_BORDER = (213, 168, 77, 255)
ROM_BORDER = (78, 112, 84, 255)
RESAMPLING = getattr(Image, "Resampling", Image)


def paste_contained(
    canvas: Image.Image,
    source: Image.Image,
    box: tuple[int, int, int, int],
    *,
    resample: int,
) -> None:
    left, top, right, bottom = box
    available_width = right - left
    available_height = bottom - top
    image = source.convert("RGBA")
    scale = min(
        available_width / image.width,
        available_height / image.height,
    )
    image = image.resize(
        (
            max(1, round(image.width * scale)),
            max(1, round(image.height * scale)),
        ),
        resample,
    )
    x = left + (available_width - image.width) // 2
    y = top + (available_height - image.height) // 2
    canvas.alpha_composite(image, (x, y))


def draw_frame(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int, int],
) -> None:
    draw.rectangle(box, outline=color, width=2)


def write_character_comparison_sheets(
    manifest: dict[str, object],
    ai_output_dir: Path = DEFAULT_AI_OUTPUT,
) -> list[str]:
    output_paths: list[str] = []
    font = ImageFont.load_default()
    card_width = 570
    card_height = 230
    columns = 2
    margin = 24
    heading_height = 54
    for commander_id, slug in COMMANDER_SLUGS.items():
        commander = manifest["commanders"][str(commander_id)]
        rows = [
            row
            for row in commander["classes"].values()
            if row["redesigned"]
        ]
        rows.sort(key=lambda row: (row["tier"], row["class_id"]))
        row_count = math.ceil(len(rows) / columns)
        canvas = Image.new(
            "RGBA",
            (
                margin * 2 + card_width * columns,
                margin * 2 + heading_height + card_height * row_count,
            ),
            BACKGROUND,
        )
        draw = ImageDraw.Draw(canvas)
        draw.text(
            (margin, margin),
            (
                f"COMMANDER {commander_id:02d} {slug.upper()}  "
                "AI SOURCE -> FINAL 16x16 -> ROM"
            ),
            fill=LABEL,
            font=font,
        )
        draw.text(
            (margin, margin + 20),
            "Purple: generated source  Gold: converted  Green: original",
            fill=MUTED,
            font=font,
        )
        for index, row in enumerate(rows):
            column = index % columns
            card_row = index // columns
            left = margin + column * card_width
            top = margin + heading_height + card_row * card_height
            draw.rounded_rectangle(
                (
                    left + 4,
                    top + 4,
                    left + card_width - 8,
                    top + card_height - 8,
                ),
                radius=8,
                fill=CARD_BACKGROUND,
                outline=(62, 68, 61, 255),
                width=1,
            )
            class_id = int(row["class_id"])
            draw.text(
                (left + 16, top + 14),
                (
                    f"CLASS {class_id:02X}  "
                    f"mask {row['identity_lock_pixel_count']}px"
                ),
                fill=LABEL,
                font=font,
            )
            ai_box = (left + 16, top + 42, left + 216, top + 214)
            final_box = (
                left + 232,
                top + 64,
                left + 372,
                top + 204,
            )
            rom_box = (
                left + 406,
                top + 64,
                left + 546,
                top + 204,
            )
            draw_frame(draw, ai_box, AI_BORDER)
            draw_frame(draw, final_box, FINAL_BORDER)
            draw_frame(draw, rom_box, ROM_BORDER)
            source = Image.open(
                ai_output_dir / row["ai_source_cell_file"]
            )
            final = Image.open(ai_output_dir / row["file"])
            original = Image.open(
                ROOT
                / "editor/static/class-sprites/commanders"
                / str(commander_id)
                / f"{class_id:02X}-p1.png"
            )
            paste_contained(
                canvas,
                source,
                (
                    ai_box[0] + 4,
                    ai_box[1] + 4,
                    ai_box[2] - 4,
                    ai_box[3] - 4,
                ),
                resample=RESAMPLING.NEAREST,
            )
            paste_contained(
                canvas,
                final,
                (
                    final_box[0] + 6,
                    final_box[1] + 6,
                    final_box[2] - 6,
                    final_box[3] - 6,
                ),
                resample=RESAMPLING.NEAREST,
            )
            paste_contained(
                canvas,
                original,
                (
                    rom_box[0] + 6,
                    rom_box[1] + 6,
                    rom_box[2] - 6,
                    rom_box[3] - 6,
                ),
                resample=RESAMPLING.NEAREST,
            )
        output_path = (
            CHARACTER_AI_ROOT
            / slug
            / f"{slug}-ai-and-16x16.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert("RGB").save(output_path, optimize=True)
        output_paths.append(str(output_path.relative_to(ROOT)))
    return output_paths


def write_character_comparison_cards(
    manifest: dict[str, object],
    commander_id: int,
    output_dir: Path,
    ai_output_dir: Path = DEFAULT_AI_OUTPUT,
) -> list[str]:
    """Write one AI-source/final/ROM comparison PNG per redesigned class."""

    commander = manifest["commanders"][str(commander_id)]
    rows = [
        row
        for row in commander["classes"].values()
        if row["redesigned"]
    ]
    rows.sort(key=lambda row: (row["tier"], row["class_id"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    output_paths: list[str] = []
    for row in rows:
        class_id = int(row["class_id"])
        canvas = Image.new("RGBA", (900, 380), BACKGROUND)
        draw = ImageDraw.Draw(canvas)
        draw.text(
            (24, 20),
            (
                f"COMMANDER {commander_id:02d}  CLASS {class_id:02X}  "
                f"mask {row['identity_lock_pixel_count']}px"
            ),
            fill=LABEL,
            font=font,
        )
        draw.text(
            (24, 42),
            "AI EDIT SOURCE          FINAL 16x16          ORIGINAL ROM",
            fill=MUTED,
            font=font,
        )
        ai_box = (24, 70, 344, 358)
        final_box = (370, 104, 602, 336)
        rom_box = (642, 104, 874, 336)
        draw_frame(draw, ai_box, AI_BORDER)
        draw_frame(draw, final_box, FINAL_BORDER)
        draw_frame(draw, rom_box, ROM_BORDER)
        with Image.open(
            ai_output_dir / row["ai_source_cell_file"]
        ) as source:
            paste_contained(
                canvas,
                source,
                (
                    ai_box[0] + 6,
                    ai_box[1] + 6,
                    ai_box[2] - 6,
                    ai_box[3] - 6,
                ),
                resample=RESAMPLING.NEAREST,
            )
        with Image.open(ai_output_dir / row["file"]) as final:
            paste_contained(
                canvas,
                final,
                (
                    final_box[0] + 8,
                    final_box[1] + 8,
                    final_box[2] - 8,
                    final_box[3] - 8,
                ),
                resample=RESAMPLING.NEAREST,
            )
        original_path = (
            ROOT
            / "editor/static/class-sprites/commanders"
            / str(commander_id)
            / f"{class_id:02X}-p1.png"
        )
        with Image.open(original_path) as original:
            paste_contained(
                canvas,
                original,
                (
                    rom_box[0] + 8,
                    rom_box[1] + 8,
                    rom_box[2] - 8,
                    rom_box[3] - 8,
                ),
                resample=RESAMPLING.NEAREST,
            )
        output_path = output_dir / f"{class_id:02X}-ai-final-rom.png"
        canvas.convert("RGB").save(output_path, optimize=True)
        output_paths.append(str(output_path))
    return output_paths


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build per-commander AI and 16x16 comparison PNGs"
    )
    parser.add_argument(
        "--ai-output",
        type=Path,
        default=DEFAULT_AI_OUTPUT,
    )
    parser.add_argument(
        "--individual-commander",
        type=int,
        choices=sorted(COMMANDER_SLUGS),
        help="also write one comparison PNG per class for this commander",
    )
    parser.add_argument(
        "--individual-output",
        type=Path,
        help="directory for --individual-commander comparison PNGs",
    )
    args = parser.parse_args()
    manifest = json.loads(
        (args.ai_output / "manifest.json").read_text(encoding="utf-8")
    )
    for path in write_character_comparison_sheets(
        manifest,
        args.ai_output,
    ):
        print(path)
    if args.individual_commander is not None:
        output_dir = args.individual_output
        if output_dir is None:
            slug = COMMANDER_SLUGS[args.individual_commander]
            output_dir = CHARACTER_AI_ROOT / slug / "comparisons"
        for path in write_character_comparison_cards(
            manifest,
            args.individual_commander,
            output_dir,
            args.ai_output,
        ):
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
