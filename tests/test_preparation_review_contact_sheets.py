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
            with Image.open(destination) as result:
                self.assertEqual(result.size, (640, 520))
                self.assertEqual(result.getpixel((10, 30)), (0, 0, 0))
                self.assertEqual(result.getpixel((330, 30)), (1, 1, 1))
                self.assertEqual(result.getpixel((10, 290)), (2, 2, 2))
                self.assertEqual(result.getpixel((330, 290)), (3, 3, 3))

    def test_group_selection_omits_duplicate_returned_menu(self) -> None:
        with TemporaryDirectory() as directory:
            pre = Path(directory)
            arrangement = pre / "arrangement"
            arrangement.mkdir()
            for name in ("menu.png", "returned_menu.png", "roster_page_01.png"):
                Image.new("RGB", (320, 240)).save(arrangement / name)
            selected = sheets.sources_for(pre, "arrangement")
            self.assertEqual(
                [path.name for path in selected],
                ["menu.png", "roster_page_01.png"],
            )


if __name__ == "__main__":
    unittest.main()
