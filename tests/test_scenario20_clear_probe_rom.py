import unittest

from tools import build_scenario20_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario20ClearProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(self, *, completion_layout: bool = False) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(
            data,
            self.source,
            completion_layout=completion_layout,
        )
        return data

    def allowed_offsets(self, *, completion_layout: bool = False) -> set[int]:
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        allowed = {0x18E, 0x18F}
        for index in range(layout.record_count):
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
        if completion_layout:
            allowed.update(
                {
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 1,
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 3,
                }
            )
            for index in probe_builder.COMPLETION_HIDDEN_RECORD_INDEXES:
                allowed.add(layout.records_offset + index * FIXED_RECORD_SIZE)
        return allowed

    def test_changes_only_declared_enemy_fields_and_checksum(self):
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
            self.assertEqual(self.source[base + 0x08], 0x04)
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            mercenaries = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[mercenaries : mercenaries + 6], b"\xFF" * 6)
            for offset in (
                0,
                FIELD_OFFSETS["level"],
                FIELD_OFFSETS["name_id"],
                FIELD_OFFSETS["class_id"],
                FIELD_OFFSETS["x"],
                FIELD_OFFSETS["y"],
            ):
                self.assertEqual(data[base + offset], self.source[base + offset])

    def test_preserves_fias_and_hidden_sea_monsters(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        expected = {
            probe_builder.FIAS_RECORD_INDEX: (0x73, 0x5D, 1, 46, 32, False),
            7: (0x52, 0x55, 6, 32, 27, True),
            8: (0x60, 0x5B, 4, 39, 32, True),
            9: (0x53, 0x55, 6, 32, 27, True),
        }
        for index, (name_id, class_id, level, at, df, hidden) in expected.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(bool(self.source[base] & 0x80), hidden)
            self.assertEqual(self.source[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(self.source[base + FIELD_OFFSETS["class_id"]], class_id)
            self.assertEqual(self.source[base + FIELD_OFFSETS["level"]], level)
            self.assertEqual(self.source[base + FIELD_OFFSETS["at"]], at)
            self.assertEqual(self.source[base + FIELD_OFFSETS["df"]], df)
            self.assertEqual(data[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(data[base + FIELD_OFFSETS["class_id"]], class_id)
            if hidden:
                self.assertEqual(
                    data[
                        base + FIELD_OFFSETS["x"] : base + FIELD_OFFSETS["y"] + 1
                    ],
                    b"\xFF\xFF",
                )
        fias = layout.records_offset + (
            probe_builder.FIAS_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        self.assertEqual(
            (
                self.source[fias + FIELD_OFFSETS["x"]],
                self.source[fias + FIELD_OFFSETS["y"]],
            ),
            probe_builder.FIAS_POSITION,
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

    def test_completion_layout_keeps_fias_record_index_and_hides_other_records(self):
        data = self.patched(completion_layout=True)
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(
            changed,
            self.allowed_offsets(completion_layout=True),
        )
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        expected = probe_builder.deployment_bytes(
            (
                probe_builder.COMPLETION_ELWIN_POSITION,
                *probe_builder.SOURCE_PLAYER_DEPLOYMENTS[1:],
            )
        )
        self.assertEqual(data[start : start + len(expected)], expected)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        fias_source = layout.records_offset + (
            probe_builder.FIAS_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        expected_fias = bytearray(
            self.source[fias_source : fias_source + FIXED_RECORD_SIZE]
        )
        expected_fias[FIELD_OFFSETS["at"]] = probe_builder.PROBE_AT
        expected_fias[FIELD_OFFSETS["df"]] = probe_builder.PROBE_DF
        mercenaries = FIELD_OFFSETS["mercenaries"]
        expected_fias[mercenaries : mercenaries + 6] = b"\xFF" * 6
        self.assertEqual(
            data[fias_source : fias_source + FIXED_RECORD_SIZE], expected_fias
        )
        for index in probe_builder.COMPLETION_HIDDEN_RECORD_INDEXES:
            enemy = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertTrue(bool(data[enemy] & 0x80))

    def test_default_and_completion_checksums_are_locked(self):
        default = bytearray(self.production)
        completion = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(default, self.source),
            0xE860,
        )
        self.assertEqual(
            probe_builder.patch_probe(
                completion,
                self.source,
                completion_layout=True,
            ),
            0xE87C,
        )

    def test_rejects_non_source_fixed_record(self):
        damaged = bytearray(self.production)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        damaged[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed record 0"):
            probe_builder.patch_probe(damaged, self.source)


if __name__ == "__main__":
    unittest.main()
