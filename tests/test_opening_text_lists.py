from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class OpeningTextListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = JP_ROM.read_bytes()

    def test_source_terminator_layout_is_locked(self):
        self.assertEqual(
            set(builder.OPENING_TEXT_LIST_PATCHES),
            set(builder.OPENING_TEXT_LIST_SOURCE_TERMINATOR_INDICES),
        )
        for offset, (renderer_count, _) in builder.OPENING_TEXT_LIST_PATCHES.items():
            terminator_index = builder.OPENING_TEXT_LIST_SOURCE_TERMINATOR_INDICES[
                offset
            ]
            words = [
                builder.be16(self.rom, offset + index * 2)
                for index in range(renderer_count)
            ]
            if terminator_index is None:
                self.assertNotIn(0xFFFF, words)
            else:
                self.assertNotIn(0xFFFF, words[:terminator_index])
                self.assertEqual(
                    builder.be16(self.rom, offset + terminator_index * 2),
                    0xFFFF,
                )

    def test_patch_preserves_each_original_terminator(self):
        data = bytearray(self.rom)
        builder.expand_rom(data)
        builder.install_blank_custom_space(data)
        texts = [text for _, text in builder.OPENING_TEXT_LIST_PATCHES.values()]
        chars = builder.collect_chars(
            builder.RETIRED_OPENING_TEXT_GLYPH_COMPATIBILITY_TEXT,
            *texts,
        )
        glyph_by_char = builder.install_custom_glyphs(data, chars)

        builder.patch_opening_text_lists(data, glyph_by_char)

        expected_words = {}
        for offset, (renderer_count, text) in builder.OPENING_TEXT_LIST_PATCHES.items():
            terminator_index = builder.OPENING_TEXT_LIST_SOURCE_TERMINATOR_INDICES[
                offset
            ]
            storage_capacity = (
                renderer_count if terminator_index is None else terminator_index
            )
            expected = [
                builder.OPENING_SPACE_GLYPH
                if char == " "
                else glyph_by_char[char]
                for char in text
            ]
            expected.extend(
                [builder.OPENING_SPACE_GLYPH] * (storage_capacity - len(expected))
            )
            for index, value in enumerate(expected):
                expected_words[offset + index * 2] = value
            if terminator_index is not None:
                expected_words[offset + terminator_index * 2] = 0xFFFF

        for offset, expected in expected_words.items():
            self.assertEqual(builder.be16(data, offset), expected)

    def test_reviewed_ending_montage_drops_invented_scenario_one_recap(self):
        texts = {
            offset: text
            for offset, (_, text) in builder.OPENING_TEXT_LIST_PATCHES.items()
        }
        self.assertNotIn("리아나가 위험해", "".join(texts.values()))
        self.assertEqual(
            texts[0xA6CEC],
            "리아나: 그 마음 덕분에 많은 동료를 얻었고... 폭주한 제국도 막을 수 있었어.",
        )
        self.assertIn("베른하르트", texts[0xA6C2A])
        self.assertIn("랑그릿사의 힘", texts[0xA6D5E])
        self.assertIn("이상을 실현", texts[0xA6E80])
        for address in (0xA6BEA, 0xA6CA6, 0xA6DFE, 0xA6F02):
            self.assertTrue(texts[address].startswith(": "))
        self.assertEqual(
            builder.OPENING_TEXT_LIST_REVIEWED_ADDRESSES,
            set(texts) - {0xA6B20, 0xA6B54},
        )


if __name__ == "__main__":
    unittest.main()
