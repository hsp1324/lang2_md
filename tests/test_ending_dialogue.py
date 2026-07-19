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

    def translated_address(self, row: dict[str, object]) -> int:
        return builder.be32(self.korean, int(row["pointer_reference_int"]))

    def test_all_ending_visit_records_are_present(self):
        main_records = {int(row["english_record"]) for row in self.rows}
        self.assertEqual(main_records, set(range(1785, 1799)))
        self.assertEqual(len(self.rows), 23)

    def test_source_hashes_and_pointer_owners_are_valid(self):
        for row in self.rows:
            start = int(row["address_int"])
            capacity, _, _ = builder.direct_record_layout(self.japanese, start)
            source = self.japanese[start : start + capacity * 2]
            self.assertEqual(hashlib.sha256(source).hexdigest(), row["source_sha256"])
            pointer_reference = int(row["pointer_reference_int"])
            self.assertEqual(builder.be32(self.japanese, pointer_reference), start)
            self.assertEqual(self.korean[start : start + capacity * 2], source)

    def test_all_records_are_uniquely_relocated_in_order(self):
        addresses = [self.translated_address(row) for row in self.rows]
        self.assertEqual(addresses, sorted(addresses))
        self.assertEqual(len(addresses), len(set(addresses)))
        self.assertTrue(
            all(
                builder.ENDING_DIALOGUE_RELOC_BASE
                <= address
                < builder.ENDING_DIALOGUE_RELOC_LIMIT
                for address in addresses
            )
        )

    def test_dynamic_names_and_page_breaks_are_preserved(self):
        for row in self.rows:
            start = int(row["address_int"])
            original = record_words(self.japanese, start)
            translated = record_words(self.korean, self.translated_address(row))
            self.assertEqual(name_controls(translated), name_controls(original))
            self.assertEqual(translated.count(0xFFFD), original.count(0xFFFD))

    def test_translated_records_have_no_japanese_glyph_ids(self):
        for row in self.rows:
            start = self.translated_address(row)
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
            for word in record_words(self.korean, self.translated_address(row))
        }
        self.assertTrue(any(0x7300 <= word <= 0x73FE for word in used))

    def test_authored_lines_fit_the_dialogue_window(self):
        for row in self.rows:
            for page_number, page in enumerate(str(row["text"]).split("\f"), 1):
                lines = page.splitlines()
                self.assertLessEqual(
                    len(lines),
                    3,
                    f"{row['address']} page {page_number} has too many lines",
                )
                for line in lines:
                    visible = builder.EVENT_NAME_CONTROL_RE.sub("이름", line)
                    self.assertLessEqual(
                        len(visible),
                        24,
                        f"{row['address']} line is too wide: {visible!r}",
                    )


if __name__ == "__main__":
    unittest.main()
