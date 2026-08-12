#!/usr/bin/env python3
"""Build the ROM-anchored ten-design sample campaign.

The generative step produces one 5x2 board per commander/class group.  This
tool prepares ROM-only references, extracts each board cell, converts it to a
native 16x16 sprite without shared body templates, restores the user's face
and hair pixels (including a one-pixel dark boundary), validates ROM-relative
scale, and publishes the review catalog used by the editor.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.build_ten_sample_class_campaign import (
    CLASSES,
    COMMANDERS,
    campaign_groups,
)
from tools.pillow_compat import flattened_image_data


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/"
    / "sample-class-variants-v3-rom-reference-ten"
)
STATIC_ROOT = ROOT / "editor/static/sample-class-sprites"
ROM_ROOT = ROOT / "editor/static/class-sprites/commanders"
CURRENT_ROOT = ROOT / "editor/static/ai-class-sprites"
CURRENT_MANIFEST = CURRENT_ROOT / "manifest.json"
MASK_FILE = ROOT / "editor/ai_identity_masks.json"
ASSET_VERSION = "sample-classes-v3-rom-reference-ten"
TRANSPARENT = (0, 0, 0, 0)


CLASS_VARIATIONS = {
    0x08: (
        "short cross staff and compact mantle",
        "ring healing staff and split stole",
        "small crozier and broad sleeves",
        "crystal rod and asymmetric mantle",
        "book and short blessing wand",
        "sun-disk staff and layered tabard",
        "bell staff and narrow shoulder cape",
        "long diagonal healing staff",
        "open casting hand and short scepter",
        "double-bar staff and full ritual mantle",
    ),
    0x15: (
        "round-orb staff and compact robe",
        "crescent staff and short shoulder cape",
        "crooked staff and layered mantle",
        "short wand and closed spellbook",
        "ring staff and high collar",
        "forked staff and split-front robe",
        "crystal rod and asymmetric cape",
        "long diagonal staff and pale inner panel",
        "double-orb staff and narrow robe",
        "tall wizard staff and broad mantle",
    ),
    0x16: (
        "tall cross staff and broad vestment",
        "sunburst staff and layered stole",
        "curved crozier and symmetrical cape",
        "scripture and short ceremonial scepter",
        "bell staff and edged robe",
        "halo-ring staff and long inner tabard",
        "double-bar cross and compact mantle",
        "crystal cross and wide ritual sleeves",
        "blessing scepter and open hand",
        "long ceremonial staff and split robe",
    ),
    0x18: (
        "closed codex and slim crystal staff",
        "scroll and orb-topped staff",
        "hourglass and short rune wand",
        "held orb and rectangular tablet",
        "forked staff and open book",
        "lantern staff and scroll case",
        "long diagonal rune staff",
        "short wand and large codex",
        "twin-crystal scepter and compact mantle",
        "tall wisdom staff and scholarly robe",
    ),
    0x22: (
        "large diagonal sword and broad pauldrons",
        "upright sword and full cape",
        "forward sword and asymmetric shoulders",
        "sword and compact shield",
        "broad blade and wing-like pauldrons",
        "two-handed sword held low",
        "raised sword and wind-swept cape",
        "royal sword and wide chest armor",
        "greatsword behind one shoulder",
        "heavy hero sword and layered armor",
    ),
    0x25: (
        "short blade and one-shoulder cloak",
        "slim spear and light mantle",
        "paired short weapons and split coat",
        "long dagger and compact shoulder guard",
        "small buckler and short sword",
        "throwing blade and swept cape",
        "light staff-spear and narrow coat",
        "crossed weapon pose and high collar",
        "single long blade and asymmetric armor",
        "officer weapon and broad short mantle",
    ),
    0x26: (
        "vertical long lance and light armor",
        "long diagonal javelin and short mantle",
        "leaf-blade spear and compact cape",
        "two-handed ritual spear",
        "officer lance and guarded shoulder",
        "forked spearhead and fitted armor",
        "banner spear and closed battle robe",
        "short throwing spear and broad guard",
        "crystal lance and asymmetric mantle",
        "very long diagonal spear and grounded stance",
    ),
    0x28: (
        "ring summoning staff and closed robe",
        "large crystal-orb staff and wide sleeves",
        "two-prong staff and short mantle",
        "short rune wand and shoulder emblems",
        "long diagonal staff and split inner panels",
        "summoning book and held orb scepter",
        "lantern-ring staff and asymmetric cape",
        "double-prong staff and compact sealed robe",
        "rune wand and broad sleeves",
        "twin-scroll staff and flared robe",
    ),
}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def group_root(group: dict) -> Path:
    return SOURCE_ROOT / group["id"]


def rgba_distance(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    return sum((int(a[index]) - int(b[index])) ** 2 for index in range(3))


def luminance(color: tuple[int, int, int, int]) -> float:
    return 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]


def manifest_identity_points(manifest: dict, group: dict) -> set[tuple[int, int]]:
    row = manifest["commanders"][str(group["commander_id"])]["classes"][
        str(group["class_id"])
    ]
    return {tuple(point) for point in row.get("identity_lock_points", [])}


def expanded_identity_points(
    points: set[tuple[int, int]], image: Image.Image
) -> set[tuple[int, int]]:
    """Add only the dark one-pixel boundary touching the saved identity mask."""
    result = set(points)
    for x, y in points:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                point = (x + dx, y + dy)
                if point in result or not (0 <= point[0] < 16 and 0 <= point[1] < 16):
                    continue
                color = image.getpixel(point)
                if color[3] and luminance(color) <= 112:
                    result.add(point)
    return result


def transparent_nearest(image: Image.Image, scale: int = 32) -> Image.Image:
    return image.resize(
        (image.width * scale, image.height * scale),
        Image.Resampling.NEAREST,
    )


def class_lineage_ids(class_id: int) -> tuple[int, ...]:
    return {
        0x08: (0x02, 0x08, 0x11, 0x12, 0x16),
        0x15: (0x03, 0x09, 0x13, 0x14, 0x15),
        0x16: (0x02, 0x08, 0x11, 0x12, 0x16),
        0x18: (0x11, 0x12, 0x13, 0x15, 0x18),
        0x22: (0x04, 0x0B, 0x1A, 0x23, 0x22),
        0x25: (0x01, 0x21, 0x23, 0x25),
        0x26: (0x03, 0x09, 0x0A, 0x15, 0x26),
        0x28: (0x03, 0x0A, 0x15, 0x18, 0x28),
    }[class_id]


def build_rom_board(group: dict, original: Image.Image) -> Image.Image:
    """ROM-only reference: large target plus diverse original lineage sprites."""
    canvas = Image.new("RGBA", (1024, 640), (128, 132, 136, 255))
    target = transparent_nearest(original, 32)
    canvas.alpha_composite(target, (32, 64))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((24, 56, 551, 583), outline=(210, 214, 218, 255), width=4)
    commander = int(group["commander_id"])
    target_class = int(group["class_id"])
    lineage = class_lineage_ids(target_class)
    positions = ((600, 56), (808, 56), (600, 264), (808, 264), (704, 448))
    candidates: list[Path] = []
    candidates.extend(ROM_ROOT / str(commander) / f"{class_id:02X}-p1.png" for class_id in lineage)
    candidates.extend(ROM_ROOT / str(other) / f"{target_class:02X}-p1.png" for other in COMMANDERS)
    candidates.extend(
        ROM_ROOT / str(other) / f"{class_id:02X}-p1.png"
        for class_id in lineage
        for other in COMMANDERS
    )
    target_bytes = original.tobytes()
    seen = {target_bytes}
    used = 0
    for path in candidates:
        if not path.is_file():
            continue
        with Image.open(path) as opened:
            native = opened.convert("RGBA")
        key = native.tobytes()
        if key in seen:
            continue
        seen.add(key)
        sprite = native.resize((192, 192), Image.Resampling.NEAREST)
        canvas.alpha_composite(sprite, positions[used])
        used += 1
        if used == len(positions):
            break
    return canvas


def board_prompt(group: dict) -> str:
    _, commander_name = COMMANDERS[int(group["commander_id"])]
    _, class_name = CLASSES[int(group["class_id"])]
    variations = CLASS_VARIATIONS[int(group["class_id"])]
    items = "; ".join(f"{index + 1}: {value}" for index, value in enumerate(variations))
    return f"""Use case: identity-preserve
Asset type: a 5-column by 2-row review sheet containing ten separate native-logical-16x16 Mega Drive tactical-RPG commander map sprites
Input images: Image 1 is a ROM-ONLY reference board. Its large left sprite is the exact original {commander_name} {class_name} sprite and is the primary design anchor, not merely a style reference. The smaller sprites are exact original-ROM lineage examples. Image 2 is the current face and hair identity mask including its dark boundary. No previous AI image may be used.
Primary request: create ten visibly different but ROM-faithful {commander_name} {class_name} variants. Every variant must look like a neighboring unused sprite from the same original 1994 Mega Drive game. Preserve 70-85 percent of the large target ROM sprite: facing direction, large head-to-body ratio, head location, compact anatomy, hand side, weapon side, overall scale, outline thickness, value steps and main color placement. Vary class equipment clearly, without redesigning the person.
Candidate equipment directions: {items}.
Variation rule: the ten candidates must differ visibly in weapon direction or weapon-head shape, cape or sleeve silhouette, shoulder ornament, and lower garment or armor outline. Do not create ten recolors of one body template. Preserve the character identity and original ROM visual grammar while varying 15-30 percent of equipment pixels.
Style/medium: authentic coarse early-1990s Mega Drive pixel art. Each individual sprite is exactly sixteen large logical pixel cells across and sixteen down, hard square edges, no antialiasing, no blur, no gradient, no tiny subcells, no 32x32 density, no modern indie-pixel rendering.
Layout: exactly ten equal cells in a clean 5x2 grid, one centered full sprite per cell, no labels or numbers. Keep the original ROM sprite bounding box within plus or minus one logical pixel; original empty edge columns may remain empty. Nothing may be cropped.
Identity invariants: preserve Image 2 face, eye, hair silhouette, head size, and the adjoining dark outline. Keep a closed readable neck-to-torso boundary. Do not add a hood, helmet, mount, extra face, or longer hair.
Color: derive each candidate from the large target ROM sprite's actual palette family and dark colored outlines. Candidates may use one or two restrained adjacent Mega Drive hues for equipment accents. They must not all use the same color distribution. No pure-black background and no purple/magenta border.
Backdrop: perfectly flat uniform #00FF00 chroma-key background, no border, floor, shadow, texture, gradient, scenery, text, logo or watermark. Never use #00FF00 inside a sprite.
Avoid: generic fantasy concept art, tiny head, oversized human body, shared caster template, identical robe silhouettes, palette-swapped clones, over-detailed armor, broken grip, missing hand, disconnected equipment, center hole, background-colored seams.
"""


def prepare() -> None:
    manifest = json.loads(CURRENT_MANIFEST.read_text(encoding="utf-8"))
    saved_masks = json.loads(MASK_FILE.read_text(encoding="utf-8")).get("masks", {})
    groups = campaign_groups()
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    for group in groups:
        root = group_root(group)
        for child in ("ai", "logical16", "previews", "prompts", "references", "raw-boards"):
            (root / child).mkdir(parents=True, exist_ok=True)
        original_path = ROM_ROOT / str(group["commander_id"]) / f"{group['class_id']:02X}-p1.png"
        current_path = CURRENT_ROOT / str(group["commander_id"]) / f"{group['class_id']:02X}.png"
        with Image.open(original_path) as opened:
            original = opened.convert("RGBA")
        with Image.open(current_path) as opened:
            current = opened.convert("RGBA")
        mask_key = f"{group['commander_id']}:{group['class_id']:02X}"
        base_points = {
            tuple(point) for point in saved_masks.get(mask_key, [])
        } or manifest_identity_points(manifest, group)
        points = expanded_identity_points(base_points, current)

        original.save(root / "references/rom-original16.png", optimize=True)
        transparent_nearest(original).save(
            root / "references/rom-original-32x-alpha.png", optimize=True
        )
        board = build_rom_board(group, original)
        board.save(root / "references/rom-only-board.png", optimize=True)
        identity = Image.new("RGBA", (16, 16), TRANSPARENT)
        for point in points:
            identity.putpixel(point, current.getpixel(point))
        identity.save(root / "references/identity-with-dark-boundary16.png", optimize=True)
        transparent_nearest(identity).save(
            root / "references/identity-with-dark-boundary-32x.png", optimize=True
        )
        write_json(
            root / "references/identity-mask-expanded.json",
            {
                "commander_id": group["commander_id"],
                "class_id": f"{group['class_id']:02X}",
                "points": [list(point) for point in sorted(points)],
                "pixel_count": len(points),
                "policy": "saved identity plus one touching dark boundary ring",
            },
        )
        (root / "prompts/board.txt").write_text(board_prompt(group), encoding="utf-8")
    write_json(
        SOURCE_ROOT / "campaign.json",
        {
            "asset_version": ASSET_VERSION,
            "expected_group_count": len(groups),
            "expected_candidate_count": len(groups) * 10,
            "generation_inputs": ["ROM-only board", "expanded identity-only image"],
            "previous_ai_used": False,
            "groups": groups,
        },
    )


def expand_saved_masks() -> None:
    manifest = json.loads(CURRENT_MANIFEST.read_text(encoding="utf-8"))
    data = json.loads(MASK_FILE.read_text(encoding="utf-8"))
    changed: dict[str, int] = {}
    for group in campaign_groups():
        key = f"{group['commander_id']}:{group['class_id']:02X}"
        if key not in data["masks"]:
            continue
        current_path = CURRENT_ROOT / str(group["commander_id"]) / f"{group['class_id']:02X}.png"
        with Image.open(current_path) as opened:
            current = opened.convert("RGBA")
        before = {tuple(point) for point in data["masks"][key]}
        authoritative = before or manifest_identity_points(manifest, group)
        after = expanded_identity_points(authoritative, current)
        if after != before:
            data["masks"][key] = [list(point) for point in sorted(after)]
            changed[key] = len(after) - len(before)
    write_json(MASK_FILE, data)
    write_json(SOURCE_ROOT / "expanded-mask-report.json", changed)
    print(f"expanded {len(changed)} saved masks")


def dominant_border_color(image: Image.Image) -> tuple[int, int, int, int]:
    border = []
    for x in range(image.width):
        border.extend((image.getpixel((x, 0)), image.getpixel((x, image.height - 1))))
    for y in range(image.height):
        border.extend((image.getpixel((0, y)), image.getpixel((image.width - 1, y))))
    return Counter(border).most_common(1)[0][0]


def remove_cell_background(cell: Image.Image) -> Image.Image:
    cell = cell.convert("RGBA")
    key = dominant_border_color(cell)
    result = Image.new("RGBA", cell.size, TRANSPARENT)
    for y in range(cell.height):
        for x in range(cell.width):
            color = cell.getpixel((x, y))
            if rgba_distance(color, key) <= 10000:
                continue
            result.putpixel((x, y), color)
    return keep_subject_components(result)


def keep_subject_components(image: Image.Image) -> Image.Image:
    """Discard isolated background/halo specks without redrawing the subject."""
    remaining = {
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if image.getpixel((x, y))[3]
    }
    components: list[set[tuple[int, int]]] = []
    while remaining:
        seed = remaining.pop()
        component = {seed}
        stack = [seed]
        while stack:
            x, y = stack.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if not (dx or dy):
                        continue
                    point = (x + dx, y + dy)
                    if point in remaining:
                        remaining.remove(point)
                        component.add(point)
                        stack.append(point)
        components.append(component)
    if not components:
        return image
    largest = max(len(component) for component in components)
    kept = [component for component in components if len(component) >= max(8, largest // 100)]
    result = Image.new("RGBA", image.size, TRANSPARENT)
    for component in kept:
        for point in component:
            result.putpixel(point, image.getpixel(point))
    return result


def opaque_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError("empty generated board cell")
    return bbox


def mega_drive_channel(value: int) -> int:
    levels = (0, 36, 73, 109, 146, 182, 219, 255)
    return min(levels, key=lambda level: abs(level - value))


def snap_color(color: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return tuple(mega_drive_channel(value) for value in color[:3]) + (255,)


def palette_for(
    generated: Image.Image,
    original: Image.Image,
    identity: Image.Image,
) -> list[tuple[int, int, int, int]]:
    identity_colors = [color for _, color in identity.getcolors(maxcolors=256) or [] if color[3]]
    original_colors = [color for _, color in original.getcolors(maxcolors=256) or [] if color[3]]
    counts = Counter(
        snap_color(color)
        for _, color in generated.getcolors(maxcolors=65536) or []
        if color[3] and color[:3] not in ((0, 0, 0), (255, 0, 255), (0, 255, 0))
    )
    palette: list[tuple[int, int, int, int]] = []
    for color in identity_colors + original_colors + [row[0] for row in counts.most_common()]:
        candidate = snap_color(color) if color not in identity_colors else color
        if candidate[:3] == (0, 0, 0):
            continue
        if candidate not in palette:
            palette.append(candidate)
        if len(palette) == 15:
            break
    return palette


def logical_from_cell(cell: Image.Image, root: Path) -> Image.Image:
    foreground = remove_cell_background(cell)
    crop = foreground.crop(opaque_bbox(foreground))
    with Image.open(root / "references/rom-original16.png") as opened:
        original = opened.convert("RGBA")
    with Image.open(root / "references/identity-with-dark-boundary16.png") as opened:
        identity = opened.convert("RGBA")
    left, top, right, bottom = opaque_bbox(original)
    target_width = right - left
    target_height = bottom - top
    reduced = crop.resize((target_width, target_height), Image.Resampling.BOX)
    logical = Image.new("RGBA", (16, 16), TRANSPARENT)
    logical.alpha_composite(reduced, (left, top))
    palette = palette_for(logical, original, identity)
    for y in range(16):
        for x in range(16):
            color = logical.getpixel((x, y))
            if color[3] < 96:
                logical.putpixel((x, y), TRANSPARENT)
            elif palette:
                logical.putpixel((x, y), min(palette, key=lambda target: rgba_distance(color, target)))
    mask = json.loads((root / "references/identity-mask-expanded.json").read_text(encoding="utf-8"))
    for point in mask["points"]:
        xy = tuple(point)
        logical.putpixel(xy, identity.getpixel(xy))
    return logical


def ingest_board(group_id: str, source: Path) -> None:
    root = SOURCE_ROOT / group_id
    if not root.is_dir():
        raise FileNotFoundError(root)
    with Image.open(source) as opened:
        board = opened.convert("RGBA")
    raw_target = root / "raw-boards/board.png"
    if source.resolve() != raw_target.resolve():
        shutil.copy2(source, raw_target)
    for index in range(10):
        column = index % 5
        row = index // 5
        left = round(column * board.width / 5)
        right = round((column + 1) * board.width / 5)
        top = round(row * board.height / 2)
        bottom = round((row + 1) * board.height / 2)
        cell = board.crop((left, top, right, bottom))
        ai = remove_cell_background(cell)
        bbox = opaque_bbox(ai)
        ai = ai.crop(bbox)
        ai.save(root / f"ai/{index + 1:02d}.png", optimize=True)
        logical = logical_from_cell(cell, root)
        logical.save(root / f"logical16/{index + 1:02d}.png", optimize=True)
        logical.resize((256, 256), Image.Resampling.NEAREST).save(
            root / f"previews/{index + 1:02d}.png", optimize=True
        )
    if group_id == "10-jessica-26-zarvera":
        preserved_root = (
            ROOT
            / "assets/class-sprites/source/latest/"
            / "sample-class-variants-v2-ten/10-jessica-26-zarvera"
        )
        shutil.copy2(preserved_root / "ai/01.png", root / "ai/01.png")
        with Image.open(preserved_root / "logical16/01.png") as opened:
            preserved = opened.convert("RGBA")
        with Image.open(root / "references/identity-with-dark-boundary16.png") as opened:
            identity = opened.convert("RGBA")
        mask = json.loads(
            (root / "references/identity-mask-expanded.json").read_text(encoding="utf-8")
        )
        for point in mask["points"]:
            xy = tuple(point)
            preserved.putpixel(xy, identity.getpixel(xy))
        preserved.save(root / "logical16/01.png", optimize=True)
        preserved.resize((256, 256), Image.Resampling.NEAREST).save(
            root / "previews/01.png", optimize=True
        )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bbox_delta(candidate: Image.Image, original: Image.Image) -> list[int]:
    a = opaque_bbox(candidate)
    b = opaque_bbox(original)
    return [a[index] - b[index] for index in range(4)]


def publish() -> None:
    groups = campaign_groups()
    manifest_groups = []
    reports = []
    diversity_reports = []
    contact_rows = []
    for group in groups:
        root = group_root(group)
        with Image.open(root / "references/rom-original16.png") as opened:
            original = opened.convert("RGBA")
        samples = []
        panels = []
        group_logicals: list[Image.Image] = []
        identities = json.loads((root / "references/identity-mask-expanded.json").read_text(encoding="utf-8"))["points"]
        with Image.open(root / "references/identity-with-dark-boundary16.png") as opened:
            identity_image = opened.convert("RGBA")
        for index in range(1, 11):
            sample_id = f"{index:02d}"
            preserved = group["id"] == "10-jessica-26-zarvera" and index == 1
            ai_path = root / f"ai/{sample_id}.png"
            logical_path = root / f"logical16/{sample_id}.png"
            if not ai_path.is_file() or not logical_path.is_file():
                raise FileNotFoundError(ai_path if not ai_path.is_file() else logical_path)
            with Image.open(ai_path) as opened:
                ai = opened.convert("RGBA")
            with Image.open(logical_path) as opened:
                logical = opened.convert("RGBA")
            colors = {color for _, color in logical.getcolors(maxcolors=256) or [] if color[3]}
            identity_matches = sum(
                logical.getpixel(tuple(point)) == identity_image.getpixel(tuple(point))
                for point in identities
            )
            delta = bbox_delta(logical, original)
            opaque = sum(
                1 for color in flattened_image_data(logical) if color[3]
            )
            original_opaque = sum(
                1 for color in flattened_image_data(original) if color[3]
            )
            report = {
                "group": group["id"],
                "sample": sample_id,
                "sha256": sha256(logical_path),
                "visible_colors": len(colors),
                "identity_matches": identity_matches,
                "identity_total": len(identities),
                "bbox_delta": delta,
                "opaque_ratio": round(opaque / original_opaque, 4),
                "preserved": preserved,
            }
            report["accepted"] = (
                len(colors) <= 15
                and identity_matches == len(identities)
                and (preserved or all(abs(value) <= 2 for value in delta))
                and 0.70 <= opaque / original_opaque <= 1.35
            )
            reports.append(report)
            group_logicals.append(logical.copy())

            static = STATIC_ROOT / group["id"]
            for subdir in ("ai", "logical16", "previews"):
                (static / subdir).mkdir(parents=True, exist_ok=True)
            ai_thumbnail = ai.copy()
            ai_thumbnail.thumbnail((384, 384), Image.Resampling.NEAREST)
            ai_thumbnail.save(static / f"ai/{sample_id}.png", optimize=True)
            shutil.copy2(logical_path, static / f"logical16/{sample_id}.png")
            shutil.copy2(root / f"previews/{sample_id}.png", static / f"previews/{sample_id}.png")
            samples.append({
                "id": sample_id,
                "label": "세로 장창형" if preserved else f"ROM 변형 {sample_id}",
                "description": "원본 ROM 자세·비율·도트 문법을 유지한 장비 변형",
                "ai_source": f"sample-class-sprites/{group['id']}/ai/{sample_id}.png",
                "logical16": f"sample-class-sprites/{group['id']}/logical16/{sample_id}.png",
                "preview": f"sample-class-sprites/{group['id']}/previews/{sample_id}.png",
                "preserved": preserved,
            })
            panel = Image.new("RGBA", (104, 176), (28, 32, 29, 255))
            draw = ImageDraw.Draw(panel)
            draw.text((4, 4), sample_id, fill=(235, 240, 236, 255))
            thumb = ai.copy()
            thumb.thumbnail((96, 96), Image.Resampling.NEAREST)
            panel.alpha_composite(thumb, ((104 - thumb.width) // 2, 20))
            panel.alpha_composite(logical.resize((64, 64), Image.Resampling.NEAREST), (20, 108))
            panels.append(panel)
        equipment_differences: list[int] = []
        silhouette_differences: list[int] = []
        identity_set = {tuple(point) for point in identities}
        for first in range(len(group_logicals)):
            for second in range(first + 1, len(group_logicals)):
                equipment_differences.append(
                    sum(
                        group_logicals[first].getpixel((x, y))
                        != group_logicals[second].getpixel((x, y))
                        for y in range(16)
                        for x in range(16)
                        if (x, y) not in identity_set
                    )
                )
                silhouette_differences.append(
                    sum(
                        bool(group_logicals[first].getpixel((x, y))[3])
                        != bool(group_logicals[second].getpixel((x, y))[3])
                        for y in range(16)
                        for x in range(16)
                        if (x, y) not in identity_set
                    )
                )
        diversity = {
            "group": group["id"],
            "pair_count": len(equipment_differences),
            "minimum_equipment_pixel_difference": min(equipment_differences),
            "median_equipment_pixel_difference": statistics.median(equipment_differences),
            "minimum_silhouette_pixel_difference": min(silhouette_differences),
            "median_silhouette_pixel_difference": statistics.median(silhouette_differences),
        }
        diversity["accepted"] = (
            diversity["minimum_equipment_pixel_difference"] >= 10
            and diversity["median_equipment_pixel_difference"] >= 40
            and diversity["median_silhouette_pixel_difference"] >= 8
        )
        diversity_reports.append(diversity)
        row = Image.new("RGBA", (1040, 176), (18, 21, 19, 255))
        for index, panel in enumerate(panels):
            row.alpha_composite(panel, (104 * index, 0))
        contact_path = root / "contact-sheet.png"
        row.save(contact_path, optimize=True)
        contact_rows.append((group, row))
        manifest_groups.append({
            "id": group["id"],
            "commander_id": group["commander_id"],
            "class_id": group["class_id"],
            "title": group["title"],
            "description": "원본 ROM을 주 디자인 기준으로 삼고 얼굴의 어두운 경계까지 고정한 10안",
            "expected_sample_count": 10,
            "complete": True,
            "samples": samples,
        })
    master = Image.new("RGBA", (1040, 200 * len(contact_rows)), (14, 17, 15, 255))
    draw = ImageDraw.Draw(master)
    y = 0
    for group, row in contact_rows:
        draw.text((6, y + 5), group["title"], fill=(235, 240, 236, 255))
        master.alpha_composite(row, (0, y + 24))
        y += 200
    master_path = SOURCE_ROOT / "all-ai-and-logical16.png"
    master.convert("RGB").save(master_path, optimize=True)
    commander_sheets: dict[str, str] = {}
    commander_root = SOURCE_ROOT / "contact-sheets/commanders"
    commander_root.mkdir(parents=True, exist_ok=True)
    for commander_id in sorted({int(group["commander_id"]) for group, _ in contact_rows}):
        selected = [(group, row) for group, row in contact_rows if int(group["commander_id"]) == commander_id]
        sheet = Image.new("RGBA", (1040, 200 * len(selected)), (14, 17, 15, 255))
        sheet_draw = ImageDraw.Draw(sheet)
        offset = 0
        for group, row in selected:
            sheet_draw.text((6, offset + 5), group["title"], fill=(235, 240, 236, 255))
            sheet.alpha_composite(row, (0, offset + 24))
            offset += 200
        slug = COMMANDERS[commander_id][0]
        path = commander_root / f"{commander_id:02d}-{slug}.png"
        sheet.convert("RGB").save(path, optimize=True)
        commander_sheets[f"commander_{commander_id}"] = str(path.relative_to(ROOT))
    validation = {
        "asset_version": ASSET_VERSION,
        "sample_count": len(reports),
        "accepted_count": sum(row["accepted"] for row in reports),
        "all_accepted": (
            all(row["accepted"] for row in reports)
            and all(row["accepted"] for row in diversity_reports)
        ),
        "samples": reports,
        "diversity_groups": diversity_reports,
    }
    write_json(SOURCE_ROOT / "validation-report.json", validation)
    manifest = {
        "asset_version": ASSET_VERSION,
        "layout": "vertical-groups-horizontal-ten",
        "partial": False,
        "ready_group_count": len(groups),
        "expected_group_count": len(groups),
        "ready_candidate_count": len(groups) * 10,
        "expected_candidate_count": len(groups) * 10,
        "groups": manifest_groups,
        "review_sheets": {
            "all": str(master_path.relative_to(ROOT)),
            **commander_sheets,
        },
    }
    write_json(STATIC_ROOT / "manifest.json", manifest)
    write_json(STATIC_ROOT / "validation-report.json", validation)
    print(f"published {len(groups)} groups / {len(reports)} ROM-anchored samples")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "expand-masks", "ingest", "publish"))
    parser.add_argument("--group")
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
        print(f"prepared {len(campaign_groups())} ROM reference packs")
    elif args.action == "expand-masks":
        expand_saved_masks()
    elif args.action == "ingest":
        if not args.group or not args.source:
            parser.error("ingest requires --group and --source")
        ingest_board(args.group, args.source)
    else:
        publish()


if __name__ == "__main__":
    main()
