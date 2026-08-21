from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / builder.IN_ROM


class OrderSubmenuResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = bytearray(JP_ROM.read_bytes())
        builder.expand_rom(cls.data)
        glyph_texts = [
            *(text for _, text in builder.DIRECT_WORD_SEQUENCE_PATCHES.values()),
            builder.CLASS_CHANGE_GLYPH_TEXT,
            *builder.ORDER_SUBMENU_GLYPH_SLOTS.values(),
            *builder.UNIT_NOTICE_GLYPH_SLOTS.values(),
        ]
        cls.glyphs = builder.install_custom_glyphs(
            cls.data,
            builder.collect_chars(*glyph_texts),
        )
        builder.patch_direct_word_sequences(cls.data, cls.glyphs)
        cls.reverse = {glyph: char for char, glyph in cls.glyphs.items()}

    def test_battle_order_rows_end_in_manual_control(self) -> None:
        rows = []
        for row in range(4):
            offset = builder.ORDER_SUBMENU_TOKEN_STREAM + row * 6
            rows.append(
                "".join(
                    self.reverse[
                        builder.be16(
                            self.data,
                            0x9706A
                            + builder.be16(self.data, offset + index * 2) * 2,
                        )
                    ]
                    for index in range(2)
                )
            )
        self.assertEqual(rows, ["이동", "공격", "방어", "수동"])

    def test_arrangement_menu_keeps_automatic_label(self) -> None:
        self.assertEqual(
            builder.ARRANGE_MENU_GLYPH_LIST_PATCHES,
            {0xA2BAC: "이동순변경자"},
        )


if __name__ == "__main__":
    unittest.main()
