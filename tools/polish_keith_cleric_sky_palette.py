#!/usr/bin/env python3
# ruff: noqa: E402
"""Give Keith Healer and Priest the approved royal/sky-blue class palette."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_refined_recent_class_variants import write_contact
from tools.build_shared_hein_class_variants import write_comparison
from tools.pillow_compat import flattened_image_data


LIVE_ROOT = ROOT / "editor/static/ai-class-sprites"
MANIFEST = LIVE_ROOT / "manifest.json"
ASSET_VERSION = "liana-lana-healer-shared-v106"

HEALER_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/shared-new-classes-v2-refined"
)
PRIEST_ROOT = (
    ROOT / "assets/class-sprites/source/latest/shared-hein-classes-v1"
)

TARGETS = {
    0x08: {
        "root": HEALER_ROOT,
        "map": {
            (0, 146, 109, 255): (73, 109, 255, 255),
            (36, 219, 146, 255): (109, 219, 255, 255),
        },
        "label": "힐러",
    },
    0x11: {
        "root": PRIEST_ROOT,
        "map": {
            (36, 146, 36, 255): (73, 109, 255, 255),
            (109, 219, 146, 255): (109, 219, 255, 255),
        },
        "label": "프리스트",
    },
}


def palette(image: Image.Image) -> list[str]:
    counts = Counter(
        color for color in flattened_image_data(image) if color[3]
    )
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common()
    ]


def recolor(
    image: Image.Image,
    mapping: dict[
        tuple[int, int, int, int], tuple[int, int, int, int]
    ],
) -> tuple[Image.Image, int]:
    result = image.copy().convert("RGBA")
    changed = 0
    for y in range(16):
        for x in range(16):
            color = result.getpixel((x, y))
            if color in mapping:
                result.putpixel((x, y), mapping[color])
                changed += 1
    return result, changed


def update_report(
    root: Path,
    class_id: int,
    image: Image.Image,
) -> None:
    path = root / "validation-report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    row = next(
        item
        for item in report["classes"]
        if int(item["commander_id"]) == 7
        and int(item["class_id"], 16) == class_id
    )
    colors = palette(image)
    row["visible_color_count"] = len(colors)
    row["palette"] = colors
    row["empty_rows"] = [
        y
        for y in range(16)
        if not any(image.getpixel((x, y))[3] for x in range(16))
    ]
    row["empty_columns"] = [
        x
        for x in range(16)
        if not any(image.getpixel((x, y))[3] for y in range(16))
    ]
    row["accepted"] = (
        len(colors) <= 15
        and not row["empty_rows"]
        and not row["empty_columns"]
    )
    row["sky_blue_palette"] = True
    row.pop("unchanged_from_v1", None)
    report["all_accepted"] = all(
        bool(item["accepted"]) for item in report["classes"]
    )
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []

    for class_id, spec in TARGETS.items():
        source = spec["root"] / f"logical16/07-{class_id:02X}.png"
        live = LIVE_ROOT / f"7/{class_id:02X}.png"
        previous = spec["root"] / f"previous/07-{class_id:02X}-before-sky.png"
        previous.parent.mkdir(parents=True, exist_ok=True)
        if not previous.is_file():
            shutil.copy2(source, previous)

        result, changed = recolor(
            Image.open(source).convert("RGBA"), spec["map"]
        )
        colors = palette(result)
        if changed == 0 and not {
            (73, 109, 255, 255),
            (109, 219, 255, 255),
        }.issubset(set(flattened_image_data(result))):
            raise ValueError(f"07-{class_id:02X}: no cleric colors changed")
        if len(colors) > 15:
            raise ValueError(
                f"07-{class_id:02X}: {len(colors)} visible colors"
            )

        result.save(source, optimize=True)
        result.save(live, optimize=True)
        preview = spec["root"] / f"previews/07-{class_id:02X}.png"
        preview.parent.mkdir(parents=True, exist_ok=True)
        result.resize((512, 512), Image.Resampling.NEAREST).save(
            preview, optimize=True
        )
        result.resize((512, 512), Image.Resampling.NEAREST).save(
            LIVE_ROOT / f"source-cells/7-{class_id:02X}.png",
            optimize=True,
        )
        update_report(spec["root"], class_id, result)

        original = Image.open(
            ROOT
            / f"editor/static/class-sprites/commanders/7/{class_id:02X}-p1.png"
        ).convert("RGBA")
        row = manifest["commanders"]["7"]["classes"][str(class_id)]
        row["source_palette"] = colors[:6]
        row["pixel_palette"] = colors[:12]
        row["changed_pixel_count"] = sum(
            result.getpixel((x, y)) != original.getpixel((x, y))
            for y in range(16)
            for x in range(16)
        )
        row["feature"] = (
            row.get("feature", "")
            + "·키스 로드·세인트 계열과 같은 진청·파랑·하늘색 성직복"
        )
        results.append(
            {
                "target": f"7:{class_id:02X}",
                "class": spec["label"],
                "changed_pixels": changed,
                "visible_colors": len(colors),
            }
        )

    manifest["asset_version"] = ASSET_VERSION
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    healer_report = json.loads(
        (HEALER_ROOT / "validation-report.json").read_text(
            encoding="utf-8"
        )
    )
    write_contact(healer_report["classes"])
    priest_report = json.loads(
        (PRIEST_ROOT / "validation-report.json").read_text(
            encoding="utf-8"
        )
    )
    write_comparison(priest_report["classes"])
    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
