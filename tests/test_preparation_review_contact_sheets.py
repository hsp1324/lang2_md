from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from tools import build_preparation_review_contact_sheets as sheets


class PreparationReviewContactSheetTests(unittest.TestCase):
    def test_contact_sheet_preserves_four_full_frames(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            sources = []
            for index in range(4):
                path = root / f"source_{index}.png"
                Image.new("RGB", (320, 240), (index, index, index)).save(path)
                sources.append(path)
            destination = root / "sheet.png"
            sheets.build_sheet(sources, destination)
            self.assertTrue(sheets.sheet_matches_sources(destination, sources))
            with Image.open(destination) as result:
                self.assertEqual(result.size, (640, 520))
                self.assertEqual(result.getpixel((10, 30)), (0, 0, 0))
                self.assertEqual(result.getpixel((330, 30)), (1, 1, 1))
                self.assertEqual(result.getpixel((10, 290)), (2, 2, 2))
                self.assertEqual(result.getpixel((330, 290)), (3, 3, 3))

            with Image.open(destination) as opened:
                tampered = opened.convert("RGB")
            tampered.putpixel((100, 100), (255, 0, 255))
            tampered.save(destination)
            self.assertFalse(sheets.sheet_matches_sources(destination, sources))

    def test_group_selection_includes_shop_return_surface(self) -> None:
        with TemporaryDirectory() as directory:
            pre = Path(directory)
            arrangement = pre / "arrangement"
            arrangement.mkdir()
            for name in ("menu.png", "returned_menu.png", "roster_page_01.png"):
                Image.new("RGB", (320, 240)).save(arrangement / name)
            selected = sheets.sources_for(pre, "arrangement")
            self.assertEqual(
                [path.name for path in selected],
                ["menu.png", "returned_menu.png", "roster_page_01.png"],
            )

    def test_overview_and_fixed_groups_include_key_surfaces(self) -> None:
        with TemporaryDirectory() as directory:
            pre = Path(directory)
            (pre / "fixed").mkdir()
            Image.new("RGB", (320, 240)).save(pre / "root.png")
            for name in ("map_entry.png", "record_00.png"):
                Image.new("RGB", (320, 240)).save(pre / "fixed" / name)
            self.assertEqual(sheets.sources_for(pre, "overview"), [pre / "root.png"])
            self.assertEqual(
                [path.name for path in sheets.sources_for(pre, "fixed")],
                ["map_entry.png", "record_00.png"],
            )

    def test_shop_group_includes_menu_items_and_both_return_states(self) -> None:
        with TemporaryDirectory() as directory:
            pre = Path(directory) / "pre"
            pre.mkdir()
            shop = pre.parent / "shop"
            shop.mkdir()
            for name in (
                "menu.png",
                "item_list.png",
                "returned_unfocused.png",
                "returned_focused.png",
            ):
                Image.new("RGB", (320, 240)).save(shop / name)
            self.assertEqual(
                [path.name for path in sheets.sources_for(pre, "shop")],
                [
                    "item_list.png",
                    "menu.png",
                    "returned_focused.png",
                    "returned_unfocused.png",
                ],
            )


if __name__ == "__main__":
    unittest.main()
