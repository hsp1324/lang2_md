#!/usr/bin/env python3
"""Share the latest hand-edited Keith Wizard across 25/26/28 classes."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil
import sys
import time

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.pillow_compat import flattened_image_data  # noqa: E402


OUTPUT = ROOT / "assets/class-sprites/source/latest/shared-keith-wizard-new-classes-v1"
MASTER_LIVE = ROOT / "editor/static/ai-class-sprites/7/15.png"
LIVE = ROOT / "editor/static/ai-class-sprites"
MASK_FILE = ROOT / "editor/ai_identity_masks.json"
MANIFEST = LIVE / "manifest.json"
OVERRIDES = ROOT / "editor/ai_class_design_overrides.json"
TRANSPARENT = (0, 0, 0, 0)

TARGETS = (
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
)

SCHEMES = {
    (2, 0x25): ((109, 0, 0, 255), (219, 0, 0, 255), (255, 109, 109, 255), "진홍·금색 에이전트"),
    (3, 0x25): ((0, 0, 109, 255), (0, 73, 219, 255), (109, 219, 255, 255), "남청·하늘색 에이전트"),
    (2, 0x26): ((73, 0, 109, 255), (146, 36, 182, 255), (219, 109, 255, 255), "자주·연보라 자베러"),
    (3, 0x26): ((0, 73, 73, 255), (0, 146, 146, 255), (109, 219, 219, 255), "청록·민트 자베러"),
    (5, 0x26): ((73, 36, 109, 255), (146, 73, 182, 255), (219, 146, 255, 255), "보라·연보라 자베러"),
    # Zarvera is the final class in Lester's Mage -> Archmage branch. Reuse
    # Archmage's crimson shadow, royal-blue cloth, and gold highlight instead
    # of the unrelated emerald ramp.
    (9, 0x26): ((146, 0, 36, 255), (36, 73, 219, 255), (255, 182, 36, 255), "아크메이지 연계 적·청·금 자베러"),
    (10, 0x26): ((36, 36, 109, 255), (73, 73, 219, 255), (182, 146, 255, 255), "남보라·라벤더 자베러"),
    (2, 0x28): ((109, 36, 0, 255), (219, 73, 0, 255), (255, 182, 73, 255), "주홍·금색 서머너"),
    (3, 0x28): ((0, 36, 146, 255), (36, 109, 219, 255), (146, 219, 255, 255), "코발트·빙청 서머너"),
    (5, 0x28): ((36, 73, 0, 255), (36, 146, 36, 255), (219, 182, 109, 255), "숲초록·금색 서머너"),
    (10, 0x28): ((73, 0, 73, 255), (146, 0, 146, 255), (219, 109, 219, 255), "와인·마젠타 서머너"),
}

MASTER_MAIN = (146, 36, 182, 255)
MASTER_DARK = (73, 73, 182, 255)
MASTER_MAGIC = (0, 0, 255, 255)
MASTER_RED = (219, 0, 0, 255)
MASTER_RED_LIGHT = (255, 146, 109, 255)
ROLE_INDEX = {
    MASTER_MAIN: 1,
    MASTER_DARK: 0,
    MASTER_MAGIC: 2,
    MASTER_RED: 1,
    MASTER_RED_LIGHT: 2,
}


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def flat_pixels(image: Image.Image) -> list[list[int]]:
    return [
        list(color)
        for color in flattened_image_data(image.convert("RGBA"))
    ]


def palette(image: Image.Image) -> list[str]:
    counts = Counter(color for color in flattened_image_data(image) if color[3])
    return ["#%02x%02x%02x" % color[:3] for color, _ in counts.most_common()]


def nearest(
    color: tuple[int, int, int, int],
    choices: set[tuple[int, int, int, int]],
) -> tuple[int, int, int, int]:
    return min(
        choices,
        key=lambda target: sum(
            (color[channel] - target[channel]) ** 2 for channel in range(3)
        ),
    )


def points_for(
    commander_id: int,
    class_id: int,
    masks: dict[str, list[list[int]]],
    manifest: dict,
) -> set[tuple[int, int]]:
    saved = masks.get(f"{commander_id}:{class_id:02X}", [])
    raw = (
        saved
        if saved
        else manifest["commanders"][str(commander_id)]["classes"][str(class_id)]["identity_lock_points"]
    )
    return {tuple(point) for point in raw}


def build_variant(
    master: Image.Image,
    master_points: set[tuple[int, int]],
    identity: Image.Image,
    target_points: set[tuple[int, int]],
    scheme: tuple,
) -> Image.Image:
    dark, main, light, _ = scheme
    identity_colors = {
        identity.getpixel(point)
        for point in target_points
        if identity.getpixel(point)[3]
    }
    allowed = set(identity_colors)
    for color in (main, dark, light):
        if len(allowed) < 15:
            allowed.add(color)
    if not allowed:
        raise ValueError("target identity palette is empty")

    result = master.copy()
    for point in master_points:
        result.putpixel(point, TRANSPARENT)
    ramp = (dark, main, light)
    for y in range(16):
        for x in range(16):
            point = (x, y)
            color = result.getpixel(point)
            if not color[3]:
                continue
            if color in ROLE_INDEX:
                wanted = ramp[ROLE_INDEX[color]]
                result.putpixel(point, wanted if wanted in allowed else nearest(wanted, allowed))
            else:
                result.putpixel(point, color if color in allowed else nearest(color, allowed))

    # Restore the target's current head/hair across the full master-head area.
    # Transparent selected target points retain equipment-priority pixels.
    for point in master_points | target_points:
        color = identity.getpixel(point)
        if color[3]:
            result.putpixel(point, color)

    # A large identity palette can leave fewer than three free equipment slots.
    # Compress only equipment pixels while keeping every visible target point exact.
    visible = {color for color in flattened_image_data(result) if color[3]}
    if len(visible) > 15:
        locked = {
            identity.getpixel(point)
            for point in target_points
            if identity.getpixel(point)[3]
        }
        equipment_counts = Counter(
            result.getpixel((x, y))
            for y in range(16)
            for x in range(16)
            if (x, y) not in target_points and result.getpixel((x, y))[3]
        )
        final_allowed = set(locked)
        for color, _ in equipment_counts.most_common():
            if len(final_allowed) == 15:
                break
            final_allowed.add(color)
        for y in range(16):
            for x in range(16):
                point = (x, y)
                color = result.getpixel(point)
                if point in target_points or not color[3] or color in final_allowed:
                    continue
                result.putpixel(point, nearest(color, final_allowed))
        for point in target_points:
            if identity.getpixel(point)[3]:
                result.putpixel(point, identity.getpixel(point))
    return result


def font() -> ImageFont.ImageFont:
    path = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc")
    return ImageFont.truetype(str(path), 13) if path.is_file() else ImageFont.load_default()


def main() -> None:
    for child in ("master", "logical16", "previews", "previous", "references"):
        (OUTPUT / child).mkdir(parents=True, exist_ok=True)
    master_path = OUTPUT / "master/07-15-keith-user-edited.png"
    if not master_path.is_file():
        shutil.copy2(MASTER_LIVE, master_path)
    master = Image.open(master_path).convert("RGBA")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    masks = json.loads(MASK_FILE.read_text(encoding="utf-8"))["masks"]
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    master_points = points_for(7, 0x15, masks, manifest)
    reports = []

    for sequence, (commander_id, class_id) in enumerate(TARGETS):
        key = f"{commander_id}:{class_id:02X}"
        live_path = LIVE / str(commander_id) / f"{class_id:02X}.png"
        previous_path = OUTPUT / f"previous/{commander_id:02d}-{class_id:02X}.png"
        identity_path = OUTPUT / f"references/{commander_id:02d}-{class_id:02X}-identity.png"
        if not previous_path.is_file():
            shutil.copy2(live_path, previous_path)
        if not identity_path.is_file():
            shutil.copy2(live_path, identity_path)
        identity = Image.open(identity_path).convert("RGBA")
        target_points = points_for(commander_id, class_id, masks, manifest)
        result = build_variant(
            master,
            master_points,
            identity,
            target_points,
            SCHEMES[(commander_id, class_id)],
        )
        colors = palette(result)
        visible_points = {
            point for point in target_points if identity.getpixel(point)[3]
        }
        matches = sum(
            result.getpixel(point) == identity.getpixel(point)
            for point in visible_points
        )
        empty_rows = [
            y for y in range(16)
            if not any(result.getpixel((x, y))[3] for x in range(16))
        ]
        empty_columns = [
            x for x in range(16)
            if not any(result.getpixel((x, y))[3] for y in range(16))
        ]
        accepted = (
            matches == len(visible_points)
            and len(colors) <= 15
            and (0, 0, 0, 255) not in flattened_image_data(result)
            and (255, 0, 255, 255) not in flattened_image_data(result)
            and not empty_rows
            and not empty_columns
        )
        if not accepted:
            raise ValueError(f"{key} failed validation")

        logical_path = OUTPUT / f"logical16/{commander_id:02d}-{class_id:02X}.png"
        result.save(logical_path, optimize=True)
        result.resize((512, 512), Image.Resampling.NEAREST).save(
            OUTPUT / f"previews/{commander_id:02d}-{class_id:02X}.png",
            optimize=True,
        )
        result.save(live_path, optimize=True)
        result.resize((512, 512), Image.Resampling.NEAREST).save(
            LIVE / f"source-cells/{commander_id}-{class_id:02X}.png",
            optimize=True,
        )

        revision = time.time_ns() + sequence
        overrides["designs"][key] = {
            "revision": revision,
            "pixels": flat_pixels(result),
            "base_pixels": flat_pixels(Image.open(previous_path).convert("RGBA")),
        }
        row = manifest["commanders"][str(commander_id)]["classes"][str(class_id)]
        row["identity_lock_points"] = [list(point) for point in sorted(target_points)]
        row["identity_mask_pending_rebuild"] = False
        row["design_override"] = True
        row["design_revision"] = revision
        row["design_override_superseded"] = False
        row["superseded_design_revision"] = 0
        row["pixel_palette"] = colors
        row["source_kind"] = "키스 사용자 편집 위저드 기반 공통 신규 클래스"
        row["source_position"] = f"latest/shared-keith-wizard-new-classes-v1/logical16/{commander_id:02d}-{class_id:02X}.png"
        marker = "·키스 사용자 편집 위저드 장비 좌표·캐릭터·클래스별 전용 색감"
        if marker not in row.get("feature", ""):
            row["feature"] = row.get("feature", "") + marker
        reports.append(
            {
                "commander_id": commander_id,
                "class_id": f"{class_id:02X}",
                "file": f"logical16/{commander_id:02d}-{class_id:02X}.png",
                "palette_name": SCHEMES[(commander_id, class_id)][3],
                "identity_matches": matches,
                "identity_visible": len(visible_points),
                "visible_color_count": len(colors),
                "palette": colors,
                "empty_rows": empty_rows,
                "empty_columns": empty_columns,
                "accepted": accepted,
            }
        )

    write_json(OVERRIDES, overrides)
    write_json(MANIFEST, manifest)

    columns = 6
    card_w, card_h = 230, 275
    rows = (len(reports) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * card_w, rows * card_h), (18, 18, 18))
    draw = ImageDraw.Draw(canvas)
    label_font = font()
    for index, report in enumerate(reports):
        x = index % columns * card_w
        y = index // columns * card_h
        draw.rectangle((x + 4, y + 4, x + card_w - 5, y + card_h - 5), outline=(70, 175, 90), width=2)
        draw.text((x + 10, y + 9), f"{report['commander_id']}:{report['class_id']} {report['palette_name']}", fill="white", font=label_font)
        image = Image.open(OUTPUT / report["file"]).convert("RGB").resize((208, 208), Image.Resampling.NEAREST)
        canvas.paste(image, (x + 11, y + 44))
        draw.text((x + 10, y + 254), f"face {report['identity_matches']}/{report['identity_visible']} colors {report['visible_color_count']}", fill=(190, 200, 190), font=label_font)
    canvas.save(OUTPUT / "all-keith-wizard-derived-classes.png", optimize=True)
    write_json(
        OUTPUT / "validation-report.json",
        {
            "master": "7:15 latest user-edited Keith Wizard",
            "master_file": "master/07-15-keith-user-edited.png",
            "target_count": len(TARGETS),
            "all_accepted": all(row["accepted"] for row in reports),
            "classes": reports,
        },
    )
    print(f"applied Keith Wizard design to {len(TARGETS)} Agent/Zarvera/Summoner targets")


if __name__ == "__main__":
    main()
