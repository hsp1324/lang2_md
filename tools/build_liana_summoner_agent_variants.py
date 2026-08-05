#!/usr/bin/env python3
"""Share the latest user-edited Liana Summoner with the twin magic classes."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import time

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "editor/static/ai-class-sprites"
MANIFEST = LIVE / "manifest.json"
OVERRIDES = ROOT / "editor/ai_class_design_overrides.json"
OUTPUT = (
    ROOT
    / "docs/assets/ai-class-source/latest/"
    "shared-liana-summoner-agent-v1"
)
SUMMONER_MASTER = OUTPUT / "master/02-28-liana-user-edited.png"
AGENT_MASTER = OUTPUT / "master/02-25-liana-agent-preserved.png"
ZARVERA_MASTER = OUTPUT / "master/02-26-liana-zarvera-preserved.png"
CLASS_MASTERS = OUTPUT / "class-masters"
LOGICAL = OUTPUT / "logical16"
PREVIEWS = OUTPUT / "previews"
ARCHIVE = OUTPUT / "archive/before-liana-summoner-template"
MASTER_KEY = (2, 0x28)
TARGETS = (
    (2, 0x25),
    (2, 0x26),
    (3, 0x28),
    (3, 0x25),
    (3, 0x26),
)
ALL_KEYS = (MASTER_KEY, *TARGETS)
ASSET_VERSION = "liana-lana-healer-shared-v106"

# Summoner and Agent have separate 16x16 masters. Only each master's garment
# roles change between Liana and Lana; the two classes never share geometry.
SUMMONER_ROLE_COLORS = {
    "main": (219, 73, 0, 255),
    "accent": (219, 0, 0, 255),
    "light": (255, 182, 73, 255),
    "shadow": (109, 0, 0, 255),
    "deep": (109, 36, 0, 255),
}
AGENT_ROLE_COLORS = {
    "main": (219, 0, 0, 255),
    "shadow": (109, 0, 0, 255),
    "light": (255, 109, 109, 255),
    "trim": (255, 182, 0, 255),
}
ZARVERA_ROLE_COLORS = {
    "shadow": (73, 0, 109, 255),
    "main": (146, 36, 182, 255),
    "light": (219, 109, 255, 255),
    "accent": (219, 0, 0, 255),
}
LANA_ZARVERA_ROLE_COLORS = {
    "shadow": (0, 0, 219, 255),
    "main": (73, 109, 255, 255),
    "light": (109, 219, 255, 255),
    "accent": (0, 36, 182, 255),
}
SCHEMES = {
    (2, 0x28): ({}, {}, "리아나 주홍·금색 서머너 원본"),
    (2, 0x25): (
        {
            AGENT_ROLE_COLORS["main"]: (146, 0, 73, 255),
            AGENT_ROLE_COLORS["shadow"]: (73, 0, 73, 255),
            AGENT_ROLE_COLORS["light"]: (219, 109, 182, 255),
            AGENT_ROLE_COLORS["trim"]: (219, 0, 0, 255),
        },
        {
            SUMMONER_ROLE_COLORS["main"]: (146, 0, 73, 255),
            SUMMONER_ROLE_COLORS["accent"]: (219, 0, 0, 255),
            SUMMONER_ROLE_COLORS["light"]: (219, 109, 182, 255),
            SUMMONER_ROLE_COLORS["shadow"]: (73, 0, 73, 255),
            SUMMONER_ROLE_COLORS["deep"]: (73, 0, 73, 255),
        },
        "리아나 금발 유지·와인 자주 망토와 진홍 장식 에이전트",
    ),
    (2, 0x26): (
        {},
        {
            SUMMONER_ROLE_COLORS["main"]: ZARVERA_ROLE_COLORS["main"],
            SUMMONER_ROLE_COLORS["accent"]: ZARVERA_ROLE_COLORS["main"],
            SUMMONER_ROLE_COLORS["light"]: ZARVERA_ROLE_COLORS["light"],
            SUMMONER_ROLE_COLORS["shadow"]: ZARVERA_ROLE_COLORS["shadow"],
            SUMMONER_ROLE_COLORS["deep"]: ZARVERA_ROLE_COLORS["shadow"],
        },
        "리아나 기존 자주·연보라 자베라 색감 유지",
    ),
    (3, 0x28): (
        {
            SUMMONER_ROLE_COLORS["main"]: (36, 109, 219, 255),
            SUMMONER_ROLE_COLORS["accent"]: (0, 36, 146, 255),
            SUMMONER_ROLE_COLORS["light"]: (146, 219, 255, 255),
            SUMMONER_ROLE_COLORS["shadow"]: (0, 0, 109, 255),
            SUMMONER_ROLE_COLORS["deep"]: (0, 36, 109, 255),
        },
        {},
        "라나 코발트·빙청 서머너",
    ),
    (3, 0x25): (
        {
            AGENT_ROLE_COLORS["main"]: (0, 146, 146, 255),
            AGENT_ROLE_COLORS["shadow"]: (0, 73, 73, 255),
            AGENT_ROLE_COLORS["light"]: (109, 219, 219, 255),
        },
        {
            SUMMONER_ROLE_COLORS["main"]: (0, 146, 146, 255),
            SUMMONER_ROLE_COLORS["accent"]: (0, 109, 109, 255),
            SUMMONER_ROLE_COLORS["light"]: (109, 219, 219, 255),
            SUMMONER_ROLE_COLORS["shadow"]: (0, 73, 73, 255),
            SUMMONER_ROLE_COLORS["deep"]: (0, 73, 73, 255),
        },
        "라나 금발 유지·청록 민트 에이전트",
    ),
    (3, 0x26): (
        {
            ZARVERA_ROLE_COLORS["shadow"]: LANA_ZARVERA_ROLE_COLORS["shadow"],
            ZARVERA_ROLE_COLORS["main"]: LANA_ZARVERA_ROLE_COLORS["main"],
            ZARVERA_ROLE_COLORS["light"]: LANA_ZARVERA_ROLE_COLORS["light"],
            ZARVERA_ROLE_COLORS["accent"]: LANA_ZARVERA_ROLE_COLORS["accent"],
        },
        {
            SUMMONER_ROLE_COLORS["main"]: LANA_ZARVERA_ROLE_COLORS["main"],
            SUMMONER_ROLE_COLORS["accent"]: LANA_ZARVERA_ROLE_COLORS["main"],
            SUMMONER_ROLE_COLORS["light"]: LANA_ZARVERA_ROLE_COLORS["light"],
            SUMMONER_ROLE_COLORS["shadow"]: LANA_ZARVERA_ROLE_COLORS["shadow"],
            SUMMONER_ROLE_COLORS["deep"]: LANA_ZARVERA_ROLE_COLORS["shadow"],
        },
        "라나 하이로드식 왕청·밝은 하늘색 자베라",
    ),
}


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def flat_pixels(image: Image.Image) -> list[list[int]]:
    return [list(color) for color in image.get_flattened_data()]


def palette(image: Image.Image, limit: int | None = None) -> list[str]:
    colors = Counter(color for color in image.get_flattened_data() if color[3])
    return [
        "#%02x%02x%02x" % color[:3]
        for color, _ in colors.most_common(limit)
    ]


def ensure_snapshots(*, recapture_master: bool) -> None:
    for directory in (
        SUMMONER_MASTER.parent,
        CLASS_MASTERS,
        LOGICAL,
        PREVIEWS,
        ARCHIVE,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    if recapture_master and SUMMONER_MASTER.is_file():
        previous_master = ARCHIVE / "02-28-master-before-latest-recapture.png"
        if not previous_master.is_file():
            shutil.copy2(SUMMONER_MASTER, previous_master)
        shutil.copy2(LIVE / "2/28.png", SUMMONER_MASTER)
    elif not SUMMONER_MASTER.is_file():
        shutil.copy2(LIVE / "2/28.png", SUMMONER_MASTER)
    for commander_id, class_id in TARGETS:
        path = ARCHIVE / f"{commander_id:02d}-{class_id:02X}.png"
        if not path.is_file():
            shutil.copy2(
                LIVE / str(commander_id) / f"{class_id:02X}.png",
                path,
            )
    if not AGENT_MASTER.is_file():
        shutil.copy2(ARCHIVE / "02-25.png", AGENT_MASTER)
    if not ZARVERA_MASTER.is_file():
        shutil.copy2(ARCHIVE / "02-26.png", ZARVERA_MASTER)


def align_to_latest_summoner(
    base: Image.Image,
    summoner: Image.Image,
) -> tuple[Image.Image, set[tuple[int, int]]]:
    result = base.copy()
    overlay_points = {
        (x, y) for y in range(8) for x in range(3, 13)
    }
    for point in overlay_points:
        result.putpixel(point, summoner.getpixel(point))
    return result, overlay_points


def variant(
    master: Image.Image,
    key: tuple[int, int],
    overlay_points: set[tuple[int, int]],
) -> Image.Image:
    base_mapping, overlay_mapping, _ = SCHEMES[key]
    result = master.copy()
    for y in range(16):
        for x in range(16):
            point = (x, y)
            color = result.getpixel(point)
            mapping = (
                overlay_mapping
                if point in overlay_points and overlay_mapping
                else base_mapping
            )
            result.putpixel(point, mapping.get(color, color))
    if key[1] == 0x25:
        # The gold used by the Agent hair also appears as an equipment role.
        # Preserve the aligned master's exact upper-head pixels after the
        # garment recolor so neither twin's hair is accidentally recolored.
        for y in range(8):
            for x in range(3, 13):
                point = (x, y)
                if master.getpixel(point) == AGENT_ROLE_COLORS["trim"]:
                    result.putpixel(point, master.getpixel(point))
    return result


def build(*, recapture_master: bool = False) -> dict[str, object]:
    ensure_snapshots(recapture_master=recapture_master)
    summoner = Image.open(SUMMONER_MASTER).convert("RGBA")
    agent, agent_overlay = align_to_latest_summoner(
        Image.open(AGENT_MASTER).convert("RGBA"), summoner
    )
    zarvera, zarvera_overlay = align_to_latest_summoner(
        Image.open(ZARVERA_MASTER).convert("RGBA"), summoner
    )
    masters = {0x28: summoner, 0x25: agent, 0x26: zarvera}
    overlay_points_by_class = {
        0x28: {(x, y) for y in range(16) for x in range(16)},
        0x25: agent_overlay,
        0x26: zarvera_overlay,
    }
    for class_id, master in masters.items():
        master.save(CLASS_MASTERS / f"{class_id:02X}.png", optimize=True)
    reports = []
    for commander_id, class_id in ALL_KEYS:
        key = (commander_id, class_id)
        master = masters[class_id]
        result = variant(master, key, overlay_points_by_class[class_id])
        output = LOGICAL / f"{commander_id:02d}-{class_id:02X}.png"
        result.save(output, optimize=True)
        result.resize((512, 512), Image.Resampling.NEAREST).save(
            PREVIEWS / f"{commander_id:02d}-{class_id:02X}.png",
            optimize=True,
        )

        shape_match = sum(
            bool(result.getpixel((x, y))[3])
            == bool(master.getpixel((x, y))[3])
            for y in range(16)
            for x in range(16)
        )
        colors = palette(result)
        empty_rows = [
            y for y in range(16)
            if not any(result.getpixel((x, y))[3] for x in range(16))
        ]
        empty_columns = [
            x for x in range(16)
            if not any(result.getpixel((x, y))[3] for y in range(16))
        ]
        accepted = (
            shape_match == 256
            and len(colors) <= 15
            and not empty_rows
            and not empty_columns
            and (0, 0, 0, 255) not in result.get_flattened_data()
            and (255, 0, 255, 255) not in result.get_flattened_data()
        )
        reports.append(
            {
                "commander_id": commander_id,
                "class_id": f"{class_id:02X}",
                "file": f"logical16/{commander_id:02d}-{class_id:02X}.png",
                "palette_name": SCHEMES[key][2],
                "shape_match": shape_match,
                "summoner_alignment_pixel_count": len(
                    overlay_points_by_class[class_id]
                ),
                "visible_color_count": len(colors),
                "palette": colors,
                "empty_rows": empty_rows,
                "empty_columns": empty_columns,
                "accepted": accepted,
            }
        )

    board = Image.new("RGBA", (1536, 1120), (22, 25, 23, 255))
    draw = ImageDraw.Draw(board)
    for index, row in enumerate(reports):
        x = index % 3 * 512
        y = index // 3 * 560
        draw.text((x + 10, y + 12), row["palette_name"], fill=(240, 240, 240, 255))
        image = Image.open(OUTPUT / row["file"]).convert("RGBA").resize(
            (512, 512), Image.Resampling.NEAREST
        )
        board.alpha_composite(image, (x, y + 48))
    board.convert("RGB").save(
        OUTPUT / "all-liana-lana-summoner-agent-variants.png",
        optimize=True,
    )
    class_shape_differences = {}
    for left, right in ((0x25, 0x26), (0x25, 0x28), (0x26, 0x28)):
        class_shape_differences[f"{left:02X}-{right:02X}"] = sum(
            bool(masters[left].getpixel((x, y))[3])
            != bool(masters[right].getpixel((x, y))[3])
            for y in range(16)
            for x in range(16)
        )
    report = {
        "version": 1,
        "master": "2:28 latest user-edited Liana Summoner",
        "master_files": {
            "summoner": "master/02-28-liana-user-edited.png",
            "agent": "master/02-25-liana-agent-preserved.png",
            "zarvera": "master/02-26-liana-zarvera-preserved.png",
        },
        "rule": (
            "three separate class geometry masters aligned to the latest "
            "Liana Summoner center; recolor only between twins"
        ),
        "class_alpha_differences": class_shape_differences,
        "all_accepted": (
            all(row["accepted"] for row in reports)
            and min(class_shape_differences.values()) >= 5
        ),
        "classes": reports,
    }
    write_json(OUTPUT / "validation-report.json", report)
    return report


def apply_live(report: dict[str, object]) -> None:
    if not report["all_accepted"]:
        raise ValueError("refusing to apply rejected Liana Summoner variants")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    for sequence, (commander_id, class_id) in enumerate(ALL_KEYS):
        key = f"{commander_id}:{class_id:02X}"
        source = Image.open(
            LOGICAL / f"{commander_id:02d}-{class_id:02X}.png"
        ).convert("RGBA")
        live_path = LIVE / str(commander_id) / f"{class_id:02X}.png"
        source.save(live_path, optimize=True)
        source.resize((512, 512), Image.Resampling.NEAREST).save(
            LIVE / f"source-cells/{commander_id}-{class_id:02X}.png",
            optimize=True,
        )

        row = manifest["commanders"][str(commander_id)]["classes"][str(class_id)]
        if (commander_id, class_id) != MASTER_KEY:
            revision = time.time_ns() + sequence
            before = Image.open(
                ARCHIVE / f"{commander_id:02d}-{class_id:02X}.png"
            ).convert("RGBA")
            overrides["designs"][key] = {
                "revision": revision,
                "pixels": flat_pixels(source),
                "base_pixels": flat_pixels(before),
            }
            row["design_override"] = True
            row["design_revision"] = revision
            row["design_override_superseded"] = False
            row["superseded_design_revision"] = 0
        row["ai_source_kind"] = (
            "최신 리아나 사용자 편집 서머너 기반 쌍둥이 마법 클래스 "
            "공통 16×16 템플릿"
        )
        row["ai_source_position"] = (
            "latest/shared-liana-summoner-agent-v1/logical16/"
            f"{commander_id:02d}-{class_id:02X}.png"
        )
        row["source_palette"] = palette(source, 6)
        row["pixel_palette"] = palette(source, 6)
        row["feature"] = (
            "최신 리아나 서머너의 중앙 머리·몸 비율 80픽셀 반영·"
            "서머너·에이전트·자베라의 서로 다른 외곽 장비·지팡이·망토 "
            "좌표 유지·리아나와 라나 사이에서만 의상 역할색 변형·"
            "기존 대형 머리 마스크 재합성 없음·"
            + SCHEMES[(commander_id, class_id)][2]
        )
    write_json(OVERRIDES, overrides)
    manifest["asset_version"] = ASSET_VERSION
    write_json(MANIFEST, manifest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--recapture-master",
        action="store_true",
        help="replace the preserved master with the latest live 2:28 save",
    )
    args = parser.parse_args()
    report = build(recapture_master=args.recapture_master)
    apply_live(report)
    print(
        json.dumps(
            {
                "all_accepted": report["all_accepted"],
                "targets": [
                    "2:28", "2:25", "2:26",
                    "3:28", "3:25", "3:26",
                ],
                "asset_version": ASSET_VERSION,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
