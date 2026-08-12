from __future__ import annotations

from collections import Counter
import unittest

from tools.build_ai_class_sprite_assets import (
    ASSET_VERSION,
    SHARED_CLASS_TEMPLATE_SOURCES,
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


TARGETS = ((4, 0x13), (4, 0x14))


class SherryBrightMagicCloakTests(unittest.TestCase):
    def test_retained_magic_sources_identity_and_closure_are_live(self) -> None:
        document = manifest()
        self.assertEqual(document["asset_version"], ASSET_VERSION)
        for key in TARGETS:
            with self.subTest(class_id=f"{key[1]:02X}"):
                source_path, _ = SHARED_CLASS_TEMPLATE_SOURCES[key]
                self.assertTrue(source_path.is_file())
                self.assertIn("shared-elwin-magic-v1", str(source_path))
                row = manifest_row(document, *key)
                self.assertIn(
                    "shared-elwin-magic-v1", row["ai_source_position"]
                )
                expected = compose_untranslated_shared_source(
                    key, document=document
                )
                live = rgba(LIVE_ROOT / f"4/{key[1]:02X}.png")
                self.assertEqual(pixels(expected), pixels(live))

    def test_mage_and_archmage_use_bright_princess_cyan(self) -> None:
        for _, class_id in TARGETS:
            with self.subTest(class_id=f"{class_id:02X}"):
                live = rgba(LIVE_ROOT / f"4/{class_id:02X}.png")
                colors = Counter(flattened_image_data(live))
                self.assertGreaterEqual(colors[(109, 219, 255, 255)], 12)
                self.assertGreaterEqual(colors[(0, 109, 146, 255)], 12)
                self.assertEqual(colors[(0, 36, 73, 255)], 0)
                self.assertGreater(colors[(36, 36, 36, 255)], 0)


if __name__ == "__main__":
    unittest.main()
