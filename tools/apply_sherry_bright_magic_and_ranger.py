#!/usr/bin/env python3
"""Apply only the three approved Sherry sprites when the full build is blocked."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
AI_ROOT = ROOT / "editor/static/ai-class-sprites"
MANIFEST_PATH = AI_ROOT / "manifest.json"
ROM_ROOT = ROOT / "editor/static/class-sprites/commanders/4"
ASSET_VERSION = "liana-lana-healer-shared-v106"
TARGETS = {
    0x13: (
        ROOT
        / "docs/assets/ai-class-source/latest/shared-elwin-magic-v1/"
        "logical16/04-13.png",
        "엘윈 사용자 리터칭 메이지",
        "latest/shared-elwin-magic-v1/logical16/04-13.png",
    ),
    0x14: (
        ROOT
        / "docs/assets/ai-class-source/latest/shared-elwin-magic-v1/"
        "logical16/04-14.png",
        "엘윈 사용자 리터칭 아크메이지",
        "latest/shared-elwin-magic-v1/logical16/04-14.png",
    ),
    0x21: (
        ROOT
        / "docs/assets/ai-class-source/latest/sherry-ranger-v4/"
        "logical16/04-21.png",
        "쉐리 하이마스터 동일 디자인 기반 레인저 색상 변형",
        "latest/sherry-ranger-v4/logical16/04-21.png",
    ),
}


def dominant_colors(image: Image.Image, limit: int = 6) -> list[str]:
    counts = Counter(color for color in image.get_flattened_data() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common(limit)
    ]


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rows = manifest["commanders"]["4"]["classes"]
    reports = []
    for class_id, (source_path, label, source_position) in TARGETS.items():
        image = Image.open(source_path).convert("RGBA")
        if image.size != (16, 16):
            raise ValueError(f"native source must be 16x16: {source_path}")
        visible_color_count = len(
            {color for color in image.get_flattened_data() if color[3]}
        )
        if visible_color_count > 15:
            raise ValueError(f"visible palette exceeds 15: {class_id:02X}")
        image.save(AI_ROOT / f"4/{class_id:02X}.png", optimize=True)
        image.resize((512, 512), Image.Resampling.NEAREST).save(
            AI_ROOT / f"source-cells/4-{class_id:02X}.png", optimize=True
        )
        original = Image.open(ROM_ROOT / f"{class_id:02X}-p1.png").convert(
            "RGBA"
        )
        changed = sum(
            image.getpixel((x, y)) != original.getpixel((x, y))
            for y in range(16)
            for x in range(16)
        )
        row = rows[str(class_id)]
        row["ai_source_kind"] = f"{label} 공통 16×16 클래스 템플릿"
        row["ai_source_position"] = source_position
        row["source_palette"] = dominant_colors(image)
        row["pixel_palette"] = dominant_colors(image)
        row["changed_pixel_count"] = changed
        if class_id in {0x13, 0x14}:
            row["feature"] = (
                f"{label}의 장비·무기·실루엣 좌표 유지·쉐리 프린세스의 "
                "밝은 청록 #6DDBFF를 망토 주색으로 사용·중간 청록 "
                "#006D92는 접힌 면에만 사용·#242424 외곽선으로 몸·팔·"
                f"망토 경계 분리·변경 {changed}픽셀"
            )
        else:
            row["feature"] = (
                "쉐리 하이마스터의 양쪽 어깨·쌍검·망토·몸통 좌표를 "
                "그대로 유지·레인저는 파랑·청은색·담금색으로만 재배색·"
                "쉐리 원본 단발 머리·얼굴·눈 복원·"
                f"변경 {changed}픽셀·기존 사용자 편집 이력 보존·"
                "새 하이마스터 기반 배치 우선"
            )
            stored_revision = int(row.get("design_revision", 0))
            row["design_override"] = False
            row["design_revision"] = 0
            row["design_override_superseded"] = True
            row["superseded_design_revision"] = max(
                stored_revision,
                int(row.get("superseded_design_revision", 0)),
                1785661995718102871,
            )
        reports.append(
            {
                "class_id": f"{class_id:02X}",
                "source": str(source_path.relative_to(ROOT)),
                "visible_colors": visible_color_count,
                "changed_pixels": changed,
            }
        )
    manifest["asset_version"] = ASSET_VERSION
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"asset_version": ASSET_VERSION, "targets": reports},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
