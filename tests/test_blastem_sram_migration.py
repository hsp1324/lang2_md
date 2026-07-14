from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.run_blastem_sequence import (
    JP_DEFAULT_HERO_NAME,
    JP_DEFAULT_HERO_DIALOGUE_NAME,
    KO_DEFAULT_HERO_NAME,
    MANUAL_SLOT_CHECKSUM_OFFSET,
    MANUAL_SLOT_HERO_DIALOGUE_NAME_OFFSET,
    MANUAL_SLOT_HERO_NAME_OFFSET,
    manual_slot_checksum,
    migrate_scenario_select_default_name,
    scenario_select_keys,
)


class BlastEmSramMigrationTests(unittest.TestCase):
    KO_DIALOGUE_NAME = bytes.fromhex("70 01 70 02 FF FF FF FF FF FF")

    def make_sram(self) -> tuple[bytearray, int]:
        data = bytearray(0x2000)
        base = 0x194E
        start = base + MANUAL_SLOT_HERO_NAME_OFFSET
        data[start : start + len(JP_DEFAULT_HERO_NAME)] = JP_DEFAULT_HERO_NAME
        dialogue_start = base + MANUAL_SLOT_HERO_DIALOGUE_NAME_OFFSET
        data[
            dialogue_start : dialogue_start + len(JP_DEFAULT_HERO_DIALOGUE_NAME)
        ] = JP_DEFAULT_HERO_DIALOGUE_NAME
        checksum = manual_slot_checksum(data, base)
        offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
        data[offset : offset + 2] = checksum.to_bytes(2, "big")
        return data, base

    def test_migrates_exact_japanese_default_and_updates_checksum(self):
        data, base = self.make_sram()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(data)
            self.assertEqual(
                migrate_scenario_select_default_name(path, self.KO_DIALOGUE_NAME),
                1,
            )
            migrated = path.read_bytes()

        start = base + MANUAL_SLOT_HERO_NAME_OFFSET
        self.assertEqual(
            migrated[start : start + len(KO_DEFAULT_HERO_NAME)],
            KO_DEFAULT_HERO_NAME,
        )
        dialogue_start = base + MANUAL_SLOT_HERO_DIALOGUE_NAME_OFFSET
        self.assertEqual(
            migrated[dialogue_start : dialogue_start + len(self.KO_DIALOGUE_NAME)],
            self.KO_DIALOGUE_NAME,
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
                migrate_scenario_select_default_name(path, self.KO_DIALOGUE_NAME)
            self.assertEqual(path.read_bytes(), data)

    def test_finishes_partially_migrated_default_name(self):
        data, base = self.make_sram()
        start = base + MANUAL_SLOT_HERO_NAME_OFFSET
        data[start : start + len(KO_DEFAULT_HERO_NAME)] = KO_DEFAULT_HERO_NAME
        offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
        data[offset : offset + 2] = manual_slot_checksum(data, base).to_bytes(2, "big")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(data)
            self.assertEqual(
                migrate_scenario_select_default_name(path, self.KO_DIALOGUE_NAME),
                1,
            )
            migrated = path.read_bytes()

        dialogue_start = base + MANUAL_SLOT_HERO_DIALOGUE_NAME_OFFSET
        self.assertEqual(
            migrated[dialogue_start : dialogue_start + len(self.KO_DIALOGUE_NAME)],
            self.KO_DIALOGUE_NAME,
        )
        self.assertEqual(
            int.from_bytes(migrated[offset : offset + 2], "big"),
            manual_slot_checksum(migrated, base),
        )

    def test_leaves_custom_dialogue_name_untouched(self):
        data, _ = self.make_sram()
        dialogue_start = 0x194E + MANUAL_SLOT_HERO_DIALOGUE_NAME_OFFSET
        data[dialogue_start : dialogue_start + 10] = bytes.fromhex(
            "70 03 70 04 FF FF FF FF FF FF"
        )
        checksum_offset = 0x194E + MANUAL_SLOT_CHECKSUM_OFFSET
        data[checksum_offset : checksum_offset + 2] = manual_slot_checksum(
            data, 0x194E
        ).to_bytes(2, "big")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(data)
            self.assertEqual(
                migrate_scenario_select_default_name(path, self.KO_DIALOGUE_NAME),
                0,
            )
            self.assertEqual(path.read_bytes(), data)


class BlastEmScenarioSelectTests(unittest.TestCase):
    def test_selector_cheat_uses_short_verified_key_intervals(self):
        keys = scenario_select_keys(27)
        cheat_start = keys.index("left@0.12:0.05")
        self.assertEqual(
            keys[cheat_start : cheat_start + 4],
            [
                "left@0.12:0.05",
                "right@0.12:0.05",
                "start@0.12:0.05",
                "c@0.12:0.8",
            ],
        )
        self.assertEqual(keys.count("down:0.08"), 26)
        self.assertEqual(keys[-1], "c:4.0")

    def test_selector_rejects_out_of_range_scenario(self):
        for scenario_number in (0, 32):
            with self.assertRaisesRegex(ValueError, "1..31"):
                scenario_select_keys(scenario_number)


if __name__ == "__main__":
    unittest.main()
