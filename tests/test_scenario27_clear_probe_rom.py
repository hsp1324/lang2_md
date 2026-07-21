import unittest

from tools import build_scenario27_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario27ClearProbeTests(unittest.TestCase):
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
        return allowed

    def test_changes_only_declared_enemy_fields_and_checksum(self):
        data = self.patched()
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, self.allowed_offsets())

    def test_weakens_all_enemy_records_without_changing_identity(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(self.source[base + 0x08], 0x04)
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            mercenaries = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[mercenaries : mercenaries + 6], b"\xFF" * 6)
            for offset in (
                0,
                0x08,
                FIELD_OFFSETS["level"],
                FIELD_OFFSETS["name_id"],
                FIELD_OFFSETS["class_id"],
                FIELD_OFFSETS["x"],
                FIELD_OFFSETS["y"],
            ):
                self.assertEqual(data[base + offset], self.source[base + offset])

    def test_preserves_demon_lord_and_bernhardt(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        expected = {
            probe_builder.DEMON_LORD_RECORD_INDEX: (
                0x65,
                0x5D,
                10,
                50,
                34,
                (15, 12),
            ),
            probe_builder.BERNHARDT_RECORD_INDEX: (
                0x0E,
                0x4E,
                10,
                58,
                41,
                (15, 3),
            ),
        }
        for index, values in expected.items():
            name_id, class_id, level, at, df, coordinates = values
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertFalse(bool(self.source[base] & 0x80))
            self.assertEqual(self.source[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(self.source[base + FIELD_OFFSETS["class_id"]], class_id)
            self.assertEqual(self.source[base + FIELD_OFFSETS["level"]], level)
            self.assertEqual(self.source[base + FIELD_OFFSETS["at"]], at)
            self.assertEqual(self.source[base + FIELD_OFFSETS["df"]], df)
            self.assertEqual(
                tuple(
                    self.source[
                        base + FIELD_OFFSETS["x"] : base + FIELD_OFFSETS["y"] + 1
                    ]
                ),
                coordinates,
            )
            self.assertEqual(data[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(data[base + FIELD_OFFSETS["class_id"]], class_id)

    def test_preserves_hidden_leon_identity_and_flag(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        base = layout.records_offset + probe_builder.HIDDEN_LEON_RECORD_INDEX * FIXED_RECORD_SIZE
        self.assertTrue(bool(self.source[base] & 0x80))
        self.assertEqual(self.source[base + 0x08], 0x04)
        self.assertEqual(self.source[base + FIELD_OFFSETS["name_id"]], 0x0D)
        self.assertEqual(self.source[base + FIELD_OFFSETS["class_id"]], 0x4D)
        self.assertEqual(self.source[base + FIELD_OFFSETS["level"]], 10)
        self.assertEqual(self.source[base + FIELD_OFFSETS["at"]], 51)
        self.assertEqual(self.source[base + FIELD_OFFSETS["df"]], 39)
        self.assertEqual(
            data[base + FIELD_OFFSETS["x"] : base + FIELD_OFFSETS["y"] + 1],
            b"\xFF\xFF",
        )

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

    def test_rejects_non_source_fixed_record(self):
        damaged = bytearray(self.production)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        damaged[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed record 0"):
            probe_builder.patch_probe(damaged, self.source)


if __name__ == "__main__":
    unittest.main()
