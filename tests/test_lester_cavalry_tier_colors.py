from __future__ import annotations

import unittest

from tools.build_ai_class_sprite_assets import (
    ASSET_VERSION,
    MOUNT_SHADE_VARIANTS,
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


TARGETS = ((9, 0x0C), (9, 0x1B))


class LesterCavalryTierColorTests(unittest.TestCase):
    def test_rom_mount_mask_variants_are_exactly_live(self) -> None:
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

    def test_mount_ramps_are_distinct(self) -> None:
        for key in TARGETS:
            colors = set(
                flattened_image_data(
                    rgba(LIVE_ROOT / f"9/{key[1]:02X}.png")
                )
            )
            for color in MOUNT_SHADE_VARIANTS[key]:
                self.assertIn(color, colors)
        self.assertNotEqual(
            MOUNT_SHADE_VARIANTS[TARGETS[0]],
            MOUNT_SHADE_VARIANTS[TARGETS[1]],
        )


if __name__ == "__main__":
    unittest.main()
