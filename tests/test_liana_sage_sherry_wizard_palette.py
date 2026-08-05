from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "docs/assets/ai-class-source/latest/"
    "liana-sage-sherry-wizard-palette-v1"
)
LIVE = ROOT / "editor/static/ai-class-sprites"


class LianaSageSherryWizardPaletteTests(unittest.TestCase):
    def test_palette_polish_is_live_and_valid(self) -> None:
        report = json.loads(
            (SOURCE / "validation-report.json").read_text(encoding="utf-8")
        )
        self.assertTrue(report["all_accepted"])
        for row in report["classes"]:
            commander_id = row["commander_id"]
            class_id = int(row["class_id"], 16)
            source = Image.open(SOURCE / row["file"]).convert("RGBA")
            live = Image.open(
                LIVE / str(commander_id) / f"{class_id:02X}.png"
            ).convert("RGBA")
            self.assertEqual(
                list(source.get_flattened_data()),
                list(live.get_flattened_data()),
            )
            self.assertEqual(row["identity_match"], row["identity_pixel_count"])
            self.assertEqual(row["shape_match"], 256)
            self.assertGreaterEqual(row["changed_dark_pixel_count"], 20)
            self.assertLess(row["dark_pixels_after"], row["dark_pixels_before"])
            self.assertLessEqual(row["visible_color_count"], 15)

    def test_expected_bright_material_colors_are_present(self) -> None:
        sage = Image.open(SOURCE / "logical16/02-18.png").convert("RGBA")
        wizard = Image.open(SOURCE / "logical16/04-15.png").convert("RGBA")
        self.assertIn((146, 36, 73, 255), set(sage.get_flattened_data()))
        self.assertIn((219, 0, 0, 255), set(sage.get_flattened_data()))
        wizard_colors = set(wizard.get_flattened_data())
        self.assertIn((0, 73, 109, 255), wizard_colors)
        self.assertIn((0, 109, 146, 255), wizard_colors)
        self.assertIn((109, 219, 255, 255), wizard_colors)
        self.assertNotIn((73, 36, 146, 255), wizard_colors)
        self.assertNotIn((146, 109, 219, 255), wizard_colors)

    def test_manifest_version(self) -> None:
        manifest = json.loads((LIVE / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["asset_version"],
            "liana-lana-healer-shared-v106",
        )


if __name__ == "__main__":
    unittest.main()
