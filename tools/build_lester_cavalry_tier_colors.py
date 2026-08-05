#!/usr/bin/env python3
"""Separate Lester's Knight, Highlander, and Knight Master mount tiers."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "editor/static/ai-class-sprites"
MASKS = ROOT / "editor/ai_mount_masks.json"
IDENTITY_MASKS = ROOT / "editor/ai_identity_masks.json"
MANIFEST = LIVE / "manifest.json"
OUTPUT = (
    ROOT
    / "docs/assets/ai-class-source/latest/lester-cavalry-tier-colors-v1"
)
MASTER = OUTPUT / "master"
LOGICAL = OUTPUT / "logical16"
PREVIEWS = OUTPUT / "previews"
ASSET_VERSION = "liana-lana-healer-shared-v106"

KNIGHT = (9, 0x05)
TARGETS = ((9, 0x0C), (9, 0x1B))
MAPS = {
    (9, 0x0C): {
        (73, 73, 109, 255): (36, 73, 146, 255),
        (109, 73, 36, 255): (36, 73, 146, 255),
        (182, 182, 182, 255): (109, 182, 255, 255),
    },
    (9, 0x1B): {
        (73, 73, 109, 255): (109, 0, 0, 255),
        (146, 73, 36, 255): (109, 0, 0, 255),
        (182, 182, 146, 255): (255, 109, 36, 255),
    },
}
NAMES = {
    (9, 0x05): "나이트 원본 갈색·회색 말",
    (9, 0x0C): "하이랜더 남청·청백색 말",
    (9, 0x1B): "나이트마스터 암적·주홍색 말",
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
        path = MASTER / f"{commander_id:02d}-{class_id:02X}-before.png"
        if not path.is_file():
            shutil.copy2(
                LIVE / str(commander_id) / f"{class_id:02X}.png",
                path,
            )


def build() -> dict[str, object]:
    ensure_snapshots()
    mount_masks = json.loads(MASKS.read_text(encoding="utf-8"))["masks"]
    identity_masks = json.loads(
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
            for point in mount_masks.get(f"{commander_id}:{class_id:02X}", [])
        }
        identity = {
            tuple(point)
            for point in identity_masks.get(
                f"{commander_id}:{class_id:02X}", []
            )
        }
        changed_points = set()
        for point in mount - identity:
            color = result.getpixel(point)
            replacement = MAPS.get(key, {}).get(color)
            if replacement is not None:
                result.putpixel(point, replacement)
                changed_points.add(point)

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
        outside_mount_match = sum(
            result.getpixel((x, y)) == base.getpixel((x, y))
            for y in range(16)
            for x in range(16)
            if (x, y) not in mount
        )
        outside_mount_total = 256 - len(mount)
        colors = palette(result)
        empty_rows = [
            y for y in range(16)
            if not any(result.getpixel((x, y))[3] for x in range(16))
        ]
        empty_columns = [
            x for x in range(16)
            if not any(result.getpixel((x, y))[3] for y in range(16))
        ]
        expected_changes = 0 if key == KNIGHT else 37
        accepted = (
            identity_match == len(identity)
            and outside_mount_match == outside_mount_total
            and len(changed_points) >= expected_changes
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
                "mount_pixel_count": len(mount),
                "changed_mount_pixel_count": len(changed_points),
                "identity_match": identity_match,
                "identity_pixel_count": len(identity),
                "outside_mount_match": outside_mount_match,
                "outside_mount_total": outside_mount_total,
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
    board.convert("RGB").save(OUTPUT / "all-lester-cavalry-tiers.png", optimize=True)
    report = {
        "version": 1,
        "rule": (
            "keep stock rider, weapon, horse geometry; Knight stays brown, "
            "Highlander becomes blue, Knight Master becomes red"
        ),
        "all_accepted": all(row["accepted"] for row in reports),
        "classes": reports,
    }
    write_json(OUTPUT / "validation-report.json", report)
    return report


def apply_live(report: dict[str, object]) -> None:
    if not report["all_accepted"]:
        raise ValueError("refusing to apply rejected Lester cavalry colors")
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
        row["ai_source_kind"] = "원작 ROM 기마 형태 + 레스터 단계별 탈것색"
        row["ai_source_position"] = (
            "latest/lester-cavalry-tier-colors-v1/logical16/"
            f"{commander_id:02d}-{class_id:02X}.png"
        )
        row["source_palette"] = palette(source, 6)
        row["pixel_palette"] = palette(source, 6)
        row["feature"] = (
            "나이트 원본 갈색·회색 말 유지·하이랜더는 남청·청백색·"
            "나이트마스터는 암적·주홍색으로 단계 강화·원작 기수·얼굴·"
            "갑옷·무기·탈것 좌표와 흰 하이라이트 유지"
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
                "targets": ["9:05", "9:0C", "9:1B"],
                "asset_version": ASSET_VERSION,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
