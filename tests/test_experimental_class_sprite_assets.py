from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "editor/static/ai-class-sprites"
SOURCE_ROOT = ROOT / "assets/class-sprites/source"


class CurrentClassSpriteAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(
            (ASSET_ROOT / "manifest.json").read_text(encoding="utf-8")
        )

    def test_current_catalog_is_complete(self) -> None:
        self.assertEqual(
            self.manifest["asset_version"],
            "identity-mask-and-silhouette-closure-v107",
        )
        self.assertEqual(self.manifest["commander_count"], 10)
        self.assertEqual(self.manifest["asset_count"], 180)
        self.assertEqual(self.manifest["redesigned_count"], 131)
        self.assertEqual(self.manifest["pending_redesign_count"], 0)
        self.assertEqual(
            set(self.manifest["commanders"]),
            {str(commander_id) for commander_id in range(1, 11)},
        )
        self.assertEqual(
            sum(
                len(commander["classes"])
                for commander in self.manifest["commanders"].values()
            ),
            180,
        )

    def test_published_sprites_are_native_megadrive_assets(self) -> None:
        published: set[Path] = set()
        for commander in self.manifest["commanders"].values():
            for row in commander["classes"].values():
                path = ASSET_ROOT / row["file"]
                self.assertTrue(path.is_file(), path)
                published.add(path)
                with Image.open(path) as opened:
                    image = opened.convert("RGBA")
                self.assertEqual(image.size, (16, 16), path)
                colors = {
                    color
                    for count, color in image.getcolors(maxcolors=256) or []
                    if count and color[3]
                }
                self.assertLessEqual(len(colors), 15, path)
                self.assertIsNotNone(image.getchannel("A").getbbox(), path)
        self.assertEqual(len(published), 180)

    def test_manifest_references_only_retained_current_sources(self) -> None:
        sources = {
            *self.manifest["ai_source_images"],
            *self.manifest["ai_source_sheets"],
            *self.manifest["character_comparison_images"],
        }
        self.assertEqual(len(self.manifest["ai_source_images"]), 148)
        self.assertEqual(len(self.manifest["ai_source_sheets"]), 9)
        self.assertEqual(len(self.manifest["character_comparison_images"]), 10)
        for value in sources:
            path = ROOT / value
            self.assertTrue(path.is_file(), path)
            self.assertNotIn("/archive/", value)

    def test_source_tree_stays_small_and_rebuildable(self) -> None:
        files = [path for path in SOURCE_ROOT.rglob("*") if path.is_file()]
        total_size = sum(path.stat().st_size for path in files)
        self.assertEqual(len(files), 191)
        self.assertLess(total_size, 30 * 1024 * 1024)

        required_masks = (
            ROOT / "editor/ai_identity_masks.json",
            ROOT / "editor/ai_mount_masks.json",
            ROOT / "editor/ai_class_design_overrides.json",
            SOURCE_ROOT
            / "latest/shared-new-classes-v2-refined/identity-masks.json",
            SOURCE_ROOT
            / "latest/keith-lester-tier1-mounted-v1/identity-masks.json",
            SOURCE_ROOT
            / "latest/keith-lester-tier1-mounted-v1/mount-masks.json",
        )
        for path in required_masks:
            self.assertTrue(path.is_file(), path)
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertIsInstance(value, dict)


if __name__ == "__main__":
    unittest.main()
