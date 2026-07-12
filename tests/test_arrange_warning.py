from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class ArrangeWarningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()

    def test_incomplete_arrangement_warning_uses_korean_local_glyphs(self):
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


if __name__ == "__main__":
    unittest.main()
