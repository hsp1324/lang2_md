from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


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
        self.assertEqual(self.words(0x9AE5C, 6), [1, 0x3F, 0x3F, 4, 5, 16])
        self.assertEqual(builder.be16(self.ko, 0x9AE68), 0xFFFF)

    def test_save_choices_use_korean_glyphs(self):
        chars = builder.collect_chars(
            *builder.START_MENU_TEXTS,
            *builder.START_SUBMENU_TEXTS,
        )
        glyph_by_char = {
            char: 0x7000 + index for index, char in enumerate(chars)
        }
        patched = bytearray(self.jp)
        builder.patch_start_menu(patched, glyph_by_char)
        builder.patch_start_submenus(patched, glyph_by_char)
        expected = {
            1: glyph_by_char["예"],
            4: glyph_by_char["아"],
            5: glyph_by_char["니"],
        }
        for target_slot, glyph in expected.items():
            self.assertEqual(
                builder.be16(
                    patched, builder.START_MENU_GLYPH_LIST + target_slot * 2
                ),
                glyph,
            )
        self.assertEqual(
            builder.be16(patched, builder.START_MENU_GLYPH_LIST + 16 * 2),
            glyph_by_char["오"],
        )
        self.assertEqual(
            [
                builder.be16(patched, 0x9AE58 + index * 2)
                for index in range(8)
            ],
            [0x0003, 0x0002, 1, 0x3F, 0x3F, 4, 5, 16],
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

    def test_config_entry_describes_the_control_settings_screen(self):
        self.assertIn("조작설정", builder.START_SUBMENU_TEXTS)
        self.assertNotIn("설정완료", builder.START_SUBMENU_TEXTS)
        self.assertEqual(self.words(0x9AEBC, 6), [8, 40, 21, 22, 0x3F, 0x3F])


if __name__ == "__main__":
    unittest.main()
