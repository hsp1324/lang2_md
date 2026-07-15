import hashlib
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]


def record_bytes(data: bytes, start: int) -> bytes:
    capacity, controls, page_breaks = builder.direct_record_layout(data, start)
    if controls or page_breaks:
        raise AssertionError(f"credits record at 0x{start:06X} has controls")
    return data[start : start + capacity * 2]


class CreditsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = (ROOT / builder.IN_ROM).read_bytes()
        cls.korean = (ROOT / builder.OUT_ROM).read_bytes()
        cls.payload = builder.load_credits_translations(
            ROOT / builder.CREDITS_TRANSLATIONS
        )
        cls.rows = cls.payload["records"]

    def test_original_pointer_table_and_records_match_authored_hashes(self):
        table_end = (
            builder.CREDITS_POINTER_TABLE + builder.CREDITS_SOURCE_RECORD_COUNT * 4
        )
        pointer_table = self.japanese[builder.CREDITS_POINTER_TABLE:table_end]
        self.assertEqual(
            hashlib.sha256(pointer_table).hexdigest(),
            self.payload["pointer_table_sha256"],
        )
        records = []
        for index, row in enumerate(self.rows[: builder.CREDITS_SOURCE_RECORD_COUNT]):
            pointer = builder.be32(
                self.japanese, builder.CREDITS_POINTER_TABLE + index * 4
            )
            self.assertEqual(pointer, int(row["source_address_int"]))
            records.append(record_bytes(self.japanese, pointer))
        self.assertEqual(
            hashlib.sha256(b"".join(records)).hexdigest(),
            self.payload["source_records_sha256"],
        )

    def test_all_source_records_and_developer_credit_are_relocated(self):
        pointers = [
            builder.be32(
                self.korean, builder.CREDITS_POINTER_RELOC_BASE + index * 4
            )
            for index in range(builder.CREDITS_RECORD_COUNT)
        ]
        self.assertEqual(len(pointers), 61)
        self.assertEqual(pointers, sorted(pointers))
        self.assertEqual(len(pointers), len(set(pointers)))
        self.assertTrue(
            all(
                builder.CREDITS_RELOC_BASE <= pointer < builder.CREDITS_RELOC_LIMIT
                for pointer in pointers
            )
        )

    def test_translated_records_have_expected_lengths_and_custom_glyphs(self):
        for index, row in enumerate(self.rows):
            pointer = builder.be32(
                self.korean, builder.CREDITS_POINTER_RELOC_BASE + index * 4
            )
            encoded = record_bytes(self.korean, pointer)
            if row.get("preserve_original"):
                original = record_bytes(
                    self.japanese, int(row["source_address_int"])
                )
                self.assertEqual(encoded, original)
                continue
            words = [
                builder.be16(encoded, offset)
                for offset in range(0, len(encoded), 2)
            ]
            self.assertEqual(len(words), len(str(row["target_korean"])) + 1)
            self.assertEqual(words[-1], 0xFFFF)
            for word in words[:-1]:
                if word != builder.SPACE_GLYPH:
                    self.assertGreaterEqual(word, 0x7000)

    def test_digit_helper_is_not_repurposed(self):
        start = builder.CREDITS_DIGIT_HELPER
        end = start + builder.CREDITS_DIGIT_HELPER_SIZE
        self.assertEqual(self.korean[start:end], self.japanese[start:end])

    def test_credit_renderers_use_relocated_tables(self):
        self.assertEqual(
            self.korean[
                builder.CREDITS_SEQUENCE_TABLE_HOOK :
                builder.CREDITS_SEQUENCE_TABLE_HOOK + 6
            ],
            bytes.fromhex("43 F9")
            + builder.CREDITS_SEQUENCE_RELOC_BASE.to_bytes(4, "big"),
        )
        self.assertEqual(
            self.korean[
                builder.CREDITS_POINTER_TABLE_HOOK :
                builder.CREDITS_POINTER_TABLE_HOOK + 6
            ],
            bytes.fromhex("41 F9")
            + builder.CREDITS_POINTER_RELOC_BASE.to_bytes(4, "big"),
        )

    def test_final_credit_sequence_adds_localization_developer(self):
        final_sequence = builder.be32(
            self.korean,
            builder.CREDITS_SEQUENCE_RELOC_BASE
            + (builder.CREDITS_SEQUENCE_COUNT - 1) * 4,
        )
        self.assertEqual(builder.be16(self.korean, final_sequence), 2)
        second_entry = self.korean[final_sequence + 8 : final_sequence + 14]
        self.assertEqual(second_entry, builder.CREDITS_DEVELOPER_ENTRY)
        self.assertEqual(second_entry[0], builder.CREDITS_RECORD_COUNT - 1)
        self.assertTrue(self.rows[-1].get("synthetic"))
        self.assertEqual(self.rows[-1]["target_korean"], "한국어화 hsp1324")

    def test_relocation_does_not_overlap_other_declared_banks(self):
        self.assertGreaterEqual(
            builder.CREDITS_RELOC_BASE, builder.NAME_ENTRY_CONFIRM_COPY_ROUTINE + 0x100
        )
        self.assertLess(builder.CREDITS_RELOC_LIMIT, 0x3FF000)
        self.assertGreaterEqual(
            builder.CREDITS_SEQUENCE_RELOC_BASE,
            builder.BYTE_UI_NAME_STRING_RELOC_LIMIT,
        )
        self.assertLessEqual(
            builder.CREDITS_SEQUENCE_RELOC_LIMIT,
            builder.CREDITS_POINTER_RELOC_BASE,
        )
        self.assertLess(builder.CREDITS_POINTER_RELOC_LIMIT, 0x3FF000)


if __name__ == "__main__":
    unittest.main()
