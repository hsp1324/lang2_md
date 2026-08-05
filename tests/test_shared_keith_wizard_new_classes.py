from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/assets/ai-class-source/latest/shared-keith-wizard-new-classes-v1"
LIVE = ROOT / "editor/static/ai-class-sprites"
TARGETS = (
    (2, 0x25), (3, 0x25),
    (2, 0x26), (3, 0x26), (5, 0x26), (9, 0x26), (10, 0x26),
    (2, 0x28), (3, 0x28), (5, 0x28), (10, 0x28),
)


class SharedKeithWizardNewClassesTests(unittest.TestCase):
    def test_all_eleven_variants_are_live_and_valid(self) -> None:
        report = json.loads((SOURCE / "validation-report.json").read_text())
        self.assertTrue(report["all_accepted"])
        self.assertEqual(report["target_count"], 11)
        self.assertEqual(len({row["palette_name"] for row in report["classes"]}), 11)
        for commander_id, class_id in TARGETS:
            source = SOURCE / f"logical16/{commander_id:02d}-{class_id:02X}.png"
            image = Image.open(source).convert("RGBA")
            colors = {color for color in image.get_flattened_data() if color[3]}
            self.assertLessEqual(len(colors), 15)
            self.assertNotIn((0, 0, 0, 255), colors)
            self.assertNotIn((255, 0, 255, 255), colors)


if __name__ == "__main__":
    unittest.main()
