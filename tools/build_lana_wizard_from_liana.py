#!/usr/bin/env python3
"""Restore Lana Wizard from Liana's approved Wizard shape and a blue ramp."""

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


OUTPUT = ROOT / "assets/class-sprites/source/latest/lana-wizard-liana-template-v1"
LIVE = ROOT / "editor/static/ai-class-sprites"
LIANA = LIVE / "2/15.png"
LANA = LIVE / "3/15.png"
LANA_ROM = ROOT / "editor/static/class-sprites/commanders/3/15-p1.png"
MASKS = ROOT / "editor/ai_identity_masks.json"
MANIFEST = LIVE / "manifest.json"
OVERRIDES = ROOT / "editor/ai_class_design_overrides.json"
TRANSPARENT = (0, 0, 0, 0)

COLOR_MAP = {
    (255, 36, 36, 255): (73, 109, 255, 255),
    (219, 0, 0, 255): (0, 73, 219, 255),
    (182, 0, 36, 255): (0, 36, 182, 255),
    (109, 0, 0, 255): (0, 0, 109, 255),
}


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def palette(image: Image.Image) -> list[str]:
    counts = Counter(c for c in flattened_image_data(image) if c[3])
    return ["#%02x%02x%02x" % color[:3] for color, _ in counts.most_common()]


def pixels(image: Image.Image) -> list[list[int]]:
    return [list(color) for color in flattened_image_data(image)]


def limit_palette(
    image: Image.Image,
    original: Image.Image,
    points: set[tuple[int, int]],
) -> Image.Image:
    result = image.copy().convert("RGBA")
    colors = {color for color in flattened_image_data(result) if color[3]}
    if len(colors) <= 15:
        return result
    locked = {original.getpixel(point) for point in points if original.getpixel(point)[3]}
    counts = Counter(
        result.getpixel((x, y))
        for y in range(16)
        for x in range(16)
        if (x, y) not in points and result.getpixel((x, y))[3]
    )
    allowed = list(locked)
    for color, _ in counts.most_common():
        if color not in allowed:
            allowed.append(color)
        if len(allowed) == 15:
            break
    for y in range(16):
        for x in range(16):
            point = (x, y)
            color = result.getpixel(point)
            if point in points or not color[3] or color in allowed:
                continue
            result.putpixel(
                point,
                min(
                    allowed,
                    key=lambda target: sum(
                        (color[channel] - target[channel]) ** 2
                        for channel in range(3)
                    ),
                ),
            )
    for point in points:
        if original.getpixel(point)[3]:
            result.putpixel(point, original.getpixel(point))
    return result


def font() -> ImageFont.ImageFont:
    path = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc")
    return ImageFont.truetype(str(path), 14) if path.is_file() else ImageFont.load_default()


def main() -> None:
    for child in ("master", "logical16", "previews", "previous", "references"):
        (OUTPUT / child).mkdir(parents=True, exist_ok=True)
    shutil.copy2(LIANA, OUTPUT / "master/02-15-liana-approved.png")
    previous_path = OUTPUT / "previous/03-15-before-restore.png"
    if not previous_path.is_file():
        shutil.copy2(LANA, previous_path)
    shutil.copy2(LANA_ROM, OUTPUT / "references/03-15-lana-rom-identity.png")

    mask_doc = json.loads(MASKS.read_text(encoding="utf-8"))["masks"]
    source_points = {tuple(point) for point in mask_doc.get("2:15", [])}
    target_points = {tuple(point) for point in mask_doc.get("3:15", [])}
    if not source_points or not target_points:
        raise ValueError("Liana/Lana Wizard masks must both be saved")

    source = Image.open(LIANA).convert("RGBA")
    original = Image.open(LANA_ROM).convert("RGBA")
    result = source.copy()
    for y in range(16):
        for x in range(16):
            point = (x, y)
            if (
                point not in target_points
                or not original.getpixel(point)[3]
            ):
                color = result.getpixel(point)
                if color in COLOR_MAP:
                    result.putpixel(point, COLOR_MAP[color])
    # Visible target identity wins. Transparent mask coordinates keep Liana's
    # approved equipment, matching the editor's equipment-priority behavior.
    for point in target_points:
        if original.getpixel(point)[3]:
            result.putpixel(point, original.getpixel(point))
    result = limit_palette(result, original, target_points)

    visible_points = {point for point in target_points if original.getpixel(point)[3]}
    matches = sum(result.getpixel(point) == original.getpixel(point) for point in visible_points)
    colors = palette(result)
    empty_rows = [y for y in range(16) if not any(result.getpixel((x, y))[3] for x in range(16))]
    empty_columns = [x for x in range(16) if not any(result.getpixel((x, y))[3] for y in range(16))]
    accepted = (
        matches == len(visible_points)
        and len(colors) <= 15
        and not empty_rows
        and not empty_columns
    )
    if not accepted:
        raise ValueError("Lana Wizard validation failed")

    logical = OUTPUT / "logical16/03-15.png"
    result.save(logical, optimize=True)
    result.resize((512, 512), Image.Resampling.NEAREST).save(
        OUTPUT / "previews/03-15.png", optimize=True
    )
    result.save(LANA, optimize=True)
    result.resize((512, 512), Image.Resampling.NEAREST).save(
        LIVE / "source-cells/3-15.png", optimize=True
    )

    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    revision = time.time_ns()
    before = Image.open(OUTPUT / "previous/03-15-before-restore.png").convert("RGBA")
    overrides["designs"]["3:15"] = {
        "revision": revision,
        "pixels": pixels(result),
        "base_pixels": pixels(before),
    }
    write_json(OVERRIDES, overrides)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    row = manifest["commanders"]["3"]["classes"][str(0x15)]
    row["identity_lock_points"] = [list(point) for point in sorted(target_points)]
    row["identity_mask_pending_rebuild"] = False
    row["design_override"] = True
    row["design_revision"] = revision
    row["design_override_superseded"] = False
    row["superseded_design_revision"] = 0
    row["pixel_palette"] = colors
    row["source_kind"] = "리아나 승인 위저드 장비 기반 라나 청색 위저드"
    row["source_position"] = "latest/lana-wizard-liana-template-v1/logical16/03-15.png"
    marker = "·리아나 위저드 장비 좌표 복원·라나 남청·파랑·하늘색 장비색"
    if marker not in row.get("feature", ""):
        row["feature"] = row.get("feature", "") + marker
    write_json(MANIFEST, manifest)

    canvas = Image.new("RGB", (768, 288), (18, 18, 18))
    draw = ImageDraw.Draw(canvas)
    label_font = font()
    items = (
        ("LIANA SOURCE", source),
        ("LANA BEFORE", before),
        ("LANA RESTORED", result),
    )
    for index, (label, image) in enumerate(items):
        x = index * 256
        draw.text((x + 10, 8), label, fill="white", font=label_font)
        canvas.paste(image.convert("RGB").resize((240, 240), Image.Resampling.NEAREST), (x + 8, 38))
    canvas.save(OUTPUT / "liana-source-lana-before-after.png", optimize=True)
    write_json(
        OUTPUT / "validation-report.json",
        {
            "source": "2:15 Liana Wizard current approved design",
            "target": "3:15 Lana Wizard",
            "source_mask_pixels": len(source_points),
            "target_mask_pixels": len(target_points),
            "identity_matches": matches,
            "identity_visible": len(visible_points),
            "visible_color_count": len(colors),
            "palette": colors,
            "empty_rows": empty_rows,
            "empty_columns": empty_columns,
            "accepted": accepted,
        },
    )
    print(
        f"restored Lana Wizard from Liana: identity {matches}/{len(visible_points)}, "
        f"colors {len(colors)}"
    )


if __name__ == "__main__":
    main()
