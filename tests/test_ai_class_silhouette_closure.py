import json
from pathlib import Path
import unittest

from PIL import Image

from tools.build_ai_class_sprite_assets import (
    ROM_INK,
    close_internal_transparency,
    enclosed_empty_points,
)


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "editor/static/ai-class-sprites"


class AiClassSilhouetteClosureTests(unittest.TestCase):
    def test_closes_only_transparency_separated_from_canvas_edge(self):
        image = Image.new("RGBA", (5, 5), (0, 0, 0, 0))
        for point in {(1, 1), (2, 1), (3, 1), (1, 2), (3, 2), (1, 3), (2, 3), (3, 3)}:
            image.putpixel(point, (255, 255, 255, 255))

        self.assertEqual(close_internal_transparency(image), {(2, 2)})
        self.assertEqual(image.getpixel((2, 2)), ROM_INK)
        self.assertEqual(image.getpixel((0, 0)), (0, 0, 0, 0))

    def test_saved_identity_masks_have_no_enclosed_holes(self):
        document = json.loads(
            (ROOT / "editor/ai_identity_masks.json").read_text(
                encoding="utf-8"
            )
        )
        failures = {}
        for key, raw_points in document["masks"].items():
            holes = enclosed_empty_points({tuple(point) for point in raw_points})
            if holes:
                failures[key] = sorted(holes)
        self.assertEqual(failures, {})

    def test_redesigned_assets_have_no_internal_transparency(self):
        manifest = json.loads(
            (ASSET_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        overrides = json.loads(
            (ROOT / "editor/ai_class_design_overrides.json").read_text(
                encoding="utf-8"
            )
        )["designs"]
        failures = {}
        for commander_id, commander in manifest["commanders"].items():
            for class_id, row in commander["classes"].items():
                if not row["redesigned"]:
                    continue
                # A saved New-class editor override is the user's authoritative
                # 16x16 design. Negative space inside equipment is therefore
                # allowed even when the generated-base closure policy would
                # fill it.
                override_key = row["file"].removesuffix(".png").replace("/", ":")
                if override_key in overrides:
                    continue
                image = Image.open(ASSET_ROOT / row["file"]).convert("RGBA")
                occupied = {
                    (x, y)
                    for y in range(image.height)
                    for x in range(image.width)
                    if image.getpixel((x, y))[3]
                }
                holes = enclosed_empty_points(
                    occupied,
                    width=image.width,
                    height=image.height,
                )
                if holes:
                    failures[row["file"]] = sorted(holes)
        self.assertEqual(failures, {})


if __name__ == "__main__":
    unittest.main()
