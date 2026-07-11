from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class StartSubmenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jp = JP_ROM.read_bytes()
        cls.ko = KO_ROM.read_bytes()

    def words(self, offset, count):
        return [builder.be16(self.ko, offset + index * 2) for index in range(count)]

    def test_save_choices_preserve_control_words_and_terminator(self):
        self.assertEqual(builder.be16(self.ko, 0x9AE56), 0xFFFD)
        self.assertEqual(self.words(0x9AE58, 2), [0x0003, 0x0002])
        self.assertEqual(self.words(0x9AE5C, 6), [1, 4, 5, 24, 25, 0x3F])
        self.assertEqual(builder.be16(self.ko, 0x9AE68), 0xFFFF)

    def test_save_choices_use_original_latin_glyphs(self):
        expected = {1: 0x02C6, 4: 0x0326, 5: 0x0061, 24: 0x01B0, 25: 0x02C3}
        for target_slot, glyph in expected.items():
            self.assertIn(
                glyph,
                [
                    builder.be16(
                        self.jp, builder.START_MENU_GLYPH_LIST + source_slot * 2
                    )
                    for source_slot in range(41)
                ],
            )
            self.assertEqual(
                builder.be16(
                    self.ko, builder.START_MENU_GLYPH_LIST + target_slot * 2
                ),
                glyph,
            )

    def test_load_records_keep_all_original_boundaries(self):
        for offset in (0x9B082, 0x9B0C0):
            self.assertEqual(builder.be16(self.jp, offset), 0xFFFF)
            self.assertEqual(builder.be16(self.ko, offset), 0xFFFF)
        self.assertEqual(len(self.words(0x9B066, 14)), 14)
        self.assertEqual(len(self.words(0x9B084, 7)), 7)
        self.assertEqual(len(self.words(0x9B092, 5)), 5)
        self.assertEqual(len(self.words(0x9B09C, 9)), 9)
        self.assertEqual(len(self.words(0x9B0AE, 9)), 9)


if __name__ == "__main__":
    unittest.main()
