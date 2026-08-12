#!/usr/bin/env python3
"""Initialize, audit, and publish the character-specific ten-sample campaign."""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = (
    ROOT / "assets/class-sprites/source/latest/"
    "sample-class-variants-v2-ten"
)
V1_ROOT = (
    ROOT / "assets/class-sprites/source/latest/"
    "sample-class-variants-v1"
)
STATIC_ROOT = ROOT / "editor/static/sample-class-sprites"
AI_ROOT = ROOT / "editor/static/ai-class-sprites"
AI_MANIFEST_PATH = AI_ROOT / "manifest.json"
CAMPAIGN_PATH = SOURCE_ROOT / "campaign.json"
ASSET_VERSION = "sample-classes-v2-ten"
EXPECTED_SAMPLE_IDS = tuple(f"{number:02d}" for number in range(1, 11))
FORBIDDEN_COLORS = {(0, 0, 0, 255), (255, 0, 255, 255)}


COMMANDERS = {
    1: ("elwin", "엘윈"),
    2: ("liana", "리아나"),
    3: ("lana", "라나"),
    4: ("sherry", "쉐리"),
    5: ("hein", "헤인"),
    6: ("scott", "스코트"),
    7: ("keith", "키스"),
    8: ("aaron", "아론"),
    9: ("lester", "레스터"),
    10: ("jessica", "제시카"),
}
CLASSES = {
    0x08: ("healer", "힐러"),
    0x15: ("wizard", "위저드"),
    0x16: ("high-priest", "하이프리스트"),
    0x18: ("sage", "세이지"),
    0x22: ("hero", "히어로"),
    0x25: ("agent", "에이전트"),
    0x26: ("zarvera", "자베러"),
    0x28: ("summoner", "서머너"),
}

# Only combinations present in each commander's actual class tree are sampled.
GROUP_CLASSES = {
    1: (0x22,),
    2: (0x08, 0x15, 0x16, 0x18, 0x25, 0x26, 0x28),
    3: (0x08, 0x15, 0x16, 0x18, 0x25, 0x26, 0x28),
    4: (0x15,),
    5: (0x15, 0x16, 0x18, 0x26, 0x28),
    6: (0x18,),
    7: (0x08, 0x15, 0x16),
    8: (0x16,),
    9: (0x15, 0x26),
    10: (0x08, 0x15, 0x16, 0x18, 0x26, 0x28),
}


def group_row(commander_id: int, class_id: int) -> dict:
    commander_slug, commander_name = COMMANDERS[commander_id]
    class_slug, class_name = CLASSES[class_id]
    group_id = (
        f"{commander_id:02d}-{commander_slug}-"
        f"{class_id:02X}-{class_slug}"
    )
    return {
        "id": group_id,
        "commander_id": commander_id,
        "commander_name": commander_name,
        "class_id": class_id,
        "class_hex": f"{class_id:02X}",
        "class_name": class_name,
        "title": f"{commander_name} · {class_name}",
        "expected_samples": 10,
        "preserved_samples": ["01"]
        if commander_id == 10 and class_id == 0x26
        else [],
    }


def campaign_groups() -> list[dict]:
    return [
        group_row(commander_id, class_id)
        for commander_id, class_ids in GROUP_CLASSES.items()
        for class_id in class_ids
    ]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def copy_if_missing(source: Path, target: Path) -> None:
    if target.exists():
        return
    if not source.is_file():
        raise FileNotFoundError(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def preserve_jessica_zarvera_01() -> None:
    """Keep the user-approved vertical-lance candidate byte-for-byte."""
    group_id = "10-jessica-26-zarvera"
    target = SOURCE_ROOT / group_id
    copy_if_missing(
        V1_ROOT / "jessica-zarvera/ai/01.png",
        target / "ai/01.png",
    )
    # V1's static logical sprite is already in Jessica's final editor space.
    copy_if_missing(
        STATIC_ROOT / "jessica-zarvera/logical16/01.png",
        target / "logical16/01.png",
    )
    copy_if_missing(
        V1_ROOT / "jessica-zarvera/prompts/01.txt",
        target / "prompts/01.txt",
    )
    write_json(
        target / "preserved.json",
        {
            "sample_id": "01",
            "label": "세로 장창형",
            "source_campaign": "sample-class-variants-v1/jessica-zarvera",
            "logical_source": (
                "editor/static/sample-class-sprites/"
                "jessica-zarvera/logical16/01.png"
            ),
            "locked": True,
            "note": "사용자 확정안. 재생성하거나 덮어쓰지 않는다.",
        },
    )


def initialize() -> dict:
    groups = campaign_groups()
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    for group in groups:
        group_root = SOURCE_ROOT / group["id"]
        for child in ("ai", "logical16", "previews", "prompts"):
            (group_root / child).mkdir(parents=True, exist_ok=True)
    preserve_jessica_zarvera_01()
    campaign = {
        "asset_version": ASSET_VERSION,
        "generation_policy": {
            "independent_imagegen_call_per_new_candidate": True,
            "first_generation_inputs": [
                "commander ROM class sprite",
                "current identity-only pixels",
            ],
            "previous_ai_as_generation_reference": False,
            "same_class_cross_commander_copy_or_recolor": False,
            "native_size": [16, 16],
        },
        "expected_group_count": len(groups),
        "expected_candidate_count": len(groups) * 10,
        "new_generation_count": len(groups) * 10 - 1,
        "groups": groups,
    }
    write_json(CAMPAIGN_PATH, campaign)
    return campaign


def sample_paths(group: dict, sample_id: str) -> tuple[Path, Path]:
    group_root = SOURCE_ROOT / group["id"]
    return (
        group_root / "ai" / f"{sample_id}.png",
        group_root / "logical16" / f"{sample_id}.png",
    )


def status() -> dict:
    campaign = initialize() if not CAMPAIGN_PATH.is_file() else json.loads(
        CAMPAIGN_PATH.read_text(encoding="utf-8")
    )
    groups: list[dict] = []
    ready_candidates = 0
    for group in campaign["groups"]:
        ready = []
        missing = []
        for sample_id in EXPECTED_SAMPLE_IDS:
            ai_path, logical_path = sample_paths(group, sample_id)
            if ai_path.is_file() and logical_path.is_file():
                ready.append(sample_id)
            else:
                missing.append(sample_id)
        ready_candidates += len(ready)
        groups.append(
            {
                "id": group["id"],
                "ready": ready,
                "missing": missing,
                "complete": not missing,
            }
        )
    result = {
        "asset_version": ASSET_VERSION,
        "ready_group_count": sum(row["complete"] for row in groups),
        "expected_group_count": len(groups),
        "ready_candidate_count": ready_candidates,
        "expected_candidate_count": len(groups) * 10,
        "groups": groups,
    }
    write_json(SOURCE_ROOT / "status.json", result)
    return result


def visible_colors(image: Image.Image) -> set[tuple[int, int, int, int]]:
    return {
        color
        for _, color in image.convert("RGBA").getcolors(maxcolors=256) or []
        if color[3]
    }


def connected_components(image: Image.Image) -> list[int]:
    remaining = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if image.getpixel((x, y))[3]
    }
    sizes: list[int] = []
    while remaining:
        queue = deque([remaining.pop()])
        size = 0
        while queue:
            x, y = queue.popleft()
            size += 1
            # Diagonal weapon shafts are visually connected in 16x16 art.
            for point in (
                (x + dx, y + dy)
                for dy in (-1, 0, 1)
                for dx in (-1, 0, 1)
                if dx or dy
            ):
                if point in remaining:
                    remaining.remove(point)
                    queue.append(point)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def center_holes(image: Image.Image) -> list[tuple[int, int]]:
    transparent = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if not image.getpixel((x, y))[3]
    }
    outside = {
        point
        for point in transparent
        if point[0] in (0, 15) or point[1] in (0, 15)
    }
    queue = deque(outside)
    while queue:
        x, y = queue.popleft()
        for point in (
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
        ):
            if point in transparent and point not in outside:
                outside.add(point)
                queue.append(point)
    return sorted(
        (
            point
            for point in transparent - outside
            if 4 <= point[0] <= 11 and 8 <= point[1] <= 14
        ),
        key=lambda point: (point[1], point[0]),
    )


def identity_result(
    image: Image.Image,
    group: dict,
    ai_manifest: dict,
) -> tuple[int, int]:
    commander_id = int(group["commander_id"])
    class_id = int(group["class_id"])
    row = ai_manifest["commanders"][str(commander_id)]["classes"][
        str(class_id)
    ]
    points = [tuple(point) for point in row.get("identity_lock_points", [])]
    with Image.open(
        AI_ROOT / str(commander_id) / f"{class_id:02X}.png"
    ) as opened:
        identity = opened.convert("RGBA")
    matches = sum(
        image.getpixel(point) == identity.getpixel(point)
        for point in points
    )
    return matches, len(points)


def validate_sprite(
    logical: Image.Image,
    group: dict,
    sample_id: str,
    ai_manifest: dict,
) -> dict:
    colors = visible_colors(logical)
    empty_rows = [
        y
        for y in range(16)
        if not any(logical.getpixel((x, y))[3] for x in range(16))
    ]
    empty_columns = [
        x
        for x in range(16)
        if not any(logical.getpixel((x, y))[3] for y in range(16))
    ]
    components = connected_components(logical)
    holes = center_holes(logical)
    identity_matches, identity_total = identity_result(
        logical, group, ai_manifest
    )
    result = {
        "group": group["id"],
        "sample": sample_id,
        "visible_colors": len(colors),
        "forbidden_colors": [
            list(color) for color in sorted(colors & FORBIDDEN_COLORS)
        ],
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "connected_components": components,
        "center_holes": [list(point) for point in holes],
        "identity_matches": identity_matches,
        "identity_total": identity_total,
    }
    result["accepted"] = all(
        (
            logical.size == (16, 16),
            len(colors) <= 15,
            not result["forbidden_colors"],
            not empty_rows,
            not empty_columns,
            len(components) == 1,
            not holes,
            identity_matches == identity_total,
        )
    )
    return result


def thumbnail(source: Image.Image, maximum: int = 384) -> Image.Image:
    image = source.convert("RGBA")
    image.thumbnail((maximum, maximum), Image.Resampling.NEAREST)
    return image


def contact_panel(
    sample_id: str,
    ai_image: Image.Image,
    logical: Image.Image,
) -> Image.Image:
    panel = Image.new("RGBA", (152, 236), (33, 38, 34, 255))
    draw = ImageDraw.Draw(panel)
    draw.rectangle((0, 0, 151, 235), outline=(72, 91, 77, 255), width=1)
    draw.text((6, 5), sample_id, fill=(235, 242, 236, 255))
    ai = thumbnail(ai_image, 132)
    panel.alpha_composite(ai, ((152 - ai.width) // 2, 23))
    preview = logical.resize((80, 80), Image.Resampling.NEAREST)
    panel.alpha_composite(preview, (36, 150))
    return panel


def build_master_contacts(groups: list[dict]) -> dict[str, str]:
    contact_root = SOURCE_ROOT / "contact-sheets"
    rows: list[tuple[dict, Image.Image]] = []
    for group in groups:
        path = contact_root / f"{group['id']}.png"
        with Image.open(path) as opened:
            rows.append((group, opened.convert("RGBA")))

    def stack(selected: list[tuple[dict, Image.Image]], target: Path) -> None:
        label_height = 24
        width = max(sheet.width for _, sheet in selected)
        height = sum(label_height + sheet.height for _, sheet in selected)
        canvas = Image.new("RGBA", (width, height), (15, 18, 16, 255))
        draw = ImageDraw.Draw(canvas)
        offset_y = 0
        for group, sheet in selected:
            draw.text(
                (8, offset_y + 6),
                str(group["id"]),
                fill=(232, 239, 233, 255),
            )
            offset_y += label_height
            canvas.alpha_composite(sheet, (0, offset_y))
            offset_y += sheet.height
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert("RGB").save(target, optimize=True)

    all_path = SOURCE_ROOT / "all-ai-and-logical16.png"
    stack(rows, all_path)
    commander_root = contact_root / "commanders"
    commander_paths: dict[str, str] = {}
    for commander_id in sorted({int(group["commander_id"]) for group in groups}):
        selected = [
            row for row in rows if int(row[0]["commander_id"]) == commander_id
        ]
        commander_slug = COMMANDERS[commander_id][0]
        target = commander_root / f"{commander_id:02d}-{commander_slug}.png"
        stack(selected, target)
        commander_paths[str(commander_id)] = str(target.relative_to(ROOT))
    return {
        "all": str(all_path.relative_to(ROOT)),
        **{f"commander_{key}": value for key, value in commander_paths.items()},
    }


def sample_metadata(group_root: Path) -> dict[str, dict]:
    path = group_root / "samples.json"
    result: dict[str, dict] = {}
    if path.is_file():
        value = json.loads(path.read_text(encoding="utf-8"))
        rows = value.get("samples", value) if isinstance(value, dict) else value
        result.update({str(row["id"]): row for row in rows})
    preserved_path = group_root / "preserved.json"
    if preserved_path.is_file():
        preserved = json.loads(preserved_path.read_text(encoding="utf-8"))
        result[str(preserved["sample_id"])] = preserved
    return result


def publish(partial: bool = False) -> dict:
    campaign_state = status()
    if not partial and campaign_state["ready_candidate_count"] != campaign_state[
        "expected_candidate_count"
    ]:
        raise RuntimeError(
            "campaign is incomplete: "
            f"{campaign_state['ready_candidate_count']}/"
            f"{campaign_state['expected_candidate_count']} candidates"
        )
    campaign = json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))
    ai_manifest = json.loads(AI_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest_groups: list[dict] = []
    reports: list[dict] = []
    contact_root = SOURCE_ROOT / "contact-sheets"
    contact_root.mkdir(parents=True, exist_ok=True)

    for group in campaign["groups"]:
        group_root = SOURCE_ROOT / group["id"]
        available_ids = [
            sample_id
            for sample_id in EXPECTED_SAMPLE_IDS
            if all(path.is_file() for path in sample_paths(group, sample_id))
        ]
        if not available_ids:
            continue
        static_group = STATIC_ROOT / group["id"]
        metadata = sample_metadata(group_root)
        manifest_samples: list[dict] = []
        panels: list[Image.Image] = []
        for sample_id in available_ids:
            source_ai, source_logical = sample_paths(group, sample_id)
            with Image.open(source_ai) as opened:
                ai_image = opened.convert("RGBA")
            with Image.open(source_logical) as opened:
                logical = opened.convert("RGBA")
            if logical.size != (16, 16):
                raise ValueError(f"not native 16x16: {source_logical}")
            report = validate_sprite(logical, group, sample_id, ai_manifest)
            reports.append(report)

            static_ai = static_group / "ai" / f"{sample_id}.png"
            static_logical = static_group / "logical16" / f"{sample_id}.png"
            static_preview = static_group / "previews" / f"{sample_id}.png"
            static_ai.parent.mkdir(parents=True, exist_ok=True)
            static_logical.parent.mkdir(parents=True, exist_ok=True)
            static_preview.parent.mkdir(parents=True, exist_ok=True)
            ai_thumb = thumbnail(ai_image)
            ai_thumb.save(static_ai, optimize=True)
            logical.save(static_logical, optimize=True)
            preview = logical.resize((256, 256), Image.Resampling.NEAREST)
            preview.save(static_preview, optimize=True)
            panels.append(contact_panel(sample_id, ai_thumb, logical))

            meta = metadata.get(sample_id, {})
            manifest_samples.append(
                {
                    "id": sample_id,
                    "label": meta.get("label", f"디자인 {sample_id}"),
                    "description": meta.get(
                        "description",
                        "독립 생성한 캐릭터 전용 16×16 디자인",
                    ),
                    "ai_source": (
                        f"sample-class-sprites/{group['id']}/"
                        f"ai/{sample_id}.png"
                    ),
                    "logical16": (
                        f"sample-class-sprites/{group['id']}/"
                        f"logical16/{sample_id}.png"
                    ),
                    "preview": (
                        f"sample-class-sprites/{group['id']}/"
                        f"previews/{sample_id}.png"
                    ),
                    "preserved": sample_id in group["preserved_samples"],
                }
            )

        sheet = Image.new(
            "RGBA", (len(panels) * 152, 236), (15, 18, 16, 255)
        )
        for index, panel in enumerate(panels):
            sheet.alpha_composite(panel, (index * 152, 0))
        sheet.save(contact_root / f"{group['id']}.png", optimize=True)

        manifest_groups.append(
            {
                "id": group["id"],
                "commander_id": group["commander_id"],
                "class_id": group["class_id"],
                "title": group["title"],
                "description": (
                    "ROM 원본과 현재 얼굴·머리 정체성만 참조해 독립 생성한 10안"
                ),
                "expected_sample_count": 10,
                "complete": len(available_ids) == 10,
                "samples": manifest_samples,
            }
        )

    validation = {
        "asset_version": (
            ASSET_VERSION
            if not partial
            else f"{ASSET_VERSION}-preview-{len(reports)}"
        ),
        "group_count": len(manifest_groups),
        "sample_count": len(reports),
        "expected_group_count": len(campaign["groups"]),
        "expected_sample_count": len(campaign["groups"]) * 10,
        "partial": partial,
        "all_accepted": all(row["accepted"] for row in reports),
        "samples": reports,
    }
    write_json(SOURCE_ROOT / "validation-report.json", validation)
    if not validation["all_accepted"]:
        rejected = [
            f"{row['group']}:{row['sample']}"
            for row in reports
            if not row["accepted"]
        ]
        raise ValueError("sample validation failed: " + ", ".join(rejected))

    review_sheets = build_master_contacts(manifest_groups)

    manifest = {
        "asset_version": validation["asset_version"],
        "layout": "vertical-groups-horizontal-ten",
        "partial": partial,
        "ready_group_count": campaign_state["ready_group_count"],
        "expected_group_count": campaign_state["expected_group_count"],
        "ready_candidate_count": campaign_state["ready_candidate_count"],
        "expected_candidate_count": campaign_state[
            "expected_candidate_count"
        ],
        "review_sheets": review_sheets,
        "groups": manifest_groups,
    }
    write_json(STATIC_ROOT / "manifest.json", manifest)
    write_json(STATIC_ROOT / "validation-report.json", validation)
    return validation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("init", "status", "preview", "publish"),
        nargs="?",
        default="status",
    )
    args = parser.parse_args()
    if args.action == "init":
        result = initialize()
        print(
            f"initialized {result['expected_group_count']} groups / "
            f"{result['expected_candidate_count']} candidates"
        )
    elif args.action in ("preview", "publish"):
        result = publish(partial=args.action == "preview")
        print(
            f"published{' preview' if result['partial'] else ''} "
            f"{result['group_count']} groups / "
            f"{result['sample_count']} candidates"
        )
    else:
        result = status()
        print(
            f"ready {result['ready_group_count']}/"
            f"{result['expected_group_count']} groups, "
            f"{result['ready_candidate_count']}/"
            f"{result['expected_candidate_count']} candidates"
        )


if __name__ == "__main__":
    main()
