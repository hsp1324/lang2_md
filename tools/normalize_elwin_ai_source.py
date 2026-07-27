#!/usr/bin/env python3
"""Normalize a new Elwin imagegen result to an exact-head 16x16 source."""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (
    ELWIN_NATIVE_SOURCE_FILES,
    nearest_palette_color,
    quantize_16_color_rgba,
    remove_magenta_background,
)


GUIDE_DIR = (
    ROOT / "docs/assets/ai-class-source/elwin-head-ratio-guides-v2"
)
MASK_PATH = ROOT / "editor/ai_identity_masks.json"
MAGENTA = (255, 0, 255, 255)
RESAMPLING = getattr(Image, "Resampling", Image)
CLASS_LABELS = {
    0x04: "LORD",
    0x0B: "HIGH LORD",
    0x0C: "HIGHLANDER",
    0x12: "BISHOP",
    0x13: "MAGE",
    0x14: "ARCHMAGE",
    0x1A: "SWORDMASTER",
    0x1B: "KNIGHT MASTER",
    0x1D: "SILVER KNIGHT",
    0x22: "HERO",
}
CONSERVATIVE_MOUNT_EQUIPMENT_BOXES = {
    0x0C: (4, 8, 12, 12),
    0x1B: (4, 8, 13, 13),
}
HERO_SWORD_BODY_FILL_COPIES = (
    ((4, 8), (5, 9)),
    ((5, 8), (5, 9)),
    ((11, 8), (11, 9)),
    ((12, 8), (11, 9)),
    ((4, 9), (5, 9)),
    ((12, 9), (11, 9)),
    ((13, 10), (12, 10)),
    ((4, 14), (5, 14)),
    ((4, 15), (5, 15)),
    ((12, 15), (11, 15)),
)


def is_magenta(color: tuple[int, int, int, int]) -> bool:
    red, green, blue, _ = color
    return red >= 160 and blue >= 160 and green <= 96


def logical_reference(class_id: int) -> Image.Image:
    path = GUIDE_DIR / f"{class_id:02X}-original-full-ratio.png"
    return Image.open(path).convert("RGBA").resize(
        (16, 16),
        RESAMPLING.NEAREST,
    )


def identity_points(class_id: int) -> set[tuple[int, int]]:
    document = json.loads(MASK_PATH.read_text(encoding="utf-8"))
    return {
        tuple(point)
        for point in document["masks"][f"1:{class_id:02X}"]
    }


def sample_imagegen_result(path: Path) -> Image.Image:
    source = Image.open(path).convert("RGBA").resize(
        (16, 16),
        RESAMPLING.NEAREST,
    )
    return remove_magenta_background(source)


def prelock_identity_match(
    candidate: Image.Image,
    reference: Image.Image,
    points: set[tuple[int, int]],
) -> tuple[int, int]:
    palette = [
        color
        for _, color in (
            reference.getcolors(maxcolors=256) or []
        )
        if not is_magenta(color)
    ]
    matched = 0
    for point in points:
        expected = reference.getpixel(point)
        actual = candidate.getpixel(point)
        if is_magenta(expected):
            matched += actual[3] == 0
        elif actual[3] != 0:
            matched += (
                nearest_palette_color(actual, palette) == expected
            )
    return matched, len(points)


def lock_identity(
    candidate: Image.Image,
    reference: Image.Image,
    points: set[tuple[int, int]],
) -> Image.Image:
    result = candidate.copy()
    for point in points:
        color = reference.getpixel(point)
        result.putpixel(
            point,
            (0, 0, 0, 0) if is_magenta(color) else color,
        )
    return result


def preserve_original_mount_silhouette(
    candidate: Image.Image,
    reference: Image.Image,
    points: set[tuple[int, int]],
    equipment_box: tuple[int, int, int, int],
) -> tuple[Image.Image, int]:
    """Keep the ROM mount footprint and apply AI only to central equipment."""

    original = remove_magenta_background(reference)
    result = original.copy()
    left, top, right, bottom = equipment_box
    changed = 0
    for y in range(top, bottom):
        for x in range(left, right):
            point = (x, y)
            if point in points:
                continue
            original_color = original.getpixel(point)
            candidate_color = candidate.getpixel(point)
            if original_color[3] == 0 or candidate_color[3] == 0:
                continue
            if candidate_color != original_color:
                result.putpixel(point, candidate_color)
                changed += 1
    return result, changed


def broaden_hero_sword_body(
    candidate: Image.Image,
    points: set[tuple[int, int]],
) -> tuple[Image.Image, int]:
    """Broaden the accepted sword Hero without moving its hands or weapon."""

    result = candidate.copy()
    added = 0
    for destination, source in HERO_SWORD_BODY_FILL_COPIES:
        if destination in points:
            continue
        if result.getpixel(destination)[3] != 0:
            continue
        source_color = result.getpixel(source)
        if source_color[3] == 0:
            continue
        result.putpixel(destination, source_color)
        added += 1
    return result, added


def enforce_dual_sword_margins(
    candidate: Image.Image,
    points: set[tuple[int, int]],
) -> tuple[Image.Image, int, int]:
    """Keep both Swordmaster blades inside a full one-pixel side margin."""

    result = candidate.copy()
    cleared = 0
    for x in (0, 15):
        for y in range(7, 16):
            point = (x, y)
            if point in points or result.getpixel(point)[3] == 0:
                continue
            result.putpixel(point, (0, 0, 0, 0))
            cleared += 1
    highlighted = 0
    for point in ((2, 12), (13, 12)):
        if point in points or result.getpixel(point)[3] == 0:
            continue
        if result.getpixel(point) != (255, 255, 255, 255):
            result.putpixel(point, (255, 255, 255, 255))
            highlighted += 1
    return result, cleared, highlighted


def ensure_bottom_alignment(image: Image.Image) -> int:
    if any(image.getpixel((x, 15))[3] != 0 for x in range(16)):
        return 0
    added = 0
    for x in range(5, 11):
        color = image.getpixel((x, 14))
        if color[3] != 0:
            image.putpixel((x, 15), color)
            added += 1
    return added


def connected_body_pixels(
    image: Image.Image,
    points: set[tuple[int, int]],
) -> int:
    visible = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if image.getpixel((x, y))[3] != 0
    }
    starts = visible & points
    queue = deque(starts)
    reached = set(starts)
    while queue:
        x, y = queue.popleft()
        for offset_x, offset_y in (
            (-1, -1),
            (0, -1),
            (1, -1),
            (-1, 0),
            (1, 0),
            (-1, 1),
            (0, 1),
            (1, 1),
        ):
            neighbor = (x + offset_x, y + offset_y)
            if neighbor in visible and neighbor not in reached:
                reached.add(neighbor)
                queue.append(neighbor)
    return sum(
        point not in points and point[1] >= 7
        for point in reached
    )


def magenta_canvas(image: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", image.size, MAGENTA)
    canvas.alpha_composite(image)
    return canvas


def output_sheet_prefix(output_dir: Path) -> str:
    version = output_dir.name.rsplit("-", 1)[-1]
    return f"elwin-{version}"


def normalize(
    class_id: int,
    raw_path: Path,
    output_dir: Path,
    preserve_original_mounts: bool = False,
    broaden_hero_sword: bool = False,
    dual_sword_layout: bool = False,
) -> dict[str, object]:
    filename = ELWIN_NATIVE_SOURCE_FILES[class_id]
    reference = logical_reference(class_id)
    points = identity_points(class_id)
    raw_sampled = sample_imagegen_result(raw_path)
    matched, total = prelock_identity_match(
        raw_sampled,
        reference,
        points,
    )
    sampled = quantize_16_color_rgba(raw_sampled)
    conservative_mount = (
        preserve_original_mounts
        and class_id in CONSERVATIVE_MOUNT_EQUIPMENT_BOXES
    )
    equipment_pixels_from_ai = 0
    if conservative_mount:
        sampled, equipment_pixels_from_ai = (
            preserve_original_mount_silhouette(
                sampled,
                reference,
                points,
                CONSERVATIVE_MOUNT_EQUIPMENT_BOXES[class_id],
            )
        )
    hero_sword_body = broaden_hero_sword and class_id == 0x22
    hero_body_pixels_added = 0
    if hero_sword_body:
        sampled, hero_body_pixels_added = broaden_hero_sword_body(
            sampled,
            points,
        )
    dual_swordmaster = dual_sword_layout and class_id == 0x1A
    dual_sword_margin_pixels_cleared = 0
    dual_sword_blade_pixels_highlighted = 0
    if dual_swordmaster:
        (
            sampled,
            dual_sword_margin_pixels_cleared,
            dual_sword_blade_pixels_highlighted,
        ) = enforce_dual_sword_margins(sampled, points)
    locked = lock_identity(sampled, reference, points)
    grounded = ensure_bottom_alignment(locked)
    connected = connected_body_pixels(locked, points)
    left_sword_pixels = sum(
        locked.getpixel((x, y))[3] != 0
        for y in range(11, 15)
        for x in range(1, 5)
    )
    right_sword_pixels = sum(
        locked.getpixel((x, y))[3] != 0
        for y in range(11, 15)
        for x in range(11, 15)
    )

    logical_dir = output_dir / "logical16"
    logical_dir.mkdir(parents=True, exist_ok=True)
    logical = magenta_canvas(locked)
    logical.save(logical_dir / filename)
    logical.resize(
        (1024, 1024),
        RESAMPLING.NEAREST,
    ).save(output_dir / filename, optimize=True)

    return {
        "class_id": f"{class_id:02X}",
        "raw": str(raw_path),
        "source": str(output_dir / filename),
        "prelock_identity_match": matched,
        "identity_pixel_count": total,
        "prelock_identity_ratio": round(matched / total, 4),
        "locked_identity_match": total,
        "grounded_pixels_added": grounded,
        "connected_body_pixels": connected,
        "conservative_original_mount": conservative_mount,
        "equipment_pixels_from_ai": equipment_pixels_from_ai,
        "broadened_hero_sword_body": hero_sword_body,
        "hero_body_pixels_added": hero_body_pixels_added,
        "dual_sword_layout": dual_swordmaster,
        "dual_sword_margin_pixels_cleared": (
            dual_sword_margin_pixels_cleared
        ),
        "dual_sword_blade_pixels_highlighted": (
            dual_sword_blade_pixels_highlighted
        ),
        "left_sword_region_pixels": left_sword_pixels,
        "right_sword_region_pixels": right_sword_pixels,
        "accepted": (
            matched / total >= 0.90
            and connected >= (
                84
                if hero_sword_body
                else 55 if dual_swordmaster else 45
            )
            and (
                not dual_swordmaster
                or left_sword_pixels >= 6
                and right_sword_pixels >= 6
            )
        ),
    }


def write_contact_sheet(
    output_dir: Path,
    reports: list[dict[str, object]],
) -> Path:
    columns = 5
    card_width = 280
    card_height = 310
    canvas = Image.new(
        "RGB",
        (columns * card_width, 2 * card_height),
        (18, 18, 18),
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, report in enumerate(reports):
        class_id = int(report["class_id"], 16)
        column = index % columns
        row = index // columns
        left = column * card_width
        top = row * card_height
        border = (
            (75, 170, 90)
            if report["accepted"]
            else (210, 70, 70)
        )
        draw.rectangle(
            (left + 5, top + 5, left + 274, top + 304),
            outline=border,
            width=2,
        )
        draw.text(
            (left + 12, top + 12),
            f"{class_id:02X} {CLASS_LABELS[class_id]}",
            fill=(245, 245, 245),
            font=font,
        )
        draw.text(
            (left + 12, top + 27),
            (
                f"raw head {report['prelock_identity_match']}/"
                f"{report['identity_pixel_count']} "
                f"({report['prelock_identity_ratio'] * 100:.1f}%)"
            ),
            fill=(180, 190, 180),
            font=font,
        )
        source = Image.open(report["source"]).convert("RGB").resize(
            (256, 256),
            RESAMPLING.NEAREST,
        )
        canvas.paste(source, (left + 12, top + 44))
    path = output_dir / (
        f"{output_sheet_prefix(output_dir)}-contact-sheet.png"
    )
    canvas.save(path, optimize=True)
    return path


def write_raw_contact_sheet(
    output_dir: Path,
    reports: list[dict[str, object]],
) -> Path:
    """Show every accepted image-generation output before normalization."""

    columns = 5
    card_width = 280
    card_height = 310
    canvas = Image.new(
        "RGB",
        (columns * card_width, 2 * card_height),
        (18, 18, 18),
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, report in enumerate(reports):
        class_id = int(report["class_id"], 16)
        column = index % columns
        row = index // columns
        left = column * card_width
        top = row * card_height
        border = (
            (75, 170, 90)
            if report["accepted"]
            else (210, 70, 70)
        )
        draw.rectangle(
            (left + 5, top + 5, left + 274, top + 304),
            outline=border,
            width=2,
        )
        draw.text(
            (left + 12, top + 12),
            f"{class_id:02X} {CLASS_LABELS[class_id]} · RAW AI",
            fill=(245, 245, 245),
            font=font,
        )
        draw.text(
            (left + 12, top + 27),
            (
                f"head {report['prelock_identity_match']}/"
                f"{report['identity_pixel_count']} "
                f"({report['prelock_identity_ratio'] * 100:.1f}%)"
            ),
            fill=(180, 190, 180),
            font=font,
        )
        with Image.open(report["raw"]) as raw:
            source = raw.convert("RGB").resize(
                (256, 256),
                RESAMPLING.NEAREST,
            )
        canvas.paste(source, (left + 12, top + 44))
    path = output_dir / (
        f"{output_sheet_prefix(output_dir)}-raw-ai-contact-sheet.png"
    )
    canvas.save(path, optimize=True)
    return path


def normalize_all(
    raw_dir: Path,
    output_dir: Path,
    preserve_original_mounts: bool = False,
    broaden_hero_sword: bool = False,
    dual_sword_layout: bool = False,
) -> list[dict[str, object]]:
    reports = [
        normalize(
            class_id,
            raw_dir / filename,
            output_dir,
            preserve_original_mounts,
            broaden_hero_sword,
            dual_sword_layout,
        )
        for class_id, filename in ELWIN_NATIVE_SOURCE_FILES.items()
    ]
    (output_dir / "validation-report.json").write_text(
        json.dumps(
            {
                "minimum_prelock_identity_ratio": 0.90,
                "minimum_connected_body_pixels": 45,
                "all_accepted": all(
                    report["accepted"] for report in reports
                ),
                "classes": reports,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_contact_sheet(output_dir, reports)
    write_raw_contact_sheet(output_dir, reports)
    return reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--class-id",
        type=lambda value: int(value, 0),
        choices=sorted(ELWIN_NATIVE_SOURCE_FILES),
    )
    parser.add_argument("--raw", type=Path)
    parser.add_argument("--all-raw-dir", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--preserve-original-mounts",
        action="store_true",
        help=(
            "keep the original Highlander/Knight Master mount footprint "
            "and use AI pixels only for the central equipment"
        ),
    )
    parser.add_argument(
        "--broaden-hero-sword",
        action="store_true",
        help=(
            "retain the accepted Hero sword/hands and add ten AI-derived "
            "body pixels for a moderately broad silhouette"
        ),
    )
    parser.add_argument(
        "--dual-sword-layout",
        action="store_true",
        help=(
            "keep the accepted Swordmaster dual blades inside one-pixel "
            "side margins and validate both sword regions"
        ),
    )
    args = parser.parse_args()
    if args.all_raw_dir is not None:
        if args.class_id is not None or args.raw is not None:
            parser.error(
                "--all-raw-dir cannot be combined with --class-id/--raw"
            )
        reports = normalize_all(
            args.all_raw_dir.resolve(),
            args.output_dir.resolve(),
            args.preserve_original_mounts,
            args.broaden_hero_sword,
            args.dual_sword_layout,
        )
        print(json.dumps(reports, ensure_ascii=False))
        return 0 if all(
            report["accepted"] for report in reports
        ) else 1
    if args.class_id is None or args.raw is None:
        parser.error(
            "--class-id and --raw are required without --all-raw-dir"
        )
    report = normalize(
        args.class_id,
        args.raw.resolve(),
        args.output_dir.resolve(),
        args.preserve_original_mounts,
        args.broaden_hero_sword,
        args.dual_sword_layout,
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
