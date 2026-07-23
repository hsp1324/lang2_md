from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class ControlSettingsScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jp = JP_ROM.read_bytes()
        cls.ko = KO_ROM.read_bytes()

    @staticmethod
    def words(data, offset, count):
        return tuple(
            builder.be16(data, offset + index * 2)
            for index in range(count)
        )

    def test_source_glyph_list_and_layout_are_locked(self):
        self.assertEqual(
            self.words(
                self.jp,
                builder.CONTROL_SETTINGS_GLYPH_LIST,
                len(builder.CONTROL_SETTINGS_ORIGINAL_GLYPHS),
            ),
            builder.CONTROL_SETTINGS_ORIGINAL_GLYPHS,
        )
        for offset, original, _replacement in builder.CONTROL_SETTINGS_ROWS:
            self.assertEqual(self.words(self.jp, offset, len(original)), original)
            self.assertEqual(
                builder.be16(self.jp, offset + len(original) * 2),
                0xFFFF,
            )

    def test_korean_rows_keep_every_original_record_boundary(self):
        for offset, original, replacement in builder.CONTROL_SETTINGS_ROWS:
            self.assertEqual(self.words(self.ko, offset, len(original)), replacement)
            self.assertEqual(
                builder.be16(self.ko, offset + len(original) * 2),
                0xFFFF,
            )
        self.assertEqual(builder.be16(self.ko, 0x9B05C), 0xFFFF)

    def test_rgb_and_function_key_glyphs_are_preserved(self):
        # R/G/B, values 0..7, and the hard-coded A/C/S prefix tiles must remain.
        preserved_slots = tuple(range(5, 20))
        for slot in preserved_slots:
            offset = builder.CONTROL_SETTINGS_GLYPH_LIST + slot * 2
            self.assertEqual(
                builder.be16(self.ko, offset),
                builder.CONTROL_SETTINGS_ORIGINAL_GLYPHS[slot],
            )
        space_offset = (
            builder.CONTROL_SETTINGS_GLYPH_LIST
            + builder.CONTROL_SETTINGS_SPACE_SLOT * 2
        )
        self.assertEqual(builder.be16(self.ko, space_offset), builder.SPACE_GLYPH)

    def test_builder_inventory_contains_all_visible_korean_labels(self):
        for text in (
            "색상설정",
            "키 설정",
            "A 유닛검색",
            "B 취소",
            "C 결정/메뉴",
            "S 설정메뉴",
            "나가기",
        ):
            self.assertIn(text, builder.CONTROL_SETTINGS_TEXTS)
        self.assertIn("조작설정", builder.START_SUBMENU_TEXTS)


if __name__ == "__main__":
    unittest.main()
