#!/usr/bin/env python3
"""Build five standalone native-16 Elwin Hero design samples.

The five built-in imagegen sources are used only as equipment/composition
references.  Every shipped sprite is repixelled by hand at 16x16, then the
current 73-point ROM identity is copied back exactly.
"""

from __future__ import annotations

from collections import Counter, deque
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "assets/class-sprites/source/latest/sample-class-variants-v1/elwin-hero"
)
AI_DIR = OUTPUT / "ai"
LOGICAL_DIR = OUTPUT / "logical16"
PREVIEW_DIR = OUTPUT / "previews"
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
SKIN = (219, 182, 109, 255)

VARIANT_NAMES = {
    1: "정통 대검 영웅",
    2: "넓은 견갑·한손 장검",
    3: "전방 검·비대칭 갑옷",
    4: "세로 검·왕도 중갑",
    5: "역동 사선 검·풍성한 망토",
}


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
) -> None:
    for point in identity:
        image.putpixel(point, original.getpixel(point))


def diagonal_blade(image: Image.Image, *, broad: bool = False) -> None:
    """Draw a continuous image-left diagonal blade behind the locked head."""
    outline = {
        (0, 0), (0, 1), (1, 1), (1, 2), (2, 2), (2, 3),
        (1, 3), (1, 4), (2, 4), (1, 5), (2, 5),
        (2, 6), (2, 7), (3, 7), (3, 8), (4, 8),
    }
    if broad:
        outline |= {(0, 2), (0, 3), (0, 4), (1, 6), (2, 8)}
    paint(image, outline, INK)
    paint(
        image,
        {
            (0, 0), (1, 1), (2, 2), (2, 3), (1, 4),
            (2, 5), (2, 6), (3, 7), (4, 8),
        },
        SILVER,
    )
    paint(
        image,
        {
            (1, 0), (2, 1), (3, 2), (1, 3), (2, 4),
            (1, 5), (3, 6), (4, 7), (5, 8),
        },
        WHITE,
    )


def variant_01(original: Image.Image, identity: set[tuple[int, int]]) -> Image.Image:
    """Traditional diagonal greatsword, steel armor, blue core, right cape."""
    image = Image.new("RGBA", (16, 16), TRANSPARENT)

    paint(
        image,
        {(14, 8), (13, 9), (14, 9), (15, 9)}
        | rect(12, 10, 15, 12)
        | rect(11, 13, 15, 14)
        | {(13, 15), (14, 15), (15, 15)},
        RED_DARK,
    )
    paint(
        image,
        {(15, 9), (15, 10), (14, 11), (15, 11),
         (14, 12), (15, 12), (13, 13), (14, 13), (14, 14)},
        RED,
    )
    diagonal_blade(image, broad=True)

    paint(image, rect(4, 9, 11, 14), INK)
    paint(image, {(6, 9), (7, 9), (8, 9), (9, 9)}, INK)
    paint(image, {(5, 9), (10, 9)}, GOLD)
    paint(image, {(6, y) for y in range(10, 15)} | {(10, y) for y in range(10, 15)}, BLUE_DARK)
    paint(image, rect(7, 10, 9, 14), BLUE)
    paint(image, {(7, 13), (8, 13), (9, 13)}, GOLD)

    paint(image, rect(3, 8, 6, 10) | rect(10, 8, 14, 10), INK)
    paint(image, {(3, 8), (4, 8), (5, 8), (11, 8), (12, 8), (13, 8),
                  (3, 9), (11, 9), (12, 9), (13, 9)}, SILVER)
    paint(image, {(4, 8), (12, 8), (13, 9)}, WHITE)
    paint(image, {(5, 8), (10, 8), (3, 9), (11, 9)}, GOLD)

    paint(image, {(2, 9), (3, 9), (4, 9), (5, 9)}, INK)
    paint(image, {(3, 9), (4, 9), (5, 9)}, GOLD)
    paint(image, {(3, 10), (4, 10), (5, 10)}, INK)
    paint(image, {(4, 10)}, GOLD)
    paint(image, {(3, 11), (4, 11), (5, 11)}, INK)
    paint(image, {(4, 11), (5, 11)}, SILVER)

    paint(image, {(11, 10), (12, 10), (13, 10), (14, 10)}, INK)
    paint(image, {(11, 10), (12, 10)}, SILVER)
    paint(image, {(13, 10)}, GOLD)
    paint(image, {(12, 11), (13, 11), (14, 11)}, INK)
    paint(image, {(12, 11)}, SILVER)
    paint(image, {(14, 9), (14, 10), (13, 11), (12, 12)}, INK)

    paint(image, rect(3, 12, 6, 14) | rect(10, 12, 13, 14), INK)
    paint(image, {(4, 12), (5, 12), (5, 13), (4, 14), (5, 14),
                  (11, 12), (12, 12), (11, 13), (11, 14), (12, 14)}, SILVER)
    paint(image, {(5, 12), (11, 12)}, WHITE)
    paint(image, {(4, 13), (12, 13)}, GOLD)
    paint(image, rect(2, 15, 7, 15) | rect(9, 15, 13, 15), INK)
    paint(image, {(3, 15), (4, 15), (5, 15), (10, 15), (11, 15), (12, 15)}, SILVER)

    paint(image, {(4, 8)}, SILVER)
    paint(image, {(5, 8)}, WHITE)
    paint(image, {(4, 9)}, GOLD)
    paint(image, {(4, 10)}, GOLD)
    paint(image, {(4, 11), (5, 11)}, SILVER)
    restore_identity(image, original, identity)
    return image


def variant_02(original: Image.Image, identity: set[tuple[int, int]]) -> Image.Image:
    """Broad shoulders, narrow one-handed vertical sword, compact cape."""
    image = Image.new("RGBA", (16, 16), TRANSPARENT)

    paint(image, rect(13, 9, 15, 14) | {(14, 15), (15, 15)}, RED_DARK)
    paint(image, {(15, 9), (15, 10), (14, 11), (15, 11),
                  (14, 12), (15, 12), (15, 13)}, RED)

    # A narrow inward-leaning one-handed blade, clearly shorter and lighter
    # than sample 01's greatsword and sample 04's full vertical sword.
    paint(
        image,
        {(0, 0), (0, 1), (1, 1), (1, 2), (2, 2),
         (0, 3), (1, 3), (2, 3), (1, 4), (2, 4),
         (1, 5), (2, 5), (3, 5), (2, 6), (3, 6),
         (3, 7), (4, 7), (4, 8), (5, 8)},
        INK,
    )
    paint(
        image,
        {(0, 0), (1, 1), (2, 2), (1, 3), (2, 4),
         (2, 5), (3, 6), (4, 7), (5, 8)},
        SILVER,
    )
    paint(
        image,
        {(1, 0), (2, 1), (3, 2), (0, 3), (1, 4),
         (1, 5), (2, 6), (3, 7), (4, 8)},
        WHITE,
    )

    paint(image, rect(3, 8, 6, 10) | rect(9, 8, 15, 10), INK)
    paint(image, rect(3, 8, 5, 9) | rect(11, 8, 14, 9), SILVER)
    paint(image, {(3, 8), (4, 8), (12, 8), (13, 8), (14, 9)}, WHITE)
    paint(image, {(5, 9), (10, 9), (11, 9)}, GOLD)

    paint(image, rect(4, 9, 12, 14), INK)
    paint(image, {(5, 9), (6, 9), (9, 9), (10, 9), (11, 9)}, SILVER)
    paint(image, {(6, y) for y in range(10, 15)} | {(10, y) for y in range(10, 15)}, BLUE_DARK)
    paint(image, rect(7, 10, 9, 14), BLUE)
    paint(image, {(7, 12), (8, 12), (9, 12)}, GOLD)

    paint(image, {(0, 9), (1, 9), (2, 9), (3, 9), (4, 9)}, INK)
    paint(image, {(1, 9), (2, 9), (3, 9)}, GOLD)
    paint(image, {(2, 10)}, GOLD)
    paint(image, {(2, 10), (3, 10), (4, 10), (3, 11), (4, 11)}, INK)
    paint(image, {(2, 10)}, GOLD)
    paint(image, {(3, 11), (4, 11)}, SILVER)

    paint(image, {(12, 10), (13, 10), (14, 10)}, INK)
    paint(image, {(12, 10), (13, 10)}, SILVER)
    paint(image, {(13, 11)}, GOLD)
    paint(image, {(12, 11), (13, 11), (14, 11)}, INK)
    paint(image, {(12, 11)}, SILVER)
    paint(image, {(14, 9), (14, 10), (14, 11), (13, 12)}, INK)

    paint(image, rect(4, 12, 7, 14) | rect(9, 12, 12, 14), INK)
    paint(image, {(5, 12), (6, 12), (5, 13), (4, 14), (5, 14),
                  (10, 12), (11, 12), (11, 13), (11, 14), (12, 14)}, SILVER)
    paint(image, {(5, 13), (11, 13)}, WHITE)
    paint(image, {(4, 13), (12, 13)}, GOLD)
    paint(image, rect(3, 15, 7, 15) | rect(9, 15, 13, 15), INK)
    paint(image, {(4, 15), (5, 15), (6, 15), (10, 15), (11, 15), (12, 15)}, SILVER)

    restore_identity(image, original, identity)
    return image


def variant_03(original: Image.Image, identity: set[tuple[int, int]]) -> Image.Image:
    """Forward blade, compact sword arm, oversized opposite pauldron."""
    image = Image.new("RGBA", (16, 16), TRANSPARENT)

    paint(image, {(15, 9)} | rect(14, 10, 15, 14) | {(15, 15)}, RED_DARK)
    paint(image, {(15, 10), (15, 11), (14, 12), (15, 12), (15, 13)}, RED)

    paint(
        image,
        {(0, 0), (0, 1), (1, 1), (1, 2), (2, 2),
         (0, 3), (1, 3), (2, 3), (0, 4), (1, 4), (2, 4), (3, 4),
         (1, 5), (2, 5), (3, 5), (4, 5),
         (2, 6), (3, 6), (4, 6), (3, 7), (4, 7), (5, 7),
         (4, 8), (5, 8), (6, 8)},
        INK,
    )
    paint(image, {(0, 0), (1, 1), (2, 2), (0, 3), (1, 4),
                  (2, 5), (3, 6), (4, 7), (5, 8)}, SILVER)
    paint(image, {(1, 0), (2, 1), (3, 2), (1, 3), (2, 4),
                  (3, 5), (4, 6), (5, 7), (6, 8)}, WHITE)

    paint(image, rect(5, 9, 11, 14), INK)
    paint(image, {(6, 9), (7, 9), (8, 9), (9, 9)}, INK)
    paint(image, {(5, 9), (10, 9)}, GOLD)
    paint(image, {(6, y) for y in range(10, 15)} | {(10, y) for y in range(10, 15)}, BLUE_DARK)
    paint(image, rect(7, 10, 9, 14), BLUE)
    paint(image, {(7, 13), (8, 13), (9, 13)}, GOLD)

    paint(image, rect(4, 8, 7, 10), INK)
    paint(image, {(5, 8), (6, 8), (5, 9), (6, 9)}, SILVER)
    paint(image, {(6, 8)}, WHITE)
    paint(image, {(5, 9)}, GOLD)
    paint(image, rect(10, 7, 15, 10), INK)
    paint(image, rect(11, 8, 14, 9), SILVER)
    paint(image, {(12, 8), (13, 8), (14, 9)}, WHITE)
    paint(image, {(10, 8), (11, 9), (13, 10)}, GOLD)

    paint(image, {(3, 9), (4, 9), (5, 9), (6, 9)}, INK)
    paint(image, {(4, 9), (5, 9), (6, 9)}, GOLD)
    paint(image, {(4, 10), (5, 10), (6, 10)}, INK)
    paint(image, {(5, 10)}, GOLD)
    paint(image, {(5, 11), (6, 11), (7, 11)}, INK)
    paint(image, {(5, 11), (6, 11)}, SILVER)

    paint(image, {(11, 10), (12, 10), (13, 10), (14, 10)}, INK)
    paint(image, {(11, 10), (12, 10)}, SILVER)
    paint(image, {(13, 10)}, GOLD)
    paint(image, {(12, 11), (13, 11), (14, 11)}, INK)
    paint(image, {(12, 11)}, SILVER)
    paint(image, {(14, 9), (14, 10), (13, 11), (13, 12)}, INK)

    paint(image, rect(3, 12, 6, 14) | rect(9, 11, 13, 14), INK)
    paint(image, {(4, 12), (5, 12), (4, 13), (5, 13), (4, 14),
                  (10, 12), (11, 12), (11, 13), (12, 13), (12, 14)}, SILVER)
    paint(image, {(4, 12), (11, 12)}, WHITE)
    paint(image, {(3, 13), (12, 14)}, GOLD)
    paint(image, rect(2, 15, 7, 15) | rect(9, 15, 14, 15), INK)
    paint(image, {(3, 15), (4, 15), (5, 15), (10, 15), (11, 15), (12, 15)}, SILVER)

    restore_identity(image, original, identity)
    return image


def variant_04(original: Image.Image, identity: set[tuple[int, int]]) -> Image.Image:
    """Tall vertical sword and orderly royal heavy armor."""
    image = Image.new("RGBA", (16, 16), TRANSPARENT)

    paint(image, rect(13, 9, 15, 14) | {(14, 15), (15, 15)}, RED_DARK)
    paint(image, {(15, 10), (15, 11), (14, 12), (15, 12), (14, 13)}, RED)

    paint(image, {(0, y) for y in range(0, 11)} | {(1, y) for y in range(0, 10)}, INK)
    paint(image, {(1, y) for y in range(0, 9)}, SILVER)
    paint(image, {(2, y) for y in range(1, 9)}, WHITE)
    paint(image, {(1, 0)}, WHITE)

    paint(image, rect(3, 8, 6, 10) | rect(10, 8, 14, 10), INK)
    paint(image, rect(4, 8, 6, 9) | rect(11, 8, 13, 9), SILVER)
    paint(image, {(4, 8), (5, 8), (12, 8), (13, 9)}, WHITE)
    paint(image, {(3, 9), (6, 9), (10, 9), (14, 9)}, GOLD)

    paint(image, rect(5, 9, 11, 14), INK)
    paint(image, {(6, 9), (7, 9), (8, 9), (9, 9), (10, 9)}, SILVER)
    paint(image, {(6, y) for y in range(10, 15)} | {(10, y) for y in range(10, 15)}, BLUE_DARK)
    paint(image, rect(7, 10, 9, 14), BLUE)
    paint(image, {(7, 10), (8, 10), (9, 10)}, GOLD)
    paint(image, {(7, 13), (8, 13), (9, 13)}, GOLD)

    paint(image, {(0, 9), (1, 9), (2, 9), (3, 9), (4, 9)}, INK)
    paint(image, {(1, 9), (2, 9), (3, 9)}, GOLD)
    paint(image, {(2, 10)}, GOLD)
    paint(image, {(2, 10), (3, 10), (4, 10), (3, 11), (4, 11)}, INK)
    paint(image, {(2, 10)}, GOLD)
    paint(image, {(3, 11), (4, 11)}, SILVER)

    paint(image, {(11, 10), (12, 10), (13, 10), (14, 10)}, INK)
    paint(image, {(11, 10), (12, 10), (12, 11)}, SILVER)
    paint(image, {(13, 10)}, GOLD)
    paint(image, {(12, 11), (13, 11), (14, 11)}, INK)
    paint(image, {(12, 11)}, SILVER)
    paint(image, {(14, 9), (14, 10), (13, 11), (13, 12)}, INK)

    paint(image, rect(4, 12, 6, 14) | rect(10, 12, 12, 14), INK)
    paint(image, {(4, 12), (5, 12), (5, 13), (4, 14), (5, 14),
                  (11, 12), (12, 12), (11, 13), (11, 14), (12, 14)}, SILVER)
    paint(image, {(5, 12), (11, 12)}, WHITE)
    paint(image, {(4, 13), (12, 13)}, GOLD)
    paint(image, rect(3, 15, 7, 15) | rect(9, 15, 13, 15), INK)
    paint(image, {(4, 15), (5, 15), (6, 15), (10, 15), (11, 15), (12, 15)}, SILVER)

    restore_identity(image, original, identity)
    return image


def variant_05(original: Image.Image, identity: set[tuple[int, int]]) -> Image.Image:
    """Dynamic diagonal blade and the largest layered right-side cape."""
    image = Image.new("RGBA", (16, 16), TRANSPARENT)

    paint(
        image,
        {(14, 7), (15, 7)}
        | rect(13, 8, 15, 8)
        | rect(12, 9, 15, 10)
        | rect(10, 11, 15, 12)
        | rect(9, 13, 15, 14)
        | rect(11, 15, 15, 15),
        RED_DARK,
    )
    paint(
        image,
        {(15, 8), (14, 9), (15, 9), (14, 10), (15, 10),
         (13, 11), (14, 11), (15, 11), (12, 12), (14, 12), (15, 12),
         (11, 13), (13, 13), (15, 13), (12, 14), (14, 14)},
        RED,
    )
    diagonal_blade(image, broad=True)

    paint(image, rect(5, 9, 11, 14), INK)
    paint(image, {(6, 9), (7, 9), (8, 9), (9, 9)}, INK)
    paint(image, {(5, 9), (10, 9)}, GOLD)
    paint(image, {(6, y) for y in range(10, 15)} | {(9, y) for y in range(10, 15)}, BLUE_DARK)
    paint(image, rect(7, 10, 8, 14), BLUE)
    paint(image, {(7, 12), (8, 12)}, GOLD)

    paint(image, rect(3, 8, 7, 10), INK)
    paint(image, {(4, 8), (5, 8), (6, 8), (4, 9), (5, 9)}, SILVER)
    paint(image, {(5, 8), (6, 9)}, WHITE)
    paint(image, {(3, 9), (5, 9)}, GOLD)
    paint(image, rect(10, 7, 14, 10), INK)
    paint(image, {(11, 8), (12, 8), (13, 8), (11, 9), (12, 9)}, SILVER)
    paint(image, {(12, 8), (13, 9)}, WHITE)
    paint(image, {(10, 8), (11, 9)}, GOLD)

    paint(image, {(2, 9), (3, 9), (4, 9), (5, 9)}, INK)
    paint(image, {(3, 9), (4, 9), (5, 9)}, GOLD)
    paint(image, {(3, 10), (4, 10), (5, 10)}, INK)
    paint(image, {(4, 10)}, GOLD)
    paint(image, {(4, 11), (5, 11), (6, 11)}, INK)
    paint(image, {(4, 11), (5, 11)}, SILVER)

    paint(image, {(11, 10), (12, 10), (13, 10), (14, 10)}, INK)
    paint(image, {(11, 10), (12, 10)}, SILVER)
    paint(image, {(13, 10)}, GOLD)
    paint(image, {(12, 11), (13, 11), (14, 11)}, INK)
    paint(image, {(12, 11)}, SILVER)
    paint(image, {(14, 9), (14, 10), (13, 11), (12, 12), (11, 13)}, INK)

    paint(image, rect(2, 12, 6, 14) | rect(9, 11, 13, 14), INK)
    paint(image, {(3, 12), (4, 12), (4, 13), (3, 14),
                  (10, 11), (11, 12), (12, 12), (11, 13), (12, 14)}, SILVER)
    paint(image, {(4, 12), (11, 12)}, WHITE)
    paint(image, {(2, 13), (12, 13)}, GOLD)
    paint(image, rect(1, 15, 7, 15) | rect(9, 15, 14, 15), INK)
    paint(image, {(2, 15), (3, 15), (4, 15), (10, 15), (11, 15), (12, 15)}, SILVER)

    paint(image, {(4, 8)}, SILVER)
    paint(image, {(5, 8)}, WHITE)
    paint(image, {(4, 9)}, GOLD)
    paint(image, {(4, 10)}, GOLD)
    paint(image, {(4, 11), (5, 11)}, SILVER)
    paint(image, {(14, 9), (14, 10), (13, 11), (12, 12), (11, 13)}, INK)
    restore_identity(image, original, identity)
    return image


BUILDERS = {
    1: variant_01,
    2: variant_02,
    3: variant_03,
    4: variant_04,
    5: variant_05,
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
    counts = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common()
    ]


def preview(image: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", (512, 512), (210, 210, 210, 255))
    canvas.alpha_composite(image.resize((512, 512), Image.Resampling.NEAREST))
    return canvas


def sanitize_ai_source(path: Path) -> Image.Image:
    """Keep generated alpha art but replace prohibited exact black locally."""
    source = Image.open(path).convert("RGBA")
    changed = False
    pixels: list[tuple[int, int, int, int]] = []
    for red, green, blue, alpha in source.getdata():
        if alpha and red == green == blue == 0:
            pixels.append((INK[0], INK[1], INK[2], alpha))
            changed = True
        else:
            pixels.append((red, green, blue, alpha))
    if changed:
        source.putdata(pixels)
        source.save(path, optimize=True)
    return source


def build() -> dict[str, object]:
    for directory in (LOGICAL_DIR, PREVIEW_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    original = Image.open(ROM_SPRITE).convert("RGBA")
    identity = {
        tuple(point)
        for point in json.loads(MASK_FILE.read_text(encoding="utf-8"))["masks"]["1:22"]
    }
    reports: dict[str, object] = {}
    images: dict[int, Image.Image] = {}

    for index, builder in BUILDERS.items():
        key = f"{index:02d}"
        source_path = AI_DIR / f"{key}.png"
        source = sanitize_ai_source(source_path)
        image = builder(original, identity)
        images[index] = image

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
        face_color_contamination = [
            [x, y]
            for y in range(16)
            for x in range(16)
            if (x, y) not in identity
            and image.getpixel((x, y)) in {SKIN, BROWN}
        ]
        center_holes = [
            [x, y]
            for y in range(10, 14)
            for x in range(6, 11)
            if not image.getpixel((x, y))[3]
        ]
        source_corners_transparent = all(
            source.getpixel(point)[3] == 0
            for point in ((0, 0), (source.width - 1, 0),
                          (0, source.height - 1),
                          (source.width - 1, source.height - 1))
        )
        source_alpha_coverage = round(
            sum(color[3] > 0 for color in source.getdata())
            / (source.width * source.height),
            6,
        )
        source_pure_black = any(
            alpha and red == green == blue == 0
            for red, green, blue, alpha in source.getdata()
        )
        source_green_contamination = sum(
            bool(alpha and green > 180 and green > red * 1.5 and green > blue * 1.5)
            for red, green, blue, alpha in source.getdata()
        )
        source_magenta_contamination = sum(
            bool(alpha and red > 200 and blue > 200 and green < 80)
            for red, green, blue, alpha in source.getdata()
        )
        accepted = (
            image.size == (16, 16)
            and identity_match == len(identity)
            and len(palette) <= 15
            and len(components) == 1
            and not empty_rows
            and not empty_columns
            and not pure_black
            and not magenta
            and not face_color_contamination
            and not center_holes
            and source_corners_transparent
            and not source_pure_black
            and not source_green_contamination
            and not source_magenta_contamination
        )
        reports[key] = {
            "name": VARIANT_NAMES[index],
            "ai_source": str(source_path.relative_to(ROOT)),
            "ai_source_size": list(source.size),
            "ai_source_alpha_coverage": source_alpha_coverage,
            "ai_source_corners_transparent": source_corners_transparent,
            "ai_source_pure_black": source_pure_black,
            "ai_source_green_contamination_pixels": source_green_contamination,
            "ai_source_magenta_contamination_pixels": source_magenta_contamination,
            "native_size": list(image.size),
            "identity_match": identity_match,
            "identity_pixel_count": len(identity),
            "visible_color_count": len(palette),
            "palette": palette,
            "opaque_pixels": sum(color[3] > 0 for color in image.getdata()),
            "connected_components": components,
            "empty_rows": empty_rows,
            "empty_columns": empty_columns,
            "center_holes": center_holes,
            "face_color_contamination": face_color_contamination,
            "pure_black": pure_black,
            "magenta_contamination": magenta,
            "accepted": accepted,
        }
        if not accepted:
            raise ValueError(f"invalid Elwin Hero sample {key}: {reports[key]}")
        image.save(LOGICAL_DIR / f"{key}.png", optimize=True)
        preview(image).save(PREVIEW_DIR / f"{key}.png", optimize=True)

    hashes = {
        hashlib.sha256(images[index].tobytes()).hexdigest()
        for index in images
    }
    if len(hashes) != len(images):
        raise ValueError("native Elwin Hero samples must all be distinct")

    cell = 256
    contact = Image.new("RGBA", (cell * 5, 552), (210, 210, 210, 255))
    draw = ImageDraw.Draw(contact)
    for index in range(1, 6):
        key = f"{index:02d}"
        source = Image.open(AI_DIR / f"{key}.png").convert("RGBA")
        source.thumbnail((cell, cell), Image.Resampling.LANCZOS)
        source_canvas = Image.new("RGBA", (cell, cell), (210, 210, 210, 255))
        source_canvas.alpha_composite(
            source,
            ((cell - source.width) // 2, (cell - source.height) // 2),
        )
        contact.alpha_composite(source_canvas, ((index - 1) * cell, 24))
        contact.alpha_composite(
            images[index].resize((cell, cell), Image.Resampling.NEAREST),
            ((index - 1) * cell, 296),
        )
        draw.text(((index - 1) * cell + 8, 6), f"{key} {VARIANT_NAMES[index]}", fill=INK)
        draw.text(((index - 1) * cell + 8, 278), "native 16x16", fill=INK)
    contact.save(OUTPUT / "all-elwin-hero-samples.png", optimize=True)

    report = {
        "version": 1,
        "generation_mode": "built-in image_gen; five independent calls",
        "first_generation_inputs": [
            "assets/class-sprites/source/latest/elwin-hero-ai-v7-anatomy/references/elwin-hero-rom-original-neutral-32x.png",
            "assets/class-sprites/source/latest/elwin-hero-ai-v7-anatomy/references/elwin-hero-identity-73px-neutral-32x.png",
        ],
        "previous_ai_used": False,
        "native_method": "designer repixel at 16x16 + exact 73-point ROM identity restore",
        "all_distinct": len(hashes) == 5,
        "all_accepted": all(item["accepted"] for item in reports.values()),
        "variants": reports,
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    build()
