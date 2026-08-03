#!/usr/bin/env python3
"""Share Elwin's retouched Mage/Archmage silhouettes and rebuild Hein Sorcerer."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import identity_locked_character_sprite


SOURCE_DIR = (
    ROOT / "docs/assets/ai-class-source/latest/shared-elwin-magic-v1"
)
SORCERER_DIR = (
    ROOT / "docs/assets/ai-class-source/latest/hein-warlock-sorcerer-v1"
)
PALADIN_DIR = (
    ROOT / "docs/assets/ai-class-source/latest/hein-magic-knight-paladin-v1"
)
MANIFEST_PATH = ROOT / "editor/static/ai-class-sprites/manifest.json"
ROM_SPRITE_DIR = ROOT / "editor/static/class-sprites/commanders"
COMMANDER_IDS = (1, 2, 3, 4, 5, 8, 9, 10)
TRANSPARENT = (0, 0, 0, 0)
INK = (36, 36, 36, 255)
RESAMPLING = getattr(Image, "Resampling", Image)

ELWIN_RED = (146, 0, 0, 255)
ELWIN_DARK_RED = (109, 0, 0, 255)
ELWIN_BLUE = (0, 73, 219, 255)
ELWIN_LIGHT_BLUE = (73, 109, 255, 255)
ELWIN_CYAN = (109, 219, 255, 255)
ELWIN_GOLD = (255, 182, 0, 255)
ELWIN_LIGHT_GOLD = (255, 219, 146, 255)
ELWIN_BEIGE = (219, 182, 109, 255)
ELWIN_BROWN = (146, 73, 36, 255)
ELWIN_GREEN = (36, 219, 36, 255)
ELWIN_DARK_GREEN = (36, 109, 0, 255)
JESSICA_PURPLE_DARK = (73, 36, 109, 255)
JESSICA_PURPLE_MAIN = (146, 73, 182, 255)
JESSICA_PURPLE_LIGHT = (219, 146, 255, 255)
JESSICA_INDIGO = (73, 73, 109, 255)
JESSICA_VIOLET_SILVER = (146, 146, 182, 255)
JESSICA_EQUIPMENT_COLORS = {
    JESSICA_PURPLE_DARK,
    JESSICA_PURPLE_MAIN,
    JESSICA_PURPLE_LIGHT,
    JESSICA_INDIGO,
    JESSICA_VIOLET_SILVER,
}


CLASS_SPECS = {
    0x13: {
        "name": "MAGE",
        "master": "master/elwin-13-mage-user-retouched.png",
    },
    0x14: {
        "name": "ARCHMAGE",
        "master": "master/elwin-14-archmage-user-retouched.png",
    },
}


# The Elwin coordinates stay fixed. These mappings only replace equipment
# role colors with the color language already used by each commander's class.
COLOR_SCHEMES = {
    (0x13, 1): {},
    (0x13, 2): {
        ELWIN_RED: (109, 0, 0, 255),
        ELWIN_DARK_RED: (73, 0, 0, 255),
        ELWIN_BLUE: (219, 0, 0, 255),
        ELWIN_LIGHT_BLUE: (255, 109, 109, 255),
        ELWIN_CYAN: (255, 109, 109, 255),
        # Keep equipment trim gold so the opposite free-hand skin pixel does
        # not merge into a beige cloak highlight.
        ELWIN_GOLD: (255, 182, 0, 255),
        ELWIN_GREEN: (36, 182, 36, 255),
    },
    (0x13, 3): {
        ELWIN_RED: (0, 0, 109, 255),
        ELWIN_DARK_RED: (0, 0, 73, 255),
        ELWIN_BLUE: (0, 0, 219, 255),
        ELWIN_LIGHT_BLUE: (73, 109, 255, 255),
        ELWIN_CYAN: (109, 219, 255, 255),
        ELWIN_GOLD: (219, 182, 109, 255),
        ELWIN_GREEN: (36, 182, 36, 255),
    },
    (0x13, 4): {
        ELWIN_RED: (0, 36, 73, 255),
        # Keep the cape shadow distinguishable from the editor/map darkness;
        # #242424 remains reserved for actual sprite outlines and seams.
        ELWIN_DARK_RED: (0, 36, 73, 255),
        ELWIN_BLUE: (0, 109, 146, 255),
        ELWIN_LIGHT_BLUE: (36, 109, 146, 255),
        ELWIN_CYAN: (109, 219, 255, 255),
        ELWIN_GOLD: (219, 182, 109, 255),
        ELWIN_GREEN: (36, 182, 36, 255),
    },
    (0x13, 5): {
        # Match Hein Archmage: green cloak, pale robe, lime magic accents.
        ELWIN_RED: (36, 182, 36, 255),
        ELWIN_DARK_RED: (36, 109, 0, 255),
        ELWIN_BLUE: (255, 255, 255, 255),
        ELWIN_LIGHT_BLUE: (146, 146, 146, 255),
        ELWIN_CYAN: (109, 219, 146, 255),
        ELWIN_GOLD: (219, 182, 109, 255),
    },
    (0x13, 8): {
        ELWIN_RED: (255, 255, 255, 255),
        ELWIN_DARK_RED: (73, 73, 109, 255),
        ELWIN_BLUE: (73, 109, 255, 255),
        ELWIN_LIGHT_BLUE: (109, 219, 255, 255),
        ELWIN_CYAN: (182, 219, 255, 255),
        ELWIN_GOLD: (219, 146, 36, 255),
    },
    (0x13, 9): {
        ELWIN_RED: (146, 146, 146, 255),
        ELWIN_DARK_RED: (73, 73, 109, 255),
        ELWIN_BLUE: (219, 182, 109, 255),
        ELWIN_LIGHT_BLUE: (255, 255, 255, 255),
        ELWIN_CYAN: (255, 219, 109, 255),
        ELWIN_GOLD: (219, 182, 109, 255),
    },
    (0x13, 10): {
        ELWIN_RED: JESSICA_PURPLE_MAIN,
        ELWIN_DARK_RED: JESSICA_PURPLE_DARK,
        # Purple remains the cloak identity, while the inner robe uses a
        # cool indigo/silver pair. This separates cloth planes instead of
        # flooding every equipment role with the same violet ramp.
        ELWIN_BLUE: JESSICA_INDIGO,
        ELWIN_LIGHT_BLUE: JESSICA_VIOLET_SILVER,
        ELWIN_CYAN: JESSICA_PURPLE_LIGHT,
        # Jessica's cloak uses purple cloth with a light-violet border;
        # Elwin's former gold/beige trim must not survive on the cloak.
        ELWIN_GOLD: JESSICA_PURPLE_LIGHT,
        ELWIN_LIGHT_GOLD: JESSICA_PURPLE_LIGHT,
        ELWIN_BEIGE: JESSICA_PURPLE_LIGHT,
        # A cyan crystal harmonizes with Jessica's blue hair and gives the
        # purple cloth one controlled complementary accent.
        ELWIN_GREEN: (109, 219, 255, 255),
        ELWIN_DARK_GREEN: (36, 109, 146, 255),
    },
    (0x14, 1): {},
    (0x14, 2): {
        ELWIN_RED: (109, 0, 0, 255),
        ELWIN_DARK_RED: (73, 0, 0, 255),
        ELWIN_BLUE: (219, 0, 0, 255),
        ELWIN_LIGHT_BLUE: (255, 109, 109, 255),
        ELWIN_GOLD: (255, 182, 0, 255),
    },
    (0x14, 3): {
        ELWIN_RED: (0, 0, 109, 255),
        ELWIN_DARK_RED: (0, 0, 73, 255),
        ELWIN_BLUE: (0, 73, 219, 255),
        ELWIN_LIGHT_BLUE: (73, 109, 255, 255),
    },
    (0x14, 4): {
        # Continue Sherry Mage's Princess-like navy/cyan ramp instead of
        # switching the upgraded Archmage back to red.
        ELWIN_RED: (0, 36, 73, 255),
        ELWIN_DARK_RED: (0, 36, 73, 255),
        ELWIN_BLUE: (0, 109, 146, 255),
        ELWIN_LIGHT_BLUE: (36, 109, 146, 255),
        ELWIN_CYAN: (109, 219, 255, 255),
        ELWIN_GOLD: (219, 182, 109, 255),
    },
    (0x14, 5): {
        ELWIN_RED: (36, 182, 36, 255),
        ELWIN_DARK_RED: (36, 109, 0, 255),
        ELWIN_BLUE: (255, 255, 255, 255),
        ELWIN_LIGHT_BLUE: (146, 146, 146, 255),
        ELWIN_CYAN: (109, 219, 146, 255),
        ELWIN_GOLD: (219, 219, 255, 255),
    },
    (0x14, 8): {
        ELWIN_RED: (73, 109, 255, 255),
        ELWIN_DARK_RED: (73, 73, 109, 255),
        ELWIN_BLUE: (255, 255, 255, 255),
        ELWIN_LIGHT_BLUE: (109, 219, 255, 255),
        ELWIN_CYAN: (182, 219, 255, 255),
        ELWIN_GOLD: (109, 219, 255, 255),
        ELWIN_BROWN: (219, 146, 36, 255),
    },
    (0x14, 9): {
        ELWIN_RED: (146, 0, 36, 255),
        ELWIN_DARK_RED: (109, 0, 0, 255),
        ELWIN_BLUE: (36, 73, 219, 255),
        ELWIN_GOLD: (255, 182, 36, 255),
        ELWIN_BROWN: (182, 109, 36, 255),
    },
    (0x14, 10): {
        ELWIN_RED: JESSICA_PURPLE_MAIN,
        ELWIN_DARK_RED: JESSICA_PURPLE_DARK,
        ELWIN_BLUE: JESSICA_INDIGO,
        ELWIN_LIGHT_BLUE: JESSICA_VIOLET_SILVER,
        ELWIN_CYAN: JESSICA_PURPLE_LIGHT,
        ELWIN_GOLD: JESSICA_PURPLE_LIGHT,
        ELWIN_LIGHT_GOLD: JESSICA_PURPLE_LIGHT,
        ELWIN_BEIGE: JESSICA_PURPLE_LIGHT,
        ELWIN_GREEN: (109, 219, 255, 255),
        ELWIN_DARK_GREEN: (36, 109, 146, 255),
    },
}


def points_for(row: dict[str, object]) -> set[tuple[int, int]]:
    return {tuple(point) for point in row["identity_lock_points"]}


def visible_palette(image: Image.Image) -> list[str]:
    colors = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in colors.most_common()
    ]


def validation(
    image: Image.Image,
    original: Image.Image,
    identity: set[tuple[int, int]],
) -> dict[str, object]:
    visible_identity = {
        point for point in identity if original.getpixel(point)[3]
    }
    empty_rows = [
        y for y in range(16)
        if not any(image.getpixel((x, y))[3] for x in range(16))
    ]
    empty_columns = [
        x for x in range(16)
        if not any(image.getpixel((x, y))[3] for y in range(16))
    ]
    palette = visible_palette(image)
    identity_match = sum(
        image.getpixel(point) == original.getpixel(point)
        for point in visible_identity
    )
    return {
        "identity_match": identity_match,
        "identity_pixel_count": len(visible_identity),
        "visible_color_count": len(palette),
        "palette": palette,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "accepted": (
            identity_match == len(visible_identity)
            and len(palette) <= 15
            and not empty_rows
            and not empty_columns
        ),
    }


def comparison_font() -> ImageFont.ImageFont:
    noto = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc")
    if noto.is_file():
        return ImageFont.truetype(str(noto), 12)
    return ImageFont.load_default()


def write_comparison(reports: list[dict[str, object]]) -> None:
    columns = 4
    card_width = 280
    card_height = 305
    rows = (len(reports) + columns - 1) // columns
    canvas = Image.new(
        "RGB", (columns * card_width, rows * card_height), (18, 18, 18)
    )
    draw = ImageDraw.Draw(canvas)
    font = comparison_font()
    for index, report in enumerate(reports):
        x = (index % columns) * card_width
        y = (index // columns) * card_height
        color = (70, 170, 90) if report["accepted"] else (210, 70, 70)
        draw.rectangle(
            (x + 5, y + 5, x + card_width - 6, y + card_height - 6),
            outline=color,
            width=2,
        )
        draw.text(
            (x + 12, y + 12),
            (
                f"{report['commander_id']:02d} {report['commander_name']} "
                f"{report['class_name']}"
            ),
            fill=(245, 245, 245),
            font=font,
        )
        draw.text(
            (x + 12, y + 29),
            (
                f"face {report['identity_match']}/"
                f"{report['identity_pixel_count']}  "
                f"colors {report['visible_color_count']}"
            ),
            fill=(180, 190, 180),
            font=font,
        )
        preview = Image.open(SOURCE_DIR / report["file"]).convert("RGBA")
        backdrop = Image.new("RGBA", (16, 16), (48, 48, 48, 255))
        backdrop.alpha_composite(preview)
        preview = backdrop.convert("RGB").resize(
            (240, 240), RESAMPLING.NEAREST
        )
        canvas.paste(preview, (x + 20, y + 52))
    canvas.save(SOURCE_DIR / "all-elwin-magic-variants.png", optimize=True)


def build_magic_variants(manifest: dict[str, object]) -> list[dict[str, object]]:
    logical_dir = SOURCE_DIR / "logical16"
    preview_dir = SOURCE_DIR / "previews"
    logical_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, object]] = []

    for class_id, spec in CLASS_SPECS.items():
        master = Image.open(SOURCE_DIR / spec["master"]).convert("RGBA")
        if master.size != (16, 16):
            raise ValueError(f"Elwin {class_id:02X} master must be 16x16")
        master_row = manifest["commanders"]["1"]["classes"][str(class_id)]
        master_identity = points_for(master_row)
        for commander_id in COMMANDER_IDS:
            commander = manifest["commanders"][str(commander_id)]
            row = commander["classes"][str(class_id)]
            identity = points_for(row)
            original = Image.open(
                ROM_SPRITE_DIR / str(commander_id) / f"{class_id:02X}-p1.png"
            ).convert("RGBA")
            equipment = master.copy()
            for point in master_identity:
                equipment.putpixel(point, TRANSPARENT)
            scheme = COLOR_SCHEMES[(class_id, commander_id)]
            for y in range(16):
                for x in range(16):
                    point = (x, y)
                    color = equipment.getpixel(point)
                    if color in scheme:
                        equipment.putpixel(point, scheme[color])
            converted, _, _, _ = identity_locked_character_sprite(
                equipment,
                original,
                [INK],
                identity,
                preserve_generated_palette=True,
                restore_transparent_locked_points=False,
            )
            if commander_id == 5:
                # The palette fitter can merge the requested mid green back
                # into the former bright lime. Keep Hein's shared green ramp
                # explicitly one Mega Drive step darker in both classes.
                for y in range(16):
                    for x in range(16):
                        if converted.getpixel((x, y)) == ELWIN_GREEN:
                            converted.putpixel(
                                (x, y), (36, 182, 36, 255)
                            )
            if commander_id == 4:
                # Palette fitting used to merge Sherry's very dark teal cape
                # face back into #242424 ink. Restore only source equipment
                # cells with this role; real outlines and seams stay ink.
                for y in range(16):
                    for x in range(16):
                        point = (x, y)
                        if (
                            point not in identity
                            and equipment.getpixel(point)
                            == (0, 36, 73, 255)
                        ):
                            converted.putpixel(point, (0, 36, 73, 255))
            if commander_id == 10:
                # Preserve all three purple shade roles after palette fitting;
                # otherwise the small dark-violet patches can be merged into
                # the main purple at this resolution.
                for y in range(16):
                    for x in range(16):
                        point = (x, y)
                        if point in identity:
                            continue
                        equipment_color = equipment.getpixel(point)
                        if equipment_color in JESSICA_EQUIPMENT_COLORS:
                            converted.putpixel(point, equipment_color)
            output = logical_dir / f"{commander_id:02d}-{class_id:02X}.png"
            converted.save(output, optimize=True)
            converted.resize((512, 512), RESAMPLING.NEAREST).save(
                preview_dir / output.name,
                optimize=True,
            )
            reports.append({
                "commander_id": commander_id,
                "commander_name": commander["name"],
                "class_id": f"{class_id:02X}",
                "class_name": spec["name"],
                "file": str(output.relative_to(SOURCE_DIR)),
                **validation(converted, original, identity),
            })
    return reports


def build_hein_sorcerer(manifest: dict[str, object]) -> dict[str, object]:
    master = Image.open(
        SORCERER_DIR / "master/hein-03-warlock-rom.png"
    ).convert("RGBA")
    target_row = manifest["commanders"]["5"]["classes"][str(0x09)]
    identity = points_for(target_row)
    original = Image.open(ROM_SPRITE_DIR / "5/09-p1.png").convert("RGBA")

    # Only the lower-left ROM Warlock cloak is recolored. The face, staff,
    # hands, and remaining garment pixels stay in their original positions.
    for y in range(8, 16):
        for x in range(0, 6):
            color = master.getpixel((x, y))
            if color == (73, 73, 109, 255):
                master.putpixel((x, y), (36, 109, 0, 255))
            elif color == (146, 146, 146, 255):
                master.putpixel((x, y), (36, 182, 36, 255))
            elif color == (255, 255, 255, 255):
                master.putpixel((x, y), (109, 219, 146, 255))
    for point in identity:
        if original.getpixel(point)[3]:
            master.putpixel(point, original.getpixel(point))
    # Extend the stock staff crystal outline by one pixel so the equipment
    # uses the rightmost logical column without changing the body silhouette.
    master.putpixel((15, 5), INK)
    output_dir = SORCERER_DIR / "logical16"
    preview_dir = SORCERER_DIR / "previews"
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "05-09.png"
    master.save(output, optimize=True)
    master.resize((512, 512), RESAMPLING.NEAREST).save(
        preview_dir / "05-09.png", optimize=True
    )
    return {
        "commander_id": 5,
        "commander_name": "헤인",
        "class_id": "09",
        "class_name": "SORCERER",
        "file": str(output.relative_to(SORCERER_DIR)),
        **validation(master, original, identity),
    }


def build_hein_paladin(manifest: dict[str, object]) -> dict[str, object]:
    master = Image.open(
        PALADIN_DIR / "master/hein-0D-magic-knight-rom.png"
    ).convert("RGBA")
    target_row = manifest["commanders"]["5"]["classes"][str(0x19)]
    identity = points_for(target_row)
    original = Image.open(ROM_SPRITE_DIR / "5/19-p1.png").convert("RGBA")

    # Keep the stock mounted Magic Knight drawing. Recolor only equipment
    # pixels outside the protected head/face to Hein's darker green family.
    mapping = {
        (73, 109, 255, 255): (36, 109, 0, 255),
        (109, 219, 255, 255): (36, 182, 36, 255),
        (219, 0, 0, 255): (36, 109, 0, 255),
        (255, 182, 0, 255): (109, 219, 146, 255),
    }
    for y in range(16):
        for x in range(16):
            point = (x, y)
            color = master.getpixel(point)
            if point not in identity and color in mapping:
                master.putpixel(point, mapping[color])
            elif point not in identity and y >= 10:
                if color == (73, 73, 109, 255):
                    master.putpixel(point, (36, 109, 0, 255))
                elif color == (146, 146, 146, 255):
                    master.putpixel(point, (36, 182, 36, 255))
                elif color == (255, 255, 255, 255):
                    master.putpixel(point, (109, 219, 146, 255))
    for point in identity:
        if original.getpixel(point)[3]:
            master.putpixel(point, original.getpixel(point))

    output_dir = PALADIN_DIR / "logical16"
    preview_dir = PALADIN_DIR / "previews"
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "05-19.png"
    master.save(output, optimize=True)
    master.resize((512, 512), RESAMPLING.NEAREST).save(
        preview_dir / "05-19.png", optimize=True
    )
    return {
        "commander_id": 5,
        "commander_name": "헤인",
        "class_id": "19",
        "class_name": "PALADIN",
        "file": str(output.relative_to(PALADIN_DIR)),
        **validation(master, original, identity),
    }


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    reports = build_magic_variants(manifest)
    write_comparison(reports)
    sorcerer = build_hein_sorcerer(manifest)
    paladin = build_hein_paladin(manifest)
    result = {
        "version": 1,
        "policy": (
            "Elwin's latest user-retouched equipment coordinates are shared "
            "for Mage and Archmage; target ROM identity pixels and each "
            "commander's class colors are preserved. Hein Sorcerer uses the "
            "stock Warlock silhouette with only its cloak recolored lime."
        ),
        "masters": {
            f"{class_id:02X}": spec["master"]
            for class_id, spec in CLASS_SPECS.items()
        },
        "all_accepted": (
            all(row["accepted"] for row in reports)
            and sorcerer["accepted"]
            and paladin["accepted"]
        ),
        "classes": reports,
        "hein_sorcerer": sorcerer,
        "hein_paladin": paladin,
    }
    (SOURCE_DIR / "validation-report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (SORCERER_DIR / "validation-report.json").write_text(
        json.dumps(sorcerer, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (PALADIN_DIR / "validation-report.json").write_text(
        json.dumps(paladin, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
