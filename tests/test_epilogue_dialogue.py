from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tests.test_ending_dialogue import name_controls, record_words


ROOT = Path(__file__).resolve().parents[1]


class EpilogueDialogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = (ROOT / builder.IN_ROM).read_bytes()
        cls.korean = (ROOT / builder.OUT_ROM).read_bytes()
        cls.rows = builder.load_epilogue_dialogue_translations(
            ROOT / builder.EPILOGUE_DIALOGUE_TRANSLATIONS
        )

    def test_all_character_and_world_outcomes_are_complete(self):
        self.assertEqual(len(self.rows), 90)
        self.assertEqual(
            {int(row["english_record"]) for row in self.rows},
            set(range(1934, 1943))
            | set(range(1910, 1919))
            | set(range(1901, 1910))
            | set(range(1943, 1952))
            | set(range(1961, 1970))
            | set(range(1952, 1961))
            | set(range(1978, 1987))
            | set(range(1925, 1934))
            | set(range(1919, 1925))
            | set(range(1970, 1978))
            | set(range(1987, 1991)),
        )

    def test_controls_page_breaks_capacity_and_glyphs(self):
        for row in self.rows:
            start = int(row["address_int"])
            original = record_words(self.japanese, start)
            translated = record_words(self.korean, start)
            self.assertEqual(name_controls(translated), name_controls(original))
            self.assertEqual(translated.count(0xFFFD), original.count(0xFFFD))
            self.assertLessEqual(len(translated), len(original))
            index = 0
            while index < len(translated):
                word = translated[index]
                if word == 0xFFF7:
                    index += 2
                    continue
                if word in (0xFFFD, 0xFFFE, 0xFFFF, builder.SPACE_GLYPH):
                    index += 1
                    continue
                self.assertGreaterEqual(word, 0x7000, f"0x{start:06X}: 0x{word:04X}")
                index += 1

    def test_authored_lines_fit_the_dialogue_window(self):
        for row in self.rows:
            for line in str(row["text"]).replace("\f", "\n").splitlines():
                visible = builder.EVENT_NAME_CONTROL_RE.sub("이름", line)
                self.assertLessEqual(len(visible), 24, f"{row['address']}: {visible!r}")


if __name__ == "__main__":
    unittest.main()
