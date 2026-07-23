#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import NamedTuple

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_class_sprite_assets import (
    DEFAULT_ROM,
    commander_sprite_map,
    render_sprite,
)
from tools.class_change_data import COMMANDER_COUNT, read_class_change_chain
from tools.scenario_data import KOREAN_NAME_BY_ID, class_names


DEFAULT_OUTPUT = ROOT / "editor/static/test-class-sprites"
CONCEPT_SHEET = ROOT / "docs/assets/allied_class_redesign_concept.png"

RULER_CLASSES = {0x01, 0x04, 0x0B, 0x1A, 0x20, 0x21, 0x22, 0x23}
MAGE_CLASSES = {0x03, 0x09, 0x0A, 0x13, 0x14, 0x15, 0x26, 0x28}
CLERIC_CLASSES = {0x02, 0x08, 0x11, 0x12, 0x16, 0x17, 0x18}
CAVALRY_CLASSES = {0x05, 0x0C, 0x0D, 0x0E, 0x19, 0x1B, 0x1D, 0x29}
DRAGON_CLASSES = {0x06, 0x0F, 0x1E, 0x24}
SEA_CLASSES = {0x07, 0x10, 0x1F, 0x2A}

INK = (36, 36, 36, 255)
GRAY = (146, 146, 146, 255)
WHITE = (255, 255, 255, 255)
SILVER = (182, 182, 219, 255)
LIGHT_BLUE = (73, 109, 255, 255)
BLUE = (36, 109, 255, 255)
DARK_BLUE = (0, 0, 146, 255)
ROYAL_BLUE = (36, 36, 219, 255)
SKIN = (219, 182, 109, 255)
HAIR = (146, 73, 36, 255)
GREEN = (36, 219, 73, 255)
DARK_GREEN = (0, 73, 36, 255)
EMERALD = (0, 182, 73, 255)
GOLD = (255, 182, 0, 255)
PALE_GOLD = (255, 219, 109, 255)
ORANGE = (255, 109, 0, 255)
CRIMSON = (219, 0, 36, 255)
DARK_RED = (109, 0, 0, 255)
MAGENTA = (255, 0, 255, 255)
ROSE = (255, 73, 146, 255)
VIOLET = (182, 73, 255, 255)
DARK_VIOLET = (73, 36, 109, 255)
CYAN = (73, 219, 255, 255)
TEAL = (0, 146, 146, 255)
DARK_TEAL = (0, 73, 73, 255)
TRANSPARENT = (0, 0, 0, 0)

LIGHT_SOURCE_COLORS = {
    GRAY,
    WHITE,
    (73, 109, 255, 255),
    (36, 219, 36, 255),
    (255, 182, 0, 255),
    (255, 0, 255, 255),
    (109, 219, 255, 255),
}
DARK_SOURCE_COLORS = {
    (0, 0, 219, 255),
    (36, 109, 0, 255),
    (219, 0, 0, 255),
    (109, 0, 0, 255),
    (73, 73, 109, 255),
}


class Theme(NamedTuple):
    armor: tuple[int, int, int, int]
    shadow: tuple[int, int, int, int]
    trim: tuple[int, int, int, int]
    mount: tuple[int, int, int, int]
    mount_shadow: tuple[int, int, int, int]
    weapon: tuple[int, int, int, int]
    aura: tuple[int, int, int, int]
    label: str


CLASS_THEMES = {
    0x04: Theme(CRIMSON, DARK_RED, GOLD, CRIMSON, DARK_RED, WHITE, GOLD, "진홍 갑옷·금장 대검"),
    0x08: Theme(WHITE, TEAL, CYAN, WHITE, TEAL, PALE_GOLD, CYAN, "백색 성의·청록 치유광"),
    0x09: Theme(CYAN, DARK_BLUE, SILVER, CYAN, DARK_BLUE, PALE_GOLD, CYAN, "청색 로브·대형 마력봉"),
    0x0A: Theme(MAGENTA, DARK_VIOLET, GOLD, MAGENTA, DARK_VIOLET, CYAN, VIOLET, "흑자색 로브·주술 보주"),
    0x0B: Theme(VIOLET, DARK_VIOLET, GOLD, VIOLET, DARK_VIOLET, WHITE, PALE_GOLD, "왕실 자색 갑옷·금장 망토"),
    0x0C: Theme(EMERALD, DARK_GREEN, GOLD, ORANGE, DARK_RED, PALE_GOLD, GREEN, "적갈색 군마·녹금 마갑"),
    0x0D: Theme(VIOLET, DARK_VIOLET, CYAN, ROYAL_BLUE, DARK_BLUE, CYAN, MAGENTA, "청마·자색 마갑·마력창"),
    0x0E: Theme(WHITE, SILVER, GOLD, WHITE, VIOLET, PALE_GOLD, CYAN, "백색 유니콘·금빛 뿔"),
    0x0F: Theme(CRIMSON, DARK_RED, GOLD, EMERALD, DARK_GREEN, PALE_GOLD, ORANGE, "비취 비룡·진홍 기사"),
    0x11: Theme(WHITE, DARK_BLUE, GOLD, WHITE, DARK_BLUE, PALE_GOLD, CYAN, "백금 사제복·성광 지팡이"),
    0x12: Theme(VIOLET, DARK_VIOLET, WHITE, VIOLET, DARK_VIOLET, GOLD, PALE_GOLD, "보라 주교복·대형 성표"),
    0x13: Theme(BLUE, DARK_BLUE, CYAN, BLUE, DARK_BLUE, WHITE, CYAN, "청색 마도복·서리 보주"),
    0x14: Theme(VIOLET, DARK_VIOLET, GOLD, VIOLET, DARK_VIOLET, CYAN, MAGENTA, "자금색 로브·쌍중 보주"),
    0x15: Theme(INK, DARK_VIOLET, MAGENTA, INK, DARK_VIOLET, CYAN, VIOLET, "암흑 로브·거대 마법봉"),
    0x16: Theme(PALE_GOLD, ORANGE, WHITE, PALE_GOLD, ORANGE, WHITE, GOLD, "금백 성의·태양 후광"),
    0x17: Theme(WHITE, SILVER, GOLD, WHITE, SILVER, PALE_GOLD, CYAN, "은백 성갑·광휘 검"),
    0x18: Theme(VIOLET, DARK_BLUE, WHITE, VIOLET, DARK_BLUE, GOLD, CYAN, "현자 자색 로브·빛의 고리"),
    0x19: Theme(WHITE, SILVER, GOLD, WHITE, SILVER, PALE_GOLD, GOLD, "백마·금빛 마갑·성창"),
    0x1A: Theme(CRIMSON, INK, SILVER, CRIMSON, INK, WHITE, ROSE, "흑진홍 갑옷·초대형 은검"),
    0x1B: Theme(INK, DARK_RED, CRIMSON, DARK_RED, INK, SILVER, CRIMSON, "흑마·진홍 마갑·장창"),
    0x1D: Theme(SILVER, DARK_BLUE, CYAN, SILVER, ROYAL_BLUE, WHITE, CYAN, "은청 군마·수정 장창"),
    0x1E: Theme(GOLD, DARK_RED, CRIMSON, CRIMSON, DARK_RED, WHITE, ORANGE, "적룡·황금 갑옷·화염창"),
    0x1F: Theme(CYAN, DARK_TEAL, SILVER, TEAL, DARK_TEAL, PALE_GOLD, CYAN, "청록 해룡·은빛 삼지창"),
    0x21: Theme(EMERALD, DARK_GREEN, SILVER, EMERALD, DARK_GREEN, WHITE, GREEN, "녹은 경갑·장궁·숲의 광채"),
    0x22: Theme(WHITE, ROYAL_BLUE, GOLD, WHITE, ROYAL_BLUE, PALE_GOLD, CYAN, "백금 영웅갑·빛의 대검"),
    0x23: Theme(INK, DARK_VIOLET, GOLD, INK, DARK_VIOLET, WHITE, MAGENTA, "흑금 갑옷·쌍날 대검"),
    0x24: Theme(VIOLET, DARK_VIOLET, GOLD, MAGENTA, DARK_VIOLET, PALE_GOLD, CYAN, "자색 고룡·금빛 용창"),
    0x26: Theme(MAGENTA, INK, GOLD, MAGENTA, INK, CYAN, ROSE, "흑자색 마도복·소환 문장"),
    0x28: Theme(INK, DARK_VIOLET, MAGENTA, INK, DARK_VIOLET, CYAN, MAGENTA, "암흑 소환복·쌍보주"),
    0x29: Theme(PALE_GOLD, CRIMSON, WHITE, WHITE, CRIMSON, GOLD, PALE_GOLD, "백마·금홍 왕실 마갑"),
    0x2A: Theme(PALE_GOLD, DARK_TEAL, CYAN, CYAN, DARK_TEAL, GOLD, WHITE, "백금 해룡·왕실 삼지창"),
}


def class_tiers(source: bytes, commander_id: int) -> dict[int, int]:
    tiers: dict[int, int] = {}
    for index, transition in enumerate(
        read_class_change_chain(source, commander_id)
    ):
        if index == 0:
            source_tier = 1
        elif index <= 3:
            source_tier = 2
        elif index <= 8:
            source_tier = 3
        else:
            source_tier = 4
        tiers.setdefault(transition.current_class, source_tier)
        for candidate in transition.candidates:
            tiers.setdefault(candidate, source_tier + 1)
    return tiers


def class_family(class_id: int) -> str:
    if class_id in MAGE_CLASSES:
        return "mage"
    if class_id in CLERIC_CLASSES:
        return "cleric"
    if class_id in CAVALRY_CLASSES:
        return "cavalry"
    if class_id in DRAGON_CLASSES:
        return "dragon"
    if class_id in SEA_CLASSES:
        return "sea"
    return "ruler"


def class_theme(class_id: int, family: str) -> Theme:
    if class_id in CLASS_THEMES:
        return CLASS_THEMES[class_id]
    defaults = {
        "mage": Theme(VIOLET, DARK_VIOLET, GOLD, VIOLET, DARK_VIOLET, CYAN, MAGENTA, "자색 마도복·마력봉"),
        "cleric": Theme(WHITE, ROYAL_BLUE, GOLD, WHITE, ROYAL_BLUE, PALE_GOLD, CYAN, "백금 성의·성광"),
        "cavalry": Theme(CRIMSON, DARK_RED, GOLD, SILVER, DARK_BLUE, WHITE, PALE_GOLD, "전면 마갑·대형 장창"),
        "dragon": Theme(GOLD, DARK_RED, CRIMSON, EMERALD, DARK_GREEN, WHITE, ORANGE, "전면 용갑·거대 날개"),
        "sea": Theme(CYAN, DARK_TEAL, SILVER, TEAL, DARK_TEAL, PALE_GOLD, CYAN, "해룡 갑주·삼지창"),
        "ruler": Theme(CRIMSON, DARK_RED, GOLD, CRIMSON, DARK_RED, WHITE, PALE_GOLD, "왕실 갑옷·대형 무기"),
    }
    return defaults[family]


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError("class sprite is completely transparent")
    left, top, right, bottom = bbox
    return left, top, right - 1, bottom - 1


def point(
    image: Image.Image,
    x: int,
    y: int,
    color: tuple[int, int, int, int],
    *,
    only_if_transparent: bool = False,
) -> None:
    if not (0 <= x < image.width and 0 <= y < image.height):
        return
    if only_if_transparent and image.getpixel((x, y))[3]:
        return
    image.putpixel((x, y), color)


def mix_color(
    source: tuple[int, int, int, int],
    target: tuple[int, int, int, int],
    target_weight: float,
) -> tuple[int, int, int, int]:
    return (
        round(source[0] * (1 - target_weight) + target[0] * target_weight),
        round(source[1] * (1 - target_weight) + target[1] * target_weight),
        round(source[2] * (1 - target_weight) + target[2] * target_weight),
        255,
    )


def protected_face_points(source: Image.Image) -> set[tuple[int, int]]:
    _, top, _, _ = alpha_bbox(source)
    face_limit = min(8, top + 6)
    seeds = {
        (x, y)
        for y in range(face_limit + 1)
        for x in range(source.width)
        if source.getpixel((x, y)) in {SKIN, HAIR}
    }
    protected = set(seeds)
    for x, y in seeds:
        for nx in range(max(0, x - 1), min(source.width, x + 2)):
            for ny in range(max(0, y - 1), min(source.height, y + 2)):
                if source.getpixel((nx, ny)) == INK:
                    protected.add((nx, ny))
    return protected


def restore_source_structure(
    image: Image.Image,
    source: Image.Image,
    protected_face: set[tuple[int, int]],
) -> None:
    for y in range(source.height):
        for x in range(source.width):
            source_color = source.getpixel((x, y))
            if source_color == INK or (x, y) in protected_face:
                image.putpixel((x, y), source_color)


def add_back_silhouette(
    source: Image.Image,
    family: str,
    theme: Theme,
    tier: int,
) -> Image.Image:
    left, top, right, bottom = alpha_bbox(source)
    back = Image.new("RGBA", source.size, TRANSPARENT)
    draw = ImageDraw.Draw(back)
    if family in {"ruler", "mage", "cleric"}:
        cape_top = max(top + 5, 5)
        cape_left = max(0, left - (2 if tier < 4 else 3))
        cape_right = min(15, right + (1 if tier < 4 else 2))
        draw.polygon(
            [
                (left, cape_top),
                (cape_left, min(14, cape_top + 5)),
                (cape_left + 1, min(15, bottom + 1)),
                (cape_right, min(15, bottom + 1)),
                (right, cape_top),
            ],
            fill=theme.shadow,
        )
        draw.polygon(
            [
                (left, cape_top + 1),
                (min(15, left + 1), min(15, bottom)),
                (cape_right - 1, min(15, bottom)),
                (right, cape_top + 1),
            ],
            fill=theme.armor,
        )
    elif family == "dragon":
        wing_y = max(4, top + 3)
        draw.polygon(
            [(left, wing_y), (0, max(2, wing_y - 3)), (2, wing_y + 5), (left + 2, wing_y + 3)],
            fill=theme.mount_shadow,
        )
        draw.polygon(
            [(right, wing_y), (15, max(2, wing_y - 3)), (13, wing_y + 5), (right - 2, wing_y + 3)],
            fill=theme.mount_shadow,
        )
        draw.line([(1, wing_y - 2), (left + 1, wing_y + 2)], fill=theme.mount, width=2)
        draw.line([(14, wing_y - 2), (right - 1, wing_y + 2)], fill=theme.mount, width=2)
        if tier >= 4:
            draw.line([(0, wing_y - 3), (3, wing_y + 1)], fill=theme.trim)
            draw.line([(15, wing_y - 3), (12, wing_y + 1)], fill=theme.trim)
    elif family == "cavalry":
        draw.polygon(
            [(max(0, left - 1), 8), (0, 12), (2, 15), (min(8, right), 14), (right, 9)],
            fill=theme.mount_shadow,
        )
        draw.line([(1, 12), (6, 14), (10, 12)], fill=theme.mount, width=2)
    elif family == "sea":
        draw.polygon(
            [(left, 9), (1, 12), (0, 15), (6, 14), (11, 15), (15, 12), (right, 8)],
            fill=theme.mount_shadow,
        )
        draw.line([(1, 13), (6, 12), (11, 14), (15, 11)], fill=theme.mount, width=2)
    back.alpha_composite(source)
    return back


def recolor_sprite(
    source: Image.Image,
    family: str,
    theme: Theme,
    class_id: int,
    protected_face: set[tuple[int, int]],
) -> Image.Image:
    image = source.copy()
    mounted_cut = {
        "cavalry": 7,
        "dragon": 6,
        "sea": 6,
    }.get(family, 99)
    for y in range(image.height):
        for x in range(image.width):
            color = source.getpixel((x, y))
            if (
                color[3] == 0
                or color == INK
                or (x, y) in protected_face
            ):
                continue
            is_mount = y >= mounted_cut
            base = theme.mount if is_mount else theme.armor
            shadow = theme.mount_shadow if is_mount else theme.shadow
            if is_mount:
                if color == WHITE:
                    replacement = mix_color(base, WHITE, 0.48)
                elif color == GRAY:
                    replacement = base
                elif color in {GOLD, MAGENTA}:
                    replacement = theme.trim
                elif color in LIGHT_SOURCE_COLORS or color in {SKIN, HAIR}:
                    replacement = mix_color(base, WHITE, 0.18)
                else:
                    replacement = mix_color(shadow, INK, 0.16)
            else:
                if color == WHITE:
                    replacement = mix_color(base, WHITE, 0.52)
                elif color == GRAY:
                    replacement = base
                elif color in {GOLD, MAGENTA}:
                    replacement = theme.trim
                elif color in LIGHT_SOURCE_COLORS:
                    replacement = mix_color(base, WHITE, 0.14)
                else:
                    replacement = mix_color(shadow, INK, 0.18)
            if (
                color not in {WHITE, GRAY, SKIN, HAIR}
                and (x * 3 + y + class_id) % 11 == 0
            ):
                replacement = theme.trim
            image.putpixel((x, y), replacement)
    return image


def draw_crown(image: Image.Image, theme: Theme, tier: int) -> None:
    bbox = alpha_bbox(image)
    center = (bbox[0] + bbox[2]) // 2
    y = max(0, bbox[1] - 1)
    draw = ImageDraw.Draw(image)
    draw.line([(center - 2, y + 1), (center + 2, y + 1)], fill=theme.trim)
    for dx in (-2, 0, 2):
        point(image, center + dx, y, theme.aura)
    if tier >= 4:
        point(image, center, max(0, y - 1), WHITE)


def draw_halo(image: Image.Image, theme: Theme, tier: int) -> None:
    left, top, right, _ = alpha_bbox(image)
    center = (left + right) // 2
    y = max(0, top - 1)
    draw = ImageDraw.Draw(image)
    draw.line([(max(0, center - 3), y), (min(15, center + 3), y)], fill=theme.aura)
    point(image, max(0, center - 3), min(15, y + 1), theme.trim)
    point(image, min(15, center + 3), min(15, y + 1), theme.trim)
    if tier >= 4:
        point(image, center, max(0, y - 1), WHITE)


def draw_staff(image: Image.Image, theme: Theme, tier: int, cleric: bool) -> None:
    draw = ImageDraw.Draw(image)
    x = 13 if image.getpixel((13, 8))[3] == 0 else 14
    draw.line([(x, 4), (x, 14)], fill=INK, width=2)
    draw.line([(x, 4), (x, 14)], fill=theme.weapon)
    if cleric:
        draw.line([(x - 2, 5), (x + 1, 5)], fill=theme.trim)
        draw.line([(x, 3), (x, 7)], fill=theme.trim)
        point(image, x, 4, WHITE)
    else:
        draw.rectangle((x - 1, 2, min(15, x + 1), 4), fill=theme.aura)
        point(image, x, 2, WHITE)
        if tier >= 4:
            point(image, x - 2, 3, theme.trim)
            point(image, min(15, x + 2), 3, theme.trim)


def draw_large_weapon(
    image: Image.Image,
    family: str,
    theme: Theme,
    tier: int,
) -> None:
    draw = ImageDraw.Draw(image)
    if family == "cavalry":
        draw.line([(7, 14), (15, 3)], fill=INK, width=3)
        draw.line([(7, 14), (15, 3)], fill=theme.weapon)
        draw.line([(13, 4), (15, 6)], fill=theme.trim)
        point(image, 15, 2, WHITE)
    elif family == "dragon":
        draw.line([(8, 14), (15, 4)], fill=INK, width=3)
        draw.line([(8, 14), (15, 4)], fill=theme.weapon)
        draw.polygon([(15, 2), (13, 5), (15, 5)], fill=theme.aura)
    elif family == "sea":
        draw.line([(14, 4), (14, 15)], fill=INK, width=3)
        draw.line([(14, 4), (14, 15)], fill=theme.weapon)
        draw.line([(12, 4), (15, 4)], fill=theme.aura)
        point(image, 12, 3, theme.aura)
        point(image, 14, 2, WHITE)
        point(image, 15, 3, theme.aura)
    else:
        draw.line([(8, 14), (15, 3)], fill=INK, width=3)
        draw.line([(8, 14), (15, 3)], fill=theme.weapon)
        draw.line([(8, 11), (11, 13)], fill=theme.trim)
        point(image, 15, 2, theme.aura)
        if tier >= 4:
            point(image, 14, 1, WHITE)


def add_aura_pixels(image: Image.Image, theme: Theme, class_id: int) -> None:
    for x, y in ((1, 3), (14, 2), (0, 8), (15, 10), (2, 14), (12, 15)):
        if (x + y + class_id) % 2 and image.getpixel((x, y))[3] == 0:
            point(image, x, y, theme.aura)


def redesign_sprite(
    source: Image.Image,
    class_id: int,
    tier: int,
) -> tuple[Image.Image, str, int]:
    family = class_family(class_id)
    theme = class_theme(class_id, family)
    protected_face = protected_face_points(source)
    recolored = recolor_sprite(
        source,
        family,
        theme,
        class_id,
        protected_face,
    )
    image = add_back_silhouette(recolored, family, theme, tier)

    if family == "mage":
        draw_staff(image, theme, tier, cleric=False)
        if tier >= 4:
            draw_halo(image, theme, tier)
    elif family == "cleric":
        draw_staff(image, theme, tier, cleric=True)
        draw_halo(image, theme, tier)
    elif family in {"cavalry", "dragon", "sea"}:
        draw_large_weapon(image, family, theme, tier)
        draw_crown(image, theme, tier)
    else:
        draw_large_weapon(image, family, theme, tier)
        draw_crown(image, theme, tier)
    if tier >= 4:
        add_aura_pixels(image, theme, class_id)
    restore_source_structure(image, source, protected_face)
    return image, theme.label, len(protected_face)


def changed_pixels(source: Image.Image, redesigned: Image.Image) -> int:
    return sum(
        source.getpixel((x, y)) != redesigned.getpixel((x, y))
        for y in range(source.height)
        for x in range(source.width)
    )


def build_assets(rom_path: Path, output_dir: Path) -> dict[str, object]:
    source = rom_path.read_bytes()
    classes = class_names(source)
    commanders: dict[str, object] = {}
    redesigned_count = 0

    for commander_id in range(1, COMMANDER_COUNT + 1):
        tiers = class_tiers(source, commander_id)
        sprite_map = commander_sprite_map(source, commander_id)
        by_sprite: dict[int, list[int]] = defaultdict(list)
        for class_id in tiers:
            by_sprite[sprite_map[class_id]].append(class_id)
        for class_ids in by_sprite.values():
            class_ids.sort(key=lambda class_id: (tiers[class_id], class_id))

        commander_dir = output_dir / str(commander_id)
        commander_dir.mkdir(parents=True, exist_ok=True)
        rows: dict[str, object] = {}
        for class_id, tier in sorted(tiers.items()):
            sprite_id = sprite_map[class_id]
            group = by_sprite[sprite_id]
            group_rank = group.index(class_id)
            redesigned = len(group) > 1 and group_rank > 0
            source_image = render_sprite(source, sprite_id, 1)
            image = source_image
            feature = "원본 유지"
            protected_face_pixel_count = 0
            if redesigned:
                image, feature, protected_face_pixel_count = redesign_sprite(
                    image,
                    class_id,
                    tier,
                )
                redesigned_count += 1
            changed_pixel_count = changed_pixels(source_image, image)
            opaque_pixel_count = sum(
                pixel[3] != 0 for pixel in source_image.get_flattened_data()
            )
            if redesigned and changed_pixel_count < 36:
                raise ValueError(
                    f"commander {commander_id} class 0x{class_id:02X} "
                    f"changes only {changed_pixel_count} pixels"
                )
            target = commander_dir / f"{class_id:02X}.png"
            image.save(target, optimize=True)
            rows[str(class_id)] = {
                "class_id": class_id,
                "class_name": classes[class_id]["ko"],
                "tier": tier,
                "source_sprite_id": sprite_id,
                "duplicate_group": group,
                "group_rank": group_rank,
                "redesigned": redesigned,
                "feature": feature,
                "protected_face_pixel_count": protected_face_pixel_count,
                "changed_pixel_count": changed_pixel_count,
                "changed_ratio": round(
                    changed_pixel_count / max(opaque_pixel_count, 1),
                    3,
                ),
                "file": str(target.relative_to(output_dir)),
            }
        commanders[str(commander_id)] = {
            "name": KOREAN_NAME_BY_ID[commander_id],
            "classes": rows,
        }

    manifest = {
        "generated_from": str(rom_path.relative_to(ROOT)),
        "concept_sheet": str(CONCEPT_SHEET.relative_to(ROOT)),
        "commander_count": len(commanders),
        "redesigned_count": redesigned_count,
        "policy": (
            "preserve the lowest class in each duplicate sprite group; "
            "dramatically redesign only later classes for editor comparison"
        ),
        "rom_effect": "none; preview PNG assets only",
        "commanders": commanders,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build experimental allied class-change sprite previews"
    )
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_assets(args.rom, args.output)
    print(
        f"{args.output}: {manifest['commander_count']} commanders, "
        f"{manifest['redesigned_count']} redesigned duplicate classes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
