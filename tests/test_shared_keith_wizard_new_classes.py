from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from tools.build_ai_class_sprite_assets import (
    ASSET_VERSION,
    SHARED_CLASS_TEMPLATE_SOURCES,
    USER_APPROVED_FINAL_PIXEL_OVERRIDES,
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
SOURCE = (
    ROOT
    / "assets/class-sprites/source/latest/"
    "shared-keith-wizard-new-classes-v1"
)
RETAINED_TARGETS = (
    (5, 0x26),
    (9, 0x26),
    (10, 0x26),
    (5, 0x28),
    (10, 0x28),
)
EFFECTIVE_TARGETS = RETAINED_TARGETS
JESSICA_CANONICAL_PIXEL_SHA256 = {
    (10, 0x26): "89c851424f2c2b5d4b7a1ff118a06d80defcc59839f179864f89bc364867efe7",
    (10, 0x28): "ead2e49bdac0c09e0e01a9028bc7abcdea22a0a43187418bd75b83fd29fb8638",
}


class SharedKeithWizardNewClassesTests(unittest.TestCase):
    def test_all_retained_variants_are_native_and_palette_safe(self) -> None:
        for key in RETAINED_TARGETS:
            with self.subTest(key=key):
                source = SOURCE / f"logical16/{key[0]:02d}-{key[1]:02X}.png"
                self.assertTrue(source.is_file())
                image = rgba(source)
                colors = {
                    color
                    for color in flattened_image_data(image)
                    if color[3]
                }
                self.assertEqual(image.size, (16, 16))
                self.assertLessEqual(len(colors), 15)
                self.assertNotIn((0, 0, 0, 255), colors)
                self.assertNotIn((255, 0, 255, 255), colors)

    def test_effective_source_precedence_and_saved_overrides_are_current(self) -> None:
        document = manifest()
        overrides = design_overrides()
        self.assertEqual(document["asset_version"], ASSET_VERSION)
        for key in EFFECTIVE_TARGETS:
            with self.subTest(key=key):
                source_path, _ = SHARED_CLASS_TEMPLATE_SOURCES[key]
                self.assertIn(
                    "shared-keith-wizard-new-classes-v1", str(source_path)
                )
                row = manifest_row(document, *key)
                self.assertIn(
                    "shared-keith-wizard-new-classes-v1",
                    row["ai_source_position"],
                )
                self.assertTrue(row["design_override"])
                self.assertEqual(
                    row["design_revision"], overrides[key]["revision"]
                )

        for key in ((5, 0x26), (9, 0x26), (5, 0x28)):
            expected = compose_untranslated_shared_source(
                key, document=document
            )
            live = rgba(LIVE_ROOT / f"{key[0]}/{key[1]:02X}.png")
            self.assertEqual(pixels(expected), pixels(live))

        # Jessica Zarvera's saved override contains deliberate internal
        # negative space and is the authoritative current live sprite.
        self.assertEqual(
            pixels(rgba(LIVE_ROOT / "10/26.png")),
            pixels(override_image((10, 0x26), overrides)),
        )

    def test_jessica_live_editor_outputs_are_canonical(self) -> None:
        for key, expected_digest in JESSICA_CANONICAL_PIXEL_SHA256.items():
            with self.subTest(key=key):
                live = rgba(LIVE_ROOT / f"{key[0]}/{key[1]:02X}.png")
                rgba_bytes = bytes(
                    channel
                    for color in flattened_image_data(live)
                    for channel in color
                )
                self.assertEqual(
                    hashlib.sha256(rgba_bytes).hexdigest(),
                    expected_digest,
                )
                for point, color in (
                    USER_APPROVED_FINAL_PIXEL_OVERRIDES[key].items()
                ):
                    self.assertEqual(live.getpixel(point), color)


if __name__ == "__main__":
    unittest.main()
