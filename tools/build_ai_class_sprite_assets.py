#!/usr/bin/env python3
# ruff: noqa: E402
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import colorsys
import fcntl
import json
from pathlib import Path
import shutil
import sys
import tempfile

from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_class_sprite_assets import (
    DEFAULT_ROM,
    commander_sprite_map,
    render_sprite,
)
from tools.build_test_class_sprite_assets import (
    TRANSPARENT,
    class_tiers,
)
from tools.class_change_data import COMMANDER_COUNT, hidden_class_routes
from tools.pixellab_elwin_inpaint import head_lock_box
from tools.scenario_data import KOREAN_NAME_BY_ID, class_names


DEFAULT_SHEET = ROOT / "assets/class-sprites/reference/allied_class_redesign_concept.png"
DEFAULT_BOARD_DIR = (
    ROOT
    / "assets/class-sprites/source/character-ai-v3"
)
ELWIN_NATIVE_SOURCE_DIR = (
    ROOT / "assets/class-sprites/source/elwin-native16-v16"
)
ELWIN_LORD_SOURCE_DIR = (
    ROOT / "assets/class-sprites/source/latest/elwin-lord-v2"
)
ELWIN_HERO_SOURCE_DIR = (
    ROOT / "assets/class-sprites/source/latest/elwin-hero-ai-v7-anatomy"
)
ELWIN_HERO_SELECTED_SAMPLE_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/"
    "sample-class-variants-v4-free-five/01-elwin-22-hero"
)
ELWIN_MOUNTED_SOURCE_DIR = (
    ROOT / "assets/class-sprites/source/latest/elwin-mounted-v2"
)
SHERRY_NATIVE_SOURCE_DIR = (
    ROOT / "assets/class-sprites/source/latest/sherry-v2"
)
HEIN_LATEST_SOURCE_DIR = (
    ROOT / "assets/class-sprites/source/latest/hein/raw"
)
HEIN_SORCERER_V2_DIR = (
    ROOT / "assets/class-sprites/source/latest/hein-sorcerer-v2"
)
HEIN_SORCERER_V2_CLEAN_SOURCE = (
    HEIN_SORCERER_V2_DIR / "clean/hein-09-sorcerer-ai.png"
)
HEIN_SORCERER_V2_LOGICAL_SOURCE = (
    HEIN_SORCERER_V2_DIR / "logical16/hein-09-sorcerer-ai.png"
)
LIANA_LANA_PAIRED_SOURCE_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/liana-lana-strict16-v1"
)
SHARED_ARCHMAGE_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/shared-archmage-lester-v1"
    / "logical16"
)
SHARED_ELWIN_MAGIC_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/shared-elwin-magic-v1"
    / "logical16"
)
SHARED_HEIN_WIZARD_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/shared-wizard-hein-v1"
    / "logical16"
)
LIANA_TO_LANA_WIZARD_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/lana-wizard-liana-template-v1"
    / "logical16"
)
SHARED_KEITH_WIZARD_NEW_CLASS_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/shared-keith-wizard-new-classes-v1"
    / "logical16"
)
SHARED_LIANA_SUMMONER_AGENT_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/shared-liana-summoner-agent-v1"
    / "logical16"
)
SHARED_LIANA_LANA_HEALER_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/shared-liana-lana-healer-v1"
    / "logical16"
)
LIANA_SAGE_SHERRY_WIZARD_PALETTE_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/"
    "liana-sage-sherry-wizard-palette-v1/logical16"
)
SHARED_ELWIN_SWORDMASTER_HIGH_MASTER_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/"
    "shared-high-master-elwin-swordmaster-v1"
    / "logical16"
)
SHARED_AARON_SAINT_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/shared-saint-aaron-v1"
    / "logical16"
)
SHARED_AARON_HIGH_PRIEST_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/shared-high-priest-aaron-v1"
    / "logical16"
)
SHERRY_RANGER_V4_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/sherry-ranger-v4"
    / "logical16"
)
HEIN_WARLOCK_SORCERER_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/hein-warlock-sorcerer-v1"
    / "logical16"
)
HEIN_MAGIC_KNIGHT_PALADIN_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/hein-magic-knight-paladin-v1"
    / "logical16"
)
SHARED_HEIN_CLASS_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/shared-hein-classes-v1"
    / "logical16"
)
SHARED_HIGH_LORD_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/shared-high-lord-hein-v1"
    / "logical16"
)
SHARED_SWORDMASTER_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/shared-swordmaster-hein-v1"
    / "logical16"
)
SHARED_ELWIN_LORD_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/"
    "shared-lord-elwin-high-lord-v1"
    / "logical16"
)
SCOTT_KEITH_ELWIN_LORD_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/"
    "shared-scott-keith-lord-elwin-lord-v1/logical16"
)
SHERRY_SCOTT_KEITH_AARON_LORD_SOURCE_DIR = (
    ROOT
    / "assets/class-sprites/source/latest/"
    "shared-sherry-scott-keith-lord-aaron-lord-v1/logical16"
)
SHARED_NEW_CLASS_SOURCE_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/shared-new-classes-v2-refined"
)
SHARED_NEW_CLASS_SOURCE_DIR = SHARED_NEW_CLASS_SOURCE_ROOT / "logical16"
SHARED_NEW_CLASS_MASKS = SHARED_NEW_CLASS_SOURCE_ROOT / "identity-masks.json"
JESSICA_FRESH_MAGIC_SOURCE_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/"
    / "jessica-zarvera-summoner-ai-v1-fresh"
)
JESSICA_FRESH_MAGIC_SOURCE_DIR = (
    JESSICA_FRESH_MAGIC_SOURCE_ROOT / "logical16"
)
KEITH_LESTER_TIER_MOUNT_SOURCE_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/keith-lester-tier1-mounted-v1"
)
KEITH_LESTER_TIER_MOUNT_SOURCE_DIR = (
    KEITH_LESTER_TIER_MOUNT_SOURCE_ROOT / "logical16"
)
KEITH_LESTER_TIER_IDENTITY_MASKS = (
    KEITH_LESTER_TIER_MOUNT_SOURCE_ROOT / "identity-masks.json"
)
KEITH_LESTER_TIER_MOUNT_MASKS = (
    KEITH_LESTER_TIER_MOUNT_SOURCE_ROOT / "mount-masks.json"
)
ELWIN_DIRECT_STAGE_SOURCE = (
    ROOT / "assets/class-sprites/reference/direct_16x16_01_elwin.png"
)
ELWIN_MAGIC_SOURCE = (
    ROOT
    / "assets/class-sprites/source/character-ai-v3/elwin/"
    "elwin-mage-archmage-source-v3.png"
)
IDENTITY_MASK_OVERRIDES = ROOT / "editor/ai_identity_masks.json"
MOUNT_MASK_OVERRIDES = ROOT / "editor/ai_mount_masks.json"
AI_DESIGN_OVERRIDES = ROOT / "editor/ai_class_design_overrides.json"
DEFAULT_OUTPUT = ROOT / "editor/static/ai-class-sprites"
AI_ASSET_BUILD_LOCK_PATH = (
    Path(tempfile.gettempdir())
    / "lang2_md-ai-class-assets-build.lock"
)
GRID_COLUMNS = 5
GRID_ROWS = 10
ASSET_VERSION = "identity-mask-and-silhouette-closure-v107"

ROM_INK = (36, 36, 36, 255)
ROM_WHITE = (255, 255, 255, 255)
ROM_SKIN = (219, 182, 109, 255)
ROM_BLUE_EYE = (0, 0, 219, 255)
MEGA_DRIVE_CHANNEL_LEVELS = (0, 36, 73, 109, 146, 182, 219, 255)

# Chroma-key background accidentally painted into a historical manual mask.
# Never restore these coordinates as character identity.
IDENTITY_MASK_EXCLUDED_POINTS = {
    (5, 0x15): {(12, 6)},
}

# The user finalized these transparent-to-ink boundary positions on Elwin's
# five shared class designs.  Other commanders reuse the same equipment
# grammar, but keep their own visible identity and mount pixels.  Filling only
# transparent, unlocked positions prevents the map background from leaking
# through neck, arm, torso, face, and equipment seams.
SHARED_DARK_BOUNDARY_REFERENCE_POINTS = {
    0x04: {
        (3, 5),
        (3, 6), (10, 6), (12, 6),
        (3, 7), (4, 7), (10, 7), (11, 7), (12, 7),
        (5, 8), (10, 8), (12, 8),
        (6, 9), (7, 9), (8, 9), (9, 9),
    },
    0x0B: {
        (5, 0), (10, 0), (11, 0),
        (4, 1), (12, 1), (13, 1),
        (4, 2),
        (1, 3), (2, 3),
        (2, 4), (13, 4), (15, 4),
        (2, 5), (3, 5),
        (3, 6), (10, 6), (12, 6), (13, 6),
        (4, 7), (10, 7), (11, 7), (13, 7),
        (5, 8), (10, 8),
        (6, 9), (7, 9), (8, 9), (9, 9),
        (0, 13),
        (0, 14), (1, 14),
        (0, 15), (1, 15),
    },
    0x13: {
        (2, 3),
        (2, 4),
        (2, 5), (3, 5),
        (2, 6), (3, 6), (10, 6), (12, 6),
        (2, 7), (3, 7), (4, 7), (10, 7), (11, 7), (12, 7),
        (1, 8), (5, 8), (10, 8),
        (1, 9), (5, 9), (6, 9), (7, 9), (8, 9), (9, 9), (10, 9),
        (0, 10),
    },
    0x14: {
        (1, 3), (2, 3),
        (2, 4),
        (2, 5), (3, 5),
        (10, 6), (12, 6), (13, 6),
        (3, 7), (11, 7), (13, 7),
        (2, 9),
        (2, 10),
        (10, 12),
        (10, 13), (11, 13),
        (11, 14),
    },
    0x1A: {
        (13, 2),
        (2, 3), (13, 3),
        (2, 4), (13, 4),
        (2, 5), (3, 5), (13, 5),
        (2, 6), (3, 6), (10, 6), (12, 6),
        (1, 7), (2, 7), (3, 7), (4, 7),
        (11, 7), (12, 7), (13, 7), (14, 7),
        (0, 8), (1, 8), (14, 8), (15, 8),
        (0, 9),
        (13, 10),
        (1, 11), (2, 11), (5, 11),
        (13, 11), (14, 11), (15, 11),
        (0, 12), (1, 12), (14, 12), (15, 12),
        (0, 13), (15, 13),
    },
}

RESAMPLING = getattr(Image, "Resampling", Image)
QUANTIZE = getattr(Image, "Quantize", Image)
DITHER = getattr(Image, "Dither", Image)


def identity_mask_key(commander_id: int, class_id: int) -> str:
    return f"{commander_id}:{class_id:02X}"


def box_points(
    box: tuple[int, int, int, int],
) -> set[tuple[int, int]]:
    left, top, right, bottom = box
    return {
        (x, y)
        for y in range(top, bottom)
        for x in range(left, right)
    }


def translate_selected_pixels(
    image: Image.Image,
    points: set[tuple[int, int]],
    dx: int,
    dy: int,
) -> Image.Image:
    """Move selected visible pixels without moving the equipment layer."""
    translated = {
        point: (point[0] + dx, point[1] + dy)
        for point in points
    }
    if any(
        not (0 <= target[0] < 16 and 0 <= target[1] < 16)
        for target in translated.values()
    ):
        raise ValueError("translated identity pixel exceeds 16x16 canvas")
    source = image.copy()
    result = image.copy()
    target_points = set(translated.values())
    for point in points - target_points:
        result.putpixel(point, TRANSPARENT)
    for point, target in translated.items():
        result.putpixel(target, source.getpixel(point))
    return result


def translate_points(
    points: set[tuple[int, int]],
    dx: int,
    dy: int,
) -> set[tuple[int, int]]:
    translated = {(x + dx, y + dy) for x, y in points}
    if any(
        not (0 <= x < 16 and 0 <= y < 16)
        for x, y in translated
    ):
        raise ValueError("translated mask point exceeds 16x16 canvas")
    return translated


def enclosed_empty_points(
    occupied_points: set[tuple[int, int]],
    *,
    width: int = 16,
    height: int = 16,
) -> set[tuple[int, int]]:
    """Return empty pixels that cannot reach the canvas edge.

    Four-way connectivity matches the logical Mega Drive pixel grid. A
    diagonal one-pixel crack therefore counts as a closed pinhole, which is
    exactly the kind of background leak that is visible in-game.
    """

    outside: set[tuple[int, int]] = set()
    pending: deque[tuple[int, int]] = deque()

    def add_outside(point: tuple[int, int]) -> None:
        if point not in occupied_points and point not in outside:
            outside.add(point)
            pending.append(point)

    for x in range(width):
        add_outside((x, 0))
        add_outside((x, height - 1))
    for y in range(height):
        add_outside((0, y))
        add_outside((width - 1, y))

    while pending:
        x, y = pending.popleft()
        for neighbor in (
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
        ):
            neighbor_x, neighbor_y = neighbor
            if (
                0 <= neighbor_x < width
                and 0 <= neighbor_y < height
            ):
                add_outside(neighbor)

    return {
        (x, y)
        for y in range(height)
        for x in range(width)
        if (x, y) not in occupied_points and (x, y) not in outside
    }


def close_internal_transparency(
    image: Image.Image,
    color: tuple[int, int, int, int] = ROM_INK,
) -> set[tuple[int, int]]:
    """Paint enclosed transparent sprite pinholes with stock ROM ink."""

    occupied_points = {
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if image.getpixel((x, y))[3]
    }
    closed_points = enclosed_empty_points(
        occupied_points,
        width=image.width,
        height=image.height,
    )
    for point in closed_points:
        image.putpixel(point, color)
    return closed_points


def load_identity_mask_overrides(
    path: Path = IDENTITY_MASK_OVERRIDES,
) -> dict[tuple[int, int], set[tuple[int, int]]]:
    return load_pixel_mask_overrides(path, label="identity")


def load_mount_mask_overrides(
    path: Path = MOUNT_MASK_OVERRIDES,
) -> dict[tuple[int, int], set[tuple[int, int]]]:
    return load_pixel_mask_overrides(path, label="mount")


def load_pixel_mask_overrides(
    path: Path,
    *,
    label: str,
) -> dict[tuple[int, int], set[tuple[int, int]]]:
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("version") != 1:
        raise ValueError(f"unsupported AI {label}-mask file version")
    raw_masks = document.get("masks", {})
    if not isinstance(raw_masks, dict):
        raise ValueError(f"AI {label}-mask masks must be an object")
    result: dict[tuple[int, int], set[tuple[int, int]]] = {}
    for raw_key, raw_points in raw_masks.items():
        try:
            commander_text, class_text = raw_key.split(":", 1)
            commander_id = int(commander_text)
            class_id = int(class_text, 16)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(
                f"invalid AI {label}-mask key: {raw_key!r}"
            ) from exc
        if not 1 <= commander_id <= COMMANDER_COUNT:
            raise ValueError(
                f"AI {label}-mask commander out of range: {commander_id}"
            )
        if not 0 <= class_id <= 0xFF:
            raise ValueError(
                f"AI {label}-mask class out of range: {class_id}"
            )
        if not isinstance(raw_points, list):
            raise ValueError(
                f"AI {label}-mask points must be a list: {raw_key}"
            )
        points: set[tuple[int, int]] = set()
        for raw_point in raw_points:
            if (
                not isinstance(raw_point, list)
                or len(raw_point) != 2
                or any(
                    isinstance(value, bool) or not isinstance(value, int)
                    for value in raw_point
                )
            ):
                raise ValueError(
                    f"invalid AI {label}-mask point: {raw_key}"
                )
            x, y = raw_point
            if not (0 <= x < 16 and 0 <= y < 16):
                raise ValueError(
                    f"AI {label}-mask point out of range: {raw_key}"
                )
            points.add((x, y))
        result[(commander_id, class_id)] = points
    return result


def load_ai_design_overrides(
    path: Path = AI_DESIGN_OVERRIDES,
) -> dict[tuple[int, int], dict[str, object]]:
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("version") != 1:
        raise ValueError("unsupported AI class-design override version")
    raw_designs = document.get("designs", {})
    if not isinstance(raw_designs, dict):
        raise ValueError("AI class-design overrides must be an object")
    result: dict[tuple[int, int], dict[str, object]] = {}
    for raw_key, raw_entry in raw_designs.items():
        try:
            commander_text, class_text = raw_key.split(":", 1)
            commander_id = int(commander_text)
            class_id = int(class_text, 16)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(
                f"invalid AI class-design key: {raw_key!r}"
            ) from exc
        if not 1 <= commander_id <= COMMANDER_COUNT:
            raise ValueError(
                f"AI class-design commander out of range: {commander_id}"
            )
        if not 0 <= class_id <= 0xFF:
            raise ValueError(
                f"AI class-design class out of range: {class_id}"
            )
        if not isinstance(raw_entry, dict):
            raise ValueError(
                f"AI class-design entry must be an object: {raw_key}"
            )
        raw_pixels = raw_entry.get("pixels")
        if not isinstance(raw_pixels, list) or len(raw_pixels) != 256:
            raise ValueError(
                f"AI class-design must contain 256 pixels: {raw_key}"
            )
        pixels: list[tuple[int, int, int, int]] = []
        for raw_pixel in raw_pixels:
            if (
                not isinstance(raw_pixel, list)
                or len(raw_pixel) != 4
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or not 0 <= value <= 255
                    for value in raw_pixel
                )
            ):
                raise ValueError(
                    f"invalid AI class-design pixel: {raw_key}"
                )
            red, green, blue, alpha = raw_pixel
            if alpha not in {0, 255}:
                raise ValueError(
                    f"AI class-design alpha must be 0 or 255: {raw_key}"
                )
            if alpha and any(
                channel not in MEGA_DRIVE_CHANNEL_LEVELS
                for channel in (red, green, blue)
            ):
                raise ValueError(
                    f"AI class-design color is not Mega Drive safe: "
                    f"{raw_key}"
                )
            pixels.append((red, green, blue, alpha))
        visible_colors = {
            pixel for pixel in pixels if pixel[3]
        }
        if len(visible_colors) > 15:
            raise ValueError(
                f"AI class-design exceeds 15 visible colors: {raw_key}"
            )
        result[(commander_id, class_id)] = {
            "pixels": pixels,
            "revision": int(raw_entry.get("revision", 0)),
        }
    return result


ELWIN_NATIVE_SOURCE_FILES = {
    0x04: "04-lord.png",
    0x0B: "0B-high-lord.png",
    0x0C: "0C-highlander.png",
    0x12: "12-bishop.png",
    0x13: "13-mage.png",
    0x14: "14-archmage.png",
    0x1A: "1A-swordmaster.png",
    0x1B: "1B-knight-master.png",
    0x1D: "1D-silver-knight.png",
    0x22: "22-hero.png",
}

# All ten Elwin upper duplicate classes now use v14 sources. Archmage received
# a small royal-blue/violet and gold costume pass while preserving its accepted
# v13 pose, staff, scale, and user-masked head. The other nine v13 classes stay
# represented unchanged.
ELWIN_DIRECT_STAGE_CLASSES: dict[int, int] = {}

# Midpoints between the five isolated foreground runs in the fixed 2172x724
# source sheet. Keeping the full height retains weapons and feet; the normal
# source-foreground extractor removes the black backdrop afterward.
ELWIN_DIRECT_STAGE_BOUNDS = {
    1: (0, 0, 416, 724),
    2: (416, 0, 816, 724),
    3: (816, 0, 1283, 724),
    4: (1283, 0, 1705, 724),
    5: (1705, 0, 2172, 724),
}

ELWIN_CHARACTER_AI_CLASSES: dict[int, int] = {}

ELWIN_CHARACTER_AI_BOUNDS = {
    1: (0, 0, 968, 813),
    2: (968, 0, 1935, 813),
}

SHARED_CLASS_TEMPLATE_SOURCES = {
    **{
        (commander_id, 0x04): (
            SHARED_ELWIN_LORD_SOURCE_DIR
            / f"{commander_id:02d}-04.png",
            "엘윈 사용자 편집 하이로드 기반 로드",
        )
        for commander_id in (1, 4, 6, 7, 8)
    },
    **{
        (commander_id, 0x0B): (
            SHARED_HIGH_LORD_SOURCE_DIR
            / f"{commander_id:02d}-0B.png",
            "헤인 사용자 편집 하이로드",
        )
        for commander_id in (1, 2, 3, 4, 5, 6, 7, 8, 10)
    },
    **{
        (commander_id, 0x1A): (
            SHARED_SWORDMASTER_SOURCE_DIR
            / f"{commander_id:02d}-1A.png",
            "헤인 사용자 편집 소드마스터",
        )
        for commander_id in (5, 7, 8, 10)
    },
    **{
        (commander_id, class_id): (
            SHARED_ELWIN_MAGIC_SOURCE_DIR
            / f"{commander_id:02d}-{class_id:02X}.png",
            {
                0x13: "엘윈 사용자 리터칭 메이지",
                0x14: "엘윈 사용자 리터칭 아크메이지",
            }[class_id],
        )
        for class_id in (0x13, 0x14)
        for commander_id in (1, 2, 3, 4, 5, 8, 9, 10)
    },
    **{
        (commander_id, class_id): (
            SHARED_HEIN_CLASS_SOURCE_DIR
            / f"{commander_id:02d}-{class_id:02X}.png",
            {
                0x11: "헤인 사용자 승인 프리스트",
                0x13: "헤인 사용자 편집 메이지",
                0x16: "헤인 사용자 편집 하이프리스트",
            }[class_id],
        )
        for class_id, commander_ids in {
            0x11: (2, 3, 5, 7, 10),
            0x16: (2, 3, 5, 7, 10),
        }.items()
        for commander_id in commander_ids
    },
    **{
        (commander_id, 0x15): (
            SHARED_HEIN_WIZARD_SOURCE_DIR
            / f"{commander_id:02d}-15.png",
            "헤인 위저드 복장 기반 위저드",
        )
        for commander_id in (2, 3, 4, 7, 9, 10)
    },
    (4, 0x23): (
        SHARED_ELWIN_SWORDMASTER_HIGH_MASTER_SOURCE_DIR / "04-23.png",
        "엘윈 소드마스터 장비 기반 쉐리 하이마스터",
    ),
    (8, 0x23): (
        SHARED_ELWIN_SWORDMASTER_HIGH_MASTER_SOURCE_DIR / "08-23.png",
        "엘윈 소드마스터 장비 기반 아론 하이마스터",
    ),
    **{
        (commander_id, 0x17): (
            SHARED_AARON_SAINT_SOURCE_DIR
            / f"{commander_id:02d}-17.png",
            "아론 사용자 편집 세인트 기반 공통 세인트",
        )
        for commander_id in (1, 2, 3, 4, 5, 6, 7, 8, 10)
    },
    (4, 0x21): (
        SHERRY_RANGER_V4_SOURCE_DIR / "04-21.png",
        "쉐리 하이마스터 동일 디자인 기반 레인저 색상 변형",
    ),
    (5, 0x09): (
        HEIN_WARLOCK_SORCERER_SOURCE_DIR / "05-09.png",
        "헤인 비-AI 워록 원본 기반 소서러",
    ),
    (5, 0x19): (
        HEIN_MAGIC_KNIGHT_PALADIN_SOURCE_DIR / "05-19.png",
        "헤인 비-AI 매직나이트 원본 기반 팔라딘",
    ),
}

SHARED_NEW_CLASS_TARGETS = {
    0x08: (2, 3, 7, 10),
    0x16: (2, 3, 5, 7, 8, 10),
    0x18: (2, 3, 5, 6, 10),
    0x15: (2, 3, 4, 5, 7, 9, 10),
    0x28: (2, 3, 5, 10),
    0x25: (2, 3),
    0x26: (2, 3, 5, 9, 10),
}
SHARED_NEW_CLASS_NAMES = {
    0x08: "힐러",
    0x16: "하이프리스트",
    0x18: "세이지",
    0x15: "위저드",
    0x28: "서머너",
    0x25: "에이전트",
    0x26: "자베라",
}
SHARED_NEW_CLASS_SOURCE_KEYS = {
    (commander_id, class_id)
    for class_id, commander_ids in SHARED_NEW_CLASS_TARGETS.items()
    for commander_id in commander_ids
}
SHARED_CLASS_TEMPLATE_SOURCES.update({
    key: (
        SHARED_NEW_CLASS_SOURCE_DIR / f"{key[0]:02d}-{key[1]:02X}.png",
        (
            f"캐릭터별 승인 기준형 기반 {SHARED_NEW_CLASS_NAMES[key[1]]} 논리16"
            if key[1] != 0x08
            else "사용자 승인 힐러 논리16 유지"
        ),
    )
    for key in SHARED_NEW_CLASS_SOURCE_KEYS
})

# Scott and Keith keep their current corrected body/identity pixels, but use
# the current Elwin Lord's complete right-side shield instead of the older
# gray block left by the broad High-Lord-derived template.
SCOTT_KEITH_ELWIN_LORD_SOURCE_KEYS = {
    (4, 0x04),
    (6, 0x04),
    (7, 0x04),
}
SHARED_CLASS_TEMPLATE_SOURCES.update({
    key: (
        SCOTT_KEITH_ELWIN_LORD_SOURCE_DIR / f"{key[0]:02d}-04.png",
        "현재 엘윈 로드 방패 기반 쉐리·스코트·키스 로드",
    )
    for key in SCOTT_KEITH_ELWIN_LORD_SOURCE_KEYS
})

# The user's newly saved Aaron Lord is now the approved equipment master for
# Sherry, Scott, and Keith. Register it after the former Elwin-shield-only
# source so the complete Aaron sword, armor, outline, and shield design wins.
SHERRY_SCOTT_KEITH_AARON_LORD_SOURCE_KEYS = {
    (4, 0x04),
    (6, 0x04),
    (7, 0x04),
}
SHARED_CLASS_TEMPLATE_SOURCES.update({
    key: (
        SHERRY_SCOTT_KEITH_AARON_LORD_SOURCE_DIR
        / f"{key[0]:02d}-04.png",
        "최신 아론 사용자 편집 로드 기반 쉐리·스코트·키스 로드",
    )
    for key in SHERRY_SCOTT_KEITH_AARON_LORD_SOURCE_KEYS
})

# The user's latest Aaron High Priest edit replaces the older Hein/shared-new
# High Priest body.  Register it after the broad shared-new block so this
# narrower, explicitly approved template wins for every real High Priest.
SHARED_AARON_HIGH_PRIEST_SOURCE_KEYS = {
    (commander_id, 0x16)
    for commander_id in (2, 3, 5, 7, 8, 10)
}
SHARED_CLASS_TEMPLATE_SOURCES.update({
    key: (
        SHARED_AARON_HIGH_PRIEST_SOURCE_DIR
        / f"{key[0]:02d}-16.png",
        "아론 사용자 편집 하이프리스트 기반 공통 하이프리스트",
    )
    for key in SHARED_AARON_HIGH_PRIEST_SOURCE_KEYS
})

LIANA_TO_LANA_WIZARD_SOURCE_KEYS = {(3, 0x15)}
SHARED_CLASS_TEMPLATE_SOURCES.update({
    (3, 0x15): (
        LIANA_TO_LANA_WIZARD_SOURCE_DIR / "03-15.png",
        "리아나 위저드 장비 기반 라나 청색 위저드",
    )
})

# Jessica's Zarvera and Summoner are fresh per-character generative designs,
# not variants of the shared-new-class masters.  Register them after the
# shared block so these two dedicated native-16 sources win for the same keys.
JESSICA_FRESH_MAGIC_SOURCE_KEYS = {(10, 0x26), (10, 0x28)}
SHARED_CLASS_TEMPLATE_SOURCES.update({
    key: (
        JESSICA_FRESH_MAGIC_SOURCE_DIR / f"10-{key[1]:02X}.png",
        {
            0x26: "제시카 전용 신규 AI 자베라",
            0x28: "제시카 전용 신규 AI 서머너",
        }[key[1]],
    )
    for key in JESSICA_FRESH_MAGIC_SOURCE_KEYS
})

# Latest user-approved Keith Wizard equipment is the common cross-class body
# for Agent, Zarvera, and Summoner. Register after the older refined/Jessica
# sources so this explicit reassignment wins for all eleven real targets.
SHARED_KEITH_WIZARD_NEW_CLASS_SOURCE_KEYS = {
    (2, 0x25),
    (3, 0x25),
    (2, 0x26),
    (3, 0x26),
    (5, 0x26),
    (9, 0x26),
    (10, 0x26),
    (2, 0x28),
    (3, 0x28),
    (5, 0x28),
    (10, 0x28),
}
SHARED_CLASS_TEMPLATE_SOURCES.update({
    key: (
        SHARED_KEITH_WIZARD_NEW_CLASS_SOURCE_DIR
        / f"{key[0]:02d}-{key[1]:02X}.png",
        "키스 사용자 편집 위저드 기반 공통 신규 클래스",
    )
    for key in SHARED_KEITH_WIZARD_NEW_CLASS_SOURCE_KEYS
})

# Summoner and Agent use separate class designs: the user's newest Liana
# Summoner and the preserved pre-remap Liana Agent. Each class is shared only
# between the twins with different colors; old oversized head masks must not
# be recomposited on either approved full-sprite design.
SHARED_LIANA_SUMMONER_AGENT_SOURCE_KEYS = {
    (2, 0x28),
    (2, 0x25),
    (2, 0x26),
    (3, 0x28),
    (3, 0x25),
    (3, 0x26),
}
SHARED_CLASS_TEMPLATE_SOURCES.update({
    key: (
        SHARED_LIANA_SUMMONER_AGENT_SOURCE_DIR
        / f"{key[0]:02d}-{key[1]:02X}.png",
        "최신 리아나 서머너 정렬 기반 서머너·에이전트·자베라",
    )
    for key in SHARED_LIANA_SUMMONER_AGENT_SOURCE_KEYS
})

# The user's latest Liana Healer is the equipment master for both twins.
# Lana keeps the same coordinates with a blue class ramp and her current
# identity mask. Register after the broad shared-new source so this explicit
# user-approved pair wins for 2:08 and 3:08.
SHARED_LIANA_LANA_HEALER_SOURCE_KEYS = {
    (2, 0x08),
    (3, 0x08),
}
SHARED_CLASS_TEMPLATE_SOURCES.update({
    key: (
        SHARED_LIANA_LANA_HEALER_SOURCE_DIR
        / f"{key[0]:02d}-{key[1]:02X}.png",
        "최신 리아나 사용자 편집 힐러 기반 리아나·라나 힐러",
    )
    for key in SHARED_LIANA_LANA_HEALER_SOURCE_KEYS
})

FULL_SPRITE_SHARED_TEMPLATE_SOURCE_KEYS = {
    *SHARED_LIANA_SUMMONER_AGENT_SOURCE_KEYS,
}

LIANA_SAGE_SHERRY_WIZARD_PALETTE_SOURCE_KEYS = {
    (2, 0x18),
    (4, 0x15),
}
FULL_SPRITE_SHARED_TEMPLATE_SOURCE_KEYS |= (
    LIANA_SAGE_SHERRY_WIZARD_PALETTE_SOURCE_KEYS
)
SHARED_CLASS_TEMPLATE_SOURCES.update({
    key: (
        LIANA_SAGE_SHERRY_WIZARD_PALETTE_SOURCE_DIR
        / f"{key[0]:02d}-{key[1]:02X}.png",
        "리아나 세이지·쉐리 위저드 사용자 편집형 밝은 재료색 보정",
    )
    for key in LIANA_SAGE_SHERRY_WIZARD_PALETTE_SOURCE_KEYS
})

TIER_MOUNT_CLASS_SOURCE_CLASSES = {
    (7, 0x01): 0x06,
    (7, 0x06): 0x06,
    (9, 0x01): 0x07,
    (9, 0x07): 0x07,
}
TIER_MOUNT_CLASS_DISPLAY_NAMES = {
    (7, 0x01): "호크나이트",
    (7, 0x06): "호크로드",
    (9, 0x01): "크로코나이트",
    (9, 0x07): "크로코로드",
}
TIER_MOUNT_CLASS_SOURCE_KEYS = set(TIER_MOUNT_CLASS_SOURCE_CLASSES)
SHARED_CLASS_TEMPLATE_SOURCES.update({
    key: (
        KEITH_LESTER_TIER_MOUNT_SOURCE_DIR
        / f"{key[0]:02d}-{key[1]:02X}.png",
        f"원작 {TIER_MOUNT_CLASS_DISPLAY_NAMES[key]} 동일 좌표",
    )
    for key in TIER_MOUNT_CLASS_SOURCE_KEYS
})

# These sources are already target-specific, identity-locked, validated
# native 16x16 sprites. Re-quantizing them during the aggregate build can
# collapse intentional colors (notably Jessica's purple) into gray. Preserve
# their palette byte-for-byte and only refresh visible identity pixels.
EXACT_SHARED_TEMPLATE_SOURCE_KEYS = {
    (commander_id, class_id)
    for class_id in (0x13, 0x14)
    for commander_id in (1, 2, 3, 4, 5, 8, 9, 10)
} | {
    (5, 0x09),
    (5, 0x19),
    (4, 0x15),
    (4, 0x23),
    (4, 0x21),
    (8, 0x1A),
    *{
        (commander_id, 0x17)
        for commander_id in (1, 2, 3, 4, 5, 6, 7, 8, 10)
    },
    (7, 0x15),
    (2, 0x15),
    (3, 0x15),
    (9, 0x15),
    (10, 0x15),
    (8, 0x23),
} | SHARED_NEW_CLASS_SOURCE_KEYS | SCOTT_KEITH_ELWIN_LORD_SOURCE_KEYS \
    | SHERRY_SCOTT_KEITH_AARON_LORD_SOURCE_KEYS \
    | SHARED_LIANA_SUMMONER_AGENT_SOURCE_KEYS \
    | SHARED_LIANA_LANA_HEALER_SOURCE_KEYS \
    | LIANA_SAGE_SHERRY_WIZARD_PALETTE_SOURCE_KEYS

# Keep editor history on disk, but let an explicitly remapped shared template
# win when the user has reassigned that class design. Elwin's former High Lord
# override is now the Lord master, while live 1:0B uses Hein's High Lord design.
SHARED_TEMPLATE_SUPERSEDES_DESIGN_OVERRIDES = {
    (1, 0x0B),
    (1, 0x13),
    (4, 0x13),
    (4, 0x21),
    (6, 0x04),
    (3, 0x0B),
    (5, 0x0B),
    (5, 0x14),
    (5, 0x13),
    (9, 0x14),
    (9, 0x15),
    (10, 0x0B),
    (10, 0x13),
    (5, 0x19),
    (8, 0x1A),
} | SHARED_NEW_CLASS_SOURCE_KEYS
SHARED_TEMPLATE_SUPERSEDED_DESIGN_REVISION_MAX = {
    # A newer editor save is an explicit decision made after the template
    # remap and must win on later rebuilds.
    (1, 0x0B): 1785226614151445208,
    (1, 0x13): 1785226570917742985,
    (4, 0x13): 1785499435423588529,
    (4, 0x21): 1785661995718102871,
    (6, 0x04): 1785120121020121547,
    (3, 0x0B): 1785227477665587123,
    (5, 0x0B): 1785045436288669236,
    (5, 0x14): 1785044647857633284,
    (5, 0x13): 1785044335964980169,
    (9, 0x14): 1785048405916033984,
    (9, 0x15): 1785048630530125564,
    (10, 0x0B): 1785226835415926630,
    (10, 0x13): 1785223392722184076,
    (5, 0x19): 1785506345095324852,
    (8, 0x1A): 1785120727826534811,
    (2, 0x08): 1785072980088176454,
    (5, 0x16): 1785085953622227899,
    (10, 0x16): 1785146801160065229,
}

# These older Jessica bodies still use a head one logical pixel to the right.
# Swordmaster and Zarvera now follow their freshly hand-painted destination
# masks directly, so they are intentionally absent from this table.
IDENTITY_PIXEL_TRANSLATIONS = {
    (10, 0x0B): (1, 0),
    (10, 0x13): (1, 0),
    (10, 0x14): (1, 0),
    # Jessica's Summoner still uses the older right-shifted face placement.
    # Zarvera now follows its freshly hand-painted destination mask directly.
    (10, 0x28): (1, 0),
}

# Jessica's freshly repainted High Lord mask marks the destination head
# coordinates (x+1). Read each locked color from the ROM pixel immediately to
# its left; sampling the ROM at the destination itself shears the eye/hair by
# one pixel even though the mask box looks correctly shifted.
IDENTITY_OVERRIDE_SOURCE_OFFSETS = {
    (10, 0x0B): (-1, 0),
}

# Preserve the user's newly painted Elwin Swordmaster cape pixels, but use the
# same vivid crimson as Elwin's original red commander capes.
ELWIN_SWORDMASTER_CAPE_POINTS = {
    (3, 13),
    (4, 13),
    (11, 13),
    (2, 14),
    (3, 14),
    (7, 14),
    (8, 14),
    (12, 14),
    (1, 15),
    (2, 15),
    (3, 15),
    (7, 15),
    (8, 15),
    (12, 15),
    (13, 15),
}
JESSICA_HIGH_LORD_CAPE_DARK_POINTS = {
    (5, 11),
    (11, 12),
    (4, 13),
    (12, 14),
    (3, 15),
}
JESSICA_HIGH_LORD_CAPE_POINTS = {
    (5, 10),
    (11, 10),
    (11, 11),
    (5, 11),
    (11, 12),
    (12, 12),
    (4, 13),
    (12, 13),
    (13, 13),
    (3, 14),
    (4, 14),
    (12, 14),
    (13, 14),
    (2, 15),
    (3, 15),
    (6, 15),
    (7, 15),
    (8, 15),
    (9, 15),
    (13, 15),
}
FINAL_PIXEL_OVERRIDES = {
    (1, 0x1A): {
        point: (219, 0, 0, 255)
        for point in ELWIN_SWORDMASTER_CAPE_POINTS
    },
    (1, 0x22): {
        (0, 1): (36, 36, 36, 255),
        (1, 2): (36, 36, 36, 255),
        (1, 0): (219, 182, 255, 255),
        (2, 1): (219, 182, 255, 255),
        (3, 2): (219, 182, 255, 255),
        (4, 2): (219, 182, 255, 255),
        (5, 3): (219, 182, 255, 255),
        (4, 3): (146, 36, 219, 255),
        (6, 9): (36, 36, 36, 255),
    },
}

# The editor persists accepted 16x16 designs as final live pixels, after the
# generic identity/closure stages.  These two Jessica designs intentionally
# keep details that those generic stages would otherwise replace on a later
# rebuild.  Reapply only the accepted deltas at the very end so a clean asset
# rebuild is pixel-identical to the live sprites that are encoded into ROM.
USER_APPROVED_FINAL_PIXEL_OVERRIDES = {
    (10, 0x26): {
        (10, 5): TRANSPARENT,
        (11, 5): TRANSPARENT,
        (12, 5): TRANSPARENT,
        (10, 6): TRANSPARENT,
        (11, 6): TRANSPARENT,
        (12, 6): TRANSPARENT,
        (10, 7): TRANSPARENT,
    },
    (10, 0x28): {
        (2, 0): TRANSPARENT,
        (2, 1): (255, 255, 255, 255),
        (12, 3): (146, 73, 36, 255),
        (10, 4): ROM_INK,
        (11, 4): ROM_INK,
        (4, 6): ROM_INK,
        (5, 7): ROM_INK,
        (6, 8): (73, 0, 73, 255),
    },
}

# All AI-redrawn upper cavalry classes now return to their exact stock ROM
# rider/horse silhouette. The shared manual mount masks limit recoloring to
# the mount, while these two-color ramps keep each character and tier distinct.
# Pure white sword/highlight pixels, dark outlines, skin, and overlapping face
# pixels are never included in the color map.
MOUNT_SHADE_VARIANTS = {
    # Highlander is the cooler/weaker blue tier; Knight Master advances to
    # Elwin's stronger crimson mount language.
    (1, 0x0C): ((0, 36, 109, 255), (36, 109, 219, 255)),
    (1, 0x1B): ((109, 0, 0, 255), (219, 0, 0, 255)),
    (1, 0x1D): ((73, 73, 109, 255), (146, 146, 219, 255)),
    (1, 0x29): ((109, 73, 0, 255), (255, 182, 0, 255)),
    (2, 0x19): ((109, 0, 0, 255), (219, 36, 36, 255)),
    (2, 0x1D): ((146, 0, 109, 255), (255, 73, 146, 255)),
    (3, 0x19): ((0, 36, 109, 255), (36, 109, 219, 255)),
    (3, 0x1D): ((0, 109, 146, 255), (73, 219, 255, 255)),
    (4, 0x19): ((36, 36, 109, 255), (73, 109, 182, 255)),
    (4, 0x1D): ((73, 73, 109, 255), (146, 146, 219, 255)),
    (5, 0x19): ((36, 109, 0, 255), (109, 219, 146, 255)),
    (6, 0x0C): ((36, 109, 0, 255), (146, 146, 146, 255)),
    (6, 0x19): ((36, 109, 0, 255), (182, 182, 182, 255)),
    (6, 0x1B): ((109, 0, 0, 255), (219, 0, 0, 255)),
    (6, 0x1D): ((0, 0, 219, 255), (0, 109, 255, 255)),
    (6, 0x29): ((109, 73, 36, 255), (255, 219, 109, 255)),
    (7, 0x19): ((0, 36, 109, 255), (255, 146, 0, 255)),
    (7, 0x1D): ((36, 73, 109, 255), (182, 146, 146, 255)),
    (8, 0x0C): ((73, 73, 109, 255), (182, 182, 182, 255)),
    (8, 0x19): ((109, 109, 109, 255), (182, 182, 182, 255)),
    (8, 0x1B): ((36, 36, 109, 255), (146, 146, 146, 255)),
    # Lester: stock brown Knight -> cooler blue Highlander -> forceful red
    # Knight Master. Only the shared horse mask changes.
    (9, 0x0C): ((36, 73, 146, 255), (109, 182, 255, 255)),
    (9, 0x19): ((109, 73, 36, 255), (146, 146, 146, 255)),
    (9, 0x1B): ((109, 0, 0, 255), (255, 109, 36, 255)),
    (9, 0x1D): ((73, 73, 109, 255), (182, 182, 182, 255)),
    (10, 0x19): ((0, 0, 219, 255), (73, 109, 255, 255)),
}
MOUNT_COLOR_VARIANTS = {
    key: {
        (73, 73, 109, 255): shades[0],
        (146, 146, 146, 255): shades[1],
        (146, 73, 36, 255): shades[0],
        (219, 182, 109, 255): shades[1],
    }
    for key, shades in MOUNT_SHADE_VARIANTS.items()
}

# Lester's three stock Serpent sprites share the same 16x16 geometry. Keep the
# original blue Serpent Knight as the readable base tier, then recolor only
# the user's 9:1F mount-mask pixels for increasingly forceful upper tiers.
MOUNT_COLOR_VARIANTS.update({
    # Keith/Lester keep the exact original tier-2 mounted geometry.  Their
    # old tier-2 slots are displayed as stronger Lord color variants.
    (7, 0x06): {
        (146, 73, 36, 255): (219, 36, 36, 255),
        (219, 182, 109, 255): (255, 146, 0, 255),
    },
    (9, 0x07): {
        (36, 109, 0, 255): (109, 0, 0, 255),
        (36, 219, 36, 255): (219, 36, 36, 255),
    },
    (9, 0x1F): {
        (0, 0, 219, 255): (73, 109, 255, 255),
        (73, 109, 255, 255): (109, 36, 219, 255),
        (109, 219, 255, 255): (182, 109, 255, 255),
        (219, 0, 0, 255): (255, 73, 146, 255),
    },
    (9, 0x2A): {
        (0, 0, 219, 255): (73, 109, 255, 255),
        (73, 109, 255, 255): (219, 0, 0, 255),
        (109, 219, 255, 255): (255, 73, 73, 255),
        (219, 0, 0, 255): (255, 146, 109, 255),
    },
})

ELWIN_EQUIPMENT_FEATURES = {
    0x04: (
        "담청·왕청 지휘관 흉갑·금장 견갑·짧은 진홍 망토·"
        "한손검·청금색 소형 방패·보병"
    ),
    0x0B: "중장 은색 판금·금장·긴 진홍 지휘관 망토",
    0x0C: "은색 고지 기병 갑옷·진홍 띠·청색 마갑",
    0x12: "백회색 비숍 제의·붉은 스톨·성직 지팡이",
    0x13: "남색 전투 로브·진홍 안감·녹색 보석 지팡이",
    0x14: "백남색 아크메이지 로브·금장·진홍 안감",
    0x1A: "경량 은색 검객 갑옷·진홍 허리띠·양손검",
    0x1B: "중장 은적색 기병 갑옷·금장·진홍 마갑",
    0x1D: "담청은색 기병 갑옷·진홍 포인트·은색 창",
    0x22: "백은색 영웅 판금·절제된 금장·적청 포인트",
}

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

SHERRY_EQUIPMENT_FEATURES = {
    0x04: "은색 지휘관 갑옷·금색 포인트·짧은 검·진홍 망토",
    0x0B: "중장 은색 판금·풍성한 금색 견갑·검·청색 방패",
    0x13: "왕청색 메이지 로브·보라 맨틀·보석 지팡이",
    0x14: "백청보라 아크메이지 로브·금장·녹색 보석 지팡이",
    0x15: "남색 위저드 로브·금장·적색 보석 지팡이",
    0x17: "백금색 세인트 제의·청색 포인트·성직 지팡이",
    0x19: "백은색 팔라딘 판금·금색 견갑·검·청색 방패",
    0x1D: "담청은색 기병 갑옷·남색 마갑·진홍 포인트·창",
    0x1E: "녹청색 드래곤·진홍 날개·은금색 기수 갑옷",
    0x21: "녹갈색 경량 갑옷·활·붉은 스카프",
    0x23: "백청색 하이마스터 로브·금색 견갑·보석 지팡이",
}

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

HEIN_EQUIPMENT_FEATURES = {
    0x09: "남청색 소서러 로브·금장·보석 지팡이",
    0x0A: "녹갈색 샤먼 제의·백색 망토·녹색 보석",
    0x0B: "청은색 하이로드 갑옷·방패·지휘관 장식",
    0x13: "남청색 메이지 로브·담청 맨틀·녹색 보석 지팡이",
    0x14: "백청색 아크메이지 로브·금장·청색 보석 지팡이",
    0x15: "백청색 위저드 로브·적색 포인트·지팡이",
    0x16: "백금색 하이프리스트 제의·성직 장식",
    0x18: "청금색 세이지 로브·보석 지팡이",
    0x19: "백은색 팔라딘 갑옷·검·청금색 방패",
    0x1A: "은청색 소드마스터 경갑·연두 망토·쌍검",
    0x28: "자주남색 서머너 로브·소환 장식 지팡이",
}

HEIN_LATEST_SOURCE_FILES = {
    **HEIN_NATIVE_SOURCE_FILES,
    0x11: "11-priest.png",
}

AI_SOURCE_ORIGINAL_FILES = {
    (1, 0x22): (
        ELWIN_HERO_SELECTED_SAMPLE_ROOT / "ai/04.png"
    ),
    (5, 0x11): (
        SHARED_HEIN_CLASS_SOURCE_DIR.parent
        / "master/hein-11-priest-user-approved.png"
    ),
    (5, 0x16): (
        SHARED_HEIN_CLASS_SOURCE_DIR.parent
        / "master/hein-16-high-priest-user-approved.png"
    ),
    (10, 0x26): (
        JESSICA_FRESH_MAGIC_SOURCE_ROOT
        / "selected-sources/10-26-zarvera-ai.png"
    ),
    (10, 0x28): (
        JESSICA_FRESH_MAGIC_SOURCE_ROOT
        / "selected-sources/10-28-summoner-ai.png"
    ),
}

AI_NATIVE_LOGICAL_SOURCE_KEYS: set[tuple[int, int]] = set()

JESSICA_PURPLE_EQUIPMENT_KEYS = {
    (10, class_id)
    for class_id in (0x04, 0x0B, 0x0D, 0x11, 0x12, 0x19, 0x1A)
}
JESSICA_PURPLE_ROM_BASE_KEYS = {
    (10, class_id)
    for class_id in (0x04, 0x0D, 0x12)
}
JESSICA_PURPLE_COLOR_MAP = {
    (109, 0, 0, 255): (73, 0, 109, 255),
    (146, 0, 0, 255): (109, 36, 146, 255),
    (182, 0, 0, 255): (146, 36, 182, 255),
    (219, 0, 0, 255): (182, 73, 219, 255),
    (219, 36, 36, 255): (182, 73, 219, 255),
    (255, 109, 109, 255): (219, 109, 255, 255),
}
JESSICA_HIGH_LORD_BLUE_CAPE_TO_PURPLE = {
    (36, 73, 219, 255): (73, 0, 109, 255),
    (73, 146, 255, 255): (182, 73, 219, 255),
    (109, 219, 255, 255): (219, 109, 255, 255),
}
# Restoring Jessica's exact face/hair colors after applying the shared High
# Lord design can leave two equipment-only shades beyond the Mega Drive's 15
# visible-color limit.  Fold only those unlocked equipment shades into colors
# already present in her final sprite; the identity mask remains byte-exact.
JESSICA_HIGH_LORD_PALETTE_FOLD = {
    (73, 146, 255, 255): (109, 219, 255, 255),
    (73, 73, 109, 255): ROM_INK,
}

# These classes deliberately keep their stock ROM silhouette. Sherry's Dragon
# Lord retains its editor palette override; Scott's cavalry and dragon, plus
# Keith's dragons, use the current AI concept only as a color reference.
ROM_BASE_DESIGN_KEYS = {
    (4, 0x1E),
    (4, 0x24),
    (6, 0x1E),
    (7, 0x1E),
    (7, 0x24),
    (10, 0x09),
} | set(MOUNT_COLOR_VARIANTS) | {
    (7, 0x01),
    (9, 0x01),
} | JESSICA_PURPLE_ROM_BASE_KEYS

ROM_RECOLOR_VARIANTS = {
    # Jessica Sorcerer: stock ROM geometry with the same purple/lavender
    # family used by her shared Mage and Archmage.
    (10, 0x09): {
        (109, 0, 0, 255): (73, 36, 109, 255),
        (219, 0, 0, 255): (146, 73, 182, 255),
    },
    # Scott Dragon Lord: keep ROM dragon/rider coordinates and use Sherry's
    # clearly separated golden-dragon ramp instead of another blue tier.
    (6, 0x1E): {
        (73, 109, 255, 255): (182, 109, 36, 255),
        (109, 219, 255, 255): (219, 146, 36, 255),
        (109, 0, 0, 255): (146, 0, 0, 255),
    },
    # Keith's blue Dragon Knight progresses into royal purple and then a
    # stronger crimson/gold Dragon Master. The geometry remains stock ROM.
    (7, 0x1E): {
        (73, 109, 255, 255): (73, 0, 109, 255),
        (109, 219, 255, 255): (146, 36, 219, 255),
        (109, 0, 0, 255): (182, 0, 0, 255),
    },
    (7, 0x24): {
        (73, 109, 255, 255): (109, 0, 36, 255),
        (109, 219, 255, 255): (219, 36, 109, 255),
        (109, 0, 0, 255): (219, 146, 0, 255),
    },
}
ROM_RECOLOR_VARIANTS.update({
    key: JESSICA_PURPLE_COLOR_MAP
    for key in JESSICA_PURPLE_EQUIPMENT_KEYS
})

LIANA_LANA_PAIRED_SOURCE_FILES = {
    0x08: "08.png",
    0x0B: "0B.png",
    0x11: "11.png",
    0x13: "13.png",
    0x14: "14.png",
    0x15: "15.png",
    0x16: "16.png",
    0x18: "18.png",
    0x19: "19.png",
    0x1D: "1D.png",
    0x28: "28.png",
}

LIANA_LANA_PAIRED_EQUIPMENT_FEATURES = {
    0x08: "넓은 백청색 힐러 로브·금장·청색 수정 지팡이",
    0x0B: "백은색 하이로드 판금·금장·검·넓은 망토",
    0x11: "백청색 프리스트 제의·금장·성직 지팡이",
    0x13: "남청색 메이지 로브·금장·수정 지팡이",
    0x14: "백청색 아크메이지 로브·금장·수정 지팡이",
    0x15: "청백색 위저드 로브·금장·수정 지팡이",
    0x16: "백청색 하이프리스트 제의·성직 지팡이",
    0x18: "청백색 세이지 로브·마도서·수정 지팡이",
    0x19: "백은색 팔라딘 판금·청색 마갑·검",
    0x1D: "백은색 실버나이트 판금·청색 마갑·장창",
    0x28: "남청색 서머너 로브·룬 문양·두루마리·지팡이",
}

# Each generated board contains only the classes whose ROM map image is shared
# with a lower class for that commander.  Keeping the cell order explicit
# avoids guessing from the art and makes an incorrectly positioned crop
# impossible.
BOARD_SPECS: dict[int, dict[str, object]] = {
    2: {
        "file": "../logical16-v3/liana/liana-logical16-sheet-ai.png",
        "columns": 4,
        "rows": 4,
        "logical_grid": True,
        "class_ids": [0x08, 0x0B, 0x11, 0x13, 0x14, 0x15, 0x16, 0x18, 0x19, 0x1D, 0x28],
    },
    3: {
        "file": "../logical16-v3/lana/lana-logical16-sheet-ai.png",
        "columns": 4,
        "rows": 4,
        "logical_grid": True,
        "class_ids": [0x08, 0x0B, 0x11, 0x13, 0x14, 0x15, 0x16, 0x18, 0x19, 0x1D, 0x28],
    },
    4: {
        "file": "../logical16-v3/sherry/sherry-logical16-sheet-ai.png",
        "columns": 4,
        "rows": 4,
        "logical_grid": True,
        "class_ids": [0x04, 0x0B, 0x13, 0x14, 0x15, 0x17, 0x19, 0x1D, 0x1E, 0x21, 0x23],
    },
    5: {
        "file": "../logical16-v3/hein/hein-logical16-sheet-ai.png",
        "columns": 4,
        "rows": 4,
        "logical_grid": True,
        "class_ids": [0x09, 0x0A, 0x0B, 0x13, 0x14, 0x15, 0x16, 0x18, 0x19, 0x1A, 0x28],
    },
    6: {
        "file": "../logical16-v3/scott/scott-logical16-sheet-ai.png",
        "columns": 4,
        "rows": 4,
        "logical_grid": True,
        "class_ids": [0x04, 0x0B, 0x0C, 0x19, 0x1B, 0x1D, 0x1E, 0x29],
    },
    7: {
        "file": "../logical16-v3/keith/keith-logical16-sheet-ai.png",
        "columns": 4,
        "rows": 4,
        "logical_grid": True,
        "class_ids": [0x04, 0x0B, 0x11, 0x15, 0x16, 0x19, 0x1A, 0x1D, 0x1E, 0x24],
    },
    8: {
        "file": "../logical16-v3/aaron/aaron-logical16-sheet-ai.png",
        "columns": 4,
        "rows": 4,
        "logical_grid": True,
        "class_ids": [0x04, 0x0B, 0x0C, 0x13, 0x14, 0x17, 0x19, 0x1A, 0x1B, 0x23],
    },
    9: {
        "file": "../logical16-v3/lester/lester-logical16-sheet-ai.png",
        "columns": 4,
        "rows": 4,
        "logical_grid": True,
        "class_ids": [0x0C, 0x13, 0x14, 0x15, 0x19, 0x1B, 0x1D, 0x1F, 0x2A],
    },
    10: {
        "file": "../logical16-v3/jessica/jessica-logical16-sheet-ai.png",
        "columns": 4,
        "rows": 4,
        "logical_grid": True,
        "class_ids": [0x09, 0x0B, 0x11, 0x13, 0x14, 0x15, 0x16, 0x18, 0x19, 0x1A, 0x26],
    },
}


def cell_bounds(
    image: Image.Image,
    row: int,
    column: int,
    *,
    rows: int = GRID_ROWS,
    columns: int = GRID_COLUMNS,
) -> tuple[int, int, int, int]:
    return (
        round(column * image.width / columns),
        round(row * image.height / rows),
        round((column + 1) * image.width / columns),
        round((row + 1) * image.height / rows),
    )


def source_foreground(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    seed = Image.new("L", rgb.size, 0)
    for y in range(rgb.height):
        for x in range(rgb.width):
            red, green, blue = rgb.getpixel((x, y))
            brightest = max(red, green, blue)
            chroma = brightest - min(red, green, blue)
            if brightest >= 60 or chroma >= 20:
                seed.putpixel((x, y), 255)

    # The concept sheet is already pixel art, but its black outlines sit on a
    # dark gray background. Grow from visible color instead of treating every
    # dark pixel as background. Three source pixels are enough to retain the
    # outline while excluding the broad dark glow around each sprite.
    mask = central_component(seed.filter(ImageFilter.MaxFilter(7)))
    rgba = rgb.convert("RGBA")
    rgba.putalpha(mask)
    return rgba


def central_component(mask: Image.Image) -> Image.Image:
    width, height = mask.size
    active = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if mask.getpixel((x, y)) >= 128
    }
    components: list[set[tuple[int, int]]] = []
    while active:
        start = active.pop()
        component = {start}
        pending = [start]
        while pending:
            x, y = pending.pop()
            for ny in range(max(0, y - 1), min(height, y + 2)):
                for nx in range(max(0, x - 1), min(width, x + 2)):
                    point = (nx, ny)
                    if point in active:
                        active.remove(point)
                        component.add(point)
                        pending.append(point)
        components.append(component)
    if not components:
        return mask

    center_x = (width - 1) / 2
    center_y = (height - 1) / 2
    largest = max(len(component) for component in components)
    candidates = [
        component
        for component in components
        if len(component) >= largest * 0.2
    ]
    selected = min(
        candidates,
        key=lambda component: (
            (
                sum(x for x, _ in component) / len(component) - center_x
            )
            ** 2
            + (
                sum(y for _, y in component) / len(component) - center_y
            )
            ** 2,
            -len(component),
        ),
    )
    result = Image.new("L", mask.size, 0)
    for point in selected:
        result.putpixel(point, 255)
    return result


def source_subject(image: Image.Image) -> Image.Image:
    subject = source_foreground(image)
    bbox = subject.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("AI source cell is empty")
    return subject.crop(bbox)


def direct_stage_subject(image: Image.Image) -> Image.Image:
    """Isolate one direct five-stage figure from its pure-black backdrop.

    Each stage crop already contains exactly one centered figure, so the
    general Python connected-component walk is unnecessary here. Fast Pillow
    channel operations retain colored equipment clusters and lightly grow
    them into the dark outline; the final Elwin conversion restores the ROM
    outline and silhouette afterward.
    """

    rgb = image.convert("RGB")
    red, green, blue = rgb.split()
    brightest = ImageChops.lighter(
        ImageChops.lighter(red, green),
        blue,
    )
    mask = brightest.point(
        lambda value: 255 if value >= 32 else 0
    ).filter(ImageFilter.MaxFilter(31))
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("Elwin direct stage is empty")
    subject = rgb.convert("RGBA")
    subject.putalpha(mask)
    return subject.crop(bbox)


def accent_hue_bucket(color: tuple[int, int, int]) -> int | None:
    red, green, blue = (channel / 255 for channel in color)
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    if saturation < 0.45 or value < 0.4:
        return None
    return int(hue * 12) % 12


def accent_hues(
    image: Image.Image,
    *,
    minimum: int | None = None,
) -> set[int]:
    counts: Counter[int] = Counter()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = image.getpixel((x, y))
            if alpha < 64:
                continue
            bucket = accent_hue_bucket((red, green, blue))
            if bucket is not None:
                counts[bucket] += 1
    if minimum is None:
        minimum = max(
            8,
            round(image.width * image.height * 0.0015),
        )
    return {
        bucket
        for bucket, frequency in counts.items()
        if frequency >= minimum
    }


def nearest_detail_sample(image: Image.Image) -> Image.Image:
    wanted_hues = accent_hues(image)
    best: tuple[tuple[int, int, int, int], Image.Image] | None = None
    for offset_y in range(-1, 2):
        for offset_x in range(-1, 2):
            shifted = Image.new("RGBA", image.size, TRANSPARENT)
            shifted.alpha_composite(image, (-offset_x, -offset_y))
            candidate = shifted.resize((16, 16), RESAMPLING.NEAREST)
            score = (
                len(wanted_hues & accent_hues(candidate, minimum=1)),
                -abs(offset_x) - abs(offset_y),
                -abs(offset_y),
                -abs(offset_x),
            )
            if best is None or score > best[0]:
                best = (score, candidate)
    if best is None:
        raise ValueError("AI source cell produced no sampling candidate")
    return best[1]


def pixelize_cell(
    sheet: Image.Image,
    row: int,
    column: int,
    *,
    rows: int = GRID_ROWS,
    columns: int = GRID_COLUMNS,
) -> Image.Image:
    cell = source_subject(
        sheet.crop(
            cell_bounds(
                sheet,
                row,
                column,
                rows=rows,
                columns=columns,
            )
        )
    )
    # The concept sheet uses enlarged pseudo-pixels. Sample those blocks
    # directly into the complete 16x16 destination instead of averaging them;
    # averaging destroys one-pixel eyes and thin weapon edges. MAXCOVERAGE
    # retains small, high-contrast accent colors that MEDIANCUT discards.
    sampled = nearest_detail_sample(cell)
    alpha = sampled.getchannel("A").point(
        lambda value: 255 if value >= 64 else 0
    )
    rgb = Image.new("RGB", sampled.size, (0, 0, 0))
    rgb.paste(sampled.convert("RGB"), mask=alpha)
    palette = rgb.quantize(
        colors=15,
        method=QUANTIZE.MAXCOVERAGE,
        dither=DITHER.NONE,
    ).convert("RGB")
    result = palette.convert("RGBA")
    result.putalpha(alpha)
    return result


def board_cell(
    board: Image.Image,
    index: int,
    *,
    rows: int,
    columns: int,
) -> Image.Image:
    row, column = divmod(index, columns)
    if row >= rows:
        raise ValueError(
            f"board cell {index} exceeds {columns}x{rows} layout"
        )
    return board.crop(
        cell_bounds(
            board,
            row,
            column,
            rows=rows,
            columns=columns,
        )
    )


def quantize_16_color_rgba(
    image: Image.Image,
    *,
    visible_colors: int = 15,
) -> Image.Image:
    alpha = image.getchannel("A").point(
        lambda value: 255 if value >= 64 else 0
    )
    rgb = Image.new("RGB", image.size, (0, 0, 0))
    rgb.paste(image.convert("RGB"), mask=alpha)
    palette = rgb.quantize(
        colors=visible_colors,
        method=QUANTIZE.MAXCOVERAGE,
        dither=DITHER.NONE,
    ).convert("RGB")
    result = palette.convert("RGBA")
    result.putalpha(alpha)
    return result


def align_logical_sprite_to_bottom(image: Image.Image) -> Image.Image:
    """Move a native logical sprite down without cropping or rescaling it."""

    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("generated logical class cell is empty")
    offset_y = 16 - bbox[3]
    if offset_y <= 0:
        return image
    result = Image.new("RGBA", (16, 16), TRANSPARENT)
    result.alpha_composite(image, (0, offset_y))
    return result


def fit_subject_to_16(
    image: Image.Image,
    *,
    maximum_extent: int = 16,
    foreground_isolated: bool = False,
) -> Image.Image:
    """Fit a generated sprite without stretching, clipping, or averaging it.

    Preserve the generated board's hard source pixels with nearest-neighbour
    sampling, use the complete 16-pixel extent on the limiting axis, center
    horizontally, and align feet or a mount to the bottom row. Reserving even
    one blank border pixel here discards too much class equipment.
    """

    subject = (
        image.convert("RGBA")
        if foreground_isolated
        else source_subject(image)
    )
    width, height = subject.size
    scale = min(maximum_extent / width, maximum_extent / height)
    target_width = max(1, min(maximum_extent, round(width * scale)))
    target_height = max(1, min(maximum_extent, round(height * scale)))
    sampled = subject.resize(
        (target_width, target_height),
        RESAMPLING.NEAREST,
    )
    sampled = quantize_16_color_rgba(sampled)
    sampled_bbox = sampled.getchannel("A").getbbox()
    if sampled_bbox is None:
        raise ValueError("generated class cell vanished during 16x16 fit")
    sampled = sampled.crop(sampled_bbox)
    target_width, target_height = sampled.size
    result = Image.new("RGBA", (16, 16), TRANSPARENT)
    x = (16 - target_width) // 2
    y = 16 - target_height
    result.alpha_composite(sampled, (x, y))
    return result


def fill_subject_across_16_columns(
    image: Image.Image,
    *,
    foreground_isolated: bool = False,
) -> Image.Image:
    """Map a full-square AI composition directly onto logical 16x16.

    Sample the enlarged logical blocks at nearest-neighbour cell centers.
    Then normalize only if a thin extreme weapon tip caused the first sample
    to miss an edge. This keeps broad hems, boots, shields, and staff shafts
    on the outer rows instead of reducing an entire edge to one endpoint
    pixel. The identity-lock pass later restores the exact source head.
    """

    subject = (
        image.convert("RGBA")
        if foreground_isolated
        else source_subject(image)
    )
    bbox = subject.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("generated logical class cell is empty")
    subject = subject.crop(bbox)
    sampled = subject.resize(
        (16, 16),
        RESAMPLING.NEAREST,
    )
    sampled_bbox = sampled.getchannel("A").getbbox()
    if sampled_bbox is None:
        raise ValueError("full-canvas AI sample is empty")
    if sampled_bbox != (0, 0, 16, 16):
        sampled = sampled.crop(sampled_bbox).resize(
            (16, 16),
            RESAMPLING.NEAREST,
        )
    return quantize_16_color_rgba(sampled)


def dominant_colors(
    image: Image.Image,
    count: int = 6,
) -> list[str]:
    rgba = image.convert("RGBA")
    colors = rgba.getcolors(maxcolors=rgba.width * rgba.height) or []
    visible = [
        (frequency, color)
        for frequency, color in colors
        if color[3] >= 96 and max(color[:3]) > 45
    ]
    visible.sort(reverse=True)
    return [
        f"#{red:02x}{green:02x}{blue:02x}"
        for _, (red, green, blue, _) in visible[:count]
    ]


def remove_magenta_background(image: Image.Image) -> Image.Image:
    """Remove the flat magenta generation background without soft edges."""

    rgba = image.convert("RGBA")
    red, green, blue, alpha = rgba.split()
    red_high = red.point(lambda value: 255 if value >= 160 else 0)
    blue_high = blue.point(lambda value: 255 if value >= 160 else 0)
    green_low = green.point(lambda value: 255 if value <= 96 else 0)
    background = ImageChops.multiply(
        ImageChops.multiply(red_high, blue_high),
        green_low,
    )
    rgba.putalpha(
        ImageChops.multiply(alpha, ImageChops.invert(background))
    )
    return rgba


def remove_all_magenta_background(
    image: Image.Image,
) -> Image.Image:
    """Remove a generated chroma key and every dark purple fringe shade.

    Image generation may render the requested #ff00ff backdrop closer to
    #e407df and soften it through several darker violet edge shades. These
    targeted Hein v3 sources deliberately use no purple equipment color, so
    remove every key-like shade globally. This also clears background pockets
    enclosed between a hand, robe, and staff rather than mistaking them for
    interior character detail.
    """

    result = image.convert("RGBA")
    width, height = result.size
    pixels = result.load()

    def is_key_or_fringe(x: int, y: int) -> bool:
        red, green, blue, alpha = pixels[x, y]
        bright_key = (
            red >= 50
            and blue >= 50
            and green <= 100
            and red + blue >= 140
            and red >= green * 1.25
            and blue >= green * 1.25
        )
        dark_fringe = (
            red >= 36
            and blue >= 36
            and green * 2 < min(red, blue)
        )
        return bool(alpha and (bright_key or dark_fringe))

    for y in range(height):
        for x in range(width):
            if is_key_or_fringe(x, y):
                pixels[x, y] = TRANSPARENT
    return result


def remove_ai_border_colors(
    image: Image.Image,
    locked_points: set[tuple[int, int]],
) -> Image.Image:
    """Replace AI-only black/magenta remnants outside the identity mask."""

    result = image.convert("RGBA")
    for y in range(result.height):
        for x in range(result.width):
            if (x, y) in locked_points:
                continue
            red, green, blue, alpha = result.getpixel((x, y))
            if not alpha:
                continue
            pure_black = red == 0 and green == 0 and blue == 0
            purple_fringe = (
                red >= 36
                and blue >= 36
                and green * 2 < min(red, blue)
            )
            if pure_black or purple_fringe:
                result.putpixel((x, y), ROM_INK)
    return result


def require_full_16_canvas(
    image: Image.Image,
    *,
    label: str,
) -> None:
    """Reject AI sprites that leave any complete logical row or column empty."""

    empty_rows = [
        y
        for y in range(16)
        if not any(image.getpixel((x, y))[3] for x in range(16))
    ]
    empty_columns = [
        x
        for x in range(16)
        if not any(image.getpixel((x, y))[3] for y in range(16))
    ]
    if empty_rows or empty_columns:
        raise ValueError(
            f"{label} does not fill logical 16x16 canvas: "
            f"empty rows={empty_rows}, empty columns={empty_columns}"
        )


def connected_logical_subjects(
    image: Image.Image,
    *,
    expected_count: int,
    columns: int,
) -> list[Image.Image] | None:
    """Recover complete sprites that AI drew across nominal grid borders.

    A generated logical sheet sometimes places a robe, mount, or staff a few
    source pixels over an equal 4x4 boundary.  The foreground sprites are
    normally separate connected pixel-art components, so extract those whole
    components before converting them instead of clipping at the nominal
    boundary.  Return ``None`` for sheets whose adjacent figures genuinely
    touch; their exact cells remain the safer fallback.
    """

    rgba = remove_magenta_background(image)
    alpha = rgba.getchannel("A").point(
        lambda value: 255 if value >= 64 else 0
    )
    width, height = alpha.size
    pixels = alpha.load()
    visited = bytearray(width * height)
    minimum_area = max(128, round(width * height * 0.0025))
    components: list[
        tuple[float, float, Image.Image]
    ] = []
    for y in range(height):
        for x in range(width):
            position = y * width + x
            if visited[position] or not pixels[x, y]:
                continue
            pending = [position]
            visited[position] = 1
            points: list[int] = []
            left = right = x
            top = bottom = y
            sum_x = 0
            sum_y = 0
            while pending:
                current = pending.pop()
                current_y, current_x = divmod(current, width)
                points.append(current)
                sum_x += current_x
                sum_y += current_y
                left = min(left, current_x)
                right = max(right, current_x)
                top = min(top, current_y)
                bottom = max(bottom, current_y)
                for neighbor_y in range(
                    max(0, current_y - 1),
                    min(height, current_y + 2),
                ):
                    row_offset = neighbor_y * width
                    for neighbor_x in range(
                        max(0, current_x - 1),
                        min(width, current_x + 2),
                    ):
                        neighbor = row_offset + neighbor_x
                        if (
                            not visited[neighbor]
                            and pixels[neighbor_x, neighbor_y]
                        ):
                            visited[neighbor] = 1
                            pending.append(neighbor)
            area = len(points)
            if area < minimum_area:
                continue
            box = (left, top, right + 1, bottom + 1)
            mask = Image.new(
                "L",
                (right - left + 1, bottom - top + 1),
                0,
            )
            mask_pixels = mask.load()
            for point in points:
                point_y, point_x = divmod(point, width)
                mask_pixels[point_x - left, point_y - top] = 255
            subject = rgba.crop(box)
            subject.putalpha(
                ImageChops.multiply(subject.getchannel("A"), mask)
            )
            components.append(
                (sum_x / area, sum_y / area, subject)
            )
    if len(components) != expected_count:
        return None

    # Reading order is four figures per visual row.  Row-to-row separation is
    # much larger than the small baseline variation inside one row.
    components.sort(key=lambda item: item[1])
    ordered: list[Image.Image] = []
    for start in range(0, expected_count, columns):
        row = components[start : start + columns]
        row.sort(key=lambda item: item[0])
        ordered.extend(subject for _, _, subject in row)
    return ordered


def nearest_palette_color(
    color: tuple[int, int, int, int],
    palette: list[tuple[int, int, int, int]],
) -> tuple[int, int, int, int]:
    return min(
        palette,
        key=lambda candidate: sum(
            (candidate[channel] - color[channel]) ** 2
            for channel in range(3)
        ),
    )


def mega_drive_palette_color(
    color: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    return (
        *(
            min(
                MEGA_DRIVE_CHANNEL_LEVELS,
                key=lambda level: abs(level - color[channel]),
            )
            for channel in range(3)
        ),
        255,
    )


def protected_eye_points(
    source: Image.Image,
) -> set[tuple[int, int]]:
    """Find the original eye whites and dark eye pixels to lock.

    Most commander faces use one white pixel immediately followed by one
    black pixel. Front-facing Sherry sprites use two such pairs. Scott's
    original sprites use a dark-blue eye instead of black, so that source
    color is accepted as well. Candidate pairs are restricted to the skin
    component nearest the face to avoid mistaking weapon highlights for eyes.
    """

    skin = {
        (x, y)
        for y in range(min(12, source.height))
        for x in range(source.width)
        if source.getpixel((x, y)) == ROM_SKIN
    }
    if not skin:
        return set()

    components: list[set[tuple[int, int]]] = []
    active = set(skin)
    while active:
        start = active.pop()
        component = {start}
        pending = [start]
        while pending:
            x, y = pending.pop()
            for nx in range(max(0, x - 1), min(source.width, x + 2)):
                for ny in range(
                    max(0, y - 1),
                    min(min(12, source.height), y + 2),
                ):
                    point = (nx, ny)
                    if point in active:
                        active.remove(point)
                        component.add(point)
                        pending.append(point)
        components.append(component)
    face = max(
        components,
        key=lambda component: (
            len(component),
            -min(y for _, y in component),
        ),
    )
    center_x = sum(x for x, _ in face) / len(face)
    center_y = sum(y for _, y in face) / len(face)

    def distance_to_face(x: int, y: int) -> int:
        return min(
            max(abs(x - face_x), abs(y - face_y))
            for face_x, face_y in face
        )

    pairs: list[tuple[int, int]] = []
    dark_eye_colors = {ROM_INK, ROM_BLUE_EYE}
    for y in range(min(12, source.height)):
        for x in range(source.width - 1):
            if (
                source.getpixel((x, y)) == ROM_WHITE
                and source.getpixel((x + 1, y)) in dark_eye_colors
                and min(
                    distance_to_face(x, y),
                    distance_to_face(x + 1, y),
                )
                <= 1
            ):
                pairs.append((x, y))
    if pairs:
        _, eye_y = min(
            pairs,
            key=lambda point: (
                (point[0] + 0.5 - center_x) ** 2
                + (point[1] - center_y) ** 2,
                point[1],
                point[0],
            ),
        )
        face_left = min(x for x, _ in face)
        face_right = max(x for x, _ in face)
        result: set[tuple[int, int]] = set()
        for x, y in pairs:
            if (
                y == eye_y
                and face_left - 1 <= x + 0.5 <= face_right + 1
            ):
                result.update({(x, y), (x + 1, y)})
        if result:
            return result

    # A few Scott mount sprites use gray immediately left of a blue eye.
    # Preserve that exact two-pixel source pair rather than inventing white.
    blue_candidates = [
        (x, y)
        for y in range(min(12, source.height))
        for x in range(source.width)
        if (
            source.getpixel((x, y)) == ROM_BLUE_EYE
            and distance_to_face(x, y) <= 1
        )
    ]
    if not blue_candidates:
        return set()
    eye_x, eye_y = min(
        blue_candidates,
        key=lambda point: (
            (point[0] - center_x) ** 2 + (point[1] - center_y) ** 2,
            point[1],
            point[0],
        ),
    )
    result = {(eye_x, eye_y)}
    if eye_x:
        result.add((eye_x - 1, eye_y))
    return result


def identity_locked_character_sprite(
    direct_source: Image.Image,
    original: Image.Image,
    palette: list[tuple[int, int, int, int]],
    locked_points: set[tuple[int, int]] | None = None,
    *,
    additional_locked_points: set[tuple[int, int]] | None = None,
    preserve_generated_palette: bool = False,
    restore_transparent_locked_points: bool = True,
) -> tuple[
    Image.Image,
    int,
    tuple[int, int, int, int],
    set[tuple[int, int]],
]:
    """Keep an accepted AI silhouette but restore the ROM character's head.

    The character sheets are coherent low-resolution pixel art. Their armor,
    weapon, cape, mount, and body silhouette are retained. The original class
    head rectangle (including transparent gaps) and eye pixels replace the
    generated head so identity remains byte-exact.
    """

    sampled = direct_source.convert("RGBA").resize(
        (16, 16),
        RESAMPLING.NEAREST,
    )

    detected_box = head_lock_box(original)
    lock_box = (
        detected_box[0],
        detected_box[1],
        detected_box[2],
        max(9, detected_box[3]),
    )
    eye_points = protected_eye_points(original)
    automatic_points = box_points(lock_box) | eye_points
    effective_points = (
        automatic_points
        if locked_points is None
        else set(locked_points) | eye_points
    )
    effective_points |= set(additional_locked_points or ())
    applied_lock_points = (
        effective_points
        if restore_transparent_locked_points
        else {
            point
            for point in effective_points
            if original.getpixel(point)[3]
        }
    )

    if preserve_generated_palette:
        # A 4bpp sprite has 15 visible slots.  Reserve the exact colors used
        # by the saved identity pixels, then spend the remaining slots on the
        # generated equipment.  This keeps deliberate class colors such as a
        # Wizard's purple cape instead of forcing them into an unrelated
        # brown/gold color from the commander's old equipment palette.
        identity_colors: list[tuple[int, int, int, int]] = []
        for point in sorted(applied_lock_points):
            color = original.getpixel(point)
            if color[3] and color not in identity_colors:
                identity_colors.append(color)
        available_colors = max(1, 15 - len(identity_colors))
        equipment = sampled.copy()
        for point in applied_lock_points:
            equipment.putpixel(point, TRANSPARENT)
        equipment = quantize_16_color_rgba(
            equipment,
            visible_colors=available_colors,
        )
        equipment_colors: list[tuple[int, int, int, int]] = []
        for _, color in sorted(
            equipment.getcolors(maxcolors=256) or [],
            reverse=True,
        ):
            if not color[3]:
                continue
            snapped = mega_drive_palette_color(color)
            if (
                snapped not in identity_colors
                and snapped not in equipment_colors
            ):
                equipment_colors.append(snapped)
        palette = (
            identity_colors
            + equipment_colors[: 15 - len(identity_colors)]
        )

    result = Image.new("RGBA", (16, 16), TRANSPARENT)
    for y in range(16):
        for x in range(16):
            color = sampled.getpixel((x, y))
            if color[3] < 64:
                continue
            result.putpixel(
                (x, y),
                nearest_palette_color(color, palette),
            )

    for point in applied_lock_points:
        result.putpixel(point, original.getpixel(point))

    changed = sum(
        result.getpixel((x, y)) != original.getpixel((x, y))
        for y in range(16)
        for x in range(16)
    )
    return result, changed, lock_box, automatic_points


def _build_assets_unlocked(
    rom_path: Path,
    board_dir: Path,
    output_dir: Path,
    elwin_source_dir: Path = ELWIN_NATIVE_SOURCE_DIR,
) -> dict[str, object]:
    source = rom_path.read_bytes()
    classes = class_names(source)
    identity_mask_overrides = load_identity_mask_overrides()
    for mask_path, mask_label in (
        (SHARED_NEW_CLASS_MASKS, "shared-new-class identity"),
        (KEITH_LESTER_TIER_IDENTITY_MASKS, "tier-mounted identity"),
    ):
        for key, points in load_pixel_mask_overrides(
            mask_path,
            label=mask_label,
        ).items():
            identity_mask_overrides.setdefault(key, points)
    for key, excluded_points in IDENTITY_MASK_EXCLUDED_POINTS.items():
        if key in identity_mask_overrides:
            identity_mask_overrides[key] -= excluded_points
    mount_mask_overrides = load_mount_mask_overrides()
    for key, points in load_pixel_mask_overrides(
        KEITH_LESTER_TIER_MOUNT_MASKS,
        label="tier-mounted mount",
    ).items():
        mount_mask_overrides.setdefault(key, points)
    design_overrides = load_ai_design_overrides()
    commanders: dict[str, object] = {}
    asset_count = 0
    redesigned_count = 0
    if output_dir.exists():
        shutil.rmtree(output_dir)
    source_cell_dir = output_dir / "source-cells"
    source_cell_dir.mkdir(parents=True, exist_ok=True)
    source_original_dir = output_dir / "source-originals"
    source_original_dir.mkdir(parents=True, exist_ok=True)
    source_original_files: dict[tuple[int, int], str] = {}
    for key, source_original_path in AI_SOURCE_ORIGINAL_FILES.items():
        if not source_original_path.is_file():
            raise FileNotFoundError(
                f"AI source original is missing: {source_original_path}"
            )
        target = (
            source_original_dir / f"{key[0]}-{key[1]:02X}.png"
        )
        Image.open(source_original_path).convert("RGBA").save(
            target,
            optimize=True,
        )
        source_original_files[key] = str(
            target.relative_to(output_dir)
        )

    board_subjects: dict[tuple[int, int], Image.Image] = {}
    converted_subjects: dict[tuple[int, int], Image.Image] = {}
    source_cell_files: dict[tuple[int, int], str] = {}
    native_changed_pixels: dict[tuple[int, int], int] = {}
    native_lock_boxes: dict[
        tuple[int, int], tuple[int, int, int, int]
    ] = {}
    native_automatic_mask_points: dict[
        tuple[int, int], set[tuple[int, int]]
    ] = {}
    board_paths: list[Path] = []
    targeted_native_source_paths: list[Path] = []
    for commander_id, spec in BOARD_SPECS.items():
        board_path = (board_dir / str(spec["file"])).resolve()
        board_paths.append(board_path)
        board = Image.open(board_path).convert("RGB")
        rows = int(spec["rows"])
        columns = int(spec["columns"])
        class_ids = list(spec["class_ids"])
        tiers = class_tiers(source, commander_id)
        sprite_map = commander_sprite_map(source, commander_id)
        originals = {
            class_id: render_sprite(
                source,
                sprite_map[class_id],
                1,
            )
            for class_id in tiers
        }
        palette: list[tuple[int, int, int, int]] = []
        for original in originals.values():
            for _, color in original.getcolors(maxcolors=256) or []:
                if color[3] and color not in palette:
                    palette.append(color)
        if len(palette) > 15:
            raise ValueError(
                f"commander {commander_id} ROM palette exceeds "
                "15 visible colors"
            )
        logical_grid = bool(spec.get("logical_grid"))
        recovered_subjects = (
            connected_logical_subjects(
                board,
                expected_count=len(class_ids),
                columns=columns,
            )
            if logical_grid
            else None
        )
        for index, class_id in enumerate(class_ids):
            row, column = divmod(index, columns)
            row_bounds = spec.get("row_bounds")
            if row_bounds is None:
                cell = board_cell(
                    board,
                    index,
                    rows=rows,
                    columns=columns,
                )
            else:
                bounds = [int(value) for value in row_bounds]
                if (
                    len(bounds) != rows + 1
                    or bounds[0] != 0
                    or bounds[-1] != board.height
                ):
                    raise ValueError(
                        f"invalid row bounds for {board_path}: {bounds}"
                    )
                left, _, right, _ = cell_bounds(
                    board,
                    row,
                    column,
                    rows=rows,
                    columns=columns,
                )
                cell = board.crop(
                    (
                        left,
                        bounds[row],
                        right,
                        bounds[row + 1],
                    )
                )
            if logical_grid:
                # Prefer the whole connected sprite.  This recovers robes,
                # mounts, and staves that the generator placed a few source
                # pixels across the nominal 4x4 boundary.  Lana and Lester
                # contain genuinely touching adjacent figures, so those two
                # sheets safely fall back to their already aligned cells.
                subject = (
                    recovered_subjects[index]
                    if recovered_subjects is not None
                    else remove_magenta_background(cell)
                )
                bbox = subject.getchannel("A").getbbox()
                if bbox is None:
                    raise ValueError(
                        f"AI source cell is empty: {board_path} "
                        f"index {index}"
                    )
                subject = subject.crop(bbox)
            elif board_path.name.endswith("-v2.png"):
                # The new identity-locked sheets use an exact magenta
                # backdrop. Removing it directly retains separated weapons,
                # hands, staves, and mounts without growing their silhouette.
                subject = remove_magenta_background(cell)
                bbox = subject.getchannel("A").getbbox()
                if bbox is None:
                    raise ValueError(
                        f"AI source cell is empty: {board_path} "
                        f"index {index}"
                    )
                subject = subject.crop(bbox)
            else:
                # Older character-ai-v3 sheets use a pure black backdrop and
                # may have a one-logical-pixel gap between the hand and staff,
                # sword, or mount. The wider direct-sheet mask keeps those
                # intentionally separated equipment pixels attached.
                subject = direct_stage_subject(cell)
            target = (
                source_cell_dir
                / f"{commander_id}-{class_id:02X}.png"
            )
            subject.save(target, optimize=True)
            key = (commander_id, class_id)
            generated_16 = fit_subject_to_16(
                subject,
                foreground_isolated=True,
            )
            converted, changed, lock_box, automatic_points = (
                identity_locked_character_sprite(
                    generated_16,
                    originals[class_id],
                    palette,
                    identity_mask_overrides.get(key),
                    additional_locked_points=mount_mask_overrides.get(key),
                    preserve_generated_palette=logical_grid,
                )
            )
            board_subjects[key] = subject
            converted_subjects[key] = converted
            source_cell_files[key] = str(
                target.relative_to(output_dir)
            )
            native_changed_pixels[key] = changed
            native_lock_boxes[key] = lock_box
            native_automatic_mask_points[key] = automatic_points

        if commander_id in {2, 3}:
            color_dir = (
                "native16-red"
                if commander_id == 2
                else "native16-blue"
            )
            for class_id, filename in (
                LIANA_LANA_PAIRED_SOURCE_FILES.items()
            ):
                source_path = (
                    LIANA_LANA_PAIRED_SOURCE_ROOT
                    / color_dir
                    / filename
                )
                targeted_native_source_paths.append(source_path)
                generated_16 = Image.open(source_path).convert("RGBA")
                if generated_16.size != (16, 16):
                    raise ValueError(
                        "Liana/Lana native source must be literal 16x16: "
                        f"{source_path} is {generated_16.size}"
                    )
                target = (
                    source_cell_dir
                    / f"{commander_id}-{class_id:02X}.png"
                )
                generated_16.save(target, optimize=True)
                key = (commander_id, class_id)
                converted, changed, lock_box, automatic_points = (
                    identity_locked_character_sprite(
                        generated_16,
                        originals[class_id],
                        palette,
                        identity_mask_overrides.get(key),
                        additional_locked_points=mount_mask_overrides.get(key),
                        preserve_generated_palette=True,
                    )
                )
                effective_points = (
                    automatic_points
                    if identity_mask_overrides.get(key) is None
                    else (
                        set(identity_mask_overrides[key])
                        | protected_eye_points(originals[class_id])
                    )
                )
                effective_points |= mount_mask_overrides.get(key, set())
                # These sources are already literal 16x16, 4bpp, and contain
                # the exact locked head. Keep the AI-native pixels byte-for-
                # byte instead of re-quantizing them a second time.
                converted = generated_16.copy()
                for point in effective_points:
                    converted.putpixel(
                        point,
                        originals[class_id].getpixel(point),
                    )
                changed = sum(
                    converted.getpixel((x, y))
                    != originals[class_id].getpixel((x, y))
                    for y in range(16)
                    for x in range(16)
                )
                require_full_16_canvas(
                    converted,
                    label=(
                        f"{KOREAN_NAME_BY_ID[commander_id]} "
                        f"class {class_id:02X}"
                    ),
                )
                board_subjects[key] = generated_16
                converted_subjects[key] = converted
                source_cell_files[key] = str(
                    target.relative_to(output_dir)
                )
                native_changed_pixels[key] = changed
                native_lock_boxes[key] = lock_box
                native_automatic_mask_points[key] = automatic_points

        if commander_id == 5:
            for class_id, filename in (
                HEIN_LATEST_SOURCE_FILES.items()
            ):
                key = (commander_id, class_id)
                if key in {(5, 0x09), (5, 0x19)}:
                    # These now come from stock ROM class silhouettes through
                    # the shared-template pass below, not Hein's former AI
                    # source sheet.
                    continue
                source_path = (
                    HEIN_SORCERER_V2_CLEAN_SOURCE
                    if key in AI_NATIVE_LOGICAL_SOURCE_KEYS
                    else HEIN_LATEST_SOURCE_DIR / filename
                )
                targeted_native_source_paths.append(source_path)
                if key in AI_NATIVE_LOGICAL_SOURCE_KEYS:
                    targeted_native_source_paths.append(
                        HEIN_SORCERER_V2_LOGICAL_SOURCE
                    )
                isolated = remove_all_magenta_background(
                    Image.open(source_path).convert("RGBA")
                )
                bbox = isolated.getchannel("A").getbbox()
                if bbox is None:
                    raise ValueError(
                        f"Hein latest full-square source is empty: "
                        f"{source_path}"
                    )
                isolated = isolated.crop(bbox)
                preview_source = isolated.copy()
                preview_source.thumbnail(
                    (512, 512),
                    RESAMPLING.NEAREST,
                )
                target = (
                    source_cell_dir
                    / f"{commander_id}-{class_id:02X}.png"
                )
                preview_source.save(target, optimize=True)
                if key in AI_NATIVE_LOGICAL_SOURCE_KEYS:
                    generated_16 = Image.open(
                        HEIN_SORCERER_V2_LOGICAL_SOURCE
                    ).convert("RGBA")
                    converted, changed, lock_box, automatic_points = (
                        identity_locked_character_sprite(
                            generated_16,
                            originals[class_id],
                            palette,
                            identity_mask_overrides.get(key),
                            additional_locked_points=(
                                mount_mask_overrides.get(key)
                            ),
                            preserve_generated_palette=True,
                        )
                    )
                    generated_bbox = converted.getchannel("A").getbbox()
                    if (
                        generated_bbox is None
                        or generated_bbox[1] != 0
                        or generated_bbox[3] != 16
                    ):
                        raise ValueError(
                            "Hein Sorcerer AI logical source must use "
                            "all 16 rows"
                        )
                else:
                    generated_16 = fill_subject_across_16_columns(
                        isolated,
                        foreground_isolated=True,
                    )
                    converted, changed, lock_box, automatic_points = (
                        identity_locked_character_sprite(
                            generated_16,
                            originals[class_id],
                            palette,
                            identity_mask_overrides.get(key),
                            additional_locked_points=(
                                mount_mask_overrides.get(key)
                            ),
                            preserve_generated_palette=True,
                        )
                    )
                    effective_points = (
                        automatic_points
                        if identity_mask_overrides.get(key) is None
                        else (
                            set(identity_mask_overrides[key])
                            | protected_eye_points(originals[class_id])
                        )
                    )
                    effective_points |= mount_mask_overrides.get(
                        key,
                        set(),
                    )
                    converted = remove_ai_border_colors(
                        converted,
                        effective_points,
                    )
                    require_full_16_canvas(
                        converted,
                        label=f"Hein class {class_id:02X}",
                    )
                board_subjects[key] = preview_source
                converted_subjects[key] = converted
                source_cell_files[key] = str(
                    target.relative_to(output_dir)
                )
                native_changed_pixels[key] = changed
                if lock_box is not None:
                    native_lock_boxes[key] = lock_box
                native_automatic_mask_points[key] = automatic_points

    native_specs = {
        1: {
            "source_dir": elwin_source_dir,
            "files": ELWIN_NATIVE_SOURCE_FILES,
            "direct_source": ELWIN_DIRECT_STAGE_SOURCE,
            "direct_stages": ELWIN_DIRECT_STAGE_CLASSES,
            "character_ai_source": ELWIN_MAGIC_SOURCE,
            "character_ai_classes": ELWIN_CHARACTER_AI_CLASSES,
            "features": ELWIN_EQUIPMENT_FEATURES,
        },
        4: {
            "source_dir": SHERRY_NATIVE_SOURCE_DIR,
            "files": SHERRY_NATIVE_SOURCE_FILES,
            "direct_source": None,
            "direct_stages": {},
            "character_ai_source": None,
            "character_ai_classes": {},
            "features": SHERRY_EQUIPMENT_FEATURES,
            "preserve_generated_palette": True,
        },
    }
    native_source_paths: list[Path] = []
    for commander_id, spec in native_specs.items():
        tiers = class_tiers(source, commander_id)
        sprite_map = commander_sprite_map(source, commander_id)
        originals = {
            class_id: render_sprite(
                source,
                sprite_map[class_id],
                1,
            )
            for class_id in tiers
        }
        by_sprite: dict[int, list[int]] = defaultdict(list)
        for class_id in tiers:
            by_sprite[sprite_map[class_id]].append(class_id)
        for group in by_sprite.values():
            group.sort(key=lambda value: (tiers[value], value))
        eligible_class_ids = {
            class_id
            for class_id in tiers
            if (
                len(by_sprite[sprite_map[class_id]]) > 1
                and by_sprite[sprite_map[class_id]].index(class_id) > 0
            )
        }
        source_files = dict(spec["files"])
        direct_stages = dict(spec["direct_stages"])
        character_ai_classes = dict(spec["character_ai_classes"])
        provided_class_ids = (
            set(source_files)
            | set(direct_stages)
            | set(character_ai_classes)
        )
        # A hidden destination without a dedicated AI source is added later
        # as an editable stock 16x16 baseline.  It can share a physical sprite
        # with another class, but it is not a missing native-source input.
        eligible_class_ids -= {
            route.candidates[0]
            for route in hidden_class_routes(commander_id)
            if route.candidates[0] not in provided_class_ids
        }
        if provided_class_ids != eligible_class_ids:
            raise ValueError(
                f"commander {commander_id} native sources must contain "
                f"only upper duplicate classes: expected "
                f"{sorted(eligible_class_ids)}, got "
                f"{sorted(provided_class_ids)}"
            )
        if (
            set(source_files) & set(direct_stages)
            or set(source_files) & set(character_ai_classes)
            or set(direct_stages) & set(character_ai_classes)
        ):
            raise ValueError(
                f"commander {commander_id} classes cannot use more than "
                "one AI source"
            )

        palette: list[tuple[int, int, int, int]] = []
        for original in originals.values():
            for _, color in original.getcolors(maxcolors=256) or []:
                if color[3] and color not in palette:
                    palette.append(color)
        if len(palette) > 15:
            raise ValueError(
                f"commander {commander_id} ROM palette exceeds "
                "15 visible colors"
            )

        for class_id, filename in source_files.items():
            source_dir = (
                ELWIN_LORD_SOURCE_DIR
                if commander_id == 1 and class_id == 0x04
                else ELWIN_HERO_SOURCE_DIR
                if commander_id == 1 and class_id == 0x22
                else ELWIN_MOUNTED_SOURCE_DIR
                if commander_id == 1 and class_id in {0x0C, 0x1D}
                else Path(spec["source_dir"])
            )
            source_path = source_dir / filename
            native_source_paths.append(source_path)
            ai_source = Image.open(source_path).convert("RGBA")
            isolated_source = remove_magenta_background(ai_source)
            source_bbox = isolated_source.getchannel("A").getbbox()
            if source_bbox is None:
                raise ValueError(
                    f"native AI source {source_path} has no foreground"
                )
            isolated_source = isolated_source.crop(source_bbox)
            preview_source = isolated_source.copy()
            preview_source.thumbnail(
                (512, 512),
                RESAMPLING.NEAREST,
            )
            target = (
                source_cell_dir / f"{commander_id}-{class_id:02X}.png"
            )
            preview_source.save(target, optimize=True)
            key = (commander_id, class_id)
            logical_source_path = (
                source_dir / "logical16" / filename
            )
            if logical_source_path.is_file():
                logical_source = Image.open(
                    logical_source_path
                ).convert("RGBA")
                if logical_source.size != (16, 16):
                    raise ValueError(
                        f"native logical source {logical_source_path} "
                        f"must be 16x16, got {logical_source.size}"
                    )
                generated_16 = quantize_16_color_rgba(
                    remove_magenta_background(logical_source)
                )
            else:
                generated_16 = fit_subject_to_16(
                    isolated_source,
                    foreground_isolated=True,
                )
            converted, changed, lock_box, automatic_points = (
                identity_locked_character_sprite(
                    generated_16,
                    originals[class_id],
                    palette,
                    identity_mask_overrides.get(key),
                    additional_locked_points=mount_mask_overrides.get(key),
                    preserve_generated_palette=bool(
                        spec.get("preserve_generated_palette")
                    )
                    or (
                        commander_id == 1
                        and class_id in {0x04, 0x0C, 0x1D, 0x22}
                    ),
                )
            )
            if commander_id == 4:
                protected_points = (
                    set(identity_mask_overrides[key])
                    if key in identity_mask_overrides
                    else automatic_points
                )
                protected_points |= mount_mask_overrides.get(key, set())
                for y in range(16):
                    for x in range(16):
                        if (
                            (x, y) not in protected_points
                            and converted.getpixel((x, y))
                            == (0, 0, 0, 255)
                        ):
                            converted.putpixel((x, y), ROM_INK)
                changed = sum(
                    converted.getpixel((x, y))
                    != originals[class_id].getpixel((x, y))
                    for y in range(16)
                    for x in range(16)
                )
            board_subjects[key] = preview_source
            converted_subjects[key] = converted
            source_cell_files[key] = str(target.relative_to(output_dir))
            native_changed_pixels[key] = changed
            native_lock_boxes[key] = lock_box
            native_automatic_mask_points[key] = automatic_points

        if direct_stages:
            direct_source_path = Path(spec["direct_source"])
            native_source_paths.append(direct_source_path)
            direct_sheet = Image.open(direct_source_path).convert("RGB")
            if direct_sheet.size != (2172, 724):
                raise ValueError(
                    "Elwin direct five-stage source changed size: "
                    f"{direct_sheet.size}"
                )
            for class_id, stage in direct_stages.items():
                stage_subject = direct_stage_subject(
                    direct_sheet.crop(
                        ELWIN_DIRECT_STAGE_BOUNDS[stage]
                    )
                )
                preview_source = stage_subject.copy()
                preview_source.thumbnail(
                    (512, 512),
                    RESAMPLING.NEAREST,
                )
                target = (
                    source_cell_dir
                    / f"{commander_id}-{class_id:02X}.png"
                )
                preview_source.save(target, optimize=True)
                direct_16 = fit_subject_to_16(
                    stage_subject,
                    foreground_isolated=True,
                )
                key = (commander_id, class_id)
                converted, changed, lock_box, automatic_points = (
                    identity_locked_character_sprite(
                        direct_16,
                        originals[class_id],
                        palette,
                        identity_mask_overrides.get(key),
                        additional_locked_points=mount_mask_overrides.get(key),
                    )
                )
                board_subjects[key] = preview_source
                converted_subjects[key] = converted
                source_cell_files[key] = str(
                    target.relative_to(output_dir)
                )
                native_changed_pixels[key] = changed
                native_lock_boxes[key] = lock_box
                native_automatic_mask_points[key] = automatic_points

        if character_ai_classes:
            character_source_path = Path(spec["character_ai_source"])
            native_source_paths.append(character_source_path)
            character_sheet = Image.open(
                character_source_path
            ).convert("RGB")
            if character_sheet.size != (1935, 813):
                raise ValueError(
                    "Elwin Mage/Archmage AI source changed size: "
                    f"{character_sheet.size}"
                )
            for class_id, cell_index in character_ai_classes.items():
                cell_subject = direct_stage_subject(
                    character_sheet.crop(
                        ELWIN_CHARACTER_AI_BOUNDS[cell_index]
                    )
                )
                preview_source = cell_subject.copy()
                preview_source.thumbnail(
                    (512, 512),
                    RESAMPLING.NEAREST,
                )
                target = (
                    source_cell_dir
                    / f"{commander_id}-{class_id:02X}.png"
                )
                preview_source.save(target, optimize=True)
                character_16 = fit_subject_to_16(
                    cell_subject,
                    foreground_isolated=True,
                )
                key = (commander_id, class_id)
                converted, changed, lock_box, automatic_points = (
                    identity_locked_character_sprite(
                        character_16,
                        originals[class_id],
                        palette,
                        identity_mask_overrides.get(key),
                        additional_locked_points=mount_mask_overrides.get(key),
                    )
                )
                board_subjects[key] = preview_source
                converted_subjects[key] = converted
                source_cell_files[key] = str(
                    target.relative_to(output_dir)
                )
                native_changed_pixels[key] = changed
                native_lock_boxes[key] = lock_box
                native_automatic_mask_points[key] = automatic_points

    shared_template_labels: dict[tuple[int, int], str] = {}
    for key, (source_path, template_label) in (
        SHARED_CLASS_TEMPLATE_SOURCES.items()
    ):
        commander_id, class_id = key
        targeted_native_source_paths.append(source_path)
        generated_16 = Image.open(source_path).convert("RGBA")
        if generated_16.size != (16, 16):
            raise ValueError(
                f"shared class template must be 16x16: {source_path}"
            )
        tiers = class_tiers(source, commander_id)
        if class_id not in tiers:
            raise ValueError(
                f"commander {commander_id} does not have class "
                f"{class_id:02X}"
            )
        sprite_map = commander_sprite_map(source, commander_id)
        identity_source_class_id = TIER_MOUNT_CLASS_SOURCE_CLASSES.get(
            key,
            class_id,
        )
        original = render_sprite(
            source,
            sprite_map[identity_source_class_id],
            1,
        )
        converted, changed, lock_box, automatic_points = (
            identity_locked_character_sprite(
                generated_16,
                original,
                [ROM_INK],
                identity_mask_overrides.get(key),
                additional_locked_points=mount_mask_overrides.get(key),
                preserve_generated_palette=True,
                restore_transparent_locked_points=False,
            )
        )
        if key in EXACT_SHARED_TEMPLATE_SOURCE_KEYS:
            converted = generated_16.copy()
            visible_identity_points = (
                set(identity_mask_overrides.get(key, automatic_points))
                | protected_eye_points(original)
                | set(mount_mask_overrides.get(key, set()))
            )
            for point in visible_identity_points:
                if original.getpixel(point)[3]:
                    converted.putpixel(point, original.getpixel(point))
            visible_colors = {
                color for color in converted.getdata() if color[3]
            }
            if len(visible_colors) > 15:
                raise ValueError(
                    f"exact shared source exceeds 15 colors: {key}"
                )
            changed = sum(
                converted.getpixel((x, y))
                != original.getpixel((x, y))
                for y in range(16)
                for x in range(16)
            )
        if key not in TIER_MOUNT_CLASS_SOURCE_KEYS:
            require_full_16_canvas(
                converted,
                label=(
                    f"{KOREAN_NAME_BY_ID[commander_id]} "
                    f"shared class {class_id:02X}"
                ),
            )
        preview_source = generated_16.resize(
            (512, 512),
            RESAMPLING.NEAREST,
        )
        target = (
            source_cell_dir / f"{commander_id}-{class_id:02X}.png"
        )
        preview_source.save(target, optimize=True)
        board_subjects[key] = preview_source
        converted_subjects[key] = converted
        source_cell_files[key] = str(target.relative_to(output_dir))
        native_changed_pixels[key] = changed
        native_lock_boxes[key] = lock_box
        native_automatic_mask_points[key] = automatic_points
        shared_template_labels[key] = template_label

    # Jessica's stock Lord/Magic Knight/Bishop silhouettes are not shared AI
    # templates, but their red cloth must join her purple/lavender equipment
    # language.  Register editable ROM-native baselines before the normal row
    # composition so only their color role changes.
    for key in JESSICA_PURPLE_ROM_BASE_KEYS:
        if key in converted_subjects:
            continue
        commander_id, class_id = key
        sprite_map = commander_sprite_map(source, commander_id)
        original = render_sprite(source, sprite_map[class_id], 1)
        eye_points = protected_eye_points(original)
        detected_box = head_lock_box(original)
        lock_box = (
            detected_box[0],
            detected_box[1],
            detected_box[2],
            max(9, detected_box[3]),
        )
        automatic_points = box_points(lock_box) | eye_points
        preview_source = original.resize(
            (512, 512),
            RESAMPLING.NEAREST,
        )
        target = source_cell_dir / f"{commander_id}-{class_id:02X}.png"
        preview_source.save(target, optimize=True)
        board_subjects[key] = preview_source
        converted_subjects[key] = original.copy()
        source_cell_files[key] = str(target.relative_to(output_dir))
        native_changed_pixels[key] = 0
        native_lock_boxes[key] = lock_box
        native_automatic_mask_points[key] = automatic_points

    # Each physical commander chain stores only one terminal fifth-tier
    # transition, while the stock character tree and sprite table can expose
    # additional hidden destinations. Give every supplemental hidden class an
    # editable native 16x16 baseline even before a dedicated AI redesign is
    # accepted. This keeps the editor complete without changing ROM data.
    supplemental_hidden_keys: set[tuple[int, int]] = set()
    for commander_id in range(1, COMMANDER_COUNT + 1):
        sprite_map = commander_sprite_map(source, commander_id)
        for route in hidden_class_routes(commander_id):
            class_id = route.candidates[0]
            key = (commander_id, class_id)
            if key in converted_subjects:
                continue
            original = render_sprite(
                source,
                sprite_map[class_id],
                1,
            )
            eye_points = protected_eye_points(original)
            detected_box = head_lock_box(original)
            lock_box = (
                detected_box[0],
                detected_box[1],
                detected_box[2],
                max(9, detected_box[3]),
            )
            automatic_points = box_points(lock_box) | eye_points
            preview_source = original.resize(
                (512, 512),
                RESAMPLING.NEAREST,
            )
            target = (
                source_cell_dir
                / f"{commander_id}-{class_id:02X}.png"
            )
            preview_source.save(target, optimize=True)
            board_subjects[key] = preview_source
            converted_subjects[key] = original.copy()
            source_cell_files[key] = str(
                target.relative_to(output_dir)
            )
            native_changed_pixels[key] = 0
            native_lock_boxes[key] = lock_box
            native_automatic_mask_points[key] = automatic_points
            supplemental_hidden_keys.add(key)

    pending_redesign_count = 0
    for commander_id in range(1, COMMANDER_COUNT + 1):
        tiers = class_tiers(source, commander_id)
        sprite_map = commander_sprite_map(source, commander_id)
        by_sprite: dict[int, list[int]] = defaultdict(list)
        for class_id in tiers:
            by_sprite[sprite_map[class_id]].append(class_id)
        for class_ids in by_sprite.values():
            class_ids.sort(key=lambda value: (tiers[value], value))
        commander_dir = output_dir / str(commander_id)
        commander_dir.mkdir(parents=True, exist_ok=True)
        rows: dict[str, object] = {}
        for class_id, tier in sorted(tiers.items()):
            identity_source_class_id = TIER_MOUNT_CLASS_SOURCE_CLASSES.get(
                (commander_id, class_id),
                class_id,
            )
            rom_face = render_sprite(
                source,
                sprite_map[identity_source_class_id],
                1,
            )
            eye_points = protected_eye_points(rom_face)
            group = by_sprite[sprite_map[class_id]]
            group_rank = group.index(class_id)
            eligible_redesign = len(group) > 1 and group_rank > 0
            key = (commander_id, class_id)
            redesigned = key in converted_subjects
            pending_redesign = not redesigned and eligible_redesign
            if redesigned:
                # The source board was generated from the ROM character
                # reference. Keep its head/neck/body drawing coherent.
                # Pasting a rectangular ROM head over it erased shoulders,
                # weapon edges, wings, and mounts at this tiny resolution.
                image = converted_subjects[key].copy()
                face_pixel_count = 0
                source_image = board_subjects[key]
                source_cell_file = source_cell_files[key]
                if key in ROM_BASE_DESIGN_KEYS:
                    image = rom_face.copy()
                    source_image = rom_face.resize(
                        (512, 512),
                        RESAMPLING.NEAREST,
                    )
                    source_image.save(
                        output_dir / source_cell_file,
                        optimize=True,
                    )
                automatic_mask_points = (
                    native_automatic_mask_points[key]
                    if key in native_automatic_mask_points
                    else set(eye_points)
                )
                identity_lock_points = (
                    set(identity_mask_overrides[key]) | eye_points
                    if key in identity_mask_overrides
                    else automatic_mask_points
                )
                if key in JESSICA_PURPLE_EQUIPMENT_KEYS:
                    # Jessica's historical rectangular head masks include a
                    # few red cape/shoulder cells. Her hair/skin/eyes use no
                    # red ramp, so those cells are equipment, not identity.
                    red_equipment_points = {
                        point
                        for point in identity_lock_points
                        if rom_face.getpixel(point)
                        in JESSICA_PURPLE_COLOR_MAP
                    }
                    identity_lock_points -= red_equipment_points
                    automatic_mask_points -= red_equipment_points
                identity_lock_mode = (
                    "custom"
                    if key in identity_mask_overrides
                    else "automatic"
                )
                mount_lock_points = set(
                    mount_mask_overrides.get(key, set())
                )
                mount_lock_mode = (
                    "custom"
                    if key in mount_mask_overrides
                    else "none"
                )
                if key in ROM_BASE_DESIGN_KEYS:
                    source_kind = (
                        "원작 ROM 16×16 기반 클래스 색상 편집"
                    )
                    if key in TIER_MOUNT_CLASS_SOURCE_KEYS:
                        source_class_id = (
                            TIER_MOUNT_CLASS_SOURCE_CLASSES[key]
                        )
                        source_position = (
                            "latest/keith-lester-tier1-mounted-v1/"
                            f"logical16/{commander_id:02d}-{class_id:02X}.png"
                        )
                        feature = (
                            f"원작 {classes[source_class_id]['ko']}의 기수·"
                            "탈것·무기 16×16 좌표를 그대로 사용·1단은 "
                            "원작 탈것색 유지·2단 로드는 동일 좌표에서 "
                            "탈것색만 강한 계열로 변형·얼굴과 탈것 "
                            "마스크 모두 편집 가능·실제 ROM 미적용"
                        )
                    else:
                        source_position = (
                            "class-sprites/commanders/"
                            f"{commander_id}/{class_id:02X}-p1.png"
                        )
                    if (
                        key in MOUNT_COLOR_VARIANTS
                        and key not in TIER_MOUNT_CLASS_SOURCE_KEYS
                    ):
                        feature = (
                            "AI 생성 기마 실루엣 폐기·원작 ROM 기수·말 "
                            "16×16 픽셀 배치 완전 유지·사용자 공유 탈것 "
                            "마스크 안의 말 명암만 캐릭터·클래스별로 "
                            "변형·흰 검날·창날·갑옷·얼굴 유지·실제 ROM "
                            "미적용"
                        )
                    elif key not in TIER_MOUNT_CLASS_SOURCE_KEYS:
                        feature = (
                            "AI 생성 드래곤 실루엣 폐기·원작 ROM 기수·"
                            "드래곤 16×16 픽셀 배치 완전 유지·드래곤 "
                            "몸·날개 색상만 클래스별로 변형·흰 무기·"
                            "갑옷·얼굴 유지·실제 ROM 미적용"
                        )
                elif key in AI_NATIVE_LOGICAL_SOURCE_KEYS:
                    source_kind = (
                        "OpenAI 신규 헤인 소서러 전용 네이티브 "
                        "논리16 원화"
                    )
                    source_position = (
                        "latest/hein-sorcerer-v2/clean/"
                        "hein-09-sorcerer-ai.png + logical16/"
                        "hein-09-sorcerer-ai.png"
                    )
                    feature = (
                        "현재 헤인의 얼굴·눈·청색 머리 확대 원본과 "
                        "승인된 헤인 메이지 장비 문법을 레퍼런스로 "
                        "신규 AI 생성·생성 단계에서 헤인 얼굴·머리 "
                        "형태 유지·남청색 소서러 로브·목제 지팡이·"
                        "정확한 16×16 논리 격자·메가드라이브 15색·"
                        f"사용자 얼굴 마스크 {len(identity_lock_points)}"
                        "픽셀과 원본 눈 완전 복원·실제 ROM 미적용"
                    )
                elif (
                    key in JESSICA_FRESH_MAGIC_SOURCE_KEYS
                    and key not in shared_template_labels
                ):
                    class_label = {
                        0x26: "자베라",
                        0x28: "서머너",
                    }[class_id]
                    class_slug = {
                        0x26: "zarvera",
                        0x28: "summoner",
                    }[class_id]
                    source_kind = (
                        f"OpenAI 신규 제시카 {class_label} 전용 "
                        "네이티브 논리16 원화"
                    )
                    source_position = (
                        "latest/jessica-zarvera-summoner-ai-v1-fresh/"
                        f"selected-sources/10-{class_id:02X}-"
                        f"{class_slug}-ai.png + logical16/"
                        f"10-{class_id:02X}.png"
                    )
                    feature = (
                        "이전 AI 원화·공통 클래스 템플릿·기존 장비 "
                        "가이드를 생성 입력에서 제외·제시카 ROM 원본 "
                        "얼굴·청색 머리와 현재 73픽셀 마스크만 참조해 "
                        f"{class_label} 전용 원화를 새로 생성·선정 원화의 "
                        "큰 장비 군집과 실루엣을 네이티브 16×16으로 "
                        "재픽셀화·제시카 얼굴·머리·눈 73픽셀 원본 "
                        "복원·최종 합성에서 오른쪽 1칸 정렬·15색 이하·"
                        "빈 행·열과 몸통 투명 구멍 없음·실제 ROM 미적용"
                    )
                elif key in supplemental_hidden_keys:
                    source_kind = (
                        "원작 캐릭터 전용 히든 클래스 네이티브 "
                        "16×16 편집 기준"
                    )
                    source_position = (
                        f"{commander_id}번 지휘관 "
                        f"{classes[class_id]['ko']} 원작 전용 스프라이트"
                    )
                    feature = (
                        "ROM 전직 레코드의 대표 히든 경로 밖에 있던 "
                        "원작 복수 히든 클래스를 에디터에 복원·캐릭터 "
                        "전용 원작 16×16 스프라이트를 초기 디자인으로 "
                        "사용·원본 머리·얼굴·눈 잠금·사용자 디자인 "
                        "편집 가능·실제 ROM 미적용"
                    )
                elif key in shared_template_labels:
                    template_label = shared_template_labels[key]
                    template_root = (
                        "latest/liana-sage-sherry-wizard-palette-v1"
                        if key in LIANA_SAGE_SHERRY_WIZARD_PALETTE_SOURCE_KEYS
                        else "latest/shared-liana-lana-healer-v1"
                        if key in SHARED_LIANA_LANA_HEALER_SOURCE_KEYS
                        else "latest/shared-liana-summoner-agent-v1"
                        if key in SHARED_LIANA_SUMMONER_AGENT_SOURCE_KEYS
                        else "latest/shared-keith-wizard-new-classes-v1"
                        if key in SHARED_KEITH_WIZARD_NEW_CLASS_SOURCE_KEYS
                        else "latest/shared-high-priest-aaron-v1"
                        if key in SHARED_AARON_HIGH_PRIEST_SOURCE_KEYS
                        else "latest/lana-wizard-liana-template-v1"
                        if key in LIANA_TO_LANA_WIZARD_SOURCE_KEYS
                        else (
                            "latest/shared-sherry-scott-keith-lord-"
                            "aaron-lord-v1"
                        )
                        if key in SHERRY_SCOTT_KEITH_AARON_LORD_SOURCE_KEYS
                        else "latest/shared-scott-keith-lord-elwin-lord-v1"
                        if key in SCOTT_KEITH_ELWIN_LORD_SOURCE_KEYS
                        else "latest/shared-new-classes-v2-refined"
                        if key in SHARED_NEW_CLASS_SOURCE_KEYS
                        else "latest/shared-elwin-magic-v1"
                        if class_id in {0x13, 0x14}
                        else "latest/shared-wizard-hein-v1"
                        if class_id == 0x15
                        else (
                            "latest/shared-high-master-"
                            "elwin-swordmaster-v1"
                        )
                        if key in {(4, 0x23), (8, 0x23)}
                        else "latest/shared-saint-aaron-v1"
                        if class_id == 0x17
                        else "latest/sherry-ranger-v4"
                        if key == (4, 0x21)
                        else "latest/hein-warlock-sorcerer-v1"
                        if key == (5, 0x09)
                        else "latest/hein-magic-knight-paladin-v1"
                        if key == (5, 0x19)
                        else "latest/shared-lord-elwin-high-lord-v1"
                        if class_id == 0x04
                        else "latest/shared-high-lord-hein-v1"
                        if class_id == 0x0B
                        else "latest/shared-swordmaster-hein-v1"
                        if class_id == 0x1A
                        else "latest/shared-hein-classes-v1"
                    )
                    source_kind = (
                        f"{template_label} 공통 16×16 클래스 템플릿"
                    )
                    source_position = (
                        f"{template_root}/logical16/"
                        f"{commander_id:02d}-{class_id:02X}.png"
                    )
                    feature = (
                        f"{template_label}의 장비·무기·실루엣 좌표를 "
                        "동일 클래스 공통 기준으로 유지·캐릭터별 "
                        "고유 주색·보조색으로만 재배색·현재 원작 "
                        "머리·얼굴·눈의 보이는 픽셀 유지·머리 마스크의 "
                        "투명 좌표에서는 방패·견갑·무기 디자인 우선·"
                        "원본 클래스 팔레트 기반 재배색·"
                        "16개 행·열 모두 사용·"
                        "메가드라이브 4bpp·"
                        f"변경 {native_changed_pixels[key]}픽셀"
                    )
                    if key in {(10, 0x13), (10, 0x14)}:
                        feature += (
                            "·제시카 하이로드에서 다시 저장한 얼굴 마스크 "
                            "공유·머리·얼굴 오른쪽 1칸 정렬·자주색 망토·"
                            "남보라 안감·은보라 로브·연보라 테두리로 "
                            "장비 면 분리"
                        )
                    elif key == (8, 0x04):
                        feature += (
                            "·사용자가 정리한 머리 앞 검날 유지·"
                            "엘윈 로드형 파랑·하늘색 격자 방패"
                        )
                    elif key in {(5, 0x13), (5, 0x14)}:
                        feature += (
                            "·헤인 공통 짙은 초록·중간 연두·백색 명암"
                        )
                    elif key == (5, 0x09):
                        feature += (
                            "·AI 실루엣 미사용·워록 ROM 원본 좌표·"
                            "연두색 망토"
                        )
                    elif key == (5, 0x19):
                        feature += (
                            "·AI 실루엣 미사용·매직나이트 ROM 원본 "
                            "기마 좌표·초록 장비·마갑"
                        )
                elif commander_id in native_specs:
                    native_spec = native_specs[commander_id]
                    if commander_id == 1 and class_id == 0x04:
                        source_kind = (
                            "OpenAI 신규 엘윈 보병 로드 엄격 논리16 원화"
                        )
                        source_position = (
                            "latest/elwin-lord-v2/04-lord.png"
                        )
                        feature = (
                            "원작 전체와 현재 69픽셀 얼굴 마스크만 "
                            "정체성 기준으로 사용해 신규 생성·말과 탈것 "
                            "없는 보병 로드·담청·왕청 갑옷·금장 견갑·"
                            "진홍 망토·한손검·청금색 소형 방패·16개 "
                            "행·열 전부 사용·보라색 배경 오염과 완전 "
                            "검정 제거·메가드라이브 4bpp·원본 머리·"
                            f"얼굴·눈 {len(identity_lock_points)}픽셀 "
                            "완전 잠금·"
                            f"변경 {native_changed_pixels[key]}픽셀"
                        )
                    elif commander_id == 1 and class_id == 0x22:
                        source_kind = (
                            "샘플 클래스 선정 엘윈 킹 기반 보라색 히어로"
                        )
                        source_position = (
                            "latest/sample-class-variants-v4-free-five/"
                            "01-elwin-22-hero/ai/04.png + "
                            "editor/ai_class_design_overrides.json · 1:22"
                        )
                        feature = (
                            "사용자가 샘플 클래스 4번에서 승인한 엘윈 킹 "
                            "형태의 보라·연보라 히어로 장비색 전체 적용·"
                            "붉은 머리·얼굴·눈은 원본 그대로 유지·머리 "
                            "왼쪽 흰·회색 장식 6픽셀만 보라·연보라로 변경·"
                            "흰 검날·은색 갑옷 경계·어두운 목과 몸통 경계 "
                            "유지·보병·16×16·메가드라이브 15색 이하·"
                            f"변경 {native_changed_pixels[key]}픽셀"
                        )
                    elif (
                        commander_id == 1
                        and class_id in {0x0C, 0x1D}
                    ):
                        mounted_label = (
                            "하이랜더"
                            if class_id == 0x0C
                            else "실버나이트"
                        )
                        source_kind = (
                            f"OpenAI 신규 엘윈 {mounted_label} "
                            "얼굴·탈것 이중 잠금 논리16 원화"
                        )
                        source_position = (
                            "latest/elwin-mounted-v2/"
                            f"{ELWIN_NATIVE_SOURCE_FILES[class_id]}"
                        )
                        feature = (
                            "이전 AI 원화를 사용하지 않고 원작 전체·"
                            "현재 얼굴 마스크·현재 탈것 마스크만 "
                            "기준으로 신규 생성·AI 장비·무기 디자인을 "
                            "논리 16×16로 격자 스냅·원본 머리·얼굴·눈 "
                            f"{len(identity_lock_points)}픽셀과 원본 "
                            f"탈것 {len(mount_lock_points)}픽셀 완전 "
                            "잠금·16개 행·열 전부 사용·보라색 배경 "
                            "오염과 완전 검정 제거·메가드라이브 4bpp·"
                            f"{native_spec['features'][class_id]}·"
                            f"변경 {native_changed_pixels[key]}픽셀"
                        )
                    elif (
                        commander_id == 1
                        and class_id in ELWIN_DIRECT_STAGE_CLASSES
                    ):
                        direct_stage = ELWIN_DIRECT_STAGE_CLASSES[class_id]
                        source_kind = (
                            "direct_16x16 엘윈 5단계 AI 디자인"
                        )
                        source_position = (
                            "direct_16x16_01_elwin.png · "
                            f"{direct_stage}단계 · "
                            f"{classes[class_id]['ko']}"
                        )
                        feature = (
                            "선택된 5단계 원화의 갑옷·방패·무기·망토·"
                            "보병 실루엣 유지·원본 엘윈 얼굴·머리·눈 "
                            "사각형 픽셀 완전 잠금·메가드라이브 원본 "
                            f"팔레트·{native_spec['features'][class_id]}·"
                            f"변경 {native_changed_pixels[key]}픽셀"
                        )
                    elif (
                        commander_id == 1
                        and class_id in ELWIN_CHARACTER_AI_CLASSES
                    ):
                        source_kind = (
                            "character-ai-v3 엘윈 마법사 전용 AI 디자인"
                        )
                        source_position = (
                            f"{character_source_path.name} · "
                            f"{ELWIN_CHARACTER_AI_CLASSES[class_id]}번 셀 · "
                            f"{classes[class_id]['ko']}"
                        )
                        feature = (
                            "direct 5단계와 같은 메가드라이브 픽셀 문법·"
                            "마법사 로브·지팡이·보병 실루엣 유지·원본 "
                            "엘윈 얼굴·머리·눈 사용자 편집 마스크·원본 "
                            f"팔레트·{native_spec['features'][class_id]}·"
                            f"변경 {native_changed_pixels[key]}픽셀"
                        )
                    elif commander_id == 4:
                        source_kind = (
                            "OpenAI 신규 쉐리 전 클래스 메가드라이브 "
                            "논리16 원화"
                        )
                        source_position = (
                            "latest/sherry-v2/"
                            f"{SHERRY_NATIVE_SOURCE_FILES[class_id]}"
                        )
                        feature = (
                            "이전 쉐리 AI를 입력하지 않고 원작 전체와 "
                            "현재 사용자 마스크만 참조해 클래스별 별도 "
                            "생성·생성 장비 원화의 얼굴 논리셀을 변환 전에 "
                            "원본으로 완전 고정·큰 얼굴·눈·흰자·턱선 길이 "
                            "은발 단발 유지·16개 행·열 모두 사용·보라색 "
                            "키와 검정 배경 제거·메가드라이브 4bpp·"
                            f"{native_spec['features'][class_id]}·"
                            f"변경 {native_changed_pixels[key]}픽셀"
                        )
                    else:
                        source_kind = (
                            "기존 AI 장비·실루엣과 새 사용자 마스크를 "
                            "재결합한 메가드라이브 16×16 상위 클래스"
                            if native_spec.get("reconstruction")
                            else
                            "OpenAI 원본 보존형 메가드라이브 16×16 "
                            "상위 클래스 원화"
                        )
                        source_position = (
                            f"{KOREAN_NAME_BY_ID[commander_id]} "
                            f"{classes[class_id]['ko']} · "
                            "공유 스프라이트 상위 클래스 편집"
                        )
                        feature = (
                            (
                                "새 사용자 마스크의 원본 얼굴·머리·눈 "
                                f"{len(identity_lock_points)}픽셀 완전 "
                                "잠금·기존 AI 장비·무기·실루엣 재사용·"
                            )
                            if native_spec.get("reconstruction")
                            else (
                                "사용자 마스크의 원본 얼굴·머리·눈 픽셀 "
                                f"{len(identity_lock_points)}개 완전 잠금·"
                                "원작과 같은 실제 머리 5~6논리픽셀·전체 "
                                "15~16논리픽셀 비율로 재생성한 AI 갑옷·"
                                "무기·클래스별 탈것 실루엣 유지·"
                            )
                        ) + (
                            "메가드라이브 원본 팔레트·원본 눈·흰자 "
                            f"{len(eye_points)}픽셀 잠금·"
                            f"{native_spec['features'][class_id]}·"
                            f"변경 {native_changed_pixels[key]}픽셀"
                        )
                else:
                    if (
                        commander_id in {2, 3}
                        and class_id
                        in LIANA_LANA_PAIRED_SOURCE_FILES
                    ):
                        paired_color = (
                            "적색"
                            if commander_id == 2
                            else "청색"
                        )
                        paired_dir = (
                            "native16-red"
                            if commander_id == 2
                            else "native16-blue"
                        )
                        source_kind = (
                            "OpenAI 엄격 16칸 고정 머리 리아나·라나 "
                            "동일 실루엣 "
                            f"{paired_color} 대비 네이티브 16×16 원화"
                        )
                        source_position = (
                            "latest/liana-lana-strict16-v1/"
                            f"{paired_dir}/"
                            f"{LIANA_LANA_PAIRED_SOURCE_FILES[class_id]}"
                        )
                        feature = (
                            "1254px 캔버스를 정확히 16개 행·열로 제한한 "
                            "AI 원화 후보를 반복 생성·리아나 세이지에서 "
                            "다시 저장한 얼굴 82픽셀 마스크를 리아나·라나 "
                            "모든 클래스에 공통 적용·피사체 "
                            "크롭이나 가로세로 강제 확대 없이 16칸 전체 "
                            "캔버스를 같은 좌표로 직접 16×16화·리아나 "
                            "적색과 좌표가 같은 라나 청색 짝 디자인·이미지 "
                            "기준 오른쪽 끝에 왼손 주무기 배치·16개 행·열 "
                            "모두 사용·보라색 키·검정 배경 제거·"
                            "메가드라이브 4bpp·원본 머리·얼굴·눈 "
                            f"{len(identity_lock_points)}픽셀 완전 잠금·"
                            f"{LIANA_LANA_PAIRED_EQUIPMENT_FEATURES[class_id]}"
                        )
                    elif (
                        commander_id == 5
                        and class_id
                        in HEIN_LATEST_SOURCE_FILES
                    ):
                        source_kind = (
                            "OpenAI 헤인 11종 신규 전폭 논리16 원화"
                        )
                        source_position = (
                            "latest/hein/raw/"
                            f"{HEIN_LATEST_SOURCE_FILES[class_id]}"
                        )
                        feature = (
                            "이전 AI를 사용하지 않고 원작·사용자 마스크만 "
                            "레퍼런스로 네이티브 논리16에서 신규 생성·"
                            "16개 행·열을 모두 실제 머리·옷·갑옷·망토·"
                            "무기로 채운 전폭 실루엣·메가드라이브 4bpp·"
                            f"사용자 편집 머리·얼굴 마스크 "
                            f"{len(identity_lock_points)}픽셀 완전 잠금"
                        )
                    else:
                        spec = BOARD_SPECS[commander_id]
                        cell_index = list(
                            spec["class_ids"]
                        ).index(class_id)
                        source_kind = (
                            "logical16-v3 원작·사용자 마스크 직접 편집 "
                            "AI 시트"
                        )
                        source_position = (
                            f"{spec['file']} · "
                            f"{cell_index + 1}번 클래스 셀"
                        )
                        feature = (
                            "원본 4×4 논리16 좌표 위에서 생성한 단순한 "
                            "메가드라이브급 AI 픽셀 원화·셀 경계를 넘은 "
                            "연결 장비까지 완전 복원 후 16×16 최근접 "
                            "축소·클래스별 장비·탈것 실루엣·원본 "
                            "머리색을 먼저 예약하고 남은 4bpp 색 슬롯에 "
                            "메가드라이브 채널값으로 보정한 AI 장비색 "
                            f"유지·사용자 편집 머리·얼굴 마스크 "
                            f"{len(identity_lock_points)}픽셀 완전 잠금"
                        )
                redesigned_count += 1
            else:
                image = rom_face
                face_pixel_count = 0
                automatic_mask_points = set()
                identity_lock_points = set()
                identity_lock_mode = "none"
                mount_lock_points = set()
                mount_lock_mode = "none"
                source_image = rom_face
                source_cell_file = None
                source_kind = "중복 묶음 기준 ROM 원본"
                source_position = (
                    f"{commander_id}번 지휘관 · AI 미적용"
                )
                feature = (
                    "상위 중복 클래스 디자인 생성 대기·ROM 원본 유지"
                    if pending_redesign
                    else "공유 묶음의 기본 클래스 또는 단독 클래스·"
                    "ROM 원본 유지"
                )
                pending_redesign_count += int(pending_redesign)
            stored_design_override = (
                design_overrides.get(key)
                if redesigned
                else None
            )
            design_override_superseded = (
                stored_design_override is not None
                and key
                in SHARED_TEMPLATE_SUPERSEDES_DESIGN_OVERRIDES
                and int(stored_design_override["revision"])
                <= SHARED_TEMPLATE_SUPERSEDED_DESIGN_REVISION_MAX.get(key, -1)
            )
            design_override = (
                None
                if design_override_superseded
                else stored_design_override
            )
            if redesigned:
                if (
                    key not in native_lock_boxes
                    and key not in AI_NATIVE_LOGICAL_SOURCE_KEYS
                ):
                    reserved_eye_colors = {
                        rom_face.getpixel(point)
                        for point in eye_points
                    }
                    image = quantize_16_color_rgba(
                        image,
                        visible_colors=max(
                            1,
                            15 - len(reserved_eye_colors),
                        ),
                    )
                lock_restore_points = (
                    identity_lock_points | mount_lock_points
                )
                identity_lock_transparency_mode = "exact"
                if key in shared_template_labels:
                    if key in FULL_SPRITE_SHARED_TEMPLATE_SOURCE_KEYS:
                        lock_restore_points = set()
                        identity_lock_transparency_mode = (
                            "approved_full_sprite_template"
                        )
                    else:
                        lock_restore_points = {
                            point
                            for point in lock_restore_points
                            if rom_face.getpixel(point)[3]
                        }
                        identity_lock_transparency_mode = (
                            "equipment_priority"
                        )
                for point in lock_restore_points:
                    image.putpixel(point, rom_face.getpixel(point))
                if design_override is not None:
                    override_image = Image.new(
                        "RGBA",
                        (16, 16),
                        TRANSPARENT,
                    )
                    override_image.putdata(
                        design_override["pixels"]
                    )
                    image = override_image
                    for point in lock_restore_points:
                        image.putpixel(point, rom_face.getpixel(point))
                    identity_source_offset = (
                        IDENTITY_OVERRIDE_SOURCE_OFFSETS.get(key)
                    )
                    if identity_source_offset is not None:
                        source_dx, source_dy = identity_source_offset
                        for x, y in lock_restore_points:
                            source_point = (
                                x + source_dx,
                                y + source_dy,
                            )
                            if (
                                0 <= source_point[0] < 16
                                and 0 <= source_point[1] < 16
                            ):
                                image.putpixel(
                                    (x, y),
                                    rom_face.getpixel(source_point),
                                )
                    feature += "·사용자 16×16 디자인 편집 적용"
                elif design_override_superseded:
                    feature += (
                        "·기존 사용자 16×16 디자인 편집 이력 보존·"
                        "새 공통 클래스 배치 우선"
                    )
            else:
                identity_lock_transparency_mode = "none"
            identity_translation = (
                IDENTITY_PIXEL_TRANSLATIONS.get(key)
                if redesigned
                else None
            )
            identity_translation_applied_in_override = (
                identity_translation is not None
                and design_override is not None
            )
            manifest_eye_points = set(eye_points)
            manifest_identity_lock_points = set(identity_lock_points)
            if (
                identity_translation is not None
                and not identity_translation_applied_in_override
            ):
                dx, dy = identity_translation
                visible_identity_points = {
                    point
                    for point in identity_lock_points
                    if rom_face.getpixel(point)[3]
                }
                image = translate_selected_pixels(
                    image,
                    visible_identity_points,
                    dx,
                    dy,
                )
                manifest_eye_points = translate_points(
                    set(eye_points),
                    dx,
                    dy,
                )
                manifest_identity_lock_points = translate_points(
                    set(identity_lock_points),
                    dx,
                    dy,
                )
                feature += (
                    f"·머리·얼굴 픽셀을 장비 기준 "
                    f"오른쪽 {dx}칸 이동"
                )
            elif identity_translation_applied_in_override:
                dx, dy = identity_translation
                manifest_eye_points = translate_points(
                    set(eye_points),
                    dx,
                    dy,
                )
                feature += (
                    "·머리·얼굴은 오른쪽 1칸 목적지 마스크에 "
                    "ROM 왼쪽 원본 픽셀을 대응해 고정"
                )
            rom_color_variant = ROM_RECOLOR_VARIANTS.get(key)
            if rom_color_variant is not None:
                for y in range(16):
                    for x in range(16):
                        point = (x, y)
                        if point in manifest_identity_lock_points:
                            continue
                        color = image.getpixel(point)
                        if color in rom_color_variant:
                            image.putpixel(point, rom_color_variant[color])
                feature += (
                    "·제시카의 붉은 장비 면만 자주·보라·연보라 "
                    "명암으로 변형·은색·금색·피부·머리 유지"
                    if key in JESSICA_PURPLE_EQUIPMENT_KEYS
                    else "·원작 소서러 실루엣에서 붉은 로브만 "
                    "제시카 자주·연보라 계열로 변형"
                    if key == (10, 0x09)
                    else "·원작 드래곤 색상 역할만 변형"
                )
            if key == (10, 0x0B):
                for point in JESSICA_HIGH_LORD_CAPE_POINTS:
                    color = image.getpixel(point)
                    if color in JESSICA_HIGH_LORD_BLUE_CAPE_TO_PURPLE:
                        image.putpixel(
                            point,
                            JESSICA_HIGH_LORD_BLUE_CAPE_TO_PURPLE[color],
                        )
                for y in range(16):
                    for x in range(16):
                        point = (x, y)
                        if point in manifest_identity_lock_points:
                            continue
                        color = image.getpixel(point)
                        if color in JESSICA_HIGH_LORD_PALETTE_FOLD:
                            image.putpixel(
                                point,
                                JESSICA_HIGH_LORD_PALETTE_FOLD[color],
                            )
                feature += "·하늘색 망토를 자주·보라·연보라로 변경"
            mount_color_variant = MOUNT_COLOR_VARIANTS.get(key)
            if mount_color_variant is not None:
                for point in (
                    mount_lock_points - manifest_identity_lock_points
                ):
                    color = image.getpixel(point)
                    if color in mount_color_variant:
                        image.putpixel(point, mount_color_variant[color])
                feature += (
                    "·공유 탈것 마스크 안의 회색 명암만 캐릭터별 "
                    "색으로 변형·흰 검날·흰 하이라이트 유지"
                )
            for point, color in FINAL_PIXEL_OVERRIDES.get(
                key,
                {},
            ).items():
                image.putpixel(point, color)
            if key in FINAL_PIXEL_OVERRIDES:
                feature += (
                    "·선정 샘플의 보라·연보라 머리 장식 최종 복원"
                    if key == (1, 0x22)
                    else "·사용자 망토를 원작형 진홍색으로 보정"
                )
            dark_boundary_points: set[tuple[int, int]] = set()
            if redesigned and commander_id != 1:
                protected_boundary_points = (
                    manifest_identity_lock_points | mount_lock_points
                )
                for point in SHARED_DARK_BOUNDARY_REFERENCE_POINTS.get(
                    class_id,
                    set(),
                ):
                    if (
                        point not in protected_boundary_points
                        and not image.getpixel(point)[3]
                    ):
                        image.putpixel(point, ROM_INK)
                        dark_boundary_points.add(point)
            if dark_boundary_points:
                feature += (
                    "·맵 배경 누수 방지용 원작형 짙은 경계 "
                    f"{len(dark_boundary_points)}픽셀"
                )
            if key in JESSICA_FRESH_MAGIC_SOURCE_KEYS:
                # Moving Jessica's irregular 73-pixel hair mask one cell to
                # the right exposes a single source-space notch at the neck.
                # It is equipment, not identity, so close it only after the
                # translated face is final to prevent map-background leakage.
                seam_point = (6, 8)
                if not image.getpixel(seam_point)[3]:
                    image.putpixel(seam_point, ROM_INK)
                    feature += "·얼굴 이동 뒤 목 경계 투명 1픽셀 폐쇄"
            closed_transparent_points: set[tuple[int, int]] = set()
            if redesigned:
                closed_transparent_points = close_internal_transparency(image)
            approved_final_pixels = USER_APPROVED_FINAL_PIXEL_OVERRIDES.get(
                key,
                {},
            )
            for point, color in approved_final_pixels.items():
                image.putpixel(point, color)
            closed_transparent_points.difference_update(
                point
                for point, color in approved_final_pixels.items()
                if not color[3]
            )
            if approved_final_pixels:
                feature += (
                    "·사용자 승인 최종 픽셀 "
                    f"{len(approved_final_pixels)}개 유지"
                )
            if closed_transparent_points:
                feature += (
                    "·외곽 배경과 분리된 머리·목·팔·몸통 내부 투명 "
                    f"{len(closed_transparent_points)}픽셀을 원작형 "
                    "짙은 먹색으로 폐쇄"
                )
            changed_pixel_count = sum(
                image.getpixel((x, y)) != rom_face.getpixel((x, y))
                for y in range(16)
                for x in range(16)
            )
            target = commander_dir / f"{class_id:02X}.png"
            image.save(target, optimize=True)
            hidden_source_class = next(
                (
                    route.current_class
                    for route in hidden_class_routes(commander_id)
                    if route.candidates[0] == class_id
                ),
                None,
            )
            rows[str(class_id)] = {
                "class_id": class_id,
                "class_name": TIER_MOUNT_CLASS_DISPLAY_NAMES.get(
                    key,
                    classes[class_id]["ko"],
                ),
                "tier": tier,
                "ai_sheet_row": commander_id,
                "ai_sheet_stage": tier,
                "ai_source_cell_file": source_cell_file,
                "ai_source_original_file": (
                    source_original_files.get(key)
                ),
                "ai_source_kind": source_kind,
                "ai_source_position": source_position,
                "source_palette": dominant_colors(
                    source_image
                ),
                "pixel_palette": dominant_colors(image),
                "face_source_sprite_id": sprite_map[
                    identity_source_class_id
                ],
                "face_pixel_count": face_pixel_count,
                "eye_lock_points": [
                    list(point)
                    for point in sorted(manifest_eye_points)
                ],
                "eye_lock_pixel_count": len(manifest_eye_points),
                "identity_lock_default_points": [
                    list(point)
                    for point in sorted(automatic_mask_points)
                ],
                "identity_lock_points": [
                    list(point)
                    for point in sorted(
                        manifest_identity_lock_points
                    )
                ],
                "identity_lock_pixel_count": len(
                    manifest_identity_lock_points
                ),
                "identity_lock_mode": identity_lock_mode,
                "identity_lock_transparency_mode": (
                    identity_lock_transparency_mode
                ),
                "identity_mask_pending_rebuild": False,
                "identity_mask_superseded": False,
                "identity_translation": (
                    list(identity_translation)
                    if identity_translation is not None
                    else None
                ),
                "identity_translation_applied_in_override": (
                    identity_translation_applied_in_override
                ),
                "mount_lock_points": [
                    list(point)
                    for point in sorted(mount_lock_points)
                ],
                "mount_lock_pixel_count": len(mount_lock_points),
                "mount_lock_mode": mount_lock_mode,
                "mount_mask_pending_rebuild": False,
                "design_override": design_override is not None,
                "design_revision": (
                    int(design_override["revision"])
                    if design_override is not None
                    else 0
                ),
                "design_override_superseded": (
                    design_override_superseded
                ),
                "superseded_design_revision": (
                    int(stored_design_override["revision"])
                    if design_override_superseded
                    else 0
                ),
                "duplicate_group": group,
                "group_rank": group_rank,
                "redesigned": redesigned,
                "ai_generated": (
                    key != (4, 0x27)
                    and key not in TIER_MOUNT_CLASS_SOURCE_KEYS
                ),
                "pending_redesign": pending_redesign,
                "hidden_class": hidden_source_class is not None,
                "hidden_source_class": hidden_source_class,
                "supplemental_hidden_baseline": (
                    key in supplemental_hidden_keys
                ),
                "identity_lock_box": (
                    list(native_lock_boxes[key])
                    if key in native_lock_boxes and redesigned
                    else None
                ),
                "changed_pixel_count": (
                    changed_pixel_count
                ),
                "feature": feature,
                "file": str(target.relative_to(output_dir)),
            }
            asset_count += 1
        commanders[str(commander_id)] = {
            "name": KOREAN_NAME_BY_ID[commander_id],
            "classes": rows,
        }

    manifest = {
        "asset_version": ASSET_VERSION,
        "generated_from": str(rom_path.relative_to(ROOT)),
        "ai_source_sheets": [
            str(path.relative_to(ROOT))
            for path in board_paths
        ],
        "ai_source_images": [
            str(path.relative_to(ROOT))
            for path in dict.fromkeys(
                native_source_paths
                + targeted_native_source_paths
                + list(AI_SOURCE_ORIGINAL_FILES.values())
            )
        ],
        "commander_count": len(commanders),
        "asset_count": asset_count,
        "redesigned_count": redesigned_count,
        "pending_redesign_count": pending_redesign_count,
        "pipeline": (
            "original ROM reference board + current editable identity and "
            "mount masks -> per-commander logical16-v3 AI sheet drawn directly on "
            "a 4x4 grid of native 16x16 coordinates (Elwin keeps its accepted "
            "v16 sources; Liana/Lana use selected strict 16-cell AI sources "
            "with the shared 82-pixel Liana Sage face mask already locked "
            "before whole-canvas native16 sampling, with no subject crop or "
            "anisotropic resize; Sherry uses eleven new class-specific AI "
            "sources with each current short-bob face mask locked before "
            "whole-canvas native16 sampling; Lester's user-edited Archmage "
            "Elwin's latest user-retouched Mage/Archmage and Hein's approved "
            "Priest/High Priest are shared as same-class silhouettes with "
            "commander-specific recolors; Hein Sorcerer and Paladin use the "
            "stock Warlock and Magic Knight ROM silhouettes with restrained "
            "green class recolors and current identity masks restored; "
            "explicit source originals are copied for editor "
            "comparison) -> connected "
            "full-sprite recovery across nominal cell borders -> nearest "
            "16x16 sample -> adaptive 15-color 4bpp "
            "palette that reserves exact original identity colors and keeps "
            "generated equipment hues at Mega Drive channel levels -> every "
            "editable original head/face, protected eye, and selected mount "
            "pixels restored; every stock fifth-tier route, including the "
            "supplemental multi-hidden routes absent from the ten writable "
            "chain records, is shown with an editable character-specific "
            "native 16x16 baseline; base classes stay byte-exact"
        ),
        "rom_effect": "none; preview PNG assets only",
        "commanders": commanders,
    }
    from tools.build_character_ai_comparison_sheets import (
        write_character_comparison_sheets,
    )

    manifest["character_comparison_images"] = (
        write_character_comparison_sheets(
            manifest,
            output_dir,
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def build_assets(
    rom_path: Path,
    board_dir: Path,
    output_dir: Path,
    elwin_source_dir: Path = ELWIN_NATIVE_SOURCE_DIR,
) -> dict[str, object]:
    """Build in a staging directory, then publish the manifest last.

    The editor can rebuild after a mask save while a developer also runs this
    script.  A process-wide file lock serializes those builds.  Publishing all
    PNGs before atomically replacing the manifest keeps the browser on a
    complete old or complete new asset set instead of exposing the builder's
    temporary empty output directory.
    """

    output_dir = output_dir.resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with AI_ASSET_BUILD_LOCK_PATH.open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        staging_dir = Path(
            tempfile.mkdtemp(
                prefix=".ai-class-sprites-build-",
                dir=output_dir.parent,
            )
        )
        try:
            manifest = _build_assets_unlocked(
                rom_path,
                board_dir,
                staging_dir,
                elwin_source_dir,
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            for source in sorted(staging_dir.iterdir()):
                if source.name == "manifest.json":
                    continue
                target = output_dir / source.name
                if source.is_dir():
                    shutil.copytree(
                        source,
                        target,
                        dirs_exist_ok=True,
                    )
                else:
                    shutil.copy2(source, target)
            (staging_dir / "manifest.json").replace(
                output_dir / "manifest.json"
            )
            return manifest
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build AI-derived allied class-change sprite previews"
    )
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument(
        "--boards",
        type=Path,
        default=DEFAULT_BOARD_DIR,
        help="directory containing the per-commander generated class boards",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_assets(
        args.rom,
        args.boards,
        args.output,
    )
    print(
        f"{args.output}: {manifest['commander_count']} commanders, "
        f"{manifest['asset_count']} AI-derived class sprites"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
