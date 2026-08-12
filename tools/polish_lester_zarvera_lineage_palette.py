#!/usr/bin/env python3
"""Link Lester Zarvera's palette to his preceding Archmage class."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil
import sys
import time

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.pillow_compat import flattened_image_data  # noqa: E402


SOURCE_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/shared-keith-wizard-new-classes-v1"
)
SOURCE = SOURCE_ROOT / "logical16/09-26.png"
PREVIEW = SOURCE_ROOT / "previews/09-26.png"
LIVE_ROOT = ROOT / "editor/static/ai-class-sprites"
LIVE = LIVE_ROOT / "9/26.png"
SOURCE_CELL = LIVE_ROOT / "source-cells/9-26.png"
MANIFEST = LIVE_ROOT / "manifest.json"
OVERRIDES = ROOT / "editor/ai_class_design_overrides.json"
ASSET_VERSION = "liana-lana-healer-shared-v106"

# Current green ramp -> colors already established in Lester Archmage 9:14.
COLOR_MAP = {
    (36, 73, 0, 255): (146, 0, 36, 255),
    (73, 146, 36, 255): (36, 73, 219, 255),
    (182, 219, 109, 255): (255, 182, 36, 255),
}


def flat_pixels(image: Image.Image) -> list[list[int]]:
    return [list(color) for color in flattened_image_data(image)]


def palette(image: Image.Image) -> list[str]:
    counts = Counter(
        color for color in flattened_image_data(image) if color[3]
    )
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common()
    ]


def write_contact(reports: list[dict[str, object]]) -> None:
    columns = 6
    card_width, card_height = 230, 275
    rows = (len(reports) + columns - 1) // columns
    canvas = Image.new(
        "RGB",
        (columns * card_width, rows * card_height),
        (18, 18, 18),
    )
    draw = ImageDraw.Draw(canvas)
    font_path = Path(
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"
    )
    font = (
        ImageFont.truetype(str(font_path), 13)
        if font_path.is_file()
        else ImageFont.load_default()
    )
    for index, row in enumerate(reports):
        x = index % columns * card_width
        y = index // columns * card_height
        draw.rectangle(
            (x + 4, y + 4, x + card_width - 5, y + card_height - 5),
            outline=(70, 175, 90),
            width=2,
        )
        draw.text(
            (x + 10, y + 9),
            f"{row['commander_id']}:{row['class_id']} {row['palette_name']}",
            fill="white",
            font=font,
        )
        image = Image.open(SOURCE_ROOT / row["file"]).convert("RGB")
        canvas.paste(
            image.resize((208, 208), Image.Resampling.NEAREST),
            (x + 11, y + 44),
        )
        draw.text(
            (x + 10, y + 254),
            (
                f"face {row['identity_matches']}/"
                f"{row['identity_visible']} "
                f"colors {row['visible_color_count']}"
            ),
            fill=(190, 200, 190),
            font=font,
        )
    canvas.save(
        SOURCE_ROOT / "all-keith-wizard-derived-classes.png",
        optimize=True,
    )


def main() -> int:
    previous = SOURCE_ROOT / "previous/09-26-before-archmage-palette.png"
    previous.parent.mkdir(parents=True, exist_ok=True)
    if not previous.is_file():
        shutil.copy2(SOURCE, previous)

    result = Image.open(SOURCE).convert("RGBA")
    changed = 0
    for y in range(16):
        for x in range(16):
            color = result.getpixel((x, y))
            if color in COLOR_MAP:
                result.putpixel((x, y), COLOR_MAP[color])
                changed += 1
    colors = palette(result)
    expected = {
        (146, 0, 36, 255),
        (36, 73, 219, 255),
        (255, 182, 36, 255),
    }
    if changed == 0 and not expected.issubset(
        set(flattened_image_data(result))
    ):
        raise ValueError("Lester Zarvera lineage colors were not found")
    if len(colors) > 15:
        raise ValueError(f"Lester Zarvera has {len(colors)} visible colors")

    result.save(SOURCE, optimize=True)
    result.save(LIVE, optimize=True)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    enlarged = result.resize((512, 512), Image.Resampling.NEAREST)
    enlarged.save(PREVIEW, optimize=True)
    enlarged.save(SOURCE_CELL, optimize=True)

    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    revision = time.time_ns()
    override = overrides["designs"].get("9:26")
    if override is not None:
        override["revision"] = revision
        override["pixels"] = flat_pixels(result)
    OVERRIDES.write_text(
        json.dumps(overrides, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["asset_version"] = ASSET_VERSION
    row = manifest["commanders"]["9"]["classes"][str(0x26)]
    row["pixel_palette"] = colors[:15]
    row["source_palette"] = colors[:6]
    if override is not None:
        row["design_revision"] = revision
    marker = (
        "·레스터 메이지→아크메이지 계보의 진홍 그림자·"
        "왕청색 로브·금색 강조로 상위직 색감 연결"
    )
    if marker not in row.get("feature", ""):
        row["feature"] = row.get("feature", "") + marker
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    report_path = SOURCE_ROOT / "validation-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report_row = next(
        item
        for item in report["classes"]
        if int(item["commander_id"]) == 9
        and int(item["class_id"], 16) == 0x26
    )
    report_row["palette_name"] = "아크메이지 연계 적·청·금 자베러"
    report_row["palette"] = colors
    report_row["visible_color_count"] = len(colors)
    report_row["accepted"] = len(colors) <= 15
    report["all_accepted"] = all(
        bool(item["accepted"]) for item in report["classes"]
    )
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_contact(report["classes"])

    print(
        json.dumps(
            {
                "target": "9:26",
                "changed_pixels": changed,
                "visible_colors": len(colors),
                "asset_version": ASSET_VERSION,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
