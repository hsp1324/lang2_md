import unittest

from tools import build_scenario14_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario14ClearProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(
        self,
        *,
        completion_layout: bool = False,
        protagonist_death: bool = False,
        leon_langrisser: bool = False,
    ) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(
            data,
            self.source,
            completion_layout=completion_layout,
            protagonist_death=protagonist_death,
            leon_langrisser=leon_langrisser,
        )
        return data

    def changed_offsets(self, data: bytearray) -> set[int]:
        return {
            offset
            for offset, (before, after) in enumerate(
                zip(self.production, data)
            )
            if before != after
        }

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

    def test_changes_only_declared_combat_fields_and_checksum(self):
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
            for offset in (
                0,
                FIELD_OFFSETS["level"],
                FIELD_OFFSETS["name_id"],
                FIELD_OFFSETS["class_id"],
                FIELD_OFFSETS["x"],
                FIELD_OFFSETS["y"],
            ):
                self.assertEqual(data[base + offset], self.source[base + offset])

    def test_completion_layout_moves_only_elwin_below_langrisser(self):
        data = self.patched(completion_layout=True)
        changed = self.changed_offsets(data)
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

    def test_protagonist_death_changes_only_wrapper_and_checksum(self):
        data = self.patched(protagonist_death=True)
        wrapper = probe_builder.protagonist_death_wrapper_code()
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
        self.assertLessEqual(self.changed_offsets(data), allowed)

    def test_protagonist_death_preserves_source_scenario_data(self):
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        fixed_end = (
            layout.records_offset
            + layout.record_count * FIXED_RECORD_SIZE
        )
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        deployments = probe_builder.deployment_bytes(
            probe_builder.SOURCE_PLAYER_DEPLOYMENTS
        )
        data = self.patched(protagonist_death=True)
        self.assertEqual(
            data[start : start + len(deployments)],
            deployments,
        )
        self.assertEqual(
            data[layout.records_offset:fixed_end],
            self.source[layout.records_offset:fixed_end],
        )

    def test_leon_langrisser_changes_only_source_leon_activation(self):
        data = self.patched(leon_langrisser=True)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        leon = (
            layout.records_offset
            + probe_builder.LEON_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        allowed = {
            0x18E,
            0x18F,
            leon,
            leon + FIELD_OFFSETS["x"],
            leon + FIELD_OFFSETS["y"],
        }
        self.assertLessEqual(self.changed_offsets(data), allowed)
        self.assertEqual(data[leon], self.source[leon] & 0x7F)
        self.assertEqual(
            tuple(
                data[
                    leon + FIELD_OFFSETS["x"] :
                    leon + FIELD_OFFSETS["y"] + 1
                ]
            ),
            probe_builder.LEON_PROBE_POSITION,
        )
        for offset in (
            FIELD_OFFSETS["level"],
            FIELD_OFFSETS["at"],
            FIELD_OFFSETS["df"],
            FIELD_OFFSETS["name_id"],
            FIELD_OFFSETS["class_id"],
        ):
            self.assertEqual(data[leon + offset], self.source[leon + offset])
        mercenaries = leon + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(
            data[mercenaries : mercenaries + 6],
            self.source[mercenaries : mercenaries + 6],
        )
        for index in range(layout.record_count - 1):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(
                data[base : base + FIXED_RECORD_SIZE],
                self.source[base : base + FIXED_RECORD_SIZE],
            )

    def test_protagonist_death_wrapper_targets_only_group_zero(self):
        wrapper = probe_builder.protagonist_death_wrapper_code()
        record = probe_builder.RUNTIME_GROUP_BASE
        for offset in (
            probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET,
            probe_builder.RUNTIME_HP_OFFSET,
            probe_builder.RUNTIME_X_OFFSET,
        ):
            self.assertIn((record + offset).to_bytes(4, "big"), wrapper)

    def test_diagnostic_modes_conflict(self):
        modes = (
            {"completion_layout": True, "protagonist_death": True},
            {"completion_layout": True, "leon_langrisser": True},
            {"protagonist_death": True, "leon_langrisser": True},
        )
        for kwargs in modes:
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(ValueError, "conflict"):
                    probe_builder.patch_probe(
                        bytearray(self.production),
                        self.source,
                        **kwargs,
                    )

    def test_source_verified_langrisser_triggers_are_locked(self):
        for offset, expected in probe_builder.LANGRISSER_SUCCESS_TRIGGERS.items():
            self.assertEqual(
                self.source[offset : offset + len(expected)],
                expected,
            )
            self.assertEqual(expected[4:8], bytes((16, 6, 16, 6)))
        self.assertEqual(probe_builder.LANGRISSER_POSITION, (16, 6))
        for offset, expected in (
            probe_builder.LEON_LANGRISSER_TRIGGER.items()
        ):
            self.assertEqual(
                self.source[offset : offset + len(expected)],
                expected,
            )
            self.assertEqual(expected[1], probe_builder.LEON_NAME_ID)
            self.assertEqual(expected[4:8], bytes((16, 6, 16, 6)))

    def test_default_and_completion_checksums_are_locked(self):
        default = bytearray(self.production)
        completion = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(default, self.source),
            0x7692,
        )
        self.assertEqual(
            probe_builder.patch_probe(
                completion,
                self.source,
                completion_layout=True,
            ),
            0x7678,
        )
        death = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(
                death,
                self.source,
                protagonist_death=True,
            ),
            0xF7AB,
        )
        leon = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(
                leon,
                self.source,
                leon_langrisser=True,
            ),
            0x90E3,
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

    def test_preserves_hidden_leon_record(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        base = (
            layout.records_offset
            + probe_builder.LEON_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        self.assertTrue(data[base] & 0x80)
        self.assertEqual(data[base + FIELD_OFFSETS["name_id"]], 0x0D)
        self.assertEqual(data[base + FIELD_OFFSETS["class_id"]], 0x4D)
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
