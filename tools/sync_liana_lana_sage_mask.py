#!/usr/bin/env python3
"""Copy Liana's Sage mask to Lana and refresh only the two Sage sprites."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import protected_eye_points


MASK_PATH = ROOT / "editor/ai_identity_masks.json"
SOURCE_ROOT = (
    ROOT / "assets/class-sprites/source/latest/liana-lana-strict16-v1"
)
ROM_ROOT = ROOT / "editor/static/class-sprites/commanders"
CLASS_ID = 0x18
RESAMPLING = getattr(Image, "Resampling", Image)


def main() -> None:
    document = json.loads(MASK_PATH.read_text(encoding="utf-8"))
    masks = document["masks"]
    donor = masks.get("2:18")
    if not donor:
        raise ValueError("Liana Sage mask 2:18 is missing")
    masks["3:18"] = [list(point) for point in donor]
    MASK_PATH.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    face_points = {tuple(point) for point in donor}
    rows: list[dict[str, object]] = []
    for commander_id, color_name in ((2, "red"), (3, "blue")):
        source_path = SOURCE_ROOT / f"native16-{color_name}/18.png"
        preview_path = SOURCE_ROOT / f"previews-{color_name}/18.png"
        original = Image.open(
            ROM_ROOT / str(commander_id) / "18-p1.png"
        ).convert("RGBA")
        result = Image.open(source_path).convert("RGBA")
        effective_points = face_points | protected_eye_points(original)
        for point in effective_points:
            result.putpixel(point, original.getpixel(point))

        visible_colors = Counter(
            color for color in result.getdata() if color[3]
        )
        if len(visible_colors) > 15:
            raise ValueError(
                f"{commander_id}:18 exceeds 4bpp after Sage mask refresh"
            )
        result.save(source_path, optimize=True)
        result.resize((512, 512), RESAMPLING.NEAREST).save(
            preview_path,
            optimize=True,
        )
        rows.append({
            "commander_id": commander_id,
            "class_id": "18",
            "mask_pixel_count": len(face_points),
            "visible_identity_pixel_count": sum(
                bool(original.getpixel(point)[3])
                for point in effective_points
            ),
            "identity_exact": all(
                result.getpixel(point) == original.getpixel(point)
                for point in effective_points
            ),
            "visible_color_count": len(visible_colors),
        })

    report = {
        "version": 1,
        "canonical_mask": "2:18",
        "copied_to": "3:18",
        "scope": "Sage only",
        "classes": rows,
        "all_accepted": all(
            row["identity_exact"] and row["visible_color_count"] <= 15
            for row in rows
        ),
    }
    (SOURCE_ROOT / "sage-only-face-refresh-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"2:18 -> 3:18: {len(face_points)} pixels; 2 Sage sprites")


if __name__ == "__main__":
    main()
