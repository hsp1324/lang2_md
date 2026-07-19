from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / builder.IN_ROM
KO_ROM = ROOT / builder.OUT_ROM


class BattleResultScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jp = JP_ROM.read_bytes()
        cls.ko = KO_ROM.read_bytes()

    def words(self, data, offset, count):
        return tuple(builder.be16(data, offset + index * 2) for index in range(count))

    def test_source_header_is_senka_houkoku(self):
        self.assertEqual(
            self.words(
                self.jp,
                builder.BATTLE_RESULT_HEADER_GLYPH_LIST,
                len(builder.BATTLE_RESULT_HEADER_EXPECTED_GLYPHS),
            ),
            builder.BATTLE_RESULT_HEADER_EXPECTED_GLYPHS,
        )
        self.assertEqual(
            builder.be16(
                self.jp,
                builder.BATTLE_RESULT_HEADER_GLYPH_LIST
                + len(builder.BATTLE_RESULT_HEADER_EXPECTED_GLYPHS) * 2,
            ),
            0xFFFF,
        )

    def test_built_header_renders_jeongwa_bogo(self):
        text = builder.DIRECT_WORD_SEQUENCE_PATCHES[
            builder.BATTLE_RESULT_HEADER_GLYPH_LIST
        ][1]
        self.assertEqual(text, "전과보고")

        font = builder.ImageFont.truetype(str(ROOT / builder.FONT_PATH), 16)
        blank_offset = builder.glyph_data_offset(builder.SPACE_GLYPH)
        blank = self.jp[blank_offset : blank_offset + builder.GLYPH_BYTES]
        glyphs = self.words(
            self.ko,
            builder.BATTLE_RESULT_HEADER_GLYPH_LIST,
            len(text),
        )
        for char, glyph in zip(text, glyphs):
            with self.subTest(char=char):
                actual = self.ko[
                    builder.glyph_data_offset(glyph) :
                    builder.glyph_data_offset(glyph) + builder.GLYPH_BYTES
                ]
                self.assertEqual(
                    actual,
                    builder.render_hangul_glyph(char, font, blank),
                )

        self.assertEqual(
            builder.be16(
                self.ko,
                builder.BATTLE_RESULT_HEADER_GLYPH_LIST + len(text) * 2,
            ),
            0xFFFF,
        )

    def test_source_mutation_is_rejected(self):
        data = bytearray(self.jp)
        data[builder.BATTLE_RESULT_HEADER_GLYPH_LIST] ^= 1
        with self.assertRaisesRegex(ValueError, "battle result header glyph list changed"):
            builder.validate_battle_result_header(data)


if __name__ == "__main__":
    unittest.main()
