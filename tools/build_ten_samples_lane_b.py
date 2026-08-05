#!/usr/bin/env python3
"""Prepare and validate Lane B's independent ten-sample class campaigns.

Generation is deliberately external to this deterministic builder: each
candidate is produced by one built-in imagegen call using only the current
commander/class sprite and this builder's identity-only reference.  Once the
accepted call output is copied to ``raw-ai/NN.png`` and chroma-keyed into
``ai/NN.png``, this script repixels it to native logical 16x16, restores the
current identity mask byte-exactly, and writes previews/contact/validation.

Nothing in this file updates the shared editor UI, manifest, or production
aggregate.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (
    ROM_INK,
    load_identity_mask_overrides,
    mega_drive_palette_color,
    protected_eye_points,
)
from tools.build_liana_lana_native16_assets import limit_visible_palette


OUTPUT_ROOT = (
    ROOT
    / "docs/assets/ai-class-source/latest/sample-class-variants-v2-ten"
)
EDITOR_SPRITES = ROOT / "editor/static/class-sprites/commanders"
CURRENT_SPRITES = ROOT / "editor/static/ai-class-sprites"
RESOLVED_MASKS = (
    ROOT
    / "docs/assets/ai-class-source/latest/shared-new-classes-v2-refined/identity-masks.json"
)
TRANSPARENT = (0, 0, 0, 0)
REFERENCE_BACKDROP = (232, 232, 232, 255)
BOARD_BACKDROP = (210, 210, 210, 255)
RESAMPLING = getattr(Image, "Resampling", Image)


GROUPS: tuple[dict[str, object], ...] = (
    {"key": "03-lana-08-healer", "commander": 3, "character": "Lana", "class_id": 0x08, "class_name": "Healer", "slug": "healer"},
    {"key": "03-lana-15-wizard", "commander": 3, "character": "Lana", "class_id": 0x15, "class_name": "Wizard", "slug": "wizard"},
    {"key": "03-lana-16-high-priest", "commander": 3, "character": "Lana", "class_id": 0x16, "class_name": "High Priest", "slug": "high-priest"},
    {"key": "03-lana-18-sage", "commander": 3, "character": "Lana", "class_id": 0x18, "class_name": "Sage", "slug": "sage"},
    {"key": "03-lana-25-agent", "commander": 3, "character": "Lana", "class_id": 0x25, "class_name": "Agent", "slug": "agent"},
    {"key": "03-lana-26-zarvera", "commander": 3, "character": "Lana", "class_id": 0x26, "class_name": "Zarvera", "slug": "zarvera"},
    {"key": "03-lana-28-summoner", "commander": 3, "character": "Lana", "class_id": 0x28, "class_name": "Summoner", "slug": "summoner"},
    {"key": "09-lester-15-wizard", "commander": 9, "character": "Lester", "class_id": 0x15, "class_name": "Wizard", "slug": "wizard"},
    {"key": "09-lester-26-zarvera", "commander": 9, "character": "Lester", "class_id": 0x26, "class_name": "Zarvera", "slug": "zarvera"},
    {"key": "04-sherry-15-wizard", "commander": 4, "character": "Sherry", "class_id": 0x15, "class_name": "Wizard", "slug": "wizard"},
    {"key": "06-scott-18-sage", "commander": 6, "character": "Scott", "class_id": 0x18, "class_name": "Sage", "slug": "sage"},
)
GROUP_BY_KEY = {str(group["key"]): group for group in GROUPS}


CHARACTER_DIRECTIONS = {
    "Lana": (
        "Keep Lana's long hair mass, exact reference hair colors and calm face dominant. Build a cool "
        "blue, icy-cyan, white and silver costume with restrained gold accents; "
        "the equipment must be newly composed for Lana, not a recolor of another commander."
    ),
    "Lester": (
        "Keep Lester's compact original head, face and hair placement. Use a "
        "character-specific violet, indigo, pale-silver and warm-gold equipment "
        "language with a sturdy adventurer silhouette; do not borrow another Wizard or Zarvera body."
    ),
    "Sherry": (
        "Keep Sherry's unmistakable short bob, wide paired eyes and compact face. "
        "Use a newly designed teal, cyan, white and silver costume with small gold "
        "accents; never lengthen her hair and never reuse another commander's Wizard silhouette."
    ),
    "Scott": (
        "Keep Scott's original face, hair shape and eye pixels. Create a distinct "
        "scholarly-warrior Sage in sky blue, navy, silver and white with restrained "
        "gold; it must not be a recolor or silhouette copy of any other Sage."
    ),
}


CLASS_DIRECTIONS = {
    "Healer": "A readable healing staff and protective closed robe; gentle but battle-ready, no detached spell effects.",
    "Wizard": "A strong arcane staff or wand and a high-rank mage mantle; more capable than a basic Mage, with a solid closed torso.",
    "High Priest": "A ceremonial crozier or gem staff, layered sacred tabard and broad mantle; visibly stronger than a basic Priest.",
    "Sage": "An ancient staff plus one connected scholarly cue such as a bound book, scroll case or rune tabard; wise and high-ranking.",
    "Agent": "A covert battle-caster silhouette with a short staff, blade or hooked sceptre, fitted mantle and readable hands; no modern firearms.",
    "Zarvera": "A javelin or spear specialist with a complete readable pole weapon, protective mantle and compact armor; one connected standing figure.",
    "Summoner": "A summoning staff and layered closed ritual robe; imply command through the staff and costume only, with no detached creature or floating effect.",
}


SILHOUETTES: tuple[str, ...] = (
    "Tall vertical weapon on image-right, broad asymmetric cape on image-left, one free hand clearly visible.",
    "Complete diagonal weapon running from lower image-left to upper image-right, short split mantle and wide grounded feet.",
    "Centered two-handed staff or spear, oversized symmetrical shoulder shapes and a narrow bright central tabard.",
    "Low horizontal or gently rising weapon projecting to image-right, closed bell-shaped robe and a compact cape on image-left.",
    "Hooked or crescent-topped staff along image-left, high collar, one large image-right pauldron and an offset skirt panel.",
    "Short weapon held across the waist, connected book or scroll case against one hip, broad triangular cloak and separated boots.",
    "Forked or diamond-topped polearm on image-right, layered shoulder mantle and a long central coat split only at the feet.",
    "Slightly outward vertical weapon on image-left, wing-like short cape panels, broad belt and a bright chest emblem made from large clusters.",
    "Long weapon held in both hands on a shallow diagonal below the face, armored robe, strong opposite-side shoulder and no floating parts.",
    "Royal guard pose with one complete side weapon, compact formal tabard, short cape ending above the knees and one hand near the hip.",
)


def group_dir(group: dict[str, object]) -> Path:
    return OUTPUT_ROOT / str(group["key"])


def original_path(group: dict[str, object]) -> Path:
    return (
        EDITOR_SPRITES
        / str(group["commander"])
        / f"{int(group['class_id']):02X}-p1.png"
    )


def current_identity_path(group: dict[str, object]) -> Path:
    return (
        CURRENT_SPRITES
        / str(group["commander"])
        / f"{int(group['class_id']):02X}.png"
    )


def load_resolved_masks() -> dict[tuple[int, int], set[tuple[int, int]]]:
    if not RESOLVED_MASKS.is_file():
        return {}
    document = json.loads(RESOLVED_MASKS.read_text(encoding="utf-8"))
    result: dict[tuple[int, int], set[tuple[int, int]]] = {}
    for raw_key, raw_points in document.get("masks", {}).items():
        commander_text, class_text = raw_key.split(":", 1)
        result[(int(commander_text), int(class_text, 16))] = {
            tuple(point) for point in raw_points
        }
    return result


def identity_points(
    group: dict[str, object],
    original: Image.Image,
) -> tuple[set[tuple[int, int]], str]:
    key = (int(group["commander"]), int(group["class_id"]))
    editor_masks = load_identity_mask_overrides()
    if editor_masks.get(key):
        points = set(editor_masks[key])
        source = "editor/ai_identity_masks.json"
    else:
        resolved = load_resolved_masks()
        if not resolved.get(key):
            raise ValueError(f"no current or resolved identity mask for {key}")
        points = set(resolved[key])
        source = str(RESOLVED_MASKS.relative_to(ROOT))
    points |= protected_eye_points(original)
    if not points:
        raise ValueError(f"empty identity mask for {key}")
    if any(not (0 <= x < 16 and 0 <= y < 16) for x, y in points):
        raise ValueError(f"out-of-bounds identity point for {key}")
    return points, source


def build_prompt(group: dict[str, object], candidate: int) -> str:
    character = str(group["character"])
    class_name = str(group["class_name"])
    # Rotate the same ten high-level composition families so same-class groups
    # do not even receive matching candidate-number layouts.
    offset = (int(group["commander"]) * 3 + int(group["class_id"])) % 10
    silhouette = SILHOUETTES[(candidate - 1 + offset) % 10]
    return f"""Use case: stylized-concept
Asset type: Mega Drive Langrisser II native logical-16x16 tactical-map character sprite candidate
Primary request: Generate fresh independent candidate {candidate:02d} for {character}'s {class_name} class. This is a new design made only from the two supplied inputs. Do not use, recall, imitate, or blend any previous AI generation, shared class template, or other commander's design.
Input images: Image 1 is the current {character} {class_name} 16x16 ROM/editor sprite and is a reference for exact character identity, original game pixel density and palette scale; Image 2 is the current identity-only pixel mask and is authoritative for the face, eyes, hair silhouette, hair volume and large-head placement. Neither image is an edit target.
Subject: Exactly one standing, unmounted {character} as {class_name}. {CLASS_DIRECTIONS[class_name]}
Character-specific direction: {CHARACTER_DIRECTIONS[character]}
Silhouette for this candidate: {silhouette}
Style/medium: True coarse Mega Drive-era logical-16x16 pixel art, designed as sixteen cells rather than a high-resolution anime illustration. Hard square clusters, no antialiasing, no smooth gradients and no detail that depends on subpixels.
Composition/framing: Head and hair occupy about one third of the full sprite height. Keep face and body naturally connected. Use all 16 rows and all 16 columns through meaningful hair, clothing, hand, weapon, cape or feet pixels. Keep every body part and the complete weapon inside the square without clipping. Separate face, neck, shoulders, arms, hands, closed torso, legs and equipment with intentional dark-charcoal pixels so the game background cannot show through the body.
Color palette: Follow {character}'s current reference colors and Mega Drive channel steps, with at most 15 visible sprite colors. No pure #000000; use dark charcoal or the reference outline color. Do not use chroma green in the subject.
Scene/backdrop: Perfectly flat uniform solid #00ff00 chroma-key background for local removal. No shadow, floor, texture, gradient, reflection, glow, border, frame or colored halo.
Constraints: Identity must stay recognizable and large; one connected silhouette; complete readable weapon; solid neck and torso boundaries; crisp outer contour; no empty full canvas row or column; no cropped edge; no detached ornament; no mount; no extra character; no text; no UI; no watermark.
Avoid: small head, tall anime anatomy, altered face or hair, hollow torso, missing hand, severed weapon, excessive detail, soft rendering, pure black background pixels, magenta or purple border contamination, checkerboard, previous AI artwork and simple recoloring of another commander.
"""


def prepare_group(group: dict[str, object]) -> None:
    directory = group_dir(group)
    for name in (
        "references",
        "raw-ai",
        "ai",
        "prompts",
        "logical16",
        "previews",
    ):
        (directory / name).mkdir(parents=True, exist_ok=True)

    source_path = original_path(group)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    original = Image.open(source_path).convert("RGBA")
    if original.size != (16, 16):
        raise ValueError(f"expected native 16x16 original: {source_path}")
    points, mask_source = identity_points(group, original)
    identity_source_path = current_identity_path(group)
    if not identity_source_path.is_file():
        raise FileNotFoundError(identity_source_path)
    identity_source = Image.open(identity_source_path).convert("RGBA")

    original.save(directory / "references/rom-original.png", optimize=True)
    original_matte = Image.new("RGBA", (16, 16), REFERENCE_BACKDROP)
    original_matte.alpha_composite(original)
    original_matte.resize((512, 512), RESAMPLING.NEAREST).save(
        directory / "references/rom-original-32x.png", optimize=True
    )

    identity = Image.new("RGBA", (16, 16), REFERENCE_BACKDROP)
    for point in points:
        identity.putpixel(point, identity_source.getpixel(point))
    identity.save(directory / "references/identity-only.png", optimize=True)
    identity.resize((512, 512), RESAMPLING.NEAREST).save(
        directory / "references/identity-only-32x.png", optimize=True
    )

    for candidate in range(1, 11):
        (directory / "prompts" / f"{candidate:02d}.txt").write_text(
            build_prompt(group, candidate), encoding="utf-8"
        )

    metadata = {
        "version": 1,
        "group": group,
        "generation_mode": "built-in imagegen; one independent call per candidate",
        "generation_inputs": [
            str(source_path.relative_to(ROOT)),
            str((directory / "references/identity-only-32x.png").relative_to(ROOT)),
        ],
        "derived_reference_preview": str(
            (directory / "references/rom-original-32x.png").relative_to(ROOT)
        ),
        "previous_ai_inputs": [],
        "identity_mask_source": mask_source,
        "identity_pixel_source": str(identity_source_path.relative_to(ROOT)),
        "identity_pixel_count": len(points),
        "candidate_count": 10,
    }
    (directory / "generation-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def prepare_references() -> None:
    for group in GROUPS:
        prepare_group(group)


def is_key_green(color: tuple[int, int, int, int]) -> bool:
    red, green, blue, alpha = color
    return bool(
        alpha
        and green >= 146
        and green > red * 1.65
        and green > blue * 1.65
    )


def remove_chroma_key(source: Image.Image) -> Image.Image:
    """Remove the requested green backdrop while preserving sprite colors."""
    result = source.convert("RGBA")
    for y in range(result.height):
        for x in range(result.width):
            color = result.getpixel((x, y))
            if is_key_green(color):
                result.putpixel((x, y), TRANSPARENT)
    return result


def repixel_ai(source: Image.Image) -> Image.Image:
    rgba = source.convert("RGBA")
    bbox = rgba.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("transparent AI candidate")
    subject = rgba.crop(bbox)
    sampled = subject.resize((16, 16), RESAMPLING.BOX)
    result = Image.new("RGBA", (16, 16), TRANSPARENT)
    for y in range(16):
        for x in range(16):
            color = sampled.getpixel((x, y))
            if color[3] < 48 or is_key_green(color):
                continue
            snapped = mega_drive_palette_color(color)
            if snapped[:3] == (0, 0, 0):
                snapped = ROM_INK
            if snapped[:3] == (255, 0, 255):
                snapped = (219, 36, 219, 255)
            result.putpixel((x, y), snapped)
    return result


def active_points(image: Image.Image) -> set[tuple[int, int]]:
    return {
        (x, y)
        for y in range(16)
        for x in range(16)
        if image.getpixel((x, y))[3]
    }


def components(image: Image.Image) -> list[set[tuple[int, int]]]:
    active = active_points(image)
    result: list[set[tuple[int, int]]] = []
    while active:
        start = active.pop()
        component = {start}
        pending = [start]
        while pending:
            x, y = pending.pop()
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in active:
                    active.remove(neighbor)
                    component.add(neighbor)
                    pending.append(neighbor)
        result.append(component)
    return sorted(result, key=len, reverse=True)


def shortest_connection(
    source: set[tuple[int, int]],
    target: set[tuple[int, int]],
    forbidden: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    queue = deque(source)
    previous: dict[tuple[int, int], tuple[int, int] | None] = {
        point: None for point in source
    }
    reached: tuple[int, int] | None = None
    while queue:
        point = queue.popleft()
        if point in target:
            reached = point
            break
        x, y = point
        for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            nx, ny = neighbor
            if not (0 <= nx < 16 and 0 <= ny < 16):
                continue
            if neighbor in previous or (neighbor in forbidden and neighbor not in target):
                continue
            previous[neighbor] = point
            queue.append(neighbor)
    if reached is None:
        raise ValueError("cannot connect candidate without crossing identity mask")
    path: list[tuple[int, int]] = []
    while reached is not None:
        path.append(reached)
        reached = previous[reached]
    return list(reversed(path))


def connect_components(
    image: Image.Image,
    identity: set[tuple[int, int]],
    identity_source: Image.Image,
) -> Image.Image:
    result = image.copy().convert("RGBA")
    forbidden = {
        point for point in identity if not identity_source.getpixel(point)[3]
    }
    for _ in range(32):
        parts = components(result)
        if len(parts) <= 1:
            return result
        main = parts[0]
        other = min(
            parts[1:],
            key=lambda part: min(
                abs(ax - bx) + abs(ay - by)
                for ax, ay in main
                for bx, by in part
            ),
        )
        path = shortest_connection(main, other, forbidden)
        for point in path:
            if point not in identity:
                result.putpixel(point, ROM_INK)
    raise ValueError("component repair did not converge")


def fill_empty_axes(
    image: Image.Image,
    identity: set[tuple[int, int]],
) -> Image.Image:
    result = image.copy().convert("RGBA")
    for target_y in range(16):
        if any(result.getpixel((x, target_y))[3] for x in range(16)):
            continue
        candidates = sorted(
            active_points(result), key=lambda p: (abs(p[1] - target_y), abs(p[0] - 8))
        )
        for source_x, source_y in candidates:
            ys = range(min(source_y, target_y), max(source_y, target_y) + 1)
            path = {(source_x, y) for y in ys}
            if path.isdisjoint(identity):
                color = result.getpixel((source_x, source_y))
                for point in path:
                    result.putpixel(point, color)
                break
        else:
            raise ValueError(f"cannot fill empty row {target_y}")
    for target_x in range(16):
        if any(result.getpixel((target_x, y))[3] for y in range(16)):
            continue
        candidates = sorted(
            active_points(result), key=lambda p: (abs(p[0] - target_x), abs(p[1] - 10))
        )
        for source_x, source_y in candidates:
            xs = range(min(source_x, target_x), max(source_x, target_x) + 1)
            path = {(x, source_y) for x in xs}
            if path.isdisjoint(identity):
                color = result.getpixel((source_x, source_y))
                for point in path:
                    result.putpixel(point, color)
                break
        else:
            raise ValueError(f"cannot fill empty column {target_x}")
    return result


def center_holes(image: Image.Image) -> set[tuple[int, int]]:
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
    pending = deque(outside)
    while pending:
        x, y = pending.popleft()
        for point in (
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
        ):
            if point in transparent and point not in outside:
                outside.add(point)
                pending.append(point)
    return {
        point
        for point in transparent - outside
        if 4 <= point[0] <= 11 and 8 <= point[1] <= 14
    }


def fill_center_holes(
    image: Image.Image,
    identity: set[tuple[int, int]],
) -> Image.Image:
    result = image.copy().convert("RGBA")
    for point in center_holes(result):
        if point not in identity:
            result.putpixel(point, ROM_INK)
    return result


def restore_identity(
    image: Image.Image,
    identity_source: Image.Image,
    identity: set[tuple[int, int]],
) -> Image.Image:
    result = image.copy().convert("RGBA")
    for point in identity:
        result.putpixel(point, identity_source.getpixel(point))
    return result


def finalize_native(
    source: Image.Image,
    identity_source: Image.Image,
    identity: set[tuple[int, int]],
) -> tuple[Image.Image, int]:
    result = repixel_ai(source)
    result = restore_identity(result, identity_source, identity)
    result = fill_empty_axes(result, identity)
    result = connect_components(result, identity, identity_source)
    result = fill_center_holes(result, identity)
    result = restore_identity(result, identity_source, identity)
    result = connect_components(result, identity, identity_source)
    result, remapped = limit_visible_palette(result, identity)
    result = restore_identity(result, identity_source, identity)
    return result, remapped


def image_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_candidate(
    image: Image.Image,
    identity_source: Image.Image,
    identity: set[tuple[int, int]],
) -> dict[str, object]:
    palette = Counter(color for color in image.getdata() if color[3])
    parts = components(image)
    empty_rows = [
        y for y in range(16)
        if not any(image.getpixel((x, y))[3] for x in range(16))
    ]
    empty_columns = [
        x for x in range(16)
        if not any(image.getpixel((x, y))[3] for y in range(16))
    ]
    identity_match = sum(
        image.getpixel(point) == identity_source.getpixel(point)
        for point in identity
    )
    pure_black = (0, 0, 0, 255) in palette
    # Some ROM identities legitimately contain a bright green hair/eye pixel.
    # Chroma contamination is only a failure outside the byte-exact identity.
    key_green = any(
        point not in identity and is_key_green(image.getpixel(point))
        for point in active_points(image)
    )
    exact_magenta = (255, 0, 255, 255) in palette
    holes = center_holes(image)
    accepted = bool(
        identity_match == len(identity)
        and len(palette) <= 15
        and len(parts) == 1
        and not empty_rows
        and not empty_columns
        and not pure_black
        and not key_green
        and not exact_magenta
        and not holes
    )
    return {
        "identity_match": identity_match,
        "identity_pixel_count": len(identity),
        "visible_color_count": len(palette),
        "palette": [
            "#{:02x}{:02x}{:02x}".format(*color[:3])
            for color, _ in palette.most_common()
        ],
        "connected_components": [len(part) for part in parts],
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "pure_black": pure_black,
        "chroma_green_contamination": key_green,
        "exact_magenta_contamination": exact_magenta,
        "center_holes": [list(point) for point in sorted(holes)],
        "accepted": accepted,
    }


def write_preview(image: Image.Image, path: Path) -> None:
    canvas = Image.new("RGBA", (256, 256), BOARD_BACKDROP)
    canvas.alpha_composite(image.resize((256, 256), RESAMPLING.NEAREST))
    canvas.convert("RGB").save(path, optimize=True)


def write_contact(directory: Path) -> None:
    card_width = 260
    card_height = 550
    canvas = Image.new("RGBA", (card_width * 5, card_height * 2), BOARD_BACKDROP)
    draw = ImageDraw.Draw(canvas)
    for candidate in range(1, 11):
        column = (candidate - 1) % 5
        row = (candidate - 1) // 5
        origin_x = column * card_width
        origin_y = row * card_height
        ai_image = Image.open(directory / "ai" / f"{candidate:02d}.png").convert("RGBA")
        bbox = ai_image.getchannel("A").getbbox()
        if bbox:
            ai_image = ai_image.crop(bbox)
        fitted = ImageOps.contain(ai_image, (232, 232), method=RESAMPLING.LANCZOS)
        canvas.alpha_composite(
            fitted,
            (
                origin_x + (card_width - fitted.width) // 2,
                origin_y + 30 + (232 - fitted.height) // 2,
            ),
        )
        logical = Image.open(
            directory / "logical16" / f"{candidate:02d}.png"
        ).convert("RGBA")
        logical = logical.resize((240, 240), RESAMPLING.NEAREST)
        canvas.alpha_composite(logical, (origin_x + 10, origin_y + 300))
        draw.text((origin_x + 8, origin_y + 8), f"Candidate {candidate:02d} - AI", fill=ROM_INK)
        draw.text((origin_x + 8, origin_y + 278), "Native logical 16x16", fill=ROM_INK)
    canvas.convert("RGB").save(directory / "contact-sheet.png", optimize=True)


def build_group(group: dict[str, object]) -> dict[str, object]:
    directory = group_dir(group)
    prepare_group(group)
    expected = [f"{candidate:02d}.png" for candidate in range(1, 11)]
    for candidate in range(1, 11):
        raw_path = directory / "raw-ai" / f"{candidate:02d}.png"
        ai_path = directory / "ai" / f"{candidate:02d}.png"
        if raw_path.is_file() and not ai_path.exists():
            with Image.open(raw_path) as opened:
                remove_chroma_key(opened).save(ai_path, optimize=True)
    for subdir in ("raw-ai", "ai"):
        actual = sorted(path.name for path in (directory / subdir).glob("*.png"))
        if actual != expected:
            raise ValueError(f"{group['key']} {subdir}: expected exactly {expected}, got {actual}")

    original = Image.open(original_path(group)).convert("RGBA")
    identity_source = Image.open(current_identity_path(group)).convert("RGBA")
    identity, mask_source = identity_points(group, original)
    reports: list[dict[str, object]] = []
    for candidate in range(1, 11):
        raw_path = directory / "raw-ai" / f"{candidate:02d}.png"
        ai_path = directory / "ai" / f"{candidate:02d}.png"
        logical_path = directory / "logical16" / f"{candidate:02d}.png"
        preview_path = directory / "previews" / f"{candidate:02d}.png"
        ai_image = Image.open(ai_path).convert("RGBA")
        result, remapped = finalize_native(
            ai_image, identity_source, identity
        )
        result.save(logical_path, optimize=True)
        write_preview(result, preview_path)
        reports.append({
            "candidate": candidate,
            "raw_ai": str(raw_path.relative_to(directory)),
            "transparent_ai": str(ai_path.relative_to(directory)),
            "prompt": f"prompts/{candidate:02d}.txt",
            "logical16": str(logical_path.relative_to(directory)),
            "preview": str(preview_path.relative_to(directory)),
            "raw_ai_sha256": image_hash(raw_path),
            "transparent_ai_sha256": image_hash(ai_path),
            "logical16_sha256": image_hash(logical_path),
            "palette_remapped_pixels": remapped,
            **validate_candidate(result, identity_source, identity),
        })

    write_contact(directory)
    report = {
        "version": 1,
        "group": group,
        "mode": "110-call Lane B: independent built-in imagegen -> chroma removal -> native logical16 repixel",
        "generation_input_policy": "current exact commander/class sprite plus current identity-only pixels; no previous AI",
        "previous_ai_inputs": [],
        "identity_mask_source": mask_source,
        "identity_pixel_count": len(identity),
        "candidate_count": len(reports),
        "built_in_imagegen_call_count": len(reports),
        "unique_raw_ai_count": len({row["raw_ai_sha256"] for row in reports}),
        "unique_logical16_count": len({row["logical16_sha256"] for row in reports}),
        "all_accepted": all(bool(row["accepted"]) for row in reports),
        "candidates": reports,
    }
    (directory / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def write_root_report() -> dict[str, object]:
    groups: list[dict[str, object]] = []
    raw_hashes: list[str] = []
    logical_hashes: list[str] = []
    for group in GROUPS:
        path = group_dir(group) / "validation-report.json"
        if not path.is_file():
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        groups.append({
            "key": group["key"],
            "candidate_count": report["candidate_count"],
            "all_accepted": report["all_accepted"],
            "unique_raw_ai_count": report["unique_raw_ai_count"],
            "unique_logical16_count": report["unique_logical16_count"],
        })
        raw_hashes.extend(row["raw_ai_sha256"] for row in report["candidates"])
        logical_hashes.extend(row["logical16_sha256"] for row in report["candidates"])
    result = {
        "version": 1,
        "expected_group_count": 11,
        "completed_group_count": len(groups),
        "expected_candidate_count": 110,
        "completed_candidate_count": sum(int(row["candidate_count"]) for row in groups),
        "unique_raw_ai_count": len(set(raw_hashes)),
        "unique_logical16_count": len(set(logical_hashes)),
        "all_groups_accepted": bool(
            len(groups) == 11
            and all(bool(row["all_accepted"]) for row in groups)
            and len(raw_hashes) == len(set(raw_hashes)) == 110
            and len(logical_hashes) == len(set(logical_hashes)) == 110
        ),
        "groups": groups,
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "validation-report-lane-b.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-references", action="store_true")
    parser.add_argument("--group", choices=tuple(GROUP_BY_KEY))
    parser.add_argument("--root-report", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not (args.prepare_references or args.group or args.root_report):
        raise SystemExit("choose --prepare-references, --group KEY, or --root-report")
    if args.prepare_references:
        prepare_references()
    if args.group:
        report = build_group(GROUP_BY_KEY[args.group])
        print(json.dumps({
            "group": args.group,
            "candidate_count": report["candidate_count"],
            "all_accepted": report["all_accepted"],
        }, ensure_ascii=False))
        if not report["all_accepted"]:
            raise SystemExit(1)
    if args.root_report:
        print(json.dumps(write_root_report(), ensure_ascii=False))


if __name__ == "__main__":
    main()
