import unittest

from tools import build_scenario13_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario13ClearProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(self) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(data, self.source)
        return data

    def allowed_offsets(self) -> set[int]:
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        allowed = {0x18E, 0x18F}
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
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
        zorum = layout.records_offset + probe_builder.ZORUM_RECORD_INDEX * FIXED_RECORD_SIZE
        allowed.update({zorum + FIELD_OFFSETS["x"], zorum + FIELD_OFFSETS["y"]})
        return allowed

    def test_changes_only_declared_combat_fields_zorum_position_and_checksum(self):
        data = self.patched()
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, self.allowed_offsets())

    def test_weakens_every_enemy_without_changing_identity(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            mercenaries = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[mercenaries : mercenaries + 6], b"\xFF" * 6)
            for offset in (0, FIELD_OFFSETS["level"], FIELD_OFFSETS["name_id"], FIELD_OFFSETS["class_id"]):
                self.assertEqual(data[base + offset], self.source[base + offset])

    def test_preserves_player_deployments_and_event_header(self):
        data = self.patched()
        expected = probe_builder.deployment_bytes(
            probe_builder.SOURCE_PLAYER_DEPLOYMENTS
        )
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(data[start : start + len(expected)], expected)
        self.assertEqual(
            data[probe_builder.SCENARIO_HEADER : probe_builder.DEPLOYMENT_TABLE],
            self.source[probe_builder.SCENARIO_HEADER : probe_builder.DEPLOYMENT_TABLE],
        )

    def test_moves_only_zorum_from_source_position(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            position = (
                data[base + FIELD_OFFSETS["x"]],
                data[base + FIELD_OFFSETS["y"]],
            )
            source_position = (
                self.source[base + FIELD_OFFSETS["x"]],
                self.source[base + FIELD_OFFSETS["y"]],
            )
            if index == probe_builder.ZORUM_RECORD_INDEX:
                self.assertEqual(source_position, probe_builder.SOURCE_ZORUM_POSITION)
                self.assertEqual(position, probe_builder.PROBE_ZORUM_POSITION)
            else:
                self.assertEqual(position, source_position)

    def test_preserves_hidden_vargas_leon_and_laird_records(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        expected = {
            10: (15, 73),
            11: (13, 77),
            12: (17, 67),
        }
        for index, (name_id, class_id) in expected.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertTrue(data[base] & 0x80)
            self.assertEqual(data[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(data[base + FIELD_OFFSETS["class_id"]], class_id)
            self.assertEqual(
                data[base + FIELD_OFFSETS["x"] : base + FIELD_OFFSETS["y"] + 1],
                b"\xFF\xFF",
            )

    def test_rejects_non_source_enemy_record(self):
        damaged = bytearray(self.production)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        damaged[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "enemy record 0"):
            probe_builder.patch_probe(damaged, self.source)


if __name__ == "__main__":
    unittest.main()
