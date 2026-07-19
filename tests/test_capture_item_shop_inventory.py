from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from tools.capture_item_shop_inventory import (
    ITEM_COUNT,
    artifact_path,
    item_position,
    movement_after,
    movement_to,
    shop_detail_visible,
)


class CaptureItemShopInventoryTests(unittest.TestCase):
    def test_item_positions_cover_eight_pages(self):
        self.assertEqual(item_position(1), (0, 0))
        self.assertEqual(item_position(5), (0, 4))
        self.assertEqual(item_position(6), (1, 0))
        self.assertEqual(item_position(35), (6, 4))
        self.assertEqual(item_position(36), (7, 0))
        self.assertEqual(item_position(37), (7, 1))

    def test_page_transition_returns_to_first_row_before_moving_right(self):
        self.assertEqual(movement_after(1, 0.1), ["down@0.02:0.1"])
        self.assertEqual(
            movement_after(5, 0.1),
            ["right@0.02:0.1"] + ["up@0.02:0.1"] * 4,
        )
        self.assertEqual(
            movement_after(35, 0.1),
            ["right@0.02:0.1", "up@0.02:0.1"],
        )
        self.assertEqual(movement_after(ITEM_COUNT), [])

    def test_movement_to_page_two_first_row_is_deterministic(self):
        self.assertEqual(
            movement_to(6, 0.2),
            ["down@0.02:0.2"] * 4
            + ["right@0.02:0.2"]
            + ["up@0.02:0.2"] * 4,
        )

    def test_artifact_names_are_stable_and_ascii(self):
        prefix = Path("captures/run/8374_item_shop")
        self.assertEqual(
            artifact_path(prefix, 1),
            Path("captures/run/8374_item_shop_id01.png"),
        )
        self.assertEqual(
            artifact_path(prefix, 37),
            Path("captures/run/8374_item_shop_id37.png"),
        )

    def test_invalid_item_ids_are_rejected(self):
        for item_id in (0, ITEM_COUNT + 1):
            with self.assertRaisesRegex(ValueError, "item ID"):
                item_position(item_id)

    def test_shop_panel_detector_uses_raw_blastem_palette_levels(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "frame.png"
            frame = Image.new("RGB", (320, 240), (0, 0, 0))
            for x in range(12, 164):
                for y in range(130, 218):
                    frame.putpixel((x, y), (0, 0, 87))
            frame.save(path)
            self.assertFalse(shop_detail_visible(path))

            for x in range(20, 50):
                for y in range(140, 150):
                    frame.putpixel((x, y), (87, 87, 87))
            frame.save(path)
            self.assertTrue(shop_detail_visible(path))

    def test_shop_panel_detector_accepts_dim_xlib_palette(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "frame.png"
            frame = Image.new("RGB", (320, 240), (0, 0, 0))
            for x in range(12, 164):
                for y in range(130, 218):
                    frame.putpixel((x, y), (0, 0, 49))
            for x in range(20, 50):
                for y in range(140, 150):
                    frame.putpixel((x, y), (49, 49, 49))
            frame.save(path)
            self.assertTrue(shop_detail_visible(path))


if __name__ == "__main__":
    unittest.main()
