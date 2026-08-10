from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = ROOT / "editor/static/sample-class-sprites"
AI_ROOT = ROOT / "editor/static/ai-class-sprites"
class SampleClassSpriteAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(
            (STATIC_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        cls.ai_manifest = json.loads(
            (AI_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        cls.validation = json.loads(
            (STATIC_ROOT / "validation-report.json").read_text(encoding="utf-8")
        )

    def test_catalog_has_five_samples_for_each_actual_tree_class(self) -> None:
        groups = self.manifest["groups"]
        self.assertEqual(len(groups), 5)
        self.assertEqual(
            {
                (row["commander_id"], row["class_id"])
                for row in groups
            },
            {
                (1, 0x22),
                (2, 0x18),
                (3, 0x18),
                (5, 0x18),
                (10, 0x18),
            },
        )
        for group in groups:
            self.assertTrue(group["complete"])
            self.assertEqual(group["expected_sample_count"], 5)
            self.assertEqual(len(group["samples"]), 5)
            self.assertEqual(
                [sample["id"] for sample in group["samples"]],
                [f"{number:02d}" for number in range(1, 6)],
            )
            self.assertFalse(any(sample["preserved"] for sample in group["samples"]))

    def test_published_assets_are_native_and_identity_locked(self) -> None:
        self.assertEqual(
            self.manifest["asset_version"],
            "sample-classes-v6-elwin-purple-ornament",
        )
        self.assertTrue(self.validation["all_accepted"])
        self.assertEqual(len(self.validation["diversity_groups"]), 5)
        self.assertTrue(
            all(row["accepted"] for row in self.validation["diversity_groups"])
        )
        validation_rows = {
            (row["group"], row["sample"]): row
            for row in self.validation["samples"]
        }
        for group in self.manifest["groups"]:
            for sample in group["samples"]:
                ai_path = ROOT / "editor/static" / sample["ai_source"]
                logical_path = ROOT / "editor/static" / sample["logical16"]
                preview_path = ROOT / "editor/static" / sample["preview"]
                self.assertTrue(ai_path.is_file(), ai_path)
                self.assertTrue(logical_path.is_file(), logical_path)
                self.assertTrue(preview_path.is_file(), preview_path)
                with Image.open(ai_path) as opened:
                    self.assertLessEqual(max(opened.size), 384)
                    self.assertGreaterEqual(min(opened.size), 128)
                with Image.open(logical_path) as opened:
                    logical = opened.convert("RGBA")
                self.assertEqual(logical.size, (16, 16))
                colors = {
                    color
                    for _, color in logical.getcolors(maxcolors=256) or []
                    if color[3]
                }
                self.assertLessEqual(len(colors), 15)
                self.assertNotIn((0, 0, 0, 255), colors)
                self.assertNotIn((255, 0, 255, 255), colors)
                self.assertIsNotNone(logical.getchannel("A").getbbox())
                opaque = sum(
                    1 for color in logical.getdata() if color[3]
                )
                self.assertGreaterEqual(opaque, 55)
                self.assertLessEqual(opaque, 245)
                validation = validation_rows[(group["id"], sample["id"])]
                self.assertTrue(validation["accepted"])
                self.assertTrue(validation["identity_color_variant_matches"])
                self.assertLessEqual(abs(validation["center_offset_x"]), 1.0)
                self.assertLessEqual(abs(validation["center_offset_y"]), 0.5)
                with Image.open(preview_path) as opened:
                    self.assertEqual(opened.size, (256, 256))

    def test_editor_does_not_expose_retired_sample_tab(self) -> None:
        html = (ROOT / "editor/static/index.html").read_text(encoding="utf-8")
        script = (ROOT / "editor/static/app.js").read_text(encoding="utf-8")
        styles = (ROOT / "editor/static/styles.css").read_text(
            encoding="utf-8"
        )
        self.assertNotIn('data-tab="sampleClasses"', html)
        self.assertNotIn('id="sampleClassesPanel"', html)
        self.assertNotIn("sampleClassSpriteModel", script)
        self.assertNotIn("loadClassSample", script)
        self.assertNotIn("sampleClassGroup", styles)


if __name__ == "__main__":
    unittest.main()
