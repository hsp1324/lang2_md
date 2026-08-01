from pathlib import Path
import unittest

from tools import build_scenario10_result_surface_probe_rom as probe_builder
from tools.scenario_data import FIXED_RECORD_SIZE, scenario_layout


class Scenario10ResultSurfaceProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(self, source: bytes | None = None) -> bytearray:
        data = bytearray(self.production if source is None else source)
        probe_builder.patch_probe(data)
        return data

    def test_changes_only_operand_wrapper_and_checksum(self):
        data = self.patched()
        wrapper = probe_builder.result_surface_wrapper_code()
        allowed = {
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
            for index, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, allowed)

    def test_preserves_every_scenario_record_exactly(self):
        data = self.patched()
        layout = scenario_layout(
            self.production,
            probe_builder.SCENARIO_NUMBER,
        )
        for index in range(layout.record_count):
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            self.assertEqual(data[start:end], self.production[start:end])

    def test_preserves_candidate_specific_scenario_bytes(self):
        source = bytearray(self.production)
        layout = scenario_layout(source, probe_builder.SCENARIO_NUMBER)
        changed_offset = layout.records_offset + FIXED_RECORD_SIZE + 5
        source[changed_offset] ^= 0x01
        data = self.patched(bytes(source))
        self.assertEqual(data[changed_offset], source[changed_offset])

    def test_wrapper_marks_only_runtime_monster_groups(self):
        code = probe_builder.result_surface_wrapper_code()
        self.assertEqual(len(code), 0xFC)
        for group in range(
            probe_builder.FIRST_MONSTER_RUNTIME_GROUP,
            probe_builder.LAST_MONSTER_RUNTIME_GROUP + 1,
        ):
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

        for group in (0, 5, 7, 18):
            record = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
            )
            self.assertNotIn(
                (
                    record + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
                ).to_bytes(4, "big"),
                code,
            )
        self.assertEqual(
            code[-12:],
            bytes.fromhex("41 F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big")
            + bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_checksum_is_valid(self):
        data = self.patched()
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)

    def test_rejects_changed_start_operand(self):
        damaged = bytearray(self.production)
        damaged[probe_builder.START_MENU_ENTRY_OPERAND] ^= 1
        with self.assertRaisesRegex(ValueError, "entry operand changed"):
            probe_builder.patch_probe(damaged)

    def test_rejects_occupied_wrapper_region(self):
        damaged = bytearray(self.production)
        damaged[probe_builder.RUNTIME_WRAPPER] = 0
        with self.assertRaisesRegex(ValueError, "wrapper region is not empty"):
            probe_builder.patch_probe(damaged)


if __name__ == "__main__":
    unittest.main()
