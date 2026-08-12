#!/usr/bin/env python3
"""Prepare and build fresh Jessica Zarvera/Summoner sprite assets.

The generative inputs deliberately contain no earlier AI design or shared
class template.  Only Jessica's stock ROM sprite and the current saved
identity mask are used to make the reference images.  The selected generated
concepts are repixelled into native 16x16 sprites in the second stage.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "assets/class-sprites/source/latest/"
    / "jessica-zarvera-summoner-ai-v1-fresh"
)
ROM_SPRITE_DIR = ROOT / "editor/static/class-sprites/commanders/10"
EDITOR_MASKS = ROOT / "editor/ai_identity_masks.json"
RESOLVED_MASKS = (
    ROOT
    / "assets/class-sprites/source/latest/shared-new-classes-v2-refined/"
    / "identity-masks.json"
)

CLASSES = {
    0x26: "zarvera",
    0x28: "summoner",
}
REFERENCE_BACKDROP = (238, 238, 238, 255)
TRANSPARENT = (0, 0, 0, 0)
INK = (36, 36, 36, 255)
NAVY = (36, 36, 73, 255)
BLUE_GRAY = (73, 73, 109, 255)
SILVER = (146, 146, 146, 255)
WHITE = (255, 255, 255, 255)
GOLD = (255, 182, 0, 255)
WOOD = (146, 73, 36, 255)
DEEP_WOOD = (73, 36, 36, 255)
CYAN = (109, 219, 255, 255)
ROYAL_BLUE = (0, 0, 219, 255)

SELECTED_CANDIDATES = {
    0x26: OUTPUT / "selected-sources/10-26-zarvera-ai.png",
    0x28: OUTPUT / "selected-sources/10-28-summoner-ai.png",
}


def read_masks() -> dict[str, list[list[int]]]:
    editor = json.loads(EDITOR_MASKS.read_text(encoding="utf-8"))["masks"]
    resolved = json.loads(RESOLVED_MASKS.read_text(encoding="utf-8"))["masks"]
    result: dict[str, list[list[int]]] = {}
    for class_id in CLASSES:
        key = f"10:{class_id:02X}"
        points = editor.get(key, resolved.get(key))
        if not points:
            raise ValueError(f"missing Jessica identity mask: {key}")
        result[key] = points
    return result


def prepare_references() -> None:
    """Write enlarged nearest-neighbour ROM and identity-only references."""
    reference_dir = OUTPUT / "references"
    reference_dir.mkdir(parents=True, exist_ok=True)
    masks = read_masks()

    for class_id, slug in CLASSES.items():
        source = Image.open(
            ROM_SPRITE_DIR / f"{class_id:02X}-p1.png"
        ).convert("RGBA")
        points = {tuple(point) for point in masks[f"10:{class_id:02X}"]}

        # Preserve the logical 16x16 placement while making each source pixel
        # legible to the image model.  The neutral matte is reference-only and
        # is never sampled into the game sprite.
        original_matte = Image.new("RGBA", (16, 16), REFERENCE_BACKDROP)
        original_matte.alpha_composite(source)
        original_matte.resize((512, 512), Image.Resampling.NEAREST).save(
            reference_dir / f"10-{class_id:02X}-{slug}-rom-original-32x.png",
            optimize=True,
        )

        identity = Image.new("RGBA", (16, 16), REFERENCE_BACKDROP)
        for point in points:
            color = source.getpixel(point)
            if color[3]:
                identity.putpixel(point, color)
        identity.resize((512, 512), Image.Resampling.NEAREST).save(
            reference_dir / f"10-{class_id:02X}-jessica-identity-only-32x.png",
            optimize=True,
        )

        source.save(
            reference_dir / f"10-{class_id:02X}-{slug}-rom-original.png",
            optimize=True,
        )


def rect(x0: int, y0: int, x1: int, y1: int) -> set[tuple[int, int]]:
    return {
        (x, y)
        for y in range(y0, y1 + 1)
        for x in range(x0, x1 + 1)
    }


def paint(
    image: Image.Image,
    points: set[tuple[int, int]],
    color: tuple[int, int, int, int],
) -> None:
    for point in points:
        image.putpixel(point, color)


def restore_identity(
    image: Image.Image,
    original: Image.Image,
    identity: set[tuple[int, int]],
) -> Image.Image:
    result = image.copy().convert("RGBA")
    for point in identity:
        result.putpixel(point, original.getpixel(point))
    return result


def draw_zarvera() -> Image.Image:
    """Repixel the selected dark-mantle Zarvera AI concept."""
    result = Image.new("RGBA", (16, 16), TRANSPARENT)

    # Tall gem staff on image-right.  The diamond top, shaft, and gripping
    # hand remain one connected cluster and use the full rightmost column.
    paint(result, {(14, 0), (13, 1), (14, 1), (15, 1),
                   (13, 2), (14, 2), (15, 2), (14, 3)}, INK)
    paint(result, {(14, 1), (13, 2)}, CYAN)
    paint(result, {(15, 2), (14, 3)}, WHITE)
    paint(result, {(14, y) for y in range(4, 16)}, WOOD)
    paint(result, {(15, y) for y in range(3, 16)}, DEEP_WOOD)

    # Broad asymmetric dark mantle and two bright shoulder plates preserve
    # the fresh AI candidate's strongest silhouette at native resolution.
    paint(result, rect(3, 8, 13, 14), INK)
    paint(result, rect(4, 9, 12, 14), NAVY)
    paint(result, {(3, 8), (4, 8), (4, 9), (5, 9),
                   (10, 8), (11, 8), (12, 8), (13, 8),
                   (3, 9), (12, 9), (13, 9)}, SILVER)
    paint(result, {(4, 8), (5, 9), (11, 8), (12, 9)}, WHITE)
    paint(result, {(5, 8), (10, 8), (4, 10), (11, 10)}, GOLD)

    # A connected casting hand on image-left gives the pose direction without
    # adding a detached spell or decorative UI-like object.
    paint(result, {(0, 8), (0, 9), (1, 9), (0, 10), (1, 10)}, INK)
    paint(result, {(0, 8), (1, 9)}, (219, 182, 109, 255))
    paint(result, {(1, 10), (2, 10), (3, 10), (4, 10)}, GOLD)

    # Closed blue-white ceremonial robe, central cyan gem, and two grounded
    # boots.  Broad blocks survive Mega Drive map scale better than the AI
    # render's many tiny ornaments.
    paint(result, rect(5, 9, 11, 14), BLUE_GRAY)
    paint(result, {(5, 9), (6, 9), (10, 9), (11, 9),
                   (5, 10), (11, 10), (5, 13), (11, 13),
                   (5, 14), (11, 14)}, GOLD)
    paint(result, {(6, 10), (7, 10), (9, 10), (10, 10),
                   (6, 11), (10, 11), (6, 12), (10, 12),
                   (6, 13), (10, 13)}, WHITE)
    paint(result, {(7, 11), (8, 11), (9, 11),
                   (7, 12), (9, 12), (7, 13), (9, 13)}, ROYAL_BLUE)
    paint(result, {(8, 10), (8, 11), (8, 12)}, CYAN)
    paint(result, {(7, 14), (8, 14), (9, 14)}, GOLD)
    paint(result, rect(3, 15, 6, 15) | rect(9, 15, 12, 15), INK)
    paint(result, {(4, 15), (5, 15), (10, 15), (11, 15)}, BLUE_GRAY)

    # Join the staff grip after robe layering.
    paint(result, {(12, 9), (13, 9), (14, 9)}, GOLD)
    return result


def draw_summoner() -> Image.Image:
    """Repixel the selected white-mantle Summoner AI concept."""
    result = Image.new("RGBA", (16, 16), TRANSPARENT)

    # Slim crescent-topped invocation staff on image-left.  The top passes
    # behind Jessica's large hair, while the full x0 shaft stays readable.
    paint(result, {(0, 0), (1, 0), (0, 1), (0, 2), (0, 3)}, INK)
    paint(result, {(1, 0), (0, 1)}, GOLD)
    paint(result, {(0, 2)}, CYAN)
    paint(result, {(0, y) for y in range(3, 16)}, DEEP_WOOD)
    paint(result, {(1, y) for y in range(10, 16)}, WOOD)

    # Large white invocation mantle is the class-defining form from the new
    # AI image.  A dark rim prevents it from dissolving into map backgrounds.
    paint(result, rect(2, 8, 13, 14), INK)
    paint(result, rect(3, 9, 12, 13), WHITE)
    paint(result, {(2, 9), (3, 9), (3, 10), (3, 11), (4, 12), (4, 13),
                   (12, 9), (13, 9), (12, 10), (12, 11),
                   (11, 12), (11, 13)}, SILVER)
    paint(result, {(3, 8), (4, 8), (4, 9), (11, 8), (12, 8), (12, 9)}, GOLD)

    # The summoning robe remains a closed, connected indigo column with a
    # simple gold seal.  It is deliberately different from Zarvera's split
    # blue-white front panel.
    paint(result, rect(5, 9, 10, 15), NAVY)
    paint(result, {(5, 9), (10, 9), (5, 10), (10, 10),
                   (5, 13), (10, 13), (5, 14), (10, 14)}, BLUE_GRAY)
    paint(result, {(6, 10), (9, 10), (6, 14), (9, 14)}, GOLD)
    paint(result, {(7, 10), (8, 10), (6, 11), (9, 11),
                   (6, 12), (9, 12), (7, 13), (8, 13)}, ROYAL_BLUE)
    paint(result, {(7, 11), (8, 11), (7, 12), (8, 12)}, GOLD)
    paint(result, {(8, 11)}, CYAN)
    paint(result, rect(3, 15, 6, 15) | rect(9, 15, 12, 15), INK)
    paint(result, {(4, 15), (5, 15), (10, 15), (11, 15)}, GOLD)

    # Staff hand at left and an open casting hand at right are connected to
    # their sleeves; no detached summoned creature is introduced.
    paint(result, {(1, 10), (2, 10), (3, 10), (4, 10)}, GOLD)
    paint(result, {(13, 9), (14, 8), (15, 8), (14, 9), (15, 9),
                   (13, 10), (14, 10), (15, 10)}, INK)
    paint(result, {(14, 8), (15, 9), (14, 10)}, (219, 182, 109, 255))
    paint(result, {(12, 10), (13, 10)}, GOLD)
    return result


def connected_components(image: Image.Image) -> list[int]:
    visible = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if image.getpixel((x, y))[3]
    }
    sizes: list[int] = []
    while visible:
        queue = deque([visible.pop()])
        size = 0
        while queue:
            x, y = queue.popleft()
            size += 1
            for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if point in visible:
                    visible.remove(point)
                    queue.append(point)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def visible_palette(image: Image.Image) -> list[str]:
    counts = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common()
    ]


def write_comparison(
    class_id: int,
    original: Image.Image,
    candidate: Image.Image,
    native: Image.Image,
) -> None:
    cell = 320
    header = 36
    canvas = Image.new("RGBA", (cell * 3, cell + header), (210, 210, 210, 255))
    draw = ImageDraw.Draw(canvas)
    labels = ("ROM identity", "fresh generative AI", "native 16x16")
    images = (
        original.resize((cell, cell), Image.Resampling.NEAREST),
        candidate.resize((cell, cell), Image.Resampling.LANCZOS),
        native.resize((cell, cell), Image.Resampling.NEAREST),
    )
    for index, (label, image) in enumerate(zip(labels, images, strict=True)):
        canvas.alpha_composite(image, (index * cell, header))
        draw.text((index * cell + 8, 10), label, fill=(24, 24, 24, 255))
    canvas.save(OUTPUT / f"10-{class_id:02X}-comparison.png", optimize=True)


def write_all_contact() -> None:
    """Put both selected AI concepts and both native results in one image."""
    cell = 480
    header = 32
    canvas = Image.new(
        "RGBA", (cell * 2, (cell + header) * 2), (210, 210, 210, 255)
    )
    draw = ImageDraw.Draw(canvas)
    for row_index, (class_id, slug) in enumerate(CLASSES.items()):
        y = row_index * (cell + header)
        ai = Image.open(SELECTED_CANDIDATES[class_id]).convert("RGBA")
        native = Image.open(OUTPUT / f"logical16/10-{class_id:02X}.png").convert(
            "RGBA"
        )
        canvas.alpha_composite(
            ai.resize((cell, cell), Image.Resampling.LANCZOS), (0, y + header)
        )
        canvas.alpha_composite(
            native.resize((cell, cell), Image.Resampling.NEAREST),
            (cell, y + header),
        )
        draw.text((8, y + 8), f"Jessica {slug}: fresh AI", fill=(24, 24, 24, 255))
        draw.text(
            (cell + 8, y + 8),
            f"Jessica {slug}: native 16x16",
            fill=(24, 24, 24, 255),
        )
    canvas.save(OUTPUT / "all-jessica-fresh-classes.png", optimize=True)


def build() -> dict[str, object]:
    masks = read_masks()
    logical_dir = OUTPUT / "logical16"
    preview_dir = OUTPUT / "previews"
    logical_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for class_id, slug in CLASSES.items():
        original = Image.open(
            ROM_SPRITE_DIR / f"{class_id:02X}-p1.png"
        ).convert("RGBA")
        candidate = Image.open(SELECTED_CANDIDATES[class_id]).convert("RGBA")
        identity = {tuple(point) for point in masks[f"10:{class_id:02X}"]}
        design = draw_zarvera() if class_id == 0x26 else draw_summoner()
        image = restore_identity(design, original, identity)

        palette = visible_palette(image)
        components = connected_components(image)
        identity_match = sum(
            image.getpixel(point) == original.getpixel(point)
            for point in identity
        )
        empty_rows = [
            y for y in range(16)
            if not any(image.getpixel((x, y))[3] for x in range(16))
        ]
        empty_columns = [
            x for x in range(16)
            if not any(image.getpixel((x, y))[3] for y in range(16))
        ]
        center_holes = [
            [x, y]
            for y in range(10, 15)
            for x in range(6, 10)
            if not image.getpixel((x, y))[3]
        ]
        pure_black = (0, 0, 0, 255) in image.getdata()
        magenta = any(
            color[3] and color[0] > 200 and color[2] > 200 and color[1] < 80
            for color in image.getdata()
        )
        accepted = (
            identity_match == len(identity)
            and len(palette) <= 15
            and len(components) == 1
            and not empty_rows
            and not empty_columns
            and not center_holes
            and not pure_black
            and not magenta
        )
        if not accepted:
            raise ValueError(
                f"invalid Jessica {slug}: identity={identity_match}/{len(identity)}, "
                f"palette={len(palette)}, components={components}, "
                f"rows={empty_rows}, columns={empty_columns}, "
                f"holes={center_holes}, black={pure_black}, magenta={magenta}"
            )

        output_path = logical_dir / f"10-{class_id:02X}.png"
        image.save(output_path, optimize=True)
        image.resize((512, 512), Image.Resampling.NEAREST).save(
            preview_dir / f"10-{class_id:02X}.png", optimize=True
        )
        write_comparison(class_id, original, candidate, image)
        rows.append({
            "commander_id": 10,
            "class_id": f"{class_id:02X}",
            "class_name": slug,
            "file": str(output_path.relative_to(OUTPUT)),
            "generative_source": str(SELECTED_CANDIDATES[class_id].relative_to(ROOT)),
            "input_policy": "ROM Jessica identity/head mask only; no earlier AI or shared class template",
            "identity_pixel_count": len(identity),
            "identity_match": identity_match,
            "visible_color_count": len(palette),
            "palette": palette,
            "connected_components": components,
            "empty_rows": empty_rows,
            "empty_columns": empty_columns,
            "center_holes": center_holes,
            "pure_black": pure_black,
            "magenta_contamination": magenta,
            "accepted": accepted,
        })

    write_all_contact()

    # Keep the source-space mask unshifted.  The aggregate builder applies
    # Jessica's established final +1 x translation exactly once.
    (OUTPUT / "identity-masks.json").write_text(
        json.dumps({"version": 1, "masks": masks}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = {
        "version": 1,
        "mode": "fresh generative AI concepts repixelled to dedicated native 16x16",
        "all_accepted": all(bool(row["accepted"]) for row in rows),
        "classes": rows,
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prepare-references",
        action="store_true",
        help="write ROM-only image-generation references",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.prepare_references:
        prepare_references()
        print(OUTPUT / "references")
        return 0
    report = build()
    print(json.dumps({
        "all_accepted": report["all_accepted"],
        "classes": [row["class_id"] for row in report["classes"]],
    }, ensure_ascii=False, indent=2))
    return 0 if report["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
