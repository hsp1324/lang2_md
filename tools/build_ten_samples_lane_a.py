#!/usr/bin/env python3
"""Prepare and repixelise ten independent class-design samples per group.

Lane A intentionally keeps generated-image inputs narrow: one neutral 32x ROM
reference and one identity-only reference.  Generated images are review sources,
not shippable sprites.  ``--process`` reinterprets each source on a logical
16x16 grid, restores the current editor identity pixels exactly, and validates
the constraints requested for the sample catalog.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/class-sprites/source/latest/sample-class-variants-v2-ten"
MANIFEST = ROOT / "editor/static/ai-class-sprites/manifest.json"
ROM_ROOT = ROOT / "editor/static/class-sprites/commanders"
CURRENT_ROOT = ROOT / "editor/static/ai-class-sprites"
CHROMA_HELPER = Path(
    "/home/hong/.codex/skills/.system/imagegen/scripts/remove_chroma_key.py"
)

TRANSPARENT = (0, 0, 0, 0)
NEUTRAL = (216, 216, 216, 255)
INK = (36, 36, 36, 255)
CHROMA = "#00FF00"


GROUPS = [
    (2, "liana", 0x08, "healer", "Healer"),
    (2, "liana", 0x15, "wizard", "Wizard"),
    (2, "liana", 0x16, "high-priest", "High Priest"),
    (2, "liana", 0x18, "sage", "Sage"),
    (2, "liana", 0x25, "agent", "Agent"),
    (2, "liana", 0x26, "zarvera", "Zarvera"),
    (2, "liana", 0x28, "summoner", "Summoner"),
    (7, "keith", 0x08, "healer", "Healer"),
    (7, "keith", 0x15, "wizard", "Wizard"),
    (7, "keith", 0x16, "high-priest", "High Priest"),
    (8, "aaron", 0x16, "high-priest", "High Priest"),
]

CHARACTER_NOTES = {
    "liana": (
        "Liana is a young long-haired woman. Keep her large original head and "
        "long hair silhouette. Use warm ivory, crimson red, white and restrained gold."
    ),
    "keith": (
        "Keith is a compact male commander. Keep his original short-hair head, "
        "facial pixels and sturdy stance. Use deep blue, teal, silver and restrained gold."
    ),
    "aaron": (
        "Aaron is a broad veteran male commander. Keep his original large head and "
        "facial pixels while giving the body a powerful build. Use sky blue, royal blue, "
        "silver-white and restrained gold."
    ),
}

CLASS_NOTES = {
    "healer": (
        "Readable healer vestments: simple robe, separated sleeves and one unmistakable "
        "healing implement. Gentle but battle-ready, no mount and no second character."
    ),
    "wizard": (
        "Readable field wizard: layered robe or short mantle, one clear magic implement, "
        "stronger than a healer but less ceremonial than a high priest."
    ),
    "high-priest": (
        "Advanced high-priest vestments with a broader mantle, ornate but clean trim and "
        "one clear ceremonial implement. Powerful without visual clutter."
    ),
    "sage": (
        "Advanced sage robes with an authoritative mantle and one clear scholarly magic "
        "implement. Keep the silhouette compact, wise and stronger than a wizard."
    ),
    "agent": (
        "Agile unmounted agent outfit with a fitted tunic, short cape and exactly one "
        "clearly readable light weapon. Do not turn the body into a robe."
    ),
    "zarvera": (
        "Advanced spear-and-javelin infantry with one unmistakable long pole weapon. "
        "This is not a staff-bearing mage. Keep the torso, coat and lower body solid and "
        "connected, and make spearhead, shaft and gripping hand read as one continuous weapon."
    ),
    "summoner": (
        "Advanced summoner robe with one unmistakable summoning implement. Show magic via "
        "equipment and trim only; no summoned creature and no second figure."
    ),
}

DIRECTIONS = {
    "healer": [
        "upright crozier on image-right; free hand extended on image-left",
        "short ring-topped staff on image-left; compact forward blessing pose",
        "open prayer book on image-left and a small wand on image-right",
        "bell-ended staff held diagonally toward image-right",
        "winged healing rod upright on image-left with broad opposite sleeve",
        "single-orb staff on image-right with asymmetric short mantle",
        "double-ring crozier on image-left with a narrow opposite arm",
        "forward-pointing blessing scepter on image-right and long rear sash",
        "lantern-like reliquary staff on image-left with stepped robe hem",
        "compact ceremonial mace-scepter on image-right with wide sleeves",
    ],
    "wizard": [
        "tall crystal staff on image-right with cape mass on image-left",
        "long diagonal magic rod from image-left floor toward image-right shoulder",
        "open grimoire on image-left and short wand on image-right",
        "crescent staff upright on image-left with narrow opposite sleeve",
        "single-orb staff on image-right with asymmetric robe panels",
        "fork-topped staff on image-left with one forward casting hand",
        "short wand extended to image-right with cape flowing image-left",
        "serpent-curved staff on image-right with a compact squared mantle",
        "two-handed horizontal staff crossing below the locked head",
        "rune baton on image-left and a broad tiered robe on image-right",
    ],
    "high-priest": [
        "ornate crozier upright on image-right and a broad layered mantle",
        "open scripture on image-left and a short sun scepter on image-right",
        "double-ring ceremonial staff on image-left with symmetrical vestments",
        "winged high-priest staff on image-right and a long opposite stole",
        "reliquary staff upright on image-left with a stepped ceremonial hem",
        "sunburst staff on image-right with one raised blessing hand",
        "tall straight processional staff on image-left and broad shoulder panels",
        "forward blessing scepter on image-right with asymmetric mantle layers",
        "bell crozier on image-left with a narrow central stole and wide sleeves",
        "crossbar-topped staff on image-right with compact high-tier robes",
    ],
    "sage": [
        "tall straight staff image-right and closed book image-left",
        "rune tablet image-left and short wisdom rod image-right",
        "orb wand image-right with a broad asymmetric scholarly mantle",
        "gnarled staff image-left and a compact layered robe",
        "crescent staff image-right and long opposite scroll case",
        "unrolled scroll image-left and short casting wand image-right",
        "long straight staff image-left with a square authoritative mantle",
        "short rod image-right and wide stepped robe hem",
        "double-ended staff diagonally across the lower body",
        "astrolabe-ring staff image-left with a narrow central stole",
    ],
    "agent": [
        "single dagger extended image-right and short cape image-left",
        "slender rapier image-left with the free hand drawn back",
        "compact hand crossbow image-right and fitted opposite sleeve",
        "single throwing disc image-left with a forward lean",
        "short spear image-right held diagonally outside the torso",
        "straight baton image-left and broad angular shoulder guard image-right",
        "hook blade image-right with a compact split coat",
        "small one-hand bow image-left and quiver shape image-right",
        "chain-dart handle image-right with only one short readable chain arc",
        "short sabre image-left with a long narrow rear coat panel",
    ],
    "zarvera": [
        "very long vertical lance on image-right, spearhead at top and butt at bottom, hand visibly gripping the middle",
        "long diagonal javelin rising from image-left bottom to image-right top, held clear of the face",
        "upright halberd on image-left with one simple axe-spear head and a broad opposite shoulder guard",
        "leaf-bladed spear nearly vertical on image-right with a slight inward lean and a compact split coat",
        "crescent-blade glaive upright on image-left with the free arm held close to a solid torso",
        "single throwing javelin held horizontally below the locked head, point extending image-right",
        "long partisan spear running diagonally from image-right floor toward image-left top",
        "bannerless pike perfectly vertical just right of center, with separated hand, shaft and coat",
        "three-prong military spear upright on image-left, kept coarse and readable rather than ornate",
        "broad diamond-head lance on image-right with reinforced shoulder armor and a stepped solid coat hem",
    ],
    "summoner": [
        "large ring staff image-right and a broad opposite summoning sleeve",
        "open summoning book image-left and short wand image-right",
        "single-orb staff image-left with asymmetric ritual robe panels",
        "talisman-topped staff image-right and long opposite sash",
        "crescent ritual staff image-left with a compact stepped mantle",
        "faceted crystal staff image-right and a narrow central stole",
        "bell-ended summoning rod image-left with wide opposite sleeve",
        "rolled talisman scroll image-right and short ritual baton image-left",
        "double-ring summoning staff image-right with symmetrical robe tiers",
        "forward casting wand image-left and a large cape mass image-right",
    ],
}

CHARACTER_EQUIPMENT_PALETTES = {
    "liana": [
        (109, 0, 0, 255),
        (219, 0, 0, 255),
        (255, 219, 146, 255),
        (255, 182, 0, 255),
        (73, 73, 109, 255),
        INK,
    ],
    "keith": [
        (36, 73, 146, 255),
        (36, 146, 146, 255),
        (73, 109, 182, 255),
        (182, 219, 255, 255),
        (255, 182, 0, 255),
        (109, 73, 36, 255),
        INK,
    ],
    "aaron": [
        (73, 146, 219, 255),
        (109, 182, 255, 255),
        (36, 73, 146, 255),
        (219, 219, 255, 255),
        (255, 182, 0, 255),
        (109, 109, 146, 255),
        INK,
    ],
}


def slug_for(group: tuple[int, str, int, str, str]) -> str:
    cid, name, class_id, class_slug, _ = group
    return f"{cid:02d}-{name}-{class_id:02X}-{class_slug}"


def group_by_slug(slug: str) -> tuple[int, str, int, str, str]:
    for group in GROUPS:
        if slug_for(group) == slug:
            return group
    raise SystemExit(f"Unknown group: {slug}")


def selected_groups(values: list[str] | None) -> list[tuple[int, str, int, str, str]]:
    if not values or values == ["all"]:
        return GROUPS
    return [group_by_slug(value) for value in values]


def load_entry(commander_id: int, class_id: int) -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return manifest["commanders"][str(commander_id)]["classes"][str(class_id)]


def flatten_on_neutral(image: Image.Image) -> Image.Image:
    base = Image.new("RGBA", image.size, NEUTRAL)
    base.alpha_composite(image.convert("RGBA"))
    return base.convert("RGB")


def prepare(group: tuple[int, str, int, str, str]) -> None:
    commander_id, character, class_id, class_slug, class_name = group
    directory = OUTPUT / slug_for(group)
    refs = directory / "refs"
    prompts = directory / "prompts"
    for path in (refs, prompts, directory / "raw-chroma", directory / "ai", directory / "logical16", directory / "previews"):
        path.mkdir(parents=True, exist_ok=True)

    rom_path = ROM_ROOT / str(commander_id) / f"{class_id:02X}-p1.png"
    current_path = CURRENT_ROOT / str(commander_id) / f"{class_id:02X}.png"
    rom = Image.open(rom_path).convert("RGBA")
    current = Image.open(current_path).convert("RGBA")
    entry = load_entry(commander_id, class_id)
    identity = {tuple(point) for point in entry["identity_lock_points"]}

    identity_image = Image.new("RGBA", (16, 16), TRANSPARENT)
    for point in identity:
        identity_image.putpixel(point, current.getpixel(point))

    rom.save(refs / "rom-original16.png")
    identity_image.save(refs / "identity-only16.png")
    flatten_on_neutral(rom).resize((512, 512), Image.Resampling.NEAREST).save(
        refs / "rom-original-neutral-32x.png"
    )
    flatten_on_neutral(identity_image).resize((512, 512), Image.Resampling.NEAREST).save(
        refs / "identity-only-neutral-32x.png"
    )

    records = []
    for index, direction in enumerate(DIRECTIONS[class_slug], 1):
        prompt = f"""Create one standalone retro 16-bit character sprite design, not a sheet.

REFERENCE USE
- Reference 1 is the original 16x16 ROM sprite enlarged with nearest-neighbor. Preserve its Langrisser II / Mega Drive visual language, large head-to-body ratio, facing direction and compact silhouette. Do not copy its class equipment literally.
- Reference 2 contains only the current identity-lock pixels enlarged with nearest-neighbor. Preserve the head, hair, face and eye footprint as closely as generative image output allows. The head must occupy roughly one third of the character height; never shrink it. Gray around those pixels is neutral reference background, not clothing.
- Use no other previous AI design.

SUBJECT
- Character: {character.title()}. {CHARACTER_NOTES[character]}
- Class: {class_name}. {CLASS_NOTES[class_slug]}
- Variant {index:02d} composition: {direction}.

PIXEL AND COMPOSITION RULES
- Render as an authentic logical 16x16 sprite, enlarged only by perfectly square nearest-neighbor macro pixels. Exactly sixteen logical columns and sixteen logical rows; no subpixel detail, antialiasing, blur, gradients, texture, shadows, glow or painterly rendering.
- One unmounted full-body character and exactly one connected silhouette. No companion, creature, duplicate head, pedestal, scenery, floor shadow, UI, border, text or sprite-sheet cells.
- Fill the square efficiently without cropping: hair/head or equipment reaches the top row, the main implement or cape reaches both side columns, and feet or robe reaches the bottom row. No completely unused logical row or column.
- Keep head, neck, arm, hand, torso, robe/coat, implement and feet readable as separate clustered pixel shapes. Keep the torso and lower garment solid; no transparent cavity through the center.
- Main implement is held by the character and placed outside the locked face. Avoid tangencies that merge hand, face and equipment.
- Use at most 14 opaque sprite colors. Use dark charcoal #242424 for outline instead of pure black. Do not use green on the subject and do not use magenta/purple edge pixels unless explicitly part of the character palette.
- Canvas background must be one perfectly flat, solid chroma key green {CHROMA}, edge to edge. No outline or halo made from the background color.

Deliver only the single square pixel-art sprite on the flat chroma background."""
        (prompts / f"{index:02d}.txt").write_text(prompt + "\n", encoding="utf-8")
        records.append({"index": index, "direction": direction, "prompt": f"prompts/{index:02d}.txt"})

    metadata = {
        "commander_id": commander_id,
        "character": character,
        "class_id": class_id,
        "class_hex": f"{class_id:02X}",
        "class_slug": class_slug,
        "class_name": class_name,
        "rom_reference": str(rom_path.relative_to(ROOT)),
        "identity_source": str(current_path.relative_to(ROOT)),
        "identity_lock_pixel_count": len(identity),
        "imagegen_references": [
            "refs/rom-original-neutral-32x.png",
            "refs/identity-only-neutral-32x.png",
        ],
        "variants": records,
    }
    (directory / "prompt-index.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError("source is fully transparent")
    return bbox


def rgba_distance(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    return sum((a[channel] - b[channel]) ** 2 for channel in range(3))


def sanitise_color(color: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    r, g, b, a = color
    if a == 0:
        return TRANSPARENT
    if max(r, g, b) < 28:
        return INK
    # Defensive removal of leaked key green and common generated magenta border.
    if g > r * 1.55 and g > b * 1.55 and g > 150:
        return INK
    if r > 150 and b > 150 and g < min(r, b) * 0.58:
        return (109, 73, 109, 255)
    return (r, g, b, 255)


def grid_from_ai(source: Image.Image) -> Image.Image:
    source = source.convert("RGBA")
    bbox = alpha_bbox(source)
    crop = source.crop(bbox)
    # BOX averaging is used only to measure each of the 256 logical cells; the
    # resulting cells are then hard-clustered and drawn individually.
    sampled = crop.resize((16, 16), Image.Resampling.BOX)
    output = Image.new("RGBA", (16, 16), TRANSPARENT)
    for y in range(16):
        for x in range(16):
            color = sampled.getpixel((x, y))
            if color[3] >= 28:
                output.putpixel((x, y), sanitise_color(color))
    return output


def neighbours(point: tuple[int, int], *, diagonal: bool = True) -> Iterable[tuple[int, int]]:
    x, y = point
    steps = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if diagonal:
        steps += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    for dx, dy in steps:
        nx, ny = x + dx, y + dy
        if 0 <= nx < 16 and 0 <= ny < 16:
            yield nx, ny


def components(image: Image.Image) -> list[set[tuple[int, int]]]:
    opaque = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if image.getpixel((x, y))[3] != 0
    }
    result: list[set[tuple[int, int]]] = []
    while opaque:
        start = next(iter(opaque))
        queue = [start]
        found = {start}
        opaque.remove(start)
        while queue:
            point = queue.pop()
            for neighbour in neighbours(point):
                if neighbour in opaque:
                    opaque.remove(neighbour)
                    found.add(neighbour)
                    queue.append(neighbour)
        result.append(found)
    return sorted(result, key=len, reverse=True)


def connect_components(
    image: Image.Image,
    locked_transparent: set[tuple[int, int]],
) -> None:
    for _ in range(12):
        groups = components(image)
        if len(groups) <= 1:
            return
        main, other = groups[0], groups[1]
        best = min(
            ((abs(ax - bx) + abs(ay - by), (ax, ay), (bx, by))
             for ax, ay in main for bx, by in other),
            key=lambda item: item[0],
        )
        _, start, target = best
        queue = deque([start])
        parent = {start: None}
        while queue and target not in parent:
            point = queue.popleft()
            for nxt in neighbours(point, diagonal=False):
                if nxt in parent or nxt in locked_transparent:
                    continue
                parent[nxt] = point
                queue.append(nxt)
        if target not in parent:
            return
        cursor = target
        while cursor is not None:
            if cursor not in locked_transparent and image.getpixel(cursor)[3] == 0:
                image.putpixel(cursor, INK)
            cursor = parent[cursor]


def fill_enclosed_holes(
    image: Image.Image,
    locked_transparent: set[tuple[int, int]],
) -> None:
    transparent = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if image.getpixel((x, y))[3] == 0
    }
    boundary = {p for p in transparent if p[0] in (0, 15) or p[1] in (0, 15)}
    queue = deque(boundary)
    exterior = set(boundary)
    while queue:
        point = queue.popleft()
        for nxt in neighbours(point, diagonal=False):
            if nxt in transparent and nxt not in exterior:
                exterior.add(nxt)
                queue.append(nxt)
    for point in transparent - exterior:
        if point not in locked_transparent:
            image.putpixel(point, INK)

    # Close robe/torso slits that remain connected to the outside.  A readable
    # arm/leg separation is kept; only pixels bracketed on both sides are filled.
    for y in range(9, 14):
        for x in range(4, 12):
            point = (x, y)
            if point in locked_transparent or image.getpixel(point)[3] != 0:
                continue
            left = any(image.getpixel((lx, y))[3] for lx in range(0, x))
            right = any(image.getpixel((rx, y))[3] for rx in range(x + 1, 16))
            up = image.getpixel((x, max(0, y - 1)))[3] != 0
            if left and right and up:
                image.putpixel(point, INK)


def force_canvas_use(
    image: Image.Image,
    locked_transparent: set[tuple[int, int]],
) -> None:
    opaque = [(x, y) for y in range(16) for x in range(16) if image.getpixel((x, y))[3]]
    if not opaque:
        return
    left = min(opaque, key=lambda p: (p[0], abs(p[1] - 8)))
    right = max(opaque, key=lambda p: (p[0], -abs(p[1] - 8)))
    top = min(opaque, key=lambda p: (p[1], abs(p[0] - 8)))
    bottom = max(opaque, key=lambda p: (p[1], -abs(p[0] - 8)))
    paths = [
        [(x, left[1]) for x in range(0, left[0] + 1)],
        [(x, right[1]) for x in range(right[0], 16)],
        [(top[0], y) for y in range(0, top[1] + 1)],
        [(bottom[0], y) for y in range(bottom[1], 16)],
    ]
    for path in paths:
        for point in path:
            if point not in locked_transparent and image.getpixel(point)[3] == 0:
                image.putpixel(point, INK)


def quantise_with_identity(
    image: Image.Image,
    current: Image.Image,
    identity: set[tuple[int, int]],
    character: str,
) -> None:
    identity_colors = {
        current.getpixel(point)
        for point in identity
        if current.getpixel(point)[3] != 0
    }
    identity_colors = {sanitise_color(color) for color in identity_colors}
    available = max(1, 14 - len(identity_colors))
    generated = [
        color
        for color in CHARACTER_EQUIPMENT_PALETTES[character]
        if color not in identity_colors
    ][:available]
    # Identity colors are exact only inside the lock.  In particular, do not
    # let generated hands create extra skin-colored pixels outside that mask.
    non_equipment_identity = {
        (219, 182, 109, 255),
        (255, 219, 182, 255),
        (255, 182, 146, 255),
    }
    palette = generated + [
        color for color in identity_colors
        if color not in non_equipment_identity and color not in generated
    ]
    if not palette:
        palette = [INK]
    for y in range(16):
        for x in range(16):
            point = (x, y)
            if point in identity or image.getpixel(point)[3] == 0:
                continue
            color = sanitise_color(image.getpixel(point))
            image.putpixel(point, min(palette, key=lambda target: rgba_distance(color, target)))


def restore_identity(
    image: Image.Image,
    current: Image.Image,
    identity: set[tuple[int, int]],
) -> None:
    for point in identity:
        image.putpixel(point, current.getpixel(point))


def make_variant(
    source: Image.Image,
    current: Image.Image,
    identity: set[tuple[int, int]],
    character: str,
) -> Image.Image:
    output = grid_from_ai(source)
    locked_transparent = {point for point in identity if current.getpixel(point)[3] == 0}
    restore_identity(output, current, identity)
    fill_enclosed_holes(output, locked_transparent)
    connect_components(output, locked_transparent)
    force_canvas_use(output, locked_transparent)
    connect_components(output, locked_transparent)
    quantise_with_identity(output, current, identity, character)
    restore_identity(output, current, identity)
    return output


def component_count(image: Image.Image) -> int:
    return len(components(image))


def enclosed_holes(
    image: Image.Image,
    ignored: set[tuple[int, int]] | None = None,
) -> int:
    transparent = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if image.getpixel((x, y))[3] == 0
    }
    boundary = {p for p in transparent if p[0] in (0, 15) or p[1] in (0, 15)}
    queue = deque(boundary)
    exterior = set(boundary)
    while queue:
        point = queue.popleft()
        for nxt in neighbours(point, diagonal=False):
            if nxt in transparent and nxt not in exterior:
                exterior.add(nxt)
                queue.append(nxt)
    holes = transparent - exterior
    if ignored:
        holes -= ignored
    return len(holes)


def validate(
    image: Image.Image,
    current: Image.Image,
    identity: set[tuple[int, int]],
) -> dict:
    colors = {image.getpixel((x, y)) for y in range(16) for x in range(16) if image.getpixel((x, y))[3]}
    mismatches = [point for point in identity if image.getpixel(point) != current.getpixel(point)]
    locked_transparent = {point for point in identity if current.getpixel(point)[3] == 0}
    empty_rows = [y for y in range(16) if not any(image.getpixel((x, y))[3] for x in range(16))]
    empty_columns = [x for x in range(16) if not any(image.getpixel((x, y))[3] for y in range(16))]
    result = {
        "size": list(image.size),
        "opaque_color_count": len(colors),
        "component_count_8_connected": component_count(image),
        "enclosed_transparent_holes": enclosed_holes(image, locked_transparent),
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "identity_mismatch_count": len(mismatches),
        "sha256": hashlib.sha256(image.tobytes()).hexdigest(),
    }
    result["passed"] = (
        image.size == (16, 16)
        and len(colors) <= 15
        and result["component_count_8_connected"] == 1
        and result["enclosed_transparent_holes"] == 0
        and not empty_rows
        and not empty_columns
        and not mismatches
    )
    return result


def make_preview(image: Image.Image, scale: int = 24) -> Image.Image:
    checker = Image.new("RGBA", (16, 16), (238, 238, 238, 255))
    draw = ImageDraw.Draw(checker)
    for y in range(16):
        for x in range(16):
            if (x + y) % 2:
                draw.point((x, y), fill=(205, 205, 205, 255))
    checker.alpha_composite(image)
    return checker.resize((16 * scale, 16 * scale), Image.Resampling.NEAREST)


def make_contact(directory: Path, class_name: str) -> None:
    cell = 384
    header = 48
    canvas = Image.new("RGB", (cell * 5, (cell + header) * 2), (24, 24, 24))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index in range(1, 11):
        col = (index - 1) % 5
        row = (index - 1) // 5
        preview = Image.open(directory / "previews" / f"{index:02d}.png").convert("RGB")
        canvas.paste(preview.resize((cell, cell), Image.Resampling.NEAREST), (col * cell, row * (cell + header) + header))
        draw.text((col * cell + 12, row * (cell + header) + 14), f"{index:02d}  {class_name}", fill=(245, 245, 245), font=font)
    canvas.save(directory / "contact-sheet.png")


def process(group: tuple[int, str, int, str, str]) -> None:
    commander_id, character, class_id, _, class_name = group
    directory = OUTPUT / slug_for(group)
    current = Image.open(CURRENT_ROOT / str(commander_id) / f"{class_id:02X}.png").convert("RGBA")
    entry = load_entry(commander_id, class_id)
    identity = {tuple(point) for point in entry["identity_lock_points"]}
    reports = []
    seen_hashes: set[str] = set()
    for index in range(1, 11):
        source_path = directory / "ai" / f"{index:02d}.png"
        if not source_path.exists():
            raise SystemExit(f"Missing AI source: {source_path}")
        output = make_variant(Image.open(source_path), current, identity, character)
        output_path = directory / "logical16" / f"{index:02d}.png"
        output.save(output_path)
        make_preview(output).save(directory / "previews" / f"{index:02d}.png")
        result = validate(output, current, identity)
        result.update({
            "index": index,
            "ai_source": f"ai/{index:02d}.png",
            "logical16": f"logical16/{index:02d}.png",
        })
        result["distinct_from_previous"] = result["sha256"] not in seen_hashes
        seen_hashes.add(result["sha256"])
        result["passed"] = result["passed"] and result["distinct_from_previous"]
        reports.append(result)
    report = {
        "group": slug_for(group),
        "variant_count": len(reports),
        "all_passed": all(item["passed"] for item in reports),
        "all_distinct": len(seen_hashes) == 10,
        "identity_lock_pixel_count": len(identity),
        "variants": reports,
    }
    (directory / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    make_contact(directory, class_name)


def ingest(
    group: tuple[int, str, int, str, str],
    sources: list[str],
) -> None:
    if len(sources) != 10:
        raise SystemExit("ingest requires exactly ten --source arguments")
    directory = OUTPUT / slug_for(group)
    jobs: list[tuple[Path, Path]] = []
    for index, source_value in enumerate(sources, 1):
        source = Path(source_value)
        if not source.exists():
            raise SystemExit(f"Generated source does not exist: {source}")
        raw = directory / "raw-chroma" / f"{index:02d}.png"
        alpha = directory / "ai" / f"{index:02d}.png"
        shutil.copy2(source, raw)
        jobs.append((raw, alpha))

    def remove_key(job: tuple[Path, Path]) -> None:
        raw, alpha = job
        subprocess.run(
            [
                "python3",
                str(CHROMA_HELPER),
                "--input",
                str(raw),
                "--out",
                str(alpha),
                "--auto-key",
                "border",
                "--soft-matte",
                "--transparent-threshold",
                "28",
                "--opaque-threshold",
                "96",
                "--spill-cleanup",
                "--force",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )

    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(remove_key, jobs))
    process(group)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "process", "ingest"))
    parser.add_argument("--group", action="append", help="group slug, repeatable; default all")
    parser.add_argument("--source", action="append", default=[], help="generated image path; ingest only")
    args = parser.parse_args()
    groups = selected_groups(args.group)
    for group in groups:
        if args.action == "prepare":
            prepare(group)
            print(f"prepared {slug_for(group)}")
        elif args.action == "process":
            process(group)
            print(f"processed {slug_for(group)}")
        else:
            if len(groups) != 1:
                raise SystemExit("ingest accepts exactly one --group")
            ingest(group, args.source)
            print(f"ingested {slug_for(group)}")


if __name__ == "__main__":
    main()
