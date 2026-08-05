from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "docs/assets/ai-class-source/latest/lester-cavalry-tier-colors-v1"
)
LIVE = ROOT / "editor/static/ai-class-sprites"


class LesterCavalryTierColorTests(unittest.TestCase):
    def test_three_tiers_are_valid_and_upper_tiers_are_live(self) -> None:
        report = json.loads(
            (SOURCE / "validation-report.json").read_text(encoding="utf-8")
        )
        self.assertTrue(report["all_accepted"])
        self.assertEqual(
            [row["changed_mount_pixel_count"] for row in report["classes"]],
            [0, 39, 39],
        )
        for class_id in (0x0C, 0x1B):
            source = Image.open(SOURCE / f"logical16/09-{class_id:02X}.png").convert("RGBA")
            live = Image.open(LIVE / f"9/{class_id:02X}.png").convert("RGBA")
            self.assertEqual(
                list(source.get_flattened_data()),
                list(live.get_flattened_data()),
            )

    def test_mount_ramps_are_distinct(self) -> None:
        highlander = set(
            Image.open(SOURCE / "logical16/09-0C.png").convert("RGBA").get_flattened_data()
        )
        master = set(
            Image.open(SOURCE / "logical16/09-1B.png").convert("RGBA").get_flattened_data()
        )
        self.assertIn((36, 73, 146, 255), highlander)
        self.assertIn((109, 182, 255, 255), highlander)
        self.assertIn((109, 0, 0, 255), master)
        self.assertIn((255, 109, 36, 255), master)

    def test_manifest_version(self) -> None:
        manifest = json.loads((LIVE / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["asset_version"], "liana-lana-healer-shared-v106"
        )


if __name__ == "__main__":
    unittest.main()
