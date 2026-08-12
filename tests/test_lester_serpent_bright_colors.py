from __future__ import annotations

import unittest

from tools.build_ai_class_sprite_assets import (
    ASSET_VERSION,
    MOUNT_COLOR_VARIANTS,
)
from tools.pillow_compat import flattened_image_data

from tests.ai_class_asset_contract import (
    LIVE_ROOT,
    compose_rom_mount_variant,
    manifest,
    manifest_row,
    pixels,
    rgba,
)


TARGETS = ((9, 0x1F), (9, 0x2A))


class LesterSerpentBrightColorTests(unittest.TestCase):
    def test_upper_tiers_use_rom_geometry_and_current_mount_colors(self) -> None:
        document = manifest()
        self.assertEqual(document["asset_version"], ASSET_VERSION)
        for key in TARGETS:
            with self.subTest(class_id=f"{key[1]:02X}"):
                row = manifest_row(document, *key)
                self.assertEqual(
                    row["ai_source_position"],
                    f"class-sprites/commanders/9/{key[1]:02X}-p1.png",
                )
                self.assertFalse(row["design_override"])
                self.assertGreater(row["mount_lock_pixel_count"], 0)
                expected = compose_rom_mount_variant(key, document=document)
                live = rgba(LIVE_ROOT / f"9/{key[1]:02X}.png")
                self.assertEqual(pixels(expected), pixels(live))

    def test_bright_ramps_are_present(self) -> None:
        lord = set(flattened_image_data(rgba(LIVE_ROOT / "9/1F.png")))
        master = set(flattened_image_data(rgba(LIVE_ROOT / "9/2A.png")))
        self.assertIn((109, 36, 219, 255), lord)
        self.assertIn((182, 109, 255, 255), lord)
        self.assertIn((219, 0, 0, 255), master)
        self.assertIn((255, 73, 73, 255), master)
        for key in TARGETS:
            self.assertEqual(len(MOUNT_COLOR_VARIANTS[key]), 4)


if __name__ == "__main__":
    unittest.main()
