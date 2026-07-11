from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class ClassChangeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = JP_ROM.read_bytes()

    def test_class_change_code_loads_confirmed_resources(self):
        self.assertEqual(
            self.rom[0x02BB60:0x02BB66],
            bytes.fromhex("41 F9 00 0A 3C 9C"),
        )
        self.assertEqual(
            self.rom[0x02BB80:0x02BB86],
            bytes.fromhex("41 F9 00 0A 3C BA"),
        )
        self.assertEqual(
            self.rom[0x02BC0C:0x02BC12],
            bytes.fromhex("41 F9 00 0A 3C DC"),
        )

    def test_korean_slot_plan_preserves_all_shared_indexes(self):
        text = builder.CLASS_CHANGE_GLYPH_TEXT
        self.assertEqual(len(text), 15)
        self.assertEqual(text[:7], "클래스체인지 ")
        self.assertEqual(text[:11], "클래스체인지 가능  ")
        self.assertEqual(text[11:], "용병마법")

    def test_class_change_source_is_validated(self):
        data = bytearray(self.rom)
        glyphs = {
            char: 0x7000 + index
            for index, char in enumerate(dict.fromkeys(builder.CLASS_CHANGE_GLYPH_TEXT))
            if char != " "
        }
        builder.patch_class_change_glyph_list(data, glyphs)
        actual = [
            int.from_bytes(
                data[
                    builder.CLASS_CHANGE_GLYPH_LIST + index * 2 :
                    builder.CLASS_CHANGE_GLYPH_LIST + index * 2 + 2
                ],
                "big",
            )
            for index in range(15)
        ]
        self.assertEqual(actual[6], builder.SPACE_GLYPH)
        self.assertEqual(actual[9:11], [builder.SPACE_GLYPH, builder.SPACE_GLYPH])
        data = bytearray(self.rom)
        data[builder.CLASS_CHANGE_GLYPH_LIST] ^= 1
        with self.assertRaisesRegex(ValueError, "class-change glyph source changed"):
            builder.patch_class_change_glyph_list(data, glyphs)


if __name__ == "__main__":
    unittest.main()
