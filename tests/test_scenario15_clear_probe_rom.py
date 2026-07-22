import unittest

from tools import build_scenario15_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario15ClearProbeTests(unittest.TestCase):
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
        if completion_layout:
            allowed.update(
                {
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 1,
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 3,
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

    def test_preserves_allied_scott_record(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        base = (
            layout.records_offset
            + probe_builder.SCOTT_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        self.assertEqual(
            data[base : base + FIXED_RECORD_SIZE],
            self.source[base : base + FIXED_RECORD_SIZE],
        )
        self.assertEqual(data[base + FIELD_OFFSETS["name_id"]], 0x06)
        self.assertEqual(data[base + FIELD_OFFSETS["class_id"]], 0x05)

    def test_weakens_every_enemy_without_changing_identity(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
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

    def test_completion_layout_moves_only_elwin_above_escape_region(self):
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

    def test_source_verified_completion_triggers_are_locked(self):
        for offset, expected in probe_builder.COMPLETION_TRIGGERS.items():
            self.assertEqual(
                self.source[offset : offset + len(expected)],
                expected,
            )
        escape = probe_builder.COMPLETION_TRIGGERS[0x19F148]
        self.assertEqual(escape[0], 0x0D)
        self.assertEqual(escape[1], 0x01)
        self.assertEqual(tuple(escape[4:8]), probe_builder.ESCAPE_BOUNDS)
        self.assertEqual(probe_builder.ESCAPE_TARGET, (3, 21))

    def test_default_and_completion_checksums_are_locked(self):
        default = bytearray(self.production)
        completion = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(default, self.source),
            0xE5E4,
        )
        self.assertEqual(
            probe_builder.patch_probe(
                completion,
                self.source,
                completion_layout=True,
            ),
            0xE5F6,
        )

    def test_preserves_imelda_and_hidden_enemy_identities(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        expected = {
            probe_builder.IMELDA_RECORD_INDEX: (0x15, 0x4A, False),
            8: (0x3E, 0x53, True),
            9: (0x0C, 0x60, True),
            10: (0x3F, 0x53, True),
            11: (0x52, 0x55, True),
        }
        for index, (name_id, class_id, hidden) in expected.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(bool(data[base] & 0x80), hidden)
            self.assertEqual(data[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(data[base + FIELD_OFFSETS["class_id"]], class_id)
            if hidden:
                self.assertEqual(
                    data[
                        base + FIELD_OFFSETS["x"] : base + FIELD_OFFSETS["y"] + 1
                    ],
                    b"\xFF\xFF",
                )

    def test_rejects_non_source_fixed_record(self):
        damaged = bytearray(self.production)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        damaged[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed record 0"):
            probe_builder.patch_probe(damaged, self.source)


if __name__ == "__main__":
    unittest.main()
