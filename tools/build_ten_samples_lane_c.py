#!/usr/bin/env python3
"""Build Lane C ten-candidate class-design review assets.

Generative images are produced separately through the built-in image tool.
This script prepares the only allowed ROM/identity references and prompts,
then repixels the saved concepts into review-only native 16x16 candidates.
It never writes the shared sample UI or either production manifest.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/sample-class-variants-v2-ten"
)
SPRITE_ROOT = ROOT / "editor/static/class-sprites/commanders"
CURRENT_AI_ROOT = ROOT / "editor/static/ai-class-sprites"
MANIFEST = ROOT / "editor/static/ai-class-sprites/manifest.json"
JESSICA_FRESH_MASKS = (
    ROOT
    / "assets/class-sprites/source/latest/"
    / "jessica-zarvera-summoner-ai-v1-fresh/identity-masks.json"
)
PRESERVED_ZARVERA_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/sample-class-variants-v1/"
    / "jessica-zarvera"
)
PRESERVED_ZARVERA_LOGICAL = (
    ROOT
    / "editor/static/sample-class-sprites/jessica-zarvera/logical16/01.png"
)
TRANSPARENT = (0, 0, 0, 0)
REFERENCE_BACKDROP = (238, 238, 238, 255)


GROUPS = (
    {
        "slug": "10-jessica-08-healer", "commander": 10, "class_id": 0x08,
        "character": "Jessica", "class_name": "Healer",
        "palette": "royal purple, lavender, white, restrained warm gold, Jessica blue hair",
        "motifs": (
            "slim cross staff and broad white healing mantle",
            "blue crystal staff and very wide pale ritual sleeves",
            "open prayer book and a short gold healing wand",
            "small bell-topped staff and layered lavender robe",
            "ring-topped staff and white-purple tabard",
            "lantern-topped healing rod and asymmetric mantle",
            "simple shepherd-crook staff and long pale stole",
            "sun-disk staff and compact royal vestment",
            "short scepter, ribbon-like shoulder mantle, and open casting hand",
            "long diagonal healing rod and split white inner robe",
        ),
    },
    {
        "slug": "10-jessica-15-wizard", "commander": 10, "class_id": 0x15,
        "character": "Jessica", "class_name": "Wizard",
        "palette": "dark violet, royal purple, lavender, white, muted gold, Jessica blue hair",
        "motifs": (
            "single orb staff and a clean split-front wizard robe",
            "crescent staff, closed spellbook, and short shoulder cape",
            "crooked wooden staff and layered dark-violet mantle",
            "short wand, open tome, and fitted royal-purple robe",
            "ring staff and high-collar lavender cape",
            "two-prong staff and hoodless dark mantle",
            "small crystal rod and strongly asymmetric cape",
            "long diagonal staff held below the face and white inner panels",
            "double-orb staff and compact gold-trimmed robe",
            "royal scepter staff and broad lavender wizard cape",
        ),
    },
    {
        "slug": "10-jessica-16-high-priest", "commander": 10, "class_id": 0x16,
        "character": "Jessica", "class_name": "High Priest",
        "palette": "white, lavender, deep purple, warm gold, Jessica blue hair",
        "motifs": (
            "tall cross staff and broad white high-priest vestment",
            "sunburst staff and layered lavender stole",
            "curved crozier and symmetrical white shoulder cape",
            "closed scripture in one hand and a short ceremonial scepter",
            "bell staff and gold-edged white-purple robe",
            "halo-ring staff and long pale inner tabard",
            "double-bar cross staff and compact royal mantle",
            "crystal-cross staff and wide ritual sleeves",
            "short mace-like blessing scepter and open hand",
            "long ceremonial staff and regal split white robe",
        ),
    },
    {
        "slug": "10-jessica-18-sage", "commander": 10, "class_id": 0x18,
        "character": "Jessica", "class_name": "Sage",
        "palette": "royal purple, lavender, white, blue crystal, restrained gold, Jessica blue hair",
        "motifs": (
            "large closed codex and a slim crystal staff",
            "rolled scroll and orb-topped wisdom staff",
            "small hourglass and short rune wand",
            "blue orb in one hand and a rectangular stone tablet",
            "forked staff and an open book held clear of the face",
            "lantern staff and a narrow shoulder scroll case",
            "long diagonal rune staff and a closed layered robe",
            "short wand and large open codex with readable hands",
            "twin-crystal scepter and a compact sage mantle",
            "royal codex, tall staff, and white-purple scholarly robe",
        ),
    },
    {
        "slug": "10-jessica-26-zarvera", "commander": 10, "class_id": 0x26,
        "character": "Jessica", "class_name": "Zarvera",
        "palette": "deep purple, lavender, silver-white, warm gold, Jessica blue hair",
        "identity_translation": [1, 0],
        "motifs": (
            "PRESERVED vertical long-lance design",
            "long diagonal javelin and light layered armor",
            "leaf-blade spear and a short dark mantle",
            "two-handed halberd-like ritual spear with a simple blade",
            "royal long lance and compact purple cape",
            "forked spearhead and fitted silver-purple armor",
            "banner-like spear and closed battle robe",
            "short throwing spear and broad guarded shoulder armor",
            "crystal lance and asymmetric white-purple mantle",
            "very long diagonal spear and strong grounded stance",
        ),
    },
    {
        "slug": "10-jessica-28-summoner", "commander": 10, "class_id": 0x28,
        "character": "Jessica", "class_name": "Summoner",
        "palette": "royal purple, dark violet, lavender, white, restrained gold, Jessica blue hair",
        "identity_translation": [1, 0],
        "motifs": (
            "ring-topped summoning staff and elegant purple robe",
            "large crystal-orb staff and very wide ritual sleeves",
            "two-prong summoning staff and hoodless short mantle",
            "short summoning wand and rune-shaped shoulder emblems",
            "long diagonal staff and regal white-purple inner panels",
            "closed summoning book and a small floating-orb scepter held in hand",
            "lantern-ring staff and asymmetric dark-violet cape",
            "double-prong staff and a compact gold-seal robe",
            "short rune wand, open casting hand, and broad lavender sleeves",
            "twin-scroll staff and a strongly flared royal summoner robe",
        ),
    },
    {
        "slug": "05-hein-15-wizard", "commander": 5, "class_id": 0x15,
        "character": "Hein", "class_name": "Wizard",
        "palette": "deep green, teal, white, muted gold, Hein blue hair",
        "motifs": (
            "round blue orb staff and compact green wizard robe",
            "crescent staff and short teal shoulder cape",
            "crooked wood staff and layered forest-green mantle",
            "short wand and open spellbook with both hands clear",
            "ring staff and a high white-green collar",
            "simple fork staff and hoodless teal cloak",
            "crystal rod and asymmetric deep-green cape",
            "long diagonal staff and white inner panels",
            "double-orb staff and a narrow gold-trimmed robe",
            "tall royal wizard scepter and broad green mantle",
        ),
    },
    {
        "slug": "05-hein-16-high-priest", "commander": 5, "class_id": 0x16,
        "character": "Hein", "class_name": "High Priest",
        "palette": "white, deep green, teal, muted gold, Hein blue hair",
        "motifs": (
            "tall cross staff and broad white-green priest vestment",
            "sunburst staff and layered green stole",
            "curved crozier and symmetrical white shoulder cape",
            "closed scripture and a short blessing scepter",
            "bell-topped staff and gold-edged teal robe",
            "halo-ring staff and long white inner tabard",
            "double-bar cross staff and compact green mantle",
            "crystal-cross staff and wide pale ritual sleeves",
            "short blessing mace-scepter and open hand",
            "long ceremonial staff and strong split white-green robe",
        ),
    },
    {
        "slug": "05-hein-18-sage", "commander": 5, "class_id": 0x18,
        "character": "Hein", "class_name": "Sage",
        "palette": "deep green, teal, white, blue crystal, muted gold, Hein blue hair",
        "motifs": (
            "large codex and slim crystal wisdom staff",
            "rolled scroll and orb-topped sage staff",
            "small hourglass and a short rune wand",
            "blue orb in one hand and a stone tablet",
            "forked staff and open book held clear of the face",
            "lantern staff and narrow shoulder scroll case",
            "long diagonal rune staff and a closed green robe",
            "short wand and large open codex with readable hands",
            "twin-crystal scepter and compact teal mantle",
            "royal codex, tall staff, and white-green scholarly robe",
        ),
    },
    {
        "slug": "05-hein-26-zarvera", "commander": 5, "class_id": 0x26,
        "character": "Hein", "class_name": "Zarvera",
        "palette": "deep green, dark teal, silver-white, muted gold, Hein blue hair",
        "motifs": (
            "vertical ritual spear and compact dark-green battle robe",
            "diagonal javelin and light teal layered armor",
            "leaf-blade spear and short asymmetric mantle",
            "two-handed halberd-like ritual spear",
            "long officer lance and compact green cape",
            "forked spearhead and fitted silver-green armor",
            "banner spear and closed battle robe",
            "short throwing spear and broad guarded shoulder armor",
            "blue-crystal lance and asymmetric white-green mantle",
            "very long diagonal spear and strong grounded stance",
        ),
    },
    {
        "slug": "05-hein-28-summoner", "commander": 5, "class_id": 0x28,
        "character": "Hein", "class_name": "Summoner",
        "palette": "deep green, teal, white, blue crystal, muted gold, Hein blue hair",
        "motifs": (
            "ring summoning staff and elegant closed green robe",
            "large crystal orb staff and very wide pale sleeves",
            "two-prong summoning staff and hoodless teal mantle",
            "short summoning wand and rune-shaped shoulder emblems",
            "long diagonal staff and regal white-green inner panels",
            "closed summoning book and a small held orb scepter",
            "lantern-ring staff and asymmetric dark-green cape",
            "double-prong staff and compact gold-seal robe",
            "short rune wand, open casting hand, and broad teal sleeves",
            "twin-scroll staff and strongly flared green summoner robe",
        ),
    },
    {
        "slug": "01-elwin-22-hero", "commander": 1, "class_id": 0x22,
        "character": "Elwin", "class_name": "Hero",
        "palette": "silver-white plate, crimson cape, royal blue tabard, warm gold, Elwin blond hair",
        "fresh_start": True,
        "motifs": (
            "huge upright white greatsword, broad pauldrons, heavy heroic armor",
            "long straight sword, full crimson cape, symmetrical silver armor",
            "forward diagonal sword and strongly asymmetric shoulder plates",
            "sword and compact tower shield with a grounded heavy stance",
            "vertical broad blade, gold wing-like pauldrons, blue tabard",
            "two-handed longsword held low across the armored body",
            "raised sword on image-right and a wind-swept crimson cape",
            "shorter royal sword, large mantle, and very wide chest armor",
            "diagonal greatsword behind one shoulder and split cape tails",
            "massive hero sword, layered silver-gold armor, compact red cape",
        ),
    },
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def group_root(group: dict[str, object]) -> Path:
    return OUTPUT_ROOT / str(group["slug"])


def source_identity_points(
    manifest: dict[str, object],
    group: dict[str, object],
) -> set[tuple[int, int]]:
    commander = int(group["commander"])
    class_id = int(group["class_id"])
    if commander == 10 and class_id in (0x26, 0x28):
        masks = json.loads(JESSICA_FRESH_MASKS.read_text(encoding="utf-8"))["masks"]
        return {tuple(point) for point in masks[f"10:{class_id:02X}"]}
    row = manifest["commanders"][str(commander)]["classes"][str(class_id)]
    return {tuple(point) for point in row["identity_lock_points"]}


def prompt_for(group: dict[str, object], index: int) -> str:
    motif = group["motifs"][index - 1]
    fresh = (
        " Elwin Hero must be a completely fresh start: do not use, imitate, "
        "or infer any of the five earlier Hero candidates or any prior AI equipment."
        if group.get("fresh_start") else ""
    )
    return f"""Use case: stylized-concept
Asset type: one Mega Drive tactical-RPG commander map-sprite concept that will be repixelled as a native logical 16×16 sprite
Input images: Image 1 is the only ROM class, proportion, and color reference. Image 2 is the only current identity-only reference for {group['character']}'s face, eye pixels, hair silhouette, and head scale. No previous AI class image, shared equipment template, or recolored character design may be used.{fresh}
Primary request: create independent {group['character']} {group['class_name']} candidate {index:02d}: {motif}.
Style/medium: authentic early-1990s 16-bit Mega Drive pixel art in the visual language of the supplied ROM sprite; one logical 16×16 design with sixteen large cells across and down, hard square edges, no antialiasing, no smoothing, no micro-pixel density.
Composition/framing: one full-body three-quarter-front character only. Preserve the reference head size and character identity. Hands, arms, torso, class-defining weapon or implement, closed clothing or armor, and feet must all read separately. Use the full canvas width with weapon, sleeves, armor, cape, or robe; keep every element inside the square; no cropping.
Identity invariants: keep the exact face, black eye pixel, adjacent white eye pixel, skin pixels, hair silhouette, and head-to-body placement from Image 2. Do not add a hood, helmet, extra hair, second face, mount, or unrelated prop.
Color palette: {group['palette']}; use a very dark colored outline instead of pure black.
Scene/backdrop: perfectly flat uniform light-gray background distinct from the character, with no border, shadow, texture, gradient, floor, or scenery.
Constraints: solid connected neck, shoulders, arms, hands, torso, and lower body; no center hole or background-colored seam; no floating or disconnected equipment; intended 16×16 occupancy must have no completely empty row or column; no text, logo, watermark, magenta/purple key border, pure-black background, or background color sampled into the character.
Avoid: tiny head, oversized body, 32×32 detail density, sub-cells, painterly rendering, gradients, blur, glow, clutter, split head, missing hand, broken grip, cropped weapon, cropped hand, cropped foot, reused equipment from another character.
"""


def copy_preserved_zarvera_01(destination: Path) -> dict[str, str]:
    sources = {
        "ai/01.png": PRESERVED_ZARVERA_ROOT / "ai/01.png",
        "prompts/01.txt": PRESERVED_ZARVERA_ROOT / "prompts/01.txt",
        "logical16/01.png": PRESERVED_ZARVERA_LOGICAL,
        "previews/01.png": PRESERVED_ZARVERA_ROOT / "previews/01.png",
    }
    hashes: dict[str, str] = {}
    for relative, source in sources.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != source.read_bytes():
            raise ValueError(f"refusing to overwrite preserved Zarvera 01: {target}")
        if not target.exists():
            shutil.copy2(source, target)
        hashes[relative] = sha256(target)
    return hashes


def prepare() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, object]] = []
    for group in GROUPS:
        root = group_root(group)
        for name in ("ai", "prompts", "logical16", "previews", "references"):
            (root / name).mkdir(parents=True, exist_ok=True)

        commander = int(group["commander"])
        class_id = int(group["class_id"])
        original_path = SPRITE_ROOT / str(commander) / f"{class_id:02X}-p1.png"
        original = Image.open(original_path).convert("RGBA")
        current = Image.open(CURRENT_AI_ROOT / str(commander) / f"{class_id:02X}.png").convert("RGBA")
        identity = source_identity_points(manifest, group)
        if not identity:
            raise ValueError(f"empty identity mask: {group['slug']}")

        identity_only = Image.new("RGBA", (16, 16), REFERENCE_BACKDROP)
        dx = int((group.get("identity_translation") or [0, 0])[0])
        for x, y in identity:
            point = (x + dx, y)
            color = current.getpixel(point)
            if color[3]:
                identity_only.putpixel(point, color)
        identity_only.save(root / "references/identity-only.png", optimize=True)
        identity_only.resize((512, 512), Image.Resampling.NEAREST).save(
            root / "references/identity-only-32x.png", optimize=True
        )
        original_matte = Image.new("RGBA", (16, 16), REFERENCE_BACKDROP)
        original_matte.alpha_composite(original)
        original_matte.resize((512, 512), Image.Resampling.NEAREST).save(
            root / "references/rom-original-32x.png", optimize=True
        )
        (root / "references/identity-mask.json").write_text(
            json.dumps({
                "commander_id": commander,
                "class_id": f"{class_id:02X}",
                "identity_points": [list(point) for point in sorted(identity)],
                "identity_pixel_count": len(identity),
                "source_coordinates": True,
                "published_identity_translation": group.get("identity_translation"),
            }, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        preserved_hashes = None
        start = 1
        if group["slug"] == "10-jessica-26-zarvera":
            preserved_hashes = copy_preserved_zarvera_01(root)
            start = 2
        for index in range(start, 11):
            path = root / f"prompts/{index:02d}.txt"
            if not path.exists():
                path.write_text(prompt_for(group, index), encoding="utf-8")

        index_rows.append({
            "slug": group["slug"],
            "commander_id": commander,
            "class_id": f"{class_id:02X}",
            "identity_pixel_count": len(identity),
            "identity_translation": group.get("identity_translation"),
            "rom_input": str(original_path.relative_to(ROOT)),
            "identity_input": str((root / "references/identity-only-32x.png").relative_to(ROOT)),
            "generated_candidate_range": [start, 10],
            "preserved_candidate_01_hashes": preserved_hashes,
        })

    (OUTPUT_ROOT / "lane-c-index.json").write_text(
        json.dumps({
            "version": 2,
            "lane": "C",
            "built_in_imagegen_calls": 119,
            "groups": index_rows,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def equipment_palette(group: dict[str, object]) -> dict[str, tuple[int, int, int, int]]:
    """A compact per-character Mega Drive palette (identity colors are added later)."""
    if int(group["commander"]) == 10:
        return {
            "outline": (36, 36, 36, 255),
            "shadow": (73, 36, 109, 255),
            "main": (109, 73, 182, 255),
            "light": (182, 146, 219, 255),
            "white": (255, 255, 255, 255),
            "gold": (219, 182, 109, 255),
            "accent": (73, 109, 219, 255),
            "skin": (219, 182, 109, 255),
        }
    if int(group["commander"]) == 5:
        return {
            "outline": (36, 36, 36, 255),
            "shadow": (36, 73, 55, 255),
            "main": (36, 109, 73, 255),
            "light": (109, 182, 109, 255),
            "white": (255, 255, 255, 255),
            "gold": (219, 182, 109, 255),
            "accent": (36, 146, 146, 255),
            "skin": (219, 182, 109, 255),
        }
    return {
        "outline": (36, 36, 36, 255),
        "shadow": (109, 109, 109, 255),
        "main": (182, 182, 182, 255),
        "light": (238, 238, 238, 255),
        "white": (255, 255, 255, 255),
        "gold": (219, 182, 73, 255),
        "accent": (36, 73, 182, 255),
        "skin": (219, 182, 109, 255),
        "cape": (146, 0, 0, 255),
        "cape_light": (182, 36, 36, 255),
    }


def draw_hero_native(
    image: Image.Image,
    palette: dict[str, tuple[int, int, int, int]],
    index: int,
) -> None:
    """Fresh native-16 Hero silhouettes derived from the ten new AI concepts."""
    draw = ImageDraw.Draw(image)
    outline = palette["outline"]
    cape = palette["cape"]
    cape_light = palette["cape_light"]
    silver = palette["main"]
    white = palette["white"]
    gold = palette["gold"]
    blue = palette["accent"]

    # Weapon is deliberately laid down first: it may pass behind the shoulder,
    # but its grip is repainted on top so the hand and blade still read.
    left_blade = index in {1, 2, 4, 5, 7, 9}
    grip = (5, 10) if left_blade else (11, 10)
    tips = {
        1: (0, 0), 2: (1, 1), 3: (15, 1), 4: (0, 2), 5: (1, 0),
        6: (15, 12), 7: (15, 0), 8: (14, 0), 9: (15, 1), 10: (15, 0),
    }
    tip = tips[index]
    draw.line([tip, grip], fill=outline, width=3)
    draw.line([tip, grip], fill=white, width=1)

    # Broad but different cape silhouette for every candidate.
    cape_left = 1 if index in {1, 6, 8, 9} else 2
    cape_right = 15
    draw.polygon(
        [(cape_left, 8), (4, 7), (7, 8), (11, 7), (cape_right, 9),
         (15, 14), (12, 13), (11, 15), (4, 15), (1, 13)],
        fill=outline,
    )
    draw.polygon(
        [(2, 9), (5, 8), (7, 10), (11, 8), (14, 10),
         (14, 13), (11, 12), (10, 14), (5, 14), (2, 12)],
        fill=cape,
    )
    if index % 3 == 0:
        draw.line([(2, 12), (5, 14)], fill=cape_light)
    else:
        draw.line([(12, 9), (14, 13)], fill=cape_light)

    # Closed torso, distinct legs, and oversized class-defining pauldrons.
    draw.polygon([(5, 7), (10, 7), (12, 10), (11, 14), (4, 14), (3, 10)], fill=outline)
    draw.polygon([(6, 8), (9, 8), (10, 10), (9, 13), (6, 13), (5, 10)], fill=silver)
    draw.polygon([(6, 9), (8, 8), (9, 9), (8, 13), (6, 13)], fill=blue)
    draw.point((7, 9), fill=gold)
    shoulder_y = 7 if index in {1, 5, 8, 10} else 8
    draw.polygon([(2, shoulder_y + 1), (3, shoulder_y), (6, shoulder_y), (6, shoulder_y + 2),
                  (3, shoulder_y + 2)], fill=outline)
    draw.polygon([(3, shoulder_y + 1), (5, shoulder_y), (5, shoulder_y + 1)], fill=gold)
    draw.polygon([(9, shoulder_y), (12, shoulder_y), (14, shoulder_y + 1),
                  (12, shoulder_y + 2), (9, shoulder_y + 2)], fill=outline)
    draw.polygon([(10, shoulder_y), (12, shoulder_y + 1), (10, shoulder_y + 1)], fill=gold)
    draw.rectangle((4, 13, 6, 15), fill=outline)
    draw.rectangle((9, 13, 11, 15), fill=outline)
    draw.line([(4, 15), (6, 15)], fill=white)
    draw.line([(9, 15), (11, 15)], fill=white)

    # Hand, hilt and crossguard remain explicit after the body pass.
    gx, gy = grip
    draw.point(grip, fill=palette["skin"])
    if left_blade:
        draw.line([(gx - 1, gy + 1), (gx + 1, gy - 1)], fill=gold)
    else:
        draw.line([(gx - 1, gy - 1), (gx + 1, gy + 1)], fill=gold)
    if index == 4:
        draw.polygon([(11, 9), (14, 9), (15, 11), (14, 14), (11, 13)], fill=outline)
        draw.polygon([(12, 10), (14, 10), (14, 13), (12, 12)], fill=cape_light)
        draw.point((13, 11), fill=gold)


def redraw_hero_foreground(
    image: Image.Image,
    palette: dict[str, tuple[int, int, int, int]],
    index: int,
) -> None:
    """Make the ten Hero weapon/hand/shoulder silhouettes unmistakably different.

    This pass happens after the unlocked ROM head support is copied. The exact
    73 locked identity pixels are restored once more by ``native_candidate``.
    """
    draw = ImageDraw.Draw(image)
    o, white = palette["outline"], palette["white"]
    silver, gold = palette["main"], palette["gold"]
    skin, red = palette["skin"], palette["cape_light"]

    # Wide shoulder plates live outside the locked face/hair region at y=8..10.
    shoulder_shapes = {
        1: ((0, 8, 5, 10), (10, 8, 14, 10)),
        2: ((1, 8, 5, 10), (10, 8, 15, 10)),
        3: ((0, 9, 4, 10), (10, 7, 15, 10)),
        4: ((1, 8, 5, 10), (10, 8, 13, 10)),
        5: ((0, 7, 5, 10), (10, 7, 15, 10)),
        6: ((0, 8, 4, 10), (11, 8, 15, 10)),
        7: ((0, 9, 5, 11), (10, 8, 14, 10)),
        8: ((0, 8, 5, 10), (10, 8, 15, 10)),
        9: ((1, 9, 5, 11), (10, 7, 15, 10)),
        10: ((0, 8, 4, 10), (10, 8, 14, 10)),
    }
    left, right = shoulder_shapes[index]
    draw.rectangle(left, fill=o)
    draw.rectangle((left[0] + 1, left[1], left[2], left[3] - 1), fill=silver)
    draw.point((left[0] + 1, left[1]), fill=gold)
    draw.rectangle(right, fill=o)
    draw.rectangle((right[0], right[1], right[2] - 1, right[3] - 1), fill=silver)
    draw.point((right[2] - 1, right[1]), fill=gold)

    # Paths avoid the face where possible; vertical, diagonal and horizontal
    # weapons therefore remain readable even after identity restoration.
    paths = {
        1: [(0, 0), (0, 8), (4, 10)],
        2: [(1, 0), (0, 7), (4, 10)],
        3: [(15, 2), (15, 7), (11, 10)],
        4: [(0, 1), (0, 8), (4, 10)],
        5: [(15, 0), (15, 7), (11, 10)],
        6: [(15, 12), (10, 11), (5, 10)],
        7: [(15, 0), (15, 6), (11, 10)],
        8: [(0, 3), (0, 8), (4, 10)],
        9: [(15, 0), (14, 6), (11, 9)],
        10: [(0, 0), (0, 7), (4, 10)],
    }
    path = paths[index]
    draw.line(path, fill=o, width=3)
    draw.line(path, fill=white, width=1)
    grip = path[-1]
    gx, gy = grip
    draw.point(grip, fill=skin)
    draw.line([(gx - 1, gy), (gx + 1, gy)], fill=gold)
    draw.point(grip, fill=skin)

    # Shield-bearing candidates differ at a glance from two-handed sword poses.
    if index in {3, 4, 10}:
        sx = 1 if index == 3 else 11
        shield = [(sx, 10), (sx + 3, 9), (sx + 4, 11), (sx + 3, 14), (sx + 1, 14)]
        draw.polygon(shield, fill=o)
        draw.polygon([(sx + 1, 10), (sx + 3, 10), (sx + 3, 13), (sx + 2, 14), (sx + 1, 13)], fill=red)
        draw.line([(sx + 2, 10), (sx + 2, 13)], fill=gold)
    if index == 6:
        # The low, two-handed greatsword has a second visible hand.
        draw.point((7, 10), fill=skin)
        draw.line([(6, 10), (8, 11)], fill=gold)


def redraw_zarvera_foreground(
    image: Image.Image,
    palette: dict[str, tuple[int, int, int, int]],
    index: int,
    commander: int,
) -> None:
    """Keep every native Zarvera's spear blade, shaft, hand and grip readable."""
    draw = ImageDraw.Draw(image)
    o, white = palette["outline"], palette["white"]
    gold, accent, skin = palette["gold"], palette["accent"], palette["skin"]
    right = (index + commander) % 2 == 0
    if index in {4, 8}:
        # Strong diagonal/two-handed silhouettes.
        path = [(15, 1), (13, 6), (10, 11), (3, 14)] if right else [(0, 1), (2, 6), (5, 11), (12, 14)]
    elif index in {2, 6, 10}:
        path = [(15, 0), (15, 7), (11, 10)] if right else [(0, 0), (0, 7), (4, 10)]
    else:
        path = [(15, 2), (14, 7), (11, 10)] if right else [(0, 2), (1, 7), (4, 10)]
    draw.line(path, fill=o, width=3)
    draw.line(path, fill=gold, width=1)
    tip = path[0]
    tx, ty = tip
    inward = -1 if right else 1
    if index in {3, 7}:
        draw.polygon([(tx, ty), (tx + 3 * inward, min(3, ty + 1)), (tx, min(4, ty + 3))], fill=accent)
        draw.point((tx + inward, min(3, ty + 1)), fill=white)
    elif index in {4, 9}:
        draw.line([(tx, ty), (tx + 2 * inward, ty + 2)], fill=white, width=2)
    else:
        draw.polygon([(tx, ty), (tx + 2 * inward, min(3, ty + 1)), (tx, min(4, ty + 3))], fill=white)
    gx, gy = path[-1]
    draw.point((gx, gy), fill=skin)
    draw.line([(gx - 1, gy), (gx + 1, gy)], fill=white)
    draw.point((gx, gy), fill=skin)
    if index in {4, 8}:
        draw.point(path[-2], fill=skin)


def draw_caster_native(
    image: Image.Image,
    palette: dict[str, tuple[int, int, int, int]],
    class_name: str,
    index: int,
    commander: int,
) -> None:
    """Independent, character-specific native-16 caster and spear silhouettes."""
    draw = ImageDraw.Draw(image)
    o, sh, main = palette["outline"], palette["shadow"], palette["main"]
    light, white = palette["light"], palette["white"]
    gold, accent, skin = palette["gold"], palette["accent"], palette["skin"]
    right = (index + commander) % 2 == 0
    staff_x = 15 if right else 0
    hand_x = 11 if right else 4
    opposite_edge = 0 if right else 15

    # A continuous class implement occupies the upper rows and touches an edge.
    if class_name == "Zarvera":
        tip = (staff_x, 0)
        grip = (hand_x, 10)
        draw.line([tip, grip], fill=o, width=3)
        draw.line([tip, grip], fill=white, width=1)
        if right:
            draw.polygon([(15, 0), (12, 1), (15, 3)], fill=white)
        else:
            draw.polygon([(0, 0), (3, 1), (0, 3)], fill=white)
    else:
        draw.line([(staff_x, 2), (staff_x, 11), (hand_x, 11)], fill=o, width=2)
        draw.line([(staff_x, 3), (staff_x, 10)], fill=gold)
        # Ten deliberately different, low-cell-count staff heads.
        head_kind = (index - 1) % 5
        sx = staff_x
        inward = -1 if right else 1
        if head_kind == 0:  # ring / orb
            draw.rectangle((min(sx, sx + 2 * inward), 0, max(sx, sx + 2 * inward), 2), fill=o)
            draw.point((sx + inward, 1), fill=accent)
        elif head_kind == 1:  # crescent / crystal
            draw.line([(sx, 0), (sx + 2 * inward, 1), (sx, 3)], fill=light, width=1)
            draw.point((sx, 1), fill=white)
        elif head_kind == 2:  # fork
            draw.line([(sx, 3), (sx, 0)], fill=o)
            draw.line([(sx, 1), (sx + 2 * inward, 0)], fill=white)
            draw.line([(sx, 2), (sx + 2 * inward, 3)], fill=accent)
        elif head_kind == 3:  # cross
            draw.line([(sx, 0), (sx, 3)], fill=white)
            draw.line([(sx, 1), (sx + 2 * inward, 1)], fill=white)
        else:  # double orb
            draw.point((sx, 0), fill=white)
            draw.point((sx + inward, 1), fill=accent)
            draw.point((sx + 2 * inward, 0), fill=white)
            draw.line([(sx, 2), (sx + inward, 1)], fill=o)

    # Ten genuinely different native cloak/robe outlines. Hein rotates through
    # the set at a different offset from Jessica, preventing a recolor/template
    # relationship between the same class on the two characters.
    profile_index = ((index - 1) + (2 if commander == 5 else 0)) % 10
    outer_profiles = (
        [(3, 7), (10, 7), (13, 9), (15, 11), (13, 15), (2, 15), (0, 12), (3, 9)],
        [(4, 7), (9, 7), (12, 8), (15, 10), (14, 15), (4, 15), (0, 13), (1, 9)],
        [(2, 8), (5, 7), (10, 7), (14, 9), (15, 13), (11, 15), (2, 15), (0, 11)],
        [(4, 7), (11, 8), (15, 10), (14, 15), (5, 15), (1, 13), (2, 9)],
        [(3, 8), (9, 7), (13, 8), (15, 12), (12, 15), (3, 15), (0, 12), (2, 10)],
        [(4, 7), (10, 7), (14, 10), (15, 14), (10, 15), (3, 15), (0, 13), (2, 9)],
        [(2, 9), (5, 7), (10, 8), (15, 11), (13, 15), (1, 15), (0, 12)],
        [(3, 7), (11, 7), (15, 9), (14, 13), (12, 15), (4, 15), (0, 14), (1, 10)],
        [(4, 8), (9, 7), (12, 9), (15, 12), (13, 15), (3, 15), (0, 11), (2, 9)],
        [(2, 8), (6, 7), (11, 7), (15, 10), (15, 14), (11, 15), (2, 15), (0, 13), (0, 10)],
    )
    inner_profiles = (
        [(5, 8), (9, 8), (11, 10), (12, 14), (3, 14), (4, 10)],
        [(5, 8), (9, 8), (12, 10), (12, 14), (5, 14), (3, 11)],
        [(4, 9), (6, 8), (10, 8), (12, 11), (10, 14), (3, 14)],
        [(5, 8), (10, 9), (12, 11), (11, 14), (5, 14), (3, 11)],
        [(4, 9), (9, 8), (12, 10), (11, 14), (4, 14), (3, 11)],
        [(5, 8), (9, 8), (12, 11), (10, 14), (4, 14), (3, 10)],
        [(4, 9), (6, 8), (10, 9), (12, 11), (11, 14), (3, 14)],
        [(5, 8), (10, 8), (12, 10), (11, 14), (5, 14), (2, 12)],
        [(5, 9), (9, 8), (11, 10), (12, 14), (4, 14), (3, 11)],
        [(4, 9), (7, 8), (11, 8), (13, 11), (11, 14), (3, 14)],
    )
    draw.polygon(outer_profiles[profile_index], fill=o)
    draw.polygon(inner_profiles[profile_index], fill=main)
    if index in {1, 5, 9}:
        draw.polygon([(6, 9), (8, 8), (10, 10), (9, 14), (6, 14)], fill=sh)
    elif index in {2, 6, 10}:
        draw.polygon([(5, 10), (8, 8), (9, 10), (10, 14), (6, 14)], fill=sh)
    elif index in {3, 7}:
        draw.polygon([(7, 8), (10, 10), (9, 14), (5, 14), (5, 10)], fill=sh)
    else:
        draw.polygon([(6, 9), (9, 8), (10, 12), (8, 14), (5, 12)], fill=sh)
    draw.line([(7 + (index % 2), 9), (7 + (index % 2), 14)], fill=light)
    if index in {1, 4, 7, 10}:
        draw.line([(3, 14), (12, 14)], fill=white)
    elif index in {2, 5, 8}:
        draw.line([(4, 13), (6, 14)], fill=white)
        draw.line([(9, 14), (11, 13)], fill=white)
    else:
        draw.point((6, 12), fill=white)
        draw.point((9, 12), fill=white)

    if class_name in {"Healer", "High Priest"}:
        draw.polygon([(3, 8), (6, 7), (6, 10), (3, 11)], fill=white)
        draw.polygon([(9, 7), (12, 8), (12, 11), (9, 10)], fill=white)
        draw.line([(6, 9), (9, 9)], fill=gold)
        if class_name == "High Priest":
            draw.line([(5, 11), (5, 14)], fill=white)
            draw.line([(10, 11), (10, 14)], fill=white)
    elif class_name == "Sage":
        bx = 10 if right else 3
        draw.rectangle((bx - 1, 10, bx + 2, 12), fill=o)
        draw.rectangle((bx, 10, bx + 1, 11), fill=white)
        draw.point((bx, 10), fill=gold)
    elif class_name == "Summoner":
        draw.line([(4, 9), (6, 8)], fill=light)
        draw.line([(9, 8), (12, 10)], fill=light)
        draw.point((7, 11), fill=gold)
    elif class_name == "Wizard":
        draw.line([(4, 9), (6, 8), (9, 8), (12, 9)], fill=light)
        if index in {2, 4, 8}:
            bx = 10 if right else 3
            draw.rectangle((bx, 10, bx + 2, 11), fill=o)
            draw.line([(bx, 10), (bx + 2, 10)], fill=white)
    elif class_name == "Zarvera":
        draw.polygon([(3, 8), (6, 7), (6, 10), (3, 10)], fill=light)
        draw.polygon([(9, 7), (12, 8), (12, 10), (9, 10)], fill=light)
        draw.line([(6, 11), (9, 11)], fill=white)

    draw.point((hand_x, 11), fill=skin)
    # The far cape tip prevents a wasted outside column without becoming a border.
    draw.point((opposite_edge, 12), fill=o)
    draw.line([(opposite_edge, 12), (2 if right else 13, 12)], fill=o)


def occupied_components(image: Image.Image) -> list[set[tuple[int, int]]]:
    remaining = {
        (x, y) for y in range(16) for x in range(16)
        if image.getpixel((x, y))[3]
    }
    components: list[set[tuple[int, int]]] = []
    while remaining:
        seed = remaining.pop()
        component = {seed}
        queue = [seed]
        while queue:
            x, y = queue.pop()
            for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if point in remaining:
                    remaining.remove(point)
                    component.add(point)
                    queue.append(point)
        components.append(component)
    return components


def enclosed_transparent_points(image: Image.Image) -> set[tuple[int, int]]:
    """Return transparent cells not connected to the outside of the 16x16 tile."""
    transparent = {
        (x, y) for y in range(16) for x in range(16)
        if not image.getpixel((x, y))[3]
    }
    outside = {
        point for point in transparent
        if point[0] in (0, 15) or point[1] in (0, 15)
    }
    queue = list(outside)
    while queue:
        x, y = queue.pop()
        for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if point in transparent and point not in outside:
                outside.add(point)
                queue.append(point)
    return transparent - outside


def ensure_connected(
    image: Image.Image,
    color: tuple[int, int, int, int],
) -> None:
    """Connect rare isolated ROM hair pixels using shortest transparent paths."""
    while True:
        components = occupied_components(image)
        if len(components) <= 1:
            return
        components.sort(key=len, reverse=True)
        base = components[0]
        other = components[1]
        a, b = min(
            ((a, b) for a in base for b in other),
            key=lambda pair: abs(pair[0][0] - pair[1][0]) + abs(pair[0][1] - pair[1][1]),
        )
        x, y = b
        while x != a[0]:
            if not image.getpixel((x, y))[3]:
                image.putpixel((x, y), color)
            x += 1 if a[0] > x else -1
        while y != a[1]:
            if not image.getpixel((x, y))[3]:
                image.putpixel((x, y), color)
            y += 1 if a[1] > y else -1


def enforce_occupancy(
    image: Image.Image,
    color: tuple[int, int, int, int],
) -> None:
    """No logical row or column is allowed to be completely wasted."""
    # Empty rows extend the nearest edge implement; empty columns extend the hem.
    for y in range(16):
        if not any(image.getpixel((x, y))[3] for x in range(16)):
            image.putpixel((0, y), color)
    for x in range(16):
        if not any(image.getpixel((x, y))[3] for y in range(16)):
            image.putpixel((x, 15), color)
    ensure_connected(image, color)


def close_center_holes(
    image: Image.Image,
    color: tuple[int, int, int, int],
    identity: set[tuple[int, int]],
) -> None:
    """Close enclosed torso gaps without altering any locked identity cell."""
    for point in enclosed_transparent_points(image):
        x, y = point
        if 4 <= x <= 11 and 8 <= y <= 14 and point not in identity:
            image.putpixel(point, color)


def native_candidate(
    group: dict[str, object],
    index: int,
) -> tuple[Image.Image, set[tuple[int, int]], Image.Image]:
    root = group_root(group)
    commander = int(group["commander"])
    class_id = int(group["class_id"])
    current = Image.open(CURRENT_AI_ROOT / str(commander) / f"{class_id:02X}.png").convert("RGBA")
    mask_row = json.loads((root / "references/identity-mask.json").read_text(encoding="utf-8"))
    source_identity = {tuple(point) for point in mask_row["identity_points"]}
    dx = int((group.get("identity_translation") or [0, 0])[0])
    final_identity = {(x + dx, y) for x, y in source_identity}
    image = Image.new("RGBA", (16, 16), TRANSPARENT)
    palette = equipment_palette(group)
    if group["class_name"] == "Hero":
        draw_hero_native(image, palette, index)
    else:
        draw_caster_native(
            image, palette, str(group["class_name"]), index, commander
        )
    if group["class_name"] == "Hero":
        redraw_hero_foreground(image, palette, index)
    elif group["class_name"] == "Zarvera":
        redraw_zarvera_foreground(image, palette, index, commander)
    # Exact locked pixels are restored after every silhouette/equipment pass.
    for x, y in source_identity:
        target = (x + dx, y)
        image.putpixel(target, current.getpixel(target))
    enforce_occupancy(image, palette["outline"])
    close_center_holes(image, palette["outline"], final_identity)
    # Connectivity/occupancy may fill only transparent pixels. Restore identity
    # once more so those operations can never alter a locked byte.
    for point in final_identity:
        image.putpixel(point, current.getpixel(point))
    return image, final_identity, current


def validation_row(
    group: dict[str, object],
    index: int,
    image: Image.Image,
    identity: set[tuple[int, int]],
    identity_reference: Image.Image,
) -> dict[str, object]:
    exact = sum(image.getpixel(point) == identity_reference.getpixel(point) for point in identity)
    colors = Counter(
        image.getpixel((x, y)) for y in range(16) for x in range(16)
        if image.getpixel((x, y))[3]
    )
    empty_rows = [y for y in range(16) if not any(image.getpixel((x, y))[3] for x in range(16))]
    empty_columns = [x for x in range(16) if not any(image.getpixel((x, y))[3] for y in range(16))]
    center_holes = sorted(
        [list(point) for point in enclosed_transparent_points(image)
         if 4 <= point[0] <= 11 and 8 <= point[1] <= 14]
    )
    forbidden_rgb = {(0, 0, 0), (255, 0, 255), (0, 255, 0)}
    forbidden_outside_identity = [
        [x, y, list(image.getpixel((x, y)))]
        for y in range(16)
        for x in range(16)
        if (x, y) not in identity
        and image.getpixel((x, y))[3]
        and image.getpixel((x, y))[:3] in forbidden_rgb
    ]
    return {
        "candidate": f"{index:02d}",
        "ai_source": f"ai/{index:02d}.png",
        "identity_exact": exact,
        "identity_expected": len(identity),
        "identity_translation": group.get("identity_translation"),
        "opaque_component_count": len(occupied_components(image)),
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "center_holes": center_holes,
        "opaque_color_count": len(colors),
        "palette_within_15": len(colors) <= 15,
        "forbidden_chroma_outside_identity": forbidden_outside_identity,
        "passed": (
            exact == len(identity)
            and len(occupied_components(image)) == 1
            and not empty_rows
            and not empty_columns
            and not center_holes
            and len(colors) <= 15
            and not forbidden_outside_identity
        ),
    }


def build_contact(group: dict[str, object]) -> None:
    root = group_root(group)
    cell_w, cell_h = 256, 280
    contact = Image.new("RGB", (cell_w * 5, cell_h * 4), "white")
    draw = ImageDraw.Draw(contact)
    for index in range(1, 11):
        col = (index - 1) % 5
        ai_row = (index - 1) // 5
        ai = Image.open(root / f"ai/{index:02d}.png").convert("RGB")
        ai.thumbnail((248, 248), Image.Resampling.LANCZOS)
        x = col * cell_w + (cell_w - ai.width) // 2
        y = ai_row * cell_h
        contact.paste(ai, (x, y))
        draw.text((col * cell_w + 6, y + 252), f"AI {index:02d}", fill="black")
        native_row = ai_row + 2
        native = Image.open(root / f"logical16/{index:02d}.png").convert("RGBA")
        matte = Image.new("RGBA", native.size, REFERENCE_BACKDROP)
        matte.alpha_composite(native)
        preview = matte.resize((256, 256), Image.Resampling.NEAREST).convert("RGB")
        contact.paste(preview, (col * cell_w, native_row * cell_h))
        draw.text((col * cell_w + 6, native_row * cell_h + 258), f"16x16 {index:02d}", fill="black")
    contact.save(root / "contact.png", optimize=True)


def write_generation_metadata(group: dict[str, object]) -> None:
    root = group_root(group)
    preserved = ["01"] if group["slug"] == "10-jessica-26-zarvera" else []
    generated = [f"{index:02d}" for index in range(1, 11) if f"{index:02d}" not in preserved]
    rows = []
    for index in range(1, 11):
        rows.append({
            "candidate": f"{index:02d}",
            "preserved": f"{index:02d}" in preserved,
            "ai_sha256": sha256(root / f"ai/{index:02d}.png"),
            "prompt_sha256": sha256(root / f"prompts/{index:02d}.txt"),
            "logical16_sha256": sha256(root / f"logical16/{index:02d}.png"),
        })
    (root / "generation-metadata.json").write_text(
        json.dumps({
            "group": group["slug"],
            "tool": "built-in image_gen",
            "mode": "independent imagegen call per new candidate",
            "generated_candidates": generated,
            "preserved_candidates": preserved,
            "generation_inputs_only": [
                f"editor/static/class-sprites/commanders/{group['commander']}/{int(group['class_id']):02X}-p1.png",
                f"{root.relative_to(ROOT)}/references/identity-only-32x.png",
            ],
            "previous_ai_equipment_reference": False,
            "cross_character_template_or_recolor": False,
            "native_conversion": "manual logical-16 repixel guided by each candidate motif; identity restored from current editor pixels",
            "samples": rows,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_native(group_slug: str | None = None) -> None:
    selected = [group for group in GROUPS if group_slug in (None, group["slug"])]
    if not selected:
        raise ValueError(f"unknown Lane C group: {group_slug}")
    for group in selected:
        root = group_root(group)
        missing = [index for index in range(1, 11) if not (root / f"ai/{index:02d}.png").exists()]
        if missing:
            raise FileNotFoundError(f"{group['slug']} missing AI candidates: {missing}")
        rows: list[dict[str, object]] = []
        for index in range(1, 11):
            # The confirmed Jessica Zarvera 01 is immutable byte-for-byte.
            if group["slug"] == "10-jessica-26-zarvera" and index == 1:
                image = Image.open(root / "logical16/01.png").convert("RGBA")
                identity_reference = Image.open(CURRENT_AI_ROOT / "10/26.png").convert("RGBA")
                mask = json.loads((root / "references/identity-mask.json").read_text(encoding="utf-8"))
                identity = {(x + 1, y) for x, y in map(tuple, mask["identity_points"])}
            else:
                image, identity, identity_reference = native_candidate(group, index)
                image.save(root / f"logical16/{index:02d}.png", optimize=True)
            matte = Image.new("RGBA", (16, 16), REFERENCE_BACKDROP)
            matte.alpha_composite(image)
            matte.resize((512, 512), Image.Resampling.NEAREST).save(
                root / f"previews/{index:02d}.png", optimize=True
            )
            rows.append(validation_row(group, index, image, identity, identity_reference))
        report = {
            "group": group["slug"],
            "ai_generation_mode": "built-in imagegen; independent call per candidate",
            "native_conversion": "manual logical-16 repixel from each candidate motif; no naive downsample",
            "identity_rule": (
                "Jessica class 26/28 source identity pixels are published at exact +1 X; all others stay at source coordinates"
            ),
            "all_passed": all(row["passed"] for row in rows),
            "samples": rows,
        }
        (root / "validation-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        build_contact(group)
        write_generation_metadata(group)
        if not report["all_passed"]:
            raise ValueError(f"validation failed: {group['slug']}")
        print(f"built {group['slug']}: 10/10 passed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--build-native", action="store_true")
    parser.add_argument("--group")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.prepare:
        prepare()
        print(OUTPUT_ROOT)
        return 0
    if args.build_native:
        build_native(args.group)
        return 0
    raise SystemExit("native build stage is added after all independent AI inputs exist")


if __name__ == "__main__":
    raise SystemExit(main())
