from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class TitleLoadScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jp = JP_ROM.read_bytes()
        cls.ko = KO_ROM.read_bytes()
        cls.patch_data = bytearray(cls.jp)
        builder.expand_rom(cls.patch_data)
        unique_chars = list(dict.fromkeys("".join(builder.TITLE_LOAD_TEXTS)))
        cls.glyph_by_char = {
            char: 0x7000 + index
            for index, char in enumerate(unique_chars)
            if char != " "
        }
        builder.patch_title_load_screen(cls.patch_data, cls.glyph_by_char)

    @staticmethod
    def words(data: bytes, offset: int, count: int) -> list[int]:
        return [builder.be16(data, offset + index * 2) for index in range(count)]

    def test_japanese_source_layout_is_locked(self):
        self.assertEqual(
            tuple(
                self.words(
                    self.jp,
                    builder.TITLE_LOAD_GLYPH_LIST,
                    builder.TITLE_LOAD_GLYPH_COUNT,
                )
            ),
            builder.TITLE_LOAD_GLYPH_LIST_ORIGINAL,
        )
        self.assertEqual(
            builder.be16(
                self.jp,
                builder.TITLE_LOAD_GLYPH_LIST
                + builder.TITLE_LOAD_GLYPH_COUNT * 2,
            ),
            0xFFFF,
        )
        for offset, (capacity, _) in builder.TITLE_LOAD_RECORDS.items():
            self.assertEqual(
                tuple(self.words(self.jp, offset, capacity)),
                builder.TITLE_LOAD_RECORD_ORIGINALS[offset],
            )
            self.assertEqual(builder.be16(self.jp, offset + capacity * 2), 0xFFFF)

    def test_dynamic_cursor_and_digit_glyphs_are_preserved(self):
        self.assertEqual(
            self.words(self.ko, builder.TITLE_LOAD_GLYPH_LIST, 11),
            self.words(self.jp, builder.TITLE_LOAD_GLYPH_LIST, 11),
        )

    def test_all_slot_variants_use_localized_tokens_and_keep_boundaries(self):
        glyphs = self.words(
            self.patch_data,
            builder.TITLE_LOAD_GLYPH_LIST,
            builder.TITLE_LOAD_GLYPH_COUNT,
        )
        for offset, (capacity, text) in builder.TITLE_LOAD_RECORDS.items():
            tokens = self.words(self.patch_data, offset, capacity)
            rendered = [glyphs[token] for token in tokens[: len(text)]]
            expected = [
                builder.SPACE_GLYPH
                if char == " "
                else self.glyph_by_char[char]
                for char in text
            ]
            self.assertEqual(rendered, expected)
            self.assertEqual(
                builder.be16(self.patch_data, offset + capacity * 2), 0xFFFF
            )

    def test_load_header_is_relocated_without_abbreviation(self):
        self.assertEqual(
            self.ko[
                builder.TITLE_LOAD_HEADER_LEA : builder.TITLE_LOAD_HEADER_LEA + 6
            ],
            bytes.fromhex("41 F9")
            + builder.TITLE_LOAD_HEADER_RELOC.to_bytes(4, "big"),
        )
        header = self.words(self.patch_data, builder.TITLE_LOAD_HEADER_RELOC, 7)
        self.assertEqual(
            header[:2], [builder.TITLE_LOAD_HEADER_RELOC_X, 0x0006]
        )
        self.assertEqual(header[-1], 0xFFFF)
        glyphs = self.words(
            self.patch_data,
            builder.TITLE_LOAD_GLYPH_LIST,
            builder.TITLE_LOAD_GLYPH_COUNT,
        )
        self.assertEqual(
            [glyphs[token] for token in header[2:-1]],
            [self.glyph_by_char[char] for char in "불러오기"],
        )

    def test_load_header_leaves_the_selector_number_cell_free(self):
        # Four 16-pixel glyphs beginning at tile X=15 occupy tile columns
        # 15..22. The stock selector number sprite starts at visible X=184,
        # tile column 23, so the two surfaces are adjacent rather than stacked.
        start_tile = builder.TITLE_LOAD_HEADER_RELOC_X
        self.assertEqual(start_tile + 4 * 2, 23)


if __name__ == "__main__":
    unittest.main()
