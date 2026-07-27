#!/usr/bin/env python3
"""Normalize Sherry imagegen results to exact-mask native 16x16 sources."""

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
    ROOT
    / "docs/assets/ai-class-source/latest/sherry-v2/guides"
)
RESAMPLING = getattr(Image, "Resampling", Image)
SHERRY_NATIVE_SOURCE_FILES = {
    0x04: "04-lord.png",
    0x0B: "0B-high-lord.png",
    0x13: "13-mage.png",
    0x14: "14-archmage.png",
    0x15: "15-wizard.png",
    0x17: "17-saint.png",
    0x19: "19-paladin.png",
    0x1D: "1D-silver-knight.png",
    0x1E: "1E-dragon-lord.png",
    0x21: "21-ranger.png",
    0x23: "23-high-master.png",
}
CLASS_LABELS = {
    0x04: "LORD",
    0x0B: "HIGH LORD",
    0x13: "MAGE",
    0x14: "ARCHMAGE",
    0x15: "WIZARD",
    0x17: "SAINT",
    0x19: "PALADIN",
    0x1D: "SILVER KNIGHT",
    0x1E: "DRAGON LORD",
    0x21: "RANGER",
    0x23: "HIGH MASTER",
}
MOUNTED_CLASSES = {0x1D, 0x1E}

from tools.build_ai_class_sprite_assets import (  # noqa: E402
    ROM_INK,
    quantize_16_color_rgba,
    remove_magenta_background,
)
from tools.normalize_elwin_ai_source import (  # noqa: E402
    connected_body_pixels,
    ensure_bottom_alignment,
    is_magenta,
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


def lock_high_resolution_identity(
    raw_path: Path,
    reference: Image.Image,
    points: set[tuple[int, int]],
    selected_path: Path,
) -> Image.Image:
    """Replace exact logical face cells before reducing to native16."""

    guide_metadata = GUIDE_DIR / "identity-points.json"
    if (
        selected_path.is_file()
        and selected_path.stat().st_mtime_ns
        >= raw_path.stat().st_mtime_ns
        and selected_path.stat().st_mtime_ns
        >= guide_metadata.stat().st_mtime_ns
    ):
        try:
            return Image.open(selected_path).convert("RGBA")
        except OSError:
            # A terminated PNG optimization can leave a newer but truncated
            # file. Rebuild that one source from the intact raw candidate.
            pass

    selected = Image.open(raw_path).convert("RGBA")
    for x, y in points:
        left = round(x * selected.width / 16)
        right = round((x + 1) * selected.width / 16)
        top = round(y * selected.height / 16)
        bottom = round((y + 1) * selected.height / 16)
        color = reference.getpixel((x, y))
        if is_magenta(color):
            color = (255, 0, 255, 255)
        selected.paste(color, (left, top, right, bottom))
    selected_path.parent.mkdir(parents=True, exist_ok=True)
    selected.save(selected_path, optimize=True)
    return selected


def use_outer_columns(
    image: Image.Image,
    points: set[tuple[int, int]],
) -> int:
    """Extend an existing equipment edge so all 16 columns are useful."""

    added = 0
    for direction in (-1, 1):
        while True:
            bbox = image.getchannel("A").getbbox()
            if bbox is None:
                break
            left, _, right, _ = bbox
            if direction < 0:
                if left == 0:
                    break
                source_x = left
                target_x = left - 1
            else:
                if right == 16:
                    break
                source_x = right - 1
                target_x = right
            candidates = [
                y
                for y in range(8, 16)
                if (
                    (source_x, y) not in points
                    and (target_x, y) not in points
                    and image.getpixel((source_x, y))[3] != 0
                )
            ]
            if not candidates:
                break
            y = max(candidates)
            image.putpixel(
                (target_x, y),
                image.getpixel((source_x, y)),
            )
            added += 1

    # A few broad heads establish the sprite bbox before their robe or shield
    # reaches that side. Extend the closest existing equipment run across the
    # remaining transparent cells rather than leaving a whole column unused.
    bbox = image.getchannel("A").getbbox()
    if bbox is not None and bbox[0] > 0:
        candidates = sorted(
            (
                (x, y)
                for y in range(9, 16)
                for x in range(1, 16)
                if (
                    (x, y) not in points
                    and image.getpixel((x, y))[3] != 0
                    and all(
                        (target_x, y) not in points
                        for target_x in range(x)
                    )
                )
            ),
            key=lambda point: (point[0], -point[1]),
        )
        if candidates:
            source_x, y = candidates[0]
            color = image.getpixel((source_x, y))
            for target_x in range(source_x):
                if image.getpixel((target_x, y))[3] == 0:
                    image.putpixel((target_x, y), color)
                    added += 1

    bbox = image.getchannel("A").getbbox()
    if bbox is not None and bbox[2] < 16:
        candidates = sorted(
            (
                (x, y)
                for y in range(9, 16)
                for x in range(15)
                if (
                    (x, y) not in points
                    and image.getpixel((x, y))[3] != 0
                    and all(
                        (target_x, y) not in points
                        for target_x in range(x + 1, 16)
                    )
                )
            ),
            key=lambda point: (-point[0], -point[1]),
        )
        if candidates:
            source_x, y = candidates[0]
            color = image.getpixel((source_x, y))
            for target_x in range(source_x + 1, 16):
                if image.getpixel((target_x, y))[3] == 0:
                    image.putpixel((target_x, y), color)
                    added += 1
    return added


def replace_generated_black(
    image: Image.Image,
    points: set[tuple[int, int]],
) -> int:
    replaced = 0
    for y in range(16):
        for x in range(16):
            if (x, y) in points:
                continue
            if image.getpixel((x, y)) == (0, 0, 0, 255):
                image.putpixel((x, y), ROM_INK)
                replaced += 1
    return replaced


def normalize(
    class_id: int,
    raw_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    filename = SHERRY_NATIVE_SOURCE_FILES[class_id]
    reference = logical_reference(class_id)
    points = identity_points(class_id)
    raw_unlocked_sampled = sample_imagegen_result(raw_path)
    raw_matched, raw_total = prelock_identity_match(
        raw_unlocked_sampled,
        reference,
        points,
    )
    selected_path = output_dir / "selected-sources" / filename
    lock_high_resolution_identity(
        raw_path,
        reference,
        points,
        selected_path,
    )
    raw_sampled = sample_imagegen_result(selected_path)
    matched, total = prelock_identity_match(
        raw_sampled,
        reference,
        points,
    )
    sampled = quantize_16_color_rgba(raw_sampled)
    locked = lock_identity(sampled, reference, points)
    grounded = ensure_bottom_alignment(locked)
    outer_columns_added = use_outer_columns(locked, points)
    generated_black_replaced = replace_generated_black(
        locked,
        points,
    )
    connected = connected_body_pixels(locked, points)
    bbox = locked.getchannel("A").getbbox()
    if bbox is None:
        left = top = right = bottom = 0
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

    mounted = class_id in MOUNTED_CLASSES
    minimum_body = 55 if mounted else 40
    minimum_width = 12 if mounted else 7
    return {
        "class_id": f"{class_id:02X}",
        "raw": str(raw_path),
        "selected_source": str(selected_path),
        "source": str(output_dir / filename),
        "raw_candidate_identity_match": raw_matched,
        "raw_candidate_identity_pixel_count": raw_total,
        "raw_candidate_identity_ratio": round(
            raw_matched / raw_total,
            4,
        ),
        "prelock_identity_match": matched,
        "identity_pixel_count": total,
        "prelock_identity_ratio": round(matched / total, 4),
        "locked_identity_match": total,
        "grounded_pixels_added": grounded,
        "outer_column_pixels_added": outer_columns_added,
        "generated_black_replaced": generated_black_replaced,
        "connected_body_pixels": connected,
        "visible_pixel_count": visible,
        "foreground_width": width,
        "foreground_height": height,
        "mounted": mounted,
        "accepted": (
            matched / total >= 0.90
            and connected >= minimum_body
            and width >= minimum_width
            and height >= 14
            and left == 0
            and right == 16
        ),
    }


def output_sheet_prefix(output_dir: Path) -> str:
    version = output_dir.name.rsplit("-", 1)[-1]
    return f"sherry-{version}"


def write_contact_sheet(
    output_dir: Path,
    reports: list[dict[str, object]],
    *,
    raw: bool,
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
        suffix = " · RAW AI" if raw else ""
        draw.text(
            (left + 12, top + 12),
            f"{class_id:02X} {CLASS_LABELS[class_id]}{suffix}",
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
        source_path = report["raw"] if raw else report["source"]
        with Image.open(source_path) as source_image:
            source = source_image.convert("RGB").resize(
                (256, 256),
                RESAMPLING.NEAREST,
            )
        canvas.paste(source, (left + 12, top + 44))
    kind = "raw-ai" if raw else "contact-sheet"
    path = output_dir / f"{output_sheet_prefix(output_dir)}-{kind}.png"
    canvas.save(path, optimize=True)
    return path


def write_ai_final_rom_sheet(
    output_dir: Path,
    reports: list[dict[str, object]],
) -> Path:
    canvas = Image.new(
        "RGB",
        (860, 55 + len(reports) * 270),
        (238, 238, 238),
    )
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (12, 16),
        "selected AI with exact face | final native16 | original ROM",
        fill=(24, 24, 24),
    )
    for index, report in enumerate(reports):
        class_id = int(report["class_id"], 16)
        filename = SHERRY_NATIVE_SOURCE_FILES[class_id]
        y = 55 + index * 270
        draw.text(
            (8, y + 115),
            f"{class_id:02X} {CLASS_LABELS[class_id]}",
            fill=(24, 24, 24),
        )
        selected = Image.open(
            report["selected_source"]
        ).convert("RGB")
        selected.thumbnail((240, 240), RESAMPLING.NEAREST)
        final = Image.open(
            output_dir / "logical16" / filename
        ).convert("RGB").resize((256, 256), RESAMPLING.NEAREST)
        original = logical_reference(class_id).convert("RGB").resize(
            (256, 256),
            RESAMPLING.NEAREST,
        )
        canvas.paste(selected, (55, y + 10))
        canvas.paste(final, (315, y + 10))
        canvas.paste(original, (585, y + 10))
    path = output_dir / f"{output_sheet_prefix(output_dir)}-ai-final-rom.png"
    canvas.save(path, optimize=True)
    return path


def normalize_all(
    raw_dir: Path,
    output_dir: Path,
) -> list[dict[str, object]]:
    reports = [
        normalize(class_id, raw_dir / filename, output_dir)
        for class_id, filename in SHERRY_NATIVE_SOURCE_FILES.items()
    ]
    (output_dir / "validation-report.json").write_text(
        json.dumps(
            {
                "minimum_prelock_identity_ratio": 0.90,
                "minimum_connected_body_pixels": {
                    "on_foot": 40,
                    "mounted": 55,
                },
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
    write_contact_sheet(output_dir, reports, raw=False)
    write_contact_sheet(output_dir, reports, raw=True)
    write_ai_final_rom_sheet(output_dir, reports)
    return reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--class-id",
        type=lambda value: int(value, 0),
        choices=sorted(SHERRY_NATIVE_SOURCE_FILES),
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
    report = normalize(
        args.class_id,
        args.raw.resolve(),
        output_dir,
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
