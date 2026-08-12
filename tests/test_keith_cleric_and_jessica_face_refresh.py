from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.build_ai_class_sprite_assets import (
    ASSET_VERSION,
    IDENTITY_PIXEL_TRANSLATIONS,
    SHARED_CLASS_TEMPLATE_SOURCES,
)
from tools.pillow_compat import flattened_image_data

from tests.ai_class_asset_contract import (
    LIVE_ROOT,
    compose_untranslated_shared_source,
    design_overrides,
    manifest,
    manifest_row,
    override_image,
    pixels,
    rgba,
)


ROOT = Path(__file__).resolve().parents[1]


class KeithClericSkyPaletteTests(unittest.TestCase):
    def test_healer_and_priest_use_keith_sky_blue_family(self) -> None:
        document = manifest()
        for key in ((7, 0x08), (7, 0x11)):
            with self.subTest(class_id=f"{key[1]:02X}"):
                source_path, _ = SHARED_CLASS_TEMPLATE_SOURCES[key]
                self.assertTrue(source_path.is_file())
                expected = compose_untranslated_shared_source(
                    key, document=document
                )
                live = rgba(LIVE_ROOT / f"7/{key[1]:02X}.png")
                self.assertEqual(pixels(expected), pixels(live))
                colors = set(flattened_image_data(live))
                self.assertIn((73, 109, 255, 255), colors)
                self.assertIn((109, 219, 255, 255), colors)

        healer = set(flattened_image_data(rgba(LIVE_ROOT / "7/08.png")))
        priest = set(flattened_image_data(rgba(LIVE_ROOT / "7/11.png")))
        self.assertNotIn((0, 146, 109, 255), healer)
        self.assertNotIn((36, 219, 146, 255), healer)
        self.assertNotIn((36, 146, 36, 255), priest)
        self.assertNotIn((109, 219, 146, 255), priest)


class JessicaFaceMaskRefreshTests(unittest.TestCase):
    def test_global_masks_and_saved_overrides_are_current(self) -> None:
        masks = json.loads(
            (ROOT / "editor/ai_identity_masks.json").read_text(
                encoding="utf-8"
            )
        )["masks"]
        overrides = design_overrides()
        document = manifest()
        self.assertEqual(document["asset_version"], ASSET_VERSION)

        for key in ((10, 0x08), (10, 0x11), (10, 0x26)):
            with self.subTest(class_id=f"{key[1]:02X}"):
                mask_key = f"{key[0]}:{key[1]:02X}"
                self.assertIn(mask_key, masks)
                self.assertIn(key, overrides)
                row = manifest_row(document, *key)
                self.assertTrue(row["design_override"])
                self.assertEqual(
                    row["design_revision"], overrides[key]["revision"]
                )
                self.assertEqual(
                    row["identity_lock_pixel_count"], len(masks[mask_key])
                )
                live = rgba(LIVE_ROOT / f"10/{key[1]:02X}.png")
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

    def test_saved_overrides_feed_the_current_live_assets(self) -> None:
        document = manifest()
        for key in ((10, 0x08), (10, 0x11)):
            with self.subTest(class_id=f"{key[1]:02X}"):
                expected = compose_untranslated_shared_source(
                    key, document=document
                )
                live = rgba(LIVE_ROOT / f"10/{key[1]:02X}.png")
                self.assertEqual(pixels(expected), pixels(live))

        # Jessica's saved Zarvera edit is the current authoritative full
        # sprite. Its deliberate internal negative space is not regenerated.
        zarvera = rgba(LIVE_ROOT / "10/26.png")
        self.assertEqual(pixels(zarvera), pixels(override_image((10, 0x26))))

    def test_wizard_palette_and_zarvera_placement_are_current(self) -> None:
        wizard = rgba(LIVE_ROOT / "10/15.png")
        self.assertEqual(wizard.getpixel((6, 6)), (146, 146, 146, 255))
        self.assertNotIn(
            (36, 73, 255, 255), set(flattened_image_data(wizard))
        )
        self.assertNotIn((10, 0x26), IDENTITY_PIXEL_TRANSLATIONS)
        self.assertNotIn((10, 0x1A), IDENTITY_PIXEL_TRANSLATIONS)


if __name__ == "__main__":
    unittest.main()
