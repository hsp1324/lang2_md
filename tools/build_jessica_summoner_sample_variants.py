#!/usr/bin/env python3
"""Build five review-only Jessica Summoner native-16 sample variants.

The corresponding generative concepts were made independently with only the
stock ROM Summoner cell and Jessica's identity-only reference.  This builder
does not publish anything to the editor manifest: it repixels the five ideas
into review assets while restoring the unshifted 73-pixel identity exactly.
"""

from __future__ import annotations

from collections import Counter, deque
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.pillow_compat import flattened_image_data  # noqa: E402


OUTPUT = (
    ROOT
    / "assets/class-sprites/source/latest/sample-class-variants-v1/"
    / "jessica-summoner"
)
FRESH_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/"
    / "jessica-zarvera-summoner-ai-v1-fresh"
)
ORIGINAL = FRESH_ROOT / "references/10-28-summoner-rom-original.png"
MASK_FILE = FRESH_ROOT / "identity-masks.json"

TRANSPARENT = (0, 0, 0, 0)
INK = (36, 36, 36, 255)
NAVY = (36, 36, 73, 255)
PURPLE_DARK = (73, 0, 109, 255)
PURPLE = (146, 36, 182, 255)
LAVENDER = (219, 109, 255, 255)
SILVER = (146, 146, 146, 255)
WHITE = (255, 255, 255, 255)
GOLD = (255, 182, 0, 255)
WOOD = (146, 73, 36, 255)
SKIN = (219, 182, 109, 255)
CYAN = (109, 219, 255, 255)


def paint(
    image: Image.Image,
    points: set[tuple[int, int]],
    color: tuple[int, int, int, int],
) -> None:
    for x, y in points:
        if 0 <= x < 16 and 0 <= y < 16:
            image.putpixel((x, y), color)


def rect(x0: int, y0: int, x1: int, y1: int) -> set[tuple[int, int]]:
    return {
        (x, y)
        for y in range(y0, y1 + 1)
        for x in range(x0, x1 + 1)
    }


def robe_base(
    left: int = 3,
    right: int = 12,
    top: int = 8,
) -> Image.Image:
    """Return a closed, grounded robe before variant-specific equipment."""
    image = Image.new("RGBA", (16, 16), TRANSPARENT)
    paint(image, rect(left, top, right, 14), INK)
    paint(image, rect(left + 1, top + 1, right - 1, 14), PURPLE_DARK)
    paint(image, rect(left + 2, top + 1, right - 2, 14), PURPLE)
    paint(image, {(x, 15) for x in range(left, left + 4)}, INK)
    paint(image, {(x, 15) for x in range(right - 3, right + 1)}, INK)
    paint(image, {(left + 1, 15), (left + 2, 15),
                  (right - 2, 15), (right - 1, 15)}, PURPLE_DARK)
    return image


def draw_ring_staff() -> Image.Image:
    """01: ring staff, pale sleeves, and an elegant purple robe."""
    image = robe_base(3, 12)

    # White-lavender sleeves and a free casting hand use the image-left edge.
    paint(image, {(0, 8), (0, 9), (0, 10),
                  (1, 8), (1, 9), (2, 8), (2, 9),
                  (3, 8), (3, 9), (1, 10), (2, 10), (3, 10)}, INK)
    paint(image, {(1, 8), (2, 8), (2, 9), (3, 9)}, WHITE)
    paint(image, {(1, 9), (2, 10), (3, 10)}, LAVENDER)
    paint(image, {(0, 8), (0, 9)}, SKIN)

    # Gold ring staff on image-right, connected through the gripping hand.
    paint(image, {(14, 0), (13, 1), (15, 1), (13, 2), (15, 2),
                  (14, 3), (13, 3), (15, 3)}, INK)
    paint(image, {(14, 1), (14, 2)}, PURPLE)
    paint(image, {(13, 1), (15, 1), (13, 2), (15, 2), (14, 3)}, GOLD)
    paint(image, {(14, y) for y in range(4, 16)}, WOOD)
    paint(image, {(15, y) for y in range(4, 16)}, INK)
    paint(image, {(11, 8), (12, 8), (13, 8), (14, 8),
                  (12, 9), (13, 9), (14, 9)}, INK)
    paint(image, {(12, 8), (13, 8), (13, 9)}, WHITE)
    paint(image, {(14, 8), (14, 9)}, SKIN)

    # Closed front panel with a small summoning seal.
    paint(image, {(5, 8), (6, 8), (9, 8), (10, 8)}, LAVENDER)
    paint(image, {(6, 9), (9, 9), (6, 10), (9, 10),
                  (6, 11), (9, 11), (6, 12), (9, 12),
                  (6, 13), (9, 13)}, GOLD)
    paint(image, rect(7, 9, 8, 14), PURPLE_DARK)
    paint(image, {(7, 10), (8, 10), (7, 11), (8, 11)}, LAVENDER)
    return image


def draw_orb_staff() -> Image.Image:
    """02: crystal-orb staff and exceptionally broad ritual sleeves."""
    image = robe_base(4, 11)

    # Broad sleeves make a very different hourglass silhouette.
    paint(image, rect(0, 8, 4, 11) | rect(11, 8, 14, 11), INK)
    paint(image, {(1, 8), (2, 8), (3, 8), (1, 9), (2, 9), (3, 9),
                  (1, 10), (2, 10), (12, 8), (13, 8),
                  (12, 9), (13, 9), (12, 10), (13, 10)}, LAVENDER)
    paint(image, {(2, 8), (2, 9), (12, 8), (12, 9)}, WHITE)
    paint(image, {(0, 9), (0, 10)}, SKIN)

    # One compact crystal orb and a continuous right-edge staff.
    paint(image, {(14, 0), (13, 1), (14, 1), (15, 1),
                  (13, 2), (14, 2), (15, 2), (14, 3)}, INK)
    paint(image, {(14, 1), (13, 2)}, CYAN)
    paint(image, {(15, 2), (14, 2)}, WHITE)
    paint(image, {(14, y) for y in range(3, 16)}, WOOD)
    paint(image, {(15, y) for y in range(3, 16)}, INK)
    paint(image, {(13, 9), (14, 9), (13, 10), (14, 10)}, SKIN)

    # Dark closed column and a readable gold clasp.
    paint(image, rect(6, 9, 9, 14), PURPLE_DARK)
    paint(image, {(6, 9), (9, 9), (6, 13), (9, 13)}, PURPLE)
    paint(image, {(7, 9), (8, 9), (7, 10), (8, 10)}, GOLD)
    paint(image, {(7, 11), (8, 11), (7, 12), (8, 12)}, NAVY)
    return image


def draw_fork_staff() -> Image.Image:
    """03: two-prong staff, hoodless shoulder mantle, fitted robe."""
    image = robe_base(3, 11)

    # Short hoodless mantle spreads across the shoulders without touching hair.
    paint(image, rect(1, 8, 13, 10), INK)
    paint(image, {(2, 8), (3, 8), (4, 8), (5, 8),
                  (10, 8), (11, 8), (12, 8),
                  (2, 9), (3, 9), (12, 9)}, PURPLE)
    paint(image, {(3, 8), (4, 8), (11, 8), (12, 8)}, LAVENDER)
    paint(image, {(0, 8), (0, 9), (1, 9), (0, 10), (1, 10)}, INK)
    paint(image, {(0, 8), (0, 9), (1, 10)}, SKIN)

    # Simple U-shaped fork, clearly a magical staff rather than a trident.
    paint(image, {(13, 0), (15, 0), (13, 1), (15, 1),
                  (13, 2), (14, 2), (15, 2), (14, 3)}, INK)
    paint(image, {(13, 1), (15, 1), (14, 2)}, GOLD)
    paint(image, {(14, 3)}, LAVENDER)
    paint(image, {(14, y) for y in range(4, 16)}, WOOD)
    paint(image, {(15, y) for y in range(4, 16)}, INK)
    paint(image, {(12, 8), (13, 8), (14, 8),
                  (12, 9), (13, 9), (14, 9)}, INK)
    paint(image, {(13, 8), (14, 8), (14, 9)}, SKIN)

    # Fitted lavender center motif and gold hem stay closed.
    paint(image, {(5, 10), (10, 10), (5, 11), (10, 11),
                  (5, 12), (10, 12), (5, 13), (10, 13)}, LAVENDER)
    paint(image, rect(6, 10, 9, 14), PURPLE_DARK)
    paint(image, {(7, 10), (8, 10), (7, 11), (8, 11),
                  (6, 13), (9, 13), (7, 14), (8, 14)}, GOLD)
    paint(image, {(7, 12), (8, 12)}, WHITE)
    return image


def draw_short_wand() -> Image.Image:
    """04: short wand and attached rune-shaped shoulder emblems."""
    image = robe_base(3, 12)

    # Attached crescent/rune motifs on both shoulders.
    paint(image, {(2, 8), (3, 8), (4, 8), (2, 9), (4, 9),
                  (2, 10), (3, 10), (4, 10),
                  (11, 8), (12, 8), (13, 8), (11, 9), (13, 9),
                  (11, 10), (12, 10), (13, 10)}, INK)
    paint(image, {(3, 8), (2, 9), (3, 10),
                  (12, 8), (13, 9), (12, 10)}, GOLD)
    paint(image, {(3, 9), (12, 9)}, PURPLE)

    # Short ring wand at image-left, fully attached to hand and sleeve.
    paint(image, {(0, 7), (1, 7), (0, 8), (1, 8),
                  (0, 9), (1, 9), (2, 9),
                  (0, 10), (1, 10), (2, 10), (3, 10)}, INK)
    paint(image, {(0, 7), (1, 8)}, LAVENDER)
    paint(image, {(0, 8), (1, 7)}, GOLD)
    # Keep the wand connected below Jessica's source x=1 identity column.
    # The editor removes that source column before moving the face +1px, so
    # this y=10 route must be equipment rather than an identity-dependent join.
    paint(image, {(0, 9), (0, 10), (1, 9)}, WOOD)
    paint(image, {(1, 10)}, GOLD)
    paint(image, {(2, 9), (2, 10)}, SKIN)

    # Open casting hand on image-right fills the opposite edge.
    paint(image, {(13, 8), (14, 8), (15, 8), (13, 9),
                  (14, 9), (15, 9), (13, 10), (14, 10)}, INK)
    paint(image, {(14, 8), (15, 8), (13, 9), (15, 9), (14, 10)}, SKIN)

    # One compact chest sigil, never a cutout.
    paint(image, rect(6, 9, 9, 14), PURPLE_DARK)
    paint(image, {(7, 9), (8, 9), (6, 10), (7, 10), (8, 10), (9, 10),
                  (7, 11), (8, 11), (7, 12), (8, 12)}, LAVENDER)
    paint(image, {(7, 13), (8, 13), (7, 14), (8, 14)}, GOLD)
    return image


def draw_diagonal_staff() -> Image.Image:
    """05: royal white-panel robe and one continuous diagonal staff."""
    image = robe_base(3, 12)

    # Regal white inner panels and restrained gold collar/hem.
    paint(image, {(4, 8), (5, 8), (10, 8), (11, 8),
                  (4, 9), (5, 9), (10, 9), (11, 9)}, LAVENDER)
    paint(image, {(5, 10), (6, 10), (9, 10), (10, 10),
                  (5, 11), (6, 11), (9, 11), (10, 11),
                  (5, 12), (6, 12), (9, 12), (10, 12),
                  (5, 13), (6, 13), (9, 13), (10, 13),
                  (5, 14), (6, 14), (9, 14), (10, 14)}, WHITE)
    paint(image, rect(7, 9, 8, 14), PURPLE_DARK)
    paint(image, {(6, 8), (7, 8), (8, 8), (9, 8),
                  (6, 9), (9, 9), (6, 14), (9, 14)}, GOLD)

    # Continuous diagonal shaft.  A dark parallel edge keeps it distinct
    # from the robe without allowing it to touch Jessica's face mask.
    shaft = [
        (0, 15), (1, 14), (2, 13), (3, 12), (4, 11), (5, 10),
        (6, 10), (7, 9), (8, 9), (9, 8), (10, 8), (11, 7),
        (12, 6), (13, 5), (14, 4), (15, 3),
    ]
    paint(image, {(x, y + 1) for x, y in shaft if y < 15}, INK)
    paint(image, set(shaft), WOOD)
    paint(image, {(5, 9), (6, 9), (5, 10), (6, 10),
                  (9, 8), (10, 8), (9, 9), (10, 9)}, SKIN)
    # Small crystal tip at the upper-right end.
    paint(image, {(14, 1), (15, 1), (13, 2), (14, 2), (15, 2),
                  (14, 3), (15, 3)}, INK)
    paint(image, {(14, 2), (15, 2), (15, 1)}, CYAN)
    paint(image, {(14, 1)}, WHITE)
    return image


DRAW_VARIANTS = {
    1: draw_ring_staff,
    2: draw_orb_staff,
    3: draw_fork_staff,
    4: draw_short_wand,
    5: draw_diagonal_staff,
}


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
    counts = Counter(color for color in flattened_image_data(image) if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common()
    ]


def enclosed_holes(image: Image.Image) -> list[list[int]]:
    transparent = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if not image.getpixel((x, y))[3]
    }
    outside = {
        point
        for point in transparent
        if point[0] in (0, 15) or point[1] in (0, 15)
    }
    queue = deque(outside)
    while queue:
        x, y = queue.popleft()
        for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if point in transparent and point not in outside:
                outside.add(point)
                queue.append(point)
    return [[x, y] for x, y in sorted(transparent - outside, key=lambda p: (p[1], p[0]))]


def translate_identity_for_final_space(
    image: Image.Image,
    identity: set[tuple[int, int]],
) -> Image.Image:
    """Mirror the editor's established Jessica +1px identity translation."""
    source = image.copy()
    result = image.copy()
    translated = {(x, y): (x + 1, y) for x, y in identity}
    target_points = set(translated.values())
    for point in identity - target_points:
        result.putpixel(point, TRANSPARENT)
    for point, target in translated.items():
        result.putpixel(target, source.getpixel(point))
    return result


def write_contact(images: list[Image.Image]) -> None:
    cell = 256
    header = 34
    canvas = Image.new("RGBA", (cell * 5, cell + header), (210, 210, 210, 255))
    draw = ImageDraw.Draw(canvas)
    for index, image in enumerate(images, start=1):
        x = (index - 1) * cell
        draw.text((x + 8, 10), f"Jessica Summoner {index:02d}", fill=INK)
        canvas.alpha_composite(
            image.resize((cell, cell), Image.Resampling.NEAREST),
            (x, header),
        )
    canvas.save(OUTPUT / "all-logical16-samples.png", optimize=True)


def write_ai_and_native_contact(images: list[Image.Image]) -> None:
    """Pair every independent AI concept with its native review sprite."""
    cell = 256
    header = 34
    canvas = Image.new(
        "RGBA",
        (cell * 5, (cell + header) * 2),
        (210, 210, 210, 255),
    )
    draw = ImageDraw.Draw(canvas)
    for index, native in enumerate(images, start=1):
        x = (index - 1) * cell
        ai = Image.open(OUTPUT / f"ai/{index:02d}.png").convert("RGBA")
        draw.text((x + 8, 10), f"{index:02d} built-in AI", fill=INK)
        canvas.alpha_composite(
            ai.resize((cell, cell), Image.Resampling.LANCZOS),
            (x, header),
        )
        y = cell + header
        draw.text((x + 8, y + 10), f"{index:02d} logical 16x16", fill=INK)
        canvas.alpha_composite(
            native.resize((cell, cell), Image.Resampling.NEAREST),
            (x, y + header),
        )
    canvas.save(OUTPUT / "all-ai-and-logical16-samples.png", optimize=True)


def build() -> dict[str, object]:
    original = Image.open(ORIGINAL).convert("RGBA")
    masks = json.loads(MASK_FILE.read_text(encoding="utf-8"))["masks"]
    identity = {tuple(point) for point in masks["10:28"]}
    if len(identity) != 73:
        raise ValueError(f"expected 73 Jessica identity pixels, got {len(identity)}")

    logical_dir = OUTPUT / "logical16"
    preview_dir = OUTPUT / "previews"
    logical_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    images: list[Image.Image] = []
    for index, draw_variant in DRAW_VARIANTS.items():
        image = draw_variant()
        for point in identity:
            image.putpixel(point, original.getpixel(point))

        palette = visible_palette(image)
        components = connected_components(image)
        holes = enclosed_holes(image)
        center_holes = [
            [x, y]
            for y in range(9, 15)
            for x in range(6, 10)
            if not image.getpixel((x, y))[3]
        ]
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
        pixels = tuple(flattened_image_data(image))
        pure_black = (0, 0, 0, 255) in pixels
        magenta = any(
            color[3] and color[0] > 200 and color[2] > 200 and color[1] < 80
            for color in pixels
        )
        accepted = (
            identity_match == 73
            and len(palette) <= 15
            and len(components) == 1
            and not center_holes
            and not empty_rows
            and not empty_columns
            and not pure_black
            and not magenta
        )

        # Variants 01 and 04 have equipment on the source x=0 edge and are
        # published after Jessica's +1px face translation.  Both therefore
        # receive an additional final-space continuity gate.
        final_space: dict[str, object] | None = None
        if index in (1, 4):
            final_image = translate_identity_for_final_space(image, identity)
            final_components = connected_components(final_image)
            final_empty_rows = [
                y for y in range(16)
                if not any(final_image.getpixel((x, y))[3] for x in range(16))
            ]
            final_empty_columns = [
                x for x in range(16)
                if not any(final_image.getpixel((x, y))[3] for y in range(16))
            ]
            final_identity_match = sum(
                final_image.getpixel((x + 1, y)) == original.getpixel((x, y))
                for x, y in identity
            )
            final_space = {
                "translation": [1, 0],
                "identity_match": final_identity_match,
                "connected_components": final_components,
                "empty_rows": final_empty_rows,
                "empty_columns": final_empty_columns,
                "accepted": (
                    final_identity_match == 73
                    and len(final_components) == 1
                    and not final_empty_rows
                    and not final_empty_columns
                ),
            }
            accepted = accepted and bool(final_space["accepted"])
        if not accepted:
            raise ValueError(
                f"variant {index:02d} invalid: identity={identity_match}/73, "
                f"palette={len(palette)}, components={components}, holes={holes}, "
                f"center={center_holes}, rows={empty_rows}, columns={empty_columns}, "
                f"black={pure_black}, magenta={magenta}"
            )

        output_path = logical_dir / f"{index:02d}.png"
        image.save(output_path, optimize=True)
        image.resize((256, 256), Image.Resampling.NEAREST).save(
            preview_dir / f"{index:02d}.png",
            optimize=True,
        )
        images.append(image)
        rows.append({
            "variant": index,
            "ai_source": f"ai/{index:02d}.png",
            "logical16": f"logical16/{index:02d}.png",
            "preview_16x": f"previews/{index:02d}.png",
            "identity_pixel_count": len(identity),
            "identity_match": identity_match,
            "visible_color_count": len(palette),
            "palette": palette,
            "connected_components": components,
            "enclosed_holes": holes,
            "center_holes": center_holes,
            "empty_rows": empty_rows,
            "empty_columns": empty_columns,
            "pure_black": pure_black,
            "magenta_contamination": magenta,
            "published_final_space": final_space,
            "accepted": accepted,
        })

    write_contact(images)
    write_ai_and_native_contact(images)
    report = {
        "version": 1,
        "mode": "five independent built-in imagegen concepts repixelled as review-only logical16 samples",
        "input_policy": "only ROM Summoner and Jessica identity references; no prior AI input",
        "identity_coordinates": "unshifted source coordinates; editor final +1 translation intentionally not applied",
        "all_accepted": all(row["accepted"] for row in rows),
        "variants": rows,
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    report = build()
    print(json.dumps({
        "all_accepted": report["all_accepted"],
        "variants": [row["variant"] for row in report["variants"]],
    }, ensure_ascii=False, indent=2))
    return 0 if report["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
