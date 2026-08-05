from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "docs/assets/ai-class-source/latest/sherry-ranger-v4"


class SherryRangerHighMasterTemplateTests(unittest.TestCase):
    def test_ranger_keeps_high_master_shape_and_uses_a_distinct_palette(self) -> None:
        report = json.loads(
            (SOURCE_ROOT / "validation.json").read_text(encoding="utf-8")
        )
        self.assertTrue(report["accepted"])
        self.assertEqual(
            report["template_shape_match"], report["template_shape_total"]
        )
        self.assertGreaterEqual(report["equipment_color_differences"], 24)
        self.assertLessEqual(report["visible_color_count"], 15)
        with Image.open(SOURCE_ROOT / "logical16/04-21.png") as opened:
            source = opened.convert("RGBA")
        with Image.open(
            ROOT / "editor/static/ai-class-sprites/4/21.png"
        ) as opened:
            live = opened.convert("RGBA")
        self.assertEqual(list(source.get_flattened_data()), list(live.get_flattened_data()))


if __name__ == "__main__":
    unittest.main()
