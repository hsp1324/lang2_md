from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / (
    "docs/assets/ai-class-source/latest/"
    "shared-sherry-scott-keith-lord-aaron-lord-v1"
)
AI_ROOT = ROOT / "editor/static/ai-class-sprites"


class SherryScottKeithAaronLordTests(unittest.TestCase):
    def test_targets_keep_identity_and_copy_aaron_equipment(self) -> None:
        report = json.loads(
            (SOURCE_ROOT / "validation-report.json").read_text(encoding="utf-8")
        )
        self.assertTrue(report["all_accepted"])
        for commander_id in (4, 6, 7):
            source = Image.open(
                SOURCE_ROOT / f"logical16/{commander_id:02d}-04.png"
            ).convert("RGBA")
            live = Image.open(AI_ROOT / f"{commander_id}/04.png").convert("RGBA")
            self.assertEqual(
                list(source.get_flattened_data()),
                list(live.get_flattened_data()),
            )
            row = next(
                item for item in report["classes"]
                if item["commander_id"] == commander_id
            )
            self.assertEqual(row["identity_match"], row["identity_pixel_count"])
            self.assertEqual(
                row["equipment_role_match"], row["equipment_pixel_count"]
            )

        sherry = Image.open(SOURCE_ROOT / "logical16/04-04.png").convert("RGBA")
        scott = Image.open(SOURCE_ROOT / "logical16/06-04.png").convert("RGBA")
        keith = Image.open(SOURCE_ROOT / "logical16/07-04.png").convert("RGBA")
        sherry_colors = set(sherry.get_flattened_data())
        scott_colors = set(scott.get_flattened_data())
        keith_colors = set(keith.get_flattened_data())
        self.assertIn((0, 109, 146, 255), sherry_colors)
        self.assertIn((109, 219, 255, 255), sherry_colors)
        self.assertIn((36, 182, 36, 255), scott_colors)
        self.assertIn((36, 219, 36, 255), scott_colors)
        self.assertIn((73, 109, 255, 255), keith_colors)
        self.assertIn((109, 219, 255, 255), keith_colors)

    def test_manifest_uses_new_sources_and_supersedes_scott_override(self) -> None:
        manifest = json.loads(
            (AI_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["asset_version"], "liana-lana-healer-shared-v106"
        )
        for commander_id in (4, 6, 7):
            row = manifest["commanders"][str(commander_id)]["classes"][str(4)]
            self.assertIn("최신 아론 사용자 편집 로드", row["ai_source_kind"])
        scott = manifest["commanders"]["6"]["classes"][str(4)]
        self.assertFalse(scott["design_override"])
        self.assertTrue(scott["design_override_superseded"])


if __name__ == "__main__":
    unittest.main()
