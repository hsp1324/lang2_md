from __future__ import annotations

import unittest

from tools.build_ai_class_sprite_assets import (
    ASSET_VERSION,
    SHARED_CLASS_TEMPLATE_SOURCES,
    SHARED_LIANA_LANA_HEALER_SOURCE_KEYS,
)
from tools.pillow_compat import flattened_image_data

from tests.ai_class_asset_contract import (
    LIVE_ROOT,
    compose_untranslated_shared_source,
    manifest,
    manifest_row,
    pixels,
    rgba,
)


class LianaLanaHealerVariantTests(unittest.TestCase):
    def test_retained_sources_identity_and_closure_are_live(self) -> None:
        document = manifest()
        self.assertEqual(document["asset_version"], ASSET_VERSION)
        self.assertEqual(
            SHARED_LIANA_LANA_HEALER_SOURCE_KEYS,
            {(2, 0x08), (3, 0x08)},
        )
        for key in sorted(SHARED_LIANA_LANA_HEALER_SOURCE_KEYS):
            with self.subTest(commander_id=key[0]):
                source_path, _ = SHARED_CLASS_TEMPLATE_SOURCES[key]
                self.assertTrue(source_path.is_file())
                self.assertIn("shared-liana-lana-healer-v1", str(source_path))
                row = manifest_row(document, *key)
                self.assertIn(
                    "shared-liana-lana-healer-v1",
                    row["ai_source_position"],
                )
                expected = compose_untranslated_shared_source(
                    key, document=document
                )
                live = rgba(LIVE_ROOT / f"{key[0]}/08.png")
                self.assertEqual(pixels(expected), pixels(live))

    def test_liana_and_lana_keep_distinct_red_and_blue_roles(self) -> None:
        liana = rgba(LIVE_ROOT / "2/08.png")
        lana = rgba(LIVE_ROOT / "3/08.png")
        self.assertEqual(liana.size, (16, 16))
        self.assertEqual(lana.size, (16, 16))
        liana_colors = set(flattened_image_data(liana))
        lana_colors = set(flattened_image_data(lana))
        self.assertIn((219, 0, 0, 255), liana_colors)
        self.assertIn((255, 109, 109, 255), liana_colors)
        self.assertNotIn((219, 0, 0, 255), lana_colors)
        self.assertNotIn((255, 109, 109, 255), lana_colors)
        self.assertIn((0, 36, 182, 255), lana_colors)
        self.assertIn((73, 109, 255, 255), lana_colors)


if __name__ == "__main__":
    unittest.main()
