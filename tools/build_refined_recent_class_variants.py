#!/usr/bin/env python3
"""Refine only the six recently requested class families.

Healer (08) is copied byte-for-byte at the pixel level from v1.  Wizard and
High Priest restore the previously user-approved sources that v1 accidentally
overrode.  Sage, Summoner, Agent, and Zarvera use stable per-character donors
plus role-aware native-16 repairs instead of a single HSV-recolored master.
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

from tools.build_ai_class_sprite_assets import load_identity_mask_overrides
from tools.build_class_sprite_assets import DEFAULT_ROM, commander_sprite_map, render_sprite
from tools.build_liana_lana_native16_assets import limit_visible_palette
from tools.build_shared_new_class_variants import (
    CLASS_SPECS,
    COMMANDER_RAMPS,
    IDENTITY_MASK_EXCLUDED_POINTS,
    resolve_identity_points,
    validate,
)
from tools.scenario_data import KOREAN_NAME_BY_ID


OUTPUT = ROOT / "assets/class-sprites/source/latest/shared-new-classes-v2-refined"
V1 = ROOT / "assets/class-sprites/source/latest/shared-new-classes-v1"
TRANSPARENT = (0, 0, 0, 0)
INK = (36, 36, 36, 255)
GRAY = (73, 73, 109, 255)
SILVER = (146, 146, 146, 255)
WHITE = (255, 255, 255, 255)
GOLD = (255, 182, 0, 255)
WOOD = (109, 73, 36, 255)
DARK_WOOD = (73, 36, 36, 255)
VIOLET_DARK = (36, 36, 73, 255)
VIOLET = (73, 36, 109, 255)
JESSICA_WIZARD_NEAR_PURPLE = (146, 36, 182, 255)
JESSICA_WIZARD_MAIN_PURPLE = (146, 73, 182, 255)
JESSICA_WIZARD_RARE_EQUIPMENT_BLUE = (36, 73, 255, 255)
JESSICA_WIZARD_MAIN_BLUE = (73, 109, 255, 255)
KEITH_HEALER_SKY_MAP = {
    (0, 146, 109, 255): (73, 109, 255, 255),
    (36, 219, 146, 255): (109, 219, 255, 255),
}


REFINED_CLASS_IDS = (0x15, 0x16, 0x18, 0x28, 0x25, 0x26)


def stable_donor(commander_id: int, class_id: int) -> tuple[Path | None, str]:
    """Return the approved or best target-specific source for this target."""
    if class_id == 0x15:
        if commander_id == 5:
            return (
                ROOT / "assets/class-sprites/source/latest/hein/logical16/15-wizard.png",
                "사용자 승인 헤인 위저드",
            )
        return (
            ROOT
            / "assets/class-sprites/source/latest/shared-wizard-hein-v1/logical16"
            / f"{commander_id:02d}-15.png",
            "사용자 승인 헤인 위저드 캐릭터별 변형",
        )
    if class_id == 0x16:
        if commander_id == 8:
            return None, "아론 고유 원본 하이프리스트 유지"
        return (
            ROOT
            / "assets/class-sprites/source/latest/shared-hein-classes-v1/logical16"
            / f"{commander_id:02d}-16.png",
            "사용자 승인 헤인 하이프리스트 캐릭터별 변형",
        )
    if class_id == 0x18 and commander_id in (2, 3):
        color = "red" if commander_id == 2 else "blue"
        return (
            ROOT
            / "assets/class-sprites/source/latest/liana-lana-strict16-v1"
            / f"native16-{color}/18.png",
            "리아나·라나 승인 세이지 논리16",
        )
    if class_id == 0x28 and commander_id in (2, 3):
        color = "red" if commander_id == 2 else "blue"
        return (
            ROOT
            / "assets/class-sprites/source/latest/liana-lana-strict16-v1"
            / f"native16-{color}/28.png",
            "리아나·라나 승인 서머너 논리16",
        )
    if class_id in (0x18, 0x28, 0x25, 0x26):
        return (
            V1 / "logical16" / f"{commander_id:02d}-{class_id:02X}.png",
            "v1 캐릭터별 결과 중 최적 실루엣",
        )
    raise KeyError((commander_id, class_id))


def restore_identity(
    image: Image.Image,
    original: Image.Image,
    identity: set[tuple[int, int]],
) -> Image.Image:
    result = image.copy().convert("RGBA")
    for point in identity:
        color = original.getpixel(point)
        if color[3]:
            result.putpixel(point, color)
    return result


def paint_free(
    image: Image.Image,
    identity: set[tuple[int, int]],
    points: set[tuple[int, int]],
    color: tuple[int, int, int, int],
) -> None:
    for point in points:
        if point not in identity:
            image.putpixel(point, color)


def rect(x0: int, y0: int, x1: int, y1: int) -> set[tuple[int, int]]:
    return {
        (x, y)
        for y in range(y0, y1 + 1)
        for x in range(x0, x1 + 1)
    }


def accent(commander_id: int) -> tuple[
    tuple[int, int, int, int],
    tuple[int, int, int, int],
    tuple[int, int, int, int],
]:
    return COMMANDER_RAMPS[commander_id]


def polish_sage(
    donor: Image.Image,
    commander_id: int,
    identity: set[tuple[int, int]],
) -> Image.Image:
    """Keep the best donor while clarifying book, staff, and closed robe."""
    dark, main, light = accent(commander_id)
    result = donor.copy().convert("RGBA")

    # Open book on image-left: dark cover, white pages, gold clasp, connected
    # to a sleeve rather than floating beside the character.
    paint_free(result, identity, rect(0, 7, 3, 10), INK)
    paint_free(result, identity, {(0, 7), (1, 7), (1, 8), (2, 8), (2, 9), (3, 9)}, WHITE)
    paint_free(result, identity, {(0, 9), (1, 10), (2, 10), (3, 10)}, dark)
    paint_free(result, identity, {(2, 8), (3, 9)}, GOLD)
    paint_free(result, identity, {(3, 10), (4, 10), (4, 11)}, main)

    # White/gold Sage robe stays bright while target color is a mantle accent.
    paint_free(result, identity, rect(5, 9, 11, 14), WHITE)
    paint_free(result, identity, {(5, 9), (6, 9), (10, 9), (11, 9),
                                  (5, 10), (11, 10), (5, 13), (11, 13)}, main)
    paint_free(result, identity, {(6, 10), (10, 10), (6, 13), (10, 13),
                                  (6, 14), (10, 14)}, light)
    paint_free(result, identity, {(7, 10), (8, 10), (9, 10),
                                  (7, 13), (8, 13), (9, 13)}, GOLD)
    paint_free(result, identity, {(7, 11), (8, 11), (9, 11),
                                  (7, 12), (8, 12), (9, 12)}, SILVER)
    paint_free(result, identity, rect(4, 15, 7, 15) | rect(9, 15, 12, 15), INK)

    # Ring-topped staff on image-right, kept inside and connected at the hand.
    paint_free(result, identity, {(14, 0), (15, 0), (13, 1), (14, 1), (15, 1),
                                  (13, 2), (15, 2), (13, 3), (14, 3), (15, 3)}, INK)
    paint_free(result, identity, {(14, 1), (14, 2)}, light)
    paint_free(result, identity, {(13, 2), (15, 2), (14, 3)}, GOLD)
    paint_free(result, identity, {(14, y) for y in range(4, 16)}, WOOD)
    paint_free(result, identity, {(15, y) for y in range(5, 16)}, INK)
    paint_free(result, identity, {(12, 10), (13, 10), (14, 10)}, GOLD)
    return result


def polish_wizard(
    donor: Image.Image,
    commander_id: int,
    identity: set[tuple[int, int]],
) -> Image.Image:
    """Keep the approved Wizard and repair only matte/waist regressions."""
    dark, main, _ = accent(commander_id)
    result = donor.copy().convert("RGBA")
    # The old generated Hein source carried one chroma-key pixel; background
    # colors are never valid equipment colors.
    for y in range(16):
        for x in range(16):
            red, green, blue, alpha = result.getpixel((x, y))
            if alpha and red > 200 and blue > 200 and green < 80:
                result.putpixel((x, y), TRANSPARENT)
    # Approved variants had a two-pixel transparent notch at the belt.  Close
    # it with robe cloth so map backgrounds cannot show through the torso.
    paint_free(result, identity, {(7, 10)}, dark)
    paint_free(result, identity, {(8, 10)}, main)
    return result


def merge_jessica_wizard_near_duplicate(
    image: Image.Image,
    identity: set[tuple[int, int]],
) -> tuple[Image.Image, int]:
    """Reserve one palette slot for the later global identity restoration.

    Jessica's refined Wizard contains a single #9224B6 equipment pixel next
    to the established #9249B6 cloth ramp.  The aggregate editor build also
    restores one ROM-red identity pixel from the newer mask, which otherwise
    raises the final sprite from 15 to 16 visible colors.  Merge only this
    near-duplicate equipment shade; identity pixels are never candidates.
    """

    result = image.copy().convert("RGBA")
    changed = 0
    for y in range(16):
        for x in range(16):
            point = (x, y)
            if (
                point not in identity
                and result.getpixel(point) == JESSICA_WIZARD_NEAR_PURPLE
            ):
                result.putpixel(point, JESSICA_WIZARD_MAIN_PURPLE)
                changed += 1
    return result, changed


def merge_jessica_wizard_rare_equipment_blue(
    image: Image.Image,
    identity: set[tuple[int, int]],
) -> tuple[Image.Image, int]:
    """Free one palette slot for Jessica's newly masked gray eye pixel."""

    result = image.copy().convert("RGBA")
    changed = 0
    for y in range(16):
        for x in range(16):
            point = (x, y)
            if (
                point not in identity
                and result.getpixel(point)
                == JESSICA_WIZARD_RARE_EQUIPMENT_BLUE
            ):
                result.putpixel(point, JESSICA_WIZARD_MAIN_BLUE)
                changed += 1
    return result, changed


def recolor_keith_healer_sky(image: Image.Image) -> Image.Image:
    """Replace Keith Healer's emerald cloth with his sky-blue class ramp."""

    result = image.copy().convert("RGBA")
    for y in range(16):
        for x in range(16):
            color = result.getpixel((x, y))
            if color in KEITH_HEALER_SKY_MAP:
                result.putpixel((x, y), KEITH_HEALER_SKY_MAP[color])
    return result


def polish_aaron_high_priest(
    donor: Image.Image,
    identity: set[tuple[int, int]],
) -> Image.Image:
    """Preserve Aaron's original design and only finish its staff edge."""
    result = donor.copy().convert("RGBA")
    # The stock sprite already reaches x14 at y4.  One adjacent gold pixel
    # uses the last column without creating a detached top fragment.
    paint_free(result, identity, {(15, 4)}, GOLD)
    return result


def polish_summoner(
    donor: Image.Image,
    commander_id: int,
    identity: set[tuple[int, int]],
) -> Image.Image:
    """Keep the donor pose and make scroll, crystal staff, and robe readable."""
    dark, main, light = accent(commander_id)
    result = donor.copy().convert("RGBA")

    # Rolled summoning scroll on the left, visibly held by the sleeve.
    paint_free(result, identity, rect(0, 8, 2, 11), INK)
    paint_free(result, identity, {(0, 8), (1, 8), (2, 8), (0, 9), (2, 9),
                                  (0, 10), (2, 10), (0, 11), (1, 11), (2, 11)}, GOLD)
    paint_free(result, identity, {(1, 9), (1, 10)}, WHITE)
    paint_free(result, identity, {(2, 10), (3, 10), (4, 10)}, WOOD)

    # Dark mantle outside, colored inner robe, and a pale invocation panel.
    paint_free(result, identity, rect(3, 8, 12, 14), INK)
    paint_free(result, identity, rect(4, 9, 11, 14), dark)
    paint_free(result, identity, {(4, 9), (5, 9), (10, 9), (11, 9),
                                  (4, 10), (11, 10), (5, 13), (10, 13)}, main)
    paint_free(result, identity, {(5, 10), (10, 10), (5, 14), (10, 14)}, light)
    paint_free(result, identity, rect(7, 10, 9, 13), WHITE)
    paint_free(result, identity, {(8, 10), (8, 13)}, GOLD)
    paint_free(result, identity, rect(3, 15, 6, 15) | rect(9, 15, 12, 15), INK)

    # Crystal staff on the right, joined to the forearm at y10.
    paint_free(result, identity, {(14, 0), (15, 0), (13, 1), (14, 1), (15, 1),
                                  (13, 2), (14, 2), (15, 2), (14, 3)}, INK)
    paint_free(result, identity, {(14, 1), (15, 1), (14, 2)}, light)
    paint_free(result, identity, {(15, 2), (14, 3)}, WHITE)
    paint_free(result, identity, {(14, y) for y in range(4, 16)}, WOOD)
    paint_free(result, identity, {(15, y) for y in range(4, 16)}, INK)
    paint_free(result, identity, {(12, 9), (13, 9), (14, 9), (12, 10)}, GOLD)
    return result


def draw_agent(
    commander_id: int,
    identity: set[tuple[int, int]],
) -> Image.Image:
    """Repixel the AI Agent as cloth, crystal, scroll, and staff—not armor."""
    dark, main, light = accent(commander_id)
    result = Image.new("RGBA", (16, 16), TRANSPARENT)

    # Neutral covert mantle; character color is reserved for inner cloth.
    paint_free(result, identity, rect(3, 7, 13, 14), INK)
    paint_free(result, identity, rect(4, 8, 12, 14), VIOLET_DARK)
    paint_free(result, identity, {(4, 8), (5, 8), (11, 8), (12, 8),
                                  (4, 9), (12, 9), (5, 12), (11, 12)}, GRAY)
    paint_free(result, identity, rect(6, 9, 10, 13), dark)
    paint_free(result, identity, {(6, 9), (10, 9), (6, 10), (10, 10),
                                  (6, 13), (10, 13)}, main)
    paint_free(result, identity, {(7, 10), (8, 10), (9, 10),
                                  (7, 11), (9, 11)}, SILVER)
    paint_free(result, identity, {(8, 11), (8, 12)}, light)
    paint_free(result, identity, {(7, 13), (8, 13), (9, 13)}, GOLD)
    paint_free(result, identity, rect(3, 15, 6, 15) | rect(9, 15, 12, 15), INK)

    # Crystal/encoded scroll held on image-left and a slim staff on the right.
    paint_free(result, identity, rect(0, 8, 2, 11), INK)
    paint_free(result, identity, {(0, 9), (1, 8), (1, 9), (1, 10), (2, 9)}, light)
    paint_free(result, identity, {(1, 9)}, WHITE)
    paint_free(result, identity, {(2, 10), (3, 10), (4, 10)}, GOLD)
    paint_free(result, identity, {(14, y) for y in range(2, 16)} | {(15, y) for y in range(1, 16)}, INK)
    paint_free(result, identity, {(14, 1), (15, 0), (15, 1), (14, 2)}, light)
    paint_free(result, identity, {(15, 0), (14, 1)}, WHITE)
    paint_free(result, identity, {(14, y) for y in range(3, 16)}, WOOD)
    paint_free(result, identity, {(12, 9), (13, 9), (14, 9), (13, 10)}, GOLD)
    return result


def draw_zarvera(
    commander_id: int,
    identity: set[tuple[int, int]],
) -> Image.Image:
    """Repixel Zarvera as a closed dark-mage robe with one clear staff."""
    dark, main, light = accent(commander_id)
    result = Image.new("RGBA", (16, 16), TRANSPARENT)

    # Broad dark mantle with gold piping, but a narrow, closed central robe.
    paint_free(result, identity, rect(2, 7, 13, 14), INK)
    paint_free(result, identity, rect(3, 8, 12, 14), VIOLET_DARK)
    paint_free(result, identity, {(3, 8), (4, 8), (11, 8), (12, 8),
                                  (3, 9), (12, 9), (4, 12), (11, 12)}, VIOLET)
    paint_free(result, identity, rect(5, 9, 10, 15), dark)
    paint_free(result, identity, {(5, 9), (10, 9), (5, 10), (10, 10),
                                  (5, 13), (10, 13), (5, 14), (10, 14)}, main)
    paint_free(result, identity, {(6, 10), (9, 10), (6, 13), (9, 13)}, light)
    paint_free(result, identity, {(7, 9), (8, 9), (7, 10), (8, 10),
                                  (7, 13), (8, 13), (7, 14), (8, 14)}, GOLD)
    paint_free(result, identity, rect(4, 15, 7, 15) | rect(8, 15, 11, 15), INK)

    # Connected casting hand at left; the small spell is the only intentional
    # secondary component.  Main weapon remains on image-right.
    paint_free(result, identity, {(0, 8), (1, 8), (0, 9), (1, 9)}, light)
    paint_free(result, identity, {(1, 10), (2, 9), (2, 10), (3, 10), (4, 10)}, main)
    paint_free(result, identity, {(0, 8)}, WHITE)

    # Trident/crystal staff, fully inside the canvas and joined to the hand.
    paint_free(result, identity, {(13, 0), (15, 0), (13, 1), (14, 1), (15, 1),
                                  (13, 2), (14, 2), (15, 2), (14, 3)}, INK)
    paint_free(result, identity, {(13, 0), (15, 0), (14, 1)}, GOLD)
    paint_free(result, identity, {(14, 1), (14, 2)}, light)
    paint_free(result, identity, {(14, y) for y in range(3, 16)}, WOOD)
    paint_free(result, identity, {(15, y) for y in range(3, 16)}, INK)
    paint_free(result, identity, {(11, 9), (12, 9), (13, 9), (14, 9)}, GOLD)
    return result


def component_sizes(image: Image.Image) -> list[int]:
    points = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if image.getpixel((x, y))[3]
    }
    result: list[int] = []
    while points:
        queue = deque([points.pop()])
        size = 0
        while queue:
            x, y = queue.popleft()
            size += 1
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in points:
                    points.remove(neighbor)
                    queue.append(neighbor)
        result.append(size)
    return sorted(result, reverse=True)


def write_contact(reports: list[dict[str, object]]) -> None:
    columns = 6
    cell = 192
    header = 32
    rows = (len(reports) + columns - 1) // columns
    canvas = Image.new("RGBA", (columns * cell, rows * (cell + header)), (210, 210, 210, 255))
    draw = ImageDraw.Draw(canvas)
    for index, report in enumerate(reports):
        x = (index % columns) * cell
        y = (index // columns) * (cell + header)
        draw.text(
            (x + 4, y + 4),
            f"{report['commander_id']:02d} {report['commander_name']} {report['class_id']}",
            fill=(24, 24, 24, 255),
        )
        sprite = Image.open(OUTPUT / str(report["file"])).convert("RGBA")
        canvas.alpha_composite(sprite.resize((cell, cell), Image.Resampling.NEAREST), (x, y + header))
    canvas.save(OUTPUT / "all-refined-class-variants.png", optimize=True)


def build() -> dict[str, object]:
    rom = DEFAULT_ROM.read_bytes()
    masks = load_identity_mask_overrides()
    for key, excluded in IDENTITY_MASK_EXCLUDED_POINTS.items():
        if key in masks:
            masks[key] = set(masks[key]) - excluded

    logical_dir = OUTPUT / "logical16"
    preview_dir = OUTPUT / "previews"
    for directory in (logical_dir, preview_dir):
        directory.mkdir(parents=True, exist_ok=True)

    reports: list[dict[str, object]] = []
    resolved_masks: dict[str, list[list[int]]] = {}
    donors: dict[str, dict[str, str]] = {}

    # User explicitly approved the current Healer. Preserve its pixels exactly.
    for commander_id in CLASS_SPECS[0x08]["targets"]:
        source = V1 / "logical16" / f"{commander_id:02d}-08.png"
        image = Image.open(source).convert("RGBA")
        if commander_id == 7:
            image = recolor_keith_healer_sky(image)
        output_path = logical_dir / f"{commander_id:02d}-08.png"
        image.save(output_path, optimize=True)
        image.resize((512, 512), Image.Resampling.NEAREST).save(
            preview_dir / f"{commander_id:02d}-08.png", optimize=True
        )
        old_report = next(
            row for row in json.loads((V1 / "validation-report.json").read_text(encoding="utf-8"))["classes"]
            if row["commander_id"] == commander_id and row["class_id"] == "08"
        )
        reports.append({**old_report, "file": str(output_path.relative_to(OUTPUT)), "unchanged_from_v1": True})
        donors[f"{commander_id}:08"] = {"source": str(source.relative_to(ROOT)), "reason": "사용자 승인 힐러 그대로 유지"}

    for class_id in REFINED_CLASS_IDS:
        spec = CLASS_SPECS[class_id]
        for commander_id in spec["targets"]:
            sprite_map = commander_sprite_map(rom, commander_id)
            original = render_sprite(rom, sprite_map[class_id], 1)
            identity, identity_source = resolve_identity_points(
                rom, masks, commander_id, class_id, original
            )
            resolved_masks[f"{commander_id}:{class_id:02X}"] = [
                [x, y] for x, y in sorted(identity)
            ]
            donor_path, reason = stable_donor(commander_id, class_id)
            if donor_path is None:
                donor = original.copy()
            else:
                donor = Image.open(donor_path).convert("RGBA")

            if class_id == 0x15:
                image = polish_wizard(donor, commander_id, identity)
            elif class_id == 0x16 and commander_id == 8:
                image = polish_aaron_high_priest(donor, identity)
            elif class_id == 0x18:
                image = polish_sage(donor, commander_id, identity)
            elif class_id == 0x28:
                image = polish_summoner(donor, commander_id, identity)
            elif class_id == 0x25:
                image = draw_agent(commander_id, identity)
            elif class_id == 0x26:
                image = draw_zarvera(commander_id, identity)
            else:
                image = donor.copy()
            image = restore_identity(image, original, identity)
            image, remapped = limit_visible_palette(image, identity)
            if (commander_id, class_id) == (10, 0x15):
                image, merged = merge_jessica_wizard_near_duplicate(
                    image, identity
                )
                remapped += merged
                image, merged = merge_jessica_wizard_rare_equipment_blue(
                    image, identity
                )
                remapped += merged

            output_path = logical_dir / f"{commander_id:02d}-{class_id:02X}.png"
            image.save(output_path, optimize=True)
            image.resize((512, 512), Image.Resampling.NEAREST).save(
                preview_dir / f"{commander_id:02d}-{class_id:02X}.png",
                optimize=True,
            )
            center_holes = [
                [x, y]
                for y in range(9, 15)
                for x in range(6, 10)
                if not image.getpixel((x, y))[3]
            ]
            components = component_sizes(image)
            row = {
                "commander_id": commander_id,
                "commander_name": KOREAN_NAME_BY_ID[commander_id],
                "class_id": f"{class_id:02X}",
                "class_name": spec["name"],
                "identity_source": identity_source,
                "palette_remapped_pixels": remapped,
                "near_duplicate_palette_merge": (
                    "#9224B6 -> #9249B6; #2449FF -> #496DFF"
                    if (commander_id, class_id) == (10, 0x15)
                    else None
                ),
                "file": str(output_path.relative_to(OUTPUT)),
                "donor": str(donor_path.relative_to(ROOT)) if donor_path else "ROM original",
                "donor_reason": reason,
                "connected_components": components,
                "center_holes": center_holes,
                **validate(image, original, identity),
            }
            # Body-centered classes must never regain the v1 central alpha gap.
            if class_id in (0x15, 0x18, 0x28, 0x25, 0x26) and center_holes:
                row["accepted"] = False
            reports.append(row)
            donors[f"{commander_id}:{class_id:02X}"] = {
                "source": str(donor_path.relative_to(ROOT)) if donor_path else "ROM original",
                "reason": reason,
            }

    # Preserve the v1 healer masks and add the newly resolved six-class masks.
    v1_masks = json.loads((V1 / "identity-masks.json").read_text(encoding="utf-8"))["masks"]
    for commander_id in CLASS_SPECS[0x08]["targets"]:
        key = f"{commander_id}:08"
        if key in v1_masks:
            resolved_masks[key] = v1_masks[key]
    (OUTPUT / "identity-masks.json").write_text(
        # The editor mask loader currently accepts schema version 1.  The v2
        # folder/version describes asset provenance, not a mask schema change.
        json.dumps({"version": 1, "masks": resolved_masks}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUTPUT / "class-donor-map.json").write_text(
        json.dumps({"version": 2, "donors": donors}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_contact(reports)
    result = {
        "version": 2,
        "mode": "target-specific approved donors and role-aware native16 repairs; healer unchanged",
        "all_accepted": all(bool(row["accepted"]) for row in reports),
        "classes": reports,
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    report = build()
    print(json.dumps({
        "version": report["version"],
        "all_accepted": report["all_accepted"],
        "class_count": len(report["classes"]),
        "failed": [
            f"{row['commander_id']}:{row['class_id']}"
            for row in report["classes"]
            if not row["accepted"]
        ],
    }, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["all_accepted"] else 1)
