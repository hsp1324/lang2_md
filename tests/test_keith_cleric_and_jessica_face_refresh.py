from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image

from tools.build_ai_class_sprite_assets import (
    IDENTITY_PIXEL_TRANSLATIONS,
    close_internal_transparency,
)


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "editor/static/ai-class-sprites"
JESSICA_REFRESH = (
    ROOT
    / "docs/assets/ai-class-source/latest/jessica-face-mask-refresh-v1"
)


class KeithClericSkyPaletteTests(unittest.TestCase):
    def test_healer_and_priest_use_keith_sky_blue_family(self) -> None:
        sources = {
            0x08: ROOT
            / "docs/assets/ai-class-source/latest/"
            "shared-new-classes-v2-refined/logical16/07-08.png",
            0x11: ROOT
            / "docs/assets/ai-class-source/latest/"
            "shared-hein-classes-v1/logical16/07-11.png",
        }
        for class_id, source_path in sources.items():
            with self.subTest(class_id=f"{class_id:02X}"):
                source = Image.open(source_path).convert("RGBA")
                close_internal_transparency(source)
                live = Image.open(
                    LIVE / f"7/{class_id:02X}.png"
                ).convert("RGBA")
                self.assertEqual(
                    list(source.get_flattened_data()),
                    list(live.get_flattened_data()),
                )
                colors = set(live.get_flattened_data())
                self.assertIn((73, 109, 255, 255), colors)
                self.assertIn((109, 219, 255, 255), colors)

        healer = set(
            Image.open(LIVE / "7/08.png")
            .convert("RGBA")
            .get_flattened_data()
        )
        priest = set(
            Image.open(LIVE / "7/11.png")
            .convert("RGBA")
            .get_flattened_data()
        )
        self.assertNotIn((0, 146, 109, 255), healer)
        self.assertNotIn((36, 219, 146, 255), healer)
        self.assertNotIn((36, 146, 36, 255), priest)
        self.assertNotIn((109, 219, 146, 255), priest)


class JessicaFaceMaskRefreshTests(unittest.TestCase):
    def test_latest_masks_are_exactly_restored(self) -> None:
        masks = json.loads(
            (ROOT / "editor/ai_identity_masks.json").read_text(
                encoding="utf-8"
            )
        )["masks"]
        report = json.loads(
            (JESSICA_REFRESH / "validation-report.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(report["all_accepted"])
        for row in report["classes"]:
            class_id = int(row["class_id"], 16)
            live = Image.open(
                LIVE / f"10/{class_id:02X}.png"
            ).convert("RGBA")
            source = Image.open(
                JESSICA_REFRESH / row["file"]
            ).convert("RGBA")
            close_internal_transparency(source)
            original = Image.open(
                ROOT
                / "editor/static/class-sprites/commanders/10"
                / f"{class_id:02X}-p1.png"
            ).convert("RGBA")
            self.assertEqual(
                list(source.get_flattened_data()),
                list(live.get_flattened_data()),
            )
            points = {
                tuple(point) for point in masks[f"10:{class_id:02X}"]
            }
            for point in points:
                if original.getpixel(point)[3]:
                    self.assertEqual(
                        live.getpixel(point),
                        original.getpixel(point),
                        (class_id, point),
                    )
            visible = {
                color for color in live.get_flattened_data() if color[3]
            }
            self.assertLessEqual(len(visible), 15)

    def test_wizard_palette_and_zarvera_placement_are_current(self) -> None:
        wizard = Image.open(LIVE / "10/15.png").convert("RGBA")
        self.assertEqual(wizard.getpixel((6, 6)), (146, 146, 146, 255))
        self.assertNotIn(
            (36, 73, 255, 255), set(wizard.get_flattened_data())
        )
        self.assertNotIn((10, 0x26), IDENTITY_PIXEL_TRANSLATIONS)
        self.assertNotIn((10, 0x1A), IDENTITY_PIXEL_TRANSLATIONS)

    def test_manifest_and_saved_overrides_match_live(self) -> None:
        manifest = json.loads(
            (LIVE / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["asset_version"],
            "identity-mask-and-silhouette-closure-v107",
        )
        overrides = json.loads(
            (ROOT / "editor/ai_class_design_overrides.json").read_text(
                encoding="utf-8"
            )
        )["designs"]
        for class_id in (0x08, 0x11, 0x26):
            live = Image.open(
                LIVE / f"10/{class_id:02X}.png"
            ).convert("RGBA")
            expected = Image.new("RGBA", (16, 16))
            expected.putdata(
                [
                    tuple(color)
                    for color in overrides[f"10:{class_id:02X}"]["pixels"]
                ]
            )
            close_internal_transparency(expected)
            self.assertEqual(
                [list(color) for color in expected.get_flattened_data()],
                [list(color) for color in live.get_flattened_data()],
            )


if __name__ == "__main__":
    unittest.main()
