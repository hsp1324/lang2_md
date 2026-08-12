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
    manifest,
    manifest_row,
    pixels,
    rgba,
)


TARGETS = ((2, 0x18), (4, 0x15))


class LianaSageSherryWizardPaletteTests(unittest.TestCase):
    def test_retained_full_sprite_override_and_closure_are_live(self) -> None:
        document = manifest()
        self.assertEqual(document["asset_version"], ASSET_VERSION)
        for key in TARGETS:
            with self.subTest(key=key):
                source_path, _ = SHARED_CLASS_TEMPLATE_SOURCES[key]
                self.assertTrue(source_path.is_file())
                self.assertIn(
                    "liana-sage-sherry-wizard-palette-v1",
                    str(source_path),
                )
                row = manifest_row(document, *key)
                self.assertEqual(
                    row["identity_lock_transparency_mode"],
                    "approved_full_sprite_template",
                )
                expected = compose_untranslated_shared_source(
                    key, document=document
                )
                live = rgba(
                    LIVE_ROOT / f"{key[0]}/{key[1]:02X}.png"
                )
                self.assertEqual(pixels(expected), pixels(live))
                self.assertLessEqual(
                    len(
                        {
                            color
                            for color in flattened_image_data(live)
                            if color[3]
                        }
                    ),
                    15,
                )

    def test_expected_bright_material_colors_are_present(self) -> None:
        sage_colors = set(
            flattened_image_data(rgba(LIVE_ROOT / "2/18.png"))
        )
        wizard_colors = set(
            flattened_image_data(rgba(LIVE_ROOT / "4/15.png"))
        )
        self.assertIn((146, 36, 73, 255), sage_colors)
        self.assertIn((219, 0, 0, 255), sage_colors)
        self.assertIn((0, 73, 109, 255), wizard_colors)
        self.assertIn((0, 109, 146, 255), wizard_colors)
        self.assertIn((109, 219, 255, 255), wizard_colors)
        self.assertNotIn((73, 36, 146, 255), wizard_colors)
        self.assertNotIn((146, 109, 219, 255), wizard_colors)


if __name__ == "__main__":
    unittest.main()
