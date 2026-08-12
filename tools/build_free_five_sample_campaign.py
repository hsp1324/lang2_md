#!/usr/bin/env python3
"""Build five unconstrained, centered AI class designs per sample group.

Only the user's face/hair identity (including its dark boundary), native 16x16
size, and the 15-visible-color hardware limit are hard constraints.  ROM art is
supplied for character identity and Mega Drive pixel language, but pose, scale,
equipment side, silhouette, palette, helmet, mount, and composition are free.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import statistics
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.build_rom_anchored_sample_campaign import (  # noqa: E402
    CLASSES,
    COMMANDERS,
    CURRENT_MANIFEST,
    CURRENT_ROOT,
    MASK_FILE,
    ROM_ROOT,
    ROOT,
    TRANSPARENT,
    build_rom_board,
    campaign_groups,
    expanded_identity_points,
    manifest_identity_points,
    opaque_bbox,
    remove_cell_background,
    rgba_distance,
    snap_color,
    transparent_nearest,
    write_json,
)
from tools.pillow_compat import flattened_image_data  # noqa: E402


SOURCE_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/"
    / "sample-class-variants-v4-free-five"
)
STATIC_ROOT = ROOT / "editor/static/sample-class-sprites"
ASSET_VERSION = "sample-classes-v6-elwin-purple-ornament"
ACTIVE_SAMPLE_KEYS = {
    (1, 0x22),  # Elwin Hero: King-derived five-color study.
    (2, 0x18),  # Liana Sage.
    (3, 0x18),  # Lana Sage.
    (5, 0x18),  # Hein Sage.
    (10, 0x18),  # Jessica Sage.
}


CLASS_IDEAS = {
    0x08: (
        "light traveling healer with a compact wand",
        "asymmetric battlefield medic with a broad mantle",
        "ceremonial healer with a large symbolic staff",
        "armored healer with shield-like ritual gear",
        "mystic healer with an unusual orb or book composition",
    ),
    0x15: (
        "classic staff wizard with a strong readable gesture",
        "asymmetric spellcaster with book and short wand",
        "heavily robed battle wizard with bold shoulders",
        "mobile wizard with a long diagonal implement",
        "exotic arcane design with a surprising but readable silhouette",
    ),
    0x16: (
        "classic high priest with ceremonial staff",
        "asymmetric high priest with scripture and open hand",
        "armored high priest with broad sacred mantle",
        "flowing high priest with tall symbolic headpiece or staff",
        "unusual divine caster with a bold relic composition",
    ),
    0x18: (
        "book-focused scholar with a compact staff",
        "orb and scroll sage with asymmetric sleeves",
        "armored sage with tablet or relic",
        "flowing rune sage with a long diagonal tool",
        "eccentric ancient sage with an unusual readable silhouette",
    ),
    0x22: (
        "classic sword hero with a confident open pose",
        "shield-bearing hero with asymmetric armor",
        "heavy greatsword hero with a broad silhouette",
        "fast dual-weapon or cape-swept hero",
        "unexpected legendary hero composition with a bold weapon",
    ),
    0x25: (
        "fast blade agent with a light compact silhouette",
        "long-weapon agent with an asymmetric coat",
        "shield or gadget agent with a guarded pose",
        "ranged or throwing-weapon agent with a flowing cape",
        "unusual covert agent with a striking readable prop",
    ),
    0x26: (
        "upright long-lance warrior",
        "diagonal javelin fighter with a light mantle",
        "heavy halberd warrior with broad shoulders",
        "mobile spear fighter with a wind-swept cape",
        "unusual ritual lancer with a bold asymmetric silhouette",
    ),
    0x28: (
        "classic summoner with an orb staff",
        "book and short-wand summoner",
        "broad-robed summoner with a dramatic relic",
        "mobile summoner with a long diagonal implement",
        "unusual summoner with a small mount, familiar, helmet, or bold prop",
    ),
}


def group_root(group: dict) -> Path:
    return SOURCE_ROOT / group["id"]


def active_campaign_groups() -> list[dict]:
    return [
        group
        for group in campaign_groups()
        if (int(group["commander_id"]), int(group["class_id"]))
        in ACTIVE_SAMPLE_KEYS
    ]


def write_campaign_catalog(groups: list[dict]) -> None:
    write_json(
        SOURCE_ROOT / "campaign.json",
        {
            "asset_version": ASSET_VERSION,
            "expected_group_count": len(groups),
            "expected_candidate_count": len(groups) * 5,
            "excluded_approved_classes": [
                {"class_id": "08", "class_name": "힐러"},
                {"class_id": "15", "class_name": "위저드"},
                {"class_id": "16", "class_name": "하이프리스트"},
                {"class_id": "25", "class_name": "에이전트"},
                {"class_id": "26", "class_name": "자베러"},
                {"class_id": "28", "class_name": "서머너"},
            ],
            "catalog_policy": (
                "Only unfinished Elwin Hero and Liana/Lana/Hein/Jessica "
                "Sage remain visible in the sample editor"
            ),
            "hard_constraints": [
                "16x16",
                "15 visible colors",
                "expanded identity exact",
            ],
            "removed_constraints": [
                "ROM preservation percentage",
                "ROM bounding box",
                "ROM-first equipment palette",
                "pose and weapon side",
                "helmet and mount ban",
                "class-equipment-only changes",
            ],
            "groups": groups,
        },
    )


def free_prompt(group: dict) -> str:
    _, commander_name = COMMANDERS[int(group["commander_id"])]
    _, class_name = CLASSES[int(group["class_id"])]
    ideas = "; ".join(
        f"{index + 1}: {idea}"
        for index, idea in enumerate(CLASS_IDEAS[int(group["class_id"])])
    )
    return f"""Use case: stylized-concept
Asset type: one horizontal review strip containing exactly five separate native-logical-16x16 Mega Drive tactical-RPG commander sprite concepts
Input images: Image 1 is a ROM-only character and 16-bit pixel-language reference. It is NOT a pose, bounding-box, equipment, palette, weapon-side, silhouette, or preservation-percentage constraint. Image 2 is the only hard visual invariant: {commander_name}'s exact face, eye, hair, and adjoining dark boundary pixels. No previous AI artwork is an input.
Primary request: invent five genuinely different {commander_name} {class_name} designs. Creative freedom is intentional. Pose, body width, equipment side, weapon direction, armor, robe, cape, helmet, mount, shield, prop, palette distribution, and silhouette may all change. The class should remain readable, but changes do not have to be limited to class equipment.
Five distinct creative directions: {ideas}.
Diversity requirement: do not reuse one body template or make palette swaps. Each candidate must have a clearly different body/equipment silhouette, pose, prop arrangement, and coherent color treatment.
Identity invariant: keep Image 2 face, eye, hair, head size, and dark boundary readable and unobscured. A helmet or ornament may surround the locked identity but must not replace it.
Centering and layout: exactly five equal vertical cells in one horizontal row, no second row, no labels. Inside each cell imagine a centered square design zone whose side equals the cell width. Put the entire sprite only inside that central square. The character's torso/body axis and visual mass must sit exactly on the horizontal centerline of its cell, not biased left or right by a weapon or cape. Center the full sprite vertically too, with even padding. Weapon, mount, cape, hand and feet must remain inside the centered square and must not touch or cross cell boundaries.
Style/medium: coarse authentic early-1990s Mega Drive pixel art intended for final logical 16x16 use; large square pixel clusters, hard edges, no antialiasing, no gradients, no blur, no micro-detail or 32x32 density.
Color: choose a distinct, coherent equipment palette for each candidate. Do not restrict equipment to the ROM palette. Keep enough dark colored outline contrast for neck, face, arms and body separation. Pure black may be used only as a tiny internal eye/detail if needed, never as the background.
Backdrop: perfectly flat uniform #00FF00 chroma-key background throughout all five cells, with no frame, border, floor, shadow, gradient, texture, scenery, text, logo or watermark. Never use #00FF00 inside a sprite.
Avoid: off-center body, subject leaning into one cell edge, cropped weapon, cropped mount, tiny character caused by excess padding, identical robes, shared caster template, five recolors, background color inside the body, disconnected accidental noise.
"""


def prepare() -> None:
    manifest = json.loads(CURRENT_MANIFEST.read_text(encoding="utf-8"))
    saved_masks = json.loads(MASK_FILE.read_text(encoding="utf-8")).get("masks", {})
    groups = active_campaign_groups()
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
        base_points = {tuple(point) for point in saved_masks.get(mask_key, [])} or manifest_identity_points(manifest, group)
        points = expanded_identity_points(base_points, current)
        original.save(root / "references/rom-original16.png", optimize=True)
        transparent_nearest(original).save(root / "references/rom-original-32x-alpha.png", optimize=True)
        build_rom_board(group, original).save(root / "references/rom-only-board.png", optimize=True)
        identity = Image.new("RGBA", (16, 16), TRANSPARENT)
        for point in points:
            identity.putpixel(point, current.getpixel(point))
        identity.save(root / "references/identity-with-dark-boundary16.png", optimize=True)
        transparent_nearest(identity).save(root / "references/identity-with-dark-boundary-32x.png", optimize=True)
        write_json(
            root / "references/identity-mask-expanded.json",
            {
                "commander_id": group["commander_id"],
                "class_id": f"{group['class_id']:02X}",
                "points": [list(point) for point in sorted(points)],
                "pixel_count": len(points),
            },
        )
        (root / "prompts/board.txt").write_text(free_prompt(group), encoding="utf-8")
    write_campaign_catalog(groups)


def median_coordinate(values: list[int]) -> float:
    return float(statistics.median(values))


def centered_subject(cell: Image.Image) -> tuple[Image.Image, dict[str, float]]:
    foreground = remove_cell_background(cell)
    bbox = opaque_bbox(foreground)
    subject = foreground.crop(bbox)
    side = min(cell.width, cell.height)
    alpha_points = [
        (x, y)
        for y in range(subject.height)
        for x in range(subject.width)
        if subject.getpixel((x, y))[3]
    ]
    if not alpha_points:
        raise ValueError("empty generated subject")
    central_y_min = round(subject.height * 0.18)
    central_y_max = round(subject.height * 0.82)
    body_points = [point for point in alpha_points if central_y_min <= point[1] <= central_y_max] or alpha_points
    body_x_source = median_coordinate([point[0] for point in body_points])
    body_y_source = (subject.height - 1) / 2
    maximum_radius = (side - 1) * 0.47
    source_radius = max(
        body_x_source,
        subject.width - 1 - body_x_source,
        body_y_source,
        subject.height - 1 - body_y_source,
    )
    scale = maximum_radius / max(1.0, source_radius)
    resized = (
        max(1, round(subject.width * scale)),
        max(1, round(subject.height * scale)),
    )
    subject = subject.resize(resized, Image.Resampling.NEAREST)
    alpha_points = [
        (x, y)
        for y in range(subject.height)
        for x in range(subject.width)
        if subject.getpixel((x, y))[3]
    ]
    central_y_min = round(subject.height * 0.18)
    central_y_max = round(subject.height * 0.82)
    body_points = [point for point in alpha_points if central_y_min <= point[1] <= central_y_max] or alpha_points
    body_x = median_coordinate([point[0] for point in body_points])
    body_y = (subject.height - 1) / 2
    target = (side - 1) / 2
    left = round(target - body_x)
    top = round(target - body_y)
    left = max(0, min(left, side - subject.width))
    top = max(0, min(top, side - subject.height))
    canvas = Image.new("RGBA", (side, side), TRANSPARENT)
    canvas.alpha_composite(subject, (left, top))
    placed = [
        (x, y)
        for y in range(side)
        for x in range(side)
        if canvas.getpixel((x, y))[3]
    ]
    placed_bbox = opaque_bbox(canvas)
    placed_body = [
        point
        for point in placed
        if placed_bbox[1] + (placed_bbox[3] - placed_bbox[1]) * 0.18
        <= point[1]
        <= placed_bbox[1] + (placed_bbox[3] - placed_bbox[1]) * 0.82
    ] or placed
    center_offset_x = median_coordinate([point[0] for point in placed_body]) - target
    center_offset_y = ((placed_bbox[1] + placed_bbox[3] - 1) / 2) - target
    return canvas, {
        "source_bbox_width": bbox[2] - bbox[0],
        "source_bbox_height": bbox[3] - bbox[1],
        "center_offset_x": round(center_offset_x, 3),
        "center_offset_y": round(center_offset_y, 3),
    }


def free_palette(logical: Image.Image, identity: Image.Image) -> list[tuple[int, int, int, int]]:
    identity_colors = [color for _, color in identity.getcolors(maxcolors=256) or [] if color[3]]
    generated = Counter(
        snap_color(color)
        for _, color in logical.getcolors(maxcolors=65536) or []
        if color[3] and color[:3] not in ((0, 255, 0), (255, 0, 255))
    )
    palette: list[tuple[int, int, int, int]] = []
    for color in identity_colors + [row[0] for row in generated.most_common()]:
        if color[:3] == (0, 0, 0) and color not in identity_colors:
            continue
        if color not in palette:
            palette.append(color)
        if len(palette) == 15:
            break
    return palette


def logical_from_centered(centered: Image.Image, root: Path) -> Image.Image:
    logical = centered.resize((16, 16), Image.Resampling.BOX)
    with Image.open(root / "references/identity-with-dark-boundary16.png") as opened:
        identity = opened.convert("RGBA")
    palette = free_palette(logical, identity)
    for y in range(16):
        for x in range(16):
            color = logical.getpixel((x, y))
            if color[3] < 56:
                logical.putpixel((x, y), TRANSPARENT)
            elif palette:
                logical.putpixel((x, y), min(palette, key=lambda target: rgba_distance(color, target)))
    points = json.loads((root / "references/identity-mask-expanded.json").read_text(encoding="utf-8"))["points"]
    for point in points:
        xy = tuple(point)
        logical.putpixel(xy, identity.getpixel(xy))
    return logical


def ingest_board(group_id: str, source: Path) -> None:
    root = SOURCE_ROOT / group_id
    with Image.open(source) as opened:
        board = opened.convert("RGBA")
    raw_target = root / "raw-boards/board.png"
    if source.resolve() != raw_target.resolve():
        shutil.copy2(source, raw_target)
    centering = []
    for index in range(5):
        left = round(index * board.width / 5)
        right = round((index + 1) * board.width / 5)
        cell = board.crop((left, 0, right, board.height))
        centered, metrics = centered_subject(cell)
        sample_id = f"{index + 1:02d}"
        centered.save(root / f"ai/{sample_id}.png", optimize=True)
        logical = logical_from_centered(centered, root)
        logical.save(root / f"logical16/{sample_id}.png", optimize=True)
        logical.resize((256, 256), Image.Resampling.NEAREST).save(root / f"previews/{sample_id}.png", optimize=True)
        centering.append({"sample": sample_id, **metrics})
    write_json(root / "centering-report.json", centering)


def publish() -> None:
    groups = active_campaign_groups()
    write_campaign_catalog(groups)
    manifest_groups = []
    reports = []
    diversity_reports = []
    contact_rows = []
    for group in groups:
        root = group_root(group)
        policy_path = root / "design-policy.json"
        policy = (
            json.loads(policy_path.read_text(encoding="utf-8"))
            if policy_path.is_file()
            else {}
        )
        points = [tuple(point) for point in json.loads((root / "references/identity-mask-expanded.json").read_text(encoding="utf-8"))["points"]]
        with Image.open(root / "references/identity-with-dark-boundary16.png") as opened:
            identity = opened.convert("RGBA")
        samples = []
        panels = []
        logicals = []
        center_rows = {row["sample"]: row for row in json.loads((root / "centering-report.json").read_text(encoding="utf-8"))}
        for index in range(1, 6):
            sample_id = f"{index:02d}"
            ai_path = root / f"ai/{sample_id}.png"
            logical_path = root / f"logical16/{sample_id}.png"
            with Image.open(ai_path) as opened:
                ai = opened.convert("RGBA")
            with Image.open(logical_path) as opened:
                logical = opened.convert("RGBA")
            colors = {color for _, color in logical.getcolors(maxcolors=256) or [] if color[3]}
            variant_points = {
                tuple(point)
                for point in policy.get(
                    "identity_color_variant_points_by_sample",
                    {},
                ).get(sample_id, [])
            }
            free_points = {
                tuple(point)
                for point in policy.get("identity_color_free_points", [])
            }
            locked_points = set(points) - free_points - variant_points
            matches = sum(
                logical.getpixel(point) == identity.getpixel(point)
                for point in locked_points
            )
            expected_variant_pixels = policy.get(
                "identity_color_variant_expected_pixels_by_sample",
                {},
            ).get(sample_id, {})
            variant_matches = True
            if expected_variant_pixels:
                expected_points = {
                    tuple(int(value) for value in key.split(","))
                    for key in expected_variant_pixels
                }
                variant_matches = expected_points == variant_points
                for key, expected_variant in expected_variant_pixels.items():
                    point = tuple(int(value) for value in key.split(","))
                    expected_rgba = (
                        int(expected_variant[1:3], 16),
                        int(expected_variant[3:5], 16),
                        int(expected_variant[5:7], 16),
                        255,
                    )
                    variant_matches = (
                        variant_matches
                        and logical.getpixel(point) == expected_rgba
                    )
            center = center_rows[sample_id]
            opaque = sum(
                1 for color in flattened_image_data(logical) if color[3]
            )
            report = {
                "group": group["id"],
                "sample": sample_id,
                "visible_colors": len(colors),
                "identity_matches": matches,
                "identity_total": len(locked_points),
                "identity_color_variant_pixels": len(variant_points),
                "identity_color_free_pixels": len(free_points),
                "identity_color_variant_matches": variant_matches,
                "opaque_pixels": opaque,
                "center_offset_x": center["center_offset_x"],
                "center_offset_y": center["center_offset_y"],
            }
            report["accepted"] = (
                logical.size == (16, 16)
                and len(colors) <= 15
                and matches == len(locked_points)
                and variant_matches
                and 55 <= opaque <= 245
                and abs(float(center["center_offset_x"])) <= 1.0
                and abs(float(center["center_offset_y"])) <= 0.5
            )
            reports.append(report)
            logicals.append(logical.copy())
            static = STATIC_ROOT / group["id"]
            for child in ("ai", "logical16", "previews"):
                (static / child).mkdir(parents=True, exist_ok=True)
            ai_thumb = ai.copy()
            ai_thumb.thumbnail((384, 384), Image.Resampling.NEAREST)
            ai_thumb.save(static / f"ai/{sample_id}.png", optimize=True)
            shutil.copy2(logical_path, static / f"logical16/{sample_id}.png")
            shutil.copy2(root / f"previews/{sample_id}.png", static / f"previews/{sample_id}.png")
            samples.append({
                "id": sample_id,
                "label": policy.get(
                    "sample_label_overrides",
                    {},
                ).get(
                    sample_id,
                    policy.get("sample_label", "자유 디자인") + f" {sample_id}",
                ),
                "description": policy.get(
                    "sample_description_overrides",
                    {},
                ).get(
                    sample_id,
                    policy.get(
                        "sample_description",
                        "얼굴 경계만 고정하고 중앙 정렬한 자유 클래스 디자인",
                    ),
                ),
                "ai_source": f"sample-class-sprites/{group['id']}/ai/{sample_id}.png",
                "logical16": f"sample-class-sprites/{group['id']}/logical16/{sample_id}.png",
                "preview": f"sample-class-sprites/{group['id']}/previews/{sample_id}.png",
                "preserved": False,
            })
            panel = Image.new("RGBA", (152, 236), (28, 32, 29, 255))
            draw = ImageDraw.Draw(panel)
            draw.text((5, 5), sample_id, fill=(235, 240, 236, 255))
            shown = ai.copy()
            shown.thumbnail((136, 136), Image.Resampling.NEAREST)
            panel.alpha_composite(shown, ((152 - shown.width) // 2, 22))
            panel.alpha_composite(logical.resize((72, 72), Image.Resampling.NEAREST), (40, 160))
            panels.append(panel)
        differences = []
        silhouettes = []
        identity_set = set(points)
        for first in range(5):
            for second in range(first + 1, 5):
                differences.append(sum(logicals[first].getpixel((x, y)) != logicals[second].getpixel((x, y)) for y in range(16) for x in range(16) if (x, y) not in identity_set))
                silhouettes.append(sum(bool(logicals[first].getpixel((x, y))[3]) != bool(logicals[second].getpixel((x, y))[3]) for y in range(16) for x in range(16) if (x, y) not in identity_set))
        diversity = {
            "group": group["id"],
            "minimum_equipment_pixel_difference": min(differences),
            "median_equipment_pixel_difference": statistics.median(differences),
            "minimum_silhouette_pixel_difference": min(silhouettes),
            "median_silhouette_pixel_difference": statistics.median(silhouettes),
        }
        if policy.get("diversity_mode") == "palette-study":
            # A palette study intentionally keeps one approved silhouette.  Its
            # alternatives are accepted by equipment-pixel color separation,
            # not by silhouette mutation.
            diversity["accepted"] = (
                max(differences) >= 8
                and diversity["median_equipment_pixel_difference"] >= 8
            )
        elif policy.get("diversity_mode") == "preserved-original":
            diversity["accepted"] = (
                max(differences) == 0 and max(silhouettes) == 0
            )
        else:
            diversity["accepted"] = (
                diversity["minimum_equipment_pixel_difference"] >= 8
                and diversity["median_equipment_pixel_difference"] >= 28
                and diversity["median_silhouette_pixel_difference"] >= 5
            )
        diversity["mode"] = policy.get("diversity_mode", "silhouette-and-palette")
        diversity_reports.append(diversity)
        row = Image.new("RGBA", (760, 236), (18, 21, 19, 255))
        for index, panel in enumerate(panels):
            row.alpha_composite(panel, (152 * index, 0))
        row.save(root / "contact-sheet.png", optimize=True)
        contact_rows.append((group, row))
        manifest_groups.append({
            "id": group["id"],
            "commander_id": group["commander_id"],
            "class_id": group["class_id"],
            "title": group["title"],
            "description": policy.get(
                "group_description",
                "원본 크기·자세·팔레트 제한 없이 얼굴 경계만 고정한 중앙 정렬 5안",
            ),
            "expected_sample_count": 5,
            "complete": True,
            "samples": samples,
        })
    master = Image.new("RGBA", (760, 260 * len(contact_rows)), (14, 17, 15, 255))
    draw = ImageDraw.Draw(master)
    offset = 0
    for group, row in contact_rows:
        draw.text((6, offset + 5), group["title"], fill=(235, 240, 236, 255))
        master.alpha_composite(row, (0, offset + 24))
        offset += 260
    master_path = SOURCE_ROOT / "all-ai-and-logical16.png"
    master.convert("RGB").save(master_path, optimize=True)
    commander_sheets = {}
    commander_root = SOURCE_ROOT / "contact-sheets/commanders"
    commander_root.mkdir(parents=True, exist_ok=True)
    for commander_id in sorted({int(group["commander_id"]) for group, _ in contact_rows}):
        selected = [(group, row) for group, row in contact_rows if int(group["commander_id"]) == commander_id]
        sheet = Image.new("RGBA", (760, 260 * len(selected)), (14, 17, 15, 255))
        sheet_draw = ImageDraw.Draw(sheet)
        y = 0
        for group, row in selected:
            sheet_draw.text((6, y + 5), group["title"], fill=(235, 240, 236, 255))
            sheet.alpha_composite(row, (0, y + 24))
            y += 260
        path = commander_root / f"{commander_id:02d}-{COMMANDERS[commander_id][0]}.png"
        sheet.convert("RGB").save(path, optimize=True)
        commander_sheets[f"commander_{commander_id}"] = str(path.relative_to(ROOT))
    validation = {
        "asset_version": ASSET_VERSION,
        "sample_count": len(reports),
        "accepted_count": sum(row["accepted"] for row in reports),
        "all_accepted": all(row["accepted"] for row in reports) and all(row["accepted"] for row in diversity_reports),
        "samples": reports,
        "diversity_groups": diversity_reports,
    }
    write_json(SOURCE_ROOT / "validation-report.json", validation)
    manifest = {
        "asset_version": ASSET_VERSION,
        "layout": "vertical-groups-horizontal-five",
        "partial": False,
        "ready_group_count": len(groups),
        "expected_group_count": len(groups),
        "ready_candidate_count": len(groups) * 5,
        "expected_candidate_count": len(groups) * 5,
        "groups": manifest_groups,
        "review_sheets": {"all": str(master_path.relative_to(ROOT)), **commander_sheets},
    }
    write_json(STATIC_ROOT / "manifest.json", manifest)
    write_json(STATIC_ROOT / "validation-report.json", validation)
    print(f"published {len(groups)} groups / {len(reports)} centered free samples")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "ingest", "publish"))
    parser.add_argument("--group")
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
        print(f"prepared {len(active_campaign_groups())} free-five reference packs")
    elif args.action == "ingest":
        if not args.group or not args.source:
            parser.error("ingest requires --group and --source")
        ingest_board(args.group, args.source)
    else:
        publish()


if __name__ == "__main__":
    main()
