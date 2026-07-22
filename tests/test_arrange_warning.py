from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class ArrangeWarningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()

    def test_incomplete_arrangement_warning_uses_korean_local_glyphs(self):
        self.assertEqual(builder.ARRANGE_WARNING_GLYPH_TEXT, "미완료입니다")
        self.assertEqual(len(builder.ARRANGE_WARNING_KOREAN_TOKENS), 16)
        self.assertEqual(builder.ARRANGE_WARNING_KOREAN_TOKENS.count(0x0014), 4)
        original_glyphs = tuple(
            builder.be16(
                self.japanese,
                builder.ARRANGE_WARNING_GLYPH_OFFSET + index * 2,
            )
            for index in range(len(builder.ARRANGE_WARNING_ORIGINAL_GLYPHS))
        )
        self.assertEqual(original_glyphs, builder.ARRANGE_WARNING_ORIGINAL_GLYPHS)
        self.assertEqual(
            tuple(
                builder.be16(
                    self.korean,
                    builder.ARRANGE_WARNING_TOKEN_OFFSET + index * 2,
                )
                for index in range(len(builder.ARRANGE_WARNING_KOREAN_TOKENS))
            ),
            builder.ARRANGE_WARNING_KOREAN_TOKENS,
        )
        self.assertNotEqual(
            self.korean[
                builder.ARRANGE_WARNING_GLYPH_OFFSET:
                builder.ARRANGE_WARNING_GLYPH_OFFSET
                + len(builder.ARRANGE_WARNING_ORIGINAL_GLYPHS) * 2
            ],
            self.japanese[
                builder.ARRANGE_WARNING_GLYPH_OFFSET:
                builder.ARRANGE_WARNING_GLYPH_OFFSET
                + len(builder.ARRANGE_WARNING_ORIGINAL_GLYPHS) * 2
            ],
        )

    def test_incomplete_arrangement_warning_has_readable_spacing(self):
        self.assertEqual(
            builder.ARRANGE_WARNING_KOREAN_TOKENS,
            (
                0x0001,
                0x000B, 0x000C, 0x000D,
                0x0014,
                0x000E, 0x000F,
                0x0014,
                0x0020, 0x0021, 0x0022, 0x0023, 0x0024, 0x0025,
                0x0014, 0x0014,
            ),
        )


if __name__ == "__main__":
    unittest.main()
