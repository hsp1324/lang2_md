from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario6_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario6ClearProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def test_probe_only_changes_enemy_combat_fields_coordinates_and_checksum(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        expected_changes = {0x18E, 0x18F}
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            expected_changes.update(
                {
                    base + FIELD_OFFSETS["at"],
                    base + FIELD_OFFSETS["df"],
                    *(
                        base + FIELD_OFFSETS["mercenaries"] + slot
                        for slot in range(6)
                    ),
                }
            )
            if index <= probe_builder.LAST_VISIBLE_ENEMY_RECORD_INDEX:
                expected_changes.update(
                    {base + FIELD_OFFSETS["x"], base + FIELD_OFFSETS["y"]}
                )
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_probe_preserves_all_allied_and_npc_records(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        start = layout.records_offset
        end = start + probe_builder.FIRST_ENEMY_RECORD_INDEX * FIXED_RECORD_SIZE
        self.assertEqual(data[start:end], self.source[start:end])

    def test_probe_weakens_enemies_and_moves_only_visible_records(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[mercenary_offset : mercenary_offset + 6], b"\xFF" * 6)
            if index <= probe_builder.LAST_VISIBLE_ENEMY_RECORD_INDEX:
                expected_x, expected_y = probe_builder.PROBE_VISIBLE_COORDINATES[
                    index - probe_builder.FIRST_ENEMY_RECORD_INDEX
                ]
                self.assertEqual(data[base + FIELD_OFFSETS["x"]], expected_x)
                self.assertEqual(data[base + FIELD_OFFSETS["y"]], expected_y)
            else:
                self.assertEqual(data[base + FIELD_OFFSETS["x"]], 0xFF)
                self.assertEqual(data[base + FIELD_OFFSETS["y"]], 0xFF)

    def test_probe_rejects_changed_enemy_record(self):
        data = bytearray(self.built)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        base = layout.records_offset + probe_builder.FIRST_ENEMY_RECORD_INDEX * FIXED_RECORD_SIZE
        data[base] ^= 1
        with self.assertRaisesRegex(ValueError, "enemy record 4 differs"):
            probe_builder.patch_probe(data, self.source)

    def test_probe_checksum_is_valid(self):
        data = bytearray(self.built)
        checksum = probe_builder.patch_probe(data, self.source)
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(checksum, expected)
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)


if __name__ == "__main__":
    unittest.main()
