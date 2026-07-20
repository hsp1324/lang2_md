from pathlib import Path
import unittest

from tools import build_scenario10_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario10ClearProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(self) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(data, self.source)
        return data

    def test_changes_only_monster_combat_fields(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        allowed = set()
        for index in range(
            probe_builder.FIRST_MONSTER_RECORD_INDEX,
            probe_builder.LAST_MONSTER_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            allowed.update(
                {
                    base + FIELD_OFFSETS["at"],
                    base + FIELD_OFFSETS["df"],
                    *(
                        base + FIELD_OFFSETS["mercenaries"] + slot
                        for slot in range(6)
                    ),
                }
            )
        allowed.update({0x18E, 0x18F})
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertEqual(changed - allowed, set())

    def test_preserves_all_names_classes_levels_positions_and_events(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            for field in ("level", "x", "y", "name_id", "class_id"):
                self.assertEqual(
                    data[base + FIELD_OFFSETS[field]],
                    self.source[base + FIELD_OFFSETS[field]],
                )
        self.assertEqual(
            data[probe_builder.SCENARIO_HEADER : probe_builder.DEPLOYMENT_TABLE],
            self.source[probe_builder.SCENARIO_HEADER : probe_builder.DEPLOYMENT_TABLE],
        )

    def test_preserves_player_deployment(self):
        data = self.patched()
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(
            data[start : start + 4],
            probe_builder.SOURCE_FIRST_PLAYER_DEPLOYMENT,
        )
        self.assertEqual(
            data[probe_builder.DEPLOYMENT_TABLE : probe_builder.DEPLOYMENT_TABLE + 0x16],
            self.source[
                probe_builder.DEPLOYMENT_TABLE : probe_builder.DEPLOYMENT_TABLE + 0x16
            ],
        )

    def test_weakens_every_monster_without_touching_pirates_or_lester(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            if index < probe_builder.FIRST_MONSTER_RECORD_INDEX:
                self.assertEqual(
                    data[base : base + FIXED_RECORD_SIZE],
                    self.source[base : base + FIXED_RECORD_SIZE],
                )
                continue
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(
                data[mercenary_offset : mercenary_offset + 6],
                b"\xFF" * 6,
            )

    def test_rejects_non_source_monster_record(self):
        damaged = bytearray(self.production)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        damaged[layout.records_offset + 3 * FIXED_RECORD_SIZE] ^= 1
        with self.assertRaisesRegex(ValueError, "monster record 3"):
            probe_builder.patch_probe(damaged, self.source)


if __name__ == "__main__":
    unittest.main()
