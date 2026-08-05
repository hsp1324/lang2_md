from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "editor/static/ai-class-sprites"


class KeithBlueMartialPaletteTests(unittest.TestCase):
    def test_high_lord_and_swordmaster_share_sky_blue_family(self) -> None:
        expected = {
            (0, 36, 182, 255),
            (73, 109, 255, 255),
            (109, 219, 255, 255),
        }
        high_lord = Image.open(LIVE / "7/0B.png").convert("RGBA")
        swordmaster = Image.open(LIVE / "7/1A.png").convert("RGBA")
        high_lord_colors = {
            color for color in high_lord.get_flattened_data() if color[3]
        }
        swordmaster_colors = {
            color for color in swordmaster.get_flattened_data() if color[3]
        }
        self.assertTrue(expected.issubset(high_lord_colors))
        self.assertTrue(expected.issubset(swordmaster_colors))
        self.assertNotIn((219, 146, 36, 255), high_lord_colors)
        self.assertNotIn((146, 36, 0, 255), high_lord_colors)
        self.assertNotIn((219, 146, 36, 255), swordmaster_colors)
        self.assertNotIn((109, 73, 0, 255), swordmaster_colors)
        self.assertIn((255, 255, 255, 255), high_lord_colors)
        self.assertIn((255, 255, 255, 255), swordmaster_colors)

    def test_sources_validate_and_manifest_cache_version_is_current(self) -> None:
        for source_name, class_id in (
            ("shared-high-lord-hein-v1", "0B"),
            ("shared-swordmaster-hein-v1", "1A"),
        ):
            report = json.loads(
                (
                    ROOT
                    / "docs/assets/ai-class-source/latest"
                    / source_name
                    / "validation-report.json"
                ).read_text(encoding="utf-8")
            )
            row = next(
                item
                for item in report["classes"]
                if item["commander_id"] == 7
                and item["class_id"] == class_id
            )
            self.assertTrue(row["accepted"])
        manifest = json.loads(
            (LIVE / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["asset_version"],
            "liana-lana-healer-shared-v106",
        )


if __name__ == "__main__":
    unittest.main()
