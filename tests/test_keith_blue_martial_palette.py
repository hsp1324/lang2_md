from __future__ import annotations

import unittest

from tools.build_ai_class_sprite_assets import (
    ASSET_VERSION,
    SHARED_CLASS_TEMPLATE_SOURCES,
)
from tools.pillow_compat import flattened_image_data

from tests.ai_class_asset_contract import (
    LIVE_ROOT,
    compose_untranslated_shared_source,
    design_overrides,
    manifest,
    manifest_row,
    pixels,
    rgba,
)


TARGETS = {
    (7, 0x0B): "shared-high-lord-hein-v1/logical16/07-0B.png",
    (7, 0x1A): "shared-swordmaster-hein-v1/logical16/07-1A.png",
}


class KeithBlueMartialPaletteTests(unittest.TestCase):
    def test_high_lord_and_swordmaster_share_sky_blue_family(self) -> None:
        expected = {
            (0, 36, 182, 255),
            (73, 109, 255, 255),
            (109, 219, 255, 255),
        }
        for key in TARGETS:
            with self.subTest(class_id=f"{key[1]:02X}"):
                live = rgba(LIVE_ROOT / f"7/{key[1]:02X}.png")
                colors = {
                    color
                    for color in flattened_image_data(live)
                    if color[3]
                }
                self.assertTrue(expected.issubset(colors))
                self.assertNotIn((219, 146, 36, 255), colors)
                self.assertIn((255, 255, 255, 255), colors)

    def test_retained_source_override_identity_and_closure_are_live(self) -> None:
        document = manifest()
        overrides = design_overrides()
        self.assertEqual(document["asset_version"], ASSET_VERSION)
        for key, expected_suffix in TARGETS.items():
            with self.subTest(class_id=f"{key[1]:02X}"):
                source_path, _ = SHARED_CLASS_TEMPLATE_SOURCES[key]
                self.assertTrue(source_path.is_file())
                self.assertTrue(source_path.as_posix().endswith(expected_suffix))
                row = manifest_row(document, *key)
                self.assertTrue(row["design_override"])
                self.assertEqual(
                    row["design_revision"], overrides[key]["revision"]
                )
                self.assertTrue(
                    row["ai_source_position"].endswith(expected_suffix)
                )
                expected = compose_untranslated_shared_source(
                    key, document=document
                )
                live = rgba(LIVE_ROOT / f"7/{key[1]:02X}.png")
                self.assertEqual(pixels(expected), pixels(live))


if __name__ == "__main__":
    unittest.main()
