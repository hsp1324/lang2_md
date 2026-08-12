#!/usr/bin/env python3
"""Share the latest user-edited Liana Healer design with blue Lana."""

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


OUTPUT = (
    ROOT
    / "assets/class-sprites/source/latest/shared-liana-lana-healer-v1"
)
LIVE_ROOT = ROOT / "editor/static/ai-class-sprites"
MANIFEST = LIVE_ROOT / "manifest.json"
MASKS = ROOT / "editor/ai_identity_masks.json"
ASSET_VERSION = "liana-lana-healer-shared-v106"

RED_TO_BLUE = {
    (219, 0, 0, 255): (0, 36, 182, 255),
    (255, 109, 109, 255): (73, 109, 255, 255),
}


def palette(image: Image.Image) -> list[str]:
    counts = Counter(
        color for color in flattened_image_data(image) if color[3]
    )
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common()
    ]


def same_pixels(first: Image.Image, second: Image.Image) -> bool:
    return list(flattened_image_data(first)) == list(
        flattened_image_data(second)
    )


def recolor_lana(master: Image.Image) -> Image.Image:
    result = master.copy().convert("RGBA")
    for y in range(16):
        for x in range(16):
            color = result.getpixel((x, y))
            if color in RED_TO_BLUE:
                result.putpixel((x, y), RED_TO_BLUE[color])
    return result


def write_contact(liana: Image.Image, lana: Image.Image) -> None:
    canvas = Image.new("RGB", (512, 290), (24, 24, 24))
    draw = ImageDraw.Draw(canvas)
    font_path = Path(
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"
    )
    font = (
        ImageFont.truetype(str(font_path), 14)
        if font_path.is_file()
        else ImageFont.load_default()
    )
    for index, (label, image) in enumerate(
        (("리아나 힐러 2:08", liana), ("라나 힐러 3:08", lana))
    ):
        x = index * 256
        draw.text((x + 8, 8), label, fill="white", font=font)
        background = Image.new("RGBA", (16, 16), (35, 35, 35, 255))
        background.alpha_composite(image)
        canvas.paste(
            background.convert("RGB").resize(
                (256, 256), Image.Resampling.NEAREST
            ),
            (x, 34),
        )
    canvas.save(OUTPUT / "all-liana-lana-healer-variants.png", optimize=True)


def main() -> int:
    for child in ("master", "logical16", "previews", "previous"):
        (OUTPUT / child).mkdir(parents=True, exist_ok=True)

    liana_live_path = LIVE_ROOT / "2/08.png"
    lana_live_path = LIVE_ROOT / "3/08.png"
    master_path = OUTPUT / "master/02-08-liana-user-edited.png"
    current_liana = Image.open(liana_live_path).convert("RGBA")
    if master_path.is_file():
        old_master = Image.open(master_path).convert("RGBA")
        if not same_pixels(old_master, current_liana):
            archive = OUTPUT / (
                "previous/02-08-previous-master-" f"{time.time_ns()}.png"
            )
            shutil.copy2(master_path, archive)
    current_liana.save(master_path, optimize=True)

    for source, archive_name in (
        (
            ROOT
            / "assets/class-sprites/source/latest/"
            "shared-new-classes-v2-refined/logical16/02-08.png",
            "02-08-before-latest-user-edit.png",
        ),
        (lana_live_path, "03-08-before-liana-design.png"),
    ):
        archive = OUTPUT / "previous" / archive_name
        if not archive.is_file():
            shutil.copy2(source, archive)

    masks = json.loads(MASKS.read_text(encoding="utf-8"))["masks"]
    liana_original = Image.open(
        ROOT / "editor/static/class-sprites/commanders/2/08-p1.png"
    ).convert("RGBA")
    lana_original = Image.open(
        ROOT / "editor/static/class-sprites/commanders/3/08-p1.png"
    ).convert("RGBA")
    liana_points = {tuple(point) for point in masks["2:08"]}
    lana_points = {tuple(point) for point in masks["3:08"]}

    # The current Liana editor save is authoritative, but it must still retain
    # every visible point selected by the user's identity mask.
    for point in liana_points:
        if (
            liana_original.getpixel(point)[3]
            and current_liana.getpixel(point) != liana_original.getpixel(point)
        ):
            raise ValueError(f"Liana Healer identity mismatch at {point}")

    lana = recolor_lana(current_liana)
    for point in lana_points:
        color = lana_original.getpixel(point)
        if color[3]:
            lana.putpixel(point, color)

    images = {2: current_liana, 3: lana}
    originals = {2: liana_original, 3: lana_original}
    point_sets = {2: liana_points, 3: lana_points}
    reports: list[dict[str, object]] = []
    for commander_id, image in images.items():
        colors = palette(image)
        points = point_sets[commander_id]
        original = originals[commander_id]
        visible_points = {
            point for point in points if original.getpixel(point)[3]
        }
        matches = sum(
            image.getpixel(point) == original.getpixel(point)
            for point in visible_points
        )
        if matches != len(visible_points):
            raise ValueError(
                f"{commander_id}:08 identity {matches}/{len(visible_points)}"
            )
        if len(colors) > 15:
            raise ValueError(
                f"{commander_id}:08 has {len(colors)} visible colors"
            )
        logical = OUTPUT / f"logical16/{commander_id:02d}-08.png"
        image.save(logical, optimize=True)
        image.save(LIVE_ROOT / f"{commander_id}/08.png", optimize=True)
        enlarged = image.resize((512, 512), Image.Resampling.NEAREST)
        enlarged.save(
            OUTPUT / f"previews/{commander_id:02d}-08.png", optimize=True
        )
        enlarged.save(
            LIVE_ROOT / f"source-cells/{commander_id}-08.png",
            optimize=True,
        )
        reports.append(
            {
                "commander_id": commander_id,
                "commander_name": "리아나" if commander_id == 2 else "라나",
                "class_id": "08",
                "class_name": "힐러",
                "file": f"logical16/{commander_id:02d}-08.png",
                "identity_match": matches,
                "identity_pixel_count": len(visible_points),
                "mask_pixel_count": len(points),
                "visible_color_count": len(colors),
                "palette": colors,
                "accepted": True,
            }
        )

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["asset_version"] = ASSET_VERSION
    for report in reports:
        commander_id = int(report["commander_id"])
        row = manifest["commanders"][str(commander_id)]["classes"][str(0x08)]
        row["identity_lock_points"] = [
            list(point) for point in sorted(point_sets[commander_id])
        ]
        row["identity_lock_pixel_count"] = len(point_sets[commander_id])
        row["identity_mask_pending_rebuild"] = False
        row["ai_source_kind"] = (
            "최신 리아나 사용자 편집 힐러 기반 리아나·라나 공통 디자인"
        )
        row["ai_source_position"] = (
            "latest/shared-liana-lana-healer-v1/logical16/"
            f"{commander_id:02d}-08.png"
        )
        row["pixel_palette"] = report["palette"]
        row["source_palette"] = report["palette"][:6]
        row["changed_pixel_count"] = sum(
            images[commander_id].getpixel((x, y))
            != originals[commander_id].getpixel((x, y))
            for y in range(16)
            for x in range(16)
        )
        marker = (
            "·최신 리아나 사용자 편집 힐러 장비 좌표 공유·"
            + (
                "리아나 붉은 직업색 유지"
                if commander_id == 2
                else "라나 파랑·하늘색 직업색 변형"
            )
        )
        if marker not in row.get("feature", ""):
            row["feature"] = row.get("feature", "") + marker
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    report = {
        "version": 1,
        "asset_version": ASSET_VERSION,
        "master": "master/02-08-liana-user-edited.png",
        "palette_map": {
            "#DB0000": "#0024B6",
            "#FF6D6D": "#496DFF",
        },
        "all_accepted": True,
        "classes": reports,
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_contact(current_liana, lana)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
