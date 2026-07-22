import unittest

from tools import build_scenario13_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario13ClearProbeTests(unittest.TestCase):
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
        zorum = layout.records_offset + probe_builder.ZORUM_RECORD_INDEX * FIXED_RECORD_SIZE
        allowed.update({zorum + FIELD_OFFSETS["x"], zorum + FIELD_OFFSETS["y"]})
        if completion_layout:
            wrapper = probe_builder.completion_hp_wrapper_code()
            allowed.update(
                range(
                    probe_builder.START_MENU_ENTRY_OPERAND,
                    probe_builder.START_MENU_ENTRY_OPERAND + 4,
                )
            )
            allowed.update(
                range(
                    probe_builder.COMPLETION_HP_WRAPPER,
                    probe_builder.COMPLETION_HP_WRAPPER + len(wrapper),
                )
            )
            for index in range(len(probe_builder.COMPLETION_ENEMY_POSITIONS)):
                enemy = layout.records_offset + index * FIXED_RECORD_SIZE
                allowed.update(
                    {
                        enemy + FIELD_OFFSETS["x"],
                        enemy + FIELD_OFFSETS["y"],
                    }
                )
            for index in range(len(probe_builder.COMPLETION_PLAYER_POSITIONS)):
                deployment = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + index * 4
                allowed.update({deployment + 1, deployment + 3})
            for index in probe_builder.COMPLETION_HIDDEN_RECORD_INDICES:
                enemy = layout.records_offset + index * FIXED_RECORD_SIZE
                allowed.add(enemy)
            vargas = (
                layout.records_offset
                + probe_builder.VARGAS_RECORD_INDEX * FIXED_RECORD_SIZE
            )
            allowed.add(vargas + FIELD_OFFSETS["class_id"])
        return allowed

    def test_changes_only_declared_combat_fields_zorum_position_and_checksum(self):
        data = self.patched()
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, self.allowed_offsets())

    def test_completion_layout_changes_only_declared_fields(self):
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

    def test_completion_layout_places_players_around_vargas_arrival_lane(self):
        data = self.patched(completion_layout=True)
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        expected_deployments = probe_builder.deployment_bytes(
            probe_builder.COMPLETION_PLAYER_POSITIONS
        )
        self.assertEqual(
            data[start : start + len(expected_deployments)],
            expected_deployments,
        )
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        zorum = layout.records_offset + probe_builder.ZORUM_RECORD_INDEX * FIXED_RECORD_SIZE
        self.assertEqual(
            tuple(
                data[
                    zorum + FIELD_OFFSETS["x"] : zorum + FIELD_OFFSETS["y"] + 1
                ]
            ),
            probe_builder.COMPLETION_ZORUM_POSITION,
        )
        for index, expected in enumerate(
            probe_builder.COMPLETION_ENEMY_POSITIONS
        ):
            enemy = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(
                tuple(
                    data[
                        enemy + FIELD_OFFSETS["x"] :
                        enemy + FIELD_OFFSETS["y"] + 1
                    ]
                ),
                expected,
            )

    def test_completion_layout_limits_active_route_to_zorum_and_fighter_vargas(self):
        data = self.patched(completion_layout=True)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in probe_builder.COMPLETION_HIDDEN_RECORD_INDICES:
            enemy = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertTrue(data[enemy] & 0x80)
        zorum = layout.records_offset + probe_builder.ZORUM_RECORD_INDEX * FIXED_RECORD_SIZE
        self.assertFalse(data[zorum] & 0x80)
        vargas = (
            layout.records_offset
            + probe_builder.VARGAS_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        self.assertEqual(
            data[vargas + FIELD_OFFSETS["name_id"]],
            self.source[vargas + FIELD_OFFSETS["name_id"]],
        )
        self.assertEqual(
            data[vargas + FIELD_OFFSETS["class_id"]],
            probe_builder.COMPLETION_VARGAS_CLASS,
        )
        self.assertEqual(data[vargas + FIELD_OFFSETS["df"]], 0)

    def test_completion_layout_installs_identity_guarded_vargas_hp_wrapper(self):
        data = self.patched(completion_layout=True)
        wrapper = probe_builder.completion_hp_wrapper_code()
        self.assertEqual(
            data[
                probe_builder.START_MENU_ENTRY_OPERAND :
                probe_builder.START_MENU_ENTRY_OPERAND + 4
            ],
            probe_builder.COMPLETION_HP_WRAPPER.to_bytes(4, "big"),
        )
        self.assertEqual(
            data[
                probe_builder.COMPLETION_HP_WRAPPER :
                probe_builder.COMPLETION_HP_WRAPPER + len(wrapper)
            ],
            wrapper,
        )
        self.assertIn(
            (probe_builder.VARGAS_RUNTIME_RECORD + 1).to_bytes(4, "big"),
            wrapper,
        )
        self.assertIn(
            (probe_builder.VARGAS_RUNTIME_RECORD + 3).to_bytes(4, "big"),
            wrapper,
        )

    def test_default_and_completion_checksums_are_locked(self):
        default = bytearray(self.production)
        completion = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(default, self.source),
            0xC2AA,
        )
        self.assertEqual(
            probe_builder.patch_probe(
                completion,
                self.source,
                completion_layout=True,
            ),
            0xA3AD,
        )

    def test_completion_layout_rejects_changed_start_entry(self):
        damaged = bytearray(self.production)
        damaged[probe_builder.START_MENU_ENTRY_OPERAND] ^= 1
        with self.assertRaisesRegex(ValueError, "Start-menu entry operand"):
            probe_builder.patch_probe(
                damaged,
                self.source,
                completion_layout=True,
            )

    def test_completion_layout_rejects_occupied_wrapper_region(self):
        damaged = bytearray(self.production)
        damaged[probe_builder.COMPLETION_HP_WRAPPER] = 0
        with self.assertRaisesRegex(ValueError, "wrapper region is not empty"):
            probe_builder.patch_probe(
                damaged,
                self.source,
                completion_layout=True,
            )

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
