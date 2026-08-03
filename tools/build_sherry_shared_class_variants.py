#!/usr/bin/env python3
"""Build target classes from approved Wizard and Swordmaster designs."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MASK_FILE = ROOT / "editor/ai_identity_masks.json"
ROM_DIR = ROOT / "editor/static/class-sprites/commanders"
AI_DIR = ROOT / "editor/static/ai-class-sprites"
TRANSPARENT = (0, 0, 0, 0)

# Elwin's current Swordmaster face mask includes ten left-shoulder equipment
# pixels. They must travel with the class design instead of being stripped as
# identity, otherwise the outer lower shoulder is shortened on Sherry/Aaron.
SWORDMASTER_LEFT_SHOULDER_POINTS = {
    (2, 8),
    (3, 8),
    (1, 9),
    (2, 9),
    (3, 9),
    (4, 9),
    (0, 10),
    (1, 10),
    (2, 10),
    (0, 11),
}
SWORDMASTER_RIGHT_SHOULDER_POINTS = {
    (11, 8), (12, 8), (13, 8), (14, 8), (15, 8),
    (10, 9), (11, 9), (12, 9), (13, 9), (14, 9), (15, 9),
    (13, 10), (14, 10), (15, 10),
    (15, 11),
}
SWORDMASTER_WHITE_BLADE_POINTS = {
    # Left downward blade.
    (3, 11), (2, 12), (3, 12), (1, 13), (2, 13),
    (1, 14), (0, 15),
    # Right downward blade.
    (12, 12), (13, 12), (12, 13), (13, 13), (14, 13),
    (13, 14), (14, 14), (14, 15), (15, 15),
}
SWORDMASTER_METAL_ROLE_POINTS = (
    SWORDMASTER_LEFT_SHOULDER_POINTS
    | SWORDMASTER_RIGHT_SHOULDER_POINTS
    | SWORDMASTER_WHITE_BLADE_POINTS
)

VARIANTS = {
    (2, 0x15): {
        "source_commander": 5,
        "source_class": 0x15,
        "output_dir": "shared-wizard-hein-v1",
        "label": "Hein Wizard outfit -> Liana Wizard",
        "recolor": {
            (73, 109, 255, 255): (182, 0, 36, 255),
            (109, 219, 255, 255): (219, 36, 36, 255),
            (255, 182, 73, 255): (255, 182, 0, 255),
        },
    },
    (3, 0x15): {
        "source_commander": 5,
        "source_class": 0x15,
        "output_dir": "shared-wizard-hein-v1",
        "label": "Hein Wizard outfit -> Lana Wizard",
        "recolor": {
            (73, 109, 255, 255): (0, 36, 182, 255),
            (109, 219, 255, 255): (73, 109, 255, 255),
            (255, 182, 73, 255): (255, 182, 0, 255),
        },
    },
    (4, 0x15): {
        "source_commander": 5,
        "source_class": 0x15,
        "output_dir": "shared-wizard-hein-v1",
        "label": "Hein Wizard outfit -> Sherry Wizard",
        "recolor": {
            (73, 109, 255, 255): (36, 36, 109, 255),
            (109, 219, 255, 255): (146, 146, 219, 255),
            (255, 182, 73, 255): (255, 182, 0, 255),
        },
    },
    (4, 0x23): {
        "source_commander": 1,
        "source_class": 0x1A,
        "output_dir": "shared-high-master-elwin-swordmaster-v1",
        "label": "Elwin Swordmaster equipment -> Sherry High Master",
        "source_equipment_points": SWORDMASTER_LEFT_SHOULDER_POINTS,
        # Keep Elwin's white/silver blades and gold/white shoulder ornaments
        # as metal. Only cape and cloth roles receive Sherry's teal ramp.
        "preserve_source_color_points": SWORDMASTER_METAL_ROLE_POINTS,
        "recolor": {
            (219, 0, 0, 255): (0, 109, 146, 255),
            (109, 0, 0, 255): (0, 36, 73, 255),
            (73, 73, 109, 255): (36, 109, 146, 255),
            (146, 146, 146, 255): (109, 219, 255, 255),
        },
    },
    (7, 0x15): {
        "source_commander": 5,
        "source_class": 0x15,
        "output_dir": "shared-wizard-hein-v1",
        "label": "Hein Wizard outfit -> Keith Wizard",
        "recolor": {
            (73, 109, 255, 255): (0, 36, 182, 255),
            (109, 219, 255, 255): (73, 109, 255, 255),
            (255, 182, 73, 255): (219, 146, 0, 255),
        },
    },
    (8, 0x23): {
        "source_commander": 1,
        "source_class": 0x1A,
        "output_dir": "shared-high-master-elwin-swordmaster-v1",
        "label": "Elwin Swordmaster equipment -> Aaron High Master",
        "source_equipment_points": SWORDMASTER_LEFT_SHOULDER_POINTS,
        # A lone teal equipment pixel was detached to the left of Aaron's
        # hair. It is not identity-locked and should remain transparent.
        "transparent_points": {(1, 2)},
        "recolor": {
            (219, 0, 0, 255): (73, 109, 255, 255),
            # Keep the cape shadow visibly blue instead of letting it merge
            # into the near-black map/editor background.
            (109, 0, 0, 255): (36, 73, 219, 255),
            (73, 73, 109, 255): (36, 109, 146, 255),
            (146, 146, 146, 255): (109, 219, 255, 255),
        },
    },
    (9, 0x15): {
        "source_commander": 5,
        "source_class": 0x15,
        "output_dir": "shared-wizard-hein-v1",
        "label": "Hein Wizard outfit -> Lester Wizard",
        "recolor": {
            (73, 109, 255, 255): (73, 36, 109, 255),
            (109, 219, 255, 255): (146, 73, 182, 255),
            (255, 182, 73, 255): (219, 146, 36, 255),
        },
    },
    (10, 0x15): {
        "source_commander": 5,
        "source_class": 0x15,
        "output_dir": "shared-wizard-hein-v1",
        "label": "Hein Wizard outfit -> Jessica Wizard",
        "recolor": {
            (73, 109, 255, 255): (146, 73, 182, 255),
            (109, 219, 255, 255): (219, 146, 255, 255),
            (255, 182, 73, 255): (219, 146, 255, 255),
        },
    },
}


def palette(image: Image.Image) -> list[str]:
    colors = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in colors.most_common()
    ]


def build_variant(
    target_commander: int,
    class_id: int,
    spec: dict[str, object],
    masks: dict[str, list[list[int]]],
) -> dict[str, object]:
    source_commander = int(spec["source_commander"])
    source_class = int(spec["source_class"])
    source = Image.open(
        AI_DIR / str(source_commander) / f"{source_class:02X}.png"
    ).convert("RGBA")
    preserved_source_colors = {
        point: source.getpixel(point)
        for point in spec.get("preserve_source_color_points", set())
    }
    source_identity = {
        tuple(point) for point in masks[f"{source_commander}:{source_class:02X}"]
    }
    source_equipment_points = set(spec.get("source_equipment_points", set()))
    for point in source_identity - source_equipment_points:
        source.putpixel(point, TRANSPARENT)

    recolor = spec["recolor"]
    for y in range(16):
        for x in range(16):
            point = (x, y)
            color = source.getpixel(point)
            if color in recolor:
                source.putpixel(point, recolor[color])

    for point, color in preserved_source_colors.items():
        if color[3]:
            source.putpixel(point, color)

    target_identity = {
        tuple(point)
        for point in masks[f"{target_commander}:{class_id:02X}"]
    }
    target_original = Image.open(
        ROM_DIR / str(target_commander) / f"{class_id:02X}-p1.png"
    ).convert("RGBA")
    for point in target_identity:
        color = target_original.getpixel(point)
        if color[3]:
            source.putpixel(point, color)

    for point in spec.get("transparent_points", set()):
        source.putpixel(point, TRANSPARENT)

    visible_palette = palette(source)
    empty_rows = [
        y
        for y in range(16)
        if not any(source.getpixel((x, y))[3] for x in range(16))
    ]
    empty_columns = [
        x
        for x in range(16)
        if not any(source.getpixel((x, y))[3] for y in range(16))
    ]
    identity_match = sum(
        source.getpixel(point) == target_original.getpixel(point)
        for point in target_identity
        if target_original.getpixel(point)[3]
    )
    visible_identity_count = sum(
        bool(target_original.getpixel(point)[3]) for point in target_identity
    )
    accepted = (
        identity_match == visible_identity_count
        and len(visible_palette) <= 15
        and not empty_rows
        and not empty_columns
        and (0, 0, 0, 255) not in source.getdata()
    )
    if not accepted:
        raise ValueError(
            f"invalid target class {target_commander}:{class_id:02X}: "
            f"identity={identity_match}/{visible_identity_count}, "
            f"colors={len(visible_palette)}, rows={empty_rows}, "
            f"columns={empty_columns}"
        )

    output_root = (
        ROOT / "docs/assets/ai-class-source/latest" / str(spec["output_dir"])
    )
    logical_dir = output_root / "logical16"
    preview_dir = output_root / "previews"
    logical_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    output = logical_dir / f"{target_commander:02d}-{class_id:02X}.png"
    source.save(output, optimize=True)
    source.resize((512, 512), Image.Resampling.NEAREST).save(
        preview_dir / output.name, optimize=True
    )

    report = {
        "label": spec["label"],
        "source": f"{source_commander:02d}-{source_class:02X}",
        "target": f"{target_commander:02d}-{class_id:02X}",
        "identity_match": identity_match,
        "identity_pixel_count": visible_identity_count,
        "visible_color_count": len(visible_palette),
        "palette": visible_palette,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "accepted": True,
    }
    (output_root / f"validation-{target_commander:02d}-{class_id:02X}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    masks = json.loads(MASK_FILE.read_text(encoding="utf-8"))["masks"]
    reports = [
        build_variant(target_commander, class_id, spec, masks)
        for (target_commander, class_id), spec in VARIANTS.items()
    ]
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
