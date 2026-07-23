from pathlib import Path
import unittest

from tools.class_hire_data import (
    CLASS_RECORD_SIZE,
    CLASS_RECORD_TABLE,
    class_record_offset,
    patch_class_hire_unlocks,
    read_class_hire_unlocks,
)


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class ClassHireDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()

    def test_reads_stored_bit_indexes_as_mercenary_class_ids(self):
        record = read_class_hire_unlocks(self.source, 1)
        self.assertEqual(record.class_id, 1)
        self.assertEqual(record.hire_class_ids, (0x64, 0xFF))
        self.assertEqual(record.offset, CLASS_RECORD_TABLE + CLASS_RECORD_SIZE + 0x1A)

    def test_patch_changes_only_the_two_owned_bytes(self):
        data = bytearray(self.source)
        patch_class_hire_unlocks(data, [{
            "class_id": 1,
            "hire_class_ids": [0x62, 0x71],
        }])
        changed = [
            index
            for index, (before, after) in enumerate(zip(self.source, data))
            if before != after
        ]
        base = class_record_offset(1)
        self.assertEqual(changed, [base + 0x1A, base + 0x1B])
        self.assertEqual(
            read_class_hire_unlocks(data, 1).hire_class_ids,
            (0x62, 0x71),
        )

    def test_rejects_non_md_hire_ids_and_duplicate_rows(self):
        data = bytearray(self.source)
        with self.assertRaisesRegex(ValueError, "0x62..0x71"):
            patch_class_hire_unlocks(data, [{
                "class_id": 1,
                "hire_class_ids": [0x61, 0xFF],
            }])
        with self.assertRaisesRegex(ValueError, "repeats"):
            patch_class_hire_unlocks(data, [
                {"class_id": 1, "hire_class_ids": [0x62, 0xFF]},
                {"class_id": 1, "hire_class_ids": [0x63, 0xFF]},
            ])


if __name__ == "__main__":
    unittest.main()
