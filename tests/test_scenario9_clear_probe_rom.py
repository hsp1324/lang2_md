from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario9_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario9ClearProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def diagnostic_patched(self, mode: str) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            npc_annihilation=mode == "npc",
            protagonist_death=mode == "protagonist",
        )
        return data

    def test_probe_only_changes_laird_combat_fields_coordinates_and_checksum(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        base = probe_builder.LAIRD_RECORD_OFFSET
        expected_changes = {
            0x18E,
            0x18F,
            base + FIELD_OFFSETS["at"],
            base + FIELD_OFFSETS["df"],
            base + FIELD_OFFSETS["x"],
            base + FIELD_OFFSETS["y"],
            *(base + FIELD_OFFSETS["mercenaries"] + slot for slot in range(6)),
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_probe_preserves_every_other_fixed_record(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            if index == probe_builder.LAIRD_RECORD_INDEX:
                continue
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            self.assertEqual(data[start:end], self.source[start:end])

    def test_probe_weakens_and_moves_laird_only(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        base = probe_builder.LAIRD_RECORD_OFFSET
        self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
        self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
        self.assertEqual(data[base + FIELD_OFFSETS["x"]], 8)
        self.assertEqual(data[base + FIELD_OFFSETS["y"]], 27)
        self.assertEqual(
            data[base + FIELD_OFFSETS["name_id"]],
            probe_builder.SOURCE_LAIRD_NAME_ID,
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["class_id"]],
            probe_builder.SOURCE_LAIRD_CLASS_ID,
        )
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(data[mercenary_offset : mercenary_offset + 6], b"\xFF" * 6)

    def test_probe_rejects_changed_laird_record(self):
        data = bytearray(self.built)
        data[probe_builder.LAIRD_RECORD_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Laird record differs"):
            probe_builder.patch_probe(data, self.source)

    def test_probe_checksum_is_valid(self):
        data = bytearray(self.built)
        checksum = probe_builder.patch_probe(data, self.source)
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(checksum, expected)
        self.assertEqual(checksum, 0xCE1B)
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)

    def test_diagnostic_modes_change_only_wrapper_and_checksum(self):
        for mode, wrapper in (
            ("npc", probe_builder.npc_annihilation_wrapper_code()),
            ("protagonist", probe_builder.protagonist_death_wrapper_code()),
        ):
            with self.subTest(mode=mode):
                data = self.diagnostic_patched(mode)
                expected_changes = {
                    0x18E,
                    0x18F,
                    *range(
                        probe_builder.START_MENU_ENTRY_OPERAND,
                        probe_builder.START_MENU_ENTRY_OPERAND + 4,
                    ),
                    *range(
                        probe_builder.RUNTIME_WRAPPER,
                        probe_builder.RUNTIME_WRAPPER + len(wrapper),
                    ),
                }
                changed = {
                    index
                    for index, (before, after) in enumerate(zip(self.built, data))
                    if before != after
                }
                self.assertLessEqual(changed, expected_changes)

    def test_diagnostic_modes_preserve_all_scenario_fixed_records(self):
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for mode in ("npc", "protagonist"):
            data = self.diagnostic_patched(mode)
            for index in range(layout.record_count):
                start = layout.records_offset + index * FIXED_RECORD_SIZE
                end = start + FIXED_RECORD_SIZE
                self.assertEqual(data[start:end], self.source[start:end])

    def test_npc_annihilation_marks_only_runtime_groups_seven_to_nine(self):
        code = probe_builder.npc_annihilation_wrapper_code()
        for group in (7, 8, 9):
            record = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
            )
            self.assertIn(
                bytes.fromhex("00 39 00 80")
                + (
                    record + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
                ).to_bytes(4, "big"),
                code,
            )
            self.assertIn(
                bytes.fromhex("13 FC 00 00")
                + (record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
                code,
            )
            self.assertIn(
                bytes.fromhex("13 FC 00 FF")
                + (record + probe_builder.RUNTIME_X_OFFSET).to_bytes(4, "big"),
                code,
            )
        self.assertEqual(
            code[-6:],
            bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_protagonist_death_marks_only_runtime_group_zero(self):
        code = probe_builder.protagonist_death_wrapper_code()
        protagonist = probe_builder.RUNTIME_GROUP_BASE
        self.assertIn(
            bytes.fromhex("00 39 00 80")
            + (
                protagonist + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
            ).to_bytes(4, "big"),
            code,
        )
        self.assertNotIn(
            (
                probe_builder.RUNTIME_GROUP_BASE
                + 7 * probe_builder.RUNTIME_GROUP_SIZE
                + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
            ).to_bytes(4, "big"),
            code,
        )

    def test_diagnostic_modes_conflict(self):
        data = bytearray(self.built)
        with self.assertRaisesRegex(ValueError, "modes conflict"):
            probe_builder.patch_probe(
                data,
                self.source,
                npc_annihilation=True,
                protagonist_death=True,
            )

    def test_diagnostic_checksums_are_valid(self):
        for mode, checksum in (("npc", 0x93DE), ("protagonist", 0xE3EE)):
            with self.subTest(mode=mode):
                data = self.diagnostic_patched(mode)
                expected = sum(
                    int.from_bytes(data[offset : offset + 2], "big")
                    for offset in range(0x200, len(data), 2)
                ) & 0xFFFF
                self.assertEqual(
                    int.from_bytes(data[0x18E:0x190], "big"),
                    expected,
                )
                self.assertEqual(expected, checksum)


if __name__ == "__main__":
    unittest.main()
