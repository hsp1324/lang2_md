from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image

from tools.build_shared_keith_wizard_new_classes import SCHEMES
from tools.pillow_compat import flattened_image_data


ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = ROOT / "editor/static/ai-class-sprites"
SOURCE_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/shared-keith-wizard-new-classes-v1"
)


class LesterZarveraLineagePaletteTests(unittest.TestCase):
    def test_zarvera_uses_archmage_red_blue_gold(self) -> None:
        live = Image.open(LIVE_ROOT / "9/26.png").convert("RGBA")
        archmage = Image.open(LIVE_ROOT / "9/14.png").convert("RGBA")
        overrides = json.loads(
            (ROOT / "editor/ai_class_design_overrides.json").read_text(
                encoding="utf-8"
            )
        )["designs"]
        manifest = json.loads(
            (LIVE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        row = manifest["commanders"]["9"]["classes"][str(0x26)]
        self.assertTrue(row["design_override"])
        self.assertEqual(
            row["design_revision"], overrides["9:26"]["revision"]
        )
        colors = set(flattened_image_data(live))
        lineage = {
            (146, 0, 36, 255),
            (36, 73, 219, 255),
            (255, 182, 36, 255),
        }
        self.assertTrue(lineage.issubset(colors))
        self.assertTrue(
            lineage.issubset(set(flattened_image_data(archmage)))
        )
        self.assertNotIn((36, 73, 0, 255), colors)
        self.assertNotIn((73, 146, 36, 255), colors)
        self.assertNotIn((182, 219, 109, 255), colors)
        self.assertLessEqual(
            len({color for color in colors if color[3]}), 15
        )

    def test_generator_override_and_manifest_remain_in_sync(self) -> None:
        self.assertEqual(
            SCHEMES[(9, 0x26)][:3],
            (
                (146, 0, 36, 255),
                (36, 73, 219, 255),
                (255, 182, 36, 255),
            ),
        )
        overrides = json.loads(
            (ROOT / "editor/ai_class_design_overrides.json").read_text(
                encoding="utf-8"
            )
        )["designs"]
        manifest = json.loads(
            (LIVE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["asset_version"],
            "identity-mask-and-silhouette-closure-v107",
        )
        row = manifest["commanders"]["9"]["classes"][str(0x26)]
        self.assertTrue(row["design_override"])
        self.assertEqual(
            row["design_revision"], overrides["9:26"]["revision"]
        )
        self.assertIn("사용자 16×16 디자인 편집 적용", row["feature"])


if __name__ == "__main__":
    unittest.main()
