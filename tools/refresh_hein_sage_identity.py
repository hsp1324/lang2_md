#!/usr/bin/env python3
"""Reapply Hein Sage's latest saved identity mask without changing equipment."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
COMMANDER_ID = 5
CLASS_ID = 0x18
KEY = "5:18"
LIVE = ROOT / "editor/static/ai-class-sprites/5/18.png"
ROM = ROOT / "editor/static/class-sprites/commanders/5/18-p1.png"
MASKS = ROOT / "editor/ai_identity_masks.json"
MANIFEST = ROOT / "editor/static/ai-class-sprites/manifest.json"
SOURCE = ROOT / "docs/assets/ai-class-source/latest/shared-new-classes-v2-refined"
SAMPLE = ROOT / "docs/assets/ai-class-source/latest/sample-class-variants-v4-free-five/05-hein-18-sage"
TRANSPARENT = (0, 0, 0, 0)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def luminance(color: tuple[int, int, int, int]) -> float:
    return 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]


def palette(image: Image.Image) -> list[str]:
    counts = Counter(c for c in image.get_flattened_data() if c[3])
    return ["#%02x%02x%02x" % color[:3] for color, _ in counts.most_common()]


def limit_palette(
    image: Image.Image,
    original: Image.Image,
    points: set[tuple[int, int]],
) -> Image.Image:
    result = image.copy().convert("RGBA")
    identity_colors = {
        original.getpixel(point)
        for point in points
        if original.getpixel(point)[3]
    }
    colors = {color for color in result.get_flattened_data() if color[3]}
    if len(colors) <= 15:
        return result
    counts = Counter(
        result.getpixel((x, y))
        for y in range(16)
        for x in range(16)
        if (x, y) not in points and result.getpixel((x, y))[3]
    )
    allowed = list(identity_colors)
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


def expanded_points(
    points: set[tuple[int, int]], image: Image.Image
) -> set[tuple[int, int]]:
    result = set(points)
    for x, y in points:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                point = (x + dx, y + dy)
                if point in result or not (0 <= point[0] < 16 and 0 <= point[1] < 16):
                    continue
                color = image.getpixel(point)
                if color[3] and luminance(color) <= 112:
                    result.add(point)
    return result


def main() -> None:
    saved = json.loads(MASKS.read_text(encoding="utf-8"))["masks"].get(KEY, [])
    if not saved:
        raise ValueError("Hein Sage 5:18 has no saved identity mask")
    points = {tuple(point) for point in saved}
    current = Image.open(LIVE).convert("RGBA")
    original = Image.open(ROM).convert("RGBA")
    previous_dir = SOURCE / "previous"
    previous_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LIVE, previous_dir / "05-18-before-69px-mask.png")
    result = current.copy()
    for point in points:
        if original.getpixel(point)[3]:
            result.putpixel(point, original.getpixel(point))
    result = limit_palette(result, original, points)
    visible_colors = palette(result)
    visible_points = {point for point in points if original.getpixel(point)[3]}
    matches = sum(result.getpixel(point) == original.getpixel(point) for point in visible_points)
    if matches != len(visible_points) or len(visible_colors) > 15:
        raise ValueError("Hein Sage identity refresh validation failed")

    result.save(LIVE, optimize=True)
    result.save(SOURCE / "logical16/05-18.png", optimize=True)
    result.resize((512, 512), Image.Resampling.NEAREST).save(
        SOURCE / "previews/05-18.png", optimize=True
    )
    result.resize((512, 512), Image.Resampling.NEAREST).save(
        ROOT / "editor/static/ai-class-sprites/source-cells/5-18.png", optimize=True
    )

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    row = manifest["commanders"]["5"]["classes"][str(CLASS_ID)]
    row["identity_lock_points"] = [list(point) for point in sorted(points)]
    row["identity_mask_pending_rebuild"] = False
    row["pixel_palette"] = visible_colors
    row["changed_pixel_count"] = sum(
        result.getpixel((x, y)) != original.getpixel((x, y))
        for y in range(16)
        for x in range(16)
    )
    marker = "·사용자 재저장 헤인 세이지 69픽셀 얼굴 마스크 복원"
    if marker not in row.get("feature", ""):
        row["feature"] = row.get("feature", "") + marker
    write_json(MANIFEST, manifest)

    report_path = SOURCE / "validation-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    for report_row in report["classes"]:
        if report_row["commander_id"] == 5 and report_row["class_id"] == "18":
            report_row.update(
                {
                    "identity_source": "custom-69px-refresh",
                    "identity_match": matches,
                    "identity_pixel_count": len(visible_points),
                    "mask_pixel_count": len(points),
                    "visible_color_count": len(visible_colors),
                    "palette": visible_colors,
                    "accepted": True,
                }
            )
    report["all_accepted"] = all(item["accepted"] for item in report["classes"])
    write_json(report_path, report)

    expanded = expanded_points(points, result)
    identity = Image.new("RGBA", (16, 16), TRANSPARENT)
    for point in expanded:
        identity.putpixel(point, result.getpixel(point))
    identity.save(SAMPLE / "references/identity-with-dark-boundary16.png", optimize=True)
    identity.resize((32, 32), Image.Resampling.NEAREST).save(
        SAMPLE / "references/identity-with-dark-boundary-32x.png", optimize=True
    )
    write_json(
        SAMPLE / "references/identity-mask-expanded.json",
        {
            "commander_id": 5,
            "class_id": "18",
            "points": [list(point) for point in sorted(expanded)],
            "pixel_count": len(expanded),
            "saved_mask_pixel_count": len(points),
        },
    )
    write_json(
        SOURCE / "hein-sage-mask-refresh.json",
        {
            "saved_mask_pixels": len(points),
            "expanded_sample_identity_pixels": len(expanded),
            "visible_identity_matches": matches,
            "visible_identity_pixels": len(visible_points),
            "visible_color_count": len(visible_colors),
            "accepted": True,
        },
    )
    print(
        f"refreshed Hein Sage: mask {len(points)}, expanded {len(expanded)}, "
        f"identity {matches}/{len(visible_points)}, colors {len(visible_colors)}"
    )


if __name__ == "__main__":
    main()
