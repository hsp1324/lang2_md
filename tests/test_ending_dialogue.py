import hashlib
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / builder.IN_ROM
KO_ROM = ROOT / builder.OUT_ROM


def record_words(data: bytes, start: int) -> list[int]:
    words = []
    for index in range(1024):
        word = builder.be16(data, start + index * 2)
        words.append(word)
        if word == 0xFFFF:
            return words
    raise AssertionError(f"unterminated record at 0x{start:06X}")


def name_controls(words: list[int]) -> list[tuple[int, int]]:
    controls = []
    index = 0
    while index < len(words):
        if words[index] == 0xFFF7:
            controls.append((0xFFF7, words[index + 1]))
            index += 2
        else:
            index += 1
    return controls


class EndingDialogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()
        cls.rows = builder.load_ending_dialogue_translations(
            ROOT / builder.ENDING_DIALOGUE_TRANSLATIONS
        )

    def test_all_fourteen_main_ending_records_are_present(self):
        main_records = {int(row["english_record"]) for row in self.rows}
        self.assertEqual(main_records, set(range(1785, 1799)))
        self.assertEqual(len(self.rows), 23)

    def test_source_hashes_and_capacities_are_valid(self):
        for row in self.rows:
            start = int(row["address_int"])
            capacity, _, _ = builder.direct_record_layout(self.japanese, start)
            source = self.japanese[start : start + capacity * 2]
            self.assertEqual(hashlib.sha256(source).hexdigest(), row["source_sha256"])
            self.assertLessEqual(len(record_words(self.korean, start)), capacity)

    def test_dynamic_names_and_page_breaks_are_preserved(self):
        for row in self.rows:
            start = int(row["address_int"])
            original = record_words(self.japanese, start)
            translated = record_words(self.korean, start)
            self.assertEqual(name_controls(translated), name_controls(original))
            self.assertEqual(translated.count(0xFFFD), original.count(0xFFFD))

    def test_translated_records_have_no_japanese_glyph_ids(self):
        for row in self.rows:
            start = int(row["address_int"])
            words = record_words(self.korean, start)
            index = 0
            while index < len(words):
                word = words[index]
                if word == 0xFFF7:
                    index += 2
                    continue
                if word in (0xFFFD, 0xFFFE, 0xFFFF, builder.SPACE_GLYPH):
                    index += 1
                    continue
                self.assertGreaterEqual(word, 0x7000, f"0x{start:06X}: 0x{word:04X}")
                index += 1

    def test_main_record_pointers_are_owned_by_ending_script(self):
        main_addresses = {
            int(row["address_int"])
            for row in self.rows
            if int(row["english_record"]) != 1798 or int(row["address_int"]) == 0x0967A4
        }
        pointer_region = self.japanese[0x095400:0x0954E2]
        for address in main_addresses:
            self.assertIn(address.to_bytes(4, "big"), pointer_region)

    def test_new_storage_bank_is_exercised(self):
        used = {
            word
            for row in self.rows
            for word in record_words(self.korean, int(row["address_int"]))
        }
        self.assertTrue(any(0x7300 <= word <= 0x73FE for word in used))

    def test_authored_lines_fit_the_dialogue_window(self):
        for row in self.rows:
            for line in str(row["text"]).replace("\f", "\n").splitlines():
                visible = builder.EVENT_NAME_CONTROL_RE.sub("이름", line)
                self.assertLessEqual(
                    len(visible),
                    24,
                    f"{row['address']} line is too wide: {visible!r}",
                )


if __name__ == "__main__":
    unittest.main()
