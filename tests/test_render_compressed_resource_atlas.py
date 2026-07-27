from pathlib import Path
import unittest

from tools.jp_compressed_resource_inventory import decoded_payload, resource_pointers
from tools.render_compressed_resource_atlas import (
    decode_4bpp_tiles,
    immediate_resource_indices,
    parse_indices,
    render_atlas,
    render_tiles,
)


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class CompressedResourceAtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()

    def test_decodes_nibbles_in_mega_drive_tile_order(self):
        payload = bytes([0x01, 0x23, 0x45, 0x67] * 8)
        tiles = decode_4bpp_tiles(payload)
        self.assertEqual(len(tiles), 1)
        self.assertEqual(tiles[0][:8], list(range(8)))
        self.assertEqual(tiles[0][-8:], list(range(8)))

        image = render_tiles(payload)
        self.assertEqual(image.size, (8, 8))
        self.assertEqual(image.getpixel((0, 0)), (0, 0, 0, 255))
        self.assertEqual(image.getpixel((7, 7)), (119, 119, 119, 255))

    def test_rejects_non_tile_payload(self):
        with self.assertRaisesRegex(ValueError, "not divisible by 32"):
            decode_4bpp_tiles(bytes(31))

    def test_parses_ids_and_inclusive_ranges(self):
        self.assertEqual(parse_indices("1, 3-5, 0x08"), [1, 3, 4, 5, 8])
        with self.assertRaisesRegex(ValueError, "descending"):
            parse_indices("5-3")

    def test_immediate_index_set_includes_known_ui_resources(self):
        indices = immediate_resource_indices(self.japanese)
        self.assertIn(1, indices)
        self.assertIn(223, indices)
        self.assertIn(391, indices)
        self.assertIn(393, indices)
        self.assertEqual(len(indices), 50)

    def test_renders_real_title_logo_payload(self):
        pointers = resource_pointers(self.japanese)
        payload = decoded_payload(self.japanese, pointers[393])
        self.assertIsNotNone(payload)
        image = render_tiles(payload)
        self.assertEqual(image.size, (128, 96))
        self.assertNotEqual(image.getbbox(), None)

    def test_renders_labeled_atlas_panel_without_clipping_the_payload(self):
        image = render_atlas(
            self.japanese,
            [393],
            tiles_per_row=16,
            panel_columns=1,
            scale=1,
        )
        self.assertGreaterEqual(image.width, 128)
        self.assertGreaterEqual(image.height, 96 + 14 + 12)
        with self.assertRaisesRegex(ValueError, "outside"):
            render_atlas(self.japanese, [429])


if __name__ == "__main__":
    unittest.main()
