import unittest
from pathlib import Path

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]


class CustomGlyphStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

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

    def test_period_and_comma_use_dialogue_baseline(self):
        font = builder.ImageFont.truetype(str(ROOT / builder.FONT_PATH), 16)
        blank_offset = builder.glyph_data_offset(builder.SPACE_GLYPH)
        blank = self.original[blank_offset : blank_offset + builder.GLYPH_BYTES]

        def dark_rows(char: str) -> set[int]:
            payload = builder.render_hangul_glyph(char, font, blank)
            rows = set()
            for tile in range(4):
                y_base = (tile // 2) * 8
                for row in range(8):
                    source = (tile * 8 + row) * 2
                    if payload[source : source + 2] != blank[source : source + 2]:
                        rows.add(y_base + row)
            return rows

        self.assertEqual(dark_rows("."), {12, 13})
        self.assertEqual(dark_rows(","), {11, 12, 13, 14})

    def test_built_rom_installs_bottom_aligned_period_and_comma(self):
        font = builder.ImageFont.truetype(str(ROOT / builder.FONT_PATH), 16)
        blank_offset = builder.glyph_data_offset(builder.SPACE_GLYPH)
        blank = self.original[blank_offset : blank_offset + builder.GLYPH_BYTES]

        installed_payloads = {
            self.built[
                builder.glyph_data_offset(glyph_id) :
                builder.glyph_data_offset(glyph_id) + builder.GLYPH_BYTES
            ]
            for start, end in builder.CUSTOM_GLYPH_RANGES
            for glyph_id in range(start, end + 1)
            if glyph_id not in builder.CUSTOM_GLYPH_RESERVED
        }

        for char in ".,":
            with self.subTest(char=char):
                self.assertIn(
                    builder.render_hangul_glyph(char, font, blank),
                    installed_payloads,
                )


if __name__ == "__main__":
    unittest.main()
