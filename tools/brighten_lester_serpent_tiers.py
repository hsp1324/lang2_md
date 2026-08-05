#!/usr/bin/env python3
"""Brighten Lester's approved Serpent Lord and Serpent Master mount colors."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "editor/static/ai-class-sprites"
MOUNT_MASKS = ROOT / "editor/ai_mount_masks.json"
IDENTITY_MASKS = ROOT / "editor/ai_identity_masks.json"
MANIFEST = LIVE / "manifest.json"
OUTPUT = (
    ROOT
    / "docs/assets/ai-class-source/latest/lester-serpent-bright-v1"
)
MASTER = OUTPUT / "master"
LOGICAL = OUTPUT / "logical16"
PREVIEWS = OUTPUT / "previews"
ASSET_VERSION = "liana-lana-healer-shared-v106"
KNIGHT = (9, 0x10)
TARGETS = ((9, 0x1F), (9, 0x2A))
MAPS = {
    (9, 0x1F): {
        (0, 0, 219, 255): (73, 109, 255, 255),
        (73, 0, 146, 255): (109, 36, 219, 255),
        (146, 73, 182, 255): (182, 109, 255, 255),
        (219, 36, 109, 255): (255, 73, 146, 255),
    },
    (9, 0x2A): {
        (0, 0, 219, 255): (73, 109, 255, 255),
        (146, 0, 0, 255): (219, 0, 0, 255),
        (219, 36, 36, 255): (255, 73, 73, 255),
        (255, 109, 109, 255): (255, 146, 109, 255),
    },
}
NAMES = {
    (9, 0x10): "서펜나이트 원본 청색",
    (9, 0x1F): "서펜로드 밝은 보라·연보라·청색",
    (9, 0x2A): "서펜마스터 밝은 적색·주홍·청색",
}


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def palette(image: Image.Image, limit: int | None = None) -> list[str]:
    counts = Counter(color for color in image.get_flattened_data() if color[3])
    return [
        "#%02x%02x%02x" % color[:3]
        for color, _ in counts.most_common(limit)
    ]


def ensure_snapshots() -> None:
    for directory in (MASTER, LOGICAL, PREVIEWS):
        directory.mkdir(parents=True, exist_ok=True)
    for commander_id, class_id in (KNIGHT, *TARGETS):
        target = MASTER / f"{commander_id:02d}-{class_id:02X}-before.png"
        if not target.is_file():
            shutil.copy2(
                LIVE / str(commander_id) / f"{class_id:02X}.png",
                target,
            )


def build() -> dict[str, object]:
    ensure_snapshots()
    mounts = json.loads(MOUNT_MASKS.read_text(encoding="utf-8"))["masks"]
    identities = json.loads(
        IDENTITY_MASKS.read_text(encoding="utf-8")
    )["masks"]
    reports = []
    for commander_id, class_id in (KNIGHT, *TARGETS):
        key = (commander_id, class_id)
        base = Image.open(
            MASTER / f"{commander_id:02d}-{class_id:02X}-before.png"
        ).convert("RGBA")
        result = base.copy()
        mount = {
            tuple(point)
            for point in mounts.get(f"{commander_id}:{class_id:02X}", [])
        }
        identity = {
            tuple(point)
            for point in identities.get(f"{commander_id}:{class_id:02X}", [])
        }
        changed = set()
        for point in mount - identity:
            replacement = MAPS.get(key, {}).get(result.getpixel(point))
            if replacement is not None:
                result.putpixel(point, replacement)
                changed.add(point)
        output = LOGICAL / f"{commander_id:02d}-{class_id:02X}.png"
        result.save(output, optimize=True)
        result.resize((512, 512), Image.Resampling.NEAREST).save(
            PREVIEWS / f"{commander_id:02d}-{class_id:02X}.png",
            optimize=True,
        )
        identity_match = sum(
            result.getpixel(point) == base.getpixel(point)
            for point in identity
        )
        outside_match = sum(
            result.getpixel((x, y)) == base.getpixel((x, y))
            for y in range(16)
            for x in range(16)
            if (x, y) not in mount
        )
        outside_total = 256 - len(mount)
        colors = palette(result)
        empty_rows = [
            y for y in range(16)
            if not any(result.getpixel((x, y))[3] for x in range(16))
        ]
        empty_columns = [
            x for x in range(16)
            if not any(result.getpixel((x, y))[3] for y in range(16))
        ]
        expected = 0 if key == KNIGHT else 75
        accepted = (
            identity_match == len(identity)
            and outside_match == outside_total
            and len(changed) == expected
            and len(colors) <= 15
            and not empty_rows
            and not empty_columns
            and (0, 0, 0, 255) not in result.get_flattened_data()
        )
        reports.append(
            {
                "commander_id": commander_id,
                "class_id": f"{class_id:02X}",
                "name": NAMES[key],
                "file": f"logical16/{commander_id:02d}-{class_id:02X}.png",
                "changed_mount_pixel_count": len(changed),
                "identity_match": identity_match,
                "identity_pixel_count": len(identity),
                "outside_mount_match": outside_match,
                "outside_mount_total": outside_total,
                "visible_color_count": len(colors),
                "palette": colors,
                "accepted": accepted,
            }
        )

    board = Image.new("RGBA", (1536, 560), (22, 25, 23, 255))
    draw = ImageDraw.Draw(board)
    for index, row in enumerate(reports):
        x = index * 512
        draw.text((x + 10, 12), row["name"], fill=(240, 240, 240, 255))
        image = Image.open(OUTPUT / row["file"]).convert("RGBA").resize(
            (512, 512), Image.Resampling.NEAREST
        )
        board.alpha_composite(image, (x, 48))
    board.convert("RGB").save(OUTPUT / "all-lester-serpent-tiers.png", optimize=True)
    report = {
        "version": 1,
        "rule": "keep approved serpent geometry and black outline; brighten only mount color surfaces",
        "all_accepted": all(row["accepted"] for row in reports),
        "classes": reports,
    }
    write_json(OUTPUT / "validation-report.json", report)
    return report


def apply_live(report: dict[str, object]) -> None:
    if not report["all_accepted"]:
        raise ValueError("refusing to apply rejected Lester serpent colors")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for commander_id, class_id in TARGETS:
        source = Image.open(
            LOGICAL / f"{commander_id:02d}-{class_id:02X}.png"
        ).convert("RGBA")
        source.save(LIVE / str(commander_id) / f"{class_id:02X}.png", optimize=True)
        source.resize((512, 512), Image.Resampling.NEAREST).save(
            LIVE / f"source-cells/{commander_id}-{class_id:02X}.png",
            optimize=True,
        )
        row = manifest["commanders"][str(commander_id)]["classes"][str(class_id)]
        row["ai_source_kind"] = "원작 서펜 기마 형태 + 밝은 단계별 탈것색"
        row["ai_source_position"] = (
            "latest/lester-serpent-bright-v1/logical16/"
            f"{commander_id:02d}-{class_id:02X}.png"
        )
        row["source_palette"] = palette(source, 6)
        row["pixel_palette"] = palette(source, 6)
        row["feature"] = (
            "서펜나이트 원본 청색 유지·서펜로드는 밝은 보라·연보라·"
            "청색·서펜마스터는 밝은 적색·주홍·청색·기수·얼굴·무기·"
            "바다뱀 좌표와 검은 외곽선 유지"
        )
    manifest["asset_version"] = ASSET_VERSION
    write_json(MANIFEST, manifest)


def main() -> int:
    report = build()
    apply_live(report)
    print(
        json.dumps(
            {
                "all_accepted": report["all_accepted"],
                "targets": ["9:10", "9:1F", "9:2A"],
                "asset_version": ASSET_VERSION,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
