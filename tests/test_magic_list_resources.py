from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class MagicListResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jp = JP_ROM.read_bytes()

    def test_names_fit_screen_and_dedicated_font_capacity(self):
        self.assertEqual(len(builder.MAGIC_LIST_NAMES), 31)
        self.assertTrue(
            all(
                len(name) <= builder.MAGIC_LIST_MAX_VISIBLE_GLYPHS
                for name in builder.MAGIC_LIST_NAMES
            )
        )
        self.assertLessEqual(
            sum(map(len, builder.MAGIC_LIST_NAMES)),
            builder.MAGIC_LIST_GLYPH_CAPACITY,
        )
        self.assertEqual(builder.MAGIC_LIST_NAMES[:23], (
            "매직애로우",
            "블래스트",
            "썬더",
            "파이어볼",
            "메테오",
            "블리져드",
            "토네이도",
            "턴언데드",
            "어스퀘이크",
            "힐1",
            "힐2",
            "포스힐1",
            "포스힐2",
            "슬립",
            "뮤트",
            "프로텍션",
            "어택",
            "존",
            "텔레포트",
            "일루전",
            "레지스트",
            "참",
            "소환",
        ))
        self.assertEqual(builder.MAGIC_LIST_NAMES[23:], (
            "엘리멘탈",
            "프레이야",
            "화이트드래곤",
            "발키리",
            "슬레이프니르",
            "펜릴",
            "요르문간드",
            "형님",
        ))

    def test_patch_updates_lengths_and_entire_dedicated_font_run(self):
        data = bytearray(self.jp)
        builder.patch_magic_list_names(data)

        start = builder.MAGIC_LIST_LENGTH_TABLE
        end = start + len(builder.MAGIC_LIST_NAMES)
        self.assertEqual(
            list(data[start:end]),
            [len(name) for name in builder.MAGIC_LIST_NAMES],
        )

        glyph_start = builder.glyph_data_offset(builder.MAGIC_LIST_GLYPH_START)
        used_bytes = sum(map(len, builder.MAGIC_LIST_NAMES)) * builder.GLYPH_BYTES
        self.assertNotEqual(
            data[glyph_start:glyph_start + used_bytes],
            self.jp[glyph_start:glyph_start + used_bytes],
        )
        blank_offset = builder.glyph_data_offset(builder.SPACE_GLYPH)
        blank = self.jp[blank_offset:blank_offset + builder.GLYPH_BYTES]
        self.assertEqual(
            data[glyph_start + used_bytes:glyph_start + used_bytes + builder.GLYPH_BYTES],
            blank,
        )

    def test_source_mutation_is_rejected(self):
        data = bytearray(self.jp)
        data[builder.MAGIC_LIST_LENGTH_TABLE] ^= 1
        with self.assertRaisesRegex(ValueError, "magic-list length table changed"):
            builder.patch_magic_list_names(data)

        data = bytearray(self.jp)
        data[builder.glyph_data_offset(builder.MAGIC_LIST_GLYPH_START)] ^= 1
        with self.assertRaisesRegex(ValueError, "magic-list glyph source changed"):
            builder.patch_magic_list_names(data)


if __name__ == "__main__":
    unittest.main()
