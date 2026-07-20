from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario3_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario3ClearProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        return data

    def test_probe_only_changes_verified_enemy_fields_and_checksum(self):
        data = self.patched()
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
                    base + FIELD_OFFSETS["x"],
                    base + FIELD_OFFSETS["y"],
                    *(
                        base + FIELD_OFFSETS["mercenaries"] + slot
                        for slot in range(6)
                    ),
                }
            )
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_probe_preserves_flags_names_classes_and_levels(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        preserved_offsets = (0x00, FIELD_OFFSETS["level"], FIELD_OFFSETS["name_id"], FIELD_OFFSETS["class_id"])
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            for field_offset in preserved_offsets:
                self.assertEqual(data[base + field_offset], self.source[base + field_offset])

    def test_probe_sets_expected_stats_coordinates_and_empty_mercenaries(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index, (x, y) in enumerate(
            probe_builder.PROBE_COORDINATES,
            start=probe_builder.FIRST_ENEMY_RECORD_INDEX,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], probe_builder.PROBE_AT)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], probe_builder.PROBE_DF)
            self.assertEqual(data[base + FIELD_OFFSETS["x"]], x)
            self.assertEqual(data[base + FIELD_OFFSETS["y"]], y)
            start = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[start : start + 6], b"\xFF" * 6)

    def test_probe_rejects_changed_enemy_record(self):
        data = bytearray(self.built)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        data[layout.records_offset + 2 * FIXED_RECORD_SIZE] ^= 1
        with self.assertRaisesRegex(ValueError, "enemy record 2 differs"):
            probe_builder.patch_probe(data, self.source)

    def test_probe_updates_megadrive_checksum(self):
        data = self.patched()
        expected = sum(
            builder.be16(data, offset) for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(builder.be16(data, 0x18E), expected)


if __name__ == "__main__":
    unittest.main()
