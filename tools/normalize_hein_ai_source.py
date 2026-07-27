#!/usr/bin/env python3
"""Reconstruct existing Hein AI designs with the current editor masks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
GUIDE_DIR = (
    ROOT / "docs/assets/ai-class-source/hein-head-ratio-guides-v1"
)
RESAMPLING = getattr(Image, "Resampling", Image)
HEIN_NATIVE_SOURCE_FILES = {
    0x09: "09-sorcerer.png",
    0x0A: "0A-shaman.png",
    0x0B: "0B-high-lord.png",
    0x13: "13-mage.png",
    0x14: "14-archmage.png",
    0x15: "15-wizard.png",
    0x16: "16-high-priest.png",
    0x18: "18-sage.png",
    0x19: "19-paladin.png",
    0x1A: "1A-swordmaster.png",
    0x28: "28-summoner.png",
}
CLASS_LABELS = {
    0x09: "SORCERER",
    0x0A: "SHAMAN",
    0x0B: "HIGH LORD",
    0x13: "MAGE",
    0x14: "ARCHMAGE",
    0x15: "WIZARD",
    0x16: "HIGH PRIEST",
    0x18: "SAGE",
    0x19: "PALADIN",
    0x1A: "SWORDMASTER",
    0x28: "SUMMONER",
}

from tools.build_ai_class_sprite_assets import (  # noqa: E402
    quantize_16_color_rgba,
)
from tools.normalize_elwin_ai_source import (  # noqa: E402
    connected_body_pixels,
    ensure_bottom_alignment,
    lock_identity,
    magenta_canvas,
    prelock_identity_match,
    sample_imagegen_result,
)


def logical_reference(class_id: int) -> Image.Image:
    return Image.open(
        GUIDE_DIR / f"{class_id:02X}-original-full-ratio.png"
    ).convert("RGBA").resize((16, 16), RESAMPLING.NEAREST)


def identity_points(class_id: int) -> set[tuple[int, int]]:
    document = json.loads(
        (GUIDE_DIR / "identity-points.json").read_text(encoding="utf-8")
    )
    return {
        tuple(point)
        for point in document["identity_points"][f"{class_id:02X}"]
    }


def extend_existing_feet_to_bottom(
    image: Image.Image,
    points: set[tuple[int, int]],
) -> int:
    """Extend the lowest existing body row without moving the masked head."""

    if any(image.getpixel((x, 15))[3] != 0 for x in range(16)):
        return 0
    lowest = max(
        (
            y
            for y in range(9, 16)
            if any(
                image.getpixel((x, y))[3] != 0
                for x in range(16)
            )
        ),
        default=None,
    )
    if lowest is None:
        return 0
    source_pixels = [
        (x, image.getpixel((x, lowest)))
        for x in range(3, 13)
        if image.getpixel((x, lowest))[3] != 0
    ]
    added = 0
    for target_y in range(lowest + 1, 16):
        for x, color in source_pixels:
            if (x, target_y) in points:
                continue
            image.putpixel((x, target_y), color)
            added += 1
    return added


def normalize(
    class_id: int,
    raw_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    filename = HEIN_NATIVE_SOURCE_FILES[class_id]
    reference = logical_reference(class_id)
    points = identity_points(class_id)
    raw_sampled = sample_imagegen_result(raw_path)
    source_matched, total = prelock_identity_match(
        raw_sampled,
        reference,
        points,
    )
    sampled = quantize_16_color_rgba(raw_sampled)
    locked = lock_identity(sampled, reference, points)
    grounded = ensure_bottom_alignment(locked)
    if not any(
        locked.getpixel((x, 15))[3] != 0
        for x in range(16)
    ):
        grounded += extend_existing_feet_to_bottom(locked, points)
    connected = connected_body_pixels(locked, points)
    bbox = locked.getchannel("A").getbbox()
    if bbox is None:
        width = height = visible = 0
    else:
        left, top, right, bottom = bbox
        width = right - left
        height = bottom - top
        visible = sum(
            locked.getpixel((x, y))[3] != 0
            for y in range(16)
            for x in range(16)
        )

    logical_dir = output_dir / "logical16"
    logical_dir.mkdir(parents=True, exist_ok=True)
    logical = magenta_canvas(locked)
    logical.save(logical_dir / filename)
    logical.resize((1024, 1024), RESAMPLING.NEAREST).save(
        output_dir / filename,
        optimize=True,
    )
    return {
        "class_id": f"{class_id:02X}",
        "raw": str(raw_path),
        "source": str(output_dir / filename),
        "reconstruction_mode": "existing AI equipment + current user mask",
        "source_identity_match": source_matched,
        "identity_pixel_count": total,
        "source_identity_ratio": round(source_matched / total, 4),
        "locked_identity_match": total,
        "grounded_pixels_added": grounded,
        "connected_body_pixels": connected,
        "visible_pixel_count": visible,
        "foreground_width": width,
        "foreground_height": height,
        "accepted": (
            connected >= 40
            and width >= 7
            and height >= 14
        ),
    }


def write_contact_sheet(
    output_dir: Path,
    reports: list[dict[str, object]],
) -> Path:
    columns = 4
    rows = 3
    card_width = 280
    card_height = 310
    canvas = Image.new(
        "RGB",
        (columns * card_width, rows * card_height),
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
                f"old source head {report['source_identity_match']}/"
                f"{report['identity_pixel_count']} -> locked 100%"
            ),
            fill=(180, 190, 180),
            font=font,
        )
        with Image.open(report["source"]) as source_image:
            source = source_image.convert("RGB").resize(
                (256, 256),
                RESAMPLING.NEAREST,
            )
        canvas.paste(source, (left + 12, top + 44))
    path = output_dir / "hein-v2-contact-sheet.png"
    canvas.save(path, optimize=True)
    return path


def normalize_all(
    raw_dir: Path,
    output_dir: Path,
) -> list[dict[str, object]]:
    reports = [
        normalize(class_id, raw_dir / filename, output_dir)
        for class_id, filename in HEIN_NATIVE_SOURCE_FILES.items()
    ]
    document = {
        "mode": "reconstruct existing Hein AI equipment with current mask",
        "minimum_connected_body_pixels": 40,
        "all_accepted": all(report["accepted"] for report in reports),
        "classes": reports,
    }
    (output_dir / "validation-report.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_contact_sheet(output_dir, reports)
    return reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--class-id",
        type=lambda value: int(value, 0),
        choices=sorted(HEIN_NATIVE_SOURCE_FILES),
    )
    parser.add_argument("--raw", type=Path)
    parser.add_argument("--all-raw-dir", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    if args.all_raw_dir is not None:
        if args.class_id is not None or args.raw is not None:
            parser.error(
                "--all-raw-dir cannot be combined with --class-id/--raw"
            )
        reports = normalize_all(args.all_raw_dir.resolve(), output_dir)
        print(json.dumps(reports, ensure_ascii=False))
        return 0 if all(report["accepted"] for report in reports) else 1
    if args.class_id is None or args.raw is None:
        parser.error(
            "--class-id and --raw are required without --all-raw-dir"
        )
    report = normalize(args.class_id, args.raw.resolve(), output_dir)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
