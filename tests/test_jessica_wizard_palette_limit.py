from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import unittest

from PIL import Image

from tools.build_ai_class_sprite_assets import (
    load_identity_mask_overrides,
    protected_eye_points,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "docs/assets/ai-class-source/latest/shared-new-classes-v2-refined/"
    "logical16/10-15.png"
)
LIVE = ROOT / "editor/static/ai-class-sprites/10/15.png"
ORIGINAL = ROOT / "editor/static/class-sprites/commanders/10/15-p1.png"


class JessicaWizardPaletteLimitTests(unittest.TestCase):
    def test_near_duplicate_purple_is_merged_before_identity_restore(self) -> None:
        source = Image.open(SOURCE).convert("RGBA")
        colors = Counter(source.get_flattened_data())
        self.assertEqual(colors[(146, 36, 182, 255)], 0)
        self.assertGreater(colors[(146, 73, 182, 255)], 0)
        self.assertEqual(colors[(36, 73, 255, 255)], 0)
        self.assertLessEqual(
            len({color for color in source.get_flattened_data() if color[3]}),
            15,
        )

    def test_final_global_identity_composition_fits_fifteen_colors(self) -> None:
        source = Image.open(SOURCE).convert("RGBA")
        original = Image.open(ORIGINAL).convert("RGBA")
        points = load_identity_mask_overrides()[(10, 0x15)] | protected_eye_points(
            original
        )
        composed = source.copy()
        for point in points:
            if original.getpixel(point)[3]:
                composed.putpixel(point, original.getpixel(point))
        colors = {color for color in composed.get_flattened_data() if color[3]}
        self.assertLessEqual(len(colors), 15)
        live = Image.open(LIVE).convert("RGBA")
        self.assertEqual(
            list(composed.get_flattened_data()),
            list(live.get_flattened_data()),
        )

    def test_source_report_records_the_deliberate_merge(self) -> None:
        report = json.loads(
            (
                SOURCE.parents[1] / "validation-report.json"
            ).read_text(encoding="utf-8")
        )
        row = next(
            item
            for item in report["classes"]
            if item["commander_id"] == 10 and item["class_id"] == "15"
        )
        self.assertEqual(
            row["near_duplicate_palette_merge"],
            "#9224B6 -> #9249B6; #2449FF -> #496DFF",
        )
        self.assertTrue(row["accepted"])

    def test_editor_manifest_retains_the_palette_fix_metadata(self) -> None:
        manifest = json.loads(
            (
                ROOT / "editor/static/ai-class-sprites/manifest.json"
            ).read_text(encoding="utf-8")
        )
        row = manifest["commanders"]["10"]["classes"][str(0x15)]
        self.assertIn("#9224B6을 #9249B6으로 병합", row["feature"])


if __name__ == "__main__":
    unittest.main()
