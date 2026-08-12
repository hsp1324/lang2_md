#!/usr/bin/env python3
"""Build Elwin Hero v6 from the fresh three-quarter AI concept.

The AI render is deliberately repixelled instead of automatically resized: its
left diagonal sword, asymmetric steel shoulders, blue tabard, and right-side
red cape are reduced to native 16x16 clusters while the current editor identity
mask is restored exactly.
"""

from __future__ import annotations

from collections import Counter, deque
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/class-sprites/source/latest/elwin-hero-ai-v6-fresh"
CANDIDATE = OUTPUT / "candidates/hero-fresh-three-quarter-simple-v2.png"
ROM_SPRITE = ROOT / "editor/static/class-sprites/commanders/1/22-p1.png"
MASK_FILE = ROOT / "editor/ai_identity_masks.json"

TRANSPARENT = (0, 0, 0, 0)
INK = (36, 36, 36, 255)
WHITE = (255, 255, 255, 255)
SILVER = (146, 146, 146, 255)
RED_DARK = (109, 0, 0, 255)
RED = (219, 0, 0, 255)
BLUE_DARK = (73, 73, 109, 255)
BLUE = (36, 73, 219, 255)
GOLD = (255, 182, 0, 255)
BROWN = (146, 73, 36, 255)


def visible_palette(image: Image.Image) -> list[str]:
    counts = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common()
    ]


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


def draw_native_hero(
    original: Image.Image,
    identity: set[tuple[int, int]],
) -> Image.Image:
    """Reduce the selected AI concept to readable native pixel clusters."""
    result = Image.new("RGBA", (16, 16), TRANSPARENT)

    def paint(points: set[tuple[int, int]], color: tuple[int, int, int, int]) -> None:
        for x, y in points:
            if (x, y) not in identity:
                result.putpixel((x, y), color)

    def rect(x0: int, y0: int, x1: int, y1: int) -> set[tuple[int, int]]:
        return {
            (x, y)
            for y in range(y0, y1 + 1)
            for x in range(x0, x1 + 1)
        }

    # AI concept: one connected diagonal greatsword on image-left.  These
    # bridge cells connect the two white pixels already included in the user's
    # current head mask instead of leaving them floating in the background.
    paint({(0, 0), (0, 1), (1, 1), (1, 2), (2, 2), (2, 3)}, INK)
    paint({(0, 0), (1, 1), (2, 2)}, SILVER)
    paint({(1, 0), (2, 1), (3, 2)}, WHITE)
    paint({(1, 3), (2, 3), (1, 4), (2, 4), (1, 5), (2, 5),
           (2, 6), (2, 7), (3, 7), (3, 8), (4, 8)}, INK)
    # Route the bright blade edge around the locked red hair pixels.  It reads
    # as a sword passing behind the head instead of a blade with red holes.
    paint({(2, 3), (1, 4), (2, 5), (2, 6), (3, 7), (4, 8)}, SILVER)
    paint({(1, 3), (1, 5), (2, 6), (3, 8)}, WHITE)

    # AI concept: a deep red cape concentrated behind the image-right armor,
    # with only a small left tail so the pose stays three-quarter, not frontal.
    paint(rect(9, 7, 13, 14) | rect(12, 9, 15, 14), RED_DARK)
    paint({(14, 9), (14, 10), (15, 10), (15, 11), (15, 12),
           (14, 13), (13, 14)}, RED)

    # Asymmetric shoulders: compact sword arm on the left and a large bright
    # pauldron on the right, matching the fresh AI pose.
    paint(rect(3, 8, 6, 11) | rect(10, 7, 14, 11), INK)
    paint({(3, 8), (4, 8), (4, 9), (5, 9), (11, 7), (12, 7),
           (13, 7), (11, 8), (12, 8), (13, 8), (14, 8),
           (12, 9), (13, 9), (14, 9)}, SILVER)
    paint({(4, 9), (12, 7), (13, 8), (14, 9)}, WHITE)
    paint({(3, 9), (5, 8), (10, 8), (11, 9), (13, 10)}, GOLD)
    # Cape cloth begins directly behind the right pauldron instead of as a
    # one-pixel red pole that suddenly widens near the feet.
    paint({(14, 10), (13, 11), (14, 11)}, RED_DARK)
    paint({(15, 9), (15, 10), (14, 11), (15, 11)}, RED)

    # Hilt, hand, and sword arm form one continuous cluster.
    paint({(1, 9), (2, 9), (3, 9), (4, 9), (2, 10), (3, 10),
           (4, 10), (4, 11)}, INK)
    paint({(1, 9), (2, 10), (3, 9)}, GOLD)
    paint({(3, 10), (4, 10)}, BROWN)

    # Closed steel torso with large clusters, a blue tabard, and restrained
    # gold separators.  No checkerboard highlights and no central alpha hole.
    paint(rect(5, 9, 11, 13), INK)
    paint({(5, 9), (6, 9), (7, 9), (8, 9), (9, 9), (10, 9),
           (6, 10), (7, 10), (8, 10), (9, 10), (10, 10),
           (5, 11), (10, 11)}, SILVER)
    # A dark neck/armor separator prevents the head underside from reading as
    # a second large white mouth.  White is one restrained armor highlight.
    paint({(6, 9), (7, 9), (9, 9)}, INK)
    paint({(8, 9)}, WHITE)
    paint({(5, 10), (10, 10), (5, 12), (10, 12)}, GOLD)
    paint({(7, 10), (8, 10), (7, 11), (8, 11),
           (7, 12), (8, 12), (7, 13), (8, 13)}, BLUE)
    paint({(6, 11), (9, 11), (6, 12), (9, 12), (6, 13), (9, 13)}, BLUE_DARK)

    # Two distinct armored legs and grounded feet.  The x8 separator prevents
    # the former single-platform silhouette while the cape still reaches x15.
    paint(rect(4, 12, 6, 14) | rect(9, 12, 11, 14), INK)
    paint({(5, 12), (6, 12), (9, 12), (10, 12),
           (5, 13), (10, 13), (4, 14), (5, 14), (10, 14), (11, 14)}, SILVER)
    paint({(5, 13), (10, 13)}, WHITE)
    paint({(4, 13), (11, 13), (5, 14), (10, 14)}, GOLD)
    paint(rect(3, 15, 6, 15) | rect(9, 15, 12, 15), INK)
    paint({(4, 15), (5, 15), (10, 15), (11, 15)}, SILVER)

    # Extend only the image-left boot by one cell: the former two-column gap
    # becomes a single dark separator while the two feet remain distinct.
    paint({(7, 15)}, INK)

    # Reassert the sword-to-hilt bridge after armor layering.  This is the
    # 16x16 reduction of the AI candidate's long continuous diagonal blade.
    paint({(4, 8)}, SILVER)
    paint({(5, 8)}, WHITE)
    paint({(4, 9)}, GOLD)

    # Restore the exact current identity last, including eyes, sclera, hair,
    # face, and the head-crossing part of the original diagonal blade.
    for point in identity:
        result.putpixel(point, original.getpixel(point))
    return result


def build() -> dict[str, object]:
    original = Image.open(ROM_SPRITE).convert("RGBA")
    candidate = Image.open(CANDIDATE).convert("RGBA")
    masks = json.loads(MASK_FILE.read_text(encoding="utf-8"))["masks"]
    identity = {tuple(point) for point in masks["1:22"]}
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
    pure_black = (0, 0, 0, 255) in image.getdata()
    magenta = any(
        color[3] and color[0] > 200 and color[2] > 200 and color[1] < 80
        for color in image.getdata()
    )
    accepted = (
        identity_match == len(identity)
        and len(palette) <= 15
        and components == [sum(components)]
        and not empty_rows
        and not empty_columns
        and not pure_black
        and not magenta
    )
    if not accepted:
        raise ValueError(
            "invalid Hero v6: "
            f"identity={identity_match}/{len(identity)}, palette={len(palette)}, "
            f"components={components}, rows={empty_rows}, columns={empty_columns}, "
            f"black={pure_black}, magenta={magenta}"
        )

    logical_dir = OUTPUT / "logical16"
    preview_dir = OUTPUT / "previews"
    selected_dir = OUTPUT / "selected-sources"
    for directory in (logical_dir, preview_dir, selected_dir):
        directory.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT / "22-hero.png", optimize=True)
    image.save(logical_dir / "22-hero.png", optimize=True)
    image.resize((512, 512), Image.Resampling.NEAREST).save(
        preview_dir / "22-hero.png", optimize=True
    )
    candidate.save(selected_dir / "22-hero-ai.png", optimize=True)

    comparison = Image.new("RGBA", (768, 288), (210, 210, 210, 255))
    draw = ImageDraw.Draw(comparison)
    for index, (label, sprite) in enumerate((
        ("ROM identity", original),
        ("previous Hero", Image.open(
            ROOT / "assets/class-sprites/source/latest/elwin-hero-ai-v5-fresh/22-hero.png"
        ).convert("RGBA")),
        ("fresh AI repixel v6", image),
    )):
        comparison.alpha_composite(
            sprite.resize((256, 256), Image.Resampling.NEAREST),
            (index * 256, 32),
        )
        draw.text((index * 256 + 8, 8), label, fill=(24, 24, 24, 255))
    comparison.save(OUTPUT / "elwin-hero-v6-comparison.png", optimize=True)

    report = {
        "source": str(CANDIDATE.relative_to(ROOT)),
        "source_size": list(candidate.size),
        "native_size": [16, 16],
        "input_policy": "original ROM sprite + current identity mask only",
        "repixel_mapping": [
            "single diagonal image-left sword",
            "asymmetric steel pauldrons",
            "closed steel torso and blue tabard",
            "deep-red right-side cape",
            "two separated armored feet",
        ],
        "identity_match": identity_match,
        "identity_pixel_count": len(identity),
        "visible_color_count": len(palette),
        "palette": palette,
        "connected_components": components,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "pure_black": pure_black,
        "magenta_contamination": magenta,
        "accepted": accepted,
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
