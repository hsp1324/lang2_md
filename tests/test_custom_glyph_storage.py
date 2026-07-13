import unittest
from pathlib import Path

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]


class CustomGlyphStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ROOT / builder.IN_ROM).read_bytes()

    def test_font_converter_uses_full_16_bit_glyph_id(self):
        expected = bytes.fromhex(
            "48 E7 03 20 45 F9 00 04 00 00 02 80 00 00 FF FF ED 88 D5 C0"
        )
        self.assertEqual(self.original[0x2C390 : 0x2C390 + len(expected)], expected)

    def test_custom_glyph_storage_precedes_relocated_resources(self):
        glyph_ids = [
            glyph_id
            for start, end in builder.CUSTOM_GLYPH_RANGES
            for glyph_id in range(start, end + 1)
            if glyph_id not in builder.CUSTOM_GLYPH_RESERVED
        ]
        self.assertGreaterEqual(max(glyph_ids), 0x73FE)
        self.assertLessEqual(
            builder.glyph_data_offset(max(glyph_ids)) + builder.GLYPH_BYTES,
            builder.CUSTOM_GLYPH_STORAGE_LIMIT,
        )
        self.assertLessEqual(
            builder.CUSTOM_GLYPH_STORAGE_LIMIT,
            builder.SCENARIO_GLYPH_LIST_RELOC_BASE,
        )


if __name__ == "__main__":
    unittest.main()
