from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario1_heavy_horseman_battle_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario1HeavyHorsemanBattleProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.production = (ROOT / builder.OUT_ROM).read_bytes()

    def patched(self) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(data, self.source)
        return data

    def test_probe_preserves_source_laird_identity_and_mercenaries(self):
        data = self.patched()
        base = probe_builder.LAIRD_RECORD_OFFSET
        self.assertEqual(
            data[base + FIELD_OFFSETS["name_id"]],
            probe_builder.LAIRD_NAME_ID,
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["class_id"]],
            probe_builder.LAIRD_CLASS_ID,
        )
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(
            data[mercenary_offset : mercenary_offset + 6],
            bytes(
                [
                    probe_builder.HEAVY_HORSEMAN_ID,
                    probe_builder.HEAVY_HORSEMAN_ID,
                    0xFF,
                    0xFF,
                    0xFF,
                    0xFF,
                ]
            ),
        )

    def test_probe_only_changes_coordinates_and_checksum(self):
        data = self.patched()
        layout = scenario_layout(self.source, 1)
        expected_changes = {0x18E, 0x18F}
        for record_index in (
            *probe_builder.HIDDEN_UNRELATED_ENEMY_RECORD_INDEXES,
            probe_builder.LAIRD_RECORD_INDEX,
        ):
            base = layout.records_offset + record_index * FIXED_RECORD_SIZE
            expected_changes.add(base + FIELD_OFFSETS["x"])
            expected_changes.add(base + FIELD_OFFSETS["y"])
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_probe_preserves_event_records_and_stages_only_laird_enemy_group(self):
        data = self.patched()
        layout = scenario_layout(self.source, 1)
        for record_index in range(layout.record_count):
            base = layout.records_offset + record_index * FIXED_RECORD_SIZE
            actual = (
                data[base + FIELD_OFFSETS["x"]],
                data[base + FIELD_OFFSETS["y"]],
            )
            if record_index == probe_builder.LAIRD_RECORD_INDEX:
                self.assertEqual(
                    actual,
                    (probe_builder.PROBE_LAIRD_X, probe_builder.PROBE_LAIRD_Y),
                )
            elif record_index in probe_builder.HIDDEN_UNRELATED_ENEMY_RECORD_INDEXES:
                self.assertEqual(actual, (0xFF, 0xFF))
            else:
                self.assertEqual(
                    actual,
                    (
                        self.source[base + FIELD_OFFSETS["x"]],
                        self.source[base + FIELD_OFFSETS["y"]],
                    ),
                )

    def test_probe_rejects_changed_source_heavy_horseman_slots(self):
        source = bytearray(self.source)
        source[
            probe_builder.LAIRD_RECORD_OFFSET + FIELD_OFFSETS["mercenaries"]
        ] ^= 1
        with self.assertRaisesRegex(ValueError, "Laird mercenaries differ"):
            probe_builder.patch_probe(bytearray(self.production), source)

    def test_probe_checksum_is_valid(self):
        data = self.patched()
        expected = sum(
            builder.be16(data, offset) for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(expected, 0xDDC6)
        self.assertEqual(builder.be16(data, 0x18E), expected)


if __name__ == "__main__":
    unittest.main()
