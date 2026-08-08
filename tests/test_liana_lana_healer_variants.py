from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image

from tools.build_ai_class_sprite_assets import (
    SHARED_CLASS_TEMPLATE_SOURCES,
    SHARED_LIANA_LANA_HEALER_SOURCE_KEYS,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "docs/assets/ai-class-source/latest/shared-liana-lana-healer-v1"
)
LIVE = ROOT / "editor/static/ai-class-sprites"


class LianaLanaHealerVariantTests(unittest.TestCase):
    def test_latest_liana_geometry_is_shared_with_blue_lana(self) -> None:
        liana = Image.open(LIVE / "2/08.png").convert("RGBA")
        lana = Image.open(LIVE / "3/08.png").convert("RGBA")
        overrides = json.loads(
            (ROOT / "editor/ai_class_design_overrides.json").read_text(
                encoding="utf-8"
            )
        )["designs"]
        manifest = json.loads(
            (LIVE / "manifest.json").read_text(encoding="utf-8")
        )
        row = manifest["commanders"]["2"]["classes"][str(0x08)]
        self.assertTrue(row["design_override"])
        self.assertEqual(
            row["design_revision"], overrides["2:08"]["revision"]
        )
        self.assertEqual(liana.size, lana.size)
        self.assertEqual(liana.size, (16, 16))
        liana_colors = set(liana.get_flattened_data())
        lana_colors = set(lana.get_flattened_data())
        self.assertIn((219, 0, 0, 255), liana_colors)
        self.assertIn((255, 109, 109, 255), liana_colors)
        self.assertNotIn((219, 0, 0, 255), lana_colors)
        self.assertNotIn((255, 109, 109, 255), lana_colors)
        self.assertIn((0, 36, 182, 255), lana_colors)
        self.assertIn((73, 109, 255, 255), lana_colors)

    def test_lana_identity_mask_and_sources_are_exact(self) -> None:
        masks = json.loads(
            (ROOT / "editor/ai_identity_masks.json").read_text(
                encoding="utf-8"
            )
        )["masks"]
        overrides = json.loads(
            (ROOT / "editor/ai_class_design_overrides.json").read_text(
                encoding="utf-8"
            )
        )["designs"]
        for commander_id in (2, 3):
            live = Image.open(LIVE / f"{commander_id}/08.png").convert(
                "RGBA"
            )
            original = Image.open(
                ROOT
                / "editor/static/class-sprites/commanders"
                / str(commander_id)
                / "08-p1.png"
            ).convert("RGBA")
            override_key = f"{commander_id}:08"
            if override_key in overrides:
                manifest = json.loads(
                    (LIVE / "manifest.json").read_text(encoding="utf-8")
                )
                row = manifest["commanders"][str(commander_id)]["classes"][
                    str(0x08)
                ]
                self.assertTrue(row["design_override"])
                self.assertEqual(
                    row["design_revision"], overrides[override_key]["revision"]
                )
            else:
                for raw_point in masks[override_key]:
                    point = tuple(raw_point)
                    if original.getpixel(point)[3]:
                        self.assertEqual(
                            live.getpixel(point), original.getpixel(point)
                        )

    def test_aggregate_mapping_and_manifest_version(self) -> None:
        self.assertEqual(
            SHARED_LIANA_LANA_HEALER_SOURCE_KEYS,
            {(2, 0x08), (3, 0x08)},
        )
        for key in SHARED_LIANA_LANA_HEALER_SOURCE_KEYS:
            self.assertIn(
                "shared-liana-lana-healer-v1",
                str(SHARED_CLASS_TEMPLATE_SOURCES[key][0]),
            )
        manifest = json.loads(
            (LIVE / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["asset_version"],
            "identity-mask-and-silhouette-closure-v107",
        )
        for commander_id in (2, 3):
            row = manifest["commanders"][str(commander_id)]["classes"][
                str(0x08)
            ]
            self.assertIn(
                "shared-liana-lana-healer-v1", row["ai_source_position"]
            )


if __name__ == "__main__":
    unittest.main()
