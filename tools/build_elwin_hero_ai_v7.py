#!/usr/bin/env python3
"""Build a fresh anatomy-readable Elwin Hero from ROM-only references."""

from __future__ import annotations

import argparse
from collections import Counter, deque
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/assets/ai-class-source/latest/elwin-hero-ai-v7-anatomy"
ROM_SPRITE = ROOT / "editor/static/class-sprites/commanders/1/22-p1.png"
MASK_FILE = ROOT / "editor/ai_identity_masks.json"
REFERENCE_BACKDROP = (238, 238, 238, 255)
SELECTED_CANDIDATE = OUTPUT / "selected-sources/22-hero-ai.png"
PREVIOUS_HERO = (
    ROOT / "docs/assets/ai-class-source/latest/elwin-hero-ai-v6-fresh/22-hero.png"
)

TRANSPARENT = (0, 0, 0, 0)
INK = (36, 36, 36, 255)
WHITE = (255, 255, 255, 255)
SILVER = (146, 146, 146, 255)
SKIN = (219, 182, 109, 255)
BROWN = (146, 73, 36, 255)
GOLD = (255, 182, 0, 255)
RED_DARK = (109, 0, 0, 255)
RED = (219, 0, 0, 255)
BLUE_DARK = (73, 73, 109, 255)
BLUE = (36, 73, 219, 255)


def identity_points() -> set[tuple[int, int]]:
    document = json.loads(MASK_FILE.read_text(encoding="utf-8"))
    points = {tuple(point) for point in document["masks"]["1:22"]}
    if len(points) != 73:
        raise ValueError(f"expected 73 Elwin Hero identity pixels, got {len(points)}")
    return points


def prepare_references() -> None:
    reference_dir = OUTPUT / "references"
    reference_dir.mkdir(parents=True, exist_ok=True)
    original = Image.open(ROM_SPRITE).convert("RGBA")
    identity = identity_points()

    original_matte = Image.new("RGBA", (16, 16), REFERENCE_BACKDROP)
    original_matte.alpha_composite(original)
    original_matte.resize((512, 512), Image.Resampling.NEAREST).save(
        reference_dir / "elwin-hero-rom-original-neutral-32x.png",
        optimize=True,
    )

    identity_matte = Image.new("RGBA", (16, 16), REFERENCE_BACKDROP)
    for point in identity:
        identity_matte.putpixel(point, original.getpixel(point))
    identity_matte.resize((512, 512), Image.Resampling.NEAREST).save(
        reference_dir / "elwin-hero-identity-73px-neutral-32x.png",
        optimize=True,
    )
    original.save(reference_dir / "elwin-hero-rom-original.png", optimize=True)


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


def draw_native_hero(
    original: Image.Image,
    identity: set[tuple[int, int]],
) -> Image.Image:
    """Repixel the fresh AI pose with explicit anatomy and weapon layers."""
    result = Image.new("RGBA", (16, 16), TRANSPARENT)

    # Compact cape first, only behind the image-right shoulder, arm, torso,
    # and leg. It never paints over the arm/pauldron layers drawn later.
    paint(
        result,
        {
            (15, 9), (14, 10), (15, 10),
            (13, 11), (14, 11), (15, 11),
            (12, 12), (13, 12), (14, 12), (15, 12),
            (12, 13), (13, 13), (14, 13), (15, 13),
            (12, 14), (13, 14), (14, 14), (15, 14),
            (13, 15), (14, 15), (15, 15),
        },
        RED_DARK,
    )
    paint(
        result,
        {
            (15, 10), (14, 11), (15, 11), (14, 12), (15, 12),
            (13, 13), (14, 13), (15, 13), (14, 14), (15, 14),
        },
        RED,
    )

    # One continuous upper-left diagonal blade. The current identity mask
    # supplies the original head-crossing blade pixels; the outer route stays
    # on x0..5 so no red hair pixel looks like a hole in the metal.
    paint(
        result,
        {
            (0, 0), (0, 1), (1, 1), (1, 2), (2, 2), (2, 3),
            (1, 3), (1, 4), (2, 4), (1, 5), (2, 5),
            (2, 6), (2, 7), (3, 7), (3, 8), (4, 8),
        },
        INK,
    )
    paint(
        result,
        {(0, 0), (1, 1), (2, 2), (2, 3), (1, 4),
         (2, 5), (2, 6), (3, 7), (4, 8)},
        SILVER,
    )
    paint(
        result,
        {(1, 0), (2, 1), (3, 2), (1, 3), (2, 4),
         (1, 5), (3, 6), (4, 7), (5, 8)},
        WHITE,
    )

    # Closed torso and the dark one-pixel neck separator. No consecutive
    # white pixels are allowed beneath the face, preventing the old large-mouth
    # reading. Blue remains one central, uninterrupted body mass.
    paint(result, {(6, 9), (7, 9), (8, 9), (9, 9)}, INK)
    paint(result, {(5, 9), (10, 9)}, GOLD)
    paint(result, rect(5, 10, 11, 14), INK)
    paint(result, {(6, 10), (10, 10), (6, 11), (10, 11),
                   (6, 12), (10, 12), (6, 13), (10, 13),
                   (6, 14), (10, 14)}, BLUE_DARK)
    paint(result, rect(7, 10, 9, 14), BLUE)
    paint(result, {(7, 13), (8, 13), (9, 13)}, GOLD)

    # Sword-side chain: blade -> gold guard -> skin hand -> silver forearm ->
    # torso. Each material changes color at a separate logical cell.
    paint(result, {(3, 9), (4, 9), (5, 9)}, INK)
    paint(result, {(4, 9), (5, 9)}, GOLD)
    paint(result, {(3, 10), (4, 10), (5, 10)}, INK)
    paint(result, {(4, 10)}, SKIN)
    paint(result, {(3, 11), (4, 11), (5, 11)}, INK)
    paint(result, {(4, 11), (5, 11)}, SILVER)
    paint(result, {(5, 12)}, SILVER)

    # Opposite shoulder, forearm, and open hand are independent from the
    # cape. The explicit dark chain at x14/y9 -> x12/y12 is the cape boundary.
    paint(result, {(10, 8), (11, 8), (12, 8), (13, 8), (14, 8),
                   (10, 9), (11, 9), (12, 9), (13, 9), (14, 9)}, INK)
    paint(result, {(11, 8), (12, 8), (13, 8),
                   (11, 9), (12, 9), (13, 9)}, SILVER)
    paint(result, {(12, 8), (13, 9)}, WHITE)
    paint(result, {(10, 9), (13, 9)}, GOLD)
    paint(result, {(11, 10), (12, 10), (13, 10), (14, 10)}, INK)
    paint(result, {(11, 10), (12, 10)}, SILVER)
    paint(result, {(13, 10)}, SKIN)
    paint(result, {(12, 11), (13, 11), (14, 11)}, INK)
    paint(result, {(12, 11)}, SILVER)
    paint(result, {(14, 9), (14, 10), (13, 11), (12, 12)}, INK)

    # Two armored legs and boots. The blue tabard stays central while the legs
    # use separate silver masses and separate bottom-row feet.
    paint(result, rect(3, 12, 6, 14) | rect(10, 12, 13, 14), INK)
    paint(result, {(4, 12), (5, 12), (5, 13), (6, 13), (4, 14), (5, 14),
                   (11, 12), (12, 12), (10, 13), (11, 13),
                   (11, 14), (12, 14)}, SILVER)
    paint(result, {(5, 12), (11, 12), (5, 14), (11, 14)}, WHITE)
    paint(result, {(4, 13), (12, 13)}, GOLD)
    paint(result, rect(2, 15, 6, 15) | rect(10, 15, 13, 15), INK)
    # Extend each boot one cell inward while preserving the x8 separator.
    # This keeps the broad Hero stance without the former three-cell split.
    paint(result, {(7, 15), (9, 15)}, INK)
    paint(result, {(3, 15), (4, 15), (5, 15),
                   (11, 15), (12, 15)}, SILVER)

    # Reassert the four-step sword-hand chain and the cape boundary after all
    # body layers, then restore the exact current face/hair/eye mask last.
    paint(result, {(4, 8)}, SILVER)
    paint(result, {(5, 8)}, WHITE)
    paint(result, {(4, 9)}, GOLD)
    paint(result, {(4, 10)}, SKIN)
    paint(result, {(4, 11), (5, 11)}, SILVER)
    paint(result, {(14, 9), (14, 10), (13, 11), (12, 12)}, INK)
    for point in identity:
        result.putpixel(point, original.getpixel(point))
    return result


def connected_components(image: Image.Image) -> list[int]:
    visible = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if image.getpixel((x, y))[3]
    }
    result: list[int] = []
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
        result.append(size)
    return sorted(result, reverse=True)


def visible_palette(image: Image.Image) -> list[str]:
    counts = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common()
    ]


def write_comparison(
    original: Image.Image,
    previous: Image.Image,
    candidate: Image.Image,
    native: Image.Image,
) -> None:
    cell = 320
    header = 36
    canvas = Image.new("RGBA", (cell * 4, cell + header), (210, 210, 210, 255))
    draw = ImageDraw.Draw(canvas)
    rows = (
        ("ROM original", original.resize((cell, cell), Image.Resampling.NEAREST)),
        ("previous Hero v6", previous.resize((cell, cell), Image.Resampling.NEAREST)),
        ("fresh anatomy AI", candidate.resize((cell, cell), Image.Resampling.LANCZOS)),
        ("native 16x16 v7", native.resize((cell, cell), Image.Resampling.NEAREST)),
    )
    for index, (label, image) in enumerate(rows):
        canvas.alpha_composite(image, (index * cell, header))
        draw.text((index * cell + 8, 10), label, fill=(24, 24, 24, 255))
    canvas.save(OUTPUT / "elwin-hero-v7-comparison.png", optimize=True)


def build() -> dict[str, object]:
    original = Image.open(ROM_SPRITE).convert("RGBA")
    previous = Image.open(PREVIOUS_HERO).convert("RGBA")
    candidate = Image.open(SELECTED_CANDIDATE).convert("RGBA")
    identity = identity_points()
    image = draw_native_hero(original, identity)

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
        for y in range(9, 15)
        for x in range(6, 10)
        if not image.getpixel((x, y))[3]
    ]
    semantic_checks = {
        "dark_neck_separator": all(
            image.getpixel(point) == INK
            for point in ((6, 9), (7, 9), (8, 9), (9, 9))
        ),
        "blade_guard_hand_arm_chain": [
            list(image.getpixel(point))
            for point in ((4, 8), (4, 9), (4, 10), (4, 11))
        ] == [list(SILVER), list(GOLD), list(SKIN), list(SILVER)],
        "opposite_arm_and_hand": (
            image.getpixel((12, 10)) == SILVER
            and image.getpixel((13, 10)) == SKIN
            and image.getpixel((14, 10)) == INK
            and image.getpixel((15, 10)) == RED
        ),
        "cape_boundary_chain": all(
            image.getpixel(point) == INK
            for point in ((14, 9), (14, 10), (13, 11), (12, 12))
        ),
        "closed_blue_torso": all(
            image.getpixel(point) in {BLUE, GOLD}
            for y in range(10, 15)
            for point in ((7, y), (8, y), (9, y))
        ),
    }
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
        and all(semantic_checks.values())
        and not pure_black
        and not magenta
    )
    if not accepted:
        raise ValueError(
            "invalid Hero v7: "
            f"identity={identity_match}/{len(identity)}, palette={len(palette)}, "
            f"components={components}, rows={empty_rows}, columns={empty_columns}, "
            f"holes={center_holes}, semantic={semantic_checks}, "
            f"black={pure_black}, magenta={magenta}"
        )

    logical_dir = OUTPUT / "logical16"
    preview_dir = OUTPUT / "previews"
    logical_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT / "22-hero.png", optimize=True)
    image.save(logical_dir / "22-hero.png", optimize=True)
    image.resize((512, 512), Image.Resampling.NEAREST).save(
        preview_dir / "22-hero.png", optimize=True
    )
    write_comparison(original, previous, candidate, image)

    report = {
        "version": 7,
        "source": str(SELECTED_CANDIDATE.relative_to(ROOT)),
        "input_policy": "ROM Elwin Hero + current 73-pixel identity mask only; no earlier AI used for first generation",
        "native_size": [16, 16],
        "identity_match": identity_match,
        "identity_pixel_count": len(identity),
        "visible_color_count": len(palette),
        "palette": palette,
        "connected_components": components,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "center_holes": center_holes,
        "semantic_checks": semantic_checks,
        "pure_black": pure_black,
        "magenta_contamination": magenta,
        "accepted": accepted,
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-references", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.prepare_references:
        prepare_references()
        print(OUTPUT / "references")
        return 0
    report = build()
    print(json.dumps({
        "accepted": report["accepted"],
        "semantic_checks": report["semantic_checks"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
