from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.run_blastem_sequence import (
    JP_DEFAULT_HERO_NAME,
    KO_DEFAULT_HERO_NAME,
    MANUAL_SLOT_CHECKSUM_OFFSET,
    MANUAL_SLOT_HERO_NAME_OFFSET,
    manual_slot_checksum,
    migrate_scenario_select_default_name,
)


class BlastEmSramMigrationTests(unittest.TestCase):
    def make_sram(self) -> tuple[bytearray, int]:
        data = bytearray(0x2000)
        base = 0x194E
        start = base + MANUAL_SLOT_HERO_NAME_OFFSET
        data[start : start + len(JP_DEFAULT_HERO_NAME)] = JP_DEFAULT_HERO_NAME
        checksum = manual_slot_checksum(data, base)
        offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
        data[offset : offset + 2] = checksum.to_bytes(2, "big")
        return data, base

    def test_migrates_exact_japanese_default_and_updates_checksum(self):
        data, base = self.make_sram()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(data)
            self.assertEqual(migrate_scenario_select_default_name(path), 1)
            migrated = path.read_bytes()

        start = base + MANUAL_SLOT_HERO_NAME_OFFSET
        self.assertEqual(
            migrated[start : start + len(KO_DEFAULT_HERO_NAME)],
            KO_DEFAULT_HERO_NAME,
        )
        offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
        self.assertEqual(
            int.from_bytes(migrated[offset : offset + 2], "big"),
            manual_slot_checksum(migrated, base),
        )

    def test_rejects_invalid_slot_before_writing(self):
        data, _ = self.make_sram()
        data[0x1950] ^= 1
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "invalid checksum"):
                migrate_scenario_select_default_name(path)
            self.assertEqual(path.read_bytes(), data)


if __name__ == "__main__":
    unittest.main()
