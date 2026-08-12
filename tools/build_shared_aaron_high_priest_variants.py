#!/usr/bin/env python3
"""Capture and share Aaron's latest hand-edited High Priest design."""

from __future__ import annotations

import argparse
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


OUTPUT = ROOT / "assets/class-sprites/source/latest/shared-high-priest-aaron-v1"
MASTER = OUTPUT / "master/08-16-user-edited.png"
LIVE = ROOT / "editor/static/ai-class-sprites"
MANIFEST = LIVE / "manifest.json"
OVERRIDES = ROOT / "editor/ai_class_design_overrides.json"
CLASS_ID = 0x16
TARGETS = (2, 3, 5, 7, 8, 10)
TRANSPARENT = (0, 0, 0, 0)

MASTER_GOLD_MAIN = (255, 219, 0, 255)
MASTER_GOLD_DARK = (255, 182, 0, 255)
MASTER_BLUE_MAIN = (36, 73, 219, 255)
MASTER_BLUE_LIGHT = (109, 182, 255, 255)

# Only Aaron's four garment-role colors change.  Skin, hair, white/silver
# vestments and the dark separating outline stay material-consistent.
SCHEMES = {
    2: {
        MASTER_GOLD_MAIN: (219, 0, 0, 255),
        MASTER_GOLD_DARK: (109, 0, 0, 255),
        MASTER_BLUE_MAIN: (255, 182, 0, 255),
        MASTER_BLUE_LIGHT: (255, 255, 109, 255),
    },
    3: {
        MASTER_GOLD_MAIN: (0, 73, 219, 255),
        MASTER_GOLD_DARK: (0, 0, 109, 255),
        MASTER_BLUE_MAIN: (73, 109, 255, 255),
        MASTER_BLUE_LIGHT: (109, 219, 255, 255),
    },
    5: {
        MASTER_GOLD_MAIN: (36, 146, 36, 255),
        MASTER_GOLD_DARK: (36, 73, 0, 255),
        MASTER_BLUE_MAIN: (109, 182, 73, 255),
        MASTER_BLUE_LIGHT: (182, 219, 146, 255),
    },
    7: {
        MASTER_GOLD_MAIN: (0, 146, 146, 255),
        MASTER_GOLD_DARK: (0, 73, 73, 255),
        MASTER_BLUE_MAIN: (0, 73, 219, 255),
        MASTER_BLUE_LIGHT: (109, 219, 255, 255),
    },
    8: {},
    10: {
        MASTER_GOLD_MAIN: (146, 36, 182, 255),
        MASTER_GOLD_DARK: (73, 0, 109, 255),
        MASTER_BLUE_MAIN: (182, 109, 219, 255),
        MASTER_BLUE_LIGHT: (219, 182, 255, 255),
    },
}


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def flat_pixels(image: Image.Image) -> list[list[int]]:
    return [
        list(color)
        for color in flattened_image_data(image.convert("RGBA"))
    ]


def palette(image: Image.Image) -> list[str]:
    counts = Counter(
        color
        for color in flattened_image_data(image.convert("RGBA"))
        if color[3]
    )
    return ["#%02x%02x%02x" % color[:3] for color, _ in counts.most_common()]


def capture() -> None:
    for child in ("master", "logical16", "previews", "previous", "references"):
        (OUTPUT / child).mkdir(parents=True, exist_ok=True)
    shutil.copy2(LIVE / "8/16.png", MASTER)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    masks = {}
    for commander_id in TARGETS:
        source = LIVE / str(commander_id) / "16.png"
        shutil.copy2(source, OUTPUT / f"previous/{commander_id:02d}-16.png")
        shutil.copy2(source, OUTPUT / f"references/{commander_id:02d}-identity-source.png")
        row = manifest["commanders"][str(commander_id)]["classes"][str(CLASS_ID)]
        masks[str(commander_id)] = row["identity_lock_points"]
    write_json(
        OUTPUT / "identity-points.json",
        {
            "class_id": "16",
            "master": "8:16",
            "points": masks,
        },
    )
    write_json(
        OUTPUT / "capture.json",
        {
            "captured_master": "editor/static/ai-class-sprites/8/16.png",
            "master_file": "master/08-16-user-edited.png",
            "master_palette": palette(Image.open(MASTER).convert("RGBA")),
            "targets": list(TARGETS),
        },
    )
    print("captured Aaron 8:16 and six pre-application references")


def make_variant(
    master: Image.Image,
    master_points: set[tuple[int, int]],
    target: Image.Image,
    target_points: set[tuple[int, int]],
    commander_id: int,
) -> Image.Image:
    if commander_id == 8:
        return master.copy()
    result = master.copy()
    identity_union = master_points | target_points
    for point in master_points:
        result.putpixel(point, TRANSPARENT)
    mapping = SCHEMES[commander_id]
    for y in range(16):
        for x in range(16):
            point = (x, y)
            if point in identity_union:
                result.putpixel(point, target.getpixel(point))
                continue
            color = result.getpixel(point)
            if color in mapping:
                result.putpixel(point, mapping[color])
    return result


def validation(
    result: Image.Image,
    identity: Image.Image,
    points: set[tuple[int, int]],
) -> dict[str, object]:
    colors = palette(result)
    visible_points = {point for point in points if identity.getpixel(point)[3]}
    matches = sum(
        result.getpixel(point) == identity.getpixel(point)
        for point in visible_points
    )
    empty_rows = [
        y for y in range(16)
        if not any(result.getpixel((x, y))[3] for x in range(16))
    ]
    empty_columns = [
        x for x in range(16)
        if not any(result.getpixel((x, y))[3] for y in range(16))
    ]
    return {
        "identity_matches": matches,
        "identity_visible": len(visible_points),
        "visible_color_count": len(colors),
        "palette": colors,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "accepted": (
            matches == len(visible_points)
            and len(colors) <= 15
            and not empty_rows
            and not empty_columns
        ),
    }


def font() -> ImageFont.ImageFont:
    path = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc")
    return ImageFont.truetype(str(path), 14) if path.is_file() else ImageFont.load_default()


def comparison(reports: list[dict[str, object]]) -> None:
    card_width, card_height = 250, 300
    canvas = Image.new("RGB", (card_width * len(reports), card_height), (18, 18, 18))
    draw = ImageDraw.Draw(canvas)
    label_font = font()
    for index, row in enumerate(reports):
        x = index * card_width
        outline = (70, 175, 90) if row["accepted"] else (220, 70, 70)
        draw.rectangle((x + 5, 5, x + card_width - 6, card_height - 6), outline=outline, width=2)
        draw.text((x + 12, 12), f"{row['commander_id']:02d} HIGH PRIEST", fill="white", font=label_font)
        draw.text(
            (x + 12, 32),
            f"face {row['identity_matches']}/{row['identity_visible']}  colors {row['visible_color_count']}",
            fill=(190, 200, 190),
            font=label_font,
        )
        image = Image.open(OUTPUT / row["file"]).convert("RGB").resize((224, 224), Image.Resampling.NEAREST)
        canvas.paste(image, (x + 13, 62))
    canvas.save(OUTPUT / "all-high-priest-variants.png", optimize=True)


def build(apply_live: bool) -> None:
    if not MASTER.is_file():
        raise FileNotFoundError("run capture before build")
    master = Image.open(MASTER).convert("RGBA")
    metadata = json.loads((OUTPUT / "identity-points.json").read_text(encoding="utf-8"))
    points_by_commander = {
        int(key): {tuple(point) for point in points}
        for key, points in metadata["points"].items()
    }
    master_points = points_by_commander[8]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    reports = []
    for sequence, commander_id in enumerate(TARGETS):
        identity_path = OUTPUT / f"references/{commander_id:02d}-identity-source.png"
        identity = Image.open(identity_path).convert("RGBA")
        result = make_variant(
            master,
            master_points,
            identity,
            points_by_commander[commander_id],
            commander_id,
        )
        result_path = OUTPUT / f"logical16/{commander_id:02d}-16.png"
        result.save(result_path, optimize=True)
        result.resize((512, 512), Image.Resampling.NEAREST).save(
            OUTPUT / f"previews/{commander_id:02d}-16.png", optimize=True
        )
        checked = validation(result, identity, points_by_commander[commander_id])
        if not checked["accepted"]:
            raise ValueError(f"{commander_id}:16 validation failed: {checked}")
        if apply_live:
            live_path = LIVE / str(commander_id) / "16.png"
            result.save(live_path, optimize=True)
            result.resize((512, 512), Image.Resampling.NEAREST).save(
                LIVE / f"source-cells/{commander_id}-16.png", optimize=True
            )
            if commander_id != 8:
                revision = time.time_ns() + sequence
                overrides["designs"][f"{commander_id}:16"] = {
                    "revision": revision,
                    "pixels": flat_pixels(result),
                    "base_pixels": flat_pixels(identity),
                }
                row = manifest["commanders"][str(commander_id)]["classes"][str(CLASS_ID)]
                row["design_override"] = True
                row["design_revision"] = revision
                row["design_override_superseded"] = False
                row["superseded_design_revision"] = 0
                row["pixel_palette"] = checked["palette"]
                row["source_kind"] = "아론 사용자 편집 하이프리스트 공통 16×16 템플릿"
                row["source_position"] = f"latest/shared-high-priest-aaron-v1/logical16/{commander_id:02d}-16.png"
                marker = "·아론 사용자 편집 하이프리스트 장비 좌표·캐릭터별 전용 색감 적용"
                if marker not in row.get("feature", ""):
                    row["feature"] = row.get("feature", "") + marker
        reports.append(
            {
                "commander_id": commander_id,
                "file": f"logical16/{commander_id:02d}-16.png",
                "scheme": {
                    "#%02x%02x%02x" % source[:3]: "#%02x%02x%02x" % target[:3]
                    for source, target in SCHEMES[commander_id].items()
                },
                **checked,
            }
        )
    if apply_live:
        write_json(OVERRIDES, overrides)
        write_json(MANIFEST, manifest)
    comparison(reports)
    write_json(
        OUTPUT / "validation-report.json",
        {
            "master": "8:16",
            "master_file": "master/08-16-user-edited.png",
            "targets": list(TARGETS),
            "all_accepted": all(row["accepted"] for row in reports),
            "applied_live": apply_live,
            "classes": reports,
        },
    )
    print(f"built {len(reports)} Aaron High Priest variants; live={apply_live}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("capture", "build", "apply"))
    args = parser.parse_args()
    if args.action == "capture":
        capture()
    else:
        build(apply_live=args.action == "apply")


if __name__ == "__main__":
    main()
